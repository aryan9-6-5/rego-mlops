import sys
import types
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tests.integration import fakes

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
        providers.get_artifact_dir: lambda: tmp_path,
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
