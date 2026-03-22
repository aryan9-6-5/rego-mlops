from fastapi import APIRouter
from ..schemas.regulation import RegulationRead, RegulationCreate

router = APIRouter(prefix="/regulations", tags=["regulations"])

@router.get("/", response_model=list[RegulationRead])
async def list_regulations():
    """List all extracted regulations."""
    return []

@router.post("/", response_model=RegulationRead, status_code=201)
async def create_regulation(regulation: RegulationCreate):
    """Create a new regulation entry."""
    # Stub for Stage 2.3
    return {"id": "stub", "section": regulation.section, "content": regulation.content, "status": "extracted"}
