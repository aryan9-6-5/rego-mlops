"""Static review of the row level security migration (Stage 4.1).

These checks read the SQL. They cannot prove how Postgres behaves; the live check
is to run the migrations on Supabase and try each role through PostgREST.
"""

import re
from pathlib import Path

MIGRATIONS = Path(__file__).resolve().parents[2] / "supabase" / "migrations"
RLS = (MIGRATIONS / "08_tighten_rls.sql").read_text(encoding="utf-8")


def policies() -> dict[str, str]:
    """Policy name -> full CREATE POLICY statement in migration 08."""
    return {
        m.group(1): m.group(0)
        for m in re.finditer(r'CREATE POLICY "([^"]+)"[^;]*;', RLS, re.DOTALL)
    }


def test_the_risky_original_policies_are_dropped() -> None:
    for name in (
        "Public read for active regulations",
        "Compliance Officers can manage all regulations",
        "Public read for certificates (auditors)",
        "ML Engineers can insert certificates",
        "Users can view pipeline events",
    ):
        assert f'DROP POLICY IF EXISTS "{name}"' in RLS


def test_every_policy_is_select_only_and_for_signed_in_users() -> None:
    created = policies()
    assert created
    for name, statement in created.items():
        assert "FOR SELECT" in statement, name
        assert "TO authenticated" in statement, name
        assert "USING (true)" not in statement, name


def test_the_users_policy_no_longer_queries_users_from_inside_itself() -> None:
    cto = policies()["CTOs can view all users"]
    assert "FROM users" not in cto and "public.rego_role()" in cto
    assert "SECURITY DEFINER" in RLS


def test_anonymous_users_get_no_table_privileges() -> None:
    assert re.search(
        r"REVOKE ALL ON users, regulations, certificates, pipeline_events FROM anon",
        RLS,
    )


def test_certificates_are_append_only_for_every_role() -> None:
    assert "REVOKE UPDATE, DELETE, TRUNCATE ON certificates FROM service_role" in RLS
    assert "BEFORE UPDATE OR DELETE ON certificates" in RLS
    assert "certificates are immutable" in RLS


def test_the_certificates_table_has_no_updated_at_column() -> None:
    sql = (MIGRATIONS / "03_certificates.sql").read_text(encoding="utf-8")
    code = re.sub(r"--[^\n]*", "", sql)  # comments may mention the word
    create = code[code.index("CREATE TABLE") : code.index(");")]
    assert "updated_at" not in create


def test_model_bundles_live_in_a_private_bucket_with_no_storage_policy() -> None:
    sql = (MIGRATIONS / "09_model_bundle_storage.sql").read_text(encoding="utf-8")
    code = re.sub(r"--[^\n]*", "", sql)
    assert "'model-bundles', 'model-bundles', false" in code
    assert "public = false" in code
    assert "CREATE POLICY" not in code  # only the service key can reach it
    assert "ALTER TABLE pipeline_events ADD COLUMN IF NOT EXISTS bundle_hash" in code
