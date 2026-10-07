"""When Z3 cannot give a clear YES, the answer must be NO."""

from typing import Any

import pytest
import z3

from src.lib.z3_client import (
    Z3ClientError,
    forced_zero_variables,
    prove,
    rule_variables,
)

NO_PIN = "(declare-const pin_code_weight Real)(assert (= pin_code_weight 0))"


class UnknownSolver:
    """A solver that gives up."""

    def __init__(self, *_: Any, **__: Any) -> None:
        return None

    def set(self, *_: Any) -> None:
        return None

    def add(self, *_: Any) -> None:
        return None

    def check(self) -> Any:
        return z3.unknown


class CrashingSolver(UnknownSolver):
    def check(self) -> Any:
        raise z3.Z3Exception("solver crashed")


def test_an_unknown_answer_is_not_compliant_and_has_no_counterexample(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("src.lib.z3_client.z3.Solver", UnknownSolver)
    result = prove(NO_PIN, {"pin_code_weight": 0})
    assert result.verdict == "UNKNOWN"
    assert result.compliant is False
    assert result.counterexample is None


def test_a_solver_crash_raises_instead_of_returning_a_verdict(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("src.lib.z3_client.z3.Solver", CrashingSolver)
    with pytest.raises(Z3ClientError):
        prove(NO_PIN, {"pin_code_weight": 0})


def test_integer_valued_features_are_checked_exactly() -> None:
    rule = "(declare-const loan_count Int)(assert (<= loan_count 3))"
    assert prove(rule, {"loan_count": 3}).compliant
    assert not prove(rule, {"loan_count": 4}).compliant


def test_a_violation_on_a_rule_with_several_variables_reports_all_of_them() -> None:
    rule = (
        "(declare-const a_weight Real)(declare-const b_weight Real)"
        "(assert (and (= a_weight 0) (= b_weight 0)))"
    )
    result = prove(rule, {"a_weight": 0.0, "b_weight": 0.5})
    assert not result.compliant
    assert result.counterexample == {"a_weight": "0", "b_weight": "1/2"}


def test_boolean_variables_are_never_called_prohibited_features() -> None:
    rule = "(declare-const flag Bool)(declare-const x_weight Real)(assert (and flag (= x_weight 0)))"
    assert forced_zero_variables(rule) == ["x_weight"]


def test_rule_variables_lists_every_feature_the_rule_mentions() -> None:
    rule = "(declare-const b_weight Real)(declare-const a_weight Real)(assert (> a_weight b_weight))"
    assert rule_variables(rule) == ["a_weight", "b_weight"]


def test_the_check_is_exact_not_floating_point() -> None:
    rule = "(declare-const w Real)(assert (= w (/ 1 10)))"
    assert prove(rule, {"w": 0.1}).compliant  # 0.1 is read as the decimal 1/10
    assert not prove(rule, {"w": 0.1000001}).compliant
