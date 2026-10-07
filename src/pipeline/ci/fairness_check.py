import time
from collections import defaultdict

from src.api.schemas.pipeline import GateName, GateResult, GateStatus
from src.pipeline.ci.submission import Submission

# Largest allowed gap in positive-prediction rate between any two groups.
MAX_DEMOGRAPHIC_PARITY_GAP = 0.10


def _result(
    status: GateStatus, message: str, started: float
) -> GateResult:
    return GateResult(
        gate=GateName.FAIRNESS_CHECK,
        status=status,
        duration_ms=(time.perf_counter() - started) * 1000,
        plain_english=message,
    )


def run(submission: Submission) -> GateResult:
    """Demographic parity: approval rates must be similar across groups.

    Pure-Python metric. Fails closed when there is no evaluation data or fewer
    than two groups, since parity cannot then be shown.
    """
    started = time.perf_counter()
    evaluation = submission.evaluation
    if evaluation is None:
        return _result(
            GateStatus.VIOLATION,
            "No evaluation data was supplied, so fairness cannot be checked.",
            started,
        )
    positives: dict[str, int] = defaultdict(int)
    totals: dict[str, int] = defaultdict(int)
    for group, prediction in zip(evaluation.groups, evaluation.y_pred):
        totals[group] += 1
        positives[group] += prediction
    if len(totals) < 2:
        return _result(
            GateStatus.VIOLATION,
            "Fewer than two groups were evaluated, so fairness cannot be checked.",
            started,
        )
    rates = {g: positives[g] / totals[g] for g in totals}
    gap = max(rates.values()) - min(rates.values())
    limit = MAX_DEMOGRAPHIC_PARITY_GAP * 100
    if gap > MAX_DEMOGRAPHIC_PARITY_GAP:
        return _result(
            GateStatus.VIOLATION,
            f"Approval rates differ by {gap * 100:.1f} percentage points between "
            f"groups. The limit is {limit:.0f}.",
            started,
        )
    return _result(
        GateStatus.COMPLIANT,
        f"Approval rates differ by {gap * 100:.1f} percentage points between "
        f"groups, within the {limit:.0f} point limit.",
        started,
    )
