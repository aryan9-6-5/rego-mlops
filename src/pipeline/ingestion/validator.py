import hashlib
import logging
import re
import time
from dataclasses import dataclass

import z3

from src.api.schemas.regulation import RegulationStatus

logger = logging.getLogger(__name__)

MAX_FORMULA_CHARS = 5000
SOLVER_TIMEOUT_MS = 5000
ALLOWED_COMMANDS = frozenset({"declare-const", "declare-fun", "define-fun", "assert"})
_FORBIDDEN_CHARS = re.compile(r'["|;]')


@dataclass(frozen=True)
class ValidationResult:
    status: RegulationStatus  # Z3_VALIDATED or Z3_REJECTED
    reason: str | None
    formula_hash: str
    duration_ms: float


def hash_formula(formula: str) -> str:
    return hashlib.sha256(formula.encode()).hexdigest()


def _top_level_commands(formula: str) -> list[str] | None:
    """Return the command symbol of each top-level s-expression, or None if
    the parentheses are unbalanced."""
    depth = 0
    commands: list[str] = []
    for match in re.finditer(r"\(\s*([^\s()]+)|[()]", formula):
        token = match.group(0)
        if token == ")":  # nosec B105
            depth -= 1
            if depth < 0:
                return None
        else:
            if depth == 0 and match.group(1):
                commands.append(match.group(1))
            depth += 1
    return commands if depth == 0 else None


def _check(formula: str) -> str | None:
    """Return a rejection reason, or None if the formula is well-formed."""
    if len(formula) > MAX_FORMULA_CHARS:
        return "The rule is too long to be valid."
    if _FORBIDDEN_CHARS.search(formula):
        return "The rule contains characters that are not allowed."
    commands = _top_level_commands(formula)
    if commands is None:
        return "The rule is incomplete."
    if not commands:
        return "The rule is empty."
    disallowed = sorted({c for c in commands if c not in ALLOWED_COMMANDS})
    if disallowed:
        return "The rule uses features that are not allowed."
    # Fresh context per call: one failed parse poisons the shared global
    # context, making every later (valid) formula fail until restart.
    ctx = z3.Context()
    try:
        assertions = z3.parse_smt2_string(formula, ctx=ctx)
    except z3.Z3Exception as e:
        # Raw Z3 text is for logs only; the CO sees a plain-English reason.
        logger.warning("Z3 parse error detail=%s", str(e).strip()[:200])
        return "The rule is not logically well-formed."
    if len(assertions) == 0:
        return "The rule does not state any condition."
    for assertion in assertions:
        simplified = z3.simplify(assertion)
        if z3.is_true(simplified):
            return "The rule is always true, so it would not restrict anything."
        if z3.is_false(simplified):
            return "The rule can never be met, so no model could comply."
    solver = z3.Solver(ctx=ctx)
    solver.set("timeout", SOLVER_TIMEOUT_MS)
    solver.add(assertions)
    verdict = solver.check()
    if verdict == z3.unsat:
        return "The rule contradicts itself, so no model could comply."
    if verdict == z3.unknown:
        return "The rule could not be checked."
    return None


def validate(formula: str) -> ValidationResult:
    """Z3 well-formedness check. Malformed formulas never reach the approval queue.

    Checks structure only. Whether the formula captures the regulation's intent
    is a human decision.
    """
    started = time.perf_counter()
    try:
        reason = _check(formula)
    except Exception as e:  # defensive: Z3 must never crash the pipeline
        logger.error("Z3 validation error error=%s", type(e).__name__)
        reason = "Unexpected error while validating the formula."
    duration_ms = (time.perf_counter() - started) * 1000
    formula_hash = hash_formula(formula)
    status = (
        RegulationStatus.Z3_REJECTED if reason else RegulationStatus.Z3_VALIDATED
    )
    logger.info(
        "Z3 validation complete formula_hash=%s result=%s duration_ms=%.1f",
        formula_hash,
        "REJECTED" if reason else "SAT",
        duration_ms,
    )
    return ValidationResult(status, reason, formula_hash, duration_ms)
