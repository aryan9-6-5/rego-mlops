import logging
from datetime import datetime, timezone
from typing import Any

from src.api.schemas.regulation import RegulationStatus
from src.pipeline.ingestion.approver import transition
from src.pipeline.ingestion.extractor import TextCompleter, extract_rules
from src.pipeline.ingestion.store import RegulationStore
from src.pipeline.ingestion.validator import validate
from src.pipeline.ingestion.versioner import (
    GraphClient,
    make_version_id,
    new_version,
    write_regulation,
)

logger = logging.getLogger(__name__)

S = RegulationStatus
LISTED_STATUSES = [
    S.PENDING_APPROVAL.value,
    S.APPROVED.value,
    S.ACTIVE.value,
    S.Z3_REJECTED.value,
]


class RegulationNotFoundError(Exception):
    pass


async def ingest_regulation(
    store: RegulationStore,
    llm: TextCompleter,
    *,
    text: str,
    section: str,
    jurisdiction: str,
    job_id: str,
) -> list[dict[str, Any]]:
    """LLM draft -> Z3 well-formedness -> approval queue. Never auto-approves."""
    try:
        candidates = await extract_rules(llm, text, section)
    except Exception:
        logger.error("Ingestion failed job_id=%s", job_id)
        raise
    version = new_version()
    saved: list[dict[str, Any]] = []
    for index, candidate in enumerate(candidates, start=1):
        rule_id = f"RBI-{section}" if index == 1 else f"RBI-{section}-{index}"
        row = store.insert(
            {
                "rule_id": rule_id,
                "jurisdiction": jurisdiction,
                "source_text": text,
                "formal_logic": candidate.formal_logic,
                "status": S.EXTRACTED.value,
                "version": version,
            }
        )
        result = validate(candidate.formal_logic)
        status = transition(S.EXTRACTED, result.status)
        fields: dict[str, Any] = {
            "status": status.value,
            "validation_message": result.reason,
        }
        if status is S.Z3_VALIDATED:
            fields["status"] = transition(status, S.PENDING_APPROVAL).value
        saved.append(store.update(row["id"], fields))
    logger.info("Ingestion complete job_id=%s rules=%d", job_id, len(saved))
    return saved


def list_regulations(store: RegulationStore) -> list[dict[str, Any]]:
    return store.list_by_status(LISTED_STATUSES)


def _load(store: RegulationStore, regulation_id: str) -> tuple[dict[str, Any], S]:
    row = store.get(regulation_id)
    if row is None:
        raise RegulationNotFoundError(regulation_id)
    return row, S(row["status"])


def approve_regulation(
    store: RegulationStore,
    graph: GraphClient,
    regulation_id: str,
    approver_id: str,
) -> dict[str, Any]:
    """Human approval: pending_approval -> approved -> (Neo4j write) -> active.

    A rule left `approved` by a failed graph write can be retried.
    """
    row, current = _load(store, regulation_id)
    if current is not S.APPROVED:
        approved = transition(current, S.APPROVED, by_human=True)
        row = store.update(
            regulation_id,
            {
                "status": approved.value,
                "approved_by": approver_id,
                "approved_at": datetime.now(timezone.utc).isoformat(),
            },
        )
    write_regulation(
        graph,
        version_id=make_version_id(row["rule_id"], row["version"]),
        rule_id=row["rule_id"],
        section=row["rule_id"].removeprefix("RBI-"),
        jurisdiction=row["jurisdiction"],
        formal_logic=row["formal_logic"],
        approved_by=approver_id,
    )
    active = transition(S.APPROVED, S.ACTIVE)
    return store.update(regulation_id, {"status": active.value})


def reject_regulation(
    store: RegulationStore, regulation_id: str, reason: str | None
) -> dict[str, Any]:
    _, current = _load(store, regulation_id)
    rejected = transition(current, S.REJECTED, by_human=True)
    return store.update(
        regulation_id, {"status": rejected.value, "validation_message": reason}
    )


class JobTracker:
    """In-process extraction job status (single-instance MVP; not persisted)."""

    def __init__(self) -> None:
        self._jobs: dict[str, dict[str, Any]] = {}

    def start(self, job_id: str) -> None:
        self._jobs[job_id] = {"job_id": job_id, "status": "running", "error": None}

    def finish(self, job_id: str, error: str | None = None) -> None:
        self._jobs[job_id] = {
            "job_id": job_id,
            "status": "failed" if error else "complete",
            "error": error,
        }

    def get(self, job_id: str) -> dict[str, Any] | None:
        return self._jobs.get(job_id)


async def run_ingestion_job(
    tracker: JobTracker,
    store: RegulationStore,
    llm: TextCompleter,
    *,
    text: str,
    section: str,
    jurisdiction: str,
    job_id: str,
) -> None:
    """Background wrapper: records success or a CO-readable failure message."""
    tracker.start(job_id)
    try:
        await ingest_regulation(
            store,
            llm,
            text=text,
            section=section,
            jurisdiction=jurisdiction,
            job_id=job_id,
        )
        tracker.finish(job_id)
    except Exception:
        tracker.finish(
            job_id,
            "Rule extraction failed. Please try again or check the regulatory text.",
        )
