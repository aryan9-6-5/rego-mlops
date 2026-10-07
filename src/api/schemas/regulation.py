import re
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator

MAX_REGULATORY_TEXT_CHARS = 50_000

_HTML_TAG = re.compile(r"<[^>]*>")
_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


class RegulationStatus(str, Enum):
    """Approval state machine values. Mirrors the `regulation_status` DB enum."""

    EXTRACTED = "extracted"
    Z3_VALIDATED = "z3_validated"
    Z3_REJECTED = "z3_rejected"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    ACTIVE = "active"
    SUPERSEDED = "superseded"


class RuleLogic(BaseModel):
    """A candidate rule drafted by the LLM. Never a final rule."""

    model_config = ConfigDict(frozen=True)

    section: str = Field(min_length=1, max_length=64)
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=2000)
    # SMT-LIB2: the condition a COMPLIANT model must satisfy.
    formal_logic: str = Field(min_length=1, max_length=5000)


class RegulationCreate(BaseModel):
    """Regulatory text submitted by a compliance officer."""

    # Letters, digits and . ( ) _ - only: the section reaches the LLM prompt and
    # becomes part of the rule ID, so it must not carry free text.
    section: str = Field(pattern=r"^[A-Za-z0-9._()-]{1,64}$")
    content: str = Field(min_length=1, max_length=MAX_REGULATORY_TEXT_CHARS)
    jurisdiction: str = Field(default="India", max_length=100)

    @field_validator("content")
    @classmethod
    def sanitize_content(cls, value: str) -> str:
        """Strip HTML and control characters before the text can reach the LLM."""
        cleaned = _CONTROL_CHARS.sub("", _HTML_TAG.sub("", value)).strip()
        if not cleaned:
            raise ValueError("Regulatory text is empty after sanitization.")
        return cleaned


class RegulationRead(BaseModel):
    id: str
    rule_id: str
    jurisdiction: str
    source_text: str
    description: str | None = None
    formal_logic: str
    status: RegulationStatus
    version: str
    validation_message: str | None = None
    created_at: datetime | None = None
    approved_by: str | None = None
    approved_at: datetime | None = None


class RegulationJob(BaseModel):
    """Acknowledgement for an accepted extraction request."""

    job_id: str
    status: str = "accepted"


class RejectRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=500)
