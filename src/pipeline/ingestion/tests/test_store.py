from src.lib.tests.fake_supabase import FakeClient
from src.pipeline.ingestion.store import SupabaseRegulationStore

ROW = {"id": "r1", "rule_id": "RBI-4.1", "status": "active"}


def test_insert_returns_the_stored_row() -> None:
    client = FakeClient([ROW])
    store = SupabaseRegulationStore(client)
    assert store.insert({"rule_id": "RBI-4.1"}) == ROW
    assert client.last.table_name == "regulations"
    assert client.last.called("insert") == [({"rule_id": "RBI-4.1"},)]


def test_get_returns_none_when_there_is_no_row() -> None:
    assert SupabaseRegulationStore(FakeClient([])).get("missing") is None
    assert SupabaseRegulationStore(FakeClient([ROW])).get("r1") == ROW


def test_update_targets_one_row() -> None:
    client = FakeClient([ROW])
    SupabaseRegulationStore(client).update("r1", {"status": "rejected"})
    assert client.last.called("eq") == [("id", "r1")]
    assert client.last.called("update") == [({"status": "rejected"},)]


def test_list_by_status_filters_and_orders_newest_first() -> None:
    client = FakeClient([ROW])
    rows = SupabaseRegulationStore(client).list_by_status(["active", "pending_approval"])
    assert rows == [ROW]
    assert client.last.called("in_") == [("status", ["active", "pending_approval"])]
    assert client.last.called("order")[0][0] == "created_at"


def test_active_rows_for_a_rule_are_queried_by_rule_id_and_status() -> None:
    client = FakeClient([ROW])
    SupabaseRegulationStore(client).list_active_for_rule("RBI-4.1")
    assert ("rule_id", "RBI-4.1") in client.last.called("eq")
    assert ("status", "active") in client.last.called("eq")
