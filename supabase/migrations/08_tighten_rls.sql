-- 08_tighten_rls.sql
-- Description: Stage 4.1 row level security review.
--
-- Fixes found in 01-04:
--  * users: the "CTOs can view all users" policy queried users from inside a
--    users policy, which Postgres rejects as infinite recursion. It now uses a
--    SECURITY DEFINER helper.
--  * regulations: "Public read" let anyone with the (public) anon key read active
--    rules, and COs could write rows directly, skipping Z3 validation and the
--    approval flow. Reads are now for signed-in staff; writes only go through the
--    API (service key).
--  * certificates: "Public read" exposed every certificate, and "ML Engineers can
--    insert" let an engineer write certificate rows without a deployment.
--    Certificates are now written only by the API, and can never be updated or
--    deleted, even by the service role.
--  * pipeline_events: readable by signed-in staff only; written only by the API.
--
-- Auditors verify certificates through POST /api/certificates/verify, not
-- through the database.

CREATE OR REPLACE FUNCTION public.rego_role()
RETURNS user_role
LANGUAGE sql
SECURITY DEFINER
STABLE
SET search_path = public
AS $$
    SELECT role FROM public.users WHERE id = auth.uid()
$$;

REVOKE ALL ON FUNCTION public.rego_role() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.rego_role() TO authenticated;

-- users ---------------------------------------------------------------------
DROP POLICY IF EXISTS "Users can view their own profile" ON users;
DROP POLICY IF EXISTS "CTOs can view all users" ON users;

CREATE POLICY "Users can view their own profile" ON users
    FOR SELECT TO authenticated USING (auth.uid() = id);

CREATE POLICY "CTOs can view all users" ON users
    FOR SELECT TO authenticated USING (public.rego_role() = 'cto');

-- regulations ---------------------------------------------------------------
DROP POLICY IF EXISTS "Public read for active regulations" ON regulations;
DROP POLICY IF EXISTS "Compliance Officers can manage all regulations" ON regulations;

CREATE POLICY "Staff can read regulations" ON regulations
    FOR SELECT TO authenticated
    USING (public.rego_role() IN ('compliance_officer', 'cto'));

-- certificates --------------------------------------------------------------
DROP POLICY IF EXISTS "Public read for certificates (auditors)" ON certificates;
DROP POLICY IF EXISTS "ML Engineers can insert certificates" ON certificates;

CREATE POLICY "Staff can read certificates" ON certificates
    FOR SELECT TO authenticated USING (public.rego_role() IS NOT NULL);

-- pipeline_events -----------------------------------------------------------
DROP POLICY IF EXISTS "Users can view pipeline events" ON pipeline_events;

CREATE POLICY "Staff can read pipeline events" ON pipeline_events
    FOR SELECT TO authenticated USING (public.rego_role() IS NOT NULL);

-- Privileges: anon gets nothing, signed-in users can only read ---------------
REVOKE ALL ON users, regulations, certificates, pipeline_events FROM anon;
REVOKE INSERT, UPDATE, DELETE, TRUNCATE
    ON regulations, certificates, pipeline_events FROM authenticated;
REVOKE INSERT, UPDATE, DELETE, TRUNCATE ON users FROM authenticated;

-- Certificates are append-only for every role, including the service role ----
REVOKE UPDATE, DELETE, TRUNCATE ON certificates FROM service_role;

CREATE OR REPLACE FUNCTION public.certificates_are_immutable()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION 'certificates are immutable';
END;
$$;

DROP TRIGGER IF EXISTS certificates_no_update_delete ON certificates;
CREATE TRIGGER certificates_no_update_delete
    BEFORE UPDATE OR DELETE ON certificates
    FOR EACH ROW EXECUTE FUNCTION public.certificates_are_immutable();
