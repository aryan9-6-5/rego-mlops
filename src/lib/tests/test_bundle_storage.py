"""Reading and writing model bundles in Supabase Storage (and the local folder)."""

import json
from pathlib import Path
from typing import Any

import pytest

from src.lib.model_bundle import (
    DEFAULT_BUCKET,
    BundleStorageError,
    LocalBundleSource,
    SubmissionError,
    SupabaseBundleSource,
    bundle_hash,
    fetch_bundle,
    load_submission,
)

PROFILE = json.dumps({"weights": {"age_weight": 0.2, "income_weight": 0.4}}).encode()
EVALUATION = json.dumps(
    {"y_true": [1, 0], "y_pred": [1, 0], "baseline_y_pred": [1, 0], "groups": ["a", "b"]}
).encode()


class StorageApiError(Exception):
    def __init__(self, message: str, status: int) -> None:
        super().__init__(message)
        self.status = status


class FakeBucket:
    def __init__(self, store: "FakeStorage") -> None:
        self.store = store

    def download(self, path: str) -> bytes:
        self.store.calls.append(("download", path))
        if self.store.error is not None:
            raise self.store.error
        if path not in self.store.objects:
            raise StorageApiError("Object not found", 404)
        return self.store.objects[path]

    def upload(self, path: str, data: bytes, options: dict[str, str]) -> None:
        self.store.calls.append(("upload", path))
        self.store.options.append(options)
        if self.store.error is not None:
            raise self.store.error
        self.store.objects[path] = data


class FakeStorage:
    """Stands in for `client.storage` of supabase-py."""

    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}
        self.calls: list[tuple[str, str]] = []
        self.options: list[dict[str, str]] = []
        self.error: Exception | None = None
        self.bucket_names: list[str] = []

    def from_(self, bucket: str) -> FakeBucket:
        self.bucket_names.append(bucket)
        return FakeBucket(self)


class FakeClient:
    def __init__(self) -> None:
        self.storage = FakeStorage()


@pytest.fixture
def client() -> FakeClient:
    c = FakeClient()
    c.storage.objects = {"m1/profile.json": PROFILE, "m1/evaluation.json": EVALUATION}
    return c


def test_a_bundle_is_read_from_the_private_bucket(client: FakeClient) -> None:
    submission = load_submission("m1", SupabaseBundleSource(client))
    assert submission.weights == {"age_weight": 0.2, "income_weight": 0.4}
    assert submission.evaluation is not None
    assert set(client.storage.bucket_names) == {DEFAULT_BUCKET}
    assert ("download", "m1/profile.json") in client.storage.calls


def test_the_bucket_name_is_configurable(client: FakeClient) -> None:
    fetch_bundle("m1", SupabaseBundleSource(client, "other-bucket"))
    assert set(client.storage.bucket_names) == {"other-bucket"}


def test_evaluation_data_is_optional(client: FakeClient) -> None:
    del client.storage.objects["m1/evaluation.json"]
    assert load_submission("m1", SupabaseBundleSource(client)).evaluation is None


def test_a_missing_bundle_is_a_submission_error_not_a_storage_error(client: FakeClient) -> None:
    with pytest.raises(SubmissionError, match="not found"):
        load_submission("ghost", SupabaseBundleSource(client))


def test_a_not_found_reported_in_words_only_is_still_not_found(client: FakeClient) -> None:
    client.storage.error = RuntimeError("The resource was Not Found")
    with pytest.raises(SubmissionError, match="not found"):
        load_submission("m1", SupabaseBundleSource(client))


def test_an_outage_is_a_storage_error_and_does_not_leak_the_cause(client: FakeClient) -> None:
    client.storage.error = ConnectionError("dns failure for storage.internal-host")
    with pytest.raises(BundleStorageError) as caught:
        load_submission("m1", SupabaseBundleSource(client))
    assert "internal-host" not in str(caught.value)


