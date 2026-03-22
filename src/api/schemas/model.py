from pydantic import BaseModel
from typing import Any, Optional

class ModelMetadata(BaseModel):
    name: str
    version: str
    accuracy: float
    parameters: Optional[dict[str, Any]] = None
