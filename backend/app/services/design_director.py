"""
Design Director — the "senior designer" layer of website generation.

Before this module, the generator was a template-filler: the design system
picked the fonts, the palette, the hero HTML and a numbered section list, and
the prompt told the model "MUST FOLLOW". Sites were consistent but the AI had
no room to design, and a merchant who wrote "I want it to feel like a
Tokyo listening bar, dark, one gold accent" got the same seeded look as
everyone else.

This module gives the AI the freedom a senior designer has, without giving
up the deterministic guarantees the rest of the pipeline relies on:

1. **Concept first, code second.** ``build_concept_prompt`` asks the model
   for a written design concept — mood, rationale, palette, Google Fonts
   pairing, hero idea, page plan, signature details, copy voice — as JSON.
2. **Validate, don't trust.** ``parse_concept`` accepts the concept only
   after checking every hex colour, fixing unreadable text/background
   contrast, enforcing the merchant's light/dark choice, and resolving the
   fonts against a curated Google Fonts catalogue (an unknown font would
   silently fail to load; a wrong weight would 400 the whole stylesheet).
3. **Honour the picks.** The validated palette and fonts become the
   ``tailwind.config`` tokens and the Google Fonts ``<link>`` the HTML
   prompt injects, so the Design Studio repaint, the widget theme
   extraction and the QR/promo kits keep working on AI-designed sites.
4. **Merchant brief wins.** A free-text ``design_brief`` from the create
   page is the highest-priority design input: it is passed to the concept
   step as a constraint and repeated in the HTML prompt with an explicit
   precedence rule (facts > brief > concept > house defaults).

Everything here is pure and side-effect free (no network); the AI calls live
in ``ai_service`` so this module stays trivially testable.
"""

import json
import logging
import os
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ============================================================================
# FLAGS / LIMITS
# ============================================================================

#: Hard cap on the merchant's free-text design brief. Long enough for a
#: paragraph of real direction, short enough that it cannot crowd out the
#: business data in the prompt.
DESIGN_BRIEF_MAX_CHARS = 1500

FREEDOM_DESIGNER = "designer"
FREEDOM_GUIDED = "guided"
FREEDOM_MODES = (FREEDOM_DESIGNER, FREEDOM_GUIDED)


def design_freedom_default() -> str:
    """Site-wide default freedom mode, read at call time (env-flippable).

    ``designer`` (default): the AI writes its own concept and the prompt
    treats the house design rules as defaults it may override deliberately.
    ``guided``: the pre-upgrade behaviour — seeded design system, hero
    blueprint, numbered layout, "MUST FOLLOW".
    """
    value = (os.getenv("AI_DESIGN_FREEDOM_DEFAULT", FREEDOM_DESIGNER) or "").strip().lower()
    return value if value in FREEDOM_MODES else FREEDOM_DESIGNER


def resolve_design_freedom(requested: Optional[str], template_id: Optional[str] = None) -> str:
    """Pick the freedom mode for one generation.

    A pre-built / gallery template is an explicit look the merchant chose,
    so it always runs guided — the template's design tokens must win over
    any AI concept. Otherwise an explicit request value wins, then the env
    default.
    """
    if template_id:
        return FREEDOM_GUIDED
    value = (requested or "").strip().lower()
    if value in FREEDOM_MODES:
        return value
    return design_freedom_default()


def design_concept_enabled() -> bool:
    """Whether the concept step runs at all (designer mode only)."""
    raw = os.getenv("AI_DESIGN_CONCEPT_ENABLED", "true").strip().lower()
    return raw in ("1", "true", "yes", "on")


