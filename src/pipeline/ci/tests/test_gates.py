from src.api.schemas.pipeline import GateName, GateStatus
from src.lib.regulation_graph import ActiveRule
from src.pipeline.ci import fairness_check, reg_attack, regression, symbolic_check
from src.pipeline.ci.submission import Submission
from src.pipeline.ci.tests.conftest import (
    INCOME_CAP,
    NO_PIN,
    make_evaluation,
    make_submission,
)

C, V = GateStatus.COMPLIANT, GateStatus.VIOLATION


# ---- symbolic_check -------------------------------------------------------


def test_symbolic_compliant(good_submission: Submission) -> None:
    result = symbolic_check.check_rules([NO_PIN, INCOME_CAP], good_submission)
    assert result.gate is GateName.SYMBOLIC_CHECK
    assert result.status is C
    assert result.rule_ids == ["RBI-4.1", "RBI-4.2"]
    assert result.violations == []


def test_symbolic_violation_names_rule_and_explains() -> None:
    sub = make_submission({"pin_code_weight": 0.3, "income_weight": 0.2})
    result = symbolic_check.check_rules([NO_PIN, INCOME_CAP], sub)
    assert result.status is V
    (violation,) = result.violations
    assert violation.rule_id == "RBI-4.1"
    assert "pin code" in violation.plain_english
    assert "geographic proxies" in violation.plain_english
    assert violation.counterexample == {"pin_code_weight": "3/10"}
    assert "3/10" not in violation.plain_english  # no raw Z3 in the explanation


def test_symbolic_fails_closed_without_rules() -> None:
    assert symbolic_check.check_rules([], make_submission({"a_weight": 1})).status is V


def test_symbolic_fails_closed_on_unverifiable_rule() -> None:
    broken = ActiveRule("v", "RBI-9", "(assert (= nope")
    result = symbolic_check.check_rules([broken], make_submission({"a_weight": 1}))
    assert result.status is V
    assert "could not be verified" in result.violations[0].plain_english


# ---- reg_attack -----------------------------------------------------------


def test_reg_attack_passes_for_robust_model(good_submission: Submission) -> None:
    assert reg_attack.check_rules([NO_PIN, INCOME_CAP], good_submission).status is C


def test_reg_attack_flags_knife_edge_compliance() -> None:
    sub = make_submission({"income_weight": 0.5})  # exactly on the 0.5 cap
    result = reg_attack.check_rules([INCOME_CAP], sub)
    assert result.status is V
    assert result.violations[0].rule_id == "RBI-4.2"


def test_reg_attack_leaves_existing_violations_to_symbolic_check() -> None:
    sub = make_submission({"pin_code_weight": 0.3})
    assert reg_attack.check_rules([NO_PIN], sub).status is C


# ---- fairness_check -------------------------------------------------------


def test_fairness_compliant() -> None:
    sub = make_submission({"a_weight": 1}, make_evaluation())
    assert fairness_check.run(sub).status is C


def test_fairness_violation_on_large_gap() -> None:
    preds = [1, 1, 0, 0] * 2  # group a always approved, group b never
    sub = make_submission({"a_weight": 1}, make_evaluation(y_pred=preds))
    result = fairness_check.run(sub)
    assert result.status is V
    assert "100.0 percentage points" in result.plain_english


def test_fairness_fails_closed_without_data_or_groups() -> None:
    assert fairness_check.run(make_submission({"a_weight": 1})).status is V
    one_group = make_evaluation(groups=["a"] * 8)
    assert fairness_check.run(make_submission({"a_weight": 1}, one_group)).status is V


# ---- regression -----------------------------------------------------------


def test_regression_compliant_when_f1_holds() -> None:
    sub = make_submission({"a_weight": 1}, make_evaluation())
    assert regression.run(sub).status is C


def test_regression_violation_when_f1_drops_over_five_percent() -> None:
    worse = [0, 0, 0, 0, 1, 0, 1, 0]  # misses two positives
    sub = make_submission({"a_weight": 1}, make_evaluation(y_pred=worse))
    result = regression.run(sub)
    assert result.status is V
    assert "fell" in result.plain_english


def test_regression_fails_closed_without_evaluation() -> None:
    assert regression.run(make_submission({"a_weight": 1})).status is V


def test_f1_known_value() -> None:
    assert regression.f1_score([1, 1, 0, 0], [1, 0, 1, 0]) == 0.5
