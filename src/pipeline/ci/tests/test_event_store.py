"""`pipeline_events` holds model-level results only, never applicant data."""

from typing import Any

from src.api.schemas.pipeline import GateEvent, GateName, GateStatus, Violation
from src.pipeline.ci.event_store import SupabaseEventStore

TABLE_COLUMNS = {
    "stage",
    "gate_name",
    "status",
    "model_version",
    "rule_ids",
    "duration_ms",
    "plain_english_result",
}


class FakeClient:
    def __init__(self) -> None:
        self.inserted: dict[str, Any] = {}

    def table(self, name: str) -> "FakeClient":
        assert name == "pipeline_events"
        return self

    def insert(self, row: dict[str, Any]) -> "FakeClient":
        self.inserted = row
        return self

    def execute(self) -> None:
        return None


def test_only_the_model_level_columns_are_written_and_counterexamples_are_not() -> None:
    client = FakeClient()
    event = GateEvent(
        gate=GateName.SYMBOLIC_CHECK,
        status=GateStatus.VIOLATION,
        model_version="v1",
        timestamp="2026-10-07T00:00:00Z",
        rule_ids=["RBI-4.1"],
        duration_ms=12.7,
        plain_english="The model breaks 1 of 1 active rules.",
        violations=[
            Violation(
                rule_id="RBI-4.1",
                plain_english="x",
                counterexample={"pin_code_weight": "3/10"},
            )
        ],
    )
    SupabaseEventStore(client).record(event)
    assert set(client.inserted) == TABLE_COLUMNS
    assert "3/10" not in str(client.inserted)
