"""Compliance-gated deploy and write-once certificates."""

from fastapi.testclient import TestClient

from tests.integration.conftest import CO_HEADERS, MLE_HEADERS
from tests.integration.flows import (
    activate_rule,
    certified_deployment,
    deploy,
    run_ci,
)
from tests.integration.world import NEEDS_INCOME, World


def test_a_compliant_model_is_certified_with_its_regulation_versions_and_deployed(
    api: TestClient, world: World
) -> None:
    certificate_id = certified_deployment(api, world)

    cert = api.get(f"/certificates/{certificate_id}", headers=CO_HEADERS)
    assert cert.status_code == 200
    body = cert.json()
    assert body["model_version"] == "good-1"
    (regulation,) = body["regulation_versions"]
    assert regulation["rule_id"] == "RBI-4.1"  # model AND regulation version together
    assert len(body["proof_hash"]) == 64

    assert world.deployer.calls == ["canary", "promote"]
    lineage = api.get("/models/good-1/lineage", headers=CO_HEADERS).json()
    assert [r["rule_id"] for r in lineage["regulation_versions"]] == ["RBI-4.1"]


def test_a_second_deploy_of_the_same_model_is_409_and_changes_nothing(
    api: TestClient, world: World
) -> None:
    certified_deployment(api, world)
    again = deploy(api, "good-1")
    assert again.status_code == 409
    assert len(world.certificates.rows) == 1
    assert world.deployer.calls == ["canary", "promote"]  # not deployed twice


def test_a_new_regulation_version_allows_a_fresh_certificate_for_the_same_model(
    api: TestClient, world: World
) -> None:
    """The proof hash covers the rule versions, so re-certifying after a law
    change is allowed, and the old certificate is left exactly as it was."""
    weights = {"income_weight": 0.95, "pin_code_weight": 0.0}
    first = certified_deployment(api, world, weights=weights)
    original = dict(world.certificates.rows[first])

    world.llm.formulas = [NEEDS_INCOME]
    activate_rule(api)  # supersedes the PIN rule with one this model also meets
    assert run_ci(api, "good-1")["status"] == "compliant"
    second = deploy(api, "good-1")

    assert second.status_code == 201
    assert len(world.certificates.rows) == 2
    assert world.certificates.rows[first] == original  # never modified


def test_there_is_no_route_to_create_change_or_delete_a_certificate(
    api: TestClient, world: World
) -> None:
    certificate_id = certified_deployment(api, world)
    for method in ("post", "put", "patch", "delete"):
        for path in ("/certificates/", f"/certificates/{certificate_id}"):
            response = api.request(method.upper(), path, headers=MLE_HEADERS, json={})
            assert response.status_code in (404, 405, 422), (method, path)
    assert len(world.certificates.rows) == 1


def test_deploy_is_refused_when_ci_has_not_passed(api: TestClient, world: World) -> None:
    activate_rule(api)
    world.bundle("never-checked", {"income_weight": 0.4})
    response = deploy(api, "never-checked")
    assert response.status_code == 409
    assert "gate" in response.json()["detail"]
    assert world.certificates.rows == {} and world.deployer.calls == []


def test_deploy_is_refused_after_a_failed_ci_run(api: TestClient, world: World) -> None:
    activate_rule(api)
    world.bundle("bad", {"pin_code_weight": 0.3})
    run_ci(api, "bad")
    assert deploy(api, "bad").status_code == 409
    assert world.certificates.rows == {} and world.deployer.calls == []


def test_a_failed_ci_run_after_a_pass_blocks_a_later_deploy(
    api: TestClient, world: World
) -> None:
    """The latest result per gate counts, so a model cannot ride an old pass."""
    activate_rule(api)
    world.bundle("flaky", {"income_weight": 0.4})
    assert run_ci(api, "flaky")["status"] == "compliant"
    (world.artifact_dir / "flaky" / "profile.json").write_text(
        '{"weights": {"pin_code_weight": 0.5}}'
    )
    assert run_ci(api, "flaky")["status"] == "violation"
    assert deploy(api, "flaky").status_code == 409


def test_a_model_over_a_rule_that_changed_after_ci_is_not_certified(
    api: TestClient, world: World
) -> None:
    activate_rule(api)
    world.bundle("late", {"income_weight": 0.4, "pin_code_weight": 0.0})
    assert run_ci(api, "late")["status"] == "compliant"
    world.llm.formulas = [NEEDS_INCOME]
    activate_rule(api)
    response = deploy(api, "late")
    assert response.status_code == 422
    assert world.certificates.rows == {} and world.deployer.calls == []
