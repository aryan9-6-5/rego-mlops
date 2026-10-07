import json
from pathlib import Path

import pytest

from src.lib.model_bundle import SubmissionError, load_submission

EVAL = {
    "y_true": [1, 0],
    "y_pred": [1, 0],
    "baseline_y_pred": [1, 1],
    "groups": ["a", "b"],
}


def bundle(base: Path, name: str = "m1", **files: object) -> None:
    folder = base / name
    folder.mkdir()
    for filename, content in files.items():
        (folder / f"{filename}.json").write_text(json.dumps(content))


def test_loads_profile_and_evaluation(tmp_path: Path) -> None:
    bundle(tmp_path, profile={"weights": {"income_weight": 0.4}}, evaluation=EVAL)
    sub = load_submission("m1", tmp_path)
    assert sub.model_version == "m1"
    assert sub.weights == {"income_weight": 0.4}
    assert sub.evaluation is not None and sub.evaluation.groups == ["a", "b"]


def test_evaluation_is_optional(tmp_path: Path) -> None:
    bundle(tmp_path, profile={"weights": {"a_weight": 1}})
    assert load_submission("m1", tmp_path).evaluation is None


@pytest.mark.parametrize("path", ["../outside", "/etc", "m1/../../x"])
def test_rejects_paths_outside_base_dir(tmp_path: Path, path: str) -> None:
    (tmp_path / "base").mkdir()
    bundle(tmp_path / "base", profile={"weights": {"a_weight": 1}})
    with pytest.raises(SubmissionError):
        load_submission(path, tmp_path / "base")


def test_missing_directory(tmp_path: Path) -> None:
    with pytest.raises(SubmissionError):
        load_submission("nope", tmp_path)


@pytest.mark.parametrize(
    "profile",
    [{}, {"weights": {}}, {"weights": {"a": "high"}}, {"weights": []}],
)
def test_rejects_bad_profile(tmp_path: Path, profile: object) -> None:
    bundle(tmp_path, profile=profile)
    with pytest.raises(SubmissionError):
        load_submission("m1", tmp_path)


@pytest.mark.parametrize(
    "bad",
    [
        {**EVAL, "y_pred": [1]},  # length mismatch
        {**EVAL, "y_true": [1, 2]},  # not binary
        {**EVAL, "groups": [1, 2]},
        [],
    ],
)
def test_rejects_bad_evaluation(tmp_path: Path, bad: object) -> None:
    bundle(tmp_path, profile={"weights": {"a_weight": 1}}, evaluation=bad)
    with pytest.raises(SubmissionError):
        load_submission("m1", tmp_path)
