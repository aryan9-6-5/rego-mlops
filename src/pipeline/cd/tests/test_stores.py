from typing import Any

import pytest

from src.lib.tests.fake_supabase import FakeClient
from src.pipeline.cd.certificate import DuplicateCertificateError
from src.pipeline.cd.stores import SupabaseCertificateStore, SupabaseCIEventReader

ROW = {"id": "c1", "model_version": "v1"}


class UniqueViolation(Exception):
    code = "23505"


def test_insert_get_and_list_read_the_certificates_table() -> None:
    client = FakeClient([ROW])
    store = SupabaseCertificateStore(client)
    assert store.insert({"model_version": "v1"}) == ROW
    assert store.get("c1") == ROW
    assert store.list_latest() == [ROW]
    assert {q.table_name for q in client.queries} == {"certificates"}
    assert client.last.called("order")[0][0] == "created_at"


def test_get_returns_none_for_a_missing_certificate() -> None:
    assert SupabaseCertificateStore(FakeClient([])).get("nope") is None


def test_a_unique_violation_becomes_a_duplicate_certificate_error() -> None:
    client = FakeClient()
    client.error = UniqueViolation("23505")
    with pytest.raises(DuplicateCertificateError):
        SupabaseCertificateStore(client).insert({"model_version": "v1"})


def test_a_duplicate_key_message_is_also_recognised() -> None:
    client = FakeClient()
    client.error = RuntimeError('duplicate key value violates unique constraint "x"')
    with pytest.raises(DuplicateCertificateError):
        SupabaseCertificateStore(client).insert({"model_version": "v1"})


def test_other_database_errors_are_not_swallowed() -> None:
    client = FakeClient()
    client.error = RuntimeError("connection reset")
    with pytest.raises(RuntimeError, match="connection reset"):
        SupabaseCertificateStore(client).insert({"model_version": "v1"})


def test_the_store_has_no_update_or_delete_methods() -> None:
    store = SupabaseCertificateStore(FakeClient())
    assert not hasattr(store, "update") and not hasattr(store, "delete")


def test_the_latest_result_per_gate_wins() -> None:
    rows = [  # newest first, as the query orders them
        {"gate_name": "symbolic_check", "status": "violation"},
        {"gate_name": "regression", "status": "compliant"},
        {"gate_name": "symbolic_check", "status": "compliant"},
    ]
    client = FakeClient(rows)
    latest = SupabaseCIEventReader(client).latest_gate_statuses("v1")
    assert latest == {"symbolic_check": "violation", "regression": "compliant"}
    assert ("stage", "ci") in client.last.called("eq")
    assert ("model_version", "v1") in client.last.called("eq")


def test_the_latest_bundle_hash_per_gate_wins_and_old_rows_without_one_are_none() -> None:
    rows: list[dict[str, Any]] = [  # newest first
        {"gate_name": "symbolic_check", "bundle_hash": "new"},
        {"gate_name": "regression", "bundle_hash": None},
        {"gate_name": "symbolic_check", "bundle_hash": "old"},
    ]
    client = FakeClient(rows)
    hashes = SupabaseCIEventReader(client).latest_bundle_hashes("v1")
    assert hashes == {"symbolic_check": "new", "regression": None}
    assert ("stage", "ci") in client.last.called("eq")
