import json
from pathlib import Path
from typing import Any

from src.features.model_diff import compare, diff_weights
from src.lib.regulation_graph import ActiveRule, recent_regulation_versions

NO_PIN = ActiveRule(
    "RBI-4.1-x",
    "RBI-4.1",
    "(declare-const pin_code_weight Real)(assert (= pin_code_weight 0))",
)


def changes(before: dict[str, float], after: dict[str, float]) -> dict[str, Any]:
    diff = diff_weights(before, after, [NO_PIN], "a", "b")
    return {c.feature: c for c in diff.changes}


def test_added_removed_and_changed_features() -> None:
    result = changes(
        {"income_weight": 0.4, "age_weight": 0.2},
        {"income_weight": 0.5, "credit_weight": 0.3},
    )
    assert result["income"].kind == "changed"
    assert (result["income"].before, result["income"].after) == (0.4, 0.5)
    assert result["age"].kind == "removed"
    assert result["credit"].kind == "added"


def test_unchanged_and_unused_features_are_not_listed() -> None:
    before = {"income_weight": 0.4, "pin_code_weight": 0.0}
    assert changes(before, {"income_weight": 0.4}) == {}


def test_a_feature_in_an_active_rule_is_flagged_as_compliance_impacting() -> None:
    result = changes(
        {"income_weight": 0.4}, {"income_weight": 0.4, "pin_code_weight": 0.3}
    )
    assert result["pin_code"].kind == "added"
    assert result["pin_code"].affects_rules == ["RBI-4.1"]


def test_an_unrelated_change_affects_no_rule() -> None:
    assert changes({}, {"income_weight": 0.4})["income"].affects_rules == []


class FakeGraph:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self.rows = rows
        self.params: dict[str, Any] = {}

    def run_query(
        self, query: str, params: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        self.params = params or {}
        return self.rows


def test_compare_reads_both_bundles(tmp_path: Path) -> None:
    bundles = {"v1": {"income_weight": 0.4}, "v2": {"pin_code_weight": 0.3}}
    for name, weights in bundles.items():
        (tmp_path / name).mkdir()
        (tmp_path / name / "profile.json").write_text(json.dumps({"weights": weights}))
    rule_row = {
        "version_id": NO_PIN.version_id,
        "rule_id": NO_PIN.rule_id,
        "formal_logic": NO_PIN.formal_logic,
    }
    diff = compare(FakeGraph([rule_row]), tmp_path, "v1", "v2")
    kinds = {c.feature: (c.kind, c.affects_rules) for c in diff.changes}
    assert kinds == {"income": ("removed", []), "pin_code": ("added", ["RBI-4.1"])}


def test_recent_regulation_versions_passes_the_limit() -> None:
    graph = FakeGraph([{"version_id": "v"}])
    assert recent_regulation_versions(graph, 5) == [{"version_id": "v"}]
    assert graph.params == {"limit": 5}