def normalize_design_brief(raw: Optional[str]) -> Optional[str]:
    """Trim, collapse whitespace and cap the merchant's brief.

    Returns None for an empty/whitespace brief so callers can test truthiness.
    """
    if not raw or not isinstance(raw, str):
        return None
    text = re.sub(r"[ \t\r\f\v]+", " ", raw)
    text = re.sub(r" *\n *", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    if not text:
        return None
    return text[:DESIGN_BRIEF_MAX_CHARS].rstrip()


# ============================================================================
# GOOGLE FONTS CATALOGUE
#
# Only fonts in this catalogue may be requested. Two reasons this is a hard
# allowlist rather than "anything the model says":
#   - A font that does not exist on Google Fonts silently falls back to the
#     browser default — the site loads with system-ui and the design collapses.
#   - The css2 API returns HTTP 400 for the WHOLE request when any family is
#     asked for a weight it does not ship, so the weight string per font must
#     be one Google actually serves. Single-weight faces are pinned to 400.
# ============================================================================

_W4 = "400"
_W47 = "400;700"
_W4567 = "400;500;600;700"

GOOGLE_FONTS: Dict[str, Dict[str, str]] = {
    # ---- Sans-serif (variable or full static families) ----
    "Inter": {"category": "sans", "weights": _W4567},
    "Roboto": {"category": "sans", "weights": _W4567},
    "Plus Jakarta Sans": {"category": "sans", "weights": _W4567},
    "DM Sans": {"category": "sans", "weights": _W4567},
    "Manrope": {"category": "sans", "weights": _W4567},
    "Outfit": {"category": "sans", "weights": _W4567},
    "Sora": {"category": "sans", "weights": _W4567},
    "Space Grotesk": {"category": "sans", "weights": _W4567},
    "Poppins": {"category": "sans", "weights": _W4567},
    "Nunito": {"category": "sans", "weights": _W4567},
    "Nunito Sans": {"category": "sans", "weights": _W4567},
    "Mulish": {"category": "sans", "weights": _W4567},
    "Work Sans": {"category": "sans", "weights": _W4567},
    "Figtree": {"category": "sans", "weights": _W4567},
    "Urbanist": {"category": "sans", "weights": _W4567},
    "Lexend": {"category": "sans", "weights": _W4567},
    "Rubik": {"category": "sans", "weights": _W4567},
    "Karla": {"category": "sans", "weights": _W4567},
    "Raleway": {"category": "sans", "weights": _W4567},
    "Montserrat": {"category": "sans", "weights": _W4567},
    "Lato": {"category": "sans", "weights": _W47},
    "Open Sans": {"category": "sans", "weights": _W4567},
    "Source Sans 3": {"category": "sans", "weights": _W4567},
    "IBM Plex Sans": {"category": "sans", "weights": _W4567},
    "Public Sans": {"category": "sans", "weights": _W4567},
    "Red Hat Display": {"category": "sans", "weights": _W4567},
    "Red Hat Text": {"category": "sans", "weights": _W4567},
    "Josefin Sans": {"category": "sans", "weights": _W4567},
    "Quicksand": {"category": "sans", "weights": _W4567},
    "Barlow": {"category": "sans", "weights": _W4567},
    "Barlow Condensed": {"category": "sans", "weights": _W4567},
    "Oswald": {"category": "sans", "weights": _W4567},
    "Archivo": {"category": "sans", "weights": _W4567},
    "Syne": {"category": "sans", "weights": _W4567},
    "Unbounded": {"category": "sans", "weights": _W4567},
    "Epilogue": {"category": "sans", "weights": _W4567},
    "Onest": {"category": "sans", "weights": _W4567},
    "Geist": {"category": "sans", "weights": _W4567},
    "Instrument Sans": {"category": "sans", "weights": _W4567},
    "Bricolage Grotesque": {"category": "sans", "weights": _W4567},
    "Schibsted Grotesk": {"category": "sans", "weights": _W4567},
    "Hanken Grotesk": {"category": "sans", "weights": _W4567},
    "Albert Sans": {"category": "sans", "weights": _W4567},
    "Be Vietnam Pro": {"category": "sans", "weights": _W4567},
    "Cabin": {"category": "sans", "weights": _W4567},
    "Chivo": {"category": "sans", "weights": _W4567},
    "Kanit": {"category": "sans", "weights": _W4567},
    "Prompt": {"category": "sans", "weights": _W4567},
    "Sarabun": {"category": "sans", "weights": _W4567},
    "Jost": {"category": "sans", "weights": _W4567},
    "Exo 2": {"category": "sans", "weights": _W4567},
    "Overpass": {"category": "sans", "weights": _W4567},
    "Questrial": {"category": "sans", "weights": _W4},
    # ---- Serif ----
    "Playfair Display": {"category": "serif", "weights": _W4567},
    "Cormorant Garamond": {"category": "serif", "weights": _W4567},
    "Cormorant": {"category": "serif", "weights": _W4567},
    "DM Serif Display": {"category": "serif", "weights": _W4},
    "DM Serif Text": {"category": "serif", "weights": _W4},
    "Lora": {"category": "serif", "weights": _W4567},
    "Merriweather": {"category": "serif", "weights": _W47},
    "Libre Baskerville": {"category": "serif", "weights": _W47},
    "EB Garamond": {"category": "serif", "weights": _W4567},
    "Crimson Pro": {"category": "serif", "weights": _W4567},
    "Crimson Text": {"category": "serif", "weights": "400;600;700"},
    "Spectral": {"category": "serif", "weights": _W4567},
    "Newsreader": {"category": "serif", "weights": _W4567},
    "Fraunces": {"category": "serif", "weights": _W4567},
    "Literata": {"category": "serif", "weights": _W4567},
    "Source Serif 4": {"category": "serif", "weights": _W4567},
    "Bodoni Moda": {"category": "serif", "weights": _W4567},
    "Cinzel": {"category": "serif", "weights": _W4567},
    "Cardo": {"category": "serif", "weights": _W47},
    "Noto Serif": {"category": "serif", "weights": _W4567},
    "PT Serif": {"category": "serif", "weights": _W47},
    "Libre Caslon Text": {"category": "serif", "weights": _W47},
    "Zilla Slab": {"category": "serif", "weights": _W4567},
    "Roboto Slab": {"category": "serif", "weights": _W4567},
    "Arvo": {"category": "serif", "weights": _W47},
    "Bitter": {"category": "serif", "weights": _W4567},
    "Domine": {"category": "serif", "weights": _W4567},
    "Alegreya": {"category": "serif", "weights": _W4567},
    "Vollkorn": {"category": "serif", "weights": _W4567},
    "Abril Fatface": {"category": "serif", "weights": _W4},
    "Yeseva One": {"category": "serif", "weights": _W4},
    "Rozha One": {"category": "serif", "weights": _W4},
    "Prata": {"category": "serif", "weights": _W4},
    "Italiana": {"category": "serif", "weights": _W4},
    "Marcellus": {"category": "serif", "weights": _W4},
    "Gloock": {"category": "serif", "weights": _W4},
    "Young Serif": {"category": "serif", "weights": _W4},
    "Instrument Serif": {"category": "serif", "weights": _W4},
    # ---- Display ----
    "Bebas Neue": {"category": "display", "weights": _W4},
    "Anton": {"category": "display", "weights": _W4},
    "Archivo Black": {"category": "display", "weights": _W4},
    "Righteous": {"category": "display", "weights": _W4},
    "Fredoka": {"category": "display", "weights": _W4567},
    "Baloo 2": {"category": "display", "weights": _W4567},
    "Chewy": {"category": "display", "weights": _W4},
    "Bangers": {"category": "display", "weights": _W4},
    "Luckiest Guy": {"category": "display", "weights": _W4},
    "Lilita One": {"category": "display", "weights": _W4},
    "Titan One": {"category": "display", "weights": _W4},
    "Bungee": {"category": "display", "weights": _W4},
    "Rubik Mono One": {"category": "display", "weights": _W4},
    "Monoton": {"category": "display", "weights": _W4},
    "Alfa Slab One": {"category": "display", "weights": _W4},
    "Ultra": {"category": "display", "weights": _W4},
    "Lobster": {"category": "display", "weights": _W4},
    "Pacifico": {"category": "display", "weights": _W4},
    # ---- Handwriting ----
    "Caveat": {"category": "handwriting", "weights": _W4567},
    "Kalam": {"category": "handwriting", "weights": _W47},
    "Patrick Hand": {"category": "handwriting", "weights": _W4},
    "Gloria Hallelujah": {"category": "handwriting", "weights": _W4},
    "Comic Neue": {"category": "handwriting", "weights": _W47},
    "Permanent Marker": {"category": "handwriting", "weights": _W4},
    "Shadows Into Light": {"category": "handwriting", "weights": _W4},
    "Dancing Script": {"category": "handwriting", "weights": _W4567},
    "Great Vibes": {"category": "handwriting", "weights": _W4},
    "Satisfy": {"category": "handwriting", "weights": _W4},
    "Amatic SC": {"category": "handwriting", "weights": _W47},
    "Indie Flower": {"category": "handwriting", "weights": _W4},
    "Architects Daughter": {"category": "handwriting", "weights": _W4},
    "Sacramento": {"category": "handwriting", "weights": _W4},
    "Parisienne": {"category": "handwriting", "weights": _W4},
}

#: Fallback stacks per category — what the browser shows while (or if) the
#: webfont never arrives.
FONT_FALLBACKS = {
    "sans": "system-ui, -apple-system, 'Segoe UI', sans-serif",
    "serif": "Georgia, 'Times New Roman', serif",
    "display": "Impact, 'Arial Black', sans-serif",
    "handwriting": "'Comic Sans MS', cursive",
}

#: Lower-cased lookup so "playfair display" / "PLAYFAIR DISPLAY" resolve.
_FONT_LOOKUP = {name.lower(): name for name in GOOGLE_FONTS}


def resolve_font(name: Optional[str]) -> Optional[str]:
    """Map a model-supplied font name onto the catalogue's canonical name.

    Tolerates case, surrounding quotes, "+" URL encoding and a trailing
    generic family ("Lora, serif"). Returns None when the font is unknown.
    """
    if not name or not isinstance(name, str):
        return None
    cleaned = name.strip().strip("'\"").replace("+", " ")
    cleaned = cleaned.split(",")[0].strip().strip("'\"")
    cleaned = re.sub(r"\s+", " ", cleaned)
    return _FONT_LOOKUP.get(cleaned.lower())


def font_catalogue_by_category() -> Dict[str, List[str]]:
    out: Dict[str, List[str]] = {}
    for name, meta in GOOGLE_FONTS.items():
        out.setdefault(meta["category"], []).append(name)
    return out


def font_pairing_from_names(heading: str, body: str) -> Dict[str, str]:
    """Build a design_system-shaped font pairing from two catalogue names."""
    h = GOOGLE_FONTS[heading]
    b = GOOGLE_FONTS[body]
    return {
        "heading": heading,
        "heading_weights": h["weights"],
        "heading_fallback": FONT_FALLBACKS[h["category"]],
        "heading_category": h["category"],
        "body": body,
        "body_weights": b["weights"],
        "body_fallback": FONT_FALLBACKS[b["category"]],
        "body_category": b["category"],
        "vibe": "AI concept",
    }


# ============================================================================
# COLOUR UTILITIES
# ============================================================================

_HEX6_RE = re.compile(r"^#?([0-9a-fA-F]{6})$")
_HEX3_RE = re.compile(r"^#?([0-9a-fA-F]{3})$")


def normalize_hex(value: Any) -> Optional[str]:
    """Return an upper-case ``#RRGGBB`` or None when the value is not a hex colour."""
    if not isinstance(value, str):
        return None
    v = value.strip()
    m = _HEX6_RE.match(v)
    if m:
        return "#" + m.group(1).upper()
    m = _HEX3_RE.match(v)
    if m:
        return "#" + "".join(ch * 2 for ch in m.group(1)).upper()
    return None


def _channel(c: int) -> float:
    s = c / 255.0
    return s / 12.92 if s <= 0.03928 else ((s + 0.055) / 1.055) ** 2.4


def relative_luminance(hex_color: str) -> float:
    """WCAG relative luminance (0 = black, 1 = white)."""
    h = normalize_hex(hex_color)
    if not h:
        return 0.0
    r, g, b = int(h[1:3], 16), int(h[3:5], 16), int(h[5:7], 16)
    return 0.2126 * _channel(r) + 0.7152 * _channel(g) + 0.0722 * _channel(b)


def contrast_ratio(a: str, b: str) -> float:
    """WCAG contrast ratio between two hex colours (1.0 – 21.0)."""
    la, lb = relative_luminance(a), relative_luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def is_dark(hex_color: str) -> bool:
    return relative_luminance(hex_color) < 0.35


def is_light(hex_color: str) -> bool:
    return relative_luminance(hex_color) > 0.6


#: Minimum text/background contrast we ship. 4.5 is WCAG AA for body text;
#: muted text gets the large-text threshold because it is decorative meta.
MIN_TEXT_CONTRAST = 4.5
MIN_MUTED_CONTRAST = 3.0

PALETTE_KEYS = ("primary", "secondary", "accent", "background", "surface", "text", "text_muted")


# ============================================================================
# CONCEPT MODEL
# ============================================================================

#: Content that must exist on every generated site, whatever the concept.
#: Ids are matched loosely against the model's own section ids/titles.
REQUIRED_SECTIONS: Tuple[Tuple[str, Tuple[str, ...]], ...] = (
    ("hero", ("hero", "header", "intro", "landing", "utama")),
    ("offerings", ("menu", "product", "produk", "service", "perkhidmatan", "offer", "catalog", "katalog",
                   "collection", "koleksi", "packages", "pakej", "treatment", "rawatan", "class", "program",
                   "shop", "kedai", "highlight", "signature", "pricing", "harga")),
    ("about", ("about", "tentang", "story", "kisah", "cerita", "who", "kami", "team", "pasukan", "why", "kenapa")),
    ("contact", ("contact", "hubungi", "location", "lokasi", "visit", "kunjung", "order", "pesan", "tempah",
                 "booking", "cta", "whatsapp", "find", "map", "hours", "waktu")),
    ("footer", ("footer", "kaki")),
)

MAX_SECTIONS = 10
MAX_SIGNATURE_DETAILS = 6
_SHORT = 160
_LONG = 400


def _clip(value: Any, n: int) -> str:
    if value is None:
        return ""
    text = re.sub(r"\s+", " ", str(value)).strip()
    return text[:n]


def _slug(value: Any) -> str:
    text = re.sub(r"[^a-z0-9]+", "-", str(value or "").lower()).strip("-")
    return text[:40] or "section"


@dataclass
class ConceptBrief:
    """Everything the concept step needs to know about one generation."""

    business_name: str
    description: str
    business_type: str = "general"
    language: str = "ms"
    color_mode: str = "light"
    design_brief: Optional[str] = None
    style_hint: Optional[str] = None
    color_hint: Optional[str] = None
    brand_colors: Optional[Dict[str, str]] = None
    has_images: bool = True
    image_count: int = 0
    menu_item_count: int = 0
    include_ecommerce: bool = False


@dataclass
class ConceptSection:
    id: str
    title: str
    layout: str = ""
    purpose: str = ""

    def as_dict(self) -> Dict[str, str]:
        return {"id": self.id, "title": self.title, "layout": self.layout, "purpose": self.purpose}


@dataclass
class DesignConcept:
    """A validated design concept — safe to inject into the HTML prompt."""

    name: str
    mood: List[str]
    rationale: str
    palette: Dict[str, str]
    fonts: Dict[str, str]  # design_system pairing shape (heading, body, weights, fallbacks)
    typography_note: str
    hero_pattern: str
    hero_description: str
    sections: List[ConceptSection]
    signature_details: List[str]
    copy_voice: str
    motion: str
    source: str = "ai"  # "ai" | "fallback"
    adjustments: List[str] = field(default_factory=list)

    # ---- serialisation -------------------------------------------------
    def as_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "mood": list(self.mood),
            "rationale": self.rationale,
            "palette": dict(self.palette),
            "fonts": {"heading": self.fonts.get("heading"), "body": self.fonts.get("body")},
            "typography_note": self.typography_note,
            "hero": {"pattern": self.hero_pattern, "description": self.hero_description},
            "sections": [s.as_dict() for s in self.sections],
            "signature_details": list(self.signature_details),
            "copy_voice": self.copy_voice,
            "motion": self.motion,
            "source": self.source,
            "adjustments": list(self.adjustments),
        }

    # ---- prompt rendering ------------------------------------------------
    def to_prompt_block(self, fonts: Optional[Dict[str, str]] = None) -> str:
        """The concept as the model will read it back in the HTML prompt.

        ``fonts`` overrides the pairing named in the block — used when the
        page's HEAD deliberately keeps a different pairing (the doodle look),
        so the concept never names a font that is not actually loaded.
        """
        fonts = fonts or self.fonts
        mood = " · ".join(self.mood) if self.mood else "—"
        palette_line = ", ".join(f"{k} {self.palette[k]}" for k in PALETTE_KEYS if self.palette.get(k))
        lines = [
            f'===== DESIGN CONCEPT — "{self.name}" (YOUR OWN CONCEPT — EXECUTE IT FAITHFULLY) =====',
            f"Mood: {mood}",
        ]
        if self.rationale:
            lines.append(f"Why this fits the business: {self.rationale}")
        lines.append(
            f"Palette (already wired into tailwind.config + CSS variables — use the tokens): {palette_line}"
        )
        fonts_line = (
            f"Typography: headings in '{fonts.get('heading')}' "
            f"({fonts.get('heading_category', 'sans')}), body in '{fonts.get('body')}' "
            f"({fonts.get('body_category', 'sans')}) — both already loaded in the HEAD."
        )
        if self.typography_note:
            fonts_line += f" {self.typography_note}"
        lines.append(fonts_line)
        hero = f"Hero: {self.hero_pattern.upper()}" if self.hero_pattern else "Hero:"
        if self.hero_description:
            hero += f" — {self.hero_description}"
        lines.append(hero)
        lines.append("Page plan (in this order — hero first, footer last):")
        for i, s in enumerate(self.sections, 1):
            row = f"  {i}. {s.title}"
            if s.layout:
                row += f" — {s.layout}"
            if s.purpose:
                row += f" ({s.purpose})"
            lines.append(row)
        if self.signature_details:
            lines.append("Signature details (the touches that make this site feel designed, not templated):")
            lines.extend(f"  - {d}" for d in self.signature_details)
        if self.copy_voice:
            lines.append(f"Copy voice: {self.copy_voice}")
        if self.motion:
            lines.append(f"Motion: {self.motion}")
        return "\n".join(lines)

    def section_checklist(self) -> str:
        """Compact numbered plan for the LAYOUT part of the prompt."""
        rows = []
        for i, s in enumerate(self.sections, 1):
            row = f"{i}. {s.title.upper()}"
            if s.layout:
                row += f": {s.layout}"
            rows.append(row)
        return "\n".join(rows)


