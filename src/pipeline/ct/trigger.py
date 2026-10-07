import logging
import os

import httpx

logger = logging.getLogger(__name__)

GITHUB_API = "https://api.github.com"
REQUEST_TIMEOUT_SECONDS = 15.0


class TriggerError(Exception):
    """Raised when the CT workflow cannot be dispatched."""


async def dispatch_ct_workflow(
    regulation_version: str, client: httpx.AsyncClient | None = None
) -> None:
    """Start the CT workflow in GitHub Actions.

    Needs GITHUB_TOKEN (a token allowed to run workflows) and GITHUB_REPOSITORY
    (`owner/name`). CT_WORKFLOW_FILE and CT_WORKFLOW_REF are optional.
    """
    token = os.environ.get("GITHUB_TOKEN")
    repository = os.environ.get("GITHUB_REPOSITORY")
    if not token or not repository:
        raise TriggerError("Continuous training is not configured on the server.")
    workflow = os.environ.get("CT_WORKFLOW_FILE", "ct.yml")
    ref = os.environ.get("CT_WORKFLOW_REF", "main")
    url = f"{GITHUB_API}/repos/{repository}/actions/workflows/{workflow}/dispatches"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    body = {"ref": ref, "inputs": {"regulation_version": regulation_version}}
    owns_client = client is None
    http = client or httpx.AsyncClient(timeout=REQUEST_TIMEOUT_SECONDS)
    try:
        response = await http.post(url, headers=headers, json=body)
    except httpx.HTTPError as e:
        logger.error("CT dispatch failed error=%s", type(e).__name__)
        raise TriggerError("Could not reach GitHub.") from e
    finally:
        if owns_client:
            await http.aclose()
    if response.status_code != 204:
        logger.error("CT dispatch rejected status=%d", response.status_code)
        raise TriggerError(f"GitHub rejected the request ({response.status_code}).")
    logger.info("CT workflow dispatched regulation_version=%s", regulation_version)
