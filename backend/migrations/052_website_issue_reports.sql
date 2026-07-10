-- ==========================================================================
-- Migration 052: "Report Issue → Free Regeneration" make-good flow
-- ==========================================================================
-- PURPOSE:
-- Users whose generated site came out broken (wrong images, garbled text,
-- broken page, sensitive content) can file an issue report. The first
-- ISSUE_FREE_REGEN_CAP reports per site (env, default 2) auto-grant a FREE
-- regeneration — one regen that bypasses the generate_ai_hero quota check
-- and does not charge ai_images_used. Reports beyond the cap are escalated
-- for manual admin review.
--
-- QUOTA SAFETY (read this before touching):
--   The free regen is a PER-SITE grant tracked by websites.free_regens_granted
--   + the report row's (status='auto_regen_granted', regen_used=false) pair.
--   It NEVER mutates the user's usage_tracking counters or subscription/
--   addon rows — the bypass is an explicit flag threaded through the
--   regenerate endpoint (see websites.py), not a quota decrement/refund.
--
-- LIFECYCLE:
--   open               — created, no auto-grant (unused today; reserved)
--   auto_regen_granted — created within the cap; entitles ONE free regen
--   escalated          — cap exhausted; awaiting admin review
--   resolved           — free regen completed successfully, or admin resolved
--   rejected           — admin rejected
--   A granted report flips regen_used=true + status='resolved' ONLY when the
--   regeneration completes successfully; a failed generation leaves it
--   untouched so the user can retry without burning the grant.
--
-- Backward compatibility: the websites column has a default, so existing
-- INSERTs and reads keep working (same approach as migration 039).
-- ==========================================================================

-- ==========================================================================
-- SECTION 1: PER-SITE FREE-REGEN GRANT COUNTER
-- ==========================================================================
-- Counts grants EVER issued for this site (monotonic — never decremented),
-- compared against ISSUE_FREE_REGEN_CAP at report time. Kept on the websites
-- row (not a separate counter table) to match the schema style of migration
-- 039's generation_count.

ALTER TABLE public.websites
  ADD COLUMN IF NOT EXISTS free_regens_granted INTEGER NOT NULL DEFAULT 0;

COMMENT ON COLUMN public.websites.free_regens_granted IS
    'Number of free make-good regenerations ever granted to this site via '
    'issue reports. Monotonic; compared against ISSUE_FREE_REGEN_CAP '
    '(default 2). Does NOT interact with usage_tracking quota counters.';

-- ==========================================================================
-- SECTION 2: ISSUE REPORTS TABLE
-- ==========================================================================

CREATE TABLE IF NOT EXISTS public.website_issue_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    website_id UUID NOT NULL REFERENCES public.websites(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    category TEXT NOT NULL CHECK (category IN (
        'images_wrong', 'text_wrong', 'page_broken', 'sensitive_content', 'other'
    )),
    -- Optional free-text detail from the user. 500-char ceiling enforced
    -- both here and in the Pydantic request model.
    description TEXT CHECK (description IS NULL OR char_length(description) <= 500),
    status TEXT NOT NULL DEFAULT 'open' CHECK (status IN (
        'open', 'auto_regen_granted', 'escalated', 'resolved', 'rejected'
    )),
    -- TRUE once the granted free regeneration has been consumed
    -- (set together with status='resolved' on generation success).
    regen_used BOOLEAN NOT NULL DEFAULT FALSE,
    -- Lightweight diagnostics snapshot captured at report time: html hash +
    -- length, generation/image provider flags, generation_count, last error.
    -- IDs and small metadata ONLY — never full HTML dumps.
    diagnostics JSONB,
    admin_note TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    resolved_at TIMESTAMPTZ
);

COMMENT ON TABLE public.website_issue_reports IS
    'User-filed issue reports on generated websites. Within the per-site cap '
    'a report auto-grants one free (quota-bypassing) regeneration; beyond it, '
    'reports escalate for admin review via /admin/issue-reports.';

-- Duplicate-check lookup: (website_id, category) with an open-ish status.
CREATE INDEX IF NOT EXISTS idx_issue_reports_website_category
  ON public.website_issue_reports(website_id, category, status);

-- Free-regen lookup at regenerate time: unused granted report for a site.
CREATE INDEX IF NOT EXISTS idx_issue_reports_website_granted
  ON public.website_issue_reports(website_id)
  WHERE status = 'auto_regen_granted' AND regen_used = FALSE;

-- Rate-limit counting (per site / per user, last 24h) + admin newest-first.
CREATE INDEX IF NOT EXISTS idx_issue_reports_website_created
  ON public.website_issue_reports(website_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_issue_reports_user_created
  ON public.website_issue_reports(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_issue_reports_status_created
  ON public.website_issue_reports(status, created_at DESC);

-- ==========================================================================
-- SECTION 3: ROW LEVEL SECURITY
-- ==========================================================================
-- Same posture as migration 049: ALL writes go through the service-role
-- FastAPI backend (which bypasses RLS). No public/anon write policies —
-- a browser holding the anon key must not be able to mint itself grants.
-- Owner SELECT is defense-in-depth for future Supabase-signed sessions
-- (today's anon-key frontend sessions have auth.uid() = NULL → 0 rows).

ALTER TABLE public.website_issue_reports ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "issue_reports_owner_select" ON public.website_issue_reports;
CREATE POLICY "issue_reports_owner_select"
  ON public.website_issue_reports
  FOR SELECT
  TO authenticated
  USING (auth.uid() = user_id);
