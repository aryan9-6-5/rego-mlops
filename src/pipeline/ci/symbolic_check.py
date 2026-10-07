import time
from collections.abc import Sequence

from src.api.schemas.pipeline import GateName, GateResult, GateStatus, Violation
from src.lib.model_bundle import Submission
from src.lib.regulation_graph import ActiveRule, GraphClient, fetch_active_rules
from src.lib.z3_client import Z3ClientError, prove
from src.pipeline.ci.reporter import explain_rule_violation, explain_unverifiable

NO_RULES_MESSAGE = (
    "There are no active regulation rules, so the model cannot be certified."
)


def check_rules(rules: Sequence[ActiveRule], submission: Submission) -> GateResult:
    """Z3 check of the model's weights against every active rule.

    Fails closed: no rules, an unparseable rule, or an UNKNOWN solver answer all
    count as a violation.
    """
    started = time.perf_counter()
    rule_ids = [r.rule_id for r in rules]
    violations: list[Violation] = []
    for rule in rules:
        try:
            proof = prove(
                rule.formal_logic,
                submission.weights,
                rule_ids=[rule.rule_id],
                model_version=submission.model_version,
            )
        except Z3ClientError:
            violations.append(Violation(
                rule_id=rule.rule_id, plain_english=explain_unverifiable(rule)
            ))
            continue
        if not proof.compliant:
            counterexample = proof.counterexample or {}
            violations.append(Violation(
                rule_id=rule.rule_id,
                plain_english=(
                    explain_rule_violation(rule, counterexample)
                    if counterexample
                    else explain_unverifiable(rule)
                ),
                counterexample=counterexample,
            ))
    duration_ms = (time.perf_counter() - started) * 1000
    if not rules:
        return GateResult(
            gate=GateName.SYMBOLIC_CHECK,
            status=GateStatus.VIOLATION,
            duration_ms=duration_ms,
            plain_english=NO_RULES_MESSAGE,
        )
    passed = not violations
    return GateResult(
        gate=GateName.SYMBOLIC_CHECK,
        status=GateStatus.COMPLIANT if passed else GateStatus.VIOLATION,
        rule_ids=rule_ids,
        duration_ms=duration_ms,
        plain_english=(
            f"The model satisfies all {len(rules)} active rules."
            if passed
            else f"The model breaks {len(violations)} of {len(rules)} active rules."
        ),
        violations=violations,
    )


def run(graph: GraphClient, submission: Submission) -> GateResult:
    return check_rules(fetch_active_rules(graph), submission)
