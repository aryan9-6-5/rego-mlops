import pytest

from src.lib.z3_client import (
    Z3ClientError,
    counterexample,
    forced_zero_variables,
    prove,
)

NO_PIN = "(declare-const pin_code_weight Real)(assert (= pin_code_weight 0))"
MIN_INCOME = "(declare-const income_weight Real)(assert (> income_weight 0))"
CAP = "(declare-const income_weight Real)(assert (<= income_weight 0.5))"


def test_compliant_model_is_proved() -> None:
    result = prove(NO_PIN, {"income_weight": 0.6, "pin_code_weight": 0})
    assert result.compliant
    assert result.verdict == "UNSAT"
    assert result.counterexample is None


def test_violating_model_gets_counterexample() -> None:
    result = prove(NO_PIN, {"pin_code_weight": 0.3})
    assert not result.compliant
    assert result.verdict == "SAT"
    assert result.counterexample == {"pin_code_weight": "3/10"}


def test_missing_feature_counts_as_absent() -> None:
    assert prove(NO_PIN, {"income_weight": 0.9}).compliant
    assert not prove(MIN_INCOME, {}).compliant


def test_boundary_values_are_exact() -> None:
    assert prove(CAP, {"income_weight": 0.5}).compliant
    assert not prove(CAP, {"income_weight": 0.5000001}).compliant


def test_counterexample_helper() -> None:
    assert counterexample(NO_PIN, {"pin_code_weight": 0}) is None
    assert counterexample(NO_PIN, {"pin_code_weight": 1}) == {"pin_code_weight": "1"}


def test_bool_and_int_sorts() -> None:
    rule = "(declare-const uses_caste Bool)(assert (not uses_caste))"
    assert prove(rule, {"uses_caste": False}).compliant
    assert not prove(rule, {"uses_caste": True}).compliant


def test_unparseable_formula_raises() -> None:
    with pytest.raises(Z3ClientError):
        prove("(assert (= x", {})


def test_forced_zero_variables() -> None:
    assert forced_zero_variables(NO_PIN) == ["pin_code_weight"]
    assert forced_zero_variables(MIN_INCOME) == []


def test_client_recovers_after_a_parse_failure() -> None:
    with pytest.raises(Z3ClientError):
        prove("(assert (= y 0))", {})
    assert prove(NO_PIN, {"pin_code_weight": 0}).compliant
