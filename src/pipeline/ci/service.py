import asyncio
import logging
from pathlib import Path

from src.api.schemas.pipeline import GateEvent, GateStatus
from src.lib.model_bundle import Submission, load_submission
from src.lib.regulation_graph import GraphClient, fetch_active_rules
from src.pipeline.ci.event_store import PipelineEventStore
from src.pipeline.ci.gate_runner import fail_run, run_gates
from src.pipeline.ci.run_registry import RunRegistry

logger = logging.getLogger(__name__)

FINISHED = {GateStatus.COMPLIANT, GateStatus.VIOLATION}


def prepare_submission(
    registry: RunRegistry, artifact_path: str, base_dir: Path
) -> Submission:
    """Validate the bundle and open a new run. Raises SubmissionError."""
    submission = load_submission(artifact_path, base_dir)
    registry.begin(submission.model_version)
    return submission


async def run_submission(
    registry: RunRegistry,
    store: PipelineEventStore,
    graph: GraphClient,
    submission: Submission,
) -> None:
    """Background job: run every gate, stream events, audit finished gates."""

    async def publish(event: GateEvent) -> None:
        registry.publish(event)
        if event.status in FINISHED:
            try:
                await asyncio.to_thread(store.record, event)
            except Exception:
                logger.error(
                    "Could not record pipeline event gate=%s", event.gate.value
                )

    try:
        rules = await asyncio.to_thread(fetch_active_rules, graph)
        await run_gates(rules, submission, publish)
    except Exception:
        logger.error("Pipeline run failed model=%s", submission.model_version)
        await fail_run(
            submission,
            publish,
            "The active rules could not be loaded, so the model was not certified.",
        )