# ============================================================================
# CONCEPT PROMPT
# ============================================================================

_CONCEPT_JSON_SHAPE = """{
  "concept_name": "short evocative name for the design direction",
  "mood": ["three", "mood", "words"],
  "rationale": "1-2 sentences: why THIS direction fits THIS business and its customers",
  "palette": {
    "primary": "#RRGGBB", "secondary": "#RRGGBB", "accent": "#RRGGBB",
    "background": "#RRGGBB", "surface": "#RRGGBB", "text": "#RRGGBB", "text_muted": "#RRGGBB"
  },
  "fonts": {"heading": "Google Font name from the list", "body": "Google Font name from the list"},
  "typography_note": "how the type should behave (scale, weight, italics, letterspacing, any display moment)",
  "hero": {"pattern": "one of: full-bleed | split | editorial-stack | typographic | asymmetric-collage | centered-minimal | bento | poster", "description": "what the visitor sees first and why"},
  "sections": [
    {"id": "hero", "title": "Hero", "layout": "how it is laid out", "purpose": "what it must achieve"},
    {"id": "...", "title": "...", "layout": "...", "purpose": "..."}
  ],
  "signature_details": ["3-6 concrete design moves unique to this site"],
  "copy_voice": "the tone of the writing, in one line",
  "motion": "how things move (scroll reveals, hover, any one hero moment) — restrained"
}"""


