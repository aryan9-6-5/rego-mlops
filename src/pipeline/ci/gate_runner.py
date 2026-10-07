import asyncio
import logging
from collections.abc import Awaitable, Callable, Sequence
from datetime import datetime, timezone

from src.api.schemas.pipeline import (
    GateEvent,
    GateName,
    GateResult,
    GateStatus,
)
from src.lib.model_bundle import Submission
from src.lib.regulation_graph import ActiveRule
from src.pipeline.ci import fairness_check, reg_attack, regression, symbolic_check
from src.pipeline.ci.run_registry import GATE_ORDER

logger = logging.getLogger(__name__)

Publish = Callable[[GateEvent], Awaitable[None]]


def _event(
    submission: Submission, gate: GateName, status: GateStatus, **fields: object
) -> GateEvent:
    return GateEvent(
        gate=gate,
        status=status,
        model_version=submission.model_version,
        timestamp=datetime.now(timezone.utc).isoformat(),
        **fields,  # type: ignore[arg-type]
    )


def _gate_functions(
    rules: Sequence[ActiveRule], submission: Submission
) -> dict[GateName, Callable[[], GateResult]]:
    return {
        GateName.SYMBOLIC_CHECK: lambda: symbolic_check.check_rules(
            rules, submission
        ),
        GateName.REG_ATTACK: lambda: reg_attack.check_rules(rules, submission),
        GateName.FAIRNESS_CHECK: lambda: fairness_check.run(submission),
        GateName.REGRESSION: lambda: regression.run(submission),
    }


async def run_gates(
    rules: Sequence[ActiveRule], submission: Submission, publish: Publish
) -> list[GateEvent]:
    """Run symbolic -> reg_attack -> fairness -> regression, in that order.

    The first failure halts the run: later gates are marked skipped and never
    execute. A gate that crashes counts as a failure. There is no override
.
    """
    functions = _gate_functions(rules, submission)
    events: list[GateEvent] = []
    for index, gate in enumerate(GATE_ORDER):
        await publish(_event(submission, gate, GateStatus.RUNNING))
        try:
            result = await asyncio.to_thread(functions[gate])
        except Exception:
            logger.error(
                "Gate crashed gate=%s model=%s", gate.value, submission.model_version
            )
            result = GateResult(
                gate=gate,
                status=GateStatus.VIOLATION,
                plain_english=(
                    "The check could not complete, so the model was not certified."
                ),
            )
        details = result.model_dump(exclude={"gate", "status"})
        event = _event(submission, gate, result.status, **details)
        events.append(event)
        await publish(event)
        if result.status is not GateStatus.COMPLIANT:
            for skipped in GATE_ORDER[index + 1 :]:
                skip = _event(
                    submission,
                    skipped,
                    GateStatus.SKIPPED,
                    plain_english=f"Not run because {gate.value} failed.",
                )
                events.append(skip)
                await publish(skip)
            break
    return events


async def fail_run(submission: Submission, publish: Publish, message: str) -> None:
    """Fail the whole run when it cannot start (e.g. rules cannot be loaded)."""
    first, *rest = GATE_ORDER
    await publish(
        _event(submission, first, GateStatus.VIOLATION, plain_english=message)
    )
    for gate in rest:
        await publish(
            _event(
                submission,
                gate,
                GateStatus.SKIPPED,
                plain_english=f"Not run because {first.value} failed.",
            )
        )


def all_compliant(events: Sequence[GateEvent]) -> bool:
    return len(events) == len(GATE_ORDER) and all(
        e.status is GateStatus.COMPLIANT for e in events
    )
