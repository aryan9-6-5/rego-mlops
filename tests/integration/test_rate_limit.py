"""Rate limiting."""

from fastapi.testclient import TestClient

from src.api.rate_limit import RateLimiter

VALID = {"section": "4.1", "content": "Models shall not use PIN codes.", "jurisdiction": "India"}
CO = {"Authorization": "Bearer co-token"}
CO2 = {"Authorization": "Bearer co2-token"}


def test_the_eleventh_regulation_request_in_a_minute_is_429(client: TestClient) -> None:
    statuses = [
        client.post("/regulations/", json=VALID, headers=CO).status_code
        for _ in range(11)
    ]
    assert statuses == [202] * 10 + [429]


def test_the_429_says_when_to_retry(client: TestClient) -> None:
    for _ in range(10):
        client.post("/regulations/", json=VALID, headers=CO)
    response = client.post("/regulations/", json=VALID, headers=CO)
    assert response.status_code == 429
    assert int(response.headers["retry-after"]) >= 1


def test_each_user_has_their_own_budget(client: TestClient) -> None:
    for _ in range(10):
        client.post("/regulations/", json=VALID, headers=CO)
    assert client.post("/regulations/", json=VALID, headers=CO2).status_code == 202


def test_a_rejected_request_does_not_use_up_the_budget(client: TestClient) -> None:
    for _ in range(15):
        client.post("/regulations/", json={"section": "bad section!", "content": "x"}, headers=CO)
    assert client.post("/regulations/", json=VALID, headers=CO).status_code == 202


def test_unauthenticated_requests_cannot_use_up_a_users_budget(
    client: TestClient,
) -> None:
    for _ in range(15):
        client.post("/regulations/", json=VALID)
    assert client.post("/regulations/", json=VALID, headers=CO).status_code == 202


def test_the_public_verify_route_is_limited_per_client_address(
    client: TestClient,
) -> None:
    body = {"cert_id": "0" * 8 + "-0000-0000-0000-" + "0" * 12, "proof_hash": "ab"}
    first = [client.post("/certificates/verify", json=body).status_code for _ in range(30)]
    assert 429 not in first
    assert client.post("/certificates/verify", json=body).status_code == 429
    other = client.post(
        "/certificates/verify", json=body, headers={"x-forwarded-for": "203.0.113.9"}
    )
    assert other.status_code != 429


def test_the_window_slides() -> None:
    now = [0.0]
    limiter = RateLimiter(2, window_seconds=60, clock=lambda: now[0])
    assert limiter.check("k") is None
    assert limiter.check("k") is None
    assert limiter.check("k") is not None
    now[0] = 61.0
    assert limiter.check("k") is None
