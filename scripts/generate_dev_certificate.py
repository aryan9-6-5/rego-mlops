"""Generate a signed test certificate for UI development.

Default: build the certificate in memory and write it as JSON to stdout. No
database, no pipeline run.

    python scripts/generate_dev_certificate.py > dev_certificate.json
    python scripts/generate_dev_certificate.py --insert   # also write to Supabase

`--insert` goes through the same write-once path as a real deployment
(pipeline/cd/certificate.py) and is refused when ENVIRONMENT=production.
The model version is always `dev-<timestamp>` so it cannot be mistaken for a
real one. Needs PROOF_CERT_SECRET (at least 32 bytes).
"""

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from src.api.schemas.certificate import CertificateRegulation  # noqa: E402
from src.pipeline.cd.certificate import issue_certificate  # noqa: E402

SAMPLE_FORMULA = "(declare-const pin_code_weight Real)(assert (= pin_code_weight 0))"


class MemoryStore:
    def __init__(self) -> None:
        self.row: dict[str, Any] = {}

    def insert(self, row: dict[str, Any]) -> dict[str, Any]:
        self.row = {**row, "created_at": datetime.now(timezone.utc).isoformat()}
        return dict(self.row)

    def get(self, certificate_id: str) -> dict[str, Any] | None:
        return self.row or None

    def list_latest(self) -> list[dict[str, Any]]:
        return [self.row] if self.row else []


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--insert", action="store_true")
    args = parser.parse_args()

    secret = os.environ.get("PROOF_CERT_SECRET", "")
    if not secret:
        sys.stderr.write("PROOF_CERT_SECRET must be set.\n")
        return 1
    if args.insert and os.environ.get("ENVIRONMENT") == "production":
        sys.stderr.write("Refusing to insert a dev certificate in production.\n")
        return 1

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    model_version = f"dev-{stamp}"
    regulation = CertificateRegulation(
        version_id=f"RBI-4.1-{stamp}",
        rule_id="RBI-4.1",
        formula_hash=hashlib.sha256(SAMPLE_FORMULA.encode()).hexdigest(),
    )

    if args.insert:
        from src.lib.supabase_client import supabase_client
        from src.pipeline.cd.stores import SupabaseCertificateStore

        store: Any = SupabaseCertificateStore(supabase_client.client)
    else:
        store = MemoryStore()

    certificate = issue_certificate(
        store,
        secret,
        model_version=model_version,
        bundle_digest=hashlib.sha256(model_version.encode()).hexdigest(),
        regulations=[regulation],
    )
    sys.stdout.write(json.dumps(certificate.model_dump(mode="json"), indent=2) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
