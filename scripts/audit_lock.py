"""Audit every package pinned in poetry.lock (all groups) for known vulnerabilities.

    poetry run python scripts/audit_lock.py

Checks the lock file, not the current environment, so optional groups such as
`ct` are covered too. Exits non-zero if any advisory is found that is not listed
in ACCEPTED below. Every accepted advisory needs a written reason.
"""

import json
import subprocess  # nosec B404
import sys
import tempfile
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# advisory id -> why it is accepted. Keep this list short and review it often.
ACCEPTED: dict[str, str] = {
    # The three below are only in the optional `ct` group (the GitHub Actions
    # training job). They are not installed in the deployed API. Fixes are
    # blocked by MLflow's own version caps, so revisit when MLflow 3.x moves.
    "PYSEC-2026-3552": "cryptography 49.0.0; fix is 50.0.0 but mlflow 3.15.0 requires <50",
    "PYSEC-2026-113": "pyarrow 19.0.1; fix is 23.0.1 but mlflow 3.15.0 limits pyarrow",
    "PYSEC-2026-3865": "mlflow 3.15.0; no fixed release exists yet",
}


def locked_requirements() -> list[str]:
    """One pin per package. The lock can hold several versions of a package for
    different Python versions; pip-audit rejects duplicates, so the newest wins."""
    lock = tomllib.loads((ROOT / "poetry.lock").read_text(encoding="utf-8"))
    newest: dict[str, str] = {}
    for p in lock["package"]:
        key = p["name"].lower()
        current = newest.get(key)
        if current is None or _version_key(p["version"]) > _version_key(current):
            newest[key] = p["version"]
    return sorted(f"{name}=={version}" for name, version in newest.items())


def _version_key(version: str) -> tuple[int, ...]:
    return tuple(int(part) for part in version.split(".") if part.isdigit())


def main() -> int:
    with tempfile.TemporaryDirectory() as folder:
        requirements = Path(folder) / "requirements.txt"
        requirements.write_text("\n".join(locked_requirements()) + "\n")
        done = subprocess.run(  # nosec B603
            [
                sys.executable, "-m", "pip_audit", "-r", str(requirements),
                "--no-deps", "--disable-pip", "-f", "json",
            ],
            capture_output=True,
            text=True,
        )
    # pip-audit exits 0 (clean) or 1 (vulnerabilities). Anything else, or no
    # report, means the audit did not run, which must never look like "clean".
    if done.returncode not in (0, 1) or not done.stdout.strip():
        sys.stderr.write(f"pip-audit did not run:\n{done.stderr[-800:]}\n")
        return 2
    report = json.loads(done.stdout)
    findings = []
    for dependency in report.get("dependencies", []):
        for vuln in dependency.get("vulns", []):
            if vuln["id"] not in ACCEPTED:
                fixes = ", ".join(vuln.get("fix_versions", [])) or "no fix yet"
                findings.append(
                    f"{dependency['name']} {dependency['version']}: {vuln['id']} (fixed in {fixes})"
                )
    for line in sorted(set(findings)):
        sys.stdout.write(line + "\n")
    sys.stdout.write(f"{len(set(findings))} unaccepted advisories\n")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
