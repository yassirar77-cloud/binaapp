# Hero Video Background (DashScope HappyHorse / Z.ai CogVideoX)

A short, muted, looping AI-generated clip that plays behind the hero section
of a merchant's website, with a readable scrim over it.

Ships **dark** — `HERO_VIDEO_ENABLED=false` by default. Flip it on in Render;
no frontend deploy is needed (the panel hides itself while the options call
404s).

## How it works

```
Dashboard / create page                    Backend                                   DashScope / Cloudinary / Supabase
────────────────────────────────────────── ───────────────────────────────────────── ─────────────────────────────────
POST …/hero-video/generate (or /prepare) ─▶ gates (flag, owner, credit, hero exists,
                                           balanced HTML, caps); build prompt
                                           POST video-synthesis ──────────────────▶ task id (PENDING)
                                           INSERT hero_video_jobs row ────────────▶ ledger: status=processing
◀── 202 {job_id} ─────────────────────────  spawn _drive_hero_video_job (THE poller)
                                                           ⋮  every 8 s, server-side, no browser needed
                                           GET /tasks/{task} ─────────────────────▶ task_status logged on EVERY poll
                                             PENDING/RUNNING → keep going (ledger: provider_status)
                                             poll error       → keep going (ledger: http_<code>, poll_errors+1)
                                             FAILED/CANCELED/UNKNOWN → failed + refund (FULL body logged)
                                             > 600 s          → failed('timeout') + refund + 🚨 HERO_VIDEO_TIMEOUT
                                             SUCCEEDED        → 'storing', background finaliser:
                                               download clip, upload to Cloudinary,
                                               UPDATE websites SET hero_video_url,… ──▶ the row says what the page must carry
                                               patch HTML (hero_video_patcher),
                                               republish storage + DB, bust the 60 s served-page cache
GET …/hero-video/jobs/{job} ──────────────▶ READ-ONLY: reports what the driver recorded
◀── {status, provider_status, html_content on completion}
```

Restart: `resume_hero_video_jobs()` (startup) reloads every non-terminal
ledger row with its real age and drives it again. Sweep: every 5 min the
stuck-generation scheduler also runs `sweep_stuck_hero_video_jobs()`, which
fails anything past the timeout (+120 s grace) whether or not a driver is
alive for it and whatever the website's status is.

Two halves, deliberately separate:

1. **Making the clip is the only AI call.** The provider API is
   asynchronous, so ours is too: `generate` returns a job id immediately
   and a server-side driver polls the provider until the job is terminal.
   The browser's poll reads state only — there is exactly one poller per
   job. Completion (download, Cloudinary, row write, patch, publish) is
   always a background task, never inside a request.
2. **Putting it on the page, adjusting it, and removing it are credit-free
   HTML patches** (`hero_video_patcher.py`) in the Design Studio shape: no
   AI, no quota, the merchant's copy/prices/photos never move. Removal is
   byte-exact — the page returns to what it was before the video was added.

### Durability (migration 056)

Before 2026-09-11 a job existed only in process memory. Render redeploys on
every push, so a job that was rendering — or stored and waiting for its
publish — was forgotten with no log line, no refund, and no way for the
stuck sweep (which only queried `websites.status='generating'`) to see it.
Now:

* `hero_video_jobs` mirrors every state change (`services/hero_video_jobs.py`).
  Ledger write failures are logged at ERROR and never raised: the clip must
  still land.
* `websites.hero_video_url / hero_video_poster_url / hero_video_settings /
  hero_video_updated_at` record the clip a site carries. They are written
  **before** the HTML is patched and cleared on removal.
* `resume_hero_video_jobs()` runs at startup; `sweep_stuck_hero_video_jobs()`
  runs with the stuck-generation sweep.
* Ownership: every row carries a per-process lease (`lease_owner`,
  `lease_until`), renewed on each poll. Adoption (startup, and the sweep)
  goes through a conditional PATCH only one process can win, so Render's
  deploy overlap never runs two drivers on one job. One refund per job is
  decided by the ledger (`mark_refunded`, a conditional PATCH), not by
  process memory.
* A clip prepared on the create page waits **24 h** (was 45 min) for its
  publish. The old window discarded a finished, paid clip eleven minutes
  before the merchant published (job b15c3794, 2026-09-11).
* Timeout: `ZAI_VIDEO_MAX_WAIT_SECONDS` (default 600). DashScope
  wan3.0-video clips took 2 m 15 s – 3 m 45 s across every job in a week of
  production logs; ten minutes is ~2.7× the slowest, and the point at which
  the credit goes back. A timed-out job is `failed` with `error=timeout`,
  refunded, and raises `🚨 HERO_VIDEO_TIMEOUT …` at CRITICAL plus an admin
  email (`email_service.send_admin_notification`).
