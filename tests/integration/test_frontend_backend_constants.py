"""The frontend's status constants must equal the backend enums exactly
(AIRULES Rule 14), so a rename on one side fails here instead of silently
breaking a status display."""

import re
from pathlib import Path

from src.api.schemas.pipeline import GateName, GateStatus
from src.api.schemas.regulation import RegulationStatus

CONSTANTS = (
    Path(__file__).resolve().parents[2] / "frontend" / "src" / "lib" / "utils" / "constants.ts"
).read_text(encoding="utf-8")


def ts_values(name: str) -> set[str]:
    block = re.search(rf"export const {name} = \{{(.*?)\}} as const;", CONSTANTS, re.DOTALL)
    assert block, f"{name} not found in constants.ts"
    return set(re.findall(r":\s*'([^']+)'", block.group(1)))


def test_regulation_status_values_match() -> None:
    assert ts_values("REGULATION_STATUS") == {s.value for s in RegulationStatus}


def test_gate_names_match() -> None:
    assert ts_values("GATE_NAME") == {g.value for g in GateName}


def test_gate_statuses_match() -> None:
    assert ts_values("GATE_STATUS") == {s.value for s in GateStatus}


def test_regulation_statuses_match_the_database_enum() -> None:
    migrations = Path(__file__).resolve().parents[2] / "supabase" / "migrations"
    sql = (migrations / "02_regulations.sql").read_text(encoding="utf-8")
    declared = set(re.findall(r"'([a-z_0-9]+)'", sql.split("CREATE TYPE regulation_status AS ENUM (")[1].split(");")[0]))
    added = {
        m.group(1)
        for f in migrations.glob("*.sql")
        for m in re.finditer(r"ADD VALUE IF NOT EXISTS '([a-z_]+)'", f.read_text(encoding="utf-8"))
    }
    assert declared | added == {s.value for s in RegulationStatus}
