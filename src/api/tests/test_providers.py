"""The lazy client providers: built on first use, from the environment."""

import sys
import types
from pathlib import Path
from typing import Any

import pytest

from src.api import providers
from src.lib.tests.fake_supabase import FakeClient
from src.pipeline.cd.deployer import DeployError
from src.pipeline.cd.stores import SupabaseCertificateStore, SupabaseCIEventReader
from src.pipeline.ci.event_store import SupabaseEventStore
from src.pipeline.ingestion.store import SupabaseRegulationStore


@pytest.fixture
def clients(monkeypatch: pytest.MonkeyPatch) -> FakeClient:
    db = FakeClient()
    supabase = types.ModuleType("src.lib.supabase_client")
    supabase.supabase_client = types.SimpleNamespace(client=db)  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "src.lib.supabase_client", supabase)
    graph: Any = object()
    neo4j = types.ModuleType("src.lib.neo4j_client")
    neo4j.neo4j_client = graph  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "src.lib.neo4j_client", neo4j)
    return db


def test_stores_wrap_the_service_key_client(clients: FakeClient) -> None:
    assert isinstance(providers.get_store(), SupabaseRegulationStore)
    assert isinstance(providers.get_event_store(), SupabaseEventStore)
    assert isinstance(providers.get_cert_store(), SupabaseCertificateStore)
    assert isinstance(providers.get_ci_reader(), SupabaseCIEventReader)


def test_the_graph_is_the_shared_neo4j_client(clients: FakeClient) -> None:
    from src.lib import neo4j_client as module  # the fake installed above

    assert providers.get_graph() is module.neo4j_client  # type: ignore[attr-defined]


def test_the_llm_client_needs_an_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    with pytest.raises(ValueError):
        providers.get_llm()
    monkeypatch.setenv("OPENROUTER_API_KEY", "key")
    assert providers.get_llm() is not None


def test_the_deployer_needs_railway_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("RAILWAY_API_TOKEN", raising=False)
    with pytest.raises(DeployError):
        providers.get_deployer()
    for name in (
        "RAILWAY_API_TOKEN", "RAILWAY_PROJECT_ID", "RAILWAY_ENVIRONMENT_ID",
        "RAILWAY_SERVICE_ID", "RAILWAY_CANARY_SERVICE_ID",
    ):
        monkeypatch.setenv(name, "x")
    assert providers.get_deployer() is not None


def test_the_artifact_dir_defaults_and_can_be_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MODEL_ARTIFACT_DIR", raising=False)
    assert providers.get_artifact_dir() == Path("artifacts/models")
    monkeypatch.setenv("MODEL_ARTIFACT_DIR", "/data/models")
    assert providers.get_artifact_dir() == Path("/data/models")


@pytest.mark.parametrize("secret", [None, "", "short", "x" * 31])
def test_a_missing_or_short_certificate_secret_stops_the_server_answering(
    monkeypatch: pytest.MonkeyPatch, secret: str | None
) -> None:
    if secret is None:
        monkeypatch.delenv("PROOF_CERT_SECRET", raising=False)
    else:
        monkeypatch.setenv("PROOF_CERT_SECRET", secret)
    with pytest.raises(RuntimeError, match="32 bytes"):
        providers.get_cert_secret()


def test_a_long_enough_certificate_secret_is_returned(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PROOF_CERT_SECRET", "x" * 32)
    assert providers.get_cert_secret() == "x" * 32
