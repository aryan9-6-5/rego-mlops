from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CertificateRegulation(BaseModel):
    """A regulation version a model was certified against."""

    model_config = ConfigDict(frozen=True)

    version_id: str
    rule_id: str
    formula_hash: str


class ProofCertificate(BaseModel):
    """Immutable once written."""

    model_config = ConfigDict(frozen=True)

    id: str
    model_version: str
    regulation_versions: list[CertificateRegulation]
    proof_hash: str
    hmac_signature: str
    created_at: datetime | None = None


class CertificateRead(ProofCertificate):
    """A certificate as served by the API. `verification` is `tampered` when the
    stored HMAC does not match; the hash and signature are then blanked."""

    verification: str = "valid"


class DeployRequest(BaseModel):
    model_version: str = Field(
        min_length=1, max_length=200, pattern=r"^[A-Za-z0-9._-]+$"
    )


class DeployResponse(BaseModel):
    model_version: str
    certificate_id: str
    status: str = "promoted"
