from typing import Any, Optional

from pydantic import BaseModel


class ModelMetadata(BaseModel):
    name: str
    version: str
    accuracy: float
    parameters: Optional[dict[str, Any]] = None
