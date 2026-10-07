import os
import sys
import types
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tests.integration import fakes

os.environ["FRONTEND_DIST"] = "/nonexistent"  # API tests never serve a build

# The real client connects to Supabase when imported. Replace the module before
# anything imports the API, so the app can load with no environment and no
# network. (Must run before `src.api.main` is imported.)
_fake_module = types.ModuleType("src.lib.supabase_client")
_fake_module.supabase_client = fakes.FakeSupabase()  # type: ignore[attr-defined]
sys.modules["src.lib.supabase_client"] = _fake_module

from src.api import (
    providers,  # noqa: E402
    rate_limit,  # noqa: E402
)
from src.api.main import app  # noqa: E402
from src.lib.model_bundle import LocalBundleSource  # noqa: E402

SECRET = "integration-test-secret-" + "x" * 32


@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
    store = fakes.FakeRegulationStore()
    overrides = {
        providers.get_graph: fakes.FakeGraph,
        providers.get_store: lambda: store,
        providers.get_llm: fakes.FakeLLM,
        providers.get_event_store: fakes.FakeEventStore,
        providers.get_cert_store: fakes.FakeCertStore,
        providers.get_ci_reader: fakes.FakeCIReader,
        providers.get_deployer: fakes.FakeDeployer,
        providers.get_cert_secret: lambda: SECRET,
        providers.get_bundle_source: lambda: LocalBundleSource(tmp_path),
    }
    app.dependency_overrides.update(overrides)
    rate_limit.regulation_limiter.reset()
    rate_limit.verify_limiter.reset()
    try:
        yield TestClient(app, follow_redirects=False)
    finally:
        app.dependency_overrides.clear()
        rate_limit.regulation_limiter.reset()
        rate_limit.verify_limiter.reset()


# ---- stateful world for the flow tests -------------------------------------

from src.api.routes import pipeline as pipeline_routes  # noqa: E402
from src.pipeline.ci.run_registry import RunRegistry  # noqa: E402
from tests.integration.world import World  # noqa: E402

CO_HEADERS = {"Authorization": "Bearer co-token"}
MLE_HEADERS = {"Authorization": "Bearer mle-token"}
CTO_HEADERS = {"Authorization": "Bearer cto-token"}


@pytest.fixture
def world(tmp_path: Path) -> World:
    return World(tmp_path)


@pytest.fixture
def api(world: World) -> Iterator[TestClient]:
    """The real API wired to the world, so flows run end to end."""
    app.dependency_overrides.update(
        {
            providers.get_graph: lambda: world.graph,
            providers.get_store: lambda: world.regulations,
            providers.get_llm: lambda: world.llm,
            providers.get_event_store: lambda: world.events,
            providers.get_ci_reader: lambda: world.events,
            providers.get_cert_store: lambda: world.certificates,
            providers.get_deployer: lambda: world.deployer,
            providers.get_cert_secret: lambda: SECRET,
            providers.get_bundle_source: lambda: LocalBundleSource(world.artifact_dir),
        }
    )
    pipeline_routes._registry = RunRegistry()
    rate_limit.regulation_limiter.reset()
    rate_limit.verify_limiter.reset()
    try:
        yield TestClient(app, follow_redirects=False)
    finally:
        app.dependency_overrides.clear()
        rate_limit.regulation_limiter.reset()
        rate_limit.verify_limiter.reset()
