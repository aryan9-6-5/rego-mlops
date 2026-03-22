from fastapi import APIRouter
from ..schemas.certificate import CertificateRead, CertificateCreate

router = APIRouter(prefix="/certificates", tags=["certificates"])

@router.get("/", response_model=list[CertificateRead])
async def list_certificates():
    """List all compliance certificates."""
    return []

@router.post("/", response_model=CertificateRead, status_code=201)
async def create_certificate(cert: CertificateCreate):
    """Issue a new compliance certificate."""
    return {"id": "stub", "pipeline_id": cert.pipeline_id, "hash": cert.hash}
