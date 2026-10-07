"""Repository-wide checks for secrets, PII in logs and pinned crypto (Stage 4)."""

import ast
import re
from pathlib import Path

import z3

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
LOG_METHODS = {"debug", "info", "warning", "error", "exception", "critical"}
# Fields that could identify an applicant or expose a credential.
PII_WORDS = (
    "applicant", "name", "email", "phone", "pan", "aadhaar", "income", "salary",
    "address", "dob", "birth", "ssn", "password", "token", "secret", "api_key",
    "service_key",
)


def source_files() -> list[Path]:
    return [p for p in SRC.rglob("*.py") if "tests" not in p.parts]


def log_calls() -> list[tuple[Path, ast.Call]]:
    found = []
    for path in source_files():
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr in LOG_METHODS
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id in {"logger", "logging"}
            ):
                found.append((path, node))
    return found


def words(text: str) -> set[str]:
    return set(re.findall(r"[a-z_]+", text.lower()))


def test_there_are_log_calls_to_audit() -> None:
    assert len(log_calls()) > 20


def test_no_log_call_mentions_pii_or_credentials() -> None:
    offenders = []
    for path, call in log_calls():
        texts = [
            n.value
            for n in ast.walk(call)
            if isinstance(n, ast.Constant) and isinstance(n.value, str)
        ]
        names = [n.id for n in ast.walk(call) if isinstance(n, ast.Name)]
        names += [n.attr for n in ast.walk(call) if isinstance(n, ast.Attribute)]
        names += [
            n.slice.value
            for n in ast.walk(call)
            if isinstance(n, ast.Subscript)
            and isinstance(n.slice, ast.Constant)
            and isinstance(n.slice.value, str)
        ]
        seen = set().union(*(words(t) for t in texts), *(words(n) for n in names))
        hits = sorted(seen & set(PII_WORDS))
        if hits:
            offenders.append(f"{path.relative_to(ROOT)}:{call.lineno} {hits}")
    assert offenders == []


def test_no_print_in_committed_python() -> None:
    offenders = [
        f"{p.relative_to(ROOT)}:{n.lineno}"
        for p in source_files()
        for n in ast.walk(ast.parse(p.read_text(encoding="utf-8")))
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "print"
    ]
    assert offenders == []


def test_the_certificate_secret_is_only_ever_read_from_the_environment() -> None:
    literal = re.compile(r"PROOF_CERT_SECRET\s*=\s*[\"'][^\"']+[\"']")
    for path in [*source_files(), *(ROOT / "scripts").glob("*.py")]:
        assert not literal.search(path.read_text(encoding="utf-8")), path
    users = [
        p.relative_to(SRC).as_posix()
        for p in source_files()
        if "PROOF_CERT_SECRET" in p.read_text(encoding="utf-8")
    ]
    # providers.py reads it; certificate.py only names it in an error message.
    assert sorted(users) == ["api/providers.py", "pipeline/cd/certificate.py"]


def test_the_service_key_never_reaches_the_frontend() -> None:
    for path in (ROOT / "frontend" / "src").rglob("*"):
        if path.suffix in {".ts", ".tsx"}:
            assert "SERVICE_KEY" not in path.read_text(encoding="utf-8"), path
    env_example = (ROOT / ".env.example").read_text(encoding="utf-8")
    assert not re.search(r"^VITE_\w*SERVICE\w*=", env_example, re.MULTILINE)


def test_no_console_log_in_the_frontend() -> None:
    offenders = [
        str(p.relative_to(ROOT))
        for p in (ROOT / "frontend" / "src").rglob("*.ts*")
        if "console.log" in p.read_text(encoding="utf-8")
    ]
    assert offenders == []


def test_z3_is_the_pinned_version() -> None:
    assert z3.get_version_string().startswith("4.12.6")
    assert 'z3-solver = "4.12.6.0"' in (ROOT / "pyproject.toml").read_text(encoding="utf-8")
