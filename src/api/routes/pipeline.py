from fastapi import APIRouter
from ..schemas.pipeline import PipelineEventRead, PipelineEventCreate

router = APIRouter(prefix="/pipeline", tags=["pipeline"])

@router.get("/events", response_model=list[PipelineEventRead])
async def list_events():
    """List all pipeline compliance events."""
    return []

@router.post("/events", response_model=PipelineEventRead, status_code=201)
async def log_event(event: PipelineEventCreate):
    """Log a new pipeline event."""
    return {"id": "stub", "event_type": event.event_type, "status": event.status, "metadata": event.metadata}
