import hashlib
import hmac
import json
import logging
from collections.abc import Sequence
from typing import Any, Protocol

from src.api.schemas.certificate import (
    CertificateRead,
    CertificateRegulation,
    ProofCertificate,
)

logger = logging.getLogger(__name__)


class DuplicateCertificateError(Exception):
    """A certificate for this model and regulation set already exists."""


class CertificateNotFoundError(Exception):
    pass


class TamperedCertificateError(Exception):
    """The stored HMAC does not match the certificate contents."""


class CertificateStore(Protocol):
    def insert(self, row: dict[str, Any]) -> dict[str, Any]:
        """Write-once. Raises DuplicateCertificateError on a repeated proof_hash."""
        ...

    def get(self, certificate_id: str) -> dict[str, Any] | None: ...
    def list_latest(self) -> list[dict[str, Any]]: ...


def _canonical(payload: Any) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()


def compute_proof_hash(
    model_version: str,
    bundle_digest: str,
    regulations: Sequence[CertificateRegulation],
) -> str:
    """Deterministic: the same model bundle checked against the same rule
    versions always gives the same hash, which is what makes a repeat deploy a
    409 (the table's unique constraint on proof_hash)."""
    payload = {
        "model_version": model_version,
        "bundle": bundle_digest,
        "regulations": sorted(
            (r.model_dump() for r in regulations), key=lambda r: r["version_id"]
        ),
    }
    return hashlib.sha256(_canonical(payload)).hexdigest()


def sign(
    secret: str,
    model_version: str,
    regulation_versions: Sequence[dict[str, Any]],
    proof_hash: str,
) -> str:
    message = _canonical(
        {
            "model_version": model_version,
            "regulation_versions": list(regulation_versions),
            "proof_hash": proof_hash,
        }
    )
    return hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()


def signature_is_valid(secret: str, row: dict[str, Any]) -> bool:
    expected = sign(
        secret, row["model_version"], row["regulation_versions"], row["proof_hash"]
    )
    return hmac.compare_digest(expected, str(row["hmac_signature"]))


def _to_certificate(row: dict[str, Any]) -> ProofCertificate:
    return ProofCertificate(
        id=str(row["id"]),
        model_version=row["model_version"],
        regulation_versions=[
            CertificateRegulation(**r) for r in row["regulation_versions"]
        ],
        proof_hash=row["proof_hash"],
        hmac_signature=row["hmac_signature"],
        created_at=row.get("created_at"),
    )


def issue_certificate(
    store: CertificateStore,
    secret: str,
    *,
    model_version: str,
    bundle_digest: str,
    regulations: Sequence[CertificateRegulation],
) -> ProofCertificate:
    """Write the one certificate for this deployment. There is no update path
."""
    proof_hash = compute_proof_hash(model_version, bundle_digest, regulations)
    versions = [r.model_dump() for r in regulations]
    row = store.insert(
        {
            "model_version": model_version,
            "regulation_versions": versions,
            "proof_hash": proof_hash,
            "hmac_signature": sign(secret, model_version, versions, proof_hash),
        }
    )
    logger.info(
        "Certificate issued model_version=%s proof_hash=%s regulations=%d",
        model_version,
        proof_hash,
        len(regulations),
    )
    return _to_certificate(row)


def read_certificate(
    store: CertificateStore, secret: str, certificate_id: str
) -> ProofCertificate:
    """Fetch and re-verify the HMAC. A tampered certificate is never served
."""
    row = store.get(certificate_id)
    if row is None:
        raise CertificateNotFoundError(certificate_id)
    if not signature_is_valid(secret, row):
        logger.error("Tampered certificate detected id=%s", certificate_id)
        raise TamperedCertificateError(certificate_id)
    return _to_certificate(row)


def list_certificates(store: CertificateStore, secret: str) -> list[CertificateRead]:
    """Newest first. Tampered rows are listed as such, with hash and signature
    blanked, so the problem is visible but the forged data is not served."""
    results: list[CertificateRead] = []
    for row in store.list_latest():
        if signature_is_valid(secret, row):
            valid = _to_certificate(row).model_dump()
            results.append(CertificateRead(**valid, verification="valid"))
            continue
        logger.error("Tampered certificate detected id=%s", row.get("id"))
        results.append(
            CertificateRead(
                id=str(row["id"]),
                model_version=row["model_version"],
                regulation_versions=[],
                proof_hash="",
                hmac_signature="",
                created_at=row.get("created_at"),
                verification="tampered",
            )
        )
    return results
