from typing import Any, Protocol

TABLE = "regulations"


class RegulationStore(Protocol):
    def insert(self, row: dict[str, Any]) -> dict[str, Any]: ...
    def get(self, regulation_id: str) -> dict[str, Any] | None: ...
    def update(self, regulation_id: str, fields: dict[str, Any]) -> dict[str, Any]: ...
    def list_by_status(self, statuses: list[str]) -> list[dict[str, Any]]: ...


class SupabaseRegulationStore:
    """`regulations` table access via the backend-only service-key client."""

    def __init__(self, client: Any) -> None:
        self._client = client

    def _table(self) -> Any:
        return self._client.table(TABLE)

    def insert(self, row: dict[str, Any]) -> dict[str, Any]:
        data: Any = self._table().insert(row).execute().data
        return dict(data[0])

    def get(self, regulation_id: str) -> dict[str, Any] | None:
        data: Any = self._table().select("*").eq("id", regulation_id).execute().data
        return dict(data[0]) if data else None

    def update(self, regulation_id: str, fields: dict[str, Any]) -> dict[str, Any]:
        data: Any = self._table().update(fields).eq("id", regulation_id).execute().data
        return dict(data[0])

    def list_by_status(self, statuses: list[str]) -> list[dict[str, Any]]:
        data: Any = (
            self._table()
            .select("*")
            .in_("status", statuses)
            .order("created_at", desc=True)
            .execute()
            .data
        )
        return [dict(r) for r in data]