* Every poll logs the provider's raw `task_status`; any non-SUCCEEDED
  terminal state logs the full response body; an undocumented state is
  logged as UNEXPECTED and bounded by the timeout.

## The HTML patch

Injected once, fenced by comments so removal is exact:

```html
<head> … <style id="binaapp-hero-video-style">…</style></head>
…
<section id="home" … data-binaapp-hero-video="1">
  <!--binaapp:hero-video-->
  <div class="binaapp-hero-video-layer" aria-hidden="true"
       data-binaapp-video-url="…" data-binaapp-poster-url="…"
       data-binaapp-overlay="dark" data-binaapp-overlay-opacity="0.45"
       data-binaapp-text-mode="auto" data-binaapp-mobile="video"
       style="background-image:url('…poster.jpg')">
    <video class="binaapp-hero-video" autoplay muted loop playsinline preload="metadata" poster="…">
      <source src="…hero.mp4" type="video/mp4">
    </video>
    <div class="binaapp-hero-video-scrim"></div>
  </div>
  <!--/binaapp:hero-video-->
  … the merchant's hero content, untouched …
</section>
```

* The hero is found by `id="home|hero|utama|laman-utama"`, then a `hero`
  class, then the first `<section>` in the body — the order the generator
  and the pre-built templates emit.
* Every CSS rule is scoped to `[data-binaapp-hero-video]`; nothing depends
  on the merchant's own classes. The hero's children are never restyled. The layer sits at `z-index:-1`
  inside the hero's own `isolation:isolate` stacking context, so it paints over the section's own
  background gradient/image.
* `overlay` (`dark` / `light` / `none`) + `overlay_opacity` paint the scrim.
  `text_mode: auto` forces hero headings/paragraphs white over a dark scrim
  (and dark over a light one); links and buttons keep their brand colour.
* `prefers-reduced-motion` hides the video and leaves the poster still.
  `show_on_mobile=false` does the same under 640px (data saver).
* `GET …/hero-video` reads the data-attributes back from the stored HTML.
  Since migration 056 the websites row also records the clip
  (`hero_video_url` and friends), written before the page is patched.
* URLs must be `https://` with no quote/angle characters and are
  HTML-escaped; the settings and video URL are round-tripped exactly.

## Endpoints

All under `/api/v1/websites`, owner-only except `options`:

| Method | Path | What |
| --- | --- | --- |
| GET | `/hero-video/options` | Style presets, model, poll interval (public) |
| GET | `/{id}/hero-video` | Current settings, `hero_found`, `allowed`, in-flight `job` |
| POST | `/{id}/hero-video/generate` | Start a job → `202 {job_id}` |
| GET | `/{id}/hero-video/jobs/{job_id}` | Read the job's state (never polls the provider) |
| PATCH | `/{id}/hero-video` | Change overlay / opacity / text_mode / show_on_mobile (reuses the clip) |
| DELETE | `/{id}/hero-video` | Remove; page returns to its pre-video bytes |

Generate body: `style` (`cinematic` `ambient` `energetic` `elegant` `nature`),
optional `prompt` (≤400 chars, merchant's own scene), `duration` (5 or 10),
`image_url` (https; image-to-video from an existing photo), plus the look
fields. The prompt builder prepends the business name/type/description and
appends "no text, no logos, seamless loop…" and always stays ≤ 512 chars
(the Z.ai cap).

Error codes (`detail.error`): `plan_not_allowed` 403, `hero_not_found` 422,
`no_balanced_html_base` 422, `job_in_progress` 409, `too_many_jobs` 429,
`daily_limit_reached` 429, `video_submit_failed` 502, `job_not_found` 404,
`no_hero_video` 404, `rewrite_produced_unbalanced_html` 422. Job terminal
`error` values: `timeout`, `generation_failed`, `storage_failed`,
`hero_not_found`, `no_balanced_html_base`.

## Gates and cost guards

**Paid per clip.** A hero video costs one `hero_video` add-on credit (RM5;
HappyHorse charges ~USD 0.70 to make a 5-second clip). `plan_features.
hero_video_access(user_id)` decides: admins, `HERO_VIDEO_ALLOW_ALL_PLANS=true`
and plans whose `features` carry `can_use_hero_video` generate for free;
everyone else needs a credit. `POST …/generate` answers **402
`payment_required`** (with `price_rm` and `addon_type`) when there is
neither. The credit is consumed only after the provider has *accepted* the
job — a rejected submit costs nothing — and is refunded on every failure
path (provider FAIL, timeout, storage or apply failure), exactly once.
Credits are bought through the existing add-on checkout (`POST
/payments/addon/purchase` or `/subscription/addons/purchase`, `addon_type:
hero_video`); the editor panel sells them in place and the payment-success
page returns the merchant to the editor via `pending_return_to`.
`GET /websites/hero-video/access` reports `free`/`credits`/`price_rm` for
the signed-in account (used by the create page). Migration 008 widens the
`addon_purchases.addon_type` check to admit `hero_video` and lets `status`
carry `depleted`.


* `HERO_VIDEO_ENABLED` — master flag, read per request.
* Plan: `plan_features.can_use_hero_video(user_id)` — admins pass;
  `HERO_VIDEO_ALLOW_ALL_PLANS=true` opens it to every active plan; otherwise
  the plan's `features` JSON needs `can_use_hero_video: true` (or
  `can_use_video_background: true`). Fails closed like `can_publish_subdomain`.
