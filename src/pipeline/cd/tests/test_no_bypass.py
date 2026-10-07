"""Structural checks for the "Error Prevention" principle: a model cannot reach
the deployer except through the compliance-gated flow."""

import ast
from pathlib import Path

SRC = Path(__file__).resolve().parents[3]
DEPLOYER_CALLS = {"deploy_canary", "promote", "rollback"}
BYPASS_WORDS = ("force", "bypass", "override", "skip_ci", "skip_gate", "no_verify")


def python_files() -> list[Path]:
    return [p for p in SRC.rglob("*.py") if "tests" not in p.parts]


def test_only_the_canary_calls_the_deployer() -> None:
    allowed = SRC / "pipeline" / "cd" / "canary.py"
    offenders = []
    for path in python_files():
        if path == allowed or path.name == "deployer.py":
            continue
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr in DEPLOYER_CALLS
            ):
                offenders.append(f"{path.relative_to(SRC)}:{node.lineno}")
    assert offenders == []


def test_no_deploy_function_takes_a_bypass_argument() -> None:
    paths = [
        *(SRC / "pipeline" / "cd").glob("*.py"),
        SRC / "api" / "routes" / "pipeline.py",
        SRC / "api" / "schemas" / "certificate.py",
    ]
    offenders = []
    for path in paths:
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                args = [a.arg for a in node.args.args + node.args.kwonlyargs]
                for arg in args:
                    if any(word in arg.lower() for word in BYPASS_WORDS):
                        offenders.append(f"{path.name}:{node.name}({arg})")
            if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                if any(word in node.target.id.lower() for word in BYPASS_WORDS):
                    offenders.append(f"{path.name}:{node.target.id}")
    assert offenders == []


def test_the_deploy_flow_runs_its_steps_in_the_fixed_order() -> None:
    source = (SRC / "pipeline" / "cd" / "service.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    function = next(
        n
        for n in ast.walk(tree)
        if isinstance(n, ast.AsyncFunctionDef) and n.name == "deploy_model"
    )
    steps = ("confirm_ci_passed", "verify_against_rules", "issue_certificate", "run_canary")
    first_use: dict[str, int] = {}
    for node in ast.walk(function):
        if isinstance(node, ast.Name) and node.id in steps:
            first_use[node.id] = min(first_use.get(node.id, node.lineno), node.lineno)
    assert set(first_use) == set(steps)
    ordered = sorted(steps, key=lambda step: first_use[step])
    assert ordered == list(steps)
