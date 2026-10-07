from collections.abc import Mapping

from src.lib.regulation_graph import ActiveRule


def humanize(variable: str) -> str:
    """`pin_code_weight` -> `pin code`."""
    return variable.removesuffix("_weight").replace("_", " ")


def explain_rule_violation(
    rule: ActiveRule, counterexample: Mapping[str, str]
) -> str:
    """Deterministic plain-English text for a rule violation.

    Templates only. No LLM runs in pipeline/ci/, and raw Z3
    values are never put in this text.
    """
    where = f" (section {rule.section})" if rule.section else ""
    what = rule.description or "The rule's conditions are not met."
    features = ", ".join(humanize(v) for v in counterexample)
    involved = f" Features involved: {features}." if features else ""
    return f"This model breaks rule {rule.rule_id}{where}. {what}{involved}"


def explain_unverifiable(rule: ActiveRule) -> str:
    return (
        f"Rule {rule.rule_id} could not be verified, so the model cannot be "
        "certified as compliant with it."
    )


def explain_fragile(rule: ActiveRule, feature: str, percent: float) -> str:
    return (
        f"Compliance with rule {rule.rule_id} depends on {humanize(feature)} "
        f"sitting exactly at a regulatory limit. A {percent:g}% change breaks it."
    )
