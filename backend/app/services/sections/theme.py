"""The theme the AI chose, as a fixed set of tokens the sections render with.

A ``Theme`` is the ONLY thing the design plan contributes to a composed
page: six colours, two font families, a style variant and a corner
radius. Every token is contrast-repaired here, once, so a section never
has to check its own colours: ``text`` reads on ``bg`` and ``surface``,
``primary`` reads as text on both surfaces, ``on_primary`` reads on
``primary``. The agp site shipped mustard prices on a chilli-red brand
because ``--primary-color`` pointed at the darkened SECONDARY colour; a
theme has one primary and it is the plan's accent.
"""

from __future__ import annotations

import html as _html
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.services.theme_patcher import contrast_ratio, normalize_hex, relative_luminance

AA_TEXT = 4.5

#: Style variants: how the fixed section layouts are dressed.
#:   soft      – rounded cards, soft shadows (default)
#:   outline   – square corners, 3px ink borders, hard offset shadows
#:   editorial – hairline rules, serif-friendly, no card chrome
VARIANTS = ("soft", "outline", "editorial")

_OUTLINE_DIRECTIONS = ("coret_ceria", "doodle_malam", "pesta_neon", "halal_street", "barber_tegas", "bengkel_yakin", "api_malam")
_EDITORIAL_DIRECTIONS = ("mewah_cerah", "warisan_malam", "butik_runway", "runway_malam", "studio_fokus", "studio_malam", "kedai_kek")

_FALLBACK_LIGHT = {"bg": "#FFFBF5", "surface": "#FFFFFF", "text": "#1C1917", "muted": "#57534E", "accent": "#B91C1C", "accent_2": "#1C1917"}
_FALLBACK_DARK = {"bg": "#141210", "surface": "#1F1B17", "text": "#F5F0E8", "muted": "#C7BFB3", "accent": "#F59E0B", "accent_2": "#F5F0E8"}

_SYSTEM_FALLBACK = "system-ui, -apple-system, 'Segoe UI', Roboto, Arial, sans-serif"


@dataclass
class Theme:
    bg: str
    surface: str
    text: str
    muted: str
    primary: str
    on_primary: str
    accent: str
    display_font: str = "Inter"
    body_font: str = "Inter"
    variant: str = "soft"
    dark: bool = False
    radius: str = "1rem"
    source: str = "plan"
    repairs: List[str] = field(default_factory=list)

    @property
    def fonts_href(self) -> str:
        fams = []
        for name, weights in ((self.display_font, "600;700;800"), (self.body_font, "400;500;600;700")):
            if name and name not in [f.split(":")[0].replace("+", " ") for f in fams]:
                fams.append(f"{name.replace(' ', '+')}:wght@{weights}")
        return "https://fonts.googleapis.com/css2?" + "&".join(f"family={f}" for f in fams) + "&display=swap"

    def as_dict(self) -> Dict[str, Any]:
        return {
            "bg": self.bg, "surface": self.surface, "text": self.text, "muted": self.muted,
            "primary": self.primary, "on_primary": self.on_primary, "accent": self.accent,
            "display_font": self.display_font, "body_font": self.body_font, "variant": self.variant,
            "dark": self.dark, "radius": self.radius, "source": self.source, "repairs": list(self.repairs),
        }

    #: The tokens the rest of the pipeline reads (extract_theme_tokens, widgets).
    def tokens(self) -> Dict[str, str]:
        return {
            "primary": self.primary, "secondary": self.accent, "accent": self.accent,
            "background": self.bg, "surface": self.surface, "text": self.text, "text_muted": self.muted,
        }


# ---------------------------------------------------------------------------
# Contrast repair
# ---------------------------------------------------------------------------

def _hex(value: Optional[str], default: str) -> str:
    return normalize_hex(value or "") or default


