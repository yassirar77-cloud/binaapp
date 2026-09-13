"""
Prompt blocks for Pass 2 (the HTML build) when a design plan exists.

These are the rules that turn a validated ``DesignPlan`` into a page that
looks designed for one merchant: the anti-template rules (§2), the
typography contract (§4), the Malaysian F&B section standards (§5), the
feature-toggle rules (§0), the quality floor (§8) and the hero readability
contract. They are pure string builders so the prompt and the lint that
checks the output can be tested against each other.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Sequence

from app.services import design_directions as dd
from app.services.design_plan import DesignPlan, MAX_FEATURED_MENU_ITEMS
from app.services.site_strings import string_table_block, strings_for


# ---------------------------------------------------------------------------
# §2 Anti-template rules
# ---------------------------------------------------------------------------

ANTI_TEMPLATE_RULES = """===== ANTI-TEMPLATE RULES (HARD RULES — the page is rejected by a linter if any is broken) =====
1. Headlines are set WHOLE. Never italicise, recolour, underline or wrap a single word of an h1/h2 in its own <span>. One colour, one weight, one style per headline.
2. At most ONE eyebrow/kicker label (small uppercase tracked text above a heading) on the whole page, and only if it carries real information (a neighbourhood, a year the merchant supplied, "Sejak 2009"). "Menu", "Tentang Kami", "Our Story" are NOT information — no eyebrow there. Section headings stand on their own.
3. Cards ONLY where the content is a set of equal items (menu / products / services / prices). About, story, location and contact use OPEN layouts: photo beside text, a full-bleed colour band, a ruled list, two columns of text. Never wrap every block in the same rounded card with the same grey shadow.
4. ONE page-load motion moment, on the hero only, exactly as the plan describes it, written as a CSS keyframe in the stylesheet. No AOS library, no data-aos attributes, no scroll-reveal on sections. Hover states on links, buttons and tiles only.
5. Buttons and links carry plain text. Never append "→", "➜", "»", "›" or an arrow icon to button or link text.
6. No middle-dot meta strings ("Halal · Shah Alam · 24 jam"). Write facts as sentences or as a short list with real structure.
7. The cream + serif + gold/terracotta look is not the default. Use ONLY the palette in the design plan.
8. No placeholder UI: no fake map card, no "Buka 9am–10pm" the merchant did not supply, no "coming soon", no empty gallery grid, no invented reviews or ratings.
9. No inline style="font-size" on h1/h2/h3. Type sizes live in the <style> block using clamp() and the plan's scale.
10. No third hero button. The hero CTA row is at most two actions.
"""


# ---------------------------------------------------------------------------
# §4 Typography contract
# ---------------------------------------------------------------------------

def typography_block(plan: DesignPlan) -> str:
    ratio = dd.TYPE_SCALES.get(plan.type["scale"], 1.25)
    serif_body = dd.font_class(plan.type["body"]) == "serif"
    body_lh = "1.7" if serif_body else "1.6"
    display, body = plan.type["display"], plan.type["body"]
    weight = plan.type["display_weight"]
    steps = {
        "h3": round(1.125 * ratio, 3),
        "h2": round(1.125 * ratio ** 3, 3),
        "h1": round(1.125 * ratio ** 5, 3),
    }
    return f"""===== TYPOGRAPHY (from the plan — FONT LOCK) =====
- Display face '{display}' at weight {weight} for h1 and h2 only. Body face '{body}' for everything else, 16–18px, line-height {body_lh}.
- Modular scale {plan.type['scale']}. Put this in the <style> block and use these classes — no inline font-size on headings:
  :root {{ --step-1: clamp(1.125rem, 1rem + 0.5vw, {steps['h3']}rem); --step-3: clamp(1.75rem, 1.2rem + 2.2vw, {steps['h2']}rem); --step-5: clamp(2.5rem, 1.5rem + 5vw, {max(steps['h1'], 3.5)}rem); }}
  h1 {{ font-family: '{display}', {dd.FONT_FALLBACKS_FOR.get(dd.font_class(display), 'sans-serif')}; font-weight: {weight}; font-size: var(--step-5); line-height: 1.02; letter-spacing: -0.02em; text-wrap: balance; }}
  h2 {{ font-family: '{display}', {dd.FONT_FALLBACKS_FOR.get(dd.font_class(display), 'sans-serif')}; font-weight: {weight}; font-size: var(--step-3); line-height: 1.1; text-wrap: balance; }}
  h3 {{ font-size: var(--step-1); font-weight: 600; }}
  p, li {{ max-width: 65ch; }}