def build_concept_prompt(brief: ConceptBrief) -> str:
    """Prompt for the concept step: a senior designer writing the brief-to-concept."""
    fonts_by_cat = font_catalogue_by_category()
    font_lines = "\n".join(
        f"- {cat.upper()}: {', '.join(names)}" for cat, names in fonts_by_cat.items()
    )

    constraints: List[str] = []
    constraints.append(
        f"- Colour mode: {brief.color_mode.upper()} — "
        + ("a light page (light background, dark text)." if brief.color_mode != "dark"
           else "a dark page (dark background, light text).")
    )
    if brief.brand_colors:
        pairs = ", ".join(f"{k} {v}" for k, v in brief.brand_colors.items())
        constraints.append(f"- Merchant brand colours (use them as the core of the palette): {pairs}")
    elif brief.color_hint:
        constraints.append(f"- The merchant asked for a {brief.color_hint.upper()} colour theme — build the palette around it.")
    if brief.style_hint:
        constraints.append(f"- The merchant picked the {brief.style_hint.upper()} style — the concept must read unmistakably as that.")
    constraints.append(
        f"- Site language: {'Bahasa Malaysia' if brief.language == 'ms' else 'English'} (concept text can be English)."
    )
    if brief.has_images:
        n = brief.image_count or "several"
        constraints.append(f"- Photography: {n} real photo(s) will be available (hero + items). Design around photos.")
    else:
        constraints.append("- Photography: NONE. This must be a typography-and-colour led design that looks complete with zero photos.")
    if brief.menu_item_count:
        constraints.append(
            f"- The offerings section must present {brief.menu_item_count} real item(s) with names/prices — plan a layout that scales to that count."
        )
    if brief.include_ecommerce:
        constraints.append("- An ordering/checkout widget is injected later; leave the offerings cards clean (no order buttons on cards).")

    design_brief_block = ""
    if brief.design_brief:
        design_brief_block = (
            "MERCHANT'S DESIGN BRIEF (HIGHEST PRIORITY — the concept must visibly deliver this):\n"
            f"\"\"\"{brief.design_brief}\"\"\"\n\n"
        )

    return f"""You are the senior designer at a boutique web studio in Kuala Lumpur. A merchant has hired you to design their website. Before any code is written, write the DESIGN CONCEPT — the way you would present it to a client: a clear direction, specific choices, and the reasons behind them.

Design for THIS business and THIS merchant. Study the description: who the customers are, what the place feels like, what they sell, what should be the first thing a visitor sees. Do not reach for a generic "modern website" — a nasi kandar stall, a bridal boutique, a car workshop and a kids' tuition centre should each get a visibly different concept. Be opinionated. Choose one strong idea and commit to it.

BUSINESS: {brief.business_name}
TYPE: {brief.business_type}
DESCRIPTION:
\"\"\"{brief.description}\"\"\"

{design_brief_block}CONSTRAINTS ALREADY DECIDED (honour every one):
{chr(10).join(constraints)}

FONTS — choose ONLY from this Google Fonts catalogue (exact names). Pair with intent: contrast a serif/display heading with a clean body, or go single-family when restraint is the point. Avoid Inter/Roboto/Open Sans unless the brief asks for a plain corporate look.
{font_lines}

PALETTE RULES:
- 6-digit hex only. background/surface/text/text_muted must respect the colour mode above.
- text must be clearly readable on background (aim for contrast 7:1+; never below 4.5:1). text_muted at least 3:1.
- ONE dominant colour (primary) + ONE accent. secondary is a darker/lighter relative of primary for hover states and bands.
- Palettes that feel chosen, not default: no generic SaaS blue-on-white unless the business is actually corporate.

PAGE PLAN RULES:
- 5 to 9 sections. Hero first, footer last.
- Must include: an offerings section (menu / products / services), an about/story section, a contact/order section.
- Vary the structure — not every section is "centered heading + grid of three cards". Use splits, bands, editorial stacks, full-bleed moments, lists, bento grids where they serve the content.
- Describe layouts concretely enough that a front-end developer could build them.

This concept is about DESIGN ONLY. Do not invent business facts (no years, awards, ratings, founder names, prices) — those come from the merchant's data later.

Return ONLY a JSON object, no markdown fences, no commentary, in exactly this shape:
{_CONCEPT_JSON_SHAPE}"""


