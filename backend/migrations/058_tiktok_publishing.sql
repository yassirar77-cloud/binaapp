-- ==========================================================================
-- Migration 058: TikTok publishing — connected account, OAuth states, posts
-- ==========================================================================
-- WHY
-- BinaApp posts marketing clips to its own TikTok account (@binaapp.my)
-- from the admin dashboard through TikTok's Content Posting API. That
-- needs three durable things the request cycle cannot hold:
--
--   1. The connected account's OAuth tokens. TikTok access tokens live
--      ~24h and refresh tokens ~365d; both are stored ENCRYPTED (Fernet,
--      key derived from TIKTOK_TOKEN_ENCRYPTION_KEY or, failing that, the
--      client secret) — the columns hold ciphertext only, never a raw token.
--   2. The OAuth `state` handed to TikTok's authorize URL. The callback
--      must prove the state was minted by us, for this admin, minutes ago,
--      and has not been used before (CSRF). One row per attempt, deleted
--      on use, expired rows swept opportunistically.
--   3. A ledger of every publish attempt (direct post or inbox upload) so
--      the admin UI can poll status after the browser request ends, and so
--      a Render restart mid-upload leaves a row that says "failed" rather
--      than nothing.
--
-- Multi-platform note: the tables are TikTok-specific by name on purpose
-- (the first platform), while the backend code lives under
-- app/services/social/ so Facebook/Instagram can be added beside it with
-- their own tables and the same shape.
--
-- Service-role only: the backend reads and writes with the service key
-- (bypasses RLS). RLS is enabled with a service_role-only policy so the
-- anon and authenticated roles see nothing — tokens never reach a browser.
-- Additive and idempotent; safe to re-run.
-- ==========================================================================

-- --------------------------------------------------------------------------
-- 1. Connected TikTok account(s)
-- --------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.tiktok_accounts (
    id                        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    open_id                   TEXT NOT NULL UNIQUE,      -- TikTok user id scoped to our app
    union_id                  TEXT,
    username                  TEXT,                      -- creator_username (@handle) when known
    display_name              TEXT,
    avatar_url                TEXT,
    scopes                    TEXT NOT NULL DEFAULT '',  -- comma-separated, as granted
    access_token_enc          TEXT NOT NULL,             -- Fernet ciphertext
    refresh_token_enc         TEXT NOT NULL,             -- Fernet ciphertext
    access_token_expires_at   TIMESTAMPTZ NOT NULL,
    refresh_token_expires_at  TIMESTAMPTZ,
    status                    TEXT NOT NULL DEFAULT 'connected'
                              CHECK (status IN ('connected', 'reauth_required', 'revoked')),
    last_error                TEXT,
    connected_by              TEXT NOT NULL,             -- BinaApp admin user id (JWT sub)
    connected_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at                TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE public.tiktok_accounts IS
  'TikTok accounts connected by a BinaApp admin via Login Kit. Tokens are Fernet-encrypted; service-role only.';
COMMENT ON COLUMN public.tiktok_accounts.access_token_enc IS
  'Fernet ciphertext of the TikTok access token. Never store or log the plaintext.';
COMMENT ON COLUMN public.tiktok_accounts.refresh_token_enc IS
  'Fernet ciphertext of the TikTok refresh token. Rotates on refresh when TikTok returns a new one.';

CREATE INDEX IF NOT EXISTS idx_tiktok_accounts_status
  ON public.tiktok_accounts(status);

ALTER TABLE public.tiktok_accounts ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies
    WHERE tablename = 'tiktok_accounts' AND policyname = 'tiktok_accounts_service_role_all'
  ) THEN
    CREATE POLICY tiktok_accounts_service_role_all ON public.tiktok_accounts
      FOR ALL TO service_role USING (true) WITH CHECK (true);
  END IF;
END $$;

-- --------------------------------------------------------------------------
-- 2. OAuth state nonces (CSRF)
-- --------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.tiktok_oauth_states (
    state        TEXT PRIMARY KEY,                       -- secrets.token_urlsafe(32)
    user_id      TEXT NOT NULL,                          -- admin who started the flow
    redirect_uri TEXT NOT NULL,                          -- the exact redirect_uri sent to TikTok
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at   TIMESTAMPTZ NOT NULL
);

