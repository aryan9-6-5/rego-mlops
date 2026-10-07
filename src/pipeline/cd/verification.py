from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from src.api.schemas.certificate import CertificateRegulation
from src.lib.regulation_graph import ActiveRule
from src.lib.z3_client import Z3ClientError, hash_formula, prove


@dataclass(frozen=True)
class FinalVerification:
    compliant: bool
    regulations: list[CertificateRegulation]
    failed_rule_ids: list[str]


def verify_against_rules(
    rules: Sequence[ActiveRule],
    weights: Mapping[str, float | bool],
    model_version: str,
) -> FinalVerification:
    """Final Z3 proof at deploy time, against the rules active right now.

    Z3 only. Fails closed: no rules, or any rule that cannot
    be proved, means not compliant.
    """
    failed: list[str] = []
    for rule in rules:
        try:
            proof = prove(
                rule.formal_logic,
                weights,
                rule_ids=[rule.rule_id],
                model_version=model_version,
            )
        except Z3ClientError:
            failed.append(rule.rule_id)
            continue
        if not proof.compliant:
            failed.append(rule.rule_id)
    return FinalVerification(
        compliant=bool(rules) and not failed,
        regulations=[
            CertificateRegulation(
                version_id=r.version_id,
                rule_id=r.rule_id,
                formula_hash=hash_formula(r.formal_logic),
            )
            for r in rules
        ],
        failed_rule_ids=failed,
    )