def test_an_oversized_object_is_refused(client: FakeClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("src.lib.model_bundle.MAX_FILE_BYTES", 10)
    with pytest.raises(SubmissionError, match="too large"):
        load_submission("m1", SupabaseBundleSource(client))


@pytest.mark.parametrize(
    "name", ["", "..", ".", "../x", "a/b", "a b", "x" * 201, "name;rm", "m1/../m2"]
)
def test_unsafe_names_never_reach_storage(client: FakeClient, name: str) -> None:
    with pytest.raises(SubmissionError):
        fetch_bundle(name, SupabaseBundleSource(client))
    assert client.storage.calls == []


def test_the_same_files_have_the_same_hash_whether_local_or_stored(
    client: FakeClient, tmp_path: Path
) -> None:
    (tmp_path / "m1").mkdir()
    (tmp_path / "m1" / "profile.json").write_bytes(PROFILE)
    (tmp_path / "m1" / "evaluation.json").write_bytes(EVALUATION)
    assert bundle_hash("m1", tmp_path) == bundle_hash("m1", SupabaseBundleSource(client))
    assert load_submission("m1", tmp_path).bundle_hash == bundle_hash("m1", tmp_path)


def test_changing_one_byte_changes_the_hash(client: FakeClient) -> None:
    before = bundle_hash("m1", SupabaseBundleSource(client))
    client.storage.objects["m1/profile.json"] = PROFILE.replace(b"0.4", b"0.5")
    assert bundle_hash("m1", SupabaseBundleSource(client)) != before


# ---- upload ---------------------------------------------------------------------


def write_local(folder: Path, with_evaluation: bool = True) -> None:
    folder.mkdir()
    (folder / "profile.json").write_bytes(PROFILE)
    if with_evaluation:
        (folder / "evaluation.json").write_bytes(EVALUATION)
    (folder / "model.pkl").write_bytes(b"large binary that must not be uploaded")


def test_upload_sends_only_the_two_json_files_as_json(tmp_path: Path) -> None:
    client = FakeClient()
    write_local(tmp_path / "ct-1")
    SupabaseBundleSource(client).upload("ct-1", tmp_path / "ct-1")
    assert sorted(client.storage.objects) == ["ct-1/evaluation.json", "ct-1/profile.json"]
    assert all(o["content-type"] == "application/json" for o in client.storage.options)


def test_upload_replaces_a_bundle_and_the_hash_follows_the_new_bytes(tmp_path: Path) -> None:
    client = FakeClient()
    source = SupabaseBundleSource(client)
    write_local(tmp_path / "ct-1")
    source.upload("ct-1", tmp_path / "ct-1")
    first = bundle_hash("ct-1", source)
    (tmp_path / "ct-1" / "profile.json").write_bytes(PROFILE.replace(b"0.4", b"0.9"))
    source.upload("ct-1", tmp_path / "ct-1")
    assert bundle_hash("ct-1", source) != first
    assert all(o["upsert"] == "true" for o in client.storage.options)


def test_upload_needs_a_profile_and_a_safe_name(tmp_path: Path) -> None:
    source = SupabaseBundleSource(FakeClient())
    (tmp_path / "empty").mkdir()
    with pytest.raises(SubmissionError, match="profile.json"):
        source.upload("empty", tmp_path / "empty")
    write_local(tmp_path / "ok")
    with pytest.raises(SubmissionError):
        source.upload("../escape", tmp_path / "ok")


def test_an_upload_outage_is_a_storage_error(tmp_path: Path) -> None:
    client = FakeClient()
    client.storage.error = ConnectionError("down")
    write_local(tmp_path / "ct-1")
    with pytest.raises(BundleStorageError):
        SupabaseBundleSource(client).upload("ct-1", tmp_path / "ct-1")


# ---- the local source keeps its old behaviour ---------------------------------------


def test_the_local_source_cannot_leave_its_folder(tmp_path: Path) -> None:
    (tmp_path / "base").mkdir()
    (tmp_path / "secret").mkdir()
    (tmp_path / "secret" / "profile.json").write_bytes(PROFILE)
    source: Any = LocalBundleSource(tmp_path / "base")
    with pytest.raises(SubmissionError):
        source.read("../secret", "profile.json")
    with pytest.raises(SubmissionError):
        source.read("..", "profile.json")
