import pytest

from src.lib.regulation_graph import ActiveRule
from src.pipeline.ci.submission import Evaluation, Submission

NO_PIN = ActiveRule(
    version_id="RBI-4.1-20261007T000000Z",
    rule_id="RBI-4.1",
    section="4.1",
    description="Credit models must not use geographic proxies such as PIN codes.",
    formal_logic="(declare-const pin_code_weight Real)(assert (= pin_code_weight 0))",
)
INCOME_CAP = ActiveRule(
    version_id="RBI-4.2-20261007T000000Z",
    rule_id="RBI-4.2",
    formal_logic="(declare-const income_weight Real)(assert (<= income_weight 0.5))",
)


def make_submission(
    weights: dict[str, float | bool], evaluation: Evaluation | None = None
) -> Submission:
    return Submission("v1", weights, evaluation)


def make_evaluation(
    y_pred: list[int] | None = None,
    baseline: list[int] | None = None,
    groups: list[str] | None = None,
) -> Evaluation:
    y_true = [1, 0, 1, 0, 1, 0, 1, 0]
    return Evaluation(
        y_true=y_true,
        y_pred=y_pred if y_pred is not None else list(y_true),
        baseline_y_pred=baseline if baseline is not None else list(y_true),
        groups=groups if groups is not None else ["a", "a", "b", "b"] * 2,
    )


@pytest.fixture
def good_submission() -> Submission:
    return make_submission(
        {"income_weight": 0.4, "pin_code_weight": 0.0}, make_evaluation()
    )