* One in-flight job per website, `MAX_ACTIVE_JOBS_PER_USER = 2`, and
  `HERO_VIDEO_MAX_PER_SITE_PER_DAY` (default 5). The daily counter and the
  job registry are process-local (same as `job_service`); a restart forgets
  in-flight jobs and the panel asks the merchant to try again.
* All gates run **before** the Z.ai submit, so a blocked request never
  spends money. A failed submit is not counted against the daily cap.

## Publish safety

Identical rules to the theme and contact edit paths (the mimba regression):
patch the live storage snapshot when published (DB blob as fallback), only
accept a balanced base, refuse to publish an unbalanced result, and report
`live_site_updated=false` + `warning=storage_refresh_failed` honestly when
storage rejects the republish.

## Provider

`HERO_VIDEO_PROVIDER` picks the text-to-video API that makes the clip; everything
after the clip exists (download, Cloudinary, patch, publish) is shared.

| Provider | Value | Model (default) | Submit | Poll |
|---|---|---|---|---|
| Alibaba Model Studio (default) | `dashscope` | `happyhorse-1.1-t2v` | `POST {DASHSCOPE_API_URL}/services/aigc/video-generation/video-synthesis` with `X-DashScope-Async: enable` → `output.task_id` | `GET {DASHSCOPE_API_URL}/tasks/{task_id}` → `output.task_status` PENDING/RUNNING → processing, SUCCEEDED → `output.video_url` (valid 24 h), FAILED/CANCELED/UNKNOWN → failed |
| Z.ai | `zai` | `cogvideox-3` | `POST /videos/generations` → `id` | `GET /async-result/{id}` → `task_status`, `video_result[0].url` |

**Fallback.** `HERO_VIDEO_FALLBACK_PROVIDER` (default `zai` when DashScope is
primary; `none` to disable) is tried only when the primary cannot *accept* the
job — a rejected key (`401 InvalidApiKey`), quota, outage. Each job records the
provider that holds its task, so polling always goes back to the same API. When
every provider refuses, the merchant sees `provider_not_configured` with a
Malay message pointing at server configuration rather than a retry.

DashScope uses the same key as the Qwen text path (`DASHSCOPE_API_KEY`, or
`QWEN_API_KEY`). `DASHSCOPE_VIDEO_RESOLUTION` (480P/720P/1080P, default 720P)
and `DASHSCOPE_VIDEO_RATIO` (default 16:9) set the clip; `DASHSCOPE_VIDEO_WATERMARK` (default false) is sent as `parameters.watermark` — HappyHorse burns a "Happy Horse" mark into the corner unless it is false; DashScope prices per
second of output, so 480P is the cheap option. HappyHorse is text-to-video
only: an `image_url` on the request is ignored for this provider.

## Configuration

See `ENV_TEMPLATE.txt` → "Hero Video Background". Uses the same
`ZAI_API_KEY` / `ZAI_API_URL` (or `ZAI_BASE_URL`) as GLM HTML and image
generation. Defaults: `cogvideox-3`, `1280x720`, 5 s, 30 fps, `speed`,
no audio.

## Files

* `backend/app/services/zai_video_service.py` — Z.ai submit/poll/download,
  Cloudinary video upload, prompt builder, in-memory job registry.
* `backend/app/services/hero_video_jobs.py` — the durable ledger (table `hero_video_jobs`).
* `backend/app/services/hero_video_patcher.py` — inject / detect / remove.
* `backend/app/api/v1/endpoints/hero_video.py` — routes above.
* `backend/app/services/plan_features.py` — `can_use_hero_video`.
* `frontend/src/lib/heroVideo.ts` — client + Malay error copy.
* `frontend/src/components/HeroVideoPanel.tsx` — editor panel (below the
  Design Studio on `/editor/[id]`).
* `backend/scripts/hero_video_e2e.py` — real end-to-end check against a deployment.
* Tests: `backend/tests/test_hero_video_patcher.py`,
  `test_zai_video_service.py`, `test_hero_video_api.py`, `test_hero_video_pipeline.py`,
  `frontend/src/components/HeroVideoPanel.test.tsx`.
