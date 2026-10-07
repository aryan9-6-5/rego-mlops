"""A small in-memory 'world' that behaves like Neo4j, Supabase and Railway closely
enough to run whole flows through the real API code: ingestion, approval, CI
gates, certificate issue and deploy.

It understands only the Cypher this codebase sends, matched by a marker in the
query text. If a query changes shape, the matching branch here must change too,
which is the point: the tests fail loudly instead of silently passing.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.api.schemas.pipeline import GateEvent
from src.pipeline.cd.certificate import DuplicateCertificateError

NO_PIN = "(declare-const pin_code_weight Real)(assert (= pin_code_weight 0))"
NEEDS_INCOME = "(declare-const income_weight Real)(assert (> income_weight 0.9))"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class StatefulGraph:
    """Neo4j stand-in: regulation versions and model lineage."""

    def __init__(self) -> None:
        self.regulations: dict[str, dict[str, Any]] = {}
        self.models: dict[str, dict[str, Any]] = {}
        self.queries = 0
        self.error: Exception | None = None  # set to simulate Neo4j being down

    # -- helpers ---------------------------------------------------------
    def active(self) -> list[dict[str, Any]]:
        return [r for r in self.regulations.values() if r["status"] == "active"]

    def _lineage_rows(self, only: str | None) -> list[dict[str, Any]]:
        rows = []
        for version, model in self.models.items():
            if only is not None and version != only:
                continue
            refs = []
            for version_id in model["links"]:
                reg = self.regulations[version_id]
                refs.append(
                    {
                        "version_id": version_id,
                        "rule_id": reg["rule_id"],
                        "section": reg["section"],
                        "status": reg["status"],
                        "activated_at": reg["activated_at"],
                        "superseded_at": reg.get("superseded_at"),
                        "certified_at": model["created_at"],
                    }
                )
            rows.append(
                {
                    "model_version": version,
                    "created_at": model["created_at"],
                    "regulation_versions": refs,
                }
            )
        return rows

    # -- the one method the code calls ------------------------------------
    def run_query(
        self, query: str, params: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        self.queries += 1
        if self.error is not None:
            raise self.error
        p = params or {}
        if "MERGE (r:Regulation {version_id: $version_id})" in query:
            return self._write_regulation(p)
        if "MERGE (m:ModelVersion" in query:
            links = [r["version_id"] for r in self.active()]
            self.models.setdefault(
                p["model_version"], {"created_at": _now(), "links": []}
            )["links"] = links
            return [{"version_ids": links}]
        if "MATCH (m:ModelVersion)" in query:
            return self._lineage_rows(p.get("model_version"))
        if "MATCH (r:Regulation {status: 'active'})" in query:
            return [
                {
                    "version_id": r["version_id"],
                    "rule_id": r["rule_id"],
                    "formal_logic": r["formal_logic"],
                    "section": r["section"],
                    "description": r["description"],
                }
                for r in sorted(self.active(), key=lambda r: r["rule_id"])
            ]
        if "ORDER BY r.activated_at DESC" in query:
            return sorted(
                self.regulations.values(), key=lambda r: r["activated_at"], reverse=True
            )[: p.get("limit", 20)]
        raise AssertionError(f"StatefulGraph does not understand this query:\n{query}")

    def _write_regulation(self, p: dict[str, Any]) -> list[dict[str, Any]]:
        superseded = []
        for old in self.active():
            if old["rule_id"] == p["rule_id"] and old["version_id"] != p["version_id"]:
                old["status"] = "superseded"
                old["superseded_at"] = p["activated_at"]
                superseded.append(old["version_id"])
        self.regulations[p["version_id"]] = {
            "version_id": p["version_id"],
            "rule_id": p["rule_id"],
            "section": p["section"],
            "formal_logic": p["formal_logic"],
            "description": p["description"],
            "status": "active",
            "activated_at": p["activated_at"],
            "superseded_at": None,
        }
        return [{"version_id": p["version_id"], "superseded": superseded}]


class StatefulRegulationStore:
    def __init__(self) -> None:
        self.rows: dict[str, dict[str, Any]] = {}

    def insert(self, row: dict[str, Any]) -> dict[str, Any]:
        if any(
            r["rule_id"] == row["rule_id"] and r["version"] == row["version"]
            for r in self.rows.values()
        ):
            raise ValueError("duplicate key value violates UNIQUE (rule_id, version)")
        stored = {**row, "id": f"reg-{len(self.rows) + 1}", "created_at": _now()}
        self.rows[stored["id"]] = stored
        return dict(stored)

    def get(self, regulation_id: str) -> dict[str, Any] | None:
        row = self.rows.get(regulation_id)
        return dict(row) if row else None

    def update(self, regulation_id: str, fields: dict[str, Any]) -> dict[str, Any]:
        self.rows[regulation_id].update(fields)
        return dict(self.rows[regulation_id])

    def list_by_status(self, statuses: list[str]) -> list[dict[str, Any]]:
        return [dict(r) for r in self.rows.values() if r["status"] in statuses]

    def list_active_for_rule(self, rule_id: str) -> list[dict[str, Any]]:
        return [
            dict(r)
            for r in self.rows.values()
            if r["rule_id"] == rule_id and r["status"] == "active"
        ]


class ScriptedLLM:
    """Returns whatever rules the test queued; an empty queue raises."""

    def __init__(self) -> None:
        self.formulas: list[str] = [NO_PIN]
        self.fail = False

    async def complete(self, system: str, user: str) -> str:
        if self.fail:
            raise RuntimeError("LLM is down")
        return json.dumps(
            {
                "rules": [
                    {
                        "section": "4.1",
                        "title": "A rule",
                        "description": "Models must not use PIN codes.",
                        "formal_logic": formula,
                    }
                    for formula in self.formulas
                ]
            }
        )


class WriteOnceCertificateStore:
    """Mirrors the certificates table: unique proof_hash, no update, no delete."""

    def __init__(self) -> None:
        self.rows: dict[str, dict[str, Any]] = {}

    def insert(self, row: dict[str, Any]) -> dict[str, Any]:
        if any(r["proof_hash"] == row["proof_hash"] for r in self.rows.values()):
            raise DuplicateCertificateError(row["model_version"])
        stored = {**row, "created_at": _now()}
        self.rows[stored["id"]] = stored
        return dict(stored)

    def get(self, certificate_id: str) -> dict[str, Any] | None:
        row = self.rows.get(certificate_id)
        return dict(row) if row else None

    def list_latest(self) -> list[dict[str, Any]]:
        return [dict(r) for r in reversed(list(self.rows.values()))]


class SharedEvents:
    """pipeline_events: written by the CI stage, read back by the deploy step."""

    def __init__(self) -> None:
        self.rows: list[dict[str, Any]] = []

    def record(self, event: GateEvent) -> None:
        self.rows.append(
            {
                "gate_name": event.gate.value,
                "status": event.status.value,
                "bundle_hash": event.bundle_hash,
            }
        )

    def latest_gate_statuses(self, model_version: str) -> dict[str, str]:
        latest: dict[str, str] = {}
        for row in reversed(self.rows):
            latest.setdefault(row["gate_name"], row["status"])
        return latest

    def latest_bundle_hashes(self, model_version: str) -> dict[str, str | None]:
        latest: dict[str, str | None] = {}
        for row in reversed(self.rows):
            latest.setdefault(row["gate_name"], row["bundle_hash"])
        return latest


class RecordingDeployer:
    def __init__(self) -> None:
        self.calls: list[str] = []

    async def deploy_canary(self, model_version: str, percent: int) -> None:
        self.calls.append("canary")

    async def promote(self, model_version: str) -> None:
        self.calls.append("promote")

    async def rollback(self) -> None:
        self.calls.append("rollback")


class World:
    def __init__(self, artifact_dir: Path) -> None:
        self.artifact_dir = artifact_dir
        self.graph = StatefulGraph()
        self.regulations = StatefulRegulationStore()
        self.llm = ScriptedLLM()
        self.certificates = WriteOnceCertificateStore()
        self.events = SharedEvents()
        self.deployer = RecordingDeployer()

    def bundle(
        self,
        name: str,
        weights: dict[str, float],
        evaluation: bool | dict[str, Any] = True,
    ) -> str:
        folder = self.artifact_dir / name
        folder.mkdir()
        (folder / "profile.json").write_text(json.dumps({"weights": weights}))
        if evaluation:
            data = evaluation if isinstance(evaluation, dict) else good_evaluation()
            (folder / "evaluation.json").write_text(json.dumps(data))
        return name


def good_evaluation() -> dict[str, Any]:
    truth = [1, 0, 1, 0, 1, 0, 1, 0]
    return {
        "y_true": truth,
        "y_pred": list(truth),
        "baseline_y_pred": list(truth),
        "groups": ["a", "a", "b", "b"] * 2,
    }
