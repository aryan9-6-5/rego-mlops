"""In-memory stand-ins for Supabase, Neo4j, the LLM and Railway, so the API can be
exercised end to end without any network."""

import json
from pathlib import Path
from typing import Any

TOKENS: dict[str, tuple[str, str | None]] = {
    "co-token": ("user-co", "compliance_officer"),
    "co2-token": ("user-co-2", "compliance_officer"),
    "mle-token": ("user-mle", "ml_engineer"),
    "cto-token": ("user-cto", "cto"),
    "norole-token": ("user-none", None),
}
ROLES = ("compliance_officer", "ml_engineer", "cto")
ROLE_TOKEN = {
    "compliance_officer": "co-token",
    "ml_engineer": "mle-token",
    "cto": "cto-token",
}


class _Result:
    def __init__(self, data: list[dict[str, Any]]) -> None:
        self.data = data


class _UsersTable:
    def __init__(self) -> None:
        self._user_id = ""

    def select(self, *_: Any) -> "_UsersTable":
        return self

    def eq(self, _column: str, value: str) -> "_UsersTable":
        self._user_id = value
        return self

    def execute(self) -> _Result:
        for user_id, role in TOKENS.values():
            if user_id == self._user_id and role is not None:
                return _Result([{"role": role}])
        return _Result([])


class _FakeClient:
    def table(self, _name: str) -> _UsersTable:
        return _UsersTable()


class FakeSupabase:
    """Replaces `src.lib.supabase_client.supabase_client`."""

    def __init__(self) -> None:
        self.client = _FakeClient()

    def verify_token(self, token: str) -> dict[str, Any]:
        if token == "boom-token":
            raise RuntimeError("internal supabase detail that must not leak")
        if token not in TOKENS:
            raise ValueError("Invalid token")
        return {"id": TOKENS[token][0], "email": f"{token}@example.test"}


class FakeGraph:
    def run_query(
        self, query: str, params: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        return []


class FakeRegulationStore:
    def __init__(self) -> None:
        self.rows: dict[str, dict[str, Any]] = {}

    def insert(self, row: dict[str, Any]) -> dict[str, Any]:
        stored = {**row, "id": f"reg-{len(self.rows) + 1}"}
        self.rows[stored["id"]] = stored
        return dict(stored)

    def get(self, regulation_id: str) -> dict[str, Any] | None:
        return self.rows.get(regulation_id)

    def update(self, regulation_id: str, fields: dict[str, Any]) -> dict[str, Any]:
        self.rows[regulation_id].update(fields)
        return dict(self.rows[regulation_id])

    def list_by_status(self, statuses: list[str]) -> list[dict[str, Any]]:
        return [r for r in self.rows.values() if r["status"] in statuses]

    def list_active_for_rule(self, rule_id: str) -> list[dict[str, Any]]:
        return []


class FakeLLM:
    async def complete(self, system: str, user: str) -> str:
        return json.dumps(
            {
                "rules": [
                    {
                        "section": "4.1",
                        "title": "t",
                        "description": "d",
                        "formal_logic": (
                            "(declare-const pin_code_weight Real)"
                            "(assert (= pin_code_weight 0))"
                        ),
                    }
                ]
            }
        )


class FakeCertStore:
    def insert(self, row: dict[str, Any]) -> dict[str, Any]:
        return {**row, "created_at": None}

    def get(self, certificate_id: str) -> dict[str, Any] | None:
        return None

    def list_latest(self) -> list[dict[str, Any]]:
        return []


class FakeEventStore:
    def record(self, event: Any) -> None:
        return None


class FakeCIReader:
    def latest_gate_statuses(self, model_version: str) -> dict[str, str]:
        return {}


class FakeDeployer:
    async def deploy_canary(self, model_version: str, percent: int) -> None:
        return None

    async def promote(self, model_version: str) -> None:
        return None

    async def rollback(self) -> None:
        return None


def empty_dir(tmp_path: Path) -> Path:
    return tmp_path
