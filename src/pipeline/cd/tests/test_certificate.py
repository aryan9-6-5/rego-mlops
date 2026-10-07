from typing import Any

import pytest
from pydantic import ValidationError

from src.api.schemas.certificate import CertificateRegulation
from src.pipeline.cd.certificate import (
    CertificateNotFoundError,
    DuplicateCertificateError,
    TamperedCertificateError,
    compute_proof_hash,
    issue_certificate,
    list_certificates,
    read_certificate,
    verify_proof_hash,
)

SECRET = "test-secret"
REG = CertificateRegulation(
    version_id="RBI-4.1-x", rule_id="RBI-4.1", formula_hash="ab"
)
REG2 = CertificateRegulation(
    version_id="RBI-4.2-y", rule_id="RBI-4.2", formula_hash="cd"
)


class MemoryStore:
    """Write-once store keyed like the certificates table (unique proof_hash)."""

    def __init__(self) -> None:
        self.rows: dict[str, dict[str, Any]] = {}

    def insert(self, row: dict[str, Any]) -> dict[str, Any]:
        if any(r["proof_hash"] == row["proof_hash"] for r in self.rows.values()):
            raise DuplicateCertificateError(row["model_version"])
        stored = {**row, "id": f"cert-{len(self.rows) + 1}", "created_at": None}
        self.rows[stored["id"]] = stored
        return dict(stored)

    def get(self, certificate_id: str) -> dict[str, Any] | None:
        row = self.rows.get(certificate_id)
        return dict(row) if row else None

    def list_latest(self) -> list[dict[str, Any]]:
        return [dict(r) for r in reversed(list(self.rows.values()))]


def issue(store: MemoryStore, model: str = "v1", regs: Any = (REG,)) -> Any:
    return issue_certificate(
        store, SECRET, model_version=model, bundle_digest="bundle", regulations=regs
    )


def test_issued_certificate_reads_back_with_valid_signature() -> None:
    store = MemoryStore()
    cert = issue(store)
    again = read_certificate(store, SECRET, cert.id)
    assert again == cert
    assert again.regulation_versions[0].version_id == "RBI-4.1-x"


def test_certificate_is_immutable() -> None:
    cert = issue(MemoryStore())
    with pytest.raises(ValidationError):
        cert.proof_hash = "forged"  # type: ignore[misc]


def test_proof_hash_is_deterministic_and_covers_regulations() -> None:
    a = compute_proof_hash("v1", "bundle", [REG, REG2])
    assert a == compute_proof_hash("v1", "bundle", [REG2, REG])
    assert a != compute_proof_hash("v1", "bundle", [REG])
    assert a != compute_proof_hash("v2", "bundle", [REG, REG2])
    assert a != compute_proof_hash("v1", "other-bundle", [REG, REG2])


def test_same_model_and_rules_cannot_be_certified_twice() -> None:
    store = MemoryStore()
    issue(store)
    with pytest.raises(DuplicateCertificateError):
        issue(store)


def test_new_regulation_version_allows_a_new_certificate() -> None:
    store = MemoryStore()
    issue(store)
    issue(store, regs=(REG, REG2))
    assert len(store.rows) == 2


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("proof_hash", "0" * 64),
        ("model_version", "v-other"),
        ("regulation_versions", []),
        ("hmac_signature", "00"),
    ],
)
def test_tampering_with_any_field_is_detected(field: str, value: Any) -> None:
    store = MemoryStore()
    cert = issue(store)
    store.rows[cert.id][field] = value
    with pytest.raises(TamperedCertificateError):
        read_certificate(store, SECRET, cert.id)


def test_wrong_secret_fails_verification() -> None:
    store = MemoryStore()
    cert = issue(store)
    with pytest.raises(TamperedCertificateError):
        read_certificate(store, "another-secret", cert.id)


def test_missing_certificate() -> None:
    with pytest.raises(CertificateNotFoundError):
        read_certificate(MemoryStore(), SECRET, "nope")


def test_list_is_newest_first_and_flags_tampered_rows_without_serving_them() -> None:
    store = MemoryStore()
    first = issue(store, "v1")
    second = issue(store, "v2")
    store.rows[first.id]["proof_hash"] = "forged"
    items = list_certificates(store, SECRET)
    assert [i.model_version for i in items] == ["v2", "v1"]
    assert items[0].verification == "valid"
    assert items[1].verification == "tampered"
    assert items[1].proof_hash == "" and items[1].hmac_signature == ""
    assert items[1].regulation_versions == []
    assert second.id == items[0].id


def test_verify_accepts_the_right_hash() -> None:
    store = MemoryStore()
    cert = issue(store)
    result = verify_proof_hash(store, SECRET, cert.id, cert.proof_hash)
    assert result.valid


def test_verify_rejects_a_forged_hash_with_an_explanation() -> None:
    store = MemoryStore()
    cert = issue(store)
    result = verify_proof_hash(store, SECRET, cert.id, "0" * 64)
    assert not result.valid
    assert "forged" in result.explanation


def test_verify_rejects_a_tampered_certificate_even_with_its_own_hash() -> None:
    store = MemoryStore()
    cert = issue(store)
    store.rows[cert.id]["proof_hash"] = "f" * 64  # attacker edits the DB row
    result = verify_proof_hash(store, SECRET, cert.id, "f" * 64)
    assert not result.valid
    assert "integrity" in result.explanation


def test_verify_unknown_certificate() -> None:
    result = verify_proof_hash(MemoryStore(), SECRET, "nope", "ab")
    assert not result.valid
