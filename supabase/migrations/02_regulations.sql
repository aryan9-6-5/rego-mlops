-- 02_regulations.sql
-- Description: Regulatory rules extracted by LLM and validated by Z3.

CREATE TYPE regulation_status AS ENUM (
    'extracted', 
    'z3_validated', 
    'z3_rejected', 
    'pending_approval', 
    'approved', 
    'rejected', 
    'active'
);

CREATE TABLE IF NOT EXISTS regulations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    rule_id TEXT NOT NULL,
    jurisdiction TEXT NOT NULL DEFAULT 'India',
    source_text TEXT NOT NULL,
    formal_logic TEXT NOT NULL,
    status regulation_status NOT NULL DEFAULT 'extracted',
    version TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    approved_by UUID REFERENCES auth.users(id),
    approved_at TIMESTAMPTZ,
    
    -- Constraint: rule_id + version combination should be unique
    UNIQUE (rule_id, version)
);

-- Enable RLS
ALTER TABLE regulations ENABLE ROW LEVEL SECURITY;

-- Policies
CREATE POLICY "Public read for active regulations" ON regulations
    FOR SELECT USING (status = 'active');

CREATE POLICY "Compliance Officers can manage all regulations" ON regulations
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM users WHERE id = auth.uid() AND role = 'compliance_officer'
        )
    );