def _readable(fg: str, backgrounds: List[str], target: float = AA_TEXT) -> str:
    """``fg`` nudged within its own hue until it reads on every background;
    black or white when no shade of that hue can."""
    from app.services.contrast_guard import adjust_for_contrast
    fixed = adjust_for_contrast(fg, backgrounds, target)
    if fixed:
        return fixed
    dark_ok = all(contrast_ratio("#111111", bg) >= target for bg in backgrounds)
    return "#111111" if dark_ok else "#FFFFFF"


def _on(colour: str) -> str:
    """Text colour for a solid ``colour`` fill: white or near-black."""
    return "#FFFFFF" if contrast_ratio("#FFFFFF", colour) >= contrast_ratio("#111111", colour) else "#111111"


def repair_contrast(theme: Theme) -> Theme:
    surfaces = [theme.bg, theme.surface]
    text = _readable(theme.text, surfaces)
    if text != theme.text:
        theme.repairs.append(f"text {theme.text}->{text}")
        theme.text = text
    muted = _readable(theme.muted, surfaces)
    if muted != theme.muted:
        theme.repairs.append(f"muted {theme.muted}->{muted}")
        theme.muted = muted
    # The primary is used as TEXT (prices, links) on both surfaces and as a
    # FILL under on_primary. The fill may stay the brand colour; the text
    # use is what has to read.
    primary_text = _readable(theme.primary, surfaces)
    if primary_text != theme.primary:
        theme.repairs.append(f"primary {theme.primary}->{primary_text}")
        theme.primary = primary_text
    theme.on_primary = _on(theme.primary)
    accent = _readable(theme.accent, surfaces, 3.0)  # accent is decorative: rules, badges
    if accent != theme.accent:
        theme.repairs.append(f"accent {theme.accent}->{accent}")
        theme.accent = accent
    return theme


# ---------------------------------------------------------------------------
# Building a theme
# ---------------------------------------------------------------------------

def variant_for(direction: str = "", design_style: Optional[str] = None) -> str:
    style = (design_style or "").strip().lower()
    if style in ("bold", "doodle", "playful"):
        return "outline"
    if style in ("elegant", "classic"):
        return "editorial"
    key = (direction or "").lower()
    if any(k in key for k in _OUTLINE_DIRECTIONS):
        return "outline"
    if any(k in key for k in _EDITORIAL_DIRECTIONS):
        return "editorial"
    return "soft"


def default_theme(dark: bool = False, design_style: Optional[str] = None) -> Theme:
    pal = _FALLBACK_DARK if dark else _FALLBACK_LIGHT
    theme = Theme(
        bg=pal["bg"], surface=pal["surface"], text=pal["text"], muted=pal["muted"],
        primary=pal["accent"], on_primary="#FFFFFF", accent=pal["accent_2"],
        display_font="Plus Jakarta Sans", body_font="Inter", variant=variant_for("", design_style),
        dark=dark, source="fallback",
    )
    return repair_contrast(theme)