# ============================================================================
# CONCEPT PARSING + VALIDATION
# ============================================================================

def _extract_json_object(raw: str) -> Optional[Dict[str, Any]]:
    """Find the outermost JSON object in a model reply (fence-tolerant)."""
    if not raw or not isinstance(raw, str):
        return None
    text = raw.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text)
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    candidate = text[start:end + 1]
    try:
        data = json.loads(candidate)
    except json.JSONDecodeError:
        # Common model slip: trailing commas.
        cleaned = re.sub(r",\s*([}\]])", r"\1", candidate)
        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError:
            return None
    return data if isinstance(data, dict) else None


def _validate_palette(
    raw: Any,
    fallback: Dict[str, str],
    color_mode: str,
    adjustments: List[str],
    brand_colors: Optional[Dict[str, str]] = None,
) -> Dict[str, str]:
    """Return a complete, readable palette. Every problem is repaired from
    the fallback palette and recorded in ``adjustments`` for the logs."""
    raw = raw if isinstance(raw, dict) else {}
    palette: Dict[str, str] = {}
    for key in PALETTE_KEYS:
        value = normalize_hex(raw.get(key))
        if value is None:
            value = normalize_hex(fallback.get(key)) or ("#111827" if key in ("text",) else "#FFFFFF")
            if key in raw:
                adjustments.append(f"palette.{key}: invalid hex replaced")
        palette[key] = value

    # Merchant brand colours are the strongest override of all — they beat
    # even the AI's own concept.
    if brand_colors:
        for key in ("primary", "secondary", "accent"):
            value = normalize_hex(brand_colors.get(key)) if isinstance(brand_colors, dict) else None
            if value and palette.get(key) != value:
                palette[key] = value
                adjustments.append(f"palette.{key}: merchant brand colour applied")

    # The merchant chose light or dark explicitly on the create page; an AI
    # concept that flips it is overruled, not honoured.
    wants_dark = color_mode == "dark"
    bg_ok = is_dark(palette["background"]) if wants_dark else is_light(palette["background"])
    if not bg_ok:
        for key in ("background", "surface", "text", "text_muted"):
            fb = normalize_hex(fallback.get(key))
            if fb:
                palette[key] = fb
        adjustments.append(f"palette: background did not match {color_mode} mode — neutrals reset")

    # Surface must sit on the same side of the mode as the background.
    surface_ok = is_dark(palette["surface"]) if wants_dark else not is_dark(palette["surface"])
    if not surface_ok:
        palette["surface"] = normalize_hex(fallback.get("surface")) or palette["background"]
        adjustments.append("palette.surface: did not match colour mode — reset")

    # Readability: text on background, muted text on background.
    if contrast_ratio(palette["text"], palette["background"]) < MIN_TEXT_CONTRAST:
        palette["text"] = "#F5F5F7" if wants_dark else "#111827"
        adjustments.append("palette.text: contrast below 4.5:1 — replaced with a readable neutral")
    if contrast_ratio(palette["text_muted"], palette["background"]) < MIN_MUTED_CONTRAST:
        palette["text_muted"] = "#B4B4C0" if wants_dark else "#4B5563"
        adjustments.append("palette.text_muted: contrast below 3:1 — replaced")

    # Primary must be visible against the page (buttons, headings in brand colour).
    if contrast_ratio(palette["primary"], palette["background"]) < 2.0:
        fb = normalize_hex(fallback.get("primary"))
        if fb and contrast_ratio(fb, palette["background"]) >= 2.0:
            palette["primary"] = fb
        else:
            palette["primary"] = "#E5E7EB" if wants_dark else "#1F2937"
        adjustments.append("palette.primary: invisible against background — replaced")

    palette["border"] = "rgba(255,255,255,0.1)" if wants_dark else "rgba(17,24,39,0.08)"
    return palette


