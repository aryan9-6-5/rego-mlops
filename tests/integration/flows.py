"""Reusable steps for the flow tests."""

from typing import Any

from fastapi.testclient import TestClient

from tests.integration.conftest import CO_HEADERS, MLE_HEADERS
from tests.integration.world import World

TEXT = {"section": "4.1", "content": "Models shall not use PIN codes.", "jurisdiction": "India"}


def ingest(api: TestClient, **overrides: str) -> list[dict[str, Any]]:
    """CO pastes text. Returns the rules now listed for review."""
    response = api.post("/regulations/", json={**TEXT, **overrides}, headers=CO_HEADERS)
    assert response.status_code == 202, response.text
    job = api.get(f"/regulations/jobs/{response.json()['job_id']}", headers=CO_HEADERS)
    assert job.json()["status"] == "complete", job.json()
    return api.get("/regulations/", headers=CO_HEADERS).json()  # type: ignore[no-any-return]


def pending(api: TestClient) -> dict[str, Any]:
    rules = api.get("/regulations/", headers=CO_HEADERS).json()
    waiting = [r for r in rules if r["status"] == "pending_approval"]
    assert len(waiting) == 1, rules
    return waiting[0]  # type: ignore[no-any-return]


def approve(api: TestClient, regulation_id: str) -> Any:
    return api.post(f"/regulations/{regulation_id}/approve", headers=CO_HEADERS)


def activate_rule(api: TestClient) -> dict[str, Any]:
    """Ingest and approve one rule. Returns the active regulation."""
    ingest(api)
    response = approve(api, pending(api)["id"])
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "active"
    return response.json()  # type: ignore[no-any-return]


def run_ci(api: TestClient, model: str) -> dict[str, Any]:
    """MLE submits a bundle. The background run finishes before the call returns."""
    response = api.post("/pipeline/submit", json={"artifact_path": model}, headers=MLE_HEADERS)
    assert response.status_code == 202, response.text
    return api.get("/pipeline/status", headers=MLE_HEADERS).json()  # type: ignore[no-any-return]


def deploy(api: TestClient, model: str) -> Any:
    return api.post("/pipeline/deploy", json={"model_version": model}, headers=MLE_HEADERS)


def certified_deployment(
    api: TestClient,
    world: World,
    name: str = "good-1",
    weights: dict[str, float] | None = None,
) -> str:
    """Full happy path up to a deployed, certified model. Returns the certificate id."""
    activate_rule(api)
    world.bundle(name, weights or {"income_weight": 0.4, "pin_code_weight": 0.0})
    run = run_ci(api, name)
    assert run["status"] == "compliant", run
    response = deploy(api, name)
    assert response.status_code == 201, response.text
    return response.json()["certificate_id"]  # type: ignore[no-any-return]
