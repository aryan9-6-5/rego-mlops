-- Description: Stream pipeline_events to the dashboards (Stage 3.7).
-- Realtime applies row level security, so only signed-in users receive rows.
ALTER PUBLICATION supabase_realtime ADD TABLE pipeline_events;
