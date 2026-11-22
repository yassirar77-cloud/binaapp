# Mascot Video — Phase 1 test outputs

`results.md` is the table written by `scripts/mascot_video_test.py`.
`compare_*.jpg` show one frame per second, source clip on top and the model's
output below. The rendered `.mp4` files are not committed (about 10 MB each);
re-run the script to regenerate them.

Test clip: 5.2 s cut from "Street food and nightlife in Bangkok" by Karel
Kulhavý (archive.org/details/bangkok-street-food), CC BY-SA 4.0. It stands in
for a merchant clip, which was not supplied. Test material only — not for use
in the product.

## What the wan3.0-video runs showed

| Run | Prompt | Result |
|---|---|---|
| teh tarik uncle | "add the mascot … in the foreground" | scene kept; mascot large, pasted over the frame like a sticker, stays to the end |
| cartoon chicken | same | scene kept; same sticker look, mascot fades out at about 3.5 s |
| cartoon chicken `v2` | "stands on the ground … from first frame to last" | scene kept; mascot small, standing on the street, appears once the ground is in shot and stays |
| cartoon chicken `v2raw` | same, `prompt_extend` off | same as `v2` |
| cartoon chicken (Phase 2 pipeline) | `v2` plus "large, one third of the frame height" | scene kept; **no mascot at all** |

The real scene was preserved in every run. Mascot placement is not reliable:
of five paid renders, one lost the mascot part-way and one had no mascot.
The production prompt uses the `v2` wording.

Kling O3 and Runway Aleph were not run (no Runway key).
