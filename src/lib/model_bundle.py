import hashlib
import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

logger = logging.getLogger(__name__)

MAX_EVAL_ROWS = 1_000_000
MAX_FILE_BYTES = 50 * 1024 * 1024
PROFILE_FILE = "profile.json"
EVALUATION_FILE = "evaluation.json"
BUNDLE_FILES = (PROFILE_FILE, EVALUATION_FILE)
DEFAULT_BUCKET = "model-bundles"

_NAME = re.compile(r"^[A-Za-z0-9._-]{1,200}$")


class SubmissionError(Exception):
    """Raised when a model bundle is missing, malformed or has an unsafe name."""


class BundleStorageError(Exception):
    """Raised when the place bundles are kept cannot be reached. Distinct from a
    bundle that is simply not there."""


@dataclass(frozen=True)
class Evaluation:
    """Held-out predictions produced by the training step."""

    y_true: list[int]
    y_pred: list[int]
    baseline_y_pred: list[int]
    groups: list[str]


@dataclass(frozen=True)
class Submission:
    """A model bundle: `profile.json` (feature weights, named `<feature>_weight`)
    and `evaluation.json` (held-out predictions). `bundle_hash` is a SHA-256 over
    the exact bytes that were read, so a result can be tied to those bytes."""

    model_version: str
    weights: dict[str, float | bool]
    evaluation: Evaluation | None
    bundle_hash: str = ""


@dataclass(frozen=True)
class RawBundle:
    name: str
    profile: bytes
    evaluation: bytes | None


class BundleSource(Protocol):
    def read(self, name: str, filename: str) -> bytes | None:
        """The file's bytes, or None if it does not exist. Raises
        BundleStorageError if the place it is kept cannot be reached."""
        ...


class LocalBundleSource:
    """Bundles as folders under a base directory."""

    def __init__(self, base_dir: Path) -> None:
        self._base = base_dir.resolve()

    def read(self, name: str, filename: str) -> bytes | None:
        folder = (self._base / name).resolve()
        if self._base not in folder.parents:
            raise SubmissionError("Artifact path is outside the model directory.")
        file = folder / filename
        if not file.is_file():
            return None
        if file.stat().st_size > MAX_FILE_BYTES:
            raise SubmissionError(f"{filename} is too large.")
        try:
            return file.read_bytes()
        except OSError as e:
            raise BundleStorageError("Could not read the model directory.") from e


class SupabaseBundleSource:
    """Bundles as objects `<name>/profile.json` in a private Supabase Storage
    bucket, reached only with the backend's service key."""

    def __init__(self, client: Any, bucket: str = DEFAULT_BUCKET) -> None:
        self._storage = client.storage
        self._bucket = bucket

    def read(self, name: str, filename: str) -> bytes | None:
        try:
            data: Any = self._storage.from_(self._bucket).download(f"{name}/{filename}")
        except Exception as e:
            if _is_not_found(e):
                return None
            logger.error("Bundle download failed error=%s", type(e).__name__)
            raise BundleStorageError("Model file storage is unavailable.") from e
        content = bytes(data)
        if len(content) > MAX_FILE_BYTES:
            raise SubmissionError(f"{filename} is too large.")
        return content

    def upload(self, name: str, directory: Path) -> None:
        """Store a local bundle folder. Overwrites: a replaced bundle has a new
        hash, so results from the old bytes no longer apply to it."""
        _check_name(name)
        profile = directory / PROFILE_FILE
        if not profile.is_file():
            raise SubmissionError(f"{PROFILE_FILE} is missing.")
        for filename in BUNDLE_FILES:
            file = directory / filename
            if not file.is_file():
                continue
            try:
                self._storage.from_(self._bucket).upload(
                    f"{name}/{filename}",
                    file.read_bytes(),
                    {"content-type": "application/json", "upsert": "true"},
                )
            except Exception as e:
                logger.error("Bundle upload failed error=%s", type(e).__name__)
                raise BundleStorageError("Model file storage is unavailable.") from e


