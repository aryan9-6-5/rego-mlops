from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class GateName(str, Enum):
    SYMBOLIC_CHECK = "symbolic_check"
    REG_ATTACK = "reg_attack"
    FAIRNESS_CHECK = "fairness_check"
    REGRESSION = "regression"


class GateStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLIANT = "compliant"
    VIOLATION = "violation"
    SKIPPED = "skipped"


class Violation(BaseModel):
    """One rule a model breaks. `counterexample` is for the MLE interface only
    and must never be shown to a compliance officer."""

    model_config = ConfigDict(frozen=True)

    rule_id: str
    plain_english: str
    counterexample: dict[str, str] = {}


class GateResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    gate: GateName
    status: GateStatus
    rule_ids: list[str] = []
    duration_ms: float = 0.0
    plain_english: str = ""
    violations: list[Violation] = []


class GateEvent(GateResult):
    """A gate result stamped with the model it belongs to."""

    model_version: str
    timestamp: str


class PipelineRun(BaseModel):
    model_version: str
    status: GateStatus
    gates: list[GateEvent]


class SubmitRequest(BaseModel):
    artifact_path: str = Field(min_length=1, max_length=300)


class SubmitResponse(BaseModel):
    model_version: str
    status: str = "accepted"


class TriggerCTRequest(BaseModel):
    regulation_version: str = Field(min_length=1, max_length=200)


class TriggerCTResponse(BaseModel):
    regulation_version: str
    status: str = "dispatched"
