# Mascot Video

A merchant uploads a 2–10 s clip of their shop or food, picks a mascot, and
wan3.0-video (DashScope) returns the clip with the mascot edited into the
real scene. Off by default.

| Piece | Where |
|---|---|
| Rules, job driver | `backend/app/services/mascot_video.py` |
| Routes (`/api/v1/mascot-videos/*`) | `backend/app/api/v1/endpoints/mascot_videos.py` |
| Provider calls (`upload_temp_file`, `submit_video_edit`) | `backend/app/services/zai_video_service.py` |
| Clip moderation (`check_video_safety`) | `backend/app/services/image_moderation_service.py` |
| Table + bucket | `backend/migrations/071_mascot_videos.sql` |
| Dashboard page | `frontend/src/app/dashboard/video-maskot/` (`/dashboard/video-maskot`) |
| Model bake-off script and results | `scripts/mascot_video_test.py`, `test_outputs/` |

## Turning it on

1. Run migration 071 (table `mascot_videos`, private bucket `mascot-videos`).
2. Set `MASCOT_VIDEO_ENABLED=true` on the backend. `DASHSCOPE_API_KEY` and a
   wan3.x `DASHSCOPE_VIDEO_MODEL` must already be set (they are, for hero video).
3. Link the page from the dashboard nav (`frontend/src/lib/dashboardNav.ts`);
   it is deliberately not linked while the flag is off.

"Use as hero video" also needs `HERO_VIDEO_ENABLED=true`: it copies the clip
to Cloudinary and applies it with the hero-video patcher.

## Job flow

`queued → moderating → processing → ready | rejected | failed`

1. `POST /jobs` (multipart: `clip`, `mascot` file or `mascot_url`, `prompt`,
   `consent=true`). The clip must be MP4/MOV, 2–10 s, at most
   `MASCOT_VIDEO_MAX_MB`. Duration is read from the file's `moov/mvhd` box —
   the server has no ffmpeg.
2. Clip and mascot are stored in the private bucket.
3. The clip is checked by Qwen (`QWEN_VL_VIDEO_MODEL`, default
   `qwen3-vl-plus`). This check **fails closed**: no key, an API error or a
   timeout fails the job without rendering.
4. The clip goes to wan3.0 through DashScope's temporary file store (an
   `oss://` URL, never a public one), the mascot as a base64 reference image.
5. The job is polled in the background; the result is copied into the bucket
   and the metered cost written on the row.

A backend restart loses the in-process driver; the next `GET` of the job
starts it again (a job the provider already accepted resumes polling).

## Cost controls

- DashScope bills **input + output seconds**: a 10 s clip at 720P is about
  USD 2.00, at 1080P about USD 4.00.
- `MASCOT_VIDEO_DAILY_LIMIT` (default 3) renders per merchant per UTC day,
  counted from rows that reached the provider. One job in flight per merchant.
- `MASCOT_IMAGE_DAILY_LIMIT` (default 5) glm-image mascots per merchant per
  day (in memory; resets on restart).
- **No billing yet.** `TODO(billing)` in `mascot_video.py`: charge BinaCredits
  per render once the credit deduction bug is fixed.

## Known limits

- Mascot placement is not reliable — see `test_outputs/README.md`. The real
  scene is always kept, but the mascot can come out small, fade, or be missing.
  A render that disappoints still costs money and still counts against the cap.
- The "Dijana AI" label is shown by the dashboard on every result. It is not
  burned into the downloaded file or the hero clip: wan3.0's own watermark
  reads "AI 生成" (`MASCOT_VIDEO_WATERMARK`, off by default).
- Media is served from `/api/v1/mascot-videos/media/{key}` without auth
  (a `<video>` tag cannot send a token); keys are 128-bit random.