- The headline is a design element: it may be very large, tight or stacked on several lines. It may NOT be decorated with colour splits, italic words, gradients or outlined text.
- Do not load any other font. The only fonts <link> is the one in the HEAD section.
"""


# ---------------------------------------------------------------------------
# §5 Section standards
# ---------------------------------------------------------------------------

def _hero_rules(plan: DesignPlan, S: Dict[str, str], has_whatsapp: bool, hero_video: bool, is_fnb: bool) -> str:
    primary = S["cta_order_whatsapp"] if has_whatsapp else (S["cta_book"] if plan.vertical == "salon" else S["cta_call"] if plan.vertical == "services" else S["cta_view_products"])
    secondary = {
        "food": S["cta_view_menu"], "bakery": S["cta_view_menu"], "clothing": S["cta_view_collection"],
        "salon": S["cta_view_services"], "services": S["cta_view_services"], "general": S["cta_view_products"],
    }[plan.vertical if plan.vertical in dd.VERTICALS else "general"]
    if not has_whatsapp and primary == secondary:
        secondary = ""
    video_line = ""
    if hero_video:
        video_line = (
            '- HERO VIDEO: the hero <section> carries the attribute data-binaapp-hero-video="1" and the hero image is its poster '
            "(an <img> or background covering the section). The page-load motion is the video itself — no keyframe animation on the hero.\n"
        )
    return f"""HERO — the most characteristic thing first ({plan.hero_treatment}):
