"""The remaining routes and error mappings, through the real API."""

import pytest
from fastapi.testclient import TestClient

from src.pipeline.cd.deployer import DeployError
from src.pipeline.ct import trigger
from tests.integration.conftest import CO_HEADERS, CTO_HEADERS, MLE_HEADERS
from tests.integration.flows import activate_rule, certified_deployment, deploy, run_ci
from tests.integration.world import NEEDS_INCOME, World


def test_trigger_ct_dispatches_the_workflow_for_the_given_version(
    api: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    sent: list[str] = []

    async def fake_dispatch(version: str, client: object = None) -> None:
        sent.append(version)

    monkeypatch.setattr(trigger, "dispatch_ct_workflow", fake_dispatch)
    response = api.post("/api/pipeline/trigger-ct", json={"regulation_version": "RBI-4.1-x"}, headers=MLE_HEADERS)
    assert response.status_code == 202
    assert sent == ["RBI-4.1-x"]


def test_trigger_ct_reports_a_dispatch_failure_without_internals(
    api: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def failing(version: str, client: object = None) -> None:
        raise trigger.TriggerError("Could not reach GitHub.")

    monkeypatch.setattr(trigger, "dispatch_ct_workflow", failing)
    response = api.post("/api/pipeline/trigger-ct", json={"regulation_version": "v"}, headers=MLE_HEADERS)
    assert response.status_code == 502
    assert response.json()["detail"] == "Could not reach GitHub."


def test_a_railway_failure_during_deploy_is_502_and_rolled_back(
    api: TestClient, world: World, monkeypatch: pytest.MonkeyPatch
) -> None:
    activate_rule(api)
    world.bundle("m", {"income_weight": 0.4, "pin_code_weight": 0.0})
    assert run_ci(api, "m")["status"] == "compliant"

    async def failing(model_version: str, percent: int) -> None:
        world.deployer.calls.append("canary")
        raise DeployError("railway down")

    monkeypatch.setattr(world.deployer, "deploy_canary", failing)
    response = deploy(api, "m")
    assert response.status_code == 502
    assert "promote" not in world.deployer.calls
    assert world.deployer.calls[-1] == "rollback"


def test_a_regulation_that_changes_during_the_canary_blocks_promotion(
    api: TestClient, world: World, monkeypatch: pytest.MonkeyPatch
) -> None:
    activate_rule(api)
    world.bundle("m", {"income_weight": 0.4, "pin_code_weight": 0.0})
    assert run_ci(api, "m")["status"] == "compliant"

    async def canary_then_law_changes(model_version: str, percent: int) -> None:
        world.deployer.calls.append("canary")
        world.llm.formulas = [NEEDS_INCOME]
        activate_rule(api)  # a new rule version lands while the canary runs

    monkeypatch.setattr(world.deployer, "deploy_canary", canary_then_law_changes)
    response = deploy(api, "m")
    assert response.status_code == 502
    assert "promote" not in world.deployer.calls


def test_deploying_a_model_that_does_not_exist_is_refused(api: TestClient, world: World) -> None:
    activate_rule(api)
    response = deploy(api, "ghost")
    assert response.status_code == 409  # CI cannot have passed for a model nobody checked
    assert world.certificates.rows == {}


def test_the_model_list_and_lineage_follow_the_deployment(api: TestClient, world: World) -> None:
    certified_deployment(api, world)
    (model,) = api.get("/api/models/", headers=CO_HEADERS).json()
    assert model["model_version"] == "good-1"
    assert [r["status"] for r in model["regulation_versions"]] == ["active"]
    assert api.get("/api/models/unknown/lineage", headers=CO_HEADERS).status_code == 404


def test_lineage_keeps_a_superseded_regulation_visible(api: TestClient, world: World) -> None:
    certified_deployment(api, world)
    world.llm.formulas = [NEEDS_INCOME]
    activate_rule(api)
    lineage = api.get("/api/models/good-1/lineage", headers=CO_HEADERS).json()
    assert [r["status"] for r in lineage["regulation_versions"]] == ["superseded"]


def test_the_drift_log_lists_active_and_superseded_versions(api: TestClient, world: World) -> None:
    activate_rule(api)
    world.llm.formulas = [NEEDS_INCOME]
    activate_rule(api)
    log = api.get("/api/pipeline/drift-log", headers=MLE_HEADERS).json()
    assert sorted(entry["status"] for entry in log) == ["active", "superseded"]


def test_the_model_diff_flags_a_change_that_touches_an_active_rule(
    api: TestClient, world: World
) -> None:
    activate_rule(api)
    world.bundle("old", {"income_weight": 0.4})
    world.bundle("new", {"income_weight": 0.4, "pin_code_weight": 0.3})
    diff = api.get("/api/models/diff", params={"from_version": "old", "to_version": "new"}, headers=MLE_HEADERS)
    assert diff.status_code == 200
    (change,) = diff.json()["changes"]
    assert (change["feature"], change["kind"], change["affects_rules"]) == (
        "pin_code", "added", ["RBI-4.1"],
    )
    assert api.get("/api/models/diff", params={"from_version": "old", "to_version": "gone"}, headers=CTO_HEADERS).status_code == 404
    assert api.get("/api/models/diff", params={"from_version": "../x", "to_version": "new"}, headers=MLE_HEADERS).status_code == 422


def test_register_model_is_for_ml_engineers_only(api: TestClient) -> None:
    body = {"name": "m", "version": "v1", "accuracy": 0.9}
    assert api.post("/api/models/", json=body, headers=MLE_HEADERS).json()["status"] == "registered"
    assert api.post("/api/models/", json=body, headers=CO_HEADERS).status_code == 403


def test_health_checks_need_no_login(api: TestClient) -> None:
    assert api.get("/health/").json()["status"] == "ok"
    assert api.get("/health/z3").json()["z3_version"].startswith("4.12")


# ---- a database outage is a 503 with a clear message, never a 500 ------------


@pytest.mark.parametrize(
    ("method", "path", "headers"),
    [
        ("GET", "/api/models/", CO_HEADERS),
        ("GET", "/api/pipeline/drift-log", MLE_HEADERS),
        ("GET", "/api/models/x/lineage", CO_HEADERS),
    ],
)
def test_a_neo4j_outage_is_503_with_a_plain_message_and_no_internals(
    api: TestClient, world: World, method: str, path: str, headers: dict[str, str]
) -> None:
    from neo4j.exceptions import ServiceUnavailable

    world.graph.error = ServiceUnavailable("could not connect to bolt://internal-host:7687")
    response = api.request(method, path, headers=headers)
    assert response.status_code == 503
    assert response.json() == {
        "detail": "The knowledge graph is temporarily unavailable. Please try again shortly."
    }
    assert "internal-host" not in response.text


def test_an_outage_during_approval_leaves_the_rule_approved_and_retryable(
    api: TestClient, world: World
) -> None:
    from neo4j.exceptions import ServiceUnavailable

    from tests.integration.flows import approve, ingest, pending

    ingest(api)
    rule = pending(api)
    world.graph.error = ServiceUnavailable("down")
    assert approve(api, rule["id"]).status_code == 503
    assert world.regulations.rows[rule["id"]]["status"] == "approved"  # not active, not lost

    world.graph.error = None
    retried = approve(api, rule["id"])
    assert retried.status_code == 200 and retried.json()["status"] == "active"


def test_the_health_check_does_not_depend_on_the_graph(api: TestClient, world: World) -> None:
    from neo4j.exceptions import ServiceUnavailable

    world.graph.error = ServiceUnavailable("down")
    assert api.get("/health/").status_code == 200
