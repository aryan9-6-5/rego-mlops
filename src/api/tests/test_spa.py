from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.spa import is_reserved, mount_frontend


@pytest.fixture
def dist(tmp_path: Path) -> Path:
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text("<html>REGO APP</html>")
    (tmp_path / "assets" / "app.js").write_text("console.log('app')")
    (tmp_path / "favicon.svg").write_text("<svg/>")
    (tmp_path.parent / "secret.txt").write_text("do not serve")
    return tmp_path


@pytest.fixture
def client(dist: Path) -> TestClient:
    app = FastAPI()

    @app.get("/api/ping")
    async def ping() -> dict[str, str]:
        return {"ok": "yes"}

    assert mount_frontend(app, dist)
    return TestClient(app)


def test_the_root_and_deep_links_return_the_app(client: TestClient) -> None:
    for path in ("/", "/approval-queue", "/certificates", "/some/deep/link"):
        response = client.get(path)
        assert response.status_code == 200 and "REGO APP" in response.text, path


def test_built_files_are_served(client: TestClient) -> None:
    assert client.get("/assets/app.js").text == "console.log('app')"
    assert client.get("/favicon.svg").text == "<svg/>"


def test_real_api_routes_still_win(client: TestClient) -> None:
    assert client.get("/api/ping").json() == {"ok": "yes"}


def test_an_unknown_api_path_is_a_404_not_the_login_page(client: TestClient) -> None:
    for path in ("/api/nope", "/api", "/health/missing", "/api/regulations/x/y"):
        response = client.get(path)
        assert response.status_code == 404, path
        assert "REGO APP" not in response.text


@pytest.mark.parametrize(
    "path",
    ["/../secret.txt", "/%2e%2e/secret.txt", "/assets/../../secret.txt", "//etc/passwd"],
)
def test_paths_cannot_escape_the_build_folder(client: TestClient, path: str) -> None:
    response = client.get(path)
    assert "do not serve" not in response.text
    assert "root:" not in response.text


def test_nothing_is_mounted_without_a_build(tmp_path: Path) -> None:
    app = FastAPI()
    assert mount_frontend(app, tmp_path / "missing") is False
    assert TestClient(app).get("/").status_code == 404


def test_reserved_prefixes() -> None:
    assert is_reserved("api/x") and is_reserved("/api") and is_reserved("health/z3")
    assert not is_reserved("approval-queue") and not is_reserved("")
