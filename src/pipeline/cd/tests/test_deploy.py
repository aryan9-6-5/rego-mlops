import json
from pathlib import Path
from typing import Any

import httpx
import pytest

from src.lib.regulation_graph import ActiveRule
from src.pipeline.cd.canary import run_canary
from src.pipeline.cd.certificate import DuplicateCertificateError
from src.pipeline.cd.deployer import DeployError, RailwayDeployer
from src.pipeline.cd.service import (
    DeploymentFailedError,
    VerificationFailedError,
    deploy_model,
)
from src.pipeline.cd.stores import CINotConfirmedError, confirm_ci_passed
from src.pipeline.cd.tests.test_certificate import MemoryStore
from src.pipeline.cd.verification import verify_against_rules

NO_PIN = ActiveRule(
    "RBI-4.1-x",
    "RBI-4.1",
    "(declare-const pin_code_weight Real)(assert (= pin_code_weight 0))",
)
NEW_RULE = ActiveRule(
    "RBI-4.2-y",
    "RBI-4.2",
    "(declare-const income_weight Real)(assert (> income_weight 0))",
)
OLD_VERSION_REPLY = {"data": {"variables": {"MODEL_VERSION": "old"}}}
GATES = ["symbolic_check", "reg_attack", "fairness_check", "regression"]
ALL_PASS = dict.fromkeys(GATES, "compliant")
SECRET = "s3cret"


def rule_row(rule: ActiveRule) -> dict[str, Any]:
    return {
        "version_id": rule.version_id,
        "rule_id": rule.rule_id,
        "formal_logic": rule.formal_logic,
        "section": None,
        "description": None,
    }


class FakeGraph:
    """Answers the active-rules query from a queue; accepts lineage writes."""

    def __init__(self, *rule_sets: list[ActiveRule]) -> None:
        self.rule_sets = list(rule_sets)
        self.lineage: list[str] = []

    def run_query(
        self, query: str, params: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        if "ModelVersion" in query:
            self.lineage.append((params or {})["model_version"])
            return [{"version_ids": ["x"]}]
        rules = self.rule_sets.pop(0) if len(self.rule_sets) > 1 else self.rule_sets[0]
        return [rule_row(r) for r in rules]


class FakeReader:
    def __init__(self, statuses: dict[str, str]) -> None:
        self.statuses = statuses

    def latest_gate_statuses(self, model_version: str) -> dict[str, str]:
        return self.statuses


class FakeDeployer:
    def __init__(self, fail_canary: bool = False, fail_promote: bool = False) -> None:
        self.calls: list[str] = []
        self.fail_canary = fail_canary
        self.fail_promote = fail_promote

    async def deploy_canary(self, model_version: str, percent: int) -> None:
        self.calls.append(f"canary:{percent}")
        if self.fail_canary:
            raise DeployError("canary")

    async def promote(self, model_version: str) -> None:
        self.calls.append("promote")
        if self.fail_promote:
            raise DeployError("promote")

    async def rollback(self) -> None:
        self.calls.append("rollback")


def make_bundle(base: Path, weights: dict[str, float], name: str = "m1") -> None:
    folder = base / name
    folder.mkdir()
    (folder / "profile.json").write_text(json.dumps({"weights": weights}))


async def run_deploy(
    base: Path,
    graph: FakeGraph,
    store: MemoryStore,
    deployer: FakeDeployer,
    statuses: dict[str, str] | None = None,
) -> Any:
    return await deploy_model(
        model_version="m1",
        base_dir=base,
        graph=graph,
        cert_store=store,
        ci_reader=FakeReader(ALL_PASS if statuses is None else statuses),
        deployer=deployer,
        secret=SECRET,
    )


# ---- CI confirmation ------------------------------------------------------


def test_ci_confirmed_when_every_gate_is_compliant() -> None:
    confirm_ci_passed(FakeReader(ALL_PASS), "m1")


@pytest.mark.parametrize(
    "statuses",
    [
        {},
        {**ALL_PASS, "regression": "violation"},
        {k: v for k, v in ALL_PASS.items() if k != "fairness_check"},
    ],
)
def test_ci_not_confirmed_when_a_gate_failed_or_is_missing(
    statuses: dict[str, str],
) -> None:
    with pytest.raises(CINotConfirmedError):
        confirm_ci_passed(FakeReader(statuses), "m1")


# ---- final verification ---------------------------------------------------


def test_final_verification_compliant() -> None:
    result = verify_against_rules([NO_PIN], {"pin_code_weight": 0.0}, "m1")
    assert result.compliant
    assert result.regulations[0].version_id == "RBI-4.1-x"
    assert len(result.regulations[0].formula_hash) == 64


def test_final_verification_violation() -> None:
    result = verify_against_rules([NO_PIN], {"pin_code_weight": 0.3}, "m1")
    assert not result.compliant
    assert result.failed_rule_ids == ["RBI-4.1"]


def test_final_verification_fails_closed_without_rules() -> None:
    assert not verify_against_rules([], {"a_weight": 1.0}, "m1").compliant


# ---- canary ---------------------------------------------------------------


@pytest.mark.asyncio
async def test_canary_promotes_when_shadow_check_passes() -> None:
    deployer = FakeDeployer()
    result = await run_canary(deployer, "m1", lambda: True)
    assert result.promoted
    assert deployer.calls == ["canary:10", "promote"]


@pytest.mark.asyncio
async def test_canary_never_promotes_when_shadow_check_fails() -> None:
    deployer = FakeDeployer()
    result = await run_canary(deployer, "m1", lambda: False)
    assert not result.promoted
    assert deployer.calls == ["canary:10", "rollback"]


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["canary", "promote"])
async def test_canary_rolls_back_when_a_deploy_step_fails(kind: str) -> None:
    deployer = FakeDeployer(
        fail_canary=kind == "canary", fail_promote=kind == "promote"
    )
    result = await run_canary(deployer, "m1", lambda: True)
    assert not result.promoted
    assert deployer.calls[-1] == "rollback"


