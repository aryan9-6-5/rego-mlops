import time

from src.api.schemas.pipeline import GateName, GateResult, GateStatus
from src.lib.model_bundle import Submission

# The new model fails if its F1 is more than 5% below the baseline's (relative).
MAX_RELATIVE_F1_DROP = 0.05


def f1_score(y_true: list[int], y_pred: list[int]) -> float:
    tp = sum(1 for t, p in zip(y_true, y_pred) if t == 1 and p == 1)
    fp = sum(1 for t, p in zip(y_true, y_pred) if t == 0 and p == 1)
    fn = sum(1 for t, p in zip(y_true, y_pred) if t == 1 and p == 0)
    denominator = 2 * tp + fp + fn
    return 2 * tp / denominator if denominator else 0.0


def run(submission: Submission) -> GateResult:
    """Performance regression: new model vs baseline on the held-out set."""
    started = time.perf_counter()
    evaluation = submission.evaluation
    if evaluation is None or not evaluation.y_true:
        status = GateStatus.VIOLATION
        message = "No evaluation data was supplied, so accuracy cannot be compared."
    else:
        new_f1 = f1_score(evaluation.y_true, evaluation.y_pred)
        baseline_f1 = f1_score(evaluation.y_true, evaluation.baseline_y_pred)
        if new_f1 >= baseline_f1 * (1 - MAX_RELATIVE_F1_DROP):
            status = GateStatus.COMPLIANT
            message = (
                f"F1 is {new_f1:.3f} against a baseline of {baseline_f1:.3f}, "
                "within the 5% allowed drop."
            )
        else:
            status = GateStatus.VIOLATION
            message = (
                f"F1 fell to {new_f1:.3f} from a baseline of {baseline_f1:.3f}, "
                "more than the 5% allowed drop."
            )
    return GateResult(
        gate=GateName.REGRESSION,
        status=status,
        duration_ms=(time.perf_counter() - started) * 1000,
        plain_english=message,
    )
