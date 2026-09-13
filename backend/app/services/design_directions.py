"""
Direction library — the seed catalogue of design directions a site can take.

A *direction* is a complete, opinionated starting point: a palette family, a
type pairing, a hero treatment and ONE signature device, plus the merchant
verticals and picker styles it serves. The design-plan step (Pass 1, see
``design_plan.py``) picks the closest direction for the food, audience and
place described in the brief, adapts the colours to the merchant's own photos
and writes the plan the HTML pass (Pass 2) must then execute.

Why a library instead of "let the model design freely": with no anchor every
generation converged on the same look — cream background, serif display, one
gold/terracotta accent, an italic word in every headline, an ALL-CAPS eyebrow
above every heading, identical rounded cards, fade-up on every section. A
catalogue of visibly different starting points plus a rolling "do not repeat
the last three directions in this category" rule is what keeps two mamak
sites from looking like the same template with a new colour.

House rules encoded here:

* **Bright by default.** Malaysian F&B sites are bright, appetising, warm and
  welcoming unless the merchant chose *Gelap* or the brief asks for a dark or
  night concept. Only ``theme == "dark"`` directions are dark, and the picker
  decides which theme family is even eligible.
* **Merchant picks are law.** ``styles`` tags map straight onto the create
  page's *Gaya design* picker (doodle / elegant / minimal / playful / bold /
  classic). A picked style restricts the candidate set to directions carrying
  that tag; *Auto* leaves the whole (theme-eligible) library open.
* **Every style × theme has at least two directions** so a pick can always
  rotate away from the previous site's direction (tested).
* **Non-F&B verticals get their own directions and section sets** — a salon
  never gets a "Menu" section.

Everything here is pure data + pure functions (no network, no I/O).
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

# ============================================================================
# TYPOGRAPHY — the curated allowlist (§4)
#
# Deliberately small. Every family here ships latin-ext so Bahasa Malaysia
# diacritics render, every one is a Google Fonts family the css2 API serves
# at the weights listed (a wrong weight 400s the whole stylesheet), and the
# display list is chosen so any two of them look different from each other.
# ============================================================================

#: role -> font -> {class, weights}. ``class`` drives the pairing rule: two
#: sans faces of the SAME class ("grotesk" + "grotesk") read as one font that
#: does not quite match, so they are never paired; serif + grotesk, grotesk +
#: humanist, rounded + humanist all read as deliberate.
DISPLAY_FONTS: Dict[str, Dict[str, str]] = {
    "Fraunces": {"class": "serif", "weights": "400;500;600;700;900"},
    "Playfair Display": {"class": "serif", "weights": "400;500;600;700;800"},
    "Instrument Serif": {"class": "serif", "weights": "400"},
    "Bricolage Grotesque": {"class": "grotesk", "weights": "400;500;600;700;800"},
    "Syne": {"class": "grotesk", "weights": "400;500;600;700;800"},
    "Unbounded": {"class": "grotesk", "weights": "400;500;600;700;800;900"},
    "Archivo Black": {"class": "grotesk", "weights": "400"},
    "Familjen Grotesk": {"class": "grotesk", "weights": "400;500;600;700"},
    "Rubik": {"class": "rounded", "weights": "400;500;600;700;800;900"},
    "Outfit": {"class": "rounded", "weights": "400;500;600;700;800;900"},
    # The two doodle / cartoon faces — the only way that style is allowed to
    # land. Emoji are never a substitute for a rounded display face.
    "Fredoka": {"class": "rounded", "weights": "400;500;600;700"},
    "Baloo 2": {"class": "rounded", "weights": "400;500;600;700;800"},
}

BODY_FONTS: Dict[str, Dict[str, str]] = {
    "DM Sans": {"class": "grotesk", "weights": "400;500;600;700"},
    "Inter": {"class": "grotesk", "weights": "400;500;600;700"},
    "Manrope": {"class": "grotesk", "weights": "400;500;600;700"},
    "IBM Plex Sans": {"class": "grotesk", "weights": "400;500;600;700"},
    "Source Sans 3": {"class": "humanist", "weights": "400;500;600;700"},
    "Nunito": {"class": "rounded", "weights": "400;500;600;700"},
}

ALLOWED_FONTS: Dict[str, Dict[str, str]] = {**DISPLAY_FONTS, **BODY_FONTS}

#: CSS fallback stack per class — what shows while (or if) the webfont never arrives.
FONT_FALLBACKS_FOR: Dict[str, str] = {
    "serif": "Georgia, 'Times New Roman', serif",
    "grotesk": "system-ui, -apple-system, 'Segoe UI', sans-serif",
    "humanist": "system-ui, -apple-system, 'Segoe UI', sans-serif",
    "rounded": "'Trebuchet MS', system-ui, sans-serif",
}
_FONT_LOOKUP = {name.lower(): name for name in ALLOWED_FONTS}

#: Modular type scales the plan may name. Anything else is snapped to the
#: nearest one so the CSS the page ships is always a real ratio.
TYPE_SCALES: Dict[str, float] = {
    "1.2 minor third": 1.2,
    "1.25 major third": 1.25,
    "1.333 perfect fourth": 1.333,
    "1.414 augmented fourth": 1.414,
    "1.5 perfect fifth": 1.5,
    "1.618 golden ratio": 1.618,
}


def resolve_allowed_font(name: Optional[str], role: str = "any") -> Optional[str]:
    """Map a model-supplied font name onto the allowlist (case/quote/plus
    tolerant). ``role`` narrows to display or body families."""
    if not name or not isinstance(name, str):
        return None
    cleaned = name.strip().strip("'\"").replace("+", " ")
    cleaned = cleaned.split(",")[0].strip().strip("'\"")
    cleaned = re.sub(r"\s+", " ", cleaned)
    canonical = _FONT_LOOKUP.get(cleaned.lower())
    if canonical is None:
        return None
    if role == "display" and canonical not in DISPLAY_FONTS:
        return None
    if role == "body" and canonical not in BODY_FONTS:
        return None
    return canonical


def font_class(name: str) -> str:
    return ALLOWED_FONTS.get(name, {}).get("class", "grotesk")


def is_valid_pairing(display: str, body: str) -> bool:
    """One family, or two clearly distinct families. Two sans of the same
    class (grotesk + grotesk) are the "two similar sans" the rules forbid."""
    if display == body:
        return True
    return font_class(display) != font_class(body)


def nearest_type_scale(value) -> str:
    """Snap a free-text scale ("1.25", "major third", "1.3") to a known one."""
    if isinstance(value, str):
        text = value.strip().lower()
        for label in TYPE_SCALES:
            if text == label or text in label or label.split(" ", 1)[1] in text:
                return label
        m = re.search(r"\d+(?:\.\d+)?", text)
        value = float(m.group(0)) if m else None
    try:
        ratio = float(value) if value is not None else None
    except (TypeError, ValueError):
        ratio = None
    if ratio is None:
        return "1.25 major third"
    return min(TYPE_SCALES, key=lambda label: abs(TYPE_SCALES[label] - ratio))


# ============================================================================
# DIRECTIONS
# ============================================================================

HERO_TREATMENTS = ("photo-full-bleed", "photo-split", "typographic", "pattern", "menu-first")

#: The picker's wire values (schemas.py design_style) and their labels.
STYLE_TAGS = ("doodle", "elegant", "minimal", "playful", "bold", "classic")
STYLE_LABELS_MS = {
    "doodle": "Doodle Kartun",
    "elegant": "Mewah",
    "minimal": "Minimalis",
    "playful": "Ceria",
    "bold": "Berani",
    "classic": "Klasik",
}

THEMES = ("bright", "dark")

#: Verticals as persisted on websites.business_type.
VERTICALS = ("food", "bakery", "clothing", "salon", "services", "general")


@dataclass(frozen=True)
class Direction:
    key: str
    name: str
    feel: str
    audience: str
    verticals: Tuple[str, ...]
    styles: Tuple[str, ...]
    theme: str  # "bright" | "dark"
    palette: Dict[str, str]  # bg, surface, text, muted, accent, accent_2
    type: Dict[str, object]  # display, body, scale, display_weight
    hero_treatment: str
    signature_element: str
    layout_notes: str
    motion: str
    avoid: Tuple[str, ...]
    keywords: Tuple[str, ...] = ()
    #: Cream + serif + gold is the default everything converges on. It is
    #: only allowed when a direction (or the plan's own justification)
    #: explicitly reaches for it.
    cream_allowed: bool = False
    #: Category-specific dish/service image cue used when images are generated.
    image_cue: str = ""

    def as_dict(self) -> Dict:
        return {
            "key": self.key,
            "name": self.name,
            "feel": self.feel,
            "audience": self.audience,
            "verticals": list(self.verticals),
            "styles": list(self.styles),
            "theme": self.theme,
            "palette": dict(self.palette),
            "type": dict(self.type),
            "hero_treatment": self.hero_treatment,
            "signature_element": self.signature_element,
            "layout_notes": self.layout_notes,
            "motion": self.motion,
            "avoid": list(self.avoid),
            "cream_allowed": self.cream_allowed,
        }


_DEFAULT_AVOID = (
    "italic or recoloured word inside a headline",
    "ALL-CAPS tracked eyebrow label above every heading",
    "identical rounded cards with the same grey shadow on every section",
    "fade-up on every section",
    "arrow glyphs appended to button text",
    "middle-dot meta strings (A · B · C)",
)


def _d(**kw) -> Direction:
    kw.setdefault("avoid", _DEFAULT_AVOID)
    return Direction(**kw)


DIRECTIONS: Tuple[Direction, ...] = (
    # ------------------------------------------------------------------ F&B bright
    _d(
        key="warung_cerah",
        name="Warung Cerah",
        feel="bright, loud, friendly",
        audience="mamak, nasi kandar, warung, kopitiam — walk-in crowds who order fast",
        verticals=("food",),
        styles=("playful", "bold"),
        theme="bright",
        palette={"bg": "#FFFFFF", "surface": "#FFF4D6", "text": "#1F1A17", "muted": "#5C5148", "accent": "#E8541E", "accent_2": "#F5B400"},
        type={"display": "Archivo Black", "body": "Source Sans 3", "scale": "1.333 perfect fourth", "display_weight": 400},
        hero_treatment="menu-first",
        signature_element="a saturated full-width colour band (turmeric yellow, not cream) that carries the menu highlights right under the name, with a hand-drawn wavy SVG divider top and bottom",
        layout_notes="left-aligned, tight 12-column grid, menu tiles with big RM prices, story as a plain two-column band with no card, contact as one strip",
        motion="the price tiles in the hero band slide in from the left once on load; nothing else moves",
        keywords=("mamak", "nasi kandar", "warung", "kopitiam", "gerai", "kedai makan", "tomyam", "roti canai", "teh tarik", "nasi campur", "restoran"),
        image_cue="close-up plated Malaysian dishes on a stainless steel counter, daylight",
    ),
    _d(
        key="pasar_pagi",
        name="Pasar Pagi",
        feel="fresh, morning light",
        audience="breakfast places, roti canai and nasi lemak stalls, morning kuih",
        verticals=("food", "bakery"),
        styles=("playful", "minimal"),
        theme="bright",
        palette={"bg": "#FFFFFF", "surface": "#F3F7F2", "text": "#17201B", "muted": "#4F5B54", "accent": "#D7262D", "accent_2": "#2E7D4F"},
        type={"display": "Bricolage Grotesque", "body": "Source Sans 3", "scale": "1.25 major third", "display_weight": 800},
        hero_treatment="photo-split",
        signature_element="oversized prices set in the display face next to each dish name, sized like a market chalkboard",
        layout_notes="white page, one strong warm colour used for prices and the order button only, split hero with the photo on the right, menu as a two-column list with hairline rules instead of cards",
        motion="the hero photo fades in and the headline settles up 8px on load; nothing else",
        keywords=("sarapan", "breakfast", "nasi lemak", "roti canai", "kuih", "pagi", "morning", "bubur", "lontong"),
        image_cue="nasi lemak and kuih on banana leaf in bright morning light",
    ),
    _d(
        key="kedai_kek",
        name="Kedai Kek",
        feel="soft, playful",
        audience="bakeries, dessert shops, cafés selling cakes and pastries",
        verticals=("bakery", "food"),
        styles=("doodle", "playful"),
        theme="bright",
        palette={"bg": "#FFF6F1", "surface": "#FFFFFF", "text": "#3B2A2A", "muted": "#7A6363", "accent": "#E4658A", "accent_2": "#6BB8A8"},
        type={"display": "Fredoka", "body": "Source Sans 3", "scale": "1.25 major third", "display_weight": 600},
        hero_treatment="photo-split",
        signature_element="a rounded product grid with generous whitespace where each tile sits on a soft pastel blob shape (SVG), never a hard-cornered card",
        layout_notes="pastel page, rounded display face, product grid 3-up desktop / 2-up mobile with 32px gutters, story as photo + text with no box",
        motion="the pastel blobs behind the hero photo drift 6px once on load; nothing else",
        keywords=("kek", "cake", "bakery", "bakeri", "roti", "pastri", "pastry", "dessert", "pencuci mulut", "cupcake", "brownies", "cookies", "biskut"),
        image_cue="cakes and pastries on a pale marble counter, soft window light",
    ),
    _d(
        key="kopi_moden",
        name="Kopi Moden",
        feel="calm, editorial-light",
        audience="specialty coffee, minimalist cafés, brunch spots",
        verticals=("food",),
        styles=("minimal",),
        theme="bright",
        palette={"bg": "#FAFAF8", "surface": "#F1EFEA", "text": "#1B1B19", "muted": "#5F5E58", "accent": "#5B7B63", "accent_2": "#B5654A"},
        type={"display": "Fraunces", "body": "Manrope", "scale": "1.333 perfect fourth", "display_weight": 500},
        hero_treatment="typographic",
        signature_element="a very large typographic hero — the shop name and one line about the coffee set at display size on an almost empty page, the photo arriving only in the second screen",
        layout_notes="near-white, one muted accent, wide margins (max-width 1100px), no cards anywhere: menu is a ruled list, story is two columns of text, location is a single line",
        motion="the hero headline's lines rise into place one after another on load; nothing else",
        keywords=("kopi", "coffee", "cafe", "café", "kafe", "espresso", "latte", "brunch", "specialty", "roaster"),
        image_cue="flat white and pour-over on a light wooden table, soft daylight",
    ),
    _d(
        key="dapur_keluarga",
        name="Dapur Keluarga",
        feel="warm, trustworthy",
        audience="family restaurants, catering, kenduri and home-cooked meals",
        verticals=("food",),
        styles=("classic",),
        theme="bright",
        palette={"bg": "#F7F1E6", "surface": "#FFFFFF", "text": "#2B2119", "muted": "#6A5A4E", "accent": "#9A3B2E", "accent_2": "#4F7A4A"},
        type={"display": "Fraunces", "body": "Source Sans 3", "scale": "1.25 major third", "display_weight": 600},
        hero_treatment="photo-full-bleed",
        signature_element="a photo-led story band: one wide kitchen or family photo with two short paragraphs beside it, set on the page background with no frame",
        layout_notes="cream is allowed here on purpose; humanist sans body; menu as equal tiles with photos; the story band and contact strip are open layouts with no cards",
        motion="the hero photo scales from 1.04 to 1 over 1.2s on load; nothing else",
        keywords=("keluarga", "family", "katering", "catering", "kenduri", "masakan kampung", "masakan rumah", "home cooked", "restoran keluarga"),
        cream_allowed=True,
        image_cue="a spread of home-cooked Malay dishes on a family table, warm daylight",
    ),
    _d(
        key="laut_api",
        name="Laut & Api",
        feel="bold, elemental",
        audience="seafood restaurants, ikan bakar, BBQ and grill houses",
        verticals=("food",),
        styles=("bold",),
        theme="bright",
        palette={"bg": "#FFFFFF", "surface": "#EDF3F6", "text": "#15232B", "muted": "#4C5C66", "accent": "#F25C1F", "accent_2": "#14506B"},
        type={"display": "Unbounded", "body": "Source Sans 3", "scale": "1.414 augmented fourth", "display_weight": 700},
        hero_treatment="photo-full-bleed",
        signature_element="one deep-sea blue texture band (SVG wave or grain) that cuts across the page between menu and story, with the flame-orange accent used only for prices and the order button",
        layout_notes="full-bleed hero with a solid bottom-left panel for the name, menu as a tight 3-up grid of photo tiles, story as text on the blue band in white, contact as one strip",
        motion="the hero photo fades in and the headline panel slides up once on load; nothing else",
        keywords=("seafood", "makanan laut", "ikan bakar", "bbq", "grill", "bakar", "udang", "ketam", "sotong", "steamboat"),
        image_cue="grilled fish and prawns over charcoal, close-up, bright daylight",
    ),
    _d(
        key="halal_street",
        name="Halal Street",
        feel="punchy, youthful",
        audience="burger stalls, western street food, food trucks",
        verticals=("food",),
        styles=("bold", "doodle"),
        theme="bright",
        palette={"bg": "#FFFFFF", "surface": "#FFF8E1", "text": "#121212", "muted": "#4A4A4A", "accent": "#FF3D00", "accent_2": "#FFC400"},
        type={"display": "Archivo Black", "body": "Rubik", "scale": "1.414 augmented fourth", "display_weight": 400},
        hero_treatment="menu-first",
        signature_element="rotated sticker badges (SVG, -6deg) carrying the real prices and the signature item name, poster-style, on the hero and the menu",
        layout_notes="high-contrast poster type, tight 8px grid with 16px gutters, menu as a dense 2-up grid, story as one bold pull-paragraph, contact strip in the accent colour",
        motion="the sticker badges pop in with a 200ms scale on load; nothing else",
        keywords=("burger", "street food", "food truck", "western", "hotdog", "chicken chop", "fries", "wrap", "kebab", "nachos"),
        image_cue="a stacked burger and fries on kraft paper, hard daylight, bold shadows",
    ),
    _d(
        key="coret_ceria",
        name="Coret Ceria",
        feel="hand-drawn, cheerful",
        audience="any shop that asked for the doodle / cartoon look",
        verticals=("food", "bakery", "general", "clothing"),
        styles=("doodle",),
        theme="bright",
        palette={"bg": "#FFFCF2", "surface": "#FFFFFF", "text": "#2B2B2B", "muted": "#6B6B6B", "accent": "#2F6BFF", "accent_2": "#FF6FA5"},
        type={"display": "Baloo 2", "body": "Source Sans 3", "scale": "1.25 major third", "display_weight": 700},
        hero_treatment="pattern",
        signature_element="hand-drawn inline SVG accents — scribbled underlines under the headline, a squiggle divider between sections, doodle stars and steam lines beside the menu tiles — drawn in the accent colour, never emoji",
        layout_notes="rounded display face at large sizes, tiles with a 2px hand-drawn (slightly wobbly path) border instead of shadows, story as speech-bubble-shaped panel, generous 40px section spacing",
        motion="the scribbled underline under the hero headline draws itself once on load (stroke-dashoffset); nothing else",
        keywords=("doodle", "kartun", "cartoon", "lukisan", "comel", "cute"),
        image_cue="flat cartoon illustration of the dishes, thick outlines, cheerful colours",
    ),
    _d(
        key="mewah_cerah",
        name="Mewah Cerah",
        feel="bright, refined",
        audience="patisseries, tea rooms, hotel-style dining, boutiques that asked for luxury without a dark page",
        verticals=("food", "bakery", "salon", "general"),
        styles=("elegant",),
        theme="bright",
        palette={"bg": "#FFFFFF", "surface": "#F6F1E9", "text": "#1E1E1E", "muted": "#5B5B5B", "accent": "#1F4D3A", "accent_2": "#B99B62"},
        type={"display": "Playfair Display", "body": "Manrope", "scale": "1.333 perfect fourth", "display_weight": 500},
        hero_treatment="photo-split",
        signature_element="a single thin gold rule (1px, accent_2) used once as the divider under the hero headline — the only gold on the page; everything else is white space and deep green",
        layout_notes="white page with a champagne surface for the menu block only, serif display at generous size, menu as an aligned price list with dotted leaders, story as two columns with wide margins",
        motion="the hero photo fades in over 900ms on load; nothing else",
        keywords=("mewah", "luxury", "premium", "eksklusif", "fine", "butik", "high tea", "tea room", "patisserie"),
        image_cue="an elegant plated dish on white porcelain, soft directional daylight",
    ),
    # ------------------------------------------------------------------ F&B dark
    _d(
        key="malam_bandar",
        name="Malam Bandar",
        feel="dark, dramatic",
        audience="steakhouses, western fine dining, lounges and night concepts",
        verticals=("food",),
        styles=("elegant", "classic"),
        theme="dark",
        palette={"bg": "#1B1F2A", "surface": "#242938", "text": "#F3EEE6", "muted": "#B7B0A4", "accent": "#C9A24D", "accent_2": "#8B2F2F"},
        type={"display": "Playfair Display", "body": "Manrope", "scale": "1.333 perfect fourth", "display_weight": 500},
        hero_treatment="photo-full-bleed",
        signature_element="a deep ink-navy page (not #111) with the gold accent used only three times: the price of the signature dish, the reservation button, and one hairline under the headline",
        layout_notes="full-bleed hero with a dark gradient scrim, serif display, menu as a two-column list with prices right-aligned, story as a photo beside text on the surface colour, contact strip with the address in large type",
        motion="the hero photo scales from 1.05 to 1 over 1.5s on load; nothing else",
        keywords=("steak", "steakhouse", "fine dining", "lounge", "wine", "cocktail", "night", "malam", "grill house", "bistro"),
        image_cue="a seared steak on a dark plate, low warm light, dramatic shadow",
    ),
    _d(
        key="api_malam",
        name="Api Malam",
        feel="bold, smoky",
        audience="night BBQ, ikan bakar at night, satay and grill stalls that asked for a dark page",
        verticals=("food",),
        styles=("bold",),
        theme="dark",
        palette={"bg": "#1F2326", "surface": "#2A2F33", "text": "#F4F1EC", "muted": "#B3B8BC", "accent": "#FF6A2B", "accent_2": "#F5C453"},
        type={"display": "Unbounded", "body": "Source Sans 3", "scale": "1.414 augmented fourth", "display_weight": 700},
        hero_treatment="photo-full-bleed",
        signature_element="an ember texture band (SVG grain, charcoal to flame gradient) behind the menu highlights, with the flame accent on prices only",
        layout_notes="charcoal page, poster-scale display type, menu as a tight 3-up photo grid, story as one wide paragraph in large type, contact strip in flame accent with dark text",
        motion="the hero headline slides up and the ember band fades in once on load; nothing else",
        keywords=("bbq", "bakar", "satay", "grill", "smoke", "asap", "arang", "night market", "pasar malam"),
        image_cue="satay and grilled seafood over glowing charcoal at night",
    ),
    _d(
        key="kopi_malam",
        name="Kopi Malam",
        feel="quiet, warm-dark",
        audience="night cafés, dessert bars, listening bars, late-night kopi",
        verticals=("food", "bakery"),
        styles=("minimal",),
        theme="dark",
        palette={"bg": "#2B211C", "surface": "#352A24", "text": "#F2E9E1", "muted": "#C3B5A9", "accent": "#D9A066", "accent_2": "#7C9A8A"},
        type={"display": "Instrument Serif", "body": "DM Sans", "scale": "1.414 augmented fourth", "display_weight": 400},
        hero_treatment="typographic",
        signature_element="a typographic hero on deep espresso brown — the name at display size and one line beneath, with the single photo arriving only in the second screen; no cards anywhere",
        layout_notes="wide margins, ruled lists for the menu, two-column story text, location as a single large line; the accent appears only on prices and the order link",
        motion="the hero lines fade up one after another on load; nothing else",
        keywords=("kopi", "coffee", "cafe", "kafe", "dessert bar", "malam", "night", "listening bar", "late night"),
        image_cue="a latte and a slice of cake on a dark wooden table, warm lamp light",
    ),
    _d(
        key="pesta_neon",
        name="Pesta Neon",
        feel="electric, playful",
        audience="dessert bars, bubble tea, pasar malam stalls and youth concepts that asked for a dark page",
        verticals=("food", "bakery", "general"),
        styles=("playful", "bold", "doodle"),
        theme="dark",
        palette={"bg": "#1E1240", "surface": "#2A1B57", "text": "#FBF8FF", "muted": "#C9BFE6", "accent": "#C6FF3D", "accent_2": "#FF4FA3"},
        type={"display": "Syne", "body": "Nunito", "scale": "1.414 augmented fourth", "display_weight": 800},
        hero_treatment="pattern",
        signature_element="neon sticker badges (SVG, rotated) carrying the real prices, and a dotted-grid pattern behind the hero in the surface colour",
        layout_notes="deep violet page, dense 2-up menu grid, story as a bold pull-paragraph, contact strip in the lime accent with dark text",
        motion="the sticker badges pop in with a 200ms scale on load; nothing else",
        keywords=("bubble tea", "boba", "dessert", "pasar malam", "neon", "youth", "trend", "viral", "tiktok"),
        image_cue="colourful desserts and drinks on a dark table under neon light",
    ),
    _d(
        key="doodle_malam",
        name="Doodle Malam",
        feel="chalkboard, hand-drawn",
        audience="any shop that asked for the doodle look AND a dark page",
        verticals=("food", "bakery", "general", "clothing"),
        styles=("doodle",),
        theme="dark",
        palette={"bg": "#1E2A26", "surface": "#27352F", "text": "#FBF7EE", "muted": "#C7C1B3", "accent": "#FFD447", "accent_2": "#7FD3C0"},
        type={"display": "Baloo 2", "body": "Source Sans 3", "scale": "1.25 major third", "display_weight": 700},
        hero_treatment="pattern",
        signature_element="chalk-style hand-drawn inline SVG accents (wobbly underlines, squiggle dividers, doodle stars) in chalk yellow on a slate-green chalkboard page — never emoji",
        layout_notes="rounded display face, tiles with a 2px wobbly chalk border and no shadow, story panel shaped like a speech bubble, 40px section spacing",
        motion="the chalk underline under the hero headline draws itself once on load; nothing else",
        keywords=("doodle", "kartun", "cartoon", "chalk", "kapur", "papan hitam"),
        image_cue="flat cartoon illustration of the dishes on a chalkboard, thick outlines",
    ),
    _d(
        key="warisan_malam",
        name="Warisan Malam",
        feel="heritage, dark-warm",
        audience="heritage restaurants and kenduri caterers that asked for a dark page",
        verticals=("food", "general"),
        styles=("classic",),
        theme="dark",
        palette={"bg": "#2C1E16", "surface": "#382920", "text": "#F5EBDD", "muted": "#C9B8A6", "accent": "#C8944B", "accent_2": "#6E8B5B"},
        type={"display": "Playfair Display", "body": "Source Sans 3", "scale": "1.25 major third", "display_weight": 600},
        hero_treatment="photo-split",
        signature_element="framed photographs — each story and menu photo sits inside a thin brass (accent) frame with an inner cream mat, like a family portrait wall",
        layout_notes="deep teak page, serif display, menu as framed photo tiles 3-up, story as framed photo beside two paragraphs, contact strip with a brass rule",
        motion="the hero photo frame fades in and the headline settles on load; nothing else",
        keywords=("warisan", "heritage", "tradisi", "traditional", "kenduri", "lama", "turun temurun"),
        cream_allowed=True,
        image_cue="a heritage Malay feast on brass trays, low warm light",
    ),
    # ------------------------------------------------------------------ Non-F&B bright
    _d(
        key="butik_runway",
        name="Butik Runway",
        feel="editorial, image-led",
        audience="boutiques, baju kurung, hijab, streetwear — the product photos do the work",
        verticals=("clothing",),
        styles=("elegant", "minimal"),
        theme="bright",
        palette={"bg": "#FFFFFF", "surface": "#F4F4F2", "text": "#111111", "muted": "#6E6E6E", "accent": "#111111", "accent_2": "#9C8A6E"},
        type={"display": "Instrument Serif", "body": "Inter", "scale": "1.414 augmented fourth", "display_weight": 400},
        hero_treatment="photo-full-bleed",
        signature_element="a large lookbook grid — the collection as full-height photo tiles with the item name and price set small beneath, in a 2/3 + 1/3 asymmetric rhythm",
        layout_notes="almost no colour: black text, white page, one warm neutral for size notes; wide serif display at one huge size; collection grid, then a plain 'Saiz & Penghantaran' two-column text block, then 'Cara Order' as three numbered lines",
        motion="the hero image fades in over 900ms on load; nothing else",
        keywords=("butik", "boutique", "baju", "kurung", "hijab", "tudung", "fesyen", "fashion", "streetwear", "pakaian", "apparel"),
        image_cue="a model in the garment against a plain studio backdrop, soft daylight",
    ),
    _d(
        key="salon_lembut",
        name="Salon Lembut",
        feel="soft, premium-calm",
        audience="hair salons, beauty, spa and nail studios",
        verticals=("salon",),
        styles=("elegant", "playful"),
        theme="bright",
        palette={"bg": "#FAF7F4", "surface": "#FFFFFF", "text": "#2A2523", "muted": "#6E6562", "accent": "#B8687A", "accent_2": "#8FA88F"},
        type={"display": "Fraunces", "body": "Manrope", "scale": "1.25 major third", "display_weight": 500},
        hero_treatment="photo-split",
        signature_element="a booking button that stays fixed at the bottom of the phone screen (and in the nav on desktop) in the blush accent, plus a services & prices list with dotted leaders",
        layout_notes="pale neutral page, one blush accent and one sage for hover, split hero with the salon photo, 'Servis & Harga' as a ruled price list, 'Tempah' as a calm booking band, 'Galeri kerja' only when work photos exist",
        motion="the hero photo fades in and the booking button rises once on load; nothing else",
        keywords=("salon", "rambut", "hair", "spa", "kecantikan", "beauty", "kuku", "nail", "facial", "makeup", "bridal"),
        image_cue="a bright salon interior with an empty styling chair, soft daylight",
    ),
    _d(
        key="barber_tegas",
        name="Barber Tegas",
        feel="bold, monochrome",
        audience="barbershops and men's grooming",
        verticals=("salon",),
        styles=("bold", "classic"),
        theme="bright",
        palette={"bg": "#FFFFFF", "surface": "#F2F2F2", "text": "#0F0F0F", "muted": "#555555", "accent": "#C8102E", "accent_2": "#0F0F0F"},
        type={"display": "Archivo Black", "body": "Source Sans 3", "scale": "1.414 augmented fourth", "display_weight": 400},
        hero_treatment="menu-first",
        signature_element="the price list IS the hero: cut / shave / kids in condensed display type with the real prices, on white with one red rule",
        layout_notes="black and white plus one red, price list first, then a photo band of the shop, then a booking/WhatsApp strip; no cards at all",
        motion="the price rows slide in from the left one after another on load; nothing else",
        keywords=("barber", "barbershop", "gunting", "rambut lelaki", "grooming", "shave", "fade"),
        image_cue="a barber chair and tools in a clean shop, hard daylight, monochrome feel",
    ),
    _d(
        key="bengkel_yakin",
        name="Bengkel Yakin",
        feel="trustworthy, direct",
        audience="workshops, plumbing, aircond, repair and home services",
        verticals=("services",),
        styles=("bold", "minimal"),
        theme="bright",
        palette={"bg": "#FFFFFF", "surface": "#EEF3FA", "text": "#12233A", "muted": "#4A5A70", "accent": "#0B4F9C", "accent_2": "#F58220"},
        type={"display": "Rubik", "body": "Rubik", "scale": "1.25 major third", "display_weight": 800},
        hero_treatment="typographic",
        signature_element="phone number and WhatsApp button above the fold in the hero, set as large as the headline, with a service checklist (real SVG ticks) beside them",
        layout_notes="high contrast blue/orange, single family at two weights, 'Perkhidmatan' as a checklist grid, 'Kawasan liputan' as a plain list of areas, 'Hubungi' phone-first; testimonials only if supplied",
        motion="the phone button pulses once on load; nothing else",
        keywords=("bengkel", "workshop", "paip", "plumbing", "aircond", "air cond", "elektrik", "repair", "baiki", "servis", "renovation", "kontraktor", "pembersihan", "cleaning"),
        image_cue="a technician's tools laid out on a clean bench, bright daylight",
    ),
    _d(
        key="studio_fokus",
        name="Studio Fokus",
        feel="quiet, portfolio",
        audience="photographers, designers, freelancers and studios",
        verticals=("services", "general"),
        styles=("minimal",),
        theme="bright",
        palette={"bg": "#FCFCFB", "surface": "#F3F3F1", "text": "#161616", "muted": "#6B6B6B", "accent": "#161616", "accent_2": "#B5B5B0"},
        type={"display": "Familjen Grotesk", "body": "Familjen Grotesk", "scale": "1.333 perfect fourth", "display_weight": 600},
        hero_treatment="typographic",
        signature_element="a masonry portfolio grid (CSS columns) of the work photos with almost no UI chrome — no borders, no shadows, no labels beyond a small caption",
        layout_notes="near-white, wide margins (max-width 1200px), a single family, name and one sentence as the hero, portfolio grid, a short services list, one contact line",
        motion="the portfolio tiles fade in on load in reading order; nothing else",
        keywords=("studio", "fotografi", "photography", "photographer", "design", "grafik", "freelance", "videografi", "portfolio"),
        image_cue="a clean studio with a camera on a tripod, soft daylight",
    ),
    _d(
        key="kedai_bandar",
        name="Kedai Bandar",
        feel="clear, price-led",
        audience="retail shops, kedai runcit, phone shops, hardware — anything that sells products",
        verticals=("general", "clothing"),
        styles=("minimal", "classic"),
        theme="bright",
        palette={"bg": "#FFFFFF", "surface": "#F2F7F7", "text": "#132222", "muted": "#4F5F5F", "accent": "#0F7C7C", "accent_2": "#E0A100"},
        type={"display": "Outfit", "body": "Source Sans 3", "scale": "1.25 major third", "display_weight": 700},
        hero_treatment="photo-split",
        signature_element="a product grid with prices set large in the teal accent and a single 'Cara Order' band with three numbered steps",
        layout_notes="white page, one strong colour, product grid 3-up, 'Cara Order' band, contact strip; no decorative cards elsewhere",
        motion="the hero image fades in on load; nothing else",
        keywords=("kedai", "runcit", "shop", "retail", "telefon", "gadget", "hardware", "produk", "product", "borong", "online shop"),
        image_cue="the products arranged on a plain white surface, bright daylight",
    ),
    # ------------------------------------------------------------------ Non-F&B dark
    _d(
        key="runway_malam",
        name="Runway Malam",
        feel="editorial, night",
        audience="boutiques and streetwear labels that asked for a dark page",
        verticals=("clothing",),
        styles=("elegant", "minimal"),
        theme="dark",
        palette={"bg": "#1C1B1B", "surface": "#262424", "text": "#F5F3EF", "muted": "#B8B3AB", "accent": "#F5F3EF", "accent_2": "#B49A6C"},
        type={"display": "Instrument Serif", "body": "DM Sans", "scale": "1.414 augmented fourth", "display_weight": 400},
        hero_treatment="photo-full-bleed",
        signature_element="a lookbook grid of full-height photo tiles on a near-black page, item names set small in white beneath, in an asymmetric 2/3 + 1/3 rhythm",
        layout_notes="no colour beyond one warm neutral; huge serif display; collection grid, 'Saiz & Penghantaran' as two text columns, 'Cara Order' as three numbered lines",
        motion="the hero image fades in over 900ms on load; nothing else",
        keywords=("butik", "boutique", "streetwear", "fesyen", "fashion", "label", "malam"),
        image_cue="a model in the garment against a dark studio backdrop, one soft light",
    ),
    _d(
        key="salon_senja",
        name="Salon Senja",
        feel="plush, evening",
        audience="salons, spas and beauty studios that asked for a dark page",
        verticals=("salon",),
        styles=("elegant", "playful"),
        theme="dark",
        palette={"bg": "#2A1B2E", "surface": "#35243A", "text": "#F7EFF3", "muted": "#CDB9C6", "accent": "#E7A9B4", "accent_2": "#C7A46A"},
        type={"display": "Fraunces", "body": "Manrope", "scale": "1.25 major third", "display_weight": 500},
        hero_treatment="photo-split",
        signature_element="a fixed booking button in the blush accent at the bottom of the phone screen and a services & prices list with dotted leaders in the accent",
        layout_notes="deep plum page, split hero, 'Servis & Harga' ruled list, 'Tempah' booking band, 'Galeri kerja' only when work photos exist",
        motion="the hero photo fades in and the booking button rises once on load; nothing else",
        keywords=("salon", "spa", "beauty", "kecantikan", "makeup", "bridal", "malam", "evening"),
        image_cue="a salon interior at dusk with warm lamp light and an empty chair",
    ),
    _d(
        key="barber_malam",
        name="Barber Malam",
        feel="bold, black",
        audience="barbershops that asked for a dark page",
        verticals=("salon",),
        styles=("bold", "classic"),
        theme="dark",
        palette={"bg": "#151618", "surface": "#1F2124", "text": "#F7F7F7", "muted": "#B5B5B5", "accent": "#E4172F", "accent_2": "#F7F7F7"},
        type={"display": "Archivo Black", "body": "Source Sans 3", "scale": "1.414 augmented fourth", "display_weight": 400},
        hero_treatment="menu-first",
        signature_element="the price list as the hero in condensed white display type on black, one red rule under it",
        layout_notes="black, white and one red; price list first, photo band, booking/WhatsApp strip; no cards",
        motion="the price rows slide in from the left one after another on load; nothing else",
        keywords=("barber", "barbershop", "gunting", "grooming", "fade", "malam"),
        image_cue="a barber chair under a single warm light in a dark shop",
    ),
    _d(
        key="bengkel_malam",
        name="Bengkel Malam",
        feel="direct, navy",
        audience="workshops and home services that asked for a dark page (24-hour and emergency services)",
        verticals=("services",),
        styles=("bold", "minimal"),
        theme="dark",
        palette={"bg": "#0E1F33", "surface": "#162A44", "text": "#F2F6FB", "muted": "#B7C4D6", "accent": "#F58220", "accent_2": "#4DA3FF"},
        type={"display": "Rubik", "body": "Rubik", "scale": "1.25 major third", "display_weight": 800},
        hero_treatment="typographic",
        signature_element="phone number and WhatsApp button above the fold as large as the headline, in orange on navy, with a service checklist beside them",
        layout_notes="single family at two weights, 'Perkhidmatan' checklist grid, 'Kawasan liputan' plain list, 'Hubungi' phone-first; testimonials only if supplied",
        motion="the phone button pulses once on load; nothing else",
        keywords=("bengkel", "24 jam", "emergency", "kecemasan", "towing", "aircond", "plumbing", "elektrik"),
        image_cue="a technician's tools on a bench under workshop lights at night",
    ),
    _d(
        key="studio_malam",
        name="Studio Malam",
        feel="quiet, dark portfolio",
        audience="photographers, designers and studios that asked for a dark page",
        verticals=("services", "general"),
        styles=("minimal",),
        theme="dark",
        palette={"bg": "#161A1D", "surface": "#1F2429", "text": "#F1F2F3", "muted": "#AEB4BA", "accent": "#F1F2F3", "accent_2": "#8C949B"},
        type={"display": "Familjen Grotesk", "body": "Familjen Grotesk", "scale": "1.333 perfect fourth", "display_weight": 600},
        hero_treatment="typographic",
        signature_element="a masonry portfolio grid of the work photos on a near-black page with no chrome beyond a small caption",
        layout_notes="wide margins, a single family, name and one sentence as the hero, portfolio grid, short services list, one contact line",
        motion="the portfolio tiles fade in on load in reading order; nothing else",
        keywords=("studio", "photography", "fotografi", "design", "portfolio", "malam"),
        image_cue="a dark studio with one softbox lit, camera on a tripod",
    ),
)

DIRECTION_BY_KEY: Dict[str, Direction] = {d.key: d for d in DIRECTIONS}


# ============================================================================
# SECTION SETS PER VERTICAL (§3b)
# ============================================================================

#: Section ids the plan must build, per vertical. F&B keeps the Menu; the
#: others never get one. ``optional`` sections exist only when the merchant
#: supplied what they need (gallery photos, testimonials, address).
SECTION_SETS: Dict[str, Dict[str, List[str]]] = {
    "food": {"required": ["hero", "menu", "about", "location", "contact", "footer"], "optional": ["gallery"]},
    "bakery": {"required": ["hero", "menu", "about", "location", "contact", "footer"], "optional": ["gallery"]},
    "clothing": {"required": ["hero", "koleksi", "saiz_penghantaran", "cara_order", "contact", "footer"], "optional": ["gallery"]},
    "salon": {"required": ["hero", "servis_harga", "tempah", "about", "location", "footer"], "optional": ["galeri_kerja"]},
    "services": {"required": ["hero", "perkhidmatan", "kawasan_liputan", "hubungi", "footer"], "optional": ["testimoni", "about"]},
    "general": {"required": ["hero", "produk", "about", "cara_order", "contact", "footer"], "optional": ["gallery"]},
}

SECTION_TITLES: Dict[str, Dict[str, str]] = {
    "hero": {"ms": "Hero", "en": "Hero"},
    "menu": {"ms": "Menu", "en": "Menu"},
    "about": {"ms": "Tentang Kami", "en": "About"},
    "location": {"ms": "Lokasi & Waktu", "en": "Location & Hours"},
    "contact": {"ms": "Hubungi", "en": "Contact"},
    "footer": {"ms": "Footer", "en": "Footer"},
    "gallery": {"ms": "Galeri", "en": "Gallery"},
    "koleksi": {"ms": "Koleksi", "en": "Collection"},
    "saiz_penghantaran": {"ms": "Saiz & Penghantaran", "en": "Sizes & Delivery"},
    "cara_order": {"ms": "Cara Order", "en": "How to Order"},
    "servis_harga": {"ms": "Servis & Harga", "en": "Services & Prices"},
    "tempah": {"ms": "Tempah", "en": "Book"},
    "galeri_kerja": {"ms": "Galeri Kerja", "en": "Our Work"},
    "perkhidmatan": {"ms": "Perkhidmatan", "en": "Services"},
    "kawasan_liputan": {"ms": "Kawasan Liputan", "en": "Areas Served"},
    "hubungi": {"ms": "Hubungi", "en": "Contact"},
    "testimoni": {"ms": "Testimoni", "en": "Testimonials"},
    "produk": {"ms": "Produk", "en": "Products"},
}

FNB_VERTICALS = ("food", "bakery")


def section_set_for(vertical: str) -> Dict[str, List[str]]:
    key = vertical if vertical in SECTION_SETS else "general"
    return {"required": list(SECTION_SETS[key]["required"]), "optional": list(SECTION_SETS[key]["optional"])}


# ============================================================================
# SELECTION
# ============================================================================

def _norm_style(style: Optional[str]) -> Optional[str]:
    if not style:
        return None
    s = str(style).strip().lower()
    return s if s in STYLE_TAGS else None


def _norm_theme(theme: Optional[str]) -> Optional[str]:
    if not theme:
        return None
    t = str(theme).strip().lower()
    if t in ("dark", "gelap"):
        return "dark"
    if t in ("light", "bright", "cerah"):
        return "bright"
    return None


def candidate_directions(
    vertical: str,
    *,
    theme: Optional[str] = "bright",
    style: Optional[str] = None,
    exclude: Iterable[str] = (),
) -> List[Direction]:
    """The directions a plan may choose from, in library order.

    Filters in priority order — theme (merchant's Cerah/Gelap toggle is a
    hard wall), style (the picker), vertical (section set) — and widens the
    vertical filter when it leaves nothing, so a *Doodle Kartun* pick on a
    salon still has a doodle direction to reach for. Theme and style are
    never widened: those are the merchant's explicit choices.
    """
    theme = _norm_theme(theme) or "bright"
    style = _norm_style(style)
    excluded = {e for e in exclude if e}
    vertical = vertical if vertical in VERTICALS else "general"

    def _filter(check_vertical: bool) -> List[Direction]:
        out = []
        for d in DIRECTIONS:
            if d.theme != theme:
                continue
            if style and style not in d.styles:
                continue
            if check_vertical and vertical not in d.verticals:
                continue
            out.append(d)
        return out

    pool = _filter(True) or _filter(False)
    rotated = [d for d in pool if d.key not in excluded]
    # A rolling-history exclusion can only shrink the pool, never empty it:
    # when every candidate was used recently, the least-recent one is fair.
    return rotated or pool


def _keyword_score(direction: Direction, text: str) -> int:
    score = 0
    for kw in direction.keywords:
        if kw in text:
            score += 3 if " " in kw else 2
    return score


def rank_directions(
    candidates: Sequence[Direction],
    *,
    text: str,
    vertical: str,
    seed: str = "",
) -> List[Direction]:
    """Order candidates by fit: keyword hits on the merchant's own words
    first, then vertical match, then a stable per-business tie-break so two
    identical briefs still walk the library instead of always taking the
    first row."""
    lowered = (text or "").lower()
    digest = hashlib.sha1((seed or "").encode("utf-8")).hexdigest()
    tie = int(digest[:8], 16)

    def _key(item: Tuple[int, Direction]):
        idx, d = item
        kw = _keyword_score(d, lowered)
        vert = 1 if vertical in d.verticals else 0
        # Rotate the tie-break start point with the seed.
        rot = (idx + tie) % max(1, len(candidates))
        return (-kw, -vert, rot)

    return [d for _, d in sorted(enumerate(candidates), key=_key)]


def pick_direction(
    vertical: str,
    *,
    text: str,
    theme: Optional[str] = "bright",
    style: Optional[str] = None,
    exclude: Iterable[str] = (),
    seed: str = "",
) -> Direction:
    """Deterministic closest-fit direction (the fallback when the plan model
    is unavailable, and the anchor the model is asked to choose among)."""
    ranked = rank_directions(
        candidate_directions(vertical, theme=theme, style=style, exclude=exclude),
        text=text, vertical=vertical, seed=seed,
    )
    return ranked[0]


def coverage_matrix() -> Dict[Tuple[str, str], List[str]]:
    """style × theme -> direction keys. Used by the tests that guarantee
    every merchant pick has at least two directions to rotate between."""
    out: Dict[Tuple[str, str], List[str]] = {(s, t): [] for s in STYLE_TAGS for t in THEMES}
    for d in DIRECTIONS:
        for s in d.styles:
            out[(s, d.theme)].append(d.key)
    return out


def google_fonts_link(display: str, body: str) -> str:
    """The single Google Fonts <link> for a validated pairing."""
    families = []
    for name in dict.fromkeys([display, body]):
        meta = ALLOWED_FONTS[name]
        families.append(f"family={name.replace(' ', '+')}:wght@{meta['weights']}")
    return (
        '<link rel="preconnect" href="https://fonts.googleapis.com">\n'
        '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
        f'<link href="https://fonts.googleapis.com/css2?{"&".join(families)}&display=swap" rel="stylesheet">'
    )
