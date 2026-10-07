import logging
from typing import Any

import httpx
import pytest

from src.pipeline.cd.canary import run_canary
from src.pipeline.cd.deployer import DeployError, RailwayDeployer
from src.pipeline.cd.lineage import record_lineage


def railway(handler: Any) -> RailwayDeployer:
    return RailwayDeployer(
        httpx.AsyncClient(transport=httpx.MockTransport(handler)),
        token="t", project_id="p", environment_id="e",
        service_id="main", canary_service_id="canary",
    )


@pytest.mark.asyncio
async def test_a_network_error_is_a_deploy_error_without_internals() -> None:
    def boom(_: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("internal-host unreachable")

    with pytest.raises(DeployError) as caught:
        await railway(boom).promote("m")
    assert "internal-host" not in str(caught.value)


@pytest.mark.asyncio
async def test_a_non_200_reply_is_a_deploy_error() -> None:
    with pytest.raises(DeployError):
        await railway(lambda _r: httpx.Response(401, json={})).promote("m")


@pytest.mark.asyncio
async def test_a_deployer_with_nothing_to_roll_back_does_nothing() -> None:
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append("request")
        return httpx.Response(200, json={"data": {}})

    await railway(handler).rollback()
    assert calls == []


class FailingRollback:
    async def deploy_canary(self, model_version: str, percent: int) -> None:
        raise DeployError("canary")

    async def promote(self, model_version: str) -> None:
        return None

    async def rollback(self) -> None:
        raise DeployError("rollback too")


@pytest.mark.asyncio
async def test_a_failed_rollback_is_logged_and_the_model_still_is_not_promoted(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.ERROR):
        result = await run_canary(FailingRollback(), "m", lambda: True)
    assert result.promoted is False
    assert "manual intervention" in caplog.text


class BrokenGraph:
    def run_query(self, query: str, params: dict[str, Any] | None = None) -> Any:
        raise RuntimeError("neo4j down")


def test_lineage_write_failure_is_raised_not_swallowed() -> None:
    with pytest.raises(RuntimeError, match="neo4j down"):
        record_lineage(BrokenGraph(), "m1")
