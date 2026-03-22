import os
from typing import Any, Dict, List, Optional
from neo4j import GraphDatabase, Driver
from dotenv import load_dotenv

load_dotenv()

class Neo4jClient:
    """
    Minimal Neo4j client wrapper using the official Python driver.
    """
    def __init__(self) -> None:
        self.uri: str = os.getenv("NEO4J_URI", "")
        # Use NEO4J_USER as requested, fallback to NEO4J_USERNAME from .env if present
        self.user: str = os.getenv("NEO4J_USER") or os.getenv("NEO4J_USERNAME", "")
        self.password: str = os.getenv("NEO4J_PASSWORD", "")
        self.driver: Optional[Driver] = None

    def connect(self) -> None:
        """Initialize the Neo4j driver connection."""
        if not self.driver:
            self.driver = GraphDatabase.driver(
                self.uri, 
                auth=(self.user, self.password)
            )

    def close(self) -> None:
        """Close the Neo4j driver connection."""
        if self.driver:
            self.driver.close()
            self.driver = None

    def run_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Execute a Cypher query and return results as a list of dictionaries.
        """
        if not self.driver:
            self.connect()
        
        if not self.driver:
            raise ConnectionError("Failed to connect to Neo4j.")

        with self.driver.session() as session:
            result = session.run(query, params or {})
            return [record.data() for record in result]

# Singleton instance for easy access
neo4j_client = Neo4jClient()
