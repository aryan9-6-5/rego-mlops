"""Authentication and role audit.

POLICY lists every route and who may call it. A test fails if the app has a
route that is not listed, so a new endpoint cannot ship without being audited.
"""

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from src.api.main import app
from tests.integration.fakes import ROLE_TOKEN, ROLES

CO = {"compliance_officer"}
MLE = {"ml_engineer"}
CO_CTO = {"compliance_officer", "cto"}
MLE_CTO = {"ml_engineer", "cto"}
ANY = set(ROLES)
PUBLIC = None

POLICY: dict[tuple[str, str], set[str] | None] = {
    ("GET", "/health/"): PUBLIC,
    ("GET", "/health/z3"): PUBLIC,
    ("GET", "/api/health/"): PUBLIC,
    ("GET", "/api/health/z3"): PUBLIC,
    ("POST", "/api/certificates/verify"): PUBLIC,
    ("GET", "/api/regulations/"): CO_CTO,
    ("POST", "/api/regulations/"): CO,
    ("GET", "/api/regulations/jobs/{job_id}"): CO_CTO,
    ("POST", "/api/regulations/{regulation_id}/approve"): CO,
    ("POST", "/api/regulations/{regulation_id}/reject"): CO,
    ("GET", "/api/certificates/"): ANY,
    ("GET", "/api/certificates/{certificate_id}"): ANY,
    ("GET", "/api/models/"): ANY,
    ("GET", "/api/models/{version}/lineage"): ANY,
    ("GET", "/api/models/diff"): MLE_CTO,
    ("POST", "/api/models/"): MLE,
    ("GET", "/api/pipeline/status"): MLE_CTO,
    ("GET", "/api/pipeline/drift-log"): MLE_CTO,
    ("POST", "/api/pipeline/submit"): MLE,
    ("POST", "/api/pipeline/deploy"): MLE,
    ("POST", "/api/pipeline/trigger-ct"): MLE,
}
PROTECTED = [(k, v) for k, v in POLICY.items() if v is not None]
PUBLIC_ROUTES = [k for k, v in POLICY.items() if v is None]


def concrete(path: str) -> str:
    out = path
    while "{" in out:
        start = out.index("{")
        out = out[:start] + "x" + out[out.index("}") + 1 :]
    return out


HTTP_METHODS = {"get", "post", "put", "patch", "delete"}


def registered() -> set[tuple[str, str]]:
    """Every HTTP route, read from the OpenAPI schema so it does not depend on
    FastAPI's internal router classes. (WebSockets are tested separately.)"""
    paths = app.openapi()["paths"]
    return {
        (method.upper(), path)
        for path, operations in paths.items()
        for method in operations
        if method in HTTP_METHODS
    }


def call(client: TestClient, method: str, path: str, token: str | None) -> int:
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    return client.request(method, concrete(path), headers=headers, json={}).status_code


def test_every_route_is_in_the_policy_and_the_policy_has_no_stale_entries() -> None:
    assert registered() == set(POLICY)


@pytest.mark.parametrize(("route", "allowed"), PROTECTED)
def test_no_token_is_401(client: TestClient, route: tuple[str, str], allowed: set[str]) -> None:
    assert call(client, *route, token=None) == 401


@pytest.mark.parametrize(("route", "allowed"), PROTECTED)
@pytest.mark.parametrize("token", ["unknown-token", "norole-token", "boom-token"])
def test_bad_or_roleless_tokens_are_401(
    client: TestClient, route: tuple[str, str], allowed: set[str], token: str
) -> None:
    assert call(client, *route, token=token) == 401


@pytest.mark.parametrize(("route", "allowed"), PROTECTED)
@pytest.mark.parametrize("role", ROLES)
def test_roles_outside_the_policy_are_403_and_inside_are_let_through(
    client: TestClient, route: tuple[str, str], allowed: set[str], role: str
) -> None:
    status = call(client, *route, token=ROLE_TOKEN[role])
    if role in allowed:
        assert status not in (401, 403), f"{role} should reach {route}"
    else:
        assert status == 403, f"{role} should be refused {route}"


@pytest.mark.parametrize("route", PUBLIC_ROUTES)
def test_public_routes_need_no_token(client: TestClient, route: tuple[str, str]) -> None:
    assert call(client, *route, token=None) not in (401, 403)


def test_a_failed_login_reveals_nothing(client: TestClient) -> None:
    response = client.get(
        "/api/regulations/", headers={"Authorization": "Bearer boom-token"}
    )
    assert response.status_code == 401
    assert response.json() == {"detail": "Could not validate credentials."}
    assert "internal" not in response.text
    assert response.headers["www-authenticate"] == "Bearer"


def test_a_forbidden_response_does_not_list_roles(client: TestClient) -> None:
    response = client.post(
        "/api/regulations/x/approve", headers={"Authorization": "Bearer mle-token"}, json={}
    )
    assert response.status_code == 403
    assert "compliance_officer" not in response.text


def test_the_certificate_routes_have_no_write_methods() -> None:
    methods = {m for (m, p) in registered() if p.startswith("/api/certificates")}
    assert methods == {"GET", "POST"}
    assert ("POST", "/api/certificates/") not in registered()


def test_the_event_socket_rejects_missing_unknown_and_wrong_role_tokens(
    client: TestClient,
) -> None:
    for message in ({}, {"token": "unknown-token"}, {"token": "co-token"}):
        with client.websocket_connect("/api/pipeline/events") as socket:
            socket.send_json(message)
            with pytest.raises(WebSocketDisconnect) as closed:
                socket.receive_text()
            assert closed.value.code == 1008


def test_docs_are_not_public_in_production(monkeypatch: pytest.MonkeyPatch) -> None:
    import importlib

    import src.api.main as main

    monkeypatch.setenv("ENVIRONMENT", "production")
    try:
        reloaded = importlib.reload(main)
        assert reloaded.app.docs_url is None
        assert reloaded.app.openapi_url is None
    finally:
        monkeypatch.delenv("ENVIRONMENT")
        importlib.reload(main)