# ---- deploy service -------------------------------------------------------


@pytest.mark.asyncio
async def test_compliant_model_gets_certificate_lineage_and_is_promoted(
    tmp_path: Path,
) -> None:
    make_bundle(tmp_path, {"pin_code_weight": 0.0, "income_weight": 0.4})
    graph, store, deployer = FakeGraph([NO_PIN]), MemoryStore(), FakeDeployer()
    outcome = await run_deploy(tmp_path, graph, store, deployer)
    assert outcome.certificate.model_version == "m1"
    assert [r.version_id for r in outcome.certificate.regulation_versions] == [
        "RBI-4.1-x"
    ]
    assert graph.lineage == ["m1"]
    assert deployer.calls == ["canary:10", "promote"]


@pytest.mark.asyncio
async def test_second_deploy_of_same_model_and_rules_is_a_conflict(
    tmp_path: Path,
) -> None:
    make_bundle(tmp_path, {"pin_code_weight": 0.0})
    graph, store = FakeGraph([NO_PIN]), MemoryStore()
    await run_deploy(tmp_path, graph, store, FakeDeployer())
    second = FakeDeployer()
    with pytest.raises(DuplicateCertificateError):
        await run_deploy(tmp_path, graph, store, second)
    assert second.calls == []
    assert len(store.rows) == 1


@pytest.mark.asyncio
async def test_deploy_refused_when_ci_has_not_passed(tmp_path: Path) -> None:
    make_bundle(tmp_path, {"pin_code_weight": 0.0})
    store, deployer = MemoryStore(), FakeDeployer()
    with pytest.raises(CINotConfirmedError):
        await run_deploy(tmp_path, FakeGraph([NO_PIN]), store, deployer, statuses={})
    assert store.rows == {} and deployer.calls == []


@pytest.mark.asyncio
async def test_violating_model_gets_no_certificate_and_is_not_deployed(
    tmp_path: Path,
) -> None:
    make_bundle(tmp_path, {"pin_code_weight": 0.3})
    store, deployer = MemoryStore(), FakeDeployer()
    with pytest.raises(VerificationFailedError):
        await run_deploy(tmp_path, FakeGraph([NO_PIN]), store, deployer)
    assert store.rows == {} and deployer.calls == []


@pytest.mark.asyncio
async def test_regulation_change_during_canary_blocks_promotion(
    tmp_path: Path,
) -> None:
    make_bundle(tmp_path, {"pin_code_weight": 0.0, "income_weight": 0.4})
    # First fetch sees one rule; the shadow check later sees two.
    graph = FakeGraph([NO_PIN], [NO_PIN, NEW_RULE])
    deployer = FakeDeployer()
    with pytest.raises(DeploymentFailedError):
        await run_deploy(tmp_path, graph, MemoryStore(), deployer)
    assert "promote" not in deployer.calls
    assert deployer.calls[-1] == "rollback"


# ---- Railway deployer (API shape not verified against a live project) -----


def railway(handler: Any) -> RailwayDeployer:
    return RailwayDeployer(
        httpx.AsyncClient(transport=httpx.MockTransport(handler)),
        token="t",
        project_id="p",
        environment_id="e",
        service_id="main",
        canary_service_id="canary",
    )


@pytest.mark.asyncio
async def test_railway_canary_sets_version_and_redeploys_canary_service() -> None:
    seen: list[dict[str, Any]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        seen.append(body)
        return httpx.Response(200, json=OLD_VERSION_REPLY)

    await railway(handler).deploy_canary("m2", 10)
    mutations = [b["variables"] for b in seen[1:]]
    assert mutations[0]["i"]["serviceId"] == "canary"
    assert mutations[0]["i"]["value"] == "m2"
    assert mutations[-1] == {"s": "canary", "e": "e"}


@pytest.mark.asyncio
async def test_railway_rollback_restores_previous_version() -> None:
    values: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        variables = json.loads(request.content)["variables"]
        if "i" in variables and variables["i"]["serviceId"] == "main":
            values.append(variables["i"]["value"])
        return httpx.Response(200, json=OLD_VERSION_REPLY)

    deployer = railway(handler)
    await deployer.deploy_canary("m2", 10)
    await deployer.rollback()
    assert values[0] == "old"


@pytest.mark.asyncio
async def test_railway_errors_become_deploy_errors() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"errors": [{"message": "nope"}]})

    with pytest.raises(DeployError):
        await railway(handler).promote("m2")


def test_railway_requires_configuration(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("RAILWAY_API_TOKEN", raising=False)
    with pytest.raises(DeployError):
        RailwayDeployer()
