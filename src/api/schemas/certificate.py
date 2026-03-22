from pydantic import BaseModel
from datetime import datetime

class CertificateBase(BaseModel):
    pipeline_id: str
    hash: str

class CertificateCreate(CertificateBase):
    pass

class CertificateRead(CertificateBase):
    id: str
    created_at: datetime

    class Config:
        from_attributes = True
