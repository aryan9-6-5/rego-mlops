from typing import Any

import pytest
import z3

from src.api.schemas.regulation import RegulationStatus
from src.pipeline.ingestion.validator import validate


def test_a_rule_that_can_never_be_met_is_rejected() -> None:
    result = validate("(assert (= 1 2))")
    assert result.status is RegulationStatus.Z3_REJECTED
    assert "never be met" in (result.reason or "")


def test_a_rule_with_only_declarations_states_no_condition() -> None:
    result = validate("(declare-const x Real)")
    assert result.status is RegulationStatus.Z3_REJECTED
    assert "does not state any condition" in (result.reason or "")


def test_a_rule_that_contradicts_itself_is_rejected() -> None:
    result = validate("(declare-const x Real)(assert (> x 1))(assert (< x 0))")
    assert "contradicts itself" in (result.reason or "")


def test_unbalanced_closing_parentheses_are_rejected() -> None:
    assert validate("(assert true))").status is RegulationStatus.Z3_REJECTED


class UnknownSolver:
    def __init__(self, *_: Any, **__: Any) -> None:
        return None

    def set(self, *_: Any) -> None:
        return None

    def add(self, *_: Any) -> None:
        return None

    def check(self) -> Any:
        return z3.unknown


def test_a_rule_z3_cannot_decide_is_rejected_not_accepted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("src.pipeline.ingestion.validator.z3.Solver", UnknownSolver)
    result = validate("(declare-const x Real)(assert (> x 1))")
    assert result.status is RegulationStatus.Z3_REJECTED
    assert "could not be checked" in (result.reason or "")


def test_an_unexpected_error_rejects_the_rule_instead_of_crashing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def boom(*_: Any, **__: Any) -> Any:
        raise RuntimeError("z3 exploded")

    monkeypatch.setattr("src.pipeline.ingestion.validator.z3.parse_smt2_string", boom)
    result = validate("(declare-const x Real)(assert (> x 1))")
    assert result.status is RegulationStatus.Z3_REJECTED
    assert result.reason and "exploded" not in result.reason
