"""The demo scripts do what the demo guide says they do."""

import importlib.util
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

from src.lib.model_bundle import load_submission
from src.lib.regulation_graph import ActiveRule
from src.pipeline.ci import fairness_check, reg_attack, regression, symbolic_check

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"


def load(name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(f"script_{name}", SCRIPTS / f"{name}.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# The three demo rules, as the offline demo and docs/DEMO.md define them.
RULES = [
    ActiveRule(
        "RBI-12.1-x", "RBI-12.1",
        "(declare-const contact_list_weight Real)(declare-const call_logs_weight Real)"
        "(declare-const media_files_weight Real)"
        "(assert (and (= contact_list_weight 0) (= call_logs_weight 0) (= media_files_weight 0)))",
    ),
    ActiveRule("RBI-13.3-x", "RBI-13.3", "(declare-const biometric_weight Real)(assert (= biometric_weight 0))"),
    ActiveRule(
        "RBI-7.1-x", "RBI-7.1",
        "(declare-const age_weight Real)(declare-const occupation_weight Real)"
        "(declare-const income_weight Real)"
        "(assert (and (> age_weight 0) (> occupation_weight 0) (> income_weight 0)))",
    ),
]


@pytest.fixture
def bundles(tmp_path: Path) -> Path:
    load("make_demo_models").write_bundles(tmp_path)
    return tmp_path


def gates(base: Path, name: str) -> dict[str, str]:
    submission = load_submission(name, base)
    results = [
        symbolic_check.check_rules(RULES, submission),
        reg_attack.check_rules(RULES, submission),
        fairness_check.run(submission),
        regression.run(submission),
    ]
    return {r.gate.value: r.status.value for r in results}


def test_the_compliant_bundle_passes_every_gate(bundles: Path) -> None:
    assert set(gates(bundles, "demo-compliant").values()) == {"compliant"}


@pytest.mark.parametrize(
    ("name", "failing_gate"),
    [
        ("demo-contact-list", "symbolic_check"),
        ("demo-biometric", "symbolic_check"),
        ("demo-no-income", "symbolic_check"),
        ("demo-unfair", "fairness_check"),
    ],
)
def test_each_violating_bundle_fails_the_gate_the_guide_says(
    bundles: Path, name: str, failing_gate: str
) -> None:
    result = gates(bundles, name)
    assert result[failing_gate] == "violation", result


def test_the_unfair_bundle_passes_the_rule_gates(bundles: Path) -> None:
    result = gates(bundles, "demo-unfair")
    assert result["symbolic_check"] == result["reg_attack"] == "compliant"


class FakeAdmin:
    def __init__(self) -> None:
        self.created: list[dict[str, Any]] = []

    def create_user(self, attributes: dict[str, Any]) -> Any:
        self.created.append(attributes)
        user = type("User", (), {})()
        user.id = f"id-{len(self.created)}"
        return type("Response", (), {"user": user})()


class FakeClient:
    def __init__(self) -> None:
        self.auth = type("Auth", (), {"admin": FakeAdmin()})()
        self.rows: list[dict[str, Any]] = []

    def table(self, name: str) -> "FakeClient":
        assert name == "users"
        return self

    def insert(self, row: dict[str, Any]) -> "FakeClient":
        self.rows.append(row)
        return self

    def execute(self) -> None:
        return None


def test_demo_accounts_get_the_right_roles_in_auth_and_in_the_users_table() -> None:
    client = FakeClient()
    created = load("create_demo_users").create_accounts(client, None)
    assert [(e, r) for e, r, _ in created] == [
        ("demo-co@rego.dev", "compliance_officer"),
        ("demo-mle@rego.dev", "ml_engineer"),
    ]
    assert [row["role"] for row in client.rows] == ["compliance_officer", "ml_engineer"]
    assert [row["id"] for row in client.rows] == ["id-1", "id-2"]
    assert all(a["email_confirm"] is True for a in client.auth.admin.created)


def test_demo_passwords_are_random_and_different_unless_one_is_chosen() -> None:
    random = load("create_demo_users").create_accounts(FakeClient(), None)
    assert random[0][2] != random[1][2] and len(random[0][2]) >= 16
    chosen = load("create_demo_users").create_accounts(FakeClient(), "a-long-demo-password")
    assert {p for _e, _r, p in chosen} == {"a-long-demo-password"}


def test_a_short_chosen_password_is_refused() -> None:
    with pytest.raises(ValueError):
        load("create_demo_users").create_accounts(FakeClient(), "short")


def test_no_password_is_written_in_the_script() -> None:
    source = (SCRIPTS / "create_demo_users.py").read_text(encoding="utf-8")
    assert "password=" not in source.replace('"password": password', "")


# ---- the seed script queues rules for review and never activates them ---------


def test_the_seed_script_queues_three_rules_checked_by_z3_and_activates_none() -> None:
    from tests.integration.world import StatefulRegulationStore

    store = StatefulRegulationStore()
    results = load("seed_rbi_rules").seed(store)
    assert [r for r, _ in results] == ["RBI-12.1", "RBI-13.3", "RBI-7.1"]
    rows = list(store.rows.values())
    assert {r["status"] for r in rows} == {"pending_approval"}
    assert all(r["description"] and r["source_text"] and r["formal_logic"] for r in rows)
    assert {r["version"] for r in rows} == {rows[0]["version"]}


def test_running_the_seed_script_twice_does_not_duplicate_rules() -> None:
    from tests.integration.world import StatefulRegulationStore

    store = StatefulRegulationStore()
    seed = load("seed_rbi_rules").seed
    seed(store)
    second = seed(store)
    assert len(store.rows) == 3
    assert all("skipped" in outcome for _r, outcome in second)


def test_the_seed_script_only_writes_pending_rows_never_active_ones_or_the_graph() -> None:
    source = (SCRIPTS / "seed_rbi_rules.py").read_text(encoding="utf-8")
    assert "neo4j" not in source.lower().replace("never writes to neo4j", "")
    assert "S.ACTIVE" not in source.replace("S.ACTIVE.value,\n]", "")  # only in the skip list


def test_the_provisions_are_real_quotes_and_each_rule_is_valid_z3() -> None:
    from src.api.schemas.regulation import RegulationStatus
    from src.pipeline.ingestion.validator import validate

    provisions = load("rbi_digital_lending_2025").PROVISIONS
    assert set(provisions) == {"12.1", "13.3", "7.1"}
    for section, (text, description, formula) in provisions.items():
        assert validate(formula).status is RegulationStatus.Z3_VALIDATED, section
        assert description and text.startswith("RE shall")


def test_no_invented_pin_code_rule_is_presented_as_an_rbi_provision() -> None:
    for name in ("seed_rbi_rules.py", "poc_pipeline.py", "demo_offline.py", "rbi_digital_lending_2025.py"):
        text = (SCRIPTS / name).read_text(encoding="utf-8").lower()
        assert "pin_code" not in text and "pin code" not in text.replace("no pin code", ""), name
