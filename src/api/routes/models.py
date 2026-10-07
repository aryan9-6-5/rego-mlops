from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from src.api.dependencies import require_role
from src.api.schemas.model import ModelLineage, ModelMetadata
from src.pipeline.cd import lineage
from src.pipeline.cd.lineage import GraphClient

router = APIRouter(prefix="/models", tags=["models"])

ANY_ROLE = Depends(require_role(["compliance_officer", "ml_engineer", "cto"]))


def get_graph() -> GraphClient:
    from src.lib.neo4j_client import neo4j_client

    return neo4j_client


@router.get("/", response_model=list[ModelLineage], dependencies=[ANY_ROLE])
async def list_models(graph: GraphClient = Depends(get_graph)) -> Any:
    """Every model version with the regulation versions it was certified against."""
    return lineage.list_lineages(graph)


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
