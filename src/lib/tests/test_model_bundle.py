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


def test_an_unreadable_or_non_json_profile_is_a_clear_error(tmp_path: Path) -> None:
    (tmp_path / "m1").mkdir()
    (tmp_path / "m1" / "profile.json").write_text("{not json")
    with pytest.raises(SubmissionError, match="profile.json"):
        load_submission("m1", tmp_path)


def test_an_evaluation_list_that_is_not_a_list_is_rejected(tmp_path: Path) -> None:
    bundle(tmp_path, profile={"weights": {"a_weight": 1}}, evaluation={**EVAL, "y_true": "10"})
    with pytest.raises(SubmissionError, match="must be a list"):
        load_submission("m1", tmp_path)


def test_the_bundle_hash_changes_when_any_file_changes(tmp_path: Path) -> None:
    from src.lib.model_bundle import bundle_hash

    bundle(tmp_path, profile={"weights": {"a_weight": 1}}, evaluation=EVAL)
    first = bundle_hash("m1", tmp_path)
    assert first == bundle_hash("m1", tmp_path)
    (tmp_path / "m1" / "profile.json").write_text(json.dumps({"weights": {"a_weight": 2}}))
    assert bundle_hash("m1", tmp_path) != first


def test_the_bundle_hash_refuses_paths_outside_the_base_dir(tmp_path: Path) -> None:
    from src.lib.model_bundle import bundle_hash

    with pytest.raises(SubmissionError):
        bundle_hash("../elsewhere", tmp_path)
