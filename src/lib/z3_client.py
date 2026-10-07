import hashlib
import logging
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from fractions import Fraction

import z3

logger = logging.getLogger(__name__)

SOLVER_TIMEOUT_MS = 5000
Value = float | int | bool


class Z3ClientError(Exception):
    """Raised when a formula cannot be parsed or solved."""


@dataclass(frozen=True)
class ProofResult:
    """`compliant` is True only when Z3 proves the rule holds (UNSAT of its
    negation). SAT and UNKNOWN both mean not compliant."""

    compliant: bool
    verdict: str  # "UNSAT" | "SAT" | "UNKNOWN"
    formula_hash: str
    duration_ms: float
    counterexample: dict[str, str] | None


def hash_formula(formula: str) -> str:
    return hashlib.sha256(formula.encode()).hexdigest()


def _parse(formula: str) -> tuple[z3.Context, z3.AstVector]:
    """Parse in a fresh context: after one failed parse the shared global
    context rejects every later formula until the process restarts."""
    ctx = z3.Context()
    try:
        return ctx, z3.parse_smt2_string(formula, ctx=ctx)
    except z3.Z3Exception as e:
        raise Z3ClientError("Formula could not be parsed.") from e


def _free_constants(assertions: Sequence[z3.ExprRef]) -> dict[str, z3.ExprRef]:
    """Uninterpreted constants (the rule's feature variables), by name."""
    found: dict[str, z3.ExprRef] = {}
    seen: set[int] = set()
    stack = list(assertions)
    while stack:
        expr = stack.pop()
        if expr.get_id() in seen:
            continue
        seen.add(expr.get_id())
        if z3.is_const(expr) and expr.decl().kind() == z3.Z3_OP_UNINTERPRETED:
            found[str(expr)] = expr
        stack.extend(expr.children())
    return found


def _value_for(const: z3.ExprRef, value: Value) -> z3.ExprRef:
    ctx = const.ctx
    if z3.is_bool(const):
        return z3.BoolVal(bool(value), ctx)
    if z3.is_int(const):
        return z3.IntVal(int(value), ctx)
    fraction = Fraction(repr(float(value)))
    return z3.RealVal(f"{fraction.numerator}/{fraction.denominator}", ctx)


def prove(
    formula: str,
    constraints: Mapping[str, Value],
    *,
    rule_ids: Sequence[str] = (),
    model_version: str | None = None,
) -> ProofResult:
    """Does a model with these feature values satisfy the rule?

    `formula` is the SMT-LIB2 rule (the condition a compliant model must meet).
    `constraints` maps variable names to the model's values. A variable the
    model does not mention is treated as absent: 0 (or False). Z3 searches for a
    way the rule can be false under those values: UNSAT proves compliance,
    SAT yields a counterexample.
    """
    started = time.perf_counter()
    ctx, assertions = _parse(formula)
    constants = _free_constants(list(assertions))
    solver = z3.Solver(ctx=ctx)
    solver.set("timeout", SOLVER_TIMEOUT_MS)
    for name, const in constants.items():
        solver.add(const == _value_for(const, constraints.get(name, 0)))
    solver.add(z3.Not(z3.And(*assertions)))
    try:
        outcome = solver.check()
    except z3.Z3Exception as e:
        raise Z3ClientError("Z3 failed while checking the rule.") from e

    counterexample: dict[str, str] | None = None
    if outcome == z3.sat:
        verdict = "SAT"
        z3_model = solver.model()
        counterexample = {
            name: str(z3_model.eval(const, model_completion=True))
            for name, const in constants.items()
        }
    elif outcome == z3.unsat:
        verdict = "UNSAT"
    else:
        verdict = "UNKNOWN"

    duration_ms = (time.perf_counter() - started) * 1000
    formula_hash = hash_formula(formula)
    logger.info(
        "Z3 check complete formula_hash=%s result=%s duration_ms=%.1f "
        "rules_checked=%s model_version=%s",
        formula_hash,
        verdict,
        duration_ms,
        list(rule_ids),
        model_version,
    )
    return ProofResult(
        compliant=verdict == "UNSAT",
        verdict=verdict,
        formula_hash=formula_hash,
        duration_ms=duration_ms,
        counterexample=counterexample,
    )


def counterexample(
    formula: str,
    constraints: Mapping[str, Value],
    *,
    rule_ids: Sequence[str] = (),
    model_version: str | None = None,
) -> dict[str, str] | None:
    """The violating variable assignment, or None if the model complies."""
    return prove(
        formula, constraints, rule_ids=rule_ids, model_version=model_version
    ).counterexample


def forced_zero_variables(formula: str) -> list[str]:
    """Variables the rule forces to exactly zero (the prohibited features)."""
    ctx, assertions = _parse(formula)
    forced: list[str] = []
    for name, const in sorted(_free_constants(list(assertions)).items()):
        if z3.is_bool(const):
            continue
        solver = z3.Solver(ctx=ctx)
        solver.set("timeout", SOLVER_TIMEOUT_MS)
        solver.add(*assertions)
        solver.add(const != 0)
        if solver.check() == z3.unsat:
            forced.append(name)
    logger.info(
        "Z3 forced-zero analysis formula_hash=%s result=%s",
        hash_formula(formula),
        forced,
    )
    return forced


def rule_variables(formula: str) -> list[str]:
    """Names of the feature variables a rule talks about."""
    _, assertions = _parse(formula)
    return sorted(_free_constants(list(assertions)))
