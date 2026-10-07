-- Description: Keep superseded regulation versions for lineage history (Stage 3.2).
ALTER TYPE regulation_status ADD VALUE IF NOT EXISTS 'superseded';
