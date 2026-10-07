import pytest

from src.api.schemas.regulation import RegulationStatus as S
from src.pipeline.ingestion.approver import InvalidStateTransitionError, transition


def test_happy_path() -> None:
    assert transition(S.EXTRACTED, S.Z3_VALIDATED) is S.Z3_VALIDATED
    assert transition(S.Z3_VALIDATED, S.PENDING_APPROVAL) is S.PENDING_APPROVAL
    assert transition(S.PENDING_APPROVAL, S.APPROVED, by_human=True) is S.APPROVED
    assert transition(S.APPROVED, S.ACTIVE) is S.ACTIVE


def test_no_auto_approval() -> None:
    with pytest.raises(InvalidStateTransitionError):
        transition(S.PENDING_APPROVAL, S.APPROVED)
    with pytest.raises(InvalidStateTransitionError):
        transition(S.PENDING_APPROVAL, S.REJECTED)


@pytest.mark.parametrize(
    ("current", "target"),
    [
        (S.EXTRACTED, S.PENDING_APPROVAL),  # skips Z3
        (S.EXTRACTED, S.ACTIVE),
        (S.Z3_REJECTED, S.PENDING_APPROVAL),  # malformed never reaches queue
        (S.Z3_VALIDATED, S.APPROVED),
        (S.PENDING_APPROVAL, S.ACTIVE),  # skips human approval
        (S.REJECTED, S.ACTIVE),
        (S.ACTIVE, S.REJECTED),
        (S.SUPERSEDED, S.ACTIVE),  # history is never reactivated
    ],
)
def test_invalid_transitions_raise(current: S, target: S) -> None:
    with pytest.raises(InvalidStateTransitionError):
        transition(current, target, by_human=True)
