# Showcase wall clips

The merchant hero videos that fill the masonry grid on the homepage. Each card
plays one restaurant's own hero video — nothing else goes on the card but the
business name.

The file names are already written into `src/lib/landing/showcaseClips.ts`, so
dropping a file here with the right name is all it takes:

```
public/showcase/nasi-kukus-wak-hassan.mp4     ← the clip
public/showcase/nasi-kukus-wak-hassan.jpg     ← first frame; add `poster` to the clip
```

The wall expects these sixteen, in this order:

| File | Card |
|---|---|
| `nasi-kukus-wak-hassan.mp4` | NASI KUKUS WAK HASSAN — links to https://mayam.binaapp.my |
| `nasi-kandar-pak-din.mp4` | NASI KANDAR PAK DIN |
| `roti-canai-abang-li.mp4` | ROTI CANAI ABANG LI |
| `ckt-ah-seng.mp4` | CHAR KUEY TEOW AH SENG |
| `satay-haji-ramli.mp4` | SATAY KAJANG HAJI RAMLI |
| `laksa-mak-timah.mp4` | LAKSA PENANG MAK TIMAH |
| `nasi-lemak-kak-yah.mp4` | NASI LEMAK KAK YAH |
| `burger-abang-burn.mp4` | BURGER BAKAR ABANG BURN |
| `kopitiam-lim.mp4` | KOPITIAM LIM |
| `cendol-tok-mat.mp4` | CENDOL PULUT TOK MAT |
| `tandoori-raju.mp4` | TANDOORI BISTRO RAJU |
| `sup-tulang-johor.mp4` | SUP TULANG MERAH JOHOR |
| `ayam-penyet-mbok-sri.mp4` | AYAM PENYET MBOK SRI |
| `dimsum-hong-kee.mp4` | DIM SUM HONG KEE |
| `al-mandi-house.mp4` | NASI ARAB AL-MANDI HOUSE |
| `sweet-crumbs.mp4` | SWEET CRUMBS BAKERY |

A card whose file is not here yet draws itself instead — gradient and food
mark under the business name — so the section holds its shape while you add
clips a few at a time.

## Posters

`preload` is off, so a card downloads nothing until it scrolls into view. Until
playback starts it sits on its gradient. Add a poster and it shows the first
frame instead, which is worth the extra ~40KB on the cards near the top:

```ts
// src/lib/landing/showcaseClips.ts
{
  id: 'nasi-kukus-wak-hassan',
  ...
  poster: '/showcase/nasi-kukus-wak-hassan.jpg',
},
```

## What the files should be

The cards are small — roughly 250-330px wide on a desktop screen — and several
play at once, so keep each file tiny:

| | |
|---|---|
| Format | MP4, H.264 + `faststart` (add a WebM only if you need it) |
| Size | **under 1 MB each**, ideally 300-600 KB |
| Width | 480px is plenty — the cards are never shown larger |
| Aspect | matches the card's `ratio`: `tall` 9:16, `portrait` 3:4, `square` 1:1; anything else gets cropped centre |
| Length | 3-6 seconds, looping cleanly |
| Audio | none — strip it, the wall is always muted |
| Frame rate | 24-30fps |

A clip re-encoded to spec, for a `tall` card:

```bash
ffmpeg -i original.mov \
  -an -t 6 \
  -vf "scale=-2:854,crop=480:854" \
  -c:v libx264 -crf 30 -preset slow -pix_fmt yuv420p \
  -movflags +faststart \
  nasi-kukus-wak-hassan.mp4

# matching poster from the first frame
ffmpeg -i nasi-kukus-wak-hassan.mp4 -vframes 1 -q:v 6 nasi-kukus-wak-hassan.jpg
```

## Why the size matters

Every card that scrolls into view downloads its clip. The wall pauses a video
the moment it leaves the viewport, and when the tab is hidden, and it holds
every card on its poster when the visitor has asked for reduced motion — but
it cannot un-download a 10MB file. Sixteen clips at 500KB is a section that
loads; sixteen at 5MB is a homepage nobody scrolls to the bottom of.
