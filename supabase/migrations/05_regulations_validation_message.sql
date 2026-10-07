-- Description: Z3 rejection reason / human rejection note, shown to the CO.
ALTER TABLE regulations ADD COLUMN IF NOT EXISTS validation_message TEXT;
