-- 09_model_bundle_storage.sql
-- Description: where model bundles are kept in production, and tying CI results to
-- the exact files they were run on.
--
-- Model bundles (profile.json, evaluation.json) live in a PRIVATE Storage bucket.
-- No storage policy is created, so only the backend (service key) can read or write
-- it. Browsers never reach it. Objects are named <model_version>/<file>.

INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES ('model-bundles', 'model-bundles', false, 52428800, ARRAY['application/json'])
ON CONFLICT (id) DO UPDATE
    SET public = false,
        file_size_limit = EXCLUDED.file_size_limit,
        allowed_mime_types = EXCLUDED.allowed_mime_types;

-- A deploy is allowed only if every CI gate passed on the same bytes it is about
-- to deploy. Bundles live in storage that can be written, so a pass on old files
-- must not carry over to replaced files.
ALTER TABLE pipeline_events ADD COLUMN IF NOT EXISTS bundle_hash TEXT;
