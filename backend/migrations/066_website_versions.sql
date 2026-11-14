-- Migration 066: website version history (undo for a merchant's page)
--
-- Every path that overwrites a site's HTML (editor save, AI regenerate,
-- Design Studio repaint, contact edit, hero-video patch, restore) first
-- stores the page AS IT WAS in this table, so a bad regenerate or a wrong
-- save is no longer permanent. See services/website_versions.py.
--
--   * A row is the page BEFORE the change named in `source`.
--   * `content_hash` (SHA-256 of the html) lets the service skip a snapshot
--     identical to the newest one without reading the html back.
--   * The service keeps only the newest 20 rows per website.
--
-- Only the backend (service role) touches this table; RLS is on with no
-- policies so the anon/authenticated keys cannot read a merchant's pages.
-- Ownership is enforced in the API (website.user_id == caller).

CREATE TABLE IF NOT EXISTS public.website_versions (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    website_id    UUID NOT NULL REFERENCES public.websites(id) ON DELETE CASCADE,
    html          TEXT NOT NULL,
    content_hash  TEXT NOT NULL,
    source        TEXT NOT NULL DEFAULT 'manual_save'
                  CHECK (source IN ('manual_save', 'regenerate', 'theme',
                                    'contact', 'hero_video', 'restore',
                                    'publish')),
    label         TEXT CHECK (label IS NULL OR char_length(label) <= 80),
    size_bytes    INTEGER NOT NULL DEFAULT 0,
    created_by    UUID,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- The only read pattern: one website's versions, newest first.
CREATE INDEX IF NOT EXISTS website_versions_site_created_idx
    ON public.website_versions (website_id, created_at DESC);

ALTER TABLE public.website_versions ENABLE ROW LEVEL SECURITY;

COMMENT ON TABLE public.website_versions IS
    'Snapshots of a website''s HTML taken before each overwrite (newest 20 kept per site). Backend/service-role only.';