- Headline: the dish / product / service name the merchant is known for when the description names one, otherwise the business name. One line beneath it, from the description.
- Text on a photo MUST sit on a solid panel or a gradient scrim (rgba overlay ≥ 0.45 on the text side) so it reads at 4.5:1. Outlined buttons on a photo get a translucent fill (bg-white/15 backdrop-blur).
- CTA row = "{primary}"{f' + "{secondary}" (anchor to the section)' if secondary else ''}. NO third button.
{video_line}- On a 390px phone: headline, line and CTA row visible without scrolling; the primary CTA is thumb-reachable (also a fixed bottom bar on mobile is acceptable when the plan's layout calls for it).
"""


def _menu_rules(S: Dict[str, str], has_whatsapp: bool, item_count: int, has_item_images: bool, show_prices: bool, wa_digits: str, prefill: str) -> str:
    featured = min(item_count, MAX_FEATURED_MENU_ITEMS) if item_count else 0
    more = ""
    if item_count > MAX_FEATURED_MENU_ITEMS:
        more = f"- Show the first {MAX_FEATURED_MENU_ITEMS} as featured tiles; the remaining {item_count - MAX_FEATURED_MENU_ITEMS} go in a plain ruled list under a \"{S['cta_full_menu']}\" heading (same section, no second grid).\n"
    tile = (
        "- Every item tile has its photo (4:3, object-cover, identical size across tiles) — never a placeholder icon."
        if has_item_images else
        f"- No item photos were supplied: render TYPOGRAPHIC tiles — the item name set large in the display face on the accent (or accent_2) colour block, the price beneath. NEVER a placeholder icon, emoji, or grey image box."
    )
    price = "- Prices large and aligned (same baseline, same size on every tile), copied character-for-character." if show_prices else "- Prices are OFF: no price element and no substitute wording."
    wa = (
        f"- Every tile has its own \"{S['cta_order_item']}\" link deep-linking WhatsApp with the item name prefilled: https://wa.me/{wa_digits}?text={prefill.replace(' ', '%20')}%20ITEM_NAME (URL-encoded)."
        if has_whatsapp and wa_digits else
        "- No WhatsApp number: tiles carry no order button."
    )
    return f"""MENU — the core of the site ({featured} featured tile(s)):
- A grid of EQUAL tiles (2-up on mobile, 3-up on desktop, identical heights) — this is the ONE place cards are expected.
{tile}
{price}
{wa}
{more}"""


def _about_rules() -> str:
    return """ABOUT / STORY — open layout:
- One photo (if an unused photo exists) beside two short paragraphs written from the description. No card, no shadow, no box.
- No quote block unless the merchant supplied a quote. At most ONE trust fact, and only if the description states it (year founded, "Pengusaha Muslim", an award).
"""


def _location_rules(S: Dict[str, str], address: Optional[str], include_maps: bool, hours: Optional[str]) -> str:
    if not address:
        return """LOCATION — no address was supplied: omit the location section entirely (no map, no invented address, no "Jumpa Kami" filler). Keep hours out unless supplied.
"""
    from urllib.parse import quote_plus
    maps_line = (
        '- Google Maps ON: the map is injected later into the empty slot <div id="binaapp-maps-slot"></div> — emit that slot beside the address text (a 16:9 area) and do NOT embed your own iframe or draw a map.'
        if include_maps else
        f'- Google Maps OFF: address TEXT only plus one link "{S["cta_open_maps"]}" → https://www.google.com/maps/search/?api=1&query={quote_plus(address)}. NO map card, NO decorative map illustration, NO iframe.'
    )
    hours_line = f"- Hours (supplied — render exactly): {hours}" if hours else "- Hours were NOT supplied: do not render any opening hours."
    return f"""LOCATION & HOURS:
- Address text exactly: {address}
{maps_line}
{hours_line}
- Never a decorative "map card" or a fake map image.
"""


def _gallery_rules(gallery_count: int) -> str:
    if gallery_count >= 3:
        return f"GALLERY — {gallery_count} gallery photo(s) supplied: a simple grid at 3:2 with identical tile sizes, no captions unless supplied.\n"
    return "GALLERY — fewer than 3 non-menu photos: NO gallery section.\n"


def _contact_rules(S: Dict[str, str], has_whatsapp: bool, include_contact_form: bool, include_social: bool, socials: Optional[Dict[str, str]]) -> str:
    lines = ["CONTACT — ONE CTA band, not two sections:"]
    if has_whatsapp:
        lines.append(f'- One full-width band with a short line and the "{S["cta_chat_whatsapp"]}" button. Never a separate "Hantar Mesej" section AND a "Jumpa Kami" section that both carry WhatsApp.')
    else:
        lines.append("- No WhatsApp number: the band carries the address / hours text and, if provided, the form slot only.")
    if include_contact_form:
        lines.append('- Borang Tempahan ON: emit the empty slot <div id="binaapp-contact-slot"></div> inside the band; the form is injected later. Do not build your own form.')
    else:
        lines.append("- Borang Tempahan OFF: NO contact form, NO form slot, NO input fields anywhere on the page.")
    if include_social and socials:
        handles = ", ".join(f"{k}: {v}" for k, v in socials.items() if v)
        lines.append(f"- Social Media ON: icon links for exactly these handles ({handles}) in the band and footer.")
    else:
        lines.append("- Social Media OFF: no social icons or links anywhere.")
    return "\n".join(lines) + "\n"


def _footer_rules(S: Dict[str, str], address: Optional[str], hours: Optional[str], has_whatsapp: bool, payment_methods: Sequence[str]) -> str:
    badges = []
    if "cod" in payment_methods:
        badges.append(S["payment_cod"])
    if "qr" in payment_methods:
        badges.append(S["payment_qr"])
    pay = f'- Payment badges (text pills under "{S["label_payment"]}"): {", ".join(badges)}.' if badges else "- No payment badges (none selected)."
    return f"""FOOTER:
- Business name, {'the address, ' if address else ''}{'the hours, ' if hours else ''}the nav links{', the WhatsApp link' if has_whatsapp else ''}, and the © line with the dynamic year.
{pay}
- No QR code image (the site has no published address yet) and no newsletter form.
"""


def section_standards_block(
    plan: DesignPlan,
    *,
    language: str,
    has_whatsapp: bool,
    wa_digits: str = "",
    address: Optional[str],
    hours: Optional[str],
    include_maps: bool,
    include_contact_form: bool,
    include_social: bool,
    socials: Optional[Dict[str, str]],
    item_count: int,
    has_item_images: bool,
    show_prices: bool,
    gallery_count: int,
    hero_video: bool,
    payment_methods: Sequence[str],
) -> str:
    S = strings_for(language)
    is_fnb = plan.vertical in dd.FNB_VERTICALS
    parts: List[str] = ["===== SECTION STANDARDS (build each listed section exactly like this) =====",
                        _hero_rules(plan, S, has_whatsapp, hero_video, is_fnb)]
    if is_fnb and "menu" in plan.sections:
        parts.append(_menu_rules(S, has_whatsapp, item_count, has_item_images, show_prices, wa_digits, S["wa_prefill"]))
    elif plan.vertical == "clothing":
        parts.append(
            "KOLEKSI — a lookbook grid of the supplied products (photo tiles, item name and price beneath), then SAIZ & PENGHANTARAN as two columns of plain text from the description, then CARA ORDER as three numbered lines. No Menu section.\n"
        )
    elif plan.vertical == "salon":
        parts.append(
            "SERVIS & HARGA — a ruled price list (service name left, price right, dotted leaders) from the supplied items; TEMPAH — one booking band with the WhatsApp/booking CTA; GALERI KERJA only when ≥ 3 work photos exist. No Menu section.\n"
        )
    elif plan.vertical == "services":
        parts.append(
            "PERKHIDMATAN — a checklist grid of the supplied services (SVG tick, name, one line); KAWASAN LIPUTAN — a plain list of the areas from the description; HUBUNGI — phone-first with the number as large as a heading; TESTIMONI only if supplied. No Menu section.\n"
        )
    else:
        parts.append(
            "PRODUK — a grid of equal product tiles from the supplied items with prices; CARA ORDER — three numbered lines. No Menu section.\n"
        )
    if "about" in plan.sections:
        parts.append(_about_rules())
    if "location" in plan.sections or "hubungi" in plan.sections:
        parts.append(_location_rules(S, address, include_maps, hours))
    parts.append(_gallery_rules(gallery_count))
    parts.append(_contact_rules(S, has_whatsapp, include_contact_form, include_social, socials))
    parts.append(_footer_rules(S, address, hours, has_whatsapp, payment_methods))
    parts.append(string_table_block(language))
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# §8 Quality floor
# ---------------------------------------------------------------------------

QUALITY_FLOOR_RULES = """===== QUALITY FLOOR (always, invisible) =====
- Responsive down to 360px: no horizontal overflow, grids collapse to one or two columns, images never exceed their container.
- Visible keyboard focus: a :focus-visible rule with a 2px outline in the accent colour on every link, button and input.
- Respect prefers-reduced-motion: wrap the hero keyframe in @media (prefers-reduced-motion: no-preference) {} so reduced-motion users get a static hero.
- WCAG AA contrast everywhere: text on bg/surface ≥ 4.5:1, accent-coloured text uses var(--accent-strong).
- Every <img> has a descriptive alt, width and height attributes (use the rendered aspect ratio, e.g. width="800" height="600"), and loading="lazy" below the fold (the hero image is eager).
- Semantic landmarks: <header>, <main>, <section> with ids, <footer>. One <h1> only.
"""


def head_block(plan: DesignPlan, fonts_cdn: str, tw_config: str, palette: Dict[str, str], accent_fill: str, accent_strong: str, body_font: str, body_fallback: str) -> str:
    """HEAD contract for plan mode — no AOS."""
    return f"""===== HEAD SECTION (MUST INCLUDE ALL — and NOTHING else external) =====
{fonts_cdn}
<script src="https://cdn.tailwindcss.com"></script>
{tw_config}
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
<style>
html {{ scroll-behavior: smooth; scroll-padding-top: 5rem; }}
:root {{ --bg-color: {palette['background']}; --surface-color: {palette['surface']}; --text-color: {palette['text']}; --text-muted-color: {palette['text_muted']}; --accent-color: {accent_fill}; --accent-strong: {accent_strong}; }}
body {{ background-color: var(--bg-color); color: var(--text-color); font-family: '{body_font}', {body_fallback}; }}
:focus-visible {{ outline: 2px solid var(--accent-strong); outline-offset: 2px; }}
@media (prefers-reduced-motion: reduce) {{ *, *::before, *::after {{ animation: none !important; transition: none !important; }} }}
</style>
(Do NOT load AOS or any animation library. The single hero motion moment is a CSS keyframe you write in this <style> block.)

===== BEFORE </body> (MUST INCLUDE) =====
<script>document.getElementById('binaapp-year').textContent=new Date().getFullYear()</script>
"""
