"""Who may do what, with real flows behind each call.

`test_auth_matrix.py` proves every route is gated. These tests prove the gates
hold when the call would otherwise succeed.
"""

from fastapi.testclient import TestClient

from tests.integration.conftest import CO_HEADERS, CTO_HEADERS, MLE_HEADERS
from tests.integration.flows import TEXT, certified_deployment, ingest, pending
from tests.integration.world import World


def test_the_compliance_officer_cannot_deploy_submit_or_start_training(
    api: TestClient, world: World
) -> None:
    certified_deployment(api, world)
    world.bundle("another", {"income_weight": 0.4})
    assert api.post("/api/pipeline/deploy", json={"model_version": "another"}, headers=CO_HEADERS).status_code == 403
    assert api.post("/api/pipeline/submit", json={"artifact_path": "another"}, headers=CO_HEADERS).status_code == 403
    assert api.post("/api/pipeline/trigger-ct", json={"regulation_version": "RBI-4.1-x"}, headers=CO_HEADERS).status_code == 403
    assert world.deployer.calls == ["canary", "promote"]  # only the legitimate deploy


def test_the_compliance_officer_cannot_see_counterexamples_or_the_pipeline(
    api: TestClient, world: World
) -> None:
    certified_deployment(api, world)
    for path in ("/api/pipeline/status", "/api/pipeline/drift-log", "/api/models/diff?from_version=a&to_version=b"):
        assert api.get(path, headers=CO_HEADERS).status_code == 403, path


def test_the_ml_engineer_cannot_approve_reject_or_add_rules(api: TestClient) -> None:
    ingest(api)
    rule = pending(api)
    for response in (
        api.post(f"/api/regulations/{rule['id']}/approve", headers=MLE_HEADERS),
        api.post(f"/api/regulations/{rule['id']}/reject", json={}, headers=MLE_HEADERS),
        api.post("/api/regulations/", json=TEXT, headers=MLE_HEADERS),
        api.get("/api/regulations/", headers=MLE_HEADERS),
    ):
        assert response.status_code == 403
    assert pending(api)["status"] == "pending_approval"  # untouched


def test_the_cto_can_read_but_never_change_anything(api: TestClient, world: World) -> None:
    certificate_id = certified_deployment(api, world)
    for path in ("/api/regulations/", "/api/certificates/", f"/api/certificates/{certificate_id}",
                 "/api/models/", "/api/pipeline/status", "/api/pipeline/drift-log"):
        assert api.get(path, headers=CTO_HEADERS).status_code == 200, path
    rule = world.regulations.rows["reg-1"]
    writes = (
        api.post("/api/regulations/", json=TEXT, headers=CTO_HEADERS),
        api.post(f"/api/regulations/{rule['id']}/approve", headers=CTO_HEADERS),
        api.post("/api/pipeline/submit", json={"artifact_path": "good-1"}, headers=CTO_HEADERS),
        api.post("/api/pipeline/deploy", json={"model_version": "good-1"}, headers=CTO_HEADERS),
        api.post("/api/pipeline/trigger-ct", json={"regulation_version": "v"}, headers=CTO_HEADERS),
    )
    assert [w.status_code for w in writes] == [403] * 5


def test_nothing_is_reachable_without_a_login_except_the_public_routes(
    api: TestClient, world: World
) -> None:
    certified_deployment(api, world)
    for method, path in (("GET", "/api/regulations/"), ("GET", "/api/certificates/"),
                         ("GET", "/api/models/"), ("GET", "/api/pipeline/status"),
                         ("POST", "/api/pipeline/deploy"), ("POST", "/api/regulations/")):
        assert api.request(method, path, json={}).status_code == 401, (method, path)
    assert api.get("/health/").status_code == 200