def _validate_fonts(raw: Any, fallback: Dict[str, str], adjustments: List[str]) -> Dict[str, str]:
    raw = raw if isinstance(raw, dict) else {}
    heading = resolve_font(raw.get("heading"))
    body = resolve_font(raw.get("body"))
    fb_heading = resolve_font(fallback.get("heading")) or "Plus Jakarta Sans"
    fb_body = resolve_font(fallback.get("body")) or "Mulish"
    if heading is None:
        adjustments.append(f"fonts.heading: '{raw.get('heading')}' not in catalogue — using {fb_heading}")
        heading = fb_heading
    if body is None:
        adjustments.append(f"fonts.body: '{raw.get('body')}' not in catalogue — using {fb_body}")
        body = fb_body
    # A display/handwriting face is a headline instrument, not body text —
    # paragraphs set in Bangers or Pacifico are unreadable.
    if GOOGLE_FONTS[body]["category"] in ("display",):
        adjustments.append(f"fonts.body: display face '{body}' not readable for body copy — using {fb_body}")
        body = fb_body if GOOGLE_FONTS[fb_body]["category"] not in ("display",) else "Manrope"
    return font_pairing_from_names(heading, body)


def _matches_required(section_id: str, title: str, keywords: Tuple[str, ...]) -> bool:
    hay = f"{section_id} {title}".lower()
    return any(k in hay for k in keywords)


