# Showcase wall clips

The clips that play in the moving columns of the homepage showcase section.
Drop files here, then point the matching clip in
`src/lib/landing/showcaseClips.ts` at them by uncommenting its `src` line.

```
public/showcase/nasi-lemak.mp4     ← the clip
public/showcase/nasi-lemak.jpg     ← optional first frame, shown while it loads
```

```ts
// src/lib/landing/showcaseClips.ts
{
  id: 'nasi-lemak',
  label: 'Nasi Lemak Kak Yah',
  ...
  src: '/showcase/nasi-lemak.mp4',
  poster: '/showcase/nasi-lemak.jpg',
},
```

Clips without a `src` are not broken — the wall draws a gradient card with the
business name instead, so you can add videos a few at a time.

## What the files should be

The cards are small (roughly 200-260px wide on a desktop screen) and a dozen of
them play at once, so keep each file tiny:

| | |
|---|---|
| Format | MP4, H.264 + `faststart` (add a WebM only if you need it) |
| Size | **under 1 MB each**, ideally 300-600 KB |
| Width | 480px is plenty — the cards are never shown larger |
| Aspect | 3:4 portrait, matching the card; anything else gets cropped centre |
| Length | 3-6 seconds, looping cleanly |
| Audio | none — strip it, the wall is always muted |
| Frame rate | 24-30fps |

A clip that already looks right, re-encoded to spec:

```bash
ffmpeg -i original.mov \
  -an -t 6 \
  -vf "scale=-2:640,crop=480:640" \
  -c:v libx264 -crf 30 -preset slow -pix_fmt yuv420p \
  -movflags +faststart \
  nasi-lemak.mp4

# matching poster from the first frame
ffmpeg -i nasi-lemak.mp4 -vframes 1 -q:v 6 nasi-lemak.jpg
```

## Why the size matters

Every card in view loads on the homepage. The
wall pauses itself when it scrolls out of view, when the tab is hidden, and
when the visitor has asked for reduced motion, but it cannot un-download a
10MB clip. Fifteen clips at 500KB is a wall that loads; fifteen at 5MB is a
homepage nobody waits for.
