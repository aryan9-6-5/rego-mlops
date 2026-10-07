from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from src.api.dependencies import require_role
from src.api.providers import get_artifact_dir, get_graph
from src.api.schemas.model import ModelDiff, ModelLineage, ModelMetadata
from src.features import model_diff
from src.lib.model_bundle import SubmissionError
from src.pipeline.cd import lineage
from src.pipeline.cd.lineage import GraphClient

router = APIRouter(prefix="/models", tags=["models"])

ANY_ROLE = Depends(require_role(["compliance_officer", "ml_engineer", "cto"]))
MLE_OR_CTO = Depends(require_role(["ml_engineer", "cto"]))
VERSION = Query(min_length=1, max_length=200, pattern=r"^[A-Za-z0-9._-]+$")


@router.get("/", response_model=list[ModelLineage], dependencies=[ANY_ROLE])
async def list_models(graph: GraphClient = Depends(get_graph)) -> Any:
    """Every model version with the regulation versions it was certified against."""
    return lineage.list_lineages(graph)


@router.get("/diff", response_model=ModelDiff, dependencies=[MLE_OR_CTO])
async def diff_models(
    from_version: str = VERSION,
    to_version: str = VERSION,
    graph: GraphClient = Depends(get_graph),
    base_dir: Path = Depends(get_artifact_dir),
) -> Any:
    """Features added, removed or re-weighted between two model versions."""
    try:
        return model_diff.compare(graph, base_dir, from_version, to_version)
    except SubmissionError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get(
    "/{version}/lineage", response_model=ModelLineage, dependencies=[ANY_ROLE]
)
async def get_model_lineage(
    version: str, graph: GraphClient = Depends(get_graph)
) -> Any:
    result = lineage.get_lineage(graph, version)
    if result is None:
        raise HTTPException(status_code=404, detail="Model version not found.")
    return result


@router.post("/")
async def register_model(metadata: ModelMetadata) -> Any:
    """Register metadata for a new model version."""
    return {"status": "registered", "name": metadata.name, "version": metadata.version}