def _validate_sections(raw: Any, language: str, adjustments: List[str]) -> List[ConceptSection]:
    sections: List[ConceptSection] = []
    seen_ids: set = set()
    if isinstance(raw, list):
        for item in raw:
            if isinstance(item, str):
                item = {"id": item, "title": item}
            if not isinstance(item, dict):
                continue
            title = _clip(item.get("title") or item.get("name") or item.get("id"), 60)
            if not title:
                continue
            sid = _slug(item.get("id") or title)
            if sid in seen_ids:
                sid = f"{sid}-{len(sections) + 1}"
            seen_ids.add(sid)
            sections.append(ConceptSection(
                id=sid,
                title=title,
                layout=_clip(item.get("layout"), _LONG),
                purpose=_clip(item.get("purpose"), _SHORT),
            ))
            if len(sections) >= MAX_SECTIONS:
                adjustments.append(f"sections: trimmed to {MAX_SECTIONS}")
                break

    ms = language == "ms"
    defaults = {
        "hero": ConceptSection("hero", "Hero", "Full-width opening statement with the business name and primary CTA", "First impression"),
        "offerings": ConceptSection("offerings", "Menu" if ms else "Offerings", "Cards or list of the real items with names and prices", "Show what is sold"),
        "about": ConceptSection("about", "Tentang Kami" if ms else "About", "Split story section", "Build trust"),
        "contact": ConceptSection("contact", "Hubungi Kami" if ms else "Contact", "Contact details, hours and the order CTA", "Convert"),
        "footer": ConceptSection("footer", "Footer", "Business name, links, copyright", "Close"),
    }

    # Ensure every required content block exists; insert missing ones in a
    # sensible position (hero at the top, footer at the bottom, the rest
    # before contact/footer).
    for req_id, keywords in REQUIRED_SECTIONS:
        if any(_matches_required(s.id, s.title, keywords) for s in sections):
            continue
        adjustments.append(f"sections: added missing '{req_id}'")
        block = defaults[req_id]
        if req_id == "hero":
            sections.insert(0, block)
        elif req_id == "footer":
            sections.append(block)
        else:
            insert_at = len(sections)
            for i, s in enumerate(sections):
                if _matches_required(s.id, s.title, REQUIRED_SECTIONS[4][1]) or (
                    req_id != "contact" and _matches_required(s.id, s.title, REQUIRED_SECTIONS[3][1])
                ):
                    insert_at = i
                    break
            sections.insert(insert_at, block)

    # Hero first, footer last — non-negotiable page anatomy.
    hero_idx = next((i for i, s in enumerate(sections) if _matches_required(s.id, s.title, REQUIRED_SECTIONS[0][1])), 0)
    if hero_idx != 0:
        sections.insert(0, sections.pop(hero_idx))
        adjustments.append("sections: hero moved to the top")
    footer_idx = next((i for i, s in enumerate(sections) if _matches_required(s.id, s.title, REQUIRED_SECTIONS[4][1])), len(sections) - 1)
    if footer_idx != len(sections) - 1:
        sections.append(sections.pop(footer_idx))
        adjustments.append("sections: footer moved to the bottom")
    return sections[:MAX_SECTIONS + 2]


