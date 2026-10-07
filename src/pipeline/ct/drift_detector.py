import json
import logging
import os
from dataclasses import dataclass

from src.lib.regulation_graph import GraphClient

logger = logging.getLogger(__name__)

_READ_STATE = """
MERGE (s:CTState {id: 'regulation_drift'})
RETURN s.last_checked AS last_checked
"""

_NEW_VERSIONS = """
MATCH (r:Regulation {status: 'active'})
WHERE r.activated_at > $since
RETURN r.version_id AS version_id, r.activated_at AS activated_at
ORDER BY r.activated_at
"""

_MARK_CHECKED = """
MERGE (s:CTState {id: 'regulation_drift'})
SET s.last_checked = $checked_up_to
"""


@dataclass(frozen=True)
class RegulationDrift:
    """Regulation change since the last handled check (law drift)."""

    regulation_version: str  # newest active version
    version_ids: list[str]
    detected_at: str  # activation time of the newest version


def detect_drift(graph: GraphClient) -> RegulationDrift | None:
    """Active regulation versions activated after the last handled check."""
    state = graph.run_query(_READ_STATE)
    since = (state[0]["last_checked"] if state else None) or ""
    rows = graph.run_query(_NEW_VERSIONS, {"since": since})
    if not rows:
        return None
    drift = RegulationDrift(
        regulation_version=rows[-1]["version_id"],
        version_ids=[r["version_id"] for r in rows],
        detected_at=rows[-1]["activated_at"],
    )
    logger.info(
        "Regulation drift detected regulation_version=%s count=%d",
        drift.regulation_version,
        len(rows),
    )
    return drift


def mark_checked(graph: GraphClient, checked_up_to: str) -> None:
    """Record that drift up to this time was handled. Call after training succeeds,
    so a failed run is picked up again."""
    graph.run_query(_MARK_CHECKED, {"checked_up_to": checked_up_to})


def main() -> None:
    """Workflow step: print drift as `key=value` lines for $GITHUB_OUTPUT."""
    from src.lib.neo4j_client import neo4j_client

    drift = detect_drift(neo4j_client)
    lines = (
        {"regulation_version": "", "detected_at": ""}
        if drift is None
        else {
            "regulation_version": drift.regulation_version,
            "detected_at": drift.detected_at,
        }
    )
    output = "".join(f"{k}={v}\n" for k, v in lines.items())
    path = os.environ.get("GITHUB_OUTPUT")
    if path:
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(output)
    logger.info("Drift check result %s", json.dumps(lines))


if __name__ == "__main__":
    main()
