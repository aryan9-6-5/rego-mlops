"""Walk through Rego end to end with no accounts and no network.

    poetry run python scripts/demo_offline.py

It runs the real API and the real Z3 solver. Only the outside services are
replaced: Neo4j, Supabase and Railway are in-memory stand-ins, and the LLM is
scripted so the output is repeatable. Three real provisions of the RBI Digital
Lending Directions, 2025 are used (see docs/DEMO.md).
"""

import json
import os
import sys
import tempfile
import time
import types
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ["FRONTEND_DIST"] = "/nonexistent"  # the API only

sys.path.insert(0, str(ROOT / "scripts"))

from rbi_digital_lending_2025 import PROVISIONS  # noqa: E402
from tests.integration import fakes  # noqa: E402

_supabase = types.ModuleType("src.lib.supabase_client")
_supabase.supabase_client = fakes.FakeSupabase()  # type: ignore[attr-defined]
sys.modules["src.lib.supabase_client"] = _supabase

from fastapi.testclient import TestClient  # noqa: E402

from src.api import providers  # noqa: E402
from src.api.main import app  # noqa: E402
from src.lib.model_bundle import LocalBundleSource  # noqa: E402
from tests.integration.world import World  # noqa: E402

CO = {"Authorization": "Bearer co-token"}
MLE = {"Authorization": "Bearer mle-token"}
SECRET = "offline-demo-secret-" + "x" * 32

class DemoLLM:
    """Stands in for the real model: returns the formula for the section asked."""

    async def complete(self, system: str, user: str) -> str:
        section = user.split("Section: ", 1)[1].split("\n", 1)[0]
        _text, description, formula = PROVISIONS[section]
        return json.dumps(
            {"rules": [{"section": section, "title": "Rule", "description": description, "formal_logic": formula}]}
        )


def step(title: str) -> None:
    sys.stdout.write(f"\n== {title}\n")


def say(text: str) -> None:
    sys.stdout.write(f"   {text}\n")


def main() -> int:
    started = time.perf_counter()
    with tempfile.TemporaryDirectory() as folder:
        world = World(Path(folder))
        app.dependency_overrides.update(
            {
                providers.get_graph: lambda: world.graph,
                providers.get_store: lambda: world.regulations,
                providers.get_llm: DemoLLM,
                providers.get_event_store: lambda: world.events,
                providers.get_ci_reader: lambda: world.events,
                providers.get_cert_store: lambda: world.certificates,
                providers.get_deployer: lambda: world.deployer,
                providers.get_cert_secret: lambda: SECRET,
                providers.get_bundle_source: lambda: LocalBundleSource(world.artifact_dir),
            }
        )
        api = TestClient(app)

        step("1. The compliance officer pastes three provisions of the RBI Digital Lending Directions, 2025")
        for section, (text, _d, _f) in PROVISIONS.items():
            reply = api.post("/api/regulations/", json={"section": section, "content": text}, headers=CO)
            say(f"section {section}: accepted ({reply.status_code})")

        step("2. Each rule waits for human review. Nothing is active yet")
        rules = api.get("/api/regulations/", headers=CO).json()
        for rule in rules:
            say(f"{rule['status']:<17} {rule['description']}")
        say(f"rules active in the knowledge graph: {len(world.graph.active())}")

        step("3. The officer approves them (the real UI needs two deliberate clicks)")
        for rule in rules:
            reply = api.post(f"/api/regulations/{rule['id']}/approve", headers=CO)
            say(f"{rule['rule_id']}: {reply.json()['status']}")

        step("4. An ML engineer submits a model that uses only allowed features")
        world.bundle("loan-model-v1", {"age_weight": 0.2, "occupation_weight": 0.15, "income_weight": 0.4, "credit_history_weight": 0.25})
        api.post("/api/pipeline/submit", json={"artifact_path": "loan-model-v1"}, headers=MLE)
        run = api.get("/api/pipeline/status", headers=MLE).json()
        for gate in run["gates"]:
            say(f"{gate['gate']:<16} {gate['status']}")
        deploy = api.post("/api/pipeline/deploy", json={"model_version": "loan-model-v1"}, headers=MLE)
        certificate_id = deploy.json()["certificate_id"]
        say(f"deployed. Certificate {certificate_id}")

        step("5. A model that reads the phone's contact list is stopped")
        world.bundle(
            "loan-model-v2",
            {"age_weight": 0.2, "occupation_weight": 0.15, "income_weight": 0.3, "contact_list_weight": 0.12},
        )
        api.post("/api/pipeline/submit", json={"artifact_path": "loan-model-v2"}, headers=MLE)
        run = api.get("/api/pipeline/status", headers=MLE).json()
        first = run["gates"][0]
        say(f"{first['gate']}: {first['status']}")
        for violation in first["violations"]:
            say(f"plain English: {violation['plain_english']}")
            say(f"counterexample (engineers only): {violation['counterexample']}")
        say("later gates: " + ", ".join(g["status"] for g in run["gates"][1:]))
        blocked = api.post("/api/pipeline/deploy", json={"model_version": "loan-model-v2"}, headers=MLE)
        say(f"deploy attempt: HTTP {blocked.status_code}: {blocked.json()['detail']}")

        step("6. An auditor checks the certificate with no account")
        certificate = world.certificates.rows[certificate_id]
        say("regulation versions: " + ", ".join(r["rule_id"] for r in certificate["regulation_versions"]))
        real = api.post("/api/certificates/verify", json={"cert_id": certificate_id, "proof_hash": certificate["proof_hash"]}).json()
        fake = api.post("/api/certificates/verify", json={"cert_id": certificate_id, "proof_hash": "0" * 64}).json()
        say(f"real hash   -> valid={real['valid']}")
        say(f"forged hash -> valid={fake['valid']} ({fake['explanation']})")

        step("7. Someone edits the stored certificate")
        certificate["model_version"] = "loan-model-v9"
        tampered = api.get(f"/api/certificates/{certificate_id}", headers=CO)
        say(f"read back: HTTP {tampered.status_code}: {tampered.json()['detail']}")

        app.dependency_overrides.clear()
    elapsed: Any = time.perf_counter() - started
    sys.stdout.write(f"\nDone in {elapsed:.1f}s. Real Z3, real API; stand-ins for Neo4j, Supabase, Railway and the LLM.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
