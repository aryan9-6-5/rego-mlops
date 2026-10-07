"""Lazy providers for infrastructure clients.

Clients connect on import, so they are built on first use. Tests replace these
through `app.dependency_overrides`.
"""

import os
from pathlib import Path

from src.pipeline.ci.event_store import PipelineEventStore
from src.pipeline.ingestion.extractor import TextCompleter
from src.pipeline.ingestion.store import RegulationStore
from src.pipeline.ingestion.versioner import GraphClient


def get_graph() -> GraphClient:
    from src.lib.neo4j_client import neo4j_client

    return neo4j_client


def get_store() -> RegulationStore:
    from src.lib.supabase_client import supabase_client
    from src.pipeline.ingestion.store import SupabaseRegulationStore

    return SupabaseRegulationStore(supabase_client.client)


def get_llm() -> TextCompleter:
    from src.lib.llm_client import LLMClient

    return LLMClient()


def get_event_store() -> PipelineEventStore:
    from src.lib.supabase_client import supabase_client
    from src.pipeline.ci.event_store import SupabaseEventStore

    return SupabaseEventStore(supabase_client.client)


def get_artifact_dir() -> Path:
    return Path(os.environ.get("MODEL_ARTIFACT_DIR", "artifacts/models"))
