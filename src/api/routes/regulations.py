from typing import Any

from fastapi import APIRouter

from src.api.schemas.regulation import RegulationCreate, RegulationRead

router = APIRouter(prefix="/regulations", tags=["regulations"])

@router.get("/", response_model=list[RegulationRead])
async def list_regulations() -> Any:
    """List all extracted regulations."""
    return []

@router.post("/", response_model=RegulationRead, status_code=201)
async def create_regulation(regulation: RegulationCreate) -> Any:
    """Create a new regulation entry."""
    # Stub for Stage 2.3
    return {
        "id": "stub",
        "section": regulation.section,
        "content": regulation.content,
        "status": "extracted",
    }