def _string_list(raw: Any, n: int, each: int) -> List[str]:
    if isinstance(raw, str):
        raw = [raw]
    if not isinstance(raw, list):
        return []
    out = []
    for item in raw:
        text = _clip(item, each)
        if text:
            out.append(text)
        if len(out) >= n:
            break
    return out


def parse_concept(
    raw: Optional[str],
    brief: ConceptBrief,
    fallback_fonts: Dict[str, str],
    fallback_palette: Dict[str, str],
) -> Optional[DesignConcept]:
    """Turn the concept model's reply into a validated DesignConcept.

    Returns None when the reply carries no usable JSON — the caller then
    proceeds without a concept (seeded design system), never with a broken
    one. Partial concepts are completed from the fallbacks.
    """
    data = _extract_json_object(raw or "")
    if data is None:
        return None

    adjustments: List[str] = []
    palette = _validate_palette(
        data.get("palette"), fallback_palette, brief.color_mode, adjustments,
        brand_colors=brief.brand_colors,
    )
    fonts = _validate_fonts(data.get("fonts"), fallback_fonts, adjustments)
    sections = _validate_sections(data.get("sections"), brief.language, adjustments)

    hero = data.get("hero") if isinstance(data.get("hero"), dict) else {}
    hero_pattern = _clip(hero.get("pattern"), 40).lower()
    hero_description = _clip(hero.get("description"), _LONG)

    name = _clip(data.get("concept_name") or data.get("name"), 60) or "Studio concept"
    concept = DesignConcept(
        name=name,
        mood=_string_list(data.get("mood"), 5, 24),
        rationale=_clip(data.get("rationale"), _LONG),
        palette=palette,
        fonts=fonts,
        typography_note=_clip(data.get("typography_note"), _LONG),
        hero_pattern=hero_pattern,
        hero_description=hero_description,
        sections=sections,
        signature_details=_string_list(data.get("signature_details"), MAX_SIGNATURE_DETAILS, _SHORT),
        copy_voice=_clip(data.get("copy_voice"), _SHORT),
        motion=_clip(data.get("motion"), _SHORT),
        source="ai",
        adjustments=adjustments,
    )
    if adjustments:
        logger.info("🎨 Concept adjusted during validation: %s", "; ".join(adjustments))
    return concept


# ============================================================================
# PROMPT FRAGMENTS SHARED BY THE HTML GENERATORS
# ============================================================================

def design_brief_block(design_brief: Optional[str]) -> str:
    """The merchant's brief as a top-priority prompt section (or '')."""
    brief = normalize_design_brief(design_brief)
    if not brief:
        return ""
    return f"""===== MERCHANT'S DESIGN BRIEF (HIGHEST DESIGN PRIORITY) =====
The merchant wrote this about how they want the site to LOOK and FEEL:
\"\"\"{brief}\"\"\"

- Deliver it visibly. If they asked for dark and moody, the page is dark and moody; if they asked for a specific colour, section, vibe, layout or reference style, it is there and obvious on first scroll.
- The brief overrides every stylistic default in this prompt (type scale, spacing, colour restraint, hero pattern, section order, card styling).
- The brief NEVER overrides a NON-NEGOTIABLE rule (real data only, exact URLs, WhatsApp number, mobile layout, free icons, language)."""


PRECEDENCE_BLOCK = """===== PRECEDENCE (when instructions conflict) =====
1. NON-NEGOTIABLE rules: real business data only, exact image URLs, WhatsApp/phone rules, language, mobile responsiveness, free Font Awesome icons, fonts loaded in the HEAD.
2. The merchant's explicit picks: design brief, colour theme, light/dark mode, chosen style.
3. Your design concept.
4. The studio's house defaults (type scale, spacing system, card patterns, animation defaults) — strong starting points you may deliberately depart from when 2 or 3 call for it."""


DESIGNER_ROLE_BLOCK = """You are the senior designer at a boutique web studio, building this site for a paying Malaysian merchant. You have full creative ownership of the visual design — layout, composition, typography, colour usage, rhythm, details — the way a senior designer would on a real client project. Two things you never touch: the merchant's FACTS (nothing invented, nothing embellished) and the TECHNICAL contract below (exact URLs, links, mobile, free icons). Everything else is yours to design, and it should look designed for this business alone."""
