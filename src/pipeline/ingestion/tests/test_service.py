import json
from typing import Any

import pytest

from src.api.schemas.regulation import RegulationStatus as S
from src.pipeline.ingestion.approver import InvalidStateTransitionError
from src.pipeline.ingestion.service import (
    approve_regulation,
    ingest_regulation,
    reject_regulation,
)

GOOD_FORMULA = "(declare-const pin_code_weight Real)(assert (= pin_code_weight 0))"


def reply(*formulas: str) -> str:
    return json.dumps(
        {
            "rules": [
                {"section": "4.1", "title": "t", "description": "d", "formal_logic": f}
                for f in formulas
            ]
        }
    )


class FakeLLM:
    def __init__(self, text: str) -> None:
        self.text = text

    async def complete(self, system: str, user: str) -> str:
        return self.text


class FakeStore:
    def __init__(self) -> None:
        self.rows: dict[str, dict[str, Any]] = {}

    def insert(self, row: dict[str, Any]) -> dict[str, Any]:
        row = {**row, "id": f"id{len(self.rows) + 1}"}
        self.rows[row["id"]] = row
        return dict(row)

    def get(self, regulation_id: str) -> dict[str, Any] | None:
        row = self.rows.get(regulation_id)
        return dict(row) if row else None

    def update(self, regulation_id: str, fields: dict[str, Any]) -> dict[str, Any]:
        self.rows[regulation_id].update(fields)
        return dict(self.rows[regulation_id])

    def list_by_status(self, statuses: list[str]) -> list[dict[str, Any]]:
        return [r for r in self.rows.values() if r["status"] in statuses]


class FakeGraph:
    def __init__(self, fail: bool = False) -> None:
        self.fail = fail
        self.writes: list[dict[str, Any]] = []

    def run_query(
        self, query: str, params: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        if self.fail:
            raise RuntimeError("neo4j down")
        self.writes.append(params or {})
        return [{"version_id": (params or {})["version_id"]}]


async def ingest(store: FakeStore, *formulas: str) -> list[dict[str, Any]]:
    return await ingest_regulation(
        store,
        FakeLLM(reply(*formulas)),
        text="src",
        section="4.1",
        jurisdiction="India",
        job_id="j1",
    )


@pytest.mark.asyncio
async def test_valid_rule_lands_in_approval_queue_not_active() -> None:
    store = FakeStore()
    (row,) = await ingest(store, GOOD_FORMULA)
    assert row["status"] == S.PENDING_APPROVAL.value
    assert row["rule_id"] == "RBI-4.1"


@pytest.mark.asyncio
async def test_malformed_rule_is_z3_rejected_with_reason() -> None:
    store = FakeStore()
    good, bad = await ingest(store, GOOD_FORMULA, "(assert true)")
    assert good["status"] == S.PENDING_APPROVAL.value
    assert bad["status"] == S.Z3_REJECTED.value
    assert bad["validation_message"]
    assert bad["rule_id"] == "RBI-4.1-2"


@pytest.mark.asyncio
async def test_approve_writes_graph_and_activates() -> None:
    store, graph = FakeStore(), FakeGraph()
    (row,) = await ingest(store, GOOD_FORMULA)
    done = approve_regulation(store, graph, row["id"], "user-1")
    assert done["status"] == S.ACTIVE.value
    assert done["approved_by"] == "user-1"
    assert graph.writes[0]["version_id"].startswith("RBI-4.1-")


@pytest.mark.asyncio
async def test_cannot_approve_z3_rejected_rule() -> None:
    store, graph = FakeStore(), FakeGraph()
    (row,) = await ingest(store, "(assert true)")
    with pytest.raises(InvalidStateTransitionError):
        approve_regulation(store, graph, row["id"], "user-1")
    assert graph.writes == []


@pytest.mark.asyncio
async def test_reject_never_touches_graph() -> None:
    store = FakeStore()
    (row,) = await ingest(store, GOOD_FORMULA)
    done = reject_regulation(store, row["id"], "wrong intent")
    assert done["status"] == S.REJECTED.value


@pytest.mark.asyncio
async def test_graph_failure_leaves_rule_approved_and_retryable() -> None:
    store = FakeStore()
    (row,) = await ingest(store, GOOD_FORMULA)
    with pytest.raises(RuntimeError):
        approve_regulation(store, FakeGraph(fail=True), row["id"], "u")
    assert store.rows[row["id"]]["status"] == S.APPROVED.value
    done = approve_regulation(store, FakeGraph(), row["id"], "u")
    assert done["status"] == S.ACTIVE.value
