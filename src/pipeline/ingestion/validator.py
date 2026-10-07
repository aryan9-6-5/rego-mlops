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
        if token == ")":
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
        return f"Formula exceeds {MAX_FORMULA_CHARS} characters."
    if _FORBIDDEN_CHARS.search(formula):
        return "Formula contains quoted symbols, strings or comments."
    commands = _top_level_commands(formula)
    if commands is None:
        return "Formula has unbalanced parentheses."
    if not commands:
        return "Formula contains no commands."
    disallowed = sorted({c for c in commands if c not in ALLOWED_COMMANDS})
    if disallowed:
        return f"Formula uses disallowed commands: {', '.join(disallowed)}."
    try:
        assertions = z3.parse_smt2_string(formula)
    except z3.Z3Exception as e:
        return f"Z3 could not parse the formula: {str(e).strip()[:200]}"
    if len(assertions) == 0:
        return "Formula contains no assertions."
    for assertion in assertions:
        simplified = z3.simplify(assertion)
        if z3.is_true(simplified):
            return "An assertion is always true, so it constrains nothing."
        if z3.is_false(simplified):
            return "An assertion is always false, so no model can comply."
    solver = z3.Solver()
    solver.set("timeout", SOLVER_TIMEOUT_MS)
    solver.add(assertions)
    verdict = solver.check()
    if verdict == z3.unsat:
        return "The assertions contradict each other, so no model can comply."
    if verdict == z3.unknown:
        return "Z3 could not decide whether the rule is satisfiable."
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
