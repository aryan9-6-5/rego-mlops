"""A chainable stand-in for the supabase-py query builder, for store tests."""

from typing import Any


class Result:
    def __init__(self, data: list[dict[str, Any]]) -> None:
        self.data = data


class FakeQuery:
    """Records the calls made and returns canned data from `execute()`."""

    def __init__(self, client: "FakeClient", table: str) -> None:
        self.client = client
        self.table_name = table
        self.calls: list[tuple[str, tuple[Any, ...], dict[str, Any]]] = []

    def __getattr__(self, name: str) -> Any:
        def record(*args: Any, **kwargs: Any) -> "FakeQuery":
            self.calls.append((name, args, kwargs))
            return self

        return record

    def execute(self) -> Result:
        self.client.queries.append(self)
        if self.client.error is not None:
            raise self.client.error
        return Result(self.client.data)

    def called(self, name: str) -> list[tuple[Any, ...]]:
        return [args for (n, args, _kw) in self.calls if n == name]


class FakeClient:
    def __init__(self, data: list[dict[str, Any]] | None = None) -> None:
        self.data = data if data is not None else []
        self.error: Exception | None = None
        self.queries: list[FakeQuery] = []

    def table(self, name: str) -> FakeQuery:
        return FakeQuery(self, name)

    @property
    def last(self) -> FakeQuery:
        return self.queries[-1]