def theme_from_plan(plan: Any, *, color_mode: str = "light", design_style: Optional[str] = None,
                    brand_colors: Optional[Dict[str, str]] = None) -> Theme:
    """A repaired ``Theme`` from a design plan (``DesignPlan`` or its
    ``as_dict()``). Missing or malformed plan → the fallback theme."""
    dark = str(color_mode or "").lower() == "dark"
    if plan is None:
        return default_theme(dark, design_style)
    data = plan.as_dict() if hasattr(plan, "as_dict") else (plan if isinstance(plan, dict) else {})
    palette = data.get("palette") if isinstance(data.get("palette"), dict) else {}
    typ = data.get("type") if isinstance(data.get("type"), dict) else {}
    if str(data.get("theme") or "").lower() == "dark":
        dark = True
    fallback = _FALLBACK_DARK if dark else _FALLBACK_LIGHT
    primary = _hex(palette.get("accent"), fallback["accent"])
    if brand_colors and normalize_hex(str(brand_colors.get("primary") or "")):
        primary = normalize_hex(str(brand_colors["primary"]))
    theme = Theme(
        bg=_hex(palette.get("bg"), fallback["bg"]),
        surface=_hex(palette.get("surface"), fallback["surface"]),
        text=_hex(palette.get("text"), fallback["text"]),
        muted=_hex(palette.get("muted"), fallback["muted"]),
        primary=primary,
        on_primary="#FFFFFF",
        accent=_hex(palette.get("accent_2"), fallback["accent_2"]),
        display_font=str(typ.get("display") or "Plus Jakarta Sans").strip() or "Plus Jakarta Sans",
        body_font=str(typ.get("body") or "Inter").strip() or "Inter",
        variant=variant_for(str(data.get("direction") or ""), design_style),
        dark=dark,
        source=str(data.get("source") or "plan"),
    )
    # The background must agree with the mode: a plan that answered "dark"
    # with a cream page is repainted to the fallback neutrals.
    if dark and relative_luminance(theme.bg) > 0.3:
        theme.bg, theme.surface, theme.text, theme.muted = fallback["bg"], fallback["surface"], fallback["text"], fallback["muted"]
        theme.repairs.append("dark mode: neutrals replaced")
    if not dark and relative_luminance(theme.bg) < 0.4:
        theme.bg, theme.surface, theme.text, theme.muted = fallback["bg"], fallback["surface"], fallback["text"], fallback["muted"]
        theme.repairs.append("light mode: neutrals replaced")
    return repair_contrast(theme)


# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------

def _font_stack(name: str) -> str:
    safe = name.replace("'", "")
    return f"'{safe}', {_SYSTEM_FALLBACK}"


