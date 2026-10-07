import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Protocol

from src.api.schemas.regulation import RegulationStatus

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class WriteResult:
    version_id: str
    superseded: list[str]


class GraphClient(Protocol):
    def run_query(
        self, query: str, params: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]: ...


_WRITE_REGULATION = """
MERGE (r:Regulation {version_id: $version_id})
SET r.rule_id = $rule_id,
    r.section = $section,
    r.jurisdiction = $jurisdiction,
    r.formal_logic = $formal_logic,
    r.description = $description,
    r.status = $status,
    r.approved_by = $approved_by,
    r.activated_at = $activated_at
WITH r
OPTIONAL MATCH (old:Regulation {rule_id: $rule_id, status: $active})
WHERE old.version_id <> r.version_id
FOREACH (_ IN CASE WHEN old IS NULL THEN [] ELSE [1] END |
    SET old.status = $superseded, old.superseded_at = $activated_at
    MERGE (r)-[:SUPERSEDES]->(old)
)
RETURN r.version_id AS version_id, collect(old.version_id) AS superseded
"""


def new_version(now: datetime | None = None) -> str:
    """UTC timestamp used as the `version` column."""
    return (now or datetime.now(timezone.utc)).strftime("%Y%m%dT%H%M%SZ")


def make_version_id(rule_id: str, version: str) -> str:
    """`RBI-{section}-{timestamp}` (PLAN.md 3.1); rule_id is `RBI-{section}`."""
    return f"{rule_id}-{version}"


def write_regulation(
    graph: GraphClient,
    *,
    version_id: str,
    rule_id: str,
    section: str,
    jurisdiction: str,
    formal_logic: str,
    description: str | None,
    approved_by: str,
) -> WriteResult:
    """Write an approved rule to Neo4j as an active `(:Regulation)` node.

    A previously active version of the same rule is marked `superseded` and
    linked with `(new)-[:SUPERSEDES]->(old)`; the old node is kept so lineage
    history is preserved. Only call after human approval.
    """
    try:
        rows = graph.run_query(
            _WRITE_REGULATION,
            {
                "version_id": version_id,
                "rule_id": rule_id,
                "section": section,
                "jurisdiction": jurisdiction,
                "formal_logic": formal_logic,
                "description": description,
                "status": RegulationStatus.ACTIVE.value,
                "active": RegulationStatus.ACTIVE.value,
                "superseded": RegulationStatus.SUPERSEDED.value,
                "approved_by": approved_by,
                "activated_at": datetime.now(timezone.utc).isoformat(),
            },
        )
    except Exception:
        logger.error("Neo4j write failed version_id=%s", version_id)
        raise
    if not rows:
        raise RuntimeError(f"Neo4j did not confirm write of {version_id}.")
    superseded = [str(v) for v in rows[0].get("superseded", [])]
    logger.info(
        "Regulation written to graph version_id=%s superseded=%s",
        version_id,
        superseded,
    )
    return WriteResult(str(rows[0]["version_id"]), superseded)
