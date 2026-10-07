from datetime import datetime, timezone

from src.pipeline.ingestion.versioner import make_version_id, new_version


def test_versions_created_microseconds_apart_are_different() -> None:
    first = datetime(2026, 10, 7, 12, 0, 0, 100, tzinfo=timezone.utc)
    second = datetime(2026, 10, 7, 12, 0, 0, 200, tzinfo=timezone.utc)
    assert new_version(first) != new_version(second)


def test_version_id_is_the_rule_id_plus_the_timestamp() -> None:
    stamp = new_version(datetime(2026, 10, 7, 12, 0, 0, 5, tzinfo=timezone.utc))
    assert stamp == "20261007T120000000005Z"
    assert make_version_id("RBI-4.1", stamp) == "RBI-4.1-20261007T120000000005Z"
