import argparse
import asyncio
import os
import sys
from pathlib import Path

from src.api.schemas.pipeline import GateEvent
from src.lib.model_bundle import load_submission
from src.lib.regulation_graph import fetch_active_rules
from src.pipeline.ci.event_store import PipelineEventStore, SupabaseEventStore
from src.pipeline.ci.gate_runner import Publish, all_compliant, run_gates
from src.pipeline.ci.service import FINISHED


def _make_publisher(store: PipelineEventStore | None) -> Publish:
    async def publish(event: GateEvent) -> None:
        line = f"{event.gate.value}: {event.status.value} {event.plain_english}"
        sys.stdout.write(line + "\n")
        if store is not None and event.status in FINISHED:
            await asyncio.to_thread(store.record, event)

    return publish


def main() -> int:
    """Workflow step: run the CI gates on a model bundle.

    Exits non-zero unless every gate is compliant, so a failing model fails
    the workflow and never moves on to deployment.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact", required=True)
    args = parser.parse_args()

    from src.lib.neo4j_client import neo4j_client

    root = Path(os.environ.get("MODEL_ARTIFACT_DIR", "artifacts/models"))
    submission = load_submission(args.artifact, root)
    rules = fetch_active_rules(neo4j_client)
    store: PipelineEventStore | None = None
    if os.environ.get("SUPABASE_URL") and os.environ.get("SUPABASE_SERVICE_KEY"):
        # Record results so the deploy step can confirm CI passed.
        from src.lib.supabase_client import supabase_client

        store = SupabaseEventStore(supabase_client.client)
    events = asyncio.run(run_gates(rules, submission, _make_publisher(store)))
    return 0 if all_compliant(events) else 1


if __name__ == "__main__":
    sys.exit(main())
