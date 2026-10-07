from src.api.schemas.regulation import RegulationStatus

S = RegulationStatus

ALLOWED_TRANSITIONS: dict[RegulationStatus, frozenset[RegulationStatus]] = {
    S.EXTRACTED: frozenset({S.Z3_VALIDATED, S.Z3_REJECTED}),
    S.Z3_VALIDATED: frozenset({S.PENDING_APPROVAL}),
    S.PENDING_APPROVAL: frozenset({S.APPROVED, S.REJECTED}),
    S.APPROVED: frozenset({S.ACTIVE}),
    S.Z3_REJECTED: frozenset(),
    S.REJECTED: frozenset(),
    S.ACTIVE: frozenset({S.SUPERSEDED}),
    S.SUPERSEDED: frozenset(),
}

# Transitions that only a human action may trigger.
HUMAN_ONLY_TARGETS = frozenset({S.APPROVED, S.REJECTED})


class InvalidStateTransitionError(Exception):
    """Raised when a regulation status change is not permitted."""


def transition(
    current: RegulationStatus,
    target: RegulationStatus,
    *,
    by_human: bool = False,
) -> RegulationStatus:
    """Return `target` if the move is legal, else raise.

    `by_human` must be True for approve/reject. There is no auto-approve path.
    """
    if target not in ALLOWED_TRANSITIONS[current]:
        raise InvalidStateTransitionError(
            f"Cannot move a rule from '{current.value}' to '{target.value}'."
        )
    if target in HUMAN_ONLY_TARGETS and not by_human:
        raise InvalidStateTransitionError(
            f"Moving to '{target.value}' requires a human action."
        )
    return target
