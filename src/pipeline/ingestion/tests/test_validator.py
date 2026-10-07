import pytest

from src.api.schemas.regulation import RegulationStatus
from src.pipeline.ingestion.validator import validate

VALID = "(declare-const pin_code_weight Real)(assert (= pin_code_weight 0))"


def test_valid_formula_is_z3_validated() -> None:
    result = validate(VALID)
    assert result.status is RegulationStatus.Z3_VALIDATED
    assert result.reason is None


@pytest.mark.parametrize(
    "formula",
    [
        "(declare-const x Real)(assert (= x",  # unbalanced
        "(assert (= y 0))",  # undeclared constant
        "(assert true)",  # vacuous
        "(declare-const x Real)(assert (and (> x 1) (< x 0)))",  # contradiction
        "(set-option :timeout 1)(assert true)",  # disallowed command
        "(declare-const x Real)(check-sat)",  # disallowed command
        "(declare-const x Real)(assert (> x 0)) ; hi",  # comment
        "(assert (= 1 1))",
        "",
        "x" * 6000,
    ],
)
def test_malformed_formula_is_z3_rejected(formula: str) -> None:
    result = validate(formula)
    assert result.status is RegulationStatus.Z3_REJECTED
    assert result.reason


def test_valid_formula_still_validates_after_a_malformed_one() -> None:
    """Regression: a failed Z3 parse used to poison every later parse."""
    assert validate("(assert (= y 0))").status is RegulationStatus.Z3_REJECTED
    assert validate(VALID).status is RegulationStatus.Z3_VALIDATED
