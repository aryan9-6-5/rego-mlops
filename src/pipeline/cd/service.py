import logging
from dataclasses import dataclass
from pathlib import Path

from src.api.schemas.certificate import ProofCertificate
from src.lib.model_bundle import bundle_hash, load_submission
from src.lib.regulation_graph import GraphClient, fetch_active_rules
from src.pipeline.cd.canary import CANARY_PERCENT, run_canary
from src.pipeline.cd.certificate import CertificateStore, issue_certificate
from src.pipeline.cd.deployer import Deployer
from src.pipeline.cd.lineage import record_lineage
from src.pipeline.cd.stores import CIEventReader, confirm_ci_passed
from src.pipeline.cd.verification import verify_against_rules

logger = logging.getLogger(__name__)


class VerificationFailedError(Exception):
    """The final Z3 proof failed, so no certificate is issued."""


class DeploymentFailedError(Exception):
    """The canary or promotion failed and was rolled back."""


@dataclass(frozen=True)
class DeployOutcome:
    certificate: ProofCertificate
    canary_percent: int


async def deploy_model(
    *,
    model_version: str,
    base_dir: Path,
    graph: GraphClient,
    cert_store: CertificateStore,
    ci_reader: CIEventReader,
    deployer: Deployer,
    secret: str,
) -> DeployOutcome:
    """Compliance-gated deployment. There is no override.

    1. Every CI gate must have passed for this model.
    2. A final Z3 proof against the rules active now must succeed.
    3. The certificate is written once. A repeat of the same model and rules
       raises DuplicateCertificateError before anything is deployed.
    4. Lineage is recorded, then the canary runs with a shadow check, then promote.
    """
    confirm_ci_passed(ci_reader, model_version)
    submission = load_submission(model_version, base_dir)
    rules = fetch_active_rules(graph)
    verification = verify_against_rules(rules, submission.weights, model_version)
    if not verification.compliant:
        logger.error(
            "Final verification failed model=%s failed_rules=%s",
            model_version,
            verification.failed_rule_ids,
        )
        raise VerificationFailedError(
            "The model does not satisfy the active regulation rules."
        )
    certificate = issue_certificate(
        cert_store,
        secret,
        model_version=model_version,
        bundle_digest=bundle_hash(model_version, base_dir),
        regulations=verification.regulations,
    )
    record_lineage(graph, model_version)
    certified = {r.version_id for r in certificate.regulation_versions}

    def shadow_check() -> bool:
        current = fetch_active_rules(graph)
        if {r.version_id for r in current} != certified:
            return False  # a regulation changed mid-deploy
        proof = verify_against_rules(current, submission.weights, model_version)
        return proof.compliant

    result = await run_canary(deployer, model_version, shadow_check)
    if not result.promoted:
        raise DeploymentFailedError(result.reason or "Deployment failed.")
    logger.info(
        "Model promoted model_version=%s certificate=%s", model_version, certificate.id
    )
    return DeployOutcome(certificate, CANARY_PERCENT)
