-- ==========================================================================
-- Migration 034: Reconcile usage_tracking.websites_count with reality
-- ==========================================================================
-- Sets every existing usage_tracking row's websites_count to the actual
-- COUNT(*) from the websites table for that user. Idempotent — only
-- updates rows where the values differ.
--
-- Root cause of drift: frontend dashboard/page.tsx:141-144 deletes
-- websites via the anon supabase client, bypassing the backend's
-- DELETE /api/v1/websites/{id} endpoint that calls decrement_usage().
-- The cached tracker value drifts up by 1 every time a user deletes
-- from the dashboard. Phase 2 commit a5a410f (G.1 self-healing on read)
-- prevents further drift by persisting the corrected value when detected.
--
-- Limits-aware: subscription_service.get_or_create_usage_tracking
-- already overrides the in-memory websites_count with actual count
-- before returning, so limit gating was never wrong — only the stored
-- counter was stale.
--
-- Safe: UPDATE only. Targets only rows where drift exists.
-- For the current data this updated exactly 1 row
-- (yassirarafat33: 64 → 60).
-- ==========================================================================

BEGIN;

WITH actual AS (
  SELECT u.id AS user_id, COUNT(w.id) AS cnt
  FROM auth.users u
  LEFT JOIN public.websites w ON w.user_id = u.id
  GROUP BY u.id
)
UPDATE public.usage_tracking ut
SET websites_count = a.cnt,
    updated_at     = NOW()
FROM actual a
WHERE ut.user_id = a.user_id
  AND ut.websites_count IS DISTINCT FROM a.cnt;

DO $$
DECLARE
  v_drift INT;
BEGIN
  WITH actual AS (
    SELECT u.id AS user_id, COUNT(w.id) AS cnt
    FROM auth.users u
    LEFT JOIN public.websites w ON w.user_id = u.id
    GROUP BY u.id
  )
  SELECT COUNT(*) INTO v_drift
  FROM public.usage_tracking ut
  JOIN actual a ON a.user_id = ut.user_id
  WHERE ut.websites_count IS DISTINCT FROM a.cnt;
  RAISE NOTICE 'Migration 034 complete. Drifted rows remaining: % (expected 0)', v_drift;
END $$;

COMMIT;
