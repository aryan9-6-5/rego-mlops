from typing import Any

import pytest

from src.api.schemas.pipeline import GateEvent, GateName, GateStatus
from src.lib.model_bundle import Submission
from src.pipeline.ci import regression, symbolic_check
from src.pipeline.ci.gate_runner import all_compliant, run_gates
from src.pipeline.ci.run_registry import RunRegistry
from src.pipeline.ci.service import run_submission
from src.pipeline.ci.tests.conftest import INCOME_CAP, NO_PIN, make_submission


class Collector:
    def __init__(self) -> None:
        self.events: list[GateEvent] = []

    async def __call__(self, event: GateEvent) -> None:
        self.events.append(event)

    def final(self) -> dict[GateName, GateStatus]:
        return {e.gate: e.status for e in self.events}


@pytest.mark.asyncio
async def test_compliant_model_passes_all_four_gates(
    good_submission: Submission,
) -> None:
    out = Collector()
    events = await run_gates([NO_PIN, INCOME_CAP], good_submission, out)
    assert all_compliant(events)
    assert [e.gate for e in events] == list(GateName)


@pytest.mark.asyncio
async def test_failure_halts_and_later_gates_never_run(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def must_not_run(_: Submission) -> Any:
        raise AssertionError("regression ran after a failed gate")

    monkeypatch.setattr(regression, "run", must_not_run)
    sub = make_submission({"pin_code_weight": 0.3})
    out = Collector()
    events = await run_gates([NO_PIN], sub, out)
    statuses = {e.gate: e.status for e in events}
    assert statuses[GateName.SYMBOLIC_CHECK] is GateStatus.VIOLATION
    assert statuses[GateName.REGRESSION] is GateStatus.SKIPPED
    assert not all_compliant(events)


@pytest.mark.asyncio
async def test_a_crashing_gate_counts_as_failure(
    monkeypatch: pytest.MonkeyPatch, good_submission: Submission
) -> None:
    def boom(*_: Any) -> Any:
        raise RuntimeError("z3 exploded")

    monkeypatch.setattr(symbolic_check, "check_rules", boom)
    events = await run_gates([NO_PIN], good_submission, Collector())
    assert events[0].status is GateStatus.VIOLATION
    assert "could not complete" in events[0].plain_english


class FakeGraph:
    def __init__(self, rows: list[dict[str, Any]] | None = None, fail: bool = False):
        self.rows = rows or []
        self.fail = fail

    def run_query(
        self, query: str, params: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        if self.fail:
            raise RuntimeError("neo4j down")
        return self.rows


class FakeStore:
    def __init__(self) -> None:
        self.recorded: list[GateEvent] = []

    def record(self, event: GateEvent) -> None:
        self.recorded.append(event)


RULE_ROW = {
    "version_id": NO_PIN.version_id,
    "rule_id": NO_PIN.rule_id,
    "formal_logic": NO_PIN.formal_logic,
    "section": "4.1",
    "description": NO_PIN.description,
}


@pytest.mark.asyncio
async def test_service_streams_events_and_audits_finished_gates(
    good_submission: Submission,
) -> None:
    registry, store = RunRegistry(), FakeStore()
    registry.begin("v1")
    queue = registry.subscribe()
    await run_submission(registry, store, FakeGraph([RULE_ROW]), good_submission)
    run = registry.snapshot()
    assert run is not None and run.status is GateStatus.COMPLIANT
    assert len(store.recorded) == 4
    assert queue.qsize() >= 8  # running + finished for each gate


@pytest.mark.asyncio
async def test_service_fails_the_run_when_rules_cannot_load(
    good_submission: Submission,
) -> None:
    registry, store = RunRegistry(), FakeStore()
    registry.begin("v1")
    await run_submission(registry, store, FakeGraph(fail=True), good_submission)
    run = registry.snapshot()
    assert run is not None and run.status is GateStatus.VIOLATION
    assert run.gates[0].status is GateStatus.VIOLATION
    assert run.gates[1].status is GateStatus.SKIPPED
