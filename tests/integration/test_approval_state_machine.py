"""Ingestion -> approval -> active rule, through the real API."""

from fastapi.testclient import TestClient

from tests.integration.conftest import CO_HEADERS, MLE_HEADERS
from tests.integration.flows import TEXT, activate_rule, approve, ingest, pending
from tests.integration.world import NEEDS_INCOME, World


def test_a_pasted_rule_waits_for_review_and_is_not_active(
    api: TestClient, world: World
) -> None:
    ingest(api)
    rule = pending(api)
    assert rule["status"] == "pending_approval"
    assert rule["description"] == "Models must not use PIN codes."
    assert world.graph.active() == []  # nothing enters the knowledge graph yet


def test_approval_activates_the_rule_and_writes_it_to_the_graph(
    api: TestClient, world: World
) -> None:
    active = activate_rule(api)
    assert active["approved_by"] == "user-co"
    (node,) = world.graph.active()
    assert node["rule_id"] == "RBI-4.1"
    assert node["version_id"].startswith("RBI-4.1-")


def test_rejection_keeps_the_rule_out_of_the_graph(
    api: TestClient, world: World
) -> None:
    ingest(api)
    rule = pending(api)
    response = api.post(
        f"/regulations/{rule['id']}/reject", json={"reason": "wrong intent"}, headers=CO_HEADERS
    )
    assert response.status_code == 200
    assert response.json()["status"] == "rejected"
    assert world.graph.active() == []
    listed = {r["status"] for r in api.get("/regulations/", headers=CO_HEADERS).json()}
    assert "active" not in listed and "pending_approval" not in listed


def test_a_rule_cannot_be_approved_twice_or_after_rejection(api: TestClient) -> None:
    active = activate_rule(api)
    assert approve(api, active["id"]).status_code == 409

    api.post("/regulations/", json=TEXT, headers=CO_HEADERS)
    second = pending(api)
    api.post(f"/regulations/{second['id']}/reject", json={}, headers=CO_HEADERS)
    assert approve(api, second["id"]).status_code == 409


def test_a_malformed_rule_never_reaches_the_queue_and_cannot_be_approved(
    api: TestClient, world: World
) -> None:
    world.llm.formulas = ["(assert true)"]
    rules = ingest(api)
    (rule,) = rules
    assert rule["status"] == "z3_rejected"
    assert rule["validation_message"]
    assert "assert" not in rule["validation_message"]  # plain English, no Z3 text
    assert approve(api, rule["id"]).status_code == 409
    assert world.graph.active() == []


def test_a_new_version_of_a_rule_supersedes_the_old_one(
    api: TestClient, world: World
) -> None:
    first = activate_rule(api)
    world.llm.formulas = [NEEDS_INCOME]
    second = activate_rule(api)
    statuses = {r["version_id"]: r["status"] for r in world.graph.regulations.values()}
    assert list(statuses.values()).count("active") == 1
    assert list(statuses.values()).count("superseded") == 1
    assert world.regulations.rows[first["id"]]["status"] == "superseded"
    assert world.regulations.rows[second["id"]]["status"] == "active"


def test_an_unknown_rule_is_404(api: TestClient) -> None:
    assert approve(api, "does-not-exist").status_code == 404


def test_an_llm_outage_fails_the_job_cleanly(api: TestClient, world: World) -> None:
    world.llm.fail = True
    response = api.post("/regulations/", json=TEXT, headers=CO_HEADERS)
    assert response.status_code == 202
    job = api.get(f"/regulations/jobs/{response.json()['job_id']}", headers=CO_HEADERS).json()
    assert job["status"] == "failed"
    assert "down" not in job["error"]  # no internal detail
    assert api.get("/regulations/", headers=CO_HEADERS).json() == []


def test_the_ml_engineer_cannot_run_the_approval_flow(api: TestClient) -> None:
    ingest(api)
    rule = pending(api)
    assert api.post(f"/regulations/{rule['id']}/approve", headers=MLE_HEADERS).status_code == 403
    assert api.post(f"/regulations/{rule['id']}/reject", json={}, headers=MLE_HEADERS).status_code == 403
    assert api.post("/regulations/", json=TEXT, headers=MLE_HEADERS).status_code == 403
