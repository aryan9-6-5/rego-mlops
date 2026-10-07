"""CI gates through the real API: first failure halts, nothing runs after it (Rule 3)."""

from typing import Any

import pytest
from fastapi.testclient import TestClient

from src.pipeline.ci import fairness_check, regression
from tests.integration.conftest import CO_HEADERS, CTO_HEADERS, MLE_HEADERS
from tests.integration.flows import activate_rule, run_ci
from tests.integration.world import World


def statuses(run: dict[str, Any]) -> dict[str, str]:
    return {g["gate"]: g["status"] for g in run["gates"]}


def test_a_compliant_model_passes_all_four_gates(api: TestClient, world: World) -> None:
    activate_rule(api)
    world.bundle("good", {"income_weight": 0.4, "pin_code_weight": 0.0})
    run = run_ci(api, "good")
    assert run["status"] == "compliant"
    assert set(statuses(run).values()) == {"compliant"}
    assert len(world.events.rows) == 4  # every gate is in the audit log


def test_a_model_using_a_prohibited_feature_halts_at_the_first_gate(
    api: TestClient, world: World, monkeypatch: pytest.MonkeyPatch
) -> None:
    def must_not_run(*_: Any) -> Any:
        raise AssertionError("a later gate ran after the first one failed")

    monkeypatch.setattr(fairness_check, "run", must_not_run)
    monkeypatch.setattr(regression, "run", must_not_run)
    activate_rule(api)
    world.bundle("bad", {"income_weight": 0.4, "pin_code_weight": 0.3})
    run = run_ci(api, "bad")

    assert run["status"] == "violation"
    assert statuses(run) == {
        "symbolic_check": "violation",
        "reg_attack": "skipped",
        "fairness_check": "skipped",
        "regression": "skipped",
    }
    (violation,) = run["gates"][0]["violations"]
    assert violation["rule_id"] == "RBI-4.1"
    assert "pin code" in violation["plain_english"]
    assert violation["counterexample"] == {"pin_code_weight": "3/10"}
    assert [r["gate_name"] for r in world.events.rows] == ["symbolic_check"]


def test_a_model_that_is_accurate_but_unfair_fails_a_later_gate_and_halts_there(
    api: TestClient, world: World
) -> None:
    activate_rule(api)
    biased = {
        "y_true": [1, 0, 1, 0, 1, 0, 1, 0],
        "y_pred": [1, 1, 0, 0, 1, 1, 0, 0],
        "baseline_y_pred": [1, 1, 0, 0, 1, 1, 0, 0],
        "groups": ["a", "a", "b", "b"] * 2,
    }
    world.bundle("biased", {"income_weight": 0.4}, evaluation=biased)
    run = run_ci(api, "biased")
    assert statuses(run) == {
        "symbolic_check": "compliant",
        "reg_attack": "compliant",
        "fairness_check": "violation",
        "regression": "skipped",
    }


def test_with_no_active_rules_the_model_cannot_pass(api: TestClient, world: World) -> None:
    world.bundle("anything", {"income_weight": 0.4})
    run = run_ci(api, "anything")
    assert run["status"] == "violation"
    assert "no active" in run["gates"][0]["plain_english"].lower()


def test_a_model_without_evaluation_data_fails_closed(api: TestClient, world: World) -> None:
    activate_rule(api)
    world.bundle("no-eval", {"income_weight": 0.4}, evaluation=False)
    assert statuses(run_ci(api, "no-eval"))["fairness_check"] == "violation"


@pytest.mark.parametrize("path", ["missing", "../outside", "/etc/passwd", ""])
def test_bad_artifact_paths_are_refused_before_anything_runs(
    api: TestClient, world: World, path: str
) -> None:
    response = api.post("/api/pipeline/submit", json={"artifact_path": path}, headers=MLE_HEADERS)
    assert response.status_code in (400, 422)
    assert world.events.rows == []


def test_only_engineering_roles_can_see_the_run(api: TestClient, world: World) -> None:
    activate_rule(api)
    world.bundle("good", {"income_weight": 0.4})
    run_ci(api, "good")
    assert api.get("/api/pipeline/status", headers=CTO_HEADERS).status_code == 200
    assert api.get("/api/pipeline/status", headers=CO_HEADERS).status_code == 403