def _is_not_found(error: Exception) -> bool:
    status = getattr(error, "status", None) or getattr(error, "status_code", None)
    return str(status) == "404" or "not found" in str(error).lower()


def _check_name(name: str) -> None:
    if not _NAME.match(name) or not name.strip("."):
        raise SubmissionError("The model name is not valid.")


def coerce_source(source: "Path | BundleSource") -> BundleSource:
    return LocalBundleSource(source) if isinstance(source, Path) else source


def fetch_bundle(name: str, source: "Path | BundleSource") -> RawBundle:
    """Read a bundle's files once. Raises SubmissionError if it is missing."""
    _check_name(name)
    bundle_source = coerce_source(source)
    profile = bundle_source.read(name, PROFILE_FILE)
    if profile is None:
        raise SubmissionError("Model bundle not found.")
    return RawBundle(name, profile, bundle_source.read(name, EVALUATION_FILE))


def hash_raw(raw: RawBundle) -> str:
    """SHA-256 over the bundle's files, binding a certificate to exact model data."""
    digest = hashlib.sha256()
    for filename, content in (
        (PROFILE_FILE, raw.profile),
        (EVALUATION_FILE, raw.evaluation),
    ):
        if content is not None:
            digest.update(filename.encode())
            digest.update(content)
    return digest.hexdigest()


def _json(content: bytes, filename: str) -> Any:
    try:
        return json.loads(content)
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        raise SubmissionError(f"Could not read {filename}.") from e


def _binary_list(raw: Any, name: str) -> list[int]:
    if not isinstance(raw, list) or len(raw) > MAX_EVAL_ROWS:
        raise SubmissionError(f"evaluation.json: '{name}' must be a list.")
    if any(v not in (0, 1) or isinstance(v, bool) for v in raw):
        raise SubmissionError(f"evaluation.json: '{name}' must contain only 0 and 1.")
    return [int(v) for v in raw]


def _parse_weights(raw: Any) -> dict[str, float | bool]:
    weights = raw.get("weights") if isinstance(raw, dict) else None
    if not isinstance(weights, dict) or not weights:
        raise SubmissionError("profile.json needs a non-empty 'weights' object.")
    for name, value in weights.items():
        if not isinstance(value, (int, float, bool)):
            raise SubmissionError(f"profile.json: weight '{name}' is not a number.")
    return dict(weights)


def _parse_evaluation(raw: Any) -> Evaluation:
    if not isinstance(raw, dict):
        raise SubmissionError("evaluation.json must be an object.")
    y_true = _binary_list(raw.get("y_true"), "y_true")
    y_pred = _binary_list(raw.get("y_pred"), "y_pred")
    baseline = _binary_list(raw.get("baseline_y_pred"), "baseline_y_pred")
    groups = raw.get("groups")
    if not isinstance(groups, list) or not all(isinstance(g, str) for g in groups):
        raise SubmissionError("evaluation.json: 'groups' must be a list of strings.")
    if not (len(y_true) == len(y_pred) == len(baseline) == len(groups)):
        raise SubmissionError("evaluation.json: lists must be the same length.")
    return Evaluation(y_true, y_pred, baseline, groups)


def parse_bundle(raw: RawBundle) -> Submission:
    weights = _parse_weights(_json(raw.profile, PROFILE_FILE))
    evaluation = (
        _parse_evaluation(_json(raw.evaluation, EVALUATION_FILE))
        if raw.evaluation is not None
        else None
    )
    return Submission(raw.name, weights, evaluation, hash_raw(raw))


def load_submission(artifact_path: str, source: "Path | BundleSource") -> Submission:
    """Read and validate a bundle. A Path is a base directory of bundle folders."""
    return parse_bundle(fetch_bundle(artifact_path, source))


def bundle_hash(artifact_path: str, source: "Path | BundleSource") -> str:
    return hash_raw(fetch_bundle(artifact_path, source))
