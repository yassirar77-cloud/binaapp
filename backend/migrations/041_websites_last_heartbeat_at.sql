-- Migration 041: Add last_heartbeat_at to websites for stuck-generation
-- detection.
--
-- Background tasks that run AI generation now write a heartbeat
-- timestamp every HEARTBEAT_INTERVAL_SECONDS (default 30s). A scheduler
-- job sweeps for rows stuck on status='generating' with a stale
-- heartbeat AND stale updated_at, and flips them to 'failed' so the
-- user isn't blocked forever after a Render worker restart.
--
-- The column is NULL for rows that aren't actively generating, and
-- explicitly cleared at the end of every generation (success or
-- failure). Backfill is NOT required — the scheduler treats NULL OR
-- stale as the stuck condition, gated additionally by updated_at, so
-- pre-existing rows in any status are safe.

ALTER TABLE websites
    ADD COLUMN IF NOT EXISTS last_heartbeat_at TIMESTAMPTZ NULL;

-- Partial index speeds up the stuck-sweep query, which only ever looks
-- at rows currently in 'generating'. Tiny in practice (most websites
-- aren't actively generating), but keeps the scheduler cheap even as
-- the table grows. IF NOT EXISTS so the migration is idempotent.
CREATE INDEX IF NOT EXISTS idx_websites_generating_heartbeat
    ON websites (last_heartbeat_at)
    WHERE status = 'generating';
