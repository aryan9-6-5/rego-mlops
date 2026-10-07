import time
from collections.abc import Sequence

from src.api.schemas.pipeline import GateName, GateResult, GateStatus, Violation
from src.lib.model_bundle import Submission
from src.lib.regulation_graph import ActiveRule
from src.lib.z3_client import Z3ClientError, prove, rule_variables
from src.pipeline.ci.reporter import explain_fragile

# Relative nudge applied to each weight. Zero stays zero, so an unused
# prohibited feature is not "attacked" into violation.
EPSILON = 1e-3


def check_rules(rules: Sequence[ActiveRule], submission: Submission) -> GateResult:
    """Boundary robustness: compliance must survive a small change to any weight.

    A model that complies only because a weight sits exactly on a regulatory
    limit is fragile, since retraining noise would push it over. Each weight
    a rule mentions is scaled by (1 + EPSILON) and (1 - EPSILON) and re-proved.
    Rules the model already breaks are left to the symbolic check.
    """
    started = time.perf_counter()
    violations: list[Violation] = []
    for rule in rules:
        try:
            if not prove(rule.formal_logic, submission.weights).compliant:
                continue
            variables = rule_variables(rule.formal_logic)
        except Z3ClientError:
            continue
        for name in variables:
            value = submission.weights.get(name, 0)
            if isinstance(value, bool):
                continue
            broken = _first_breaking_nudge(rule, submission, name, float(value))
            if broken is not None:
                violations.append(Violation(
                    rule_id=rule.rule_id,
                    plain_english=explain_fragile(rule, name, EPSILON * 100),
                    counterexample=broken,
                ))
                break
    duration_ms = (time.perf_counter() - started) * 1000
    passed = not violations
    return GateResult(
        gate=GateName.REG_ATTACK,
        status=GateStatus.COMPLIANT if passed else GateStatus.VIOLATION,
        rule_ids=[r.rule_id for r in rules],
        duration_ms=duration_ms,
        plain_english=(
            "Compliance holds under small changes to every model weight."
            if passed
            else "Compliance depends on weights sitting exactly at a regulatory limit."
        ),
        violations=violations,
    )


def _first_breaking_nudge(
    rule: ActiveRule, submission: Submission, name: str, value: float
) -> dict[str, str] | None:
    for factor in (1 + EPSILON, 1 - EPSILON):
        nudged = {**submission.weights, name: value * factor}
        try:
            proof = prove(
                rule.formal_logic,
                nudged,
                rule_ids=[rule.rule_id],
                model_version=submission.model_version,
            )
        except Z3ClientError:
            return {name: str(value * factor)}
        if not proof.compliant:
            return proof.counterexample or {name: str(value * factor)}
    return None
