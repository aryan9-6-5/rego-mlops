from datetime import datetime

from pydantic import BaseModel


class RegulationBase(BaseModel):
    section: str
    content: str

class RegulationCreate(RegulationBase):
    pass

class RegulationRead(RegulationBase):
    id: str
    status: str = "extracted"
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
