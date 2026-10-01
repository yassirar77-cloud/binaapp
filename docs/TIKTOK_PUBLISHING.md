# TikTok Publishing (admin → @binaapp.my)

BinaApp admins post marketing videos and photos to BinaApp's own TikTok
account from `/admin/tiktok`. The integration follows TikTok's
[Content Posting API](https://developers.tiktok.com/doc/content-posting-api-get-started),
[Login Kit for Web](https://developers.tiktok.com/doc/login-kit-web/) and the
[Content Sharing Guidelines](https://developers.tiktok.com/doc/content-sharing-guidelines/)
(the UX rules TikTok's app review checks).

## What lives where

| Piece | Path |
|---|---|
| Migration (3 tables + private storage bucket) | `backend/migrations/058_tiktok_publishing.sql` |
| Migration (AI video ledger) | `backend/migrations/059_tiktok_ai_videos.sql` |
| AI video job + cost rules | `backend/app/services/social/tiktok_ai_video.py` |
| AI video panel | `frontend/src/components/admin/tiktok/TikTokAiVideoPanel.tsx` |
| Settings | `backend/app/core/config.py` (`TIKTOK_*`) |
| Admin guard (email allowlist **or** `users.role='admin'`) | `backend/app/core/admin.py` |
| TikTok HTTP client (OAuth, creator_info, init, chunk upload, status) | `backend/app/services/social/tiktok_client.py` |
| Account store + token refresh + revoke | `backend/app/services/social/tiktok_accounts.py` |
| Token encryption at rest (Fernet) | `backend/app/services/social/token_vault.py` |
| Publish job + validation + status sync | `backend/app/services/social/tiktok_publisher.py` |
| AI caption (DeepSeek → GLM → template) | `backend/app/services/social/caption_ai.py` |
| API router `/api/v1/social/tiktok/*` | `backend/app/api/v1/endpoints/tiktok.py` |
| OAuth redirect URI handler | `frontend/src/app/api/tiktok/callback/route.ts` |
| Admin page | `frontend/src/app/admin/tiktok/page.tsx` |
| Composer + account card | `frontend/src/components/admin/tiktok/` |
| Client + pure UX rules (tested) | `frontend/src/lib/tiktok.ts` |
| Privacy policy section 18A (BM + EN) | `frontend/src/lib/legal/policy-content-*.ts` |

Other platforms (Facebook/Instagram) go beside TikTok under
`backend/app/services/social/<platform>_*.py`, `/api/v1/social/<platform>/*`,
and `frontend/src/components/admin/<platform>/`.

## One-time setup checklist

### 1. Supabase — run the migration

Run `backend/migrations/058_tiktok_publishing.sql` and
`backend/migrations/059_tiktok_ai_videos.sql` in the SQL editor of the
production project. Both are idempotent. They create:

- `tiktok_accounts` (encrypted tokens, RLS: service role only)
- `tiktok_oauth_states` (single-use CSRF states)
- `tiktok_posts` (publish ledger the UI polls)
- storage bucket `tiktok-media` (private; photos staged for TikTok to pull, AI clips)
- `tiktok_ai_videos` (AI clip ledger: brief, prompt, cost, status)

### 2. TikTok developer portal

- App with **Login Kit** and **Content Posting API** products added.
- Scopes: `user.info.basic`, `video.upload`, `video.publish`.
- Redirect URIs (both are registered):
  - `https://binaapp.my/api/tiktok/callback`
  - `https://www.binaapp.my/api/tiktok/callback`
- Terms of Service URL: `https://binaapp.my/terms` → redirects to `/terms-of-service`
- Privacy Policy URL: `https://binaapp.my/privacy` → redirects to `/privacy-policy`
- **Photos only:** verify the URL prefix `https://www.binaapp.my/api/tiktok/media/`
  under Content Posting API → URL properties. TikTok accepts photos via
  `PULL_FROM_URL` only, so staged photos are served from that prefix
  (Next.js rewrite → backend). Videos use `FILE_UPLOAD` and need nothing here.
- Sandbox: add the @binaapp.my account as a target user while unaudited.

### 3. Render (backend `binaapp-backend`) — environment variables

| Variable | Value | Required |
|---|---|---|
| `TIKTOK_CLIENT_KEY` | from the portal | yes |
| `TIKTOK_CLIENT_SECRET` | from the portal | yes |
| `TIKTOK_REDIRECT_URI` | `https://binaapp.my/api/tiktok/callback` (already in `render.yaml`; must match a registered URI byte for byte; the `www.` variant also works) | yes |
| `TIKTOK_TOKEN_ENCRYPTION_KEY` | Fernet key: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` | recommended (otherwise derived from the client secret) |
| `TIKTOK_APP_AUDITED` | `false` until review passes, then `true` | no |
| `TIKTOK_MEDIA_PUBLIC_BASE` | default `https://www.binaapp.my/api/tiktok/media` | no |
| `TIKTOK_MAX_UPLOAD_MB` | default `300` | no |
| `ADMIN_EMAILS` | comma-separated admin emails (default `yassirar77@gmail.com`) | no |
| `WAN_DAILY_VIDEO_LIMIT` | AI clips per UTC day (default `10`; `0` disables) | no |
| `WAN_USD_TO_MYR` | FX for the estimate (default `4.40`) | no |
| `WAN_COST_USD_PER_SEC_720P` / `_1080P` | override list price per output second | no |

Render redeploys on push (`autoDeploy: true`). `cryptography` is now an
explicit requirement.

### 4. Vercel (frontend) — nothing new

The callback route and the media rewrite need no secrets. The existing
`NEXT_PUBLIC_API_URL` / `NEXT_PUBLIC_BACKEND_API_URL` are used; uploads go
straight to Render (Vercel's 4.5 MB body limit would block videos).

## The flow

1. **Connect TikTok** → `POST /oauth/start` stores a random `state` (10-minute
   TTL, bound to the admin's user id) and returns the v2 authorize URL
   (`client_key, scope=user.info.basic,video.upload,video.publish,
   response_type=code, redirect_uri, state`). PKCE is not required for web
   apps per TikTok's token doc.
2. TikTok redirects to `/api/tiktok/callback?code&state&scopes`. The Next.js
   route forwards them to `/admin/tiktok?tiktok=callback&code&state`; the page
   POSTs `/oauth/callback` with the admin's bearer token. The backend checks
   the state (exists, same user, not expired, single use), exchanges the code
   (`grant_type=authorization_code`, same `redirect_uri`), fetches
   `user/info` (display name, avatar) and upserts `tiktok_accounts` with
   Fernet-encrypted tokens.
3. Access tokens (~24 h) are refreshed automatically with the refresh token
   whenever less than 10 minutes remain; a rotated refresh token is stored.
   A failed refresh flips the account to `reauth_required` and the UI shows
   **Reconnect TikTok**.
4. The composer calls `creator_info/query` when it opens and the backend
   calls it again right before posting. From it: "Posting to *nickname*",
   the privacy dropdown (only `privacy_level_options`, **no default**),
   comment/duet/stitch toggles (off by default, disabled when the creator's
   settings disallow; photos show comments only), the commercial content
   disclosure (off by default; "Your brand" → *Promotional content*,
   "Branded content" → *Paid partnership*; at least one required; branded
   content can never be "Only you"), the Music Usage Confirmation / Branded
   Content Policy declaration, the AIGC checkbox, and the "may take a few
   minutes to process" notice. Video duration is checked against
   `max_video_post_duration_sec`.
5. **Post now** (Direct Post, `video.publish`) or **Send to TikTok drafts**
   (`video.upload`, inbox) → confirm dialog → multipart upload to the
   backend → `tiktok_posts` row → background job: init (`FILE_UPLOAD`
   — one whole chunk up to 64 MB, else 5–64 MB chunks — sequential PUTs with `Content-Range`) → poll
   `status/fetch` → `published` / `sent_to_inbox` / `failed` + reason.
   The UI polls `GET /posts/{id}` every 4 s; that endpoint also re-syncs
   with TikTok so a backend restart never leaves a post stuck.
6. **Disconnect TikTok** → `POST /v2/oauth/revoke/` then delete the row
   (posts cascade).

## AI video step (Wan 3.0)

`/admin/tiktok` → Video → **Generate AI video**. The admin uploads 1–3 real
photos (food, shop, product) and a short brief; the backend submits a
`wan3.0-video` reference-to-video job through the existing DashScope
integration (`app/services/zai_video_service.py`): the photos go in
`input.media` as `reference_image` items the prompt names "Image 1…",
`ratio 9:16`, `duration` 10 or 15 s, `resolution` 720P by default (1080P
option), `audio` off. The job is polled in the background
(`app/services/social/tiktok_ai_video.py`), the clip is copied into the
private `tiktok-media` bucket and served at `/api/v1/social/tiktok/media/<key>.mp4`.
The panel shows a preview with **Regenerate** and **Use this video**; the
latter loads the MP4 into the composer as if it had been chosen with the
file picker and ticks **This content is AI-generated** (`is_aigc`).

Money rules:

- The estimate (resolution × duration × list price, USD and RM) is shown
  before the button is pressed and written on every row of
  `tiktok_ai_videos` (migration 059). The panel lists the recent rows as a
  cost log with totals. List price (Alibaba Cloud Model Studio): $0.05/s
  480P, $0.10/s 720P, $0.20/s 1080P; override with
  `WAN_COST_USD_PER_SEC_<RES>`; `WAN_USD_TO_MYR` (default 4.40) converts.
- `WAN_DAILY_VIDEO_LIMIT` (default 10) caps clips that reach the provider
  per UTC day; rows refused at submit do not count. `0` disables the step.
- A Wan failure is shown with the provider's message and a **Try again**
  button (a new job, new row).

Requires `DASHSCOPE_API_KEY` and `DASHSCOPE_VIDEO_MODEL=wan3.0-video` (the
defaults the hero-video feature already uses). Reference photos are served
to DashScope from `TIKTOK_MEDIA_PUBLIC_BASE`, so the Next.js media rewrite
must be live (it is, since PR #818).

## Unaudited / Sandbox behaviour

Until TikTok approves the app, Direct Post only succeeds when the TikTok
account itself is set to Private and `privacy_level = SELF_ONLY`; otherwise
TikTok returns `unaudited_client_can_only_post_to_private_accounts`. The UI
says so up front while `TIKTOK_APP_AUDITED=false`, and the error is shown
as: "Until the app passes TikTok review, the TikTok account itself must be
set to Private and the post must be Only you. Or use Send to TikTok drafts."
 Inbox uploads are unaffected. Sandbox mode also caps pending
drafts at 5 per 24 h.

## Demo script for the review video

1. Open `/admin/tiktok`, click **Connect TikTok**, approve the three scopes,
   land back on the page showing the avatar + display name of @binaapp.my.
2. Pick an MP4; the preview plays and the duration shows.
3. Type a brief, click **Draft caption with AI**, edit the caption.
4. Under *Post settings*: show "Posting to BinaApp", open the privacy
   dropdown (no preselection) and choose **Only you**; leave interactions
   off or tick Comment; toggle *Disclose commercial content* on, tick
   **Your brand** and point at the *Promotional content* label; show the
   declaration sentence and the processing notice.
5. Click **Post now**, confirm, watch the progress bar, then "Processing on
   TikTok…" → "Posted (visible only to you)".
6. Open the TikTok app → Profile to show the private post.
7. Click **Disconnect TikTok** and show the account card reset.

## Tests

- `backend/tests/test_tiktok_publishing.py` — vault, chunk plan, validation,
  post_info, status mapping, OAuth state, route guard.
- `backend/tests/test_tiktok_ai_video.py` — cost estimate, daily cap, prompt,
  the wan3.0 reference-image request shape, the driver, the admin routes.
- `frontend/src/lib/tiktok.test.ts` — the composer rules (no default privacy,
  toggles off, disclosure gating, declaration text, limits, status copy).