def render_css(theme: Theme) -> str:
    """One stylesheet for every section. Mobile-first; nothing in it can
    exceed the viewport (every row wraps, every image is max-width:100%,
    long words break). The variant only changes radius/borders/shadows."""
    radius = {"soft": "1rem", "outline": "0", "editorial": "0.25rem"}[theme.variant]
    btn_radius = {"soft": "999px", "outline": "0", "editorial": "0.25rem"}[theme.variant]
    card_border = {
        "soft": "1px solid color-mix(in srgb, var(--text-color) 10%, transparent)",
        "outline": "3px solid var(--text-color)",
        "editorial": "1px solid color-mix(in srgb, var(--text-color) 18%, transparent)",
    }[theme.variant]
    card_shadow = {"soft": "0 8px 28px rgba(0,0,0,.07)", "outline": "6px 6px 0 var(--text-color)", "editorial": "none"}[theme.variant]
    heading_tt = "text-transform:uppercase;letter-spacing:.02em;" if theme.variant == "outline" else ""
    return f"""<style id="binaapp-sections-css">
:root{{--bg-color:{theme.bg};--surface-color:{theme.surface};--text-color:{theme.text};--text-muted:{theme.muted};--primary-color:{theme.primary};--on-primary:{theme.on_primary};--accent-color:{theme.accent};--secondary-color:{theme.accent};--font-heading:{_font_stack(theme.display_font)};--font-body:{_font_stack(theme.body_font)};--radius:{radius};--btn-radius:{btn_radius};--card-border:{card_border};--card-shadow:{card_shadow};}}
*,*::before,*::after{{box-sizing:border-box}}
html{{-webkit-text-size-adjust:100%;scroll-behavior:smooth}}
body{{margin:0;background:var(--bg-color);color:var(--text-color);font-family:var(--font-body);line-height:1.55;overflow-x:hidden;overflow-wrap:anywhere}}
img,video,iframe{{max-width:100%}}
h1,h2,h3,h4{{font-family:var(--font-heading);line-height:1.15;margin:0;color:var(--text-color);{heading_tt}}}
p{{margin:0}}
a{{color:inherit}}
.bs-wrap{{width:100%;max-width:72rem;margin:0 auto;padding:0 1.25rem}}
.bs-section{{padding:3.5rem 0}}
.bs-section.bs-alt{{background:var(--surface-color)}}
.bs-h2{{font-size:clamp(1.75rem,4.5vw,2.5rem);font-weight:800;text-align:center;margin-bottom:.5rem}}
.bs-lead{{text-align:center;color:var(--text-muted);max-width:40rem;margin:0 auto 2rem;font-size:1.05rem}}
.bs-rule{{width:3rem;height:4px;background:var(--accent-color);margin:.75rem auto 2rem;border-radius:{"0" if theme.variant == "outline" else "999px"}}}
/* buttons: always icon + label, never wider than the viewport */
.bs-btn{{display:inline-flex;align-items:center;justify-content:center;gap:.55rem;min-height:3rem;padding:.8rem 1.4rem;border-radius:var(--btn-radius);font-weight:700;font-size:1rem;text-decoration:none;max-width:100%;white-space:normal;text-align:left;border:2px solid transparent;transition:filter .15s,transform .15s}}
.bs-btn svg{{width:1.25rem;height:1.25rem;flex:0 0 auto;fill:currentColor}}
.bs-btn:hover{{filter:brightness(1.08);transform:translateY(-1px)}}
.bs-btn-primary{{background:var(--primary-color);color:var(--on-primary);border-color:var(--primary-color)}}
.bs-btn-wa{{background:#0E7466;color:#fff;border-color:#0E7466}}
.bs-btn-ghost{{background:transparent;color:var(--text-color);border-color:var(--text-color)}}
.bs-btn-ghost.bs-on-dark{{color:#fff;border-color:#fff}}
{".bs-btn{box-shadow:4px 4px 0 var(--text-color)}.bs-btn-ghost.bs-on-dark{box-shadow:4px 4px 0 #fff}" if theme.variant == "outline" else ""}
/* nav */
.bs-nav{{position:sticky;top:0;z-index:50;background:color-mix(in srgb,var(--bg-color) 92%,transparent);backdrop-filter:blur(8px);border-bottom:1px solid color-mix(in srgb,var(--text-color) 10%,transparent)}}
.bs-nav .bs-wrap{{display:flex;align-items:center;justify-content:space-between;gap:1rem;min-height:4rem}}
.bs-brand{{display:flex;align-items:center;gap:.6rem;font-family:var(--font-heading);font-weight:800;font-size:1.1rem;text-decoration:none;min-width:0}}
.bs-brand img{{height:2.5rem;width:auto;max-width:8rem;object-fit:contain}}
.bs-brand span{{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.bs-nav-links{{display:none;gap:1.4rem;list-style:none;margin:0;padding:0;font-weight:600}}
.bs-nav-links a{{text-decoration:none;color:var(--text-color)}}
.bs-nav .bs-btn{{min-height:2.5rem;padding:.5rem 1rem;font-size:.9rem}}
.bs-nav .bs-btn .bs-btn-text{{display:none}}
@media (min-width:768px){{.bs-nav-links{{display:flex}}.bs-nav .bs-btn .bs-btn-text{{display:inline}}}}
/* hero */
.bs-hero{{position:relative;display:flex;flex-direction:column;justify-content:flex-end;min-height:min(92vh,46rem);color:#fff;isolation:isolate;overflow:hidden}}
.bs-hero-media{{position:absolute;inset:0;z-index:-2}}
.bs-hero-media img{{width:100%;height:100%;object-fit:cover;display:block}}
.bs-hero-scrim{{position:absolute;inset:0;z-index:-1;background:linear-gradient(180deg,rgba(0,0,0,.15) 0%,rgba(0,0,0,.35) 45%,rgba(0,0,0,.78) 100%)}}
.bs-hero-solid{{min-height:auto;color:var(--text-color);background:var(--surface-color)}}
.bs-hero .bs-wrap{{padding-top:4rem;padding-bottom:6.5rem;position:relative;z-index:1}}
@media (min-width:768px){{.bs-hero .bs-wrap{{padding-bottom:3rem}}}}
.bs-hero-solid .bs-wrap{{padding-top:4.5rem;padding-bottom:4rem}}
.bs-kicker{{display:inline-block;font-weight:700;font-size:.8rem;letter-spacing:.14em;text-transform:uppercase;margin-bottom:.9rem;padding:.3rem .7rem;border-radius:var(--btn-radius);background:var(--primary-color);color:var(--on-primary)}}
.bs-h1{{font-size:clamp(2.1rem,7vw,4.25rem);font-weight:800;max-width:18ch;color:inherit;text-wrap:balance}}
.bs-sub{{margin-top:1rem;font-size:clamp(1.05rem,2.2vw,1.3rem);max-width:38rem;color:inherit;opacity:.95}}
.bs-hero-solid .bs-sub{{color:var(--text-muted);opacity:1}}
.bs-cta-row{{display:flex;flex-wrap:wrap;gap:.75rem;margin-top:1.6rem}}
.bs-cta-row .bs-btn{{flex:1 1 auto}}
@media (min-width:640px){{.bs-cta-row .bs-btn{{flex:0 0 auto}}}}
.bs-hero-note{{margin-top:1.25rem;display:flex;flex-wrap:wrap;gap:.5rem 1.2rem;font-size:.92rem;opacity:.9}}
.bs-ai-label{{position:absolute;right:.6rem;top:.6rem;z-index:1;padding:.15rem .45rem;border-radius:4px;background:rgba(0,0,0,.6);color:#fff;font-size:.68rem;font-weight:600;pointer-events:none}}
/* options strip (spice levels etc.) */
.bs-strip{{background:var(--surface-color);border-top:var(--card-border);border-bottom:var(--card-border);padding:1rem 0}}
.bs-strip .bs-wrap{{display:flex;flex-wrap:wrap;align-items:center;justify-content:center;gap:.6rem}}
.bs-strip-title{{font-weight:700;font-size:.95rem;margin-right:.4rem;white-space:nowrap}}
.bs-chip{{display:inline-flex;align-items:center;gap:.35rem;padding:.45rem .85rem;border-radius:var(--btn-radius);border:2px solid var(--primary-color);color:var(--primary-color);font-weight:700;font-size:.9rem;white-space:nowrap}}
.bs-chip svg{{width:1rem;height:1rem;fill:currentColor}}
/* info banners */
.bs-banners{{padding:2rem 0}}
.bs-banners .bs-wrap{{display:grid;gap:.9rem;grid-template-columns:1fr}}
@media (min-width:768px){{.bs-banners .bs-wrap{{grid-template-columns:repeat(auto-fit,minmax(16rem,1fr))}}}}
.bs-banner{{display:flex;gap:.9rem;align-items:flex-start;padding:1rem 1.1rem;background:var(--surface-color);border:var(--card-border);border-left:6px solid var(--primary-color);border-radius:var(--radius);box-shadow:var(--card-shadow)}}
.bs-banner svg{{width:1.5rem;height:1.5rem;flex:0 0 auto;fill:var(--primary-color)}}
.bs-banner strong{{display:block;font-family:var(--font-heading);font-size:1rem;margin-bottom:.15rem}}
.bs-banner p{{color:var(--text-muted);font-size:.95rem}}
/* coming soon */
.bs-soon-list{{display:flex;flex-wrap:wrap;justify-content:center;gap:.6rem;list-style:none;margin:0;padding:0}}
.bs-soon-list li{{padding:.55rem 1rem;border-radius:var(--btn-radius);background:var(--surface-color);border:var(--card-border);font-weight:600}}
/* about */
.bs-about .bs-wrap{{display:grid;gap:2rem;align-items:center;grid-template-columns:1fr}}
@media (min-width:860px){{.bs-about .bs-wrap.bs-has-photo{{grid-template-columns:1fr 1fr}}}}
.bs-about-text .bs-h2{{text-align:left}}
.bs-about-text .bs-rule{{margin-left:0}}
.bs-about-text p{{color:var(--text-muted);font-size:1.05rem;margin-bottom:1rem}}
.bs-about-photo{{position:relative;border-radius:var(--radius);overflow:hidden;border:var(--card-border);box-shadow:var(--card-shadow)}}
.bs-about-photo img{{display:block;width:100%;aspect-ratio:4/3;object-fit:cover}}
.bs-about-facts{{display:grid;gap:.75rem;grid-template-columns:repeat(auto-fit,minmax(9rem,1fr));margin-top:1.25rem}}
.bs-fact{{padding:.9rem 1rem;background:var(--surface-color);border:var(--card-border);border-radius:var(--radius)}}
.bs-fact strong{{display:block;font-family:var(--font-heading);font-size:1.1rem;color:var(--primary-color)}}
.bs-fact span{{font-size:.85rem;color:var(--text-muted)}}
/* location */
.bs-location .bs-grid{{display:grid;gap:1.5rem;grid-template-columns:1fr}}
@media (min-width:860px){{.bs-location .bs-grid{{grid-template-columns:5fr 7fr;align-items:start}}}}
.bs-info-card{{padding:1.4rem;background:var(--surface-color);border:var(--card-border);border-radius:var(--radius);box-shadow:var(--card-shadow)}}
.bs-info-row{{display:flex;gap:.8rem;align-items:flex-start;padding:.7rem 0;border-bottom:1px solid color-mix(in srgb,var(--text-color) 10%,transparent)}}
.bs-info-row:last-child{{border-bottom:0}}
.bs-info-row svg{{width:1.3rem;height:1.3rem;flex:0 0 auto;fill:var(--primary-color);margin-top:.15rem}}
.bs-info-row strong{{display:block;font-size:.8rem;letter-spacing:.08em;text-transform:uppercase;color:var(--text-muted);margin-bottom:.15rem}}
.bs-info-row a{{text-decoration:none;color:var(--primary-color);font-weight:600}}
.bs-map{{border-radius:var(--radius);overflow:visible;min-height:1px}}
.bs-map iframe{{width:100%;aspect-ratio:16/10;border:0;border-radius:var(--radius);display:block}}
.bs-map .binaapp-map-widget{{padding:0!important}}
/* contact */
.bs-contact .bs-cta-row{{justify-content:center;margin-top:1.25rem}}
.bs-hours{{margin:0;padding:0;list-style:none}}
/* footer */
.bs-footer{{background:{"#0E0C0A" if not theme.dark else "var(--surface-color)"};color:#F5F0E8;padding:3rem 0 6.5rem}}
.bs-footer .bs-wrap{{display:grid;gap:2rem;grid-template-columns:1fr}}
@media (min-width:768px){{.bs-footer .bs-wrap{{grid-template-columns:2fr 1fr 1fr}}}}
.bs-footer h4{{color:#F5F0E8;font-size:.85rem;letter-spacing:.1em;text-transform:uppercase;margin-bottom:.8rem}}
.bs-footer p,.bs-footer li{{color:#D6CFC4;font-size:.95rem}}
.bs-footer ul{{list-style:none;margin:0;padding:0;display:grid;gap:.45rem}}
.bs-footer a{{color:#F5F0E8;text-decoration:none}}
.bs-footer .bs-brand{{color:#F5F0E8;margin-bottom:.75rem}}
.bs-footer-bottom{{margin-top:2rem;padding-top:1.2rem;border-top:1px solid rgba(255,255,255,.14);font-size:.85rem;color:#B8AFA3;text-align:center}}
.bs-footer-pay{{display:flex;flex-wrap:wrap;gap:.5rem;margin-top:.5rem}}
.bs-footer-pay span{{padding:.3rem .6rem;border:1px solid rgba(255,255,255,.3);border-radius:var(--btn-radius);font-size:.8rem}}
@media (prefers-reduced-motion:reduce){{*{{animation:none!important;transition:none!important}}html{{scroll-behavior:auto}}}}
</style>"""


def esc(text: Any) -> str:
    return _html.escape(str(text if text is not None else ""), quote=True)
