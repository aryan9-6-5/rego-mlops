from typing import Any, Optional

from pydantic import BaseModel, ConfigDict


class ModelMetadata(BaseModel):
    name: str
    version: str
    accuracy: float
    parameters: Optional[dict[str, Any]] = None


class RegulationVersionRef(BaseModel):
    """A regulation version a model was certified against."""

    model_config = ConfigDict(frozen=True)

    version_id: str
    rule_id: str
    section: str | None = None
    status: str
    activated_at: str | None = None
    superseded_at: str | None = None
    certified_at: str | None = None


class ModelLineage(BaseModel):
    """Which regulation versions a model version was compliant with."""

    model_config = ConfigDict(frozen=True)

    model_version: str
    created_at: str | None = None
    regulation_versions: list[RegulationVersionRef]


class FeatureChange(BaseModel):
    """One feature whose use differs between two model versions."""

    model_config = ConfigDict(frozen=True)

    feature: str
    kind: str  # "added" | "removed" | "changed"
    before: float | None = None
    after: float | None = None
    affects_rules: list[str] = []


class ModelDiff(BaseModel):
    model_config = ConfigDict(frozen=True)

    from_version: str
    to_version: str
    changes: list[FeatureChange]
