"""Thin infrastructure wrappers: Neo4j, Supabase and MLflow."""

import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

LIB = Path(__file__).resolve().parents[1]


def load_fresh(name: str) -> ModuleType:
    """Import a lib module from its file under a private name, so a fake installed
    in sys.modules by other tests cannot stand in for it."""
    spec = importlib.util.spec_from_file_location(f"fresh_{name}", LIB / f"{name}.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# ---- Neo4j -----------------------------------------------------------------


class FakeRecord:
    def __init__(self, data: dict[str, Any]) -> None:
        self._data = data

    def data(self) -> dict[str, Any]:
        return self._data


class FakeSession:
    def __init__(self, log: list[Any]) -> None:
        self.log = log

    def __enter__(self) -> "FakeSession":
        return self

    def __exit__(self, *_: Any) -> None:
        return None

    def run(self, query: str, params: dict[str, Any]) -> list[FakeRecord]:
        self.log.append((query, params))
        return [FakeRecord({"n": 1})]


class FakeDriver:
    def __init__(self) -> None:
        self.log: list[Any] = []
        self.closed = False

    def session(self) -> FakeSession:
        return FakeSession(self.log)

    def close(self) -> None:
        self.closed = True


@pytest.fixture
def neo4j_module(monkeypatch: pytest.MonkeyPatch) -> tuple[ModuleType, FakeDriver]:
    import neo4j

    driver = FakeDriver()
    monkeypatch.setattr(neo4j.GraphDatabase, "driver", lambda *a, **k: driver)
    monkeypatch.setenv("NEO4J_URI", "bolt://test")
    monkeypatch.setenv("NEO4J_USERNAME", "neo4j")
    monkeypatch.setenv("NEO4J_PASSWORD", "pw")
    return load_fresh("neo4j_client"), driver


def test_neo4j_runs_queries_with_parameters(
    neo4j_module: tuple[ModuleType, FakeDriver],
) -> None:
    module, driver = neo4j_module
    rows = module.neo4j_client.run_query("RETURN $x AS n", {"x": 1})
    assert rows == [{"n": 1}]
    assert driver.log == [("RETURN $x AS n", {"x": 1})]
    assert module.neo4j_client.run_query("RETURN 1") == [{"n": 1}]


def test_neo4j_closes_its_driver(neo4j_module: tuple[ModuleType, FakeDriver]) -> None:
    module, driver = neo4j_module
    module.neo4j_client.close()
    assert driver.closed


def test_neo4j_accepts_the_older_user_variable(
    neo4j_module: tuple[ModuleType, FakeDriver], monkeypatch: pytest.MonkeyPatch
) -> None:
    module, _ = neo4j_module
    monkeypatch.delenv("NEO4J_USERNAME")
    monkeypatch.setenv("NEO4J_USER", "legacy")
    assert module.Neo4jClient() is not None


def test_neo4j_refuses_to_start_without_credentials(
    neo4j_module: tuple[ModuleType, FakeDriver], monkeypatch: pytest.MonkeyPatch
) -> None:
    module, _ = neo4j_module
    monkeypatch.delenv("NEO4J_PASSWORD")
    with pytest.raises(ValueError, match="NEO4J_USERNAME"):
        module.Neo4jClient()


# ---- Supabase --------------------------------------------------------------


def real_supabase() -> ModuleType:
    """The installed package, or skip. The repo's own `supabase/` folder of SQL
    migrations can look like an empty namespace package when it is not installed."""
    module: ModuleType = pytest.importorskip("supabase")
    if not hasattr(module, "create_client"):
        pytest.skip("the supabase package is not installed")
    return module


def test_supabase_verifies_a_token_and_returns_only_safe_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    supabase = real_supabase()

    class Auth:
        def get_user(self, token: str) -> Any:
            if token != "good":
                raise RuntimeError("bad token")
            user = type("U", (), {})()
            user.id, user.email = "u1", "u@example.test"
            user.app_metadata, user.user_metadata = {}, {"role": "x"}
            return type("R", (), {"user": user})()

    class Client:
        auth = Auth()

    monkeypatch.setattr(supabase, "create_client", lambda *a, **k: Client())
    monkeypatch.setenv("SUPABASE_URL", "http://db.test")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "key")
    module = load_fresh("supabase_client")
    user = module.supabase_client.verify_token("good")
    assert user["id"] == "u1" and set(user) == {
        "id", "email", "app_metadata", "user_metadata",
    }
    with pytest.raises(ValueError):
        module.supabase_client.verify_token("bad")


def test_supabase_requires_its_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    real_supabase()
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_KEY", raising=False)
    with pytest.raises(ValueError):
        load_fresh("supabase_client")


# ---- MLflow (optional `ct` group; skipped when it is not installed) ---------


def test_mlflow_logs_a_run_tagged_with_the_regulation_version(tmp_path: Path) -> None:
    mlflow = pytest.importorskip("mlflow")
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    (bundle / "profile.json").write_text('{"weights": {"a_weight": 1}}')
    store = "sqlite:///" + (tmp_path / "mlflow.db").as_posix()
    module = load_fresh("mlflow_client")
    run_id = module.MlflowTracker(tracking_uri=store, experiment="test").log_run(
        model_version="ct-RBI-4.1-x",
        regulation_version="RBI-4.1-x",
        artifact_dir=bundle,
        params={"prohibited_features": "pin_code"},
        metrics={"prohibited_feature_count": 1.0},
    )
    mlflow.set_tracking_uri(store)
    run = mlflow.get_run(run_id)
    assert run.data.tags["regulation_version"] == "RBI-4.1-x"
    assert run.data.params == {"prohibited_features": "pin_code"}
    assert run.data.metrics["prohibited_feature_count"] == 1.0
    assert "profile.json" in [a.path for a in mlflow.MlflowClient().list_artifacts(run_id)]


def test_this_module_is_loaded_in_isolation() -> None:
    assert "fresh_neo4j_client" not in sys.modules  # load_fresh never registers
