from dataclasses import dataclass
from typing import Any, Protocol


class GraphClient(Protocol):
    def run_query(
        self, query: str, params: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]: ...


@dataclass(frozen=True)
class ActiveRule:
    version_id: str
    rule_id: str
    formal_logic: str
    section: str | None = None
    description: str | None = None


_ACTIVE_RULES = """
MATCH (r:Regulation {status: 'active'})
WHERE r.formal_logic IS NOT NULL
RETURN r.version_id AS version_id,
       r.rule_id AS rule_id,
       r.formal_logic AS formal_logic,
       r.section AS section,
       r.description AS description
ORDER BY r.rule_id
"""


def fetch_active_rules(graph: GraphClient) -> list[ActiveRule]:
    """Every active regulation version with a formal rule."""
    return [
        ActiveRule(
            version_id=row["version_id"],
            rule_id=row["rule_id"],
            formal_logic=row["formal_logic"],
            section=row.get("section"),
            description=row.get("description"),
        )
        for row in graph.run_query(_ACTIVE_RULES)
    ]


_RECENT_VERSIONS = """
MATCH (r:Regulation)
WHERE r.formal_logic IS NOT NULL
RETURN r.version_id AS version_id,
       r.rule_id AS rule_id,
       r.section AS section,
       r.status AS status,
       r.activated_at AS activated_at,
       r.superseded_at AS superseded_at
ORDER BY r.activated_at DESC
LIMIT $limit
"""


def recent_regulation_versions(
    graph: GraphClient, limit: int = 20
) -> list[dict[str, Any]]:
    """Newest regulation versions first, active and superseded: the drift log."""
    return graph.run_query(_RECENT_VERSIONS, {"limit": limit})
