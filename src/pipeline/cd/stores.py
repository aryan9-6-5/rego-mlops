from typing import Any, Protocol

from src.api.schemas.pipeline import GateName
from src.pipeline.cd.certificate import DuplicateCertificateError

CERTIFICATES = "certificates"
PIPELINE_EVENTS = "pipeline_events"
UNIQUE_VIOLATION = "23505"


class SupabaseCertificateStore:
    """Insert and read only. There is deliberately no update or delete."""

    def __init__(self, client: Any) -> None:
        self._client = client

    def insert(self, row: dict[str, Any]) -> dict[str, Any]:
        try:
            data: Any = self._client.table(CERTIFICATES).insert(row).execute().data
        except Exception as e:
            duplicate = getattr(e, "code", None) == UNIQUE_VIOLATION
            if duplicate or "duplicate key" in str(e):
                raise DuplicateCertificateError(row["model_version"]) from e
            raise
        return dict(data[0])

    def get(self, certificate_id: str) -> dict[str, Any] | None:
        data: Any = (
            self._client.table(CERTIFICATES)
            .select("*")
            .eq("id", certificate_id)
            .execute()
            .data
        )
        return dict(data[0]) if data else None

    def list_latest(self) -> list[dict[str, Any]]:
        data: Any = (
            self._client.table(CERTIFICATES)
            .select("*")
            .order("created_at", desc=True)
            .execute()
            .data
        )
        return [dict(r) for r in data]


class CINotConfirmedError(Exception):
    """The CI gates have not all passed for this model."""


class SupabaseCIEventReader:
    """Reads the CI audit log written by the CI stage."""

    def __init__(self, client: Any) -> None:
        self._client = client

    def latest_gate_statuses(self, model_version: str) -> dict[str, str]:
        data: Any = (
            self._client.table(PIPELINE_EVENTS)
            .select("gate_name,status,created_at")
            .eq("stage", "ci")
            .eq("model_version", model_version)
            .order("created_at", desc=True)
            .execute()
            .data
        )
        latest: dict[str, str] = {}
        for row in data:
            latest.setdefault(row["gate_name"], row["status"])
        return latest


class CIEventReader(Protocol):
    def latest_gate_statuses(self, model_version: str) -> dict[str, str]: ...


def confirm_ci_passed(reader: CIEventReader, model_version: str) -> None:
    """Every CI gate's latest result for this model must be compliant."""
    statuses = reader.latest_gate_statuses(model_version)
    missing_or_failed = [
        gate.value for gate in GateName if statuses.get(gate.value) != "compliant"
    ]
    if missing_or_failed:
        raise CINotConfirmedError(
            "The model has not passed every CI gate: "
            + ", ".join(missing_or_failed)
            + "."
        )
