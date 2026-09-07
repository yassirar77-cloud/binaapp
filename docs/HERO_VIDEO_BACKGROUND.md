# Hero Video Background (DashScope HappyHorse / Z.ai CogVideoX)

A short, muted, looping AI-generated clip that plays behind the hero section
of a merchant's website, with a readable scrim over it.

Ships **dark** — `HERO_VIDEO_ENABLED=false` by default. Flip it on in Render;
no frontend deploy is needed (the panel hides itself while the options call
404s).

## How it works

```
Dashboard (HeroVideoPanel)                 Backend                              Z.ai / Cloudinary
────────────────────────────────────────── ──────────────────────────────────── ────────────────────
POST /websites/{id}/hero-video/generate ─▶ gates (flag, owner, plan, hero
                                           exists, balanced HTML, caps)
                                           build prompt (business + preset)
                                           POST /videos/generations ──────────▶ task id (PROCESSING)
◀── 202 {job_id} ─────────────────────────
                                                           ⋮  every ~8s
GET  /websites/{id}/hero-video/jobs/{job} ▶ GET /async-result/{task} ─────────▶ PROCESSING | SUCCESS | FAIL
                                           on SUCCESS (once, under a lock):
                                             download clip ───────────────────▶ mfile.z.ai (temporary URL)
                                             upload resource_type=video ──────▶ Cloudinary binaapp/hero-videos
                                             patch HTML (hero_video_patcher)
                                             republish live snapshot + DB
◀── {status: completed, html_content} ────
```

Two halves, deliberately separate:

1. **Making the clip is the only AI call.** Z.ai's video API is asynchronous
   (`/videos/generations` → `/async-result/{id}`), so ours is too: `generate`
   returns a job id immediately and the dashboard polls. The poll that
   observes `SUCCESS` stores the clip, patches the page and republishes in
   the same request.
2. **Putting it on the page, adjusting it, and removing it are credit-free
   HTML patches** (`hero_video_patcher.py`) in the Design Studio shape: no
   AI, no quota, the merchant's copy/prices/photos never move. Removal is
   byte-exact — the page returns to what it was before the video was added.

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
* The stored HTML is the single source of truth: `GET …/hero-video` reads
  the data-attributes back. No new DB columns.
* URLs must be `https://` with no quote/angle characters and are
  HTML-escaped; the settings and video URL are round-tripped exactly.

## Endpoints

All under `/api/v1/websites`, owner-only except `options`:

| Method | Path | What |
| --- | --- | --- |
| GET | `/hero-video/options` | Style presets, model, poll interval (public) |
| GET | `/{id}/hero-video` | Current settings, `hero_found`, `allowed`, in-flight `job` |
| POST | `/{id}/hero-video/generate` | Start a job → `202 {job_id}` |
| GET | `/{id}/hero-video/jobs/{job_id}` | Poll; completes the job on success |
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

DashScope uses the same key as the Qwen text path (`DASHSCOPE_API_KEY`, or
`QWEN_API_KEY`). `DASHSCOPE_VIDEO_RESOLUTION` (480P/720P/1080P, default 720P)
and `DASHSCOPE_VIDEO_RATIO` (default 16:9) set the clip; DashScope prices per
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
* `backend/app/services/hero_video_patcher.py` — inject / detect / remove.
* `backend/app/api/v1/endpoints/hero_video.py` — routes above.
* `backend/app/services/plan_features.py` — `can_use_hero_video`.
* `frontend/src/lib/heroVideo.ts` — client + Malay error copy.
* `frontend/src/components/HeroVideoPanel.tsx` — editor panel (below the
  Design Studio on `/editor/[id]`).
* Tests: `backend/tests/test_hero_video_patcher.py`,
  `test_zai_video_service.py`, `test_hero_video_api.py`,
  `frontend/src/components/HeroVideoPanel.test.tsx`.
