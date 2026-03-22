-- 03_certificates.sql
-- Description: Immutable proof certificates for model deployments.
-- Rule 4: No updated_at path allowed.

CREATE TABLE IF NOT EXISTS certificates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    model_version TEXT NOT NULL,
    regulation_versions JSONB NOT NULL,
    proof_hash TEXT NOT NULL UNIQUE,
    hmac_signature TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
    
    -- IMPORTANT: No updated_at column or trigger. 
    -- This table is write-once (Append-only).
);

-- Enable RLS
ALTER TABLE certificates ENABLE ROW LEVEL SECURITY;

-- Policies
CREATE POLICY "Public read for certificates (auditors)" ON certificates
    FOR SELECT USING (true);

CREATE POLICY "ML Engineers can insert certificates" ON certificates
    FOR INSERT WITH CHECK (
        EXISTS (
            SELECT 1 FROM users WHERE id = auth.uid() AND role = 'ml_engineer'
        )
    );
