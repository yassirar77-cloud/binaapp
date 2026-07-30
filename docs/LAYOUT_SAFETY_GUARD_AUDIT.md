# Layout Safety Guard — audit (P3)

`LAYOUT_SAFETY_CSS` in `backend/app/services/templates.py` is ~200 lines of CSS
injected into every generated site, at generation time **and** re-injected on
every serve (it is self-upgrading, which is how fixes reach already-published
sites without a republish).

It is well written and carefully commented. It is also, almost entirely, a
list of generator defects being patched at the wrong layer — and it ships to
every visitor of every site.

This document records what each guard patches, whether the defect can move
upstream, and the evidence needed before removing it.

## The rule this audit follows

**No guard is removed on reasoning alone.** Each one exists because something
broke on a real merchant site. `backend/app/services/layout_guard_audit.py`
reports which guards *would* fire on a given page; it runs on every generation
and logs the result:

```
🧱 Layout guards that would fire: ['b1_section_height_cap', 'f_stat_overflow'] [model=glm-5.2]
```

A guard is safe to retire once production logs show it not firing across a
meaningful sample — and note the sample must cover **all** models in the
fallback chain, since they fail differently.

## Verdicts

| Guard | Patches | Verdict |
|---|---|---|
| `a0_scroll_padding` | Generated page omits `scroll-padding-top` under a fixed nav, so anchor jumps hide the heading | **fixed-pending-telemetry** — the prompt now mandates `html { scroll-padding-top: 5rem; }` |
| `a_aos_rescue` | `aos.js` fails to load, or initialises and then stalls, leaving content permanently invisible | **KEEP — permanently.** Not a generator defect: it guards a third-party CDN. The only guard here that is genuinely load-bearing. |
| `b1_section_height_cap` | `min-h-screen` emitted on non-hero sections, pushing content off-screen | **fixable** — needs a prompt constraint plus a deterministic post-generation rewrite |
| `b2_empty_hero_cap` | 100vh hero emitted with no image behind it | **fixable** — the generator knows at prompt-build time whether a hero image exists (`image_choice`/`images`), so it should never emit the image-hero shape without one |
| `c_menu_grid` | Menu cards mix image and no-image, collapsing card heights | **fixed-pending-telemetry** — the prompt mandates identical `w-full aspect-[4/3] object-cover` on every card image |
| `d_empty_media_box` | An aspect-ratio media box emitted with nothing in it (the About photo slot) | **fixed-pending-telemetry** — P2 image-reuse rules require omitting the image or the section rather than emitting an empty holder; the validator also warns on `empty_image` |
| `e_stripped_bg` | Our own image safety guard blanked a banned stock URL and left `background-image: url()` | **FIXED UPSTREAM** — `_repaint_emptied_background_urls()` now repaints at the point of stripping. This guard patched a defect we created ourselves. |
| `f_stat_overflow` | Hero stat grid cells lack `min-w-0`, so long Malay labels collide | **fixed-pending-telemetry** — the prompt mandates `min-w-0` + `break-words` on every stat cell |
| `whatsapp_pin` | Injected floating WhatsApp button relies on the guard for `position: fixed` | **fixable** — we control that markup entirely; the styles belong inline on the injected element |

## Why nothing is deleted in this change

Two reasons, both practical:

1. **The guard is retroactive.** Because it re-injects on serve, it is
   currently protecting every site published *before* the P0–P2 fixes landed.
   Those pages still contain the old defects. Removing a rule breaks them even
   if every future generation is clean.
2. **The upstream fixes are mostly prompt constraints**, and a prompt
   constraint is a strong tendency, not a guarantee. "Fixed" here means "the
   model is now told not to do this", which is exactly the class of claim that
   needs telemetry rather than confidence.

`e_stripped_bg` is the one exception: its cause was our own deterministic code,
so it is genuinely fixed. Its CSS rule stays for the retroactive reason above,
but it should now never fire on new output — making it the first candidate for
removal, and a good calibration check on the telemetry itself.

## Retirement order

1. `e_stripped_bg` — deterministic fix landed; verify it stops firing.
2. `f_stat_overflow`, `c_menu_grid`, `a0_scroll_padding` — prompt-mandated;
   verify across GLM **and** DeepSeek output.
3. `d_empty_media_box` — needs the validator's `empty_image` warning rate to
   fall too.
4. `b2_empty_hero_cap`, `b1_section_height_cap`, `whatsapp_pin` — need real
   upstream work first (see verdicts).
5. `a_aos_rescue` — never.

Consider gating removal behind a date-based cutoff on `websites.created_at`, so
old pages keep the guard while new ones ship without it.
