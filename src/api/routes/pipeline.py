from pathlib import Path
from typing import Annotated, Any

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.security import HTTPAuthorizationCredentials

from src.api.dependencies import get_current_user, require_role
from src.api.providers import get_artifact_dir, get_event_store, get_graph
from src.api.schemas.pipeline import (
    PipelineRun,
    SubmitRequest,
    SubmitResponse,
    TriggerCTRequest,
    TriggerCTResponse,
)
from src.lib.regulation_graph import GraphClient
from src.pipeline.ci import service
from src.pipeline.ci.event_store import PipelineEventStore
from src.pipeline.ci.run_registry import RunRegistry
from src.pipeline.ci.submission import SubmissionError
from src.pipeline.ct import trigger

router = APIRouter(prefix="/pipeline", tags=["pipeline"])

_registry = RunRegistry()
MLE_ONLY = Depends(require_role(["ml_engineer"]))
MLE_OR_CTO = Depends(require_role(["ml_engineer", "cto"]))
WS_ROLES = ("ml_engineer", "cto")


@router.post("/submit", response_model=SubmitResponse, status_code=202)
async def submit_model(
    body: SubmitRequest,
    background: BackgroundTasks,
    graph: Annotated[GraphClient, Depends(get_graph)],
    store: Annotated[PipelineEventStore, Depends(get_event_store)],
    base_dir: Annotated[Path, Depends(get_artifact_dir)],
    _user: Annotated[dict[str, Any], MLE_ONLY],
) -> Any:
    """Run the CI gates against a model bundle."""
    try:
        submission = service.prepare_submission(_registry, body.artifact_path, base_dir)
    except SubmissionError as e:
        raise HTTPException(status_code=400, detail=str(e))
    background.add_task(service.run_submission, _registry, store, graph, submission)
    return SubmitResponse(model_version=submission.model_version)


@router.get("/status", response_model=PipelineRun | None, dependencies=[MLE_OR_CTO])
async def pipeline_status() -> Any:
    """Latest run with the state of every gate."""
    return _registry.snapshot()


@router.post("/trigger-ct", response_model=TriggerCTResponse, status_code=202)
async def trigger_ct(
    body: TriggerCTRequest, _user: Annotated[dict[str, Any], MLE_ONLY]
) -> Any:
    """Manually start continuous training, without waiting for a regulation change."""
    try:
        await trigger.dispatch_ct_workflow(body.regulation_version)
    except trigger.TriggerError as e:
        raise HTTPException(status_code=502, detail=str(e))
    return TriggerCTResponse(regulation_version=body.regulation_version)


@router.websocket("/events")
async def pipeline_events(websocket: WebSocket) -> None:
    """Live gate events. The first message must be `{"token": "<jwt>"}`."""
    await websocket.accept()
    try:
        token = (await websocket.receive_json())["token"]
        user = await get_current_user(
            HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
        )
        if user["role"] not in WS_ROLES:
            raise PermissionError
    except Exception:
        await websocket.close(code=1008)
        return
    queue = _registry.subscribe()
    try:
        while True:
            await websocket.send_text((await queue.get()).model_dump_json())
    except WebSocketDisconnect:
        pass
    finally:
        _registry.unsubscribe(queue)
