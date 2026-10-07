import logging
import os
from typing import Any, Protocol

import httpx

logger = logging.getLogger(__name__)

RAILWAY_GRAPHQL = "https://backboard.railway.app/graphql/v2"
REQUEST_TIMEOUT_SECONDS = 30.0
VERSION_VARIABLE = "MODEL_VERSION"


class DeployError(Exception):
    """Raised when a deploy, promote or rollback step fails."""


class Deployer(Protocol):
    async def deploy_canary(self, model_version: str, percent: int) -> None: ...
    async def promote(self, model_version: str) -> None: ...
    async def rollback(self) -> None: ...


class RailwayDeployer:
    """Railway deploys driven through its GraphQL API.

    A deploy sets the `MODEL_VERSION` variable on a service and redeploys it.
    The canary is a separate service (`RAILWAY_CANARY_SERVICE_ID`) that receives
    no live traffic: Railway cannot split traffic by percentage, so `percent` is
    only passed along as the `CANARY_PERCENT` variable for the serving app.

    NOTE: the GraphQL operations below were written from Railway's public
    schema and have not been run against a real project.
    """

    def __init__(
        self,
        client: httpx.AsyncClient | None = None,
        *,
        token: str | None = None,
        project_id: str | None = None,
        environment_id: str | None = None,
        service_id: str | None = None,
        canary_service_id: str | None = None,
    ) -> None:
        env = os.environ.get
        self._token = token or env("RAILWAY_API_TOKEN", "")
        self._project = project_id or env("RAILWAY_PROJECT_ID", "")
        self._environment = environment_id or env("RAILWAY_ENVIRONMENT_ID", "")
        self._service = service_id or env("RAILWAY_SERVICE_ID", "")
        self._canary = canary_service_id or env("RAILWAY_CANARY_SERVICE_ID", "")
        if not all(
            (self._token, self._project, self._environment, self._service, self._canary)
        ):
            raise DeployError("Deployment is not configured on the server.")
        self._client = client
        self._previous: str | None = None

    async def _graphql(self, query: str, variables: dict[str, Any]) -> dict[str, Any]:
        owns = self._client is None
        http = self._client or httpx.AsyncClient(timeout=REQUEST_TIMEOUT_SECONDS)
        try:
            response = await http.post(
                RAILWAY_GRAPHQL,
                headers={"Authorization": f"Bearer {self._token}"},
                json={"query": query, "variables": variables},
            )
        except httpx.HTTPError as e:
            logger.error("Railway request failed error=%s", type(e).__name__)
            raise DeployError("Could not reach Railway.") from e
        finally:
            if owns:
                await http.aclose()
        body = response.json() if response.content else {}
        if response.status_code != 200 or body.get("errors"):
            logger.error("Railway rejected request status=%d", response.status_code)
            raise DeployError("Railway rejected the deployment request.")
        data: dict[str, Any] = body.get("data", {})
        return data

    async def _current_version(self, service_id: str) -> str | None:
        data = await self._graphql(
            "query($p: String!, $e: String!, $s: String!) "
            "{ variables(projectId: $p, environmentId: $e, serviceId: $s) }",
            {"p": self._project, "e": self._environment, "s": service_id},
        )
        value = data.get("variables", {}).get(VERSION_VARIABLE)
        return str(value) if value else None

    async def _release(
        self, service_id: str, model_version: str, percent: int
    ) -> None:
        variables = {VERSION_VARIABLE: model_version, "CANARY_PERCENT": str(percent)}
        for name, value in variables.items():
            await self._graphql(
                "mutation($i: VariableUpsertInput!) { variableUpsert(input: $i) }",
                {
                    "i": {
                        "projectId": self._project,
                        "environmentId": self._environment,
                        "serviceId": service_id,
                        "name": name,
                        "value": value,
                    }
                },
            )
        await self._graphql(
            "mutation($s: String!, $e: String!) "
            "{ serviceInstanceRedeploy(serviceId: $s, environmentId: $e) }",
            {"s": service_id, "e": self._environment},
        )

    async def deploy_canary(self, model_version: str, percent: int) -> None:
        self._previous = await self._current_version(self._service)
        await self._release(self._canary, model_version, percent)

    async def promote(self, model_version: str) -> None:
        await self._release(self._service, model_version, 100)

    async def rollback(self) -> None:
        """Put the main service back on the version it had before the canary."""
        if self._previous is not None:
            await self._release(self._service, self._previous, 100)