COMMENT ON TABLE public.tiktok_oauth_states IS
  'Single-use OAuth state values for the TikTok Login Kit flow. Deleted on use; expired rows are swept.';

CREATE INDEX IF NOT EXISTS idx_tiktok_oauth_states_expires
  ON public.tiktok_oauth_states(expires_at);

ALTER TABLE public.tiktok_oauth_states ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies
    WHERE tablename = 'tiktok_oauth_states' AND policyname = 'tiktok_oauth_states_service_role_all'
  ) THEN
    CREATE POLICY tiktok_oauth_states_service_role_all ON public.tiktok_oauth_states
      FOR ALL TO service_role USING (true) WITH CHECK (true);
  END IF;
END $$;

-- --------------------------------------------------------------------------
-- 3. Publish ledger
-- --------------------------------------------------------------------------
-- status (ours):
--   queued        row created, upload task not yet started
--   uploading     bytes going to TikTok's upload_url (FILE_UPLOAD)
--   processing    TikTok has the media and is processing it
--   sent_to_inbox inbox flow finished; creator completes it in the TikTok app
--   published     direct post is live (privacy as chosen)
--   failed        see fail_reason / error
-- tiktok_status mirrors data.status from /v2/post/publish/status/fetch/.
CREATE TABLE IF NOT EXISTS public.tiktok_posts (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id           UUID NOT NULL REFERENCES public.tiktok_accounts(id) ON DELETE CASCADE,
    created_by           TEXT NOT NULL,                   -- admin user id
    mode                 TEXT NOT NULL CHECK (mode IN ('direct', 'inbox')),
    media_type           TEXT NOT NULL CHECK (media_type IN ('video', 'photo')),
    title                TEXT,
    description          TEXT,
    post_info            JSONB NOT NULL DEFAULT '{}'::jsonb,   -- exactly what we sent TikTok (no tokens)
    source_info          JSONB NOT NULL DEFAULT '{}'::jsonb,   -- size / chunking / photo urls
    publish_id           TEXT,
    status               TEXT NOT NULL DEFAULT 'queued'
                         CHECK (status IN ('queued', 'uploading', 'processing', 'sent_to_inbox', 'published', 'failed')),
    tiktok_status        TEXT,
    fail_reason          TEXT,
    error                TEXT,
    uploaded_bytes       BIGINT NOT NULL DEFAULT 0,
    total_bytes          BIGINT NOT NULL DEFAULT 0,
    public_post_ids      JSONB,                               -- publicaly_available_post_id
    created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at          TIMESTAMPTZ
);

COMMENT ON TABLE public.tiktok_posts IS
  'One row per TikTok publish attempt from the admin dashboard. Polled by the UI; mirrors TikTok publish status.';

CREATE INDEX IF NOT EXISTS idx_tiktok_posts_account_created
  ON public.tiktok_posts(account_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_tiktok_posts_status
  ON public.tiktok_posts(status);

ALTER TABLE public.tiktok_posts ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies
    WHERE tablename = 'tiktok_posts' AND policyname = 'tiktok_posts_service_role_all'
  ) THEN
    CREATE POLICY tiktok_posts_service_role_all ON public.tiktok_posts
      FOR ALL TO service_role USING (true) WITH CHECK (true);
  END IF;
END $$;

-- --------------------------------------------------------------------------
-- 4. Photo staging bucket (private)
-- --------------------------------------------------------------------------
-- TikTok accepts photos ONLY via PULL_FROM_URL from a URL prefix verified in
-- the developer portal, so photos are staged here and served through
-- https://www.binaapp.my/api/tiktok/media/<key> (a Next.js rewrite to the
-- backend). The bucket is private; the backend streams objects out with the
-- service key, and the keys are unguessable.
INSERT INTO storage.buckets (id, name, public)
VALUES ('tiktok-media', 'tiktok-media', false)
ON CONFLICT (id) DO NOTHING;
