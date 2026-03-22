from fastapi import APIRouter
from ..schemas.model import ModelMetadata

router = APIRouter(prefix="/models", tags=["models"])

@router.get("/")
async def list_models():
    """List registered models."""
    return []

@router.post("/")
async def register_model(metadata: ModelMetadata):
    """Register metadata for a new model version."""
    return {"status": "registered", "name": metadata.name, "version": metadata.version}
