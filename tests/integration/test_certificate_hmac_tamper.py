"""Tampered certificates are never served."""

from typing import Any

import pytest
from fastapi.testclient import TestClient

from tests.integration.conftest import CO_HEADERS
from tests.integration.flows import certified_deployment
from tests.integration.world import World

TAMPERS: list[tuple[str, Any]] = [
    ("proof_hash", "f" * 64),
    ("model_version", "some-other-model"),
    ("regulation_versions", []),
    ("hmac_signature", "0" * 64),
]


@pytest.mark.parametrize(("field", "value"), TAMPERS)
def test_changing_any_field_makes_the_certificate_unservable(
    api: TestClient, world: World, field: str, value: Any
) -> None:
    certificate_id = certified_deployment(api, world)
    assert api.get(f"/api/certificates/{certificate_id}", headers=CO_HEADERS).status_code == 200

    world.certificates.rows[certificate_id][field] = value  # an attacker edits the row
    response = api.get(f"/api/certificates/{certificate_id}", headers=CO_HEADERS)
    assert response.status_code == 422
    assert "proof_hash" not in response.text and "hmac" not in response.text.lower()


def test_the_list_flags_a_tampered_certificate_without_serving_its_data(
    api: TestClient, world: World
) -> None:
    certificate_id = certified_deployment(api, world)
    world.certificates.rows[certificate_id]["proof_hash"] = "f" * 64
    (item,) = api.get("/api/certificates/", headers=CO_HEADERS).json()
    assert item["verification"] == "tampered"
    assert item["proof_hash"] == "" and item["hmac_signature"] == ""
    assert item["regulation_versions"] == []


def test_a_valid_row_copied_under_a_new_id_is_not_accepted(
    api: TestClient, world: World
) -> None:
    certificate_id = certified_deployment(api, world)
    copy = {**world.certificates.rows[certificate_id], "id": "11111111-1111-1111-1111-111111111111"}
    world.certificates.rows[copy["id"]] = copy
    assert api.get(f"/api/certificates/{copy['id']}", headers=CO_HEADERS).status_code == 422


def test_the_public_verify_endpoint_accepts_the_real_hash_and_rejects_others(
    api: TestClient, world: World
) -> None:
    certificate_id = certified_deployment(api, world)
    real = world.certificates.rows[certificate_id]["proof_hash"]

    good = api.post("/api/certificates/verify", json={"cert_id": certificate_id, "proof_hash": real})
    assert good.json()["valid"] is True

    forged = api.post("/api/certificates/verify", json={"cert_id": certificate_id, "proof_hash": "0" * 64})
    assert forged.json()["valid"] is False
    assert "forged" in forged.json()["explanation"]


def test_the_verify_endpoint_does_not_trust_a_tampered_row_even_with_its_own_hash(
    api: TestClient, world: World
) -> None:
    certificate_id = certified_deployment(api, world)
    world.certificates.rows[certificate_id]["proof_hash"] = "e" * 64
    response = api.post(
        "/api/certificates/verify", json={"cert_id": certificate_id, "proof_hash": "e" * 64}
    )
    assert response.json()["valid"] is False
    assert "integrity" in response.json()["explanation"]


def test_an_unknown_certificate_is_404_and_verifies_as_invalid(api: TestClient) -> None:
    unknown = "00000000-0000-0000-0000-000000000000"
    assert api.get(f"/api/certificates/{unknown}", headers=CO_HEADERS).status_code == 404
    response = api.post("/api/certificates/verify", json={"cert_id": unknown, "proof_hash": "ab"})
    assert response.json()["valid"] is False
