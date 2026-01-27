-- ==========================================
-- BinaApp - Generation Jobs Table
-- ==========================================
-- This table stores async generation job data
-- to persist across multiple Render workers
-- ==========================================

-- Create generation_jobs table
CREATE TABLE IF NOT EXISTS generation_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id TEXT UNIQUE NOT NULL,
    status TEXT DEFAULT 'processing',
    progress INTEGER DEFAULT 0,
    html TEXT,
    styles JSONB,
    error TEXT,
    description TEXT,
    language TEXT DEFAULT 'ms',
    user_id TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create index for fast job_id lookups
CREATE INDEX IF NOT EXISTS idx_generation_jobs_job_id ON generation_jobs(job_id);

-- Create index for user_id lookups
CREATE INDEX IF NOT EXISTS idx_generation_jobs_user_id ON generation_jobs(user_id);

-- Create index for status filtering
CREATE INDEX IF NOT EXISTS idx_generation_jobs_status ON generation_jobs(status);

-- Add comments for documentation
COMMENT ON TABLE generation_jobs IS 'Stores async website generation jobs to persist across workers';
COMMENT ON COLUMN generation_jobs.job_id IS 'Unique job identifier returned to client';
COMMENT ON COLUMN generation_jobs.status IS 'Job status: processing, completed, failed';
COMMENT ON COLUMN generation_jobs.progress IS 'Progress percentage (0-100)';
COMMENT ON COLUMN generation_jobs.html IS 'Generated HTML content (for single style)';
COMMENT ON COLUMN generation_jobs.styles IS 'JSON array of style variations with html';
COMMENT ON COLUMN generation_jobs.error IS 'Error message if status is failed';

-- Auto-delete old jobs after 24 hours (optional cleanup)
-- You can set up a pg_cron job or run this periodically
-- DELETE FROM generation_jobs WHERE created_at < NOW() - INTERVAL '24 hours';
