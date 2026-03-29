from typing import Any

from fastapi import APIRouter

from src.api.schemas.model import ModelMetadata

router = APIRouter(prefix="/models", tags=["models"])

@router.get("/")
async def list_models() -> Any:
    """List registered models."""
    return []

@router.post("/")
async def register_model(metadata: ModelMetadata) -> Any:
    """Register metadata for a new model version."""
    return {"status": "registered", "name": metadata.name, "version": metadata.version}
