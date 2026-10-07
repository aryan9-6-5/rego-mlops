"""Queue three sample RBI provisions for human review.

    poetry run python scripts/seed_rbi_rules.py

Creates three rules from the RBI Digital Lending Directions, 2025 (see
scripts/rbi_digital_lending_2025.py) in the `regulations` table, each checked by Z3
and left at `pending_approval`. A compliance officer then approves or rejects them
in the app, exactly as for a pasted regulation. This script never activates a rule
and never writes to Neo4j: a rule enters the pipeline only after a human approves
it. It skips a rule that is already queued or active.

Needs SUPABASE_URL and SUPABASE_SERVICE_KEY. Run it against the project you mean
to use.

This replaces an earlier version that seeded a "no PIN code" rule labelled as RBI
section 4.1. That text is not in the Directions.
"""

import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from rbi_digital_lending_2025 import PROVISIONS  # noqa: E402

from src.api.schemas.regulation import RegulationStatus  # noqa: E402
from src.pipeline.ingestion.approver import transition  # noqa: E402
from src.pipeline.ingestion.validator import validate  # noqa: E402
from src.pipeline.ingestion.versioner import new_version  # noqa: E402

S = RegulationStatus
ALREADY_PRESENT = [
    S.PENDING_APPROVAL.value,
    S.APPROVED.value,
    S.ACTIVE.value,
]


def seed(store: Any) -> list[tuple[str, str]]:
    """Queue each provision. Returns (rule_id, outcome) for each."""
    present = {row["rule_id"] for row in store.list_by_status(ALREADY_PRESENT)}
    results = []
    version = new_version()
    for section, (text, description, formula) in PROVISIONS.items():
        rule_id = f"RBI-{section}"
        if rule_id in present:
            results.append((rule_id, "skipped, already queued or active"))
            continue
        check = validate(formula)
        if check.status is not S.Z3_VALIDATED:
            # A bad built-in rule is a bug in this file, not something to queue.
            raise ValueError(f"{rule_id} failed validation: {check.reason}")
        row = store.insert(
            {
                "rule_id": rule_id,
                "jurisdiction": "India",
                "source_text": text,
                "description": description,
                "formal_logic": formula,
                "status": S.EXTRACTED.value,
                "version": version,
            }
        )
        validated = transition(S.EXTRACTED, check.status)
        queued = transition(validated, S.PENDING_APPROVAL)
        store.update(row["id"], {"status": queued.value})
        results.append((rule_id, "queued for review"))
    return results


def main() -> int:
    import os

    if not os.environ.get("SUPABASE_URL") or not os.environ.get("SUPABASE_SERVICE_KEY"):
        sys.stderr.write("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set.\n")
        return 1
    from src.lib.supabase_client import supabase_client
    from src.pipeline.ingestion.store import SupabaseRegulationStore

    store = SupabaseRegulationStore(supabase_client.client)
    for rule_id, outcome in seed(store):
        sys.stdout.write(f"{rule_id}: {outcome}\n")
    sys.stdout.write("Open the approval queue to review them. Nothing is active yet.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
