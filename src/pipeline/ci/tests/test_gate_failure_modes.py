"""Gates fail closed on rules they cannot read."""

from typing import Any

from src.lib.regulation_graph import ActiveRule
from src.lib.z3_client import Z3ClientError
from src.pipeline.cd.verification import verify_against_rules
from src.pipeline.ci import reg_attack, symbolic_check
from src.pipeline.ci.tests.conftest import INCOME_CAP, NO_PIN, make_submission

BROKEN = ActiveRule("RBI-9-x", "RBI-9", "(assert (= nope")


class Graph:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self.rows = rows

    def run_query(
        self, query: str, params: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        return self.rows


def test_symbolic_check_run_reads_the_rules_from_the_graph() -> None:
    rows = [
        {
            "version_id": NO_PIN.version_id,
            "rule_id": NO_PIN.rule_id,
            "formal_logic": NO_PIN.formal_logic,
            "section": "4.1",
            "description": None,
        }
    ]
    ok = symbolic_check.run(Graph(rows), make_submission({"pin_code_weight": 0.0}))
    assert ok.status.value == "compliant"
    bad = symbolic_check.run(Graph(rows), make_submission({"pin_code_weight": 0.3}))
    assert bad.status.value == "violation"


def test_reg_attack_skips_a_rule_it_cannot_parse_and_leaves_it_to_the_symbolic_gate() -> None:
    result = reg_attack.check_rules([BROKEN], make_submission({"a_weight": 1.0}))
    assert result.status.value == "compliant"
    assert symbolic_check.check_rules([BROKEN], make_submission({"a_weight": 1.0})).status.value == "violation"


def test_reg_attack_ignores_boolean_features() -> None:
    rule = ActiveRule("RBI-2-x", "RBI-2", "(declare-const flag Bool)(assert (not flag))")
    assert reg_attack.check_rules([rule], make_submission({"flag": False})).status.value == "compliant"


def test_reg_attack_treats_a_rule_that_breaks_during_a_nudge_as_fragile(
    monkeypatch: Any,
) -> None:
    calls = {"n": 0}
    real = reg_attack.prove  # type: ignore[attr-defined]

    def flaky(formula: str, weights: Any, **kw: Any) -> Any:
        calls["n"] += 1
        if calls["n"] > 1:  # the first call is the baseline check
            raise Z3ClientError("boom")
        return real(formula, weights, **kw)

    monkeypatch.setattr("src.pipeline.ci.reg_attack.prove", flaky)
    result = reg_attack.check_rules([INCOME_CAP], make_submission({"income_weight": 0.4}))
    assert result.status.value == "violation"


def test_final_verification_fails_closed_on_an_unreadable_rule() -> None:
    result = verify_against_rules([BROKEN], {"a_weight": 1.0}, "m1")
    assert result.compliant is False
    assert result.failed_rule_ids == ["RBI-9"]


def test_final_verification_fails_when_one_of_several_rules_is_unreadable() -> None:
    result = verify_against_rules([NO_PIN, BROKEN], {"pin_code_weight": 0.0}, "m1")
    assert result.compliant is False
