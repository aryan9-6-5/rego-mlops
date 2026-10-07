import json
from pathlib import Path
from typing import Any

import httpx
import pytest

from src.lib.regulation_graph import ActiveRule
from src.pipeline.ct import trigger
from src.pipeline.ct.constraint_loss import prohibited_features, prohibited_indices
from src.pipeline.ct.drift_detector import detect_drift, mark_checked
from src.pipeline.ct.kaggle_runner import (
    CONFIG_PLACEHOLDER,
    KaggleError,
    KaggleRunner,
)
from src.pipeline.ct.trainer import TrainerError, run_training

NO_PIN = ActiveRule(
    "RBI-4.1-x",
    "RBI-4.1",
    "(declare-const pin_code_weight Real)(assert (= pin_code_weight 0))",
)
MIN_INCOME = ActiveRule(
    "RBI-4.2-x",
    "RBI-4.2",
    "(declare-const income_weight Real)(assert (> income_weight 0))",
)


class FakeGraph:
    def __init__(self, *responses: list[dict[str, Any]]) -> None:
        self.responses = list(responses)
        self.calls: list[dict[str, Any]] = []

    def run_query(
        self, query: str, params: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        self.calls.append(params or {})
        return self.responses.pop(0) if self.responses else []


# ---- drift_detector -------------------------------------------------------


def test_no_drift_when_nothing_new() -> None:
    graph = FakeGraph([{"last_checked": "2026-10-07T00:00:00+00:00"}], [])
    assert detect_drift(graph) is None
    assert graph.calls[1]["since"] == "2026-10-07T00:00:00+00:00"


def test_drift_reports_newest_version() -> None:
    graph = FakeGraph(
        [{"last_checked": None}],
        [
            {"version_id": "RBI-4.1-a", "activated_at": "2026-10-07T01:00:00"},
            {"version_id": "RBI-4.2-b", "activated_at": "2026-10-07T02:00:00"},
        ],
    )
    drift = detect_drift(graph)
    assert drift is not None
    assert drift.regulation_version == "RBI-4.2-b"
    assert drift.version_ids == ["RBI-4.1-a", "RBI-4.2-b"]
    assert graph.calls[1]["since"] == ""  # never checked: everything counts


def test_mark_checked_stores_timestamp() -> None:
    graph = FakeGraph()
    mark_checked(graph, "2026-10-07T02:00:00")
    assert graph.calls[0] == {"checked_up_to": "2026-10-07T02:00:00"}


# ---- trigger --------------------------------------------------------------


@pytest.mark.asyncio
async def test_dispatch_posts_workflow_inputs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GITHUB_TOKEN", "t")
    monkeypatch.setenv("GITHUB_REPOSITORY", "me/rego")
    seen: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["body"] = json.loads(request.content)
        return httpx.Response(204)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        await trigger.dispatch_ct_workflow("RBI-4.1-x", client)
    assert seen["url"].endswith("/repos/me/rego/actions/workflows/ct.yml/dispatches")
    expected = {"ref": "main", "inputs": {"regulation_version": "RBI-4.1-x"}}
    assert seen["body"] == expected


@pytest.mark.asyncio
async def test_dispatch_requires_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    with pytest.raises(trigger.TriggerError):
        await trigger.dispatch_ct_workflow("v")


@pytest.mark.asyncio
async def test_dispatch_surfaces_github_rejection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GITHUB_TOKEN", "t")
    monkeypatch.setenv("GITHUB_REPOSITORY", "me/rego")
    transport = httpx.MockTransport(lambda _: httpx.Response(404))
    async with httpx.AsyncClient(transport=transport) as client:
        with pytest.raises(trigger.TriggerError):
            await trigger.dispatch_ct_workflow("v", client)


# ---- constraint_loss ------------------------------------------------------


def test_prohibited_features_come_from_zero_forcing_rules() -> None:
    assert prohibited_features([NO_PIN, MIN_INCOME]) == ["pin_code"]


def test_prohibited_indices() -> None:
    assert prohibited_indices(["income", "pin_code", "age"], ["pin_code"]) == [1]


def test_constraint_penalty_with_torch() -> None:
    torch = pytest.importorskip("torch")
    from src.pipeline.ct.constraint_loss import constraint_penalty

    weights = torch.tensor([0.5, 0.2, 0.1])
    assert float(constraint_penalty(weights, [1], strength=10.0)) == pytest.approx(2.0)
    assert float(constraint_penalty(weights, [])) == 0.0


# ---- kaggle_runner --------------------------------------------------------


def make_runner(
    tmp_path: Path, outputs: list[str]
) -> tuple[KaggleRunner, list[list[str]]]:
    notebook = tmp_path / "nb.ipynb"
    notebook.write_text(f"CONFIG = r'''{CONFIG_PLACEHOLDER}'''")
    calls: list[list[str]] = []

    def run(args: list[str]) -> str:
        calls.append(args)
        return outputs.pop(0) if outputs else ""

    runner = KaggleRunner(
        notebook, "me", "me/data", run=run, poll_seconds=0, sleep=lambda _: None
    )
    return runner, calls


def test_push_embeds_config_and_sends_metadata(tmp_path: Path) -> None:
    pushed: dict[str, str] = {}
    runner, calls = make_runner(tmp_path, [])

    def capture(args: list[str]) -> str:
        folder = Path(args[args.index("-p") + 1])
        pushed["nb"] = (folder / "ct_retrain.ipynb").read_text()
        pushed["meta"] = (folder / "kernel-metadata.json").read_text()
        return ""

    runner._run = capture
    runner.push_notebook({"prohibited_features": ["pin_code"]})
    assert "pin_code" in pushed["nb"] and CONFIG_PLACEHOLDER not in pushed["nb"]
    meta = json.loads(pushed["meta"])
    assert meta["id"] == "me/rego-ct-retrain" and meta["enable_gpu"] is True
    assert meta["dataset_sources"] == ["me/data"]
    assert calls == []


def test_push_rejects_unsafe_config(tmp_path: Path) -> None:
    runner, _ = make_runner(tmp_path, [])
    with pytest.raises(KaggleError):
        runner.push_notebook({"x": "'''"})


def test_poll_waits_then_completes_or_fails(tmp_path: Path) -> None:
    runner, _ = make_runner(tmp_path, ["running", "running", "COMPLETE"])
    runner.poll_until_complete()
    failing, _ = make_runner(tmp_path, ["running", "ERROR"])
    with pytest.raises(KaggleError):
        failing.poll_until_complete()


# ---- trainer --------------------------------------------------------------


class FakeTrainer:
    def __init__(self, write_profile: bool = True) -> None:
        self.write_profile = write_profile
        self.config: dict[str, object] = {}

    def push_notebook(self, config: dict[str, object]) -> None:
        self.config = config

    def poll_until_complete(self) -> None:
        return None

    def pull_output(self, destination: Path) -> None:
        destination.mkdir(parents=True)
        if self.write_profile:
            (destination / "profile.json").write_text('{"weights": {"a_weight": 1}}')


class FakeTracker:
    def __init__(self) -> None:
        self.runs: list[dict[str, Any]] = []

    def log_run(self, **kwargs: Any) -> str:
        self.runs.append(kwargs)
        return "run-1"


RULE_ROWS = [
    {"version_id": r.version_id, "rule_id": r.rule_id, "formal_logic": r.formal_logic}
    for r in (NO_PIN, MIN_INCOME)
]


def test_training_registers_run_tagged_with_regulation_version(
    tmp_path: Path,
) -> None:
    trainer, tracker = FakeTrainer(), FakeTracker()
    graph = FakeGraph(RULE_ROWS)
    outcome = run_training(graph, trainer, tracker, "RBI-4.1-x", tmp_path)
    assert trainer.config["prohibited_features"] == ["pin_code"]
    assert outcome.model_version == "ct-RBI-4.1-x"
    assert tracker.runs[0]["regulation_version"] == "RBI-4.1-x"
    assert outcome.mlflow_run_id == "run-1"


def test_training_without_output_bundle_fails(tmp_path: Path) -> None:
    with pytest.raises(TrainerError):
        run_training(
            FakeGraph(RULE_ROWS), FakeTrainer(False), FakeTracker(), "v1", tmp_path
        )


@pytest.mark.parametrize("bad", ["../x", "a b", "", "x/y"])
def test_training_rejects_unsafe_version(tmp_path: Path, bad: str) -> None:
    with pytest.raises(TrainerError):
        run_training(FakeGraph(RULE_ROWS), FakeTrainer(), FakeTracker(), bad, tmp_path)


def test_training_needs_active_rules(tmp_path: Path) -> None:
    with pytest.raises(TrainerError):
        run_training(FakeGraph([]), FakeTrainer(), FakeTracker(), "v1", tmp_path)


# ---- the trained bundle is kept where the API can read it ---------------------


class FakeUploader:
    def __init__(self) -> None:
        self.uploaded: list[tuple[str, bool]] = []

    def upload(self, name: str, directory: Path) -> None:
        self.uploaded.append((name, (directory / "profile.json").exists()))


def test_training_uploads_the_pulled_bundle_before_registering_it(tmp_path: Path) -> None:
    uploader = FakeUploader()
    run_training(
        FakeGraph(RULE_ROWS), FakeTrainer(), FakeTracker(), "RBI-4.1-x", tmp_path, uploader
    )
    assert uploader.uploaded == [("ct-RBI-4.1-x", True)]


def test_nothing_is_uploaded_when_training_produced_no_bundle(tmp_path: Path) -> None:
    uploader = FakeUploader()
    with pytest.raises(TrainerError):
        run_training(
            FakeGraph(RULE_ROWS), FakeTrainer(False), FakeTracker(), "v1", tmp_path, uploader
        )
    assert uploader.uploaded == []
