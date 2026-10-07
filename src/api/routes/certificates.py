from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException

from src.api.dependencies import require_role
from src.api.providers import get_cert_secret, get_cert_store
from src.api.schemas.certificate import CertificateRead, ProofCertificate
from src.pipeline.cd import certificate
from src.pipeline.cd.certificate import CertificateStore

router = APIRouter(prefix="/certificates", tags=["certificates"])

ANY_ROLE = Depends(require_role(["compliance_officer", "ml_engineer", "cto"]))
Store = Annotated[CertificateStore, Depends(get_cert_store)]
Secret = Annotated[str, Depends(get_cert_secret)]

# There is no create, update or delete route. Certificates are written only by
# the deploy flow in pipeline/cd.


@router.get("/", response_model=list[CertificateRead], dependencies=[ANY_ROLE])
async def list_certificates(store: Store, secret: Secret) -> Any:
    """All certificates, newest first, each with its HMAC re-verified."""
    return certificate.list_certificates(store, secret)


@router.get(
    "/{certificate_id}", response_model=ProofCertificate, dependencies=[ANY_ROLE]
)
async def get_certificate(certificate_id: str, store: Store, secret: Secret) -> Any:
    try:
        return certificate.read_certificate(store, secret, certificate_id)
    except certificate.CertificateNotFoundError:
        raise HTTPException(status_code=404, detail="Certificate not found.")
    except certificate.TamperedCertificateError:
        raise HTTPException(
            status_code=422,
            detail="This certificate failed verification and cannot be served.",
        )
