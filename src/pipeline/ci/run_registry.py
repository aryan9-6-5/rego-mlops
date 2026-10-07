import asyncio
from datetime import datetime, timezone

from src.api.schemas.pipeline import (
    GateEvent,
    GateName,
    GateStatus,
    PipelineRun,
)

GATE_ORDER = [
    GateName.SYMBOLIC_CHECK,
    GateName.REG_ATTACK,
    GateName.FAIRNESS_CHECK,
    GateName.REGRESSION,
]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class RunRegistry:
    """Latest pipeline run plus live fan-out to WebSocket subscribers.

    In-process, single instance. Not persisted; finished gates are written to
    `pipeline_events` by the service.
    """

    def __init__(self) -> None:
        self._gates: dict[GateName, GateEvent] = {}
        self._model_version: str | None = None
        self._subscribers: set[asyncio.Queue[GateEvent]] = set()

    def begin(self, model_version: str) -> list[GateEvent]:
        self._model_version = model_version
        self._gates = {
            gate: GateEvent(
                gate=gate,
                status=GateStatus.QUEUED,
                model_version=model_version,
                timestamp=_now(),
            )
            for gate in GATE_ORDER
        }
        return list(self._gates.values())

    def publish(self, event: GateEvent) -> None:
        self._gates[event.gate] = event
        for queue in list(self._subscribers):
            queue.put_nowait(event)

    def snapshot(self) -> PipelineRun | None:
        if self._model_version is None:
            return None
        gates = [self._gates[g] for g in GATE_ORDER]
        statuses = {g.status for g in gates}
        if GateStatus.VIOLATION in statuses:
            status = GateStatus.VIOLATION
        elif statuses == {GateStatus.COMPLIANT}:
            status = GateStatus.COMPLIANT
        else:
            status = GateStatus.RUNNING
        return PipelineRun(
            model_version=self._model_version, status=status, gates=gates
        )

    def subscribe(self) -> asyncio.Queue[GateEvent]:
        queue: asyncio.Queue[GateEvent] = asyncio.Queue()
        self._subscribers.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue[GateEvent]) -> None:
        self._subscribers.discard(queue)
