"""The two workflow steps in ct.yml: drift detection and training."""

import sys
import types
from pathlib import Path
from typing import Any

import pytest

from src.pipeline.ct import drift_detector, trainer

RULE_ROW = {
    "version_id": "RBI-4.1-x",
    "rule_id": "RBI-4.1",
    "formal_logic": "(declare-const pin_code_weight Real)(assert (= pin_code_weight 0))",
}


class Graph:
    """Answers the drift queries from a script and records every call."""

    def __init__(self, *responses: list[dict[str, Any]]) -> None:
        self.responses = list(responses)
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def run_query(
        self, query: str, params: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        self.calls.append((query, params or {}))
        return self.responses.pop(0) if self.responses else []


def install(monkeypatch: pytest.MonkeyPatch, graph: Graph) -> None:
    module = types.ModuleType("src.lib.neo4j_client")
    module.neo4j_client = graph  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "src.lib.neo4j_client", module)


def test_drift_step_writes_the_new_version_for_the_next_job(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    graph = Graph(
        [{"last_checked": None}],
        [{"version_id": "RBI-4.1-x", "activated_at": "2026-10-07T01:00:00+00:00"}],
    )
    install(monkeypatch, graph)
    output = tmp_path / "out.txt"
    monkeypatch.setenv("GITHUB_OUTPUT", str(output))
    drift_detector.main()
    assert output.read_text() == (
        "regulation_version=RBI-4.1-x\ndetected_at=2026-10-07T01:00:00+00:00\n"
    )


def test_drift_step_writes_empty_values_when_nothing_changed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    install(monkeypatch, Graph([{"last_checked": "2026-10-07T00:00:00"}], []))
    output = tmp_path / "out.txt"
    monkeypatch.setenv("GITHUB_OUTPUT", str(output))
    drift_detector.main()
    assert output.read_text() == "regulation_version=\ndetected_at=\n"


class FakeKaggle:
    def __init__(self, *_: Any) -> None:
        self.config: dict[str, object] = {}

    def push_notebook(self, config: dict[str, object]) -> None:
        self.config = config

    def poll_until_complete(self) -> None:
        return None

    def pull_output(self, destination: Path) -> None:
        destination.mkdir(parents=True)
        (destination / "profile.json").write_text('{"weights": {"a_weight": 1}}')


class FakeTracker:
    def log_run(self, **_: Any) -> str:
        return "run-1"


def test_training_step_trains_marks_drift_handled_and_reports_the_model(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    graph = Graph([RULE_ROW])
    install(monkeypatch, graph)
    tracker_module = types.ModuleType("src.lib.mlflow_client")
    tracker_module.MlflowTracker = FakeTracker  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "src.lib.mlflow_client", tracker_module)
    monkeypatch.setattr(trainer, "KaggleRunner", FakeKaggle)
    monkeypatch.setenv("MODEL_ARTIFACT_DIR", str(tmp_path / "models"))
    output = tmp_path / "out.txt"
    monkeypatch.setenv("GITHUB_OUTPUT", str(output))
    monkeypatch.setattr(
        sys,
        "argv",
        ["trainer", "--regulation-version", "RBI-4.1-x", "--detected-at", "2026-10-07T01:00:00"],
    )
    trainer.main()
    assert output.read_text() == "model_version=ct-RBI-4.1-x\n"
    assert (tmp_path / "models" / "ct-RBI-4.1-x" / "profile.json").exists()
    marked = [params for _q, params in graph.calls if "checked_up_to" in params]
    assert marked == [{"checked_up_to": "2026-10-07T01:00:00"}]


def test_a_failed_training_run_does_not_mark_drift_as_handled(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """If training fails the change must be picked up again on the next run."""
    graph = Graph([RULE_ROW])
    install(monkeypatch, graph)

    class Broken(FakeKaggle):
        def poll_until_complete(self) -> None:
            raise RuntimeError("kaggle failed")

    monkeypatch.setattr(trainer, "KaggleRunner", Broken)
    tracker_module = types.ModuleType("src.lib.mlflow_client")
    tracker_module.MlflowTracker = FakeTracker  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "src.lib.mlflow_client", tracker_module)
    monkeypatch.setenv("MODEL_ARTIFACT_DIR", str(tmp_path))
    monkeypatch.setattr(
        sys, "argv", ["trainer", "--regulation-version", "RBI-4.1-x", "--detected-at", "t"]
    )
    with pytest.raises(RuntimeError):
        trainer.main()
    assert not [p for _q, p in graph.calls if "checked_up_to" in p]
