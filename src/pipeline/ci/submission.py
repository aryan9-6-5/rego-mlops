import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

MAX_EVAL_ROWS = 1_000_000


class SubmissionError(Exception):
    """Raised when a model bundle is missing, malformed or outside the base dir."""


@dataclass(frozen=True)
class Evaluation:
    """Held-out predictions produced by the training step."""

    y_true: list[int]
    y_pred: list[int]
    baseline_y_pred: list[int]
    groups: list[str]


@dataclass(frozen=True)
class Submission:
    """A model bundle: a directory holding `profile.json` (feature weights, named
    `<feature>_weight`) and `evaluation.json` (held-out predictions)."""

    model_version: str
    weights: dict[str, float | bool]
    evaluation: Evaluation | None


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        raise SubmissionError(f"Could not read {path.name}.") from e


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


def load_submission(artifact_path: str, base_dir: Path) -> Submission:
    """Load a bundle. The path must resolve to a directory inside `base_dir`."""
    base = base_dir.resolve()
    target = (base / artifact_path).resolve()
    if base != target and base not in target.parents:
        raise SubmissionError("Artifact path is outside the model directory.")
    if not target.is_dir():
        raise SubmissionError("Artifact directory not found.")
    weights = _parse_weights(_read_json(target / "profile.json"))
    evaluation_file = target / "evaluation.json"
    evaluation = (
        _parse_evaluation(_read_json(evaluation_file))
        if evaluation_file.exists()
        else None
    )
    return Submission(target.name, weights, evaluation)
