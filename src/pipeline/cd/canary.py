import asyncio
import logging
from collections.abc import Callable
from dataclasses import dataclass

from src.pipeline.cd.deployer import Deployer, DeployError

logger = logging.getLogger(__name__)

CANARY_PERCENT = 10


@dataclass(frozen=True)
class CanaryResult:
    promoted: bool
    reason: str | None = None


async def run_canary(
    deployer: Deployer,
    model_version: str,
    shadow_check: Callable[[], bool],
    percent: int = CANARY_PERCENT,
) -> CanaryResult:
    """Canary deploy, shadow compliance check, then promote or roll back.

    `shadow_check` is a Z3-based re-verification against the rules active now
. The model is promoted only if it returns True. Any failure
    rolls back; nothing is promoted by default.
    """
    try:
        await deployer.deploy_canary(model_version, percent)
    except DeployError:
        await _rollback(deployer)
        return CanaryResult(False, "The canary deployment failed.")
    if not await asyncio.to_thread(shadow_check):
        await _rollback(deployer)
        return CanaryResult(
            False, "The shadow compliance check failed, so the model was not promoted."
        )
    try:
        await deployer.promote(model_version)
    except DeployError:
        await _rollback(deployer)
        return CanaryResult(False, "Promotion failed and was rolled back.")
    return CanaryResult(True)


async def _rollback(deployer: Deployer) -> None:
    try:
        await deployer.rollback()
    except DeployError:
        logger.error("Rollback failed; manual intervention needed")
