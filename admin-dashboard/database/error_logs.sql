-- BinaApp Admin Dashboard - Error Logs Table
-- Run this SQL in Supabase SQL Editor to create the error_logs table.
-- This is a NEW table and does NOT modify any existing tables.

CREATE TABLE IF NOT EXISTS error_logs (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  error_type TEXT NOT NULL,        -- 'deepseek', 'qwen', 'stability', 'payment', 'auth', 'publish'
  severity TEXT DEFAULT 'error',   -- 'critical', 'error', 'warning', 'info'
  message TEXT NOT NULL,
  user_id UUID REFERENCES auth.users(id),
  job_id UUID,
  metadata JSONB,                  -- extra context (API response, status code, etc.)
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_error_logs_created ON error_logs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_error_logs_type ON error_logs(error_type);
CREATE INDEX IF NOT EXISTS idx_error_logs_severity ON error_logs(severity);
CREATE INDEX IF NOT EXISTS idx_error_logs_user ON error_logs(user_id);

-- Enable RLS (service role key bypasses this)
ALTER TABLE error_logs ENABLE ROW LEVEL SECURITY;

-- Allow service role to read/write all error logs
-- No public access policy needed since admin dashboard uses service role key
