import os
from typing import Any

from dotenv import load_dotenv
from neo4j import Driver, GraphDatabase

load_dotenv()


class Neo4jClient:
    """Minimal Neo4j client wrapper using the official Python driver."""

    def __init__(self) -> None:
        uri = os.getenv("NEO4J_URI")
        user = os.getenv("NEO4J_USER")
        password = os.getenv("NEO4J_PASSWORD")

        if not uri or not user or not password:
            raise ValueError(
                "NEO4J_URI, NEO4J_USER, and NEO4J_PASSWORD must be set."
            )

        self._driver: Driver = GraphDatabase.driver(
            uri,
            auth=(user, password),
        )

    def close(self) -> None:
        """Close the Neo4j driver connection."""
        self._driver.close()

    def run_query(
        self,
        query: str,
        params: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Execute a Cypher query and return results as dictionaries."""
        with self._driver.session() as session:
            session = session
            result = session.run(query, params or {})
            return [record.data() for record in result]


neo4j_client = Neo4jClient()