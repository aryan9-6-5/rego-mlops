import uuid
from typing import Annotated, Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from src.api.dependencies import require_role
from src.api.schemas.regulation import (
    RegulationCreate,
    RegulationJob,
    RegulationRead,
    RejectRequest,
)
from src.pipeline.ingestion import service
from src.pipeline.ingestion.approver import InvalidStateTransitionError
from src.pipeline.ingestion.extractor import TextCompleter
from src.pipeline.ingestion.store import RegulationStore
from src.pipeline.ingestion.versioner import GraphClient

router = APIRouter(prefix="/regulations", tags=["regulations"])

_tracker = service.JobTracker()
CO_ONLY = Depends(require_role(["compliance_officer"]))
CO_OR_CTO = Depends(require_role(["compliance_officer", "cto"]))


def get_store() -> RegulationStore:
    from src.lib.supabase_client import supabase_client
    from src.pipeline.ingestion.store import SupabaseRegulationStore

    return SupabaseRegulationStore(supabase_client.client)


def get_llm() -> TextCompleter:
    from src.lib.llm_client import LLMClient

    return LLMClient()


def get_graph() -> GraphClient:
    from src.lib.neo4j_client import neo4j_client

    return neo4j_client


Store = Annotated[RegulationStore, Depends(get_store)]


@router.get("/", response_model=list[RegulationRead], dependencies=[CO_OR_CTO])
async def list_regulations(store: Store) -> Any:
    return service.list_regulations(store)


@router.post("/", response_model=RegulationJob, status_code=202)
async def create_regulation(
    body: RegulationCreate,
    background: BackgroundTasks,
    store: Store,
    llm: Annotated[TextCompleter, Depends(get_llm)],
    _user: Annotated[dict[str, Any], CO_ONLY],
) -> Any:
    job_id = str(uuid.uuid4())
    background.add_task(
        service.run_ingestion_job,
        _tracker,
        store,
        llm,
        text=body.content,
        section=body.section,
        jurisdiction=body.jurisdiction,
        job_id=job_id,
    )
    return RegulationJob(job_id=job_id)


@router.get("/jobs/{job_id}", dependencies=[CO_OR_CTO])
async def get_job(job_id: str) -> Any:
    job = _tracker.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    return job


@router.post("/{regulation_id}/approve", response_model=RegulationRead)
async def approve_regulation(
    regulation_id: str,
    store: Store,
    graph: Annotated[GraphClient, Depends(get_graph)],
    user: Annotated[dict[str, Any], CO_ONLY],
) -> Any:
    try:
        return service.approve_regulation(store, graph, regulation_id, user["id"])
    except service.RegulationNotFoundError:
        raise HTTPException(status_code=404, detail="Regulation not found.")
    except InvalidStateTransitionError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.post("/{regulation_id}/reject", response_model=RegulationRead)
async def reject_regulation(
    regulation_id: str,
    body: RejectRequest,
    store: Store,
    _user: Annotated[dict[str, Any], CO_ONLY],
) -> Any:
    try:
        return service.reject_regulation(store, regulation_id, body.reason)
    except service.RegulationNotFoundError:
        raise HTTPException(status_code=404, detail="Regulation not found.")
    except InvalidStateTransitionError as e:
        raise HTTPException(status_code=409, detail=str(e))
