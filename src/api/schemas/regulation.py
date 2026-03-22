from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

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
