"""The workflow entry point: exit code 0 only when every gate passes."""

import json
import sys
import types
from pathlib import Path
from typing import Any

import pytest

from src.lib.tests.fake_supabase import FakeClient
from src.pipeline.ci import cli

NO_PIN_ROW = {
    "version_id": "RBI-4.1-x",
    "rule_id": "RBI-4.1",
    "formal_logic": "(declare-const pin_code_weight Real)(assert (= pin_code_weight 0))",
    "section": "4.1",
    "description": "No PIN codes.",
}
EVALUATION = {
    "y_true": [1, 0, 1, 0, 1, 0, 1, 0],
    "y_pred": [1, 0, 1, 0, 1, 0, 1, 0],
    "baseline_y_pred": [1, 0, 1, 0, 1, 0, 1, 0],
    "groups": ["a", "a", "b", "b"] * 2,
}


class Graph:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self.rows = rows

    def run_query(
        self, query: str, params: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        return self.rows


def bundle(base: Path, weights: dict[str, float]) -> None:
    (base / "m").mkdir()
    (base / "m" / "profile.json").write_text(json.dumps({"weights": weights}))
    (base / "m" / "evaluation.json").write_text(json.dumps(EVALUATION))


def run(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    rows: list[dict[str, Any]],
    supabase: FakeClient | None = None,
) -> int:
    graph_module = types.ModuleType("src.lib.neo4j_client")
    graph_module.neo4j_client = Graph(rows)  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "src.lib.neo4j_client", graph_module)
    monkeypatch.setenv("MODEL_ARTIFACT_DIR", str(tmp_path))
    monkeypatch.setattr(sys, "argv", ["cli", "--artifact", "m"])
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_KEY", raising=False)
    if supabase is not None:
        db_module = types.ModuleType("src.lib.supabase_client")
        db_module.supabase_client = types.SimpleNamespace(client=supabase)  # type: ignore[attr-defined]
        monkeypatch.setitem(sys.modules, "src.lib.supabase_client", db_module)
        monkeypatch.setenv("SUPABASE_URL", "http://db.test")
        monkeypatch.setenv("SUPABASE_SERVICE_KEY", "key")
    return cli.main()


def test_a_compliant_model_exits_zero_and_prints_every_gate(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    bundle(tmp_path, {"income_weight": 0.4})
    assert run(monkeypatch, tmp_path, [NO_PIN_ROW]) == 0
    out = capsys.readouterr().out
    assert out.count("compliant") >= 4
    assert "violation" not in out


def test_a_violating_model_exits_non_zero_so_the_workflow_fails(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    bundle(tmp_path, {"pin_code_weight": 0.3})
    assert run(monkeypatch, tmp_path, [NO_PIN_ROW]) == 1
    out = capsys.readouterr().out
    assert "symbolic_check: violation" in out
    assert "regression: skipped" in out


def test_no_active_rules_means_a_non_zero_exit(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    bundle(tmp_path, {"income_weight": 0.4})
    assert run(monkeypatch, tmp_path, []) == 1


def test_finished_gates_are_recorded_when_supabase_is_configured(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    bundle(tmp_path, {"income_weight": 0.4})
    db = FakeClient()
    assert run(monkeypatch, tmp_path, [NO_PIN_ROW], supabase=db) == 0
    inserted = [q.called("insert")[0][0] for q in db.queries]
    assert [row["gate_name"] for row in inserted] == [
        "symbolic_check", "reg_attack", "fairness_check", "regression",
    ]
    assert {row["stage"] for row in inserted} == {"ci"}
