from typing import Any

import pytest

from src.pipeline.cd.lineage import (
    LineageError,
    get_lineage,
    list_lineages,
    record_lineage,
)

REG = {
    "version_id": "RBI-4.1-20261007T000000Z",
    "rule_id": "RBI-4.1",
    "section": "4.1",
    "status": "superseded",
    "activated_at": "2026-10-07T00:00:00+00:00",
    "superseded_at": "2026-10-08T00:00:00+00:00",
    "certified_at": "2026-10-07T01:00:00+00:00",
}


class FakeGraph:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self.rows = rows
        self.calls: list[dict[str, Any]] = []

    def run_query(
        self, query: str, params: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        self.calls.append(params or {})
        return self.rows


def test_record_lineage_links_active_regulations() -> None:
    graph = FakeGraph([{"version_ids": ["RBI-4.1-x"]}])
    assert record_lineage(graph, "v2.1.4") == ["RBI-4.1-x"]
    assert graph.calls[0]["model_version"] == "v2.1.4"
    assert graph.calls[0]["active"] == "active"


def test_record_lineage_refuses_when_no_active_rules() -> None:
    with pytest.raises(LineageError):
        record_lineage(FakeGraph([{"version_ids": []}]), "v2.1.4")


def test_get_lineage_keeps_superseded_history() -> None:
    graph = FakeGraph(
        [
            {
                "model_version": "v2.1.4",
                "created_at": "2026-10-07T01:00:00+00:00",
                "regulation_versions": [REG],
            }
        ]
    )
    lineage = get_lineage(graph, "v2.1.4")
    assert lineage is not None
    assert lineage.regulation_versions[0].status == "superseded"
    assert lineage.regulation_versions[0].version_id == REG["version_id"]


def test_get_lineage_unknown_model_is_none() -> None:
    assert get_lineage(FakeGraph([]), "nope") is None


def test_list_lineages_returns_every_model() -> None:
    rows: list[dict[str, Any]] = [
        {"model_version": "v2", "created_at": None, "regulation_versions": []},
        {"model_version": "v1", "created_at": None, "regulation_versions": [REG]},
    ]
    assert [m.model_version for m in list_lineages(FakeGraph(rows))] == ["v2", "v1"]
