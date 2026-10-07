from typing import Any, Protocol

from src.api.schemas.pipeline import GateEvent

TABLE = "pipeline_events"
STAGE = "ci"


class PipelineEventStore(Protocol):
    def record(self, event: GateEvent) -> None: ...


class SupabaseEventStore:
    """Audit log of finished gates in `pipeline_events`.

    Stores the plain-English result only. Counterexamples are never persisted.
    """

    def __init__(self, client: Any) -> None:
        self._client = client

    def record(self, event: GateEvent) -> None:
        self._client.table(TABLE).insert(
            {
                "stage": STAGE,
                "gate_name": event.gate.value,
                "status": event.status.value,
                "model_version": event.model_version,
                "rule_ids": event.rule_ids,
                "duration_ms": int(event.duration_ms),
                "plain_english_result": event.plain_english,
                "bundle_hash": event.bundle_hash,
            }
        ).execute()
