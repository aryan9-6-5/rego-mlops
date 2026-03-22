-- 04_pipeline_events.sql
-- Description: Audit log for all pipeline gate executions.

CREATE TABLE IF NOT EXISTS pipeline_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    stage TEXT NOT NULL,
    gate_name TEXT NOT NULL,
    status TEXT NOT NULL,
    model_version TEXT NOT NULL,
    rule_ids JSONB NOT NULL,
    duration_ms INTEGER NOT NULL,
    plain_english_result TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Enable RLS
ALTER TABLE pipeline_events ENABLE ROW LEVEL SECURITY;

-- Policies
CREATE POLICY "Users can view pipeline events" ON pipeline_events
    FOR SELECT USING (auth.role() = 'authenticated');
