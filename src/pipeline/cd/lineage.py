import logging
from datetime import datetime, timezone
from typing import Any, Protocol

from src.api.schemas.model import ModelLineage, RegulationVersionRef
from src.api.schemas.regulation import RegulationStatus

logger = logging.getLogger(__name__)


class GraphClient(Protocol):
    def run_query(
        self, query: str, params: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]: ...


class LineageError(Exception):
    """Raised when lineage cannot be recorded or read."""


_RECORD = """
MERGE (m:ModelVersion {version: $model_version})
ON CREATE SET m.created_at = $now
WITH m
MATCH (r:Regulation {status: $active})
MERGE (m)-[c:COMPLIANT_WITH]->(r)
ON CREATE SET c.certified_at = $now
RETURN collect(r.version_id) AS version_ids
"""

_READ = """
MATCH (m:ModelVersion)
WHERE $model_version IS NULL OR m.version = $model_version
OPTIONAL MATCH (m)-[c:COMPLIANT_WITH]->(r:Regulation)
WITH m, c, r ORDER BY r.rule_id
RETURN m.version AS model_version,
       m.created_at AS created_at,
       collect(CASE WHEN r IS NULL THEN null ELSE {
           version_id: r.version_id,
           rule_id: r.rule_id,
           section: r.section,
           status: r.status,
           activated_at: r.activated_at,
           superseded_at: r.superseded_at,
           certified_at: c.certified_at
       } END) AS regulation_versions
ORDER BY m.created_at DESC
"""


def record_lineage(graph: GraphClient, model_version: str) -> list[str]:
    """Link a model version to every regulation version active right now.

    A statement that a model is compliant with these rules. Call it only after
    every CI gate has passed. Refuses to record a model
    as compliant with nothing.
    """
    try:
        rows = graph.run_query(
            _RECORD,
            {
                "model_version": model_version,
                "active": RegulationStatus.ACTIVE.value,
                "now": datetime.now(timezone.utc).isoformat(),
            },
        )
    except Exception:
        logger.error("Lineage write failed model_version=%s", model_version)
        raise
    version_ids = [str(v) for v in (rows[0]["version_ids"] if rows else [])]
    if not version_ids:
        raise LineageError("No active regulation versions to link the model to.")
    logger.info(
        "Lineage recorded model_version=%s regulation_versions=%s",
        model_version,
        version_ids,
    )
    return version_ids


def _to_lineage(row: dict[str, Any]) -> ModelLineage:
    return ModelLineage(
        model_version=row["model_version"],
        created_at=row.get("created_at"),
        regulation_versions=[
            RegulationVersionRef(**reg) for reg in row["regulation_versions"]
        ],
    )


def get_lineage(graph: GraphClient, model_version: str) -> ModelLineage | None:
    """Full compliance lineage for one model version, or None if unknown."""
    rows = graph.run_query(_READ, {"model_version": model_version})
    return _to_lineage(rows[0]) if rows else None


def list_lineages(graph: GraphClient) -> list[ModelLineage]:
    """Lineage for every model version, newest first."""
    return [_to_lineage(r) for r in graph.run_query(_READ, {"model_version": None})]
