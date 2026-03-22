from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Any, Optional

class PipelineEventBase(BaseModel):
    event_type: str
    status: str
    metadata: Optional[dict[str, Any]] = None

class PipelineEventCreate(PipelineEventBase):
    pass

class PipelineEventRead(PipelineEventBase):
    id: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
