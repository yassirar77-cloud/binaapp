"""
Design plan — Pass 1 of two-pass generation.

Before any HTML is written, a small model call turns the merchant's brief
into a *design plan*: one direction from the library (or a custom one when
the merchant chose "Designer bebas"), a six-token palette, a type pairing, a
hero treatment, ONE signature element, layout notes, ONE motion moment and a
list of default "tells" the plan deliberately avoids. Pass 2 (the HTML call)
receives the validated plan as a binding spec it may not change.

Everything the create page collects is mapped in here (``PlanBrief``) and
every explicit merchant choice is a hard constraint that beats the library:

* Cerah/Gelap → only bright/dark directions are eligible (the default is
  bright, and only applies when the merchant did not touch the toggle).
* Gaya design → only directions tagged with that style.
* "Arahan untuk designer AI" → highest priority; the plan must quote which
  sentences it honoured, and when the brief contradicts a toggle ("guna
  tema gelap" with theme = Cerah) the brief wins and the plan says so.
* Designer bebas → a custom direction outside the library is allowed;
  Ikut sistem → library only.
* Jenis kedai → the section set and the direction subset.
* Hero video on → hero treatment is forced to photo-full-bleed.
* Feature toggles OFF → those sections do not exist. No WhatsApp number →
  no WhatsApp CTAs anywhere.

Validation is deterministic and repairs rather than rejects: palette
contrast (text ≥ 4.5:1, accent ≥ 3:1 on the page background), fonts on the
curated allowlist with a valid pairing, hero treatment in the enum, and the
direction different from the last three sites generated in the same
category. When the model is unavailable the fallback plan is built from the
library with the same rules, so Pass 2 always has a spec.

Pure module: no network, no I/O. The model calls live in ``ai_service``.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from app.services import design_directions as dd
from app.services.design_director import (
    ConceptSection,
    DesignConcept,
    FONT_FALLBACKS,
    GOOGLE_FONTS,
    contrast_ratio,
    is_dark,
    is_light,
    normalize_hex,
)
from app.services.site_strings import strings_for

logger = logging.getLogger(__name__)

PLAN_VERSION = 1
MIN_TEXT_CONTRAST = 4.5
MIN_ACCENT_CONTRAST = 3.0
MIN_MUTED_CONTRAST = 3.0
DIRECTION_HISTORY_WINDOW = 3
#: Below this completeness the plan step asks follow-up questions instead
#: of inventing (§0, "AI listening").
LISTENING_THRESHOLD_PCT = 40
MAX_FEATURED_MENU_ITEMS = 9

_SHORT = 200
_LONG = 480

_DARK_WORDS = ("gelap", "dark", "hitam", "moody", "malam", "night mode", "tema gelap", "dark mode", "dark theme")
_BRIGHT_WORDS = ("cerah", "terang", "bright", "light theme", "tema cerah", "putih bersih", "airy")

PALETTE_KEYS = ("bg", "surface", "text", "muted", "accent", "accent_2")


# ============================================================================
# BRIEF
# ============================================================================

@dataclass
class PlanBrief:
    """Everything Pass 1 needs, mapped from the create form (§0)."""

    business_name: str
    description: str
    vertical: str = "general"  # food | bakery | clothing | salon | services | general
    vertical_source: str = "auto"  # merchant | auto
    language: str = "ms"
    theme: str = "bright"  # bright | dark — the resolved wall
    theme_source: str = "default"  # merchant | brief | default
    theme_note: str = ""
    style: Optional[str] = None  # doodle | elegant | minimal | playful | bold | classic
    design_brief: Optional[str] = None
    freedom: str = "designer"  # designer (bebas) | guided (ikut sistem)
    brand_colors: Optional[Dict[str, str]] = None
    image_colours: List[str] = field(default_factory=list)
    has_hero_image: bool = False
    hero_full_bleed_ok: bool = True
    hero_video: bool = False
    menu_item_count: int = 0
    menu_has_images: bool = False
    gallery_count: int = 0
    whatsapp: bool = True
    maps: bool = True
    delivery: bool = False
    contact_form: bool = True
    social: bool = False
    show_prices: bool = True
    payment_methods: List[str] = field(default_factory=list)
    address: Optional[str] = None
    hours: Optional[str] = None
    include_ecommerce: bool = False
    location_known: bool = False
    testimonials: int = 0

    @property
    def is_fnb(self) -> bool:
        return self.vertical in dd.FNB_VERTICALS

    @property
    def custom_direction_allowed(self) -> bool:
        return self.freedom == "designer"


def brief_theme_request(text: Optional[str]) -> Optional[str]:
    """What the merchant's free text asks for — "dark", "bright" or None."""
    if not text:
        return None
    lowered = text.lower()
    dark = any(w in lowered for w in _DARK_WORDS)
    bright = any(w in lowered for w in _BRIGHT_WORDS)
    # "jangan gelap" / "not dark" is a request for bright.
    if re.search(r"(jangan|tak nak|tidak|bukan|no|not)\s+(terlalu\s+)?(gelap|dark)", lowered):
        return "bright"
    if dark and not bright:
        return "dark"
    if bright and not dark:
        return "bright"
    return None


def resolve_theme(color_mode: Optional[str], design_brief: Optional[str], touched: bool = True) -> Tuple[str, str, str]:
    """(theme, source, note). The brief beats the toggle; the toggle beats
    the bright default. ``touched`` False means the merchant never changed
    the toggle, so its value is only the default."""
    asked = brief_theme_request(design_brief)
    toggle = "dark" if str(color_mode or "").lower() in ("dark", "gelap") else "bright"
    if asked and asked != toggle:
        return asked, "brief", (
            f"The written brief asks for a {asked} page while the colour theme toggle says {toggle}; "
            f"the brief wins."
        )
    if asked:
        return asked, "brief", ""
    if touched or toggle == "dark":
        return toggle, "merchant", ""
    return "bright", "default", ""


def brief_completeness(brief: PlanBrief) -> int:
    """0–100 — how much real material the plan has to work with."""
    score = 0
    words = len((brief.description or "").split())
    score += min(35, int(words / 60 * 35)) if words else 0
    if brief.menu_item_count:
        score += min(25, 8 + brief.menu_item_count * 3)
    if brief.has_hero_image:
        score += 15
    if brief.address:
        score += 10
    if brief.whatsapp:
        score += 5
    if brief.hours:
        score += 5
    if brief.design_brief:
        score += 5
    return max(0, min(100, score))


def listening_questions(brief: PlanBrief) -> List[str]:
    """The follow-up questions to ask when the brief is too thin to plan
    from. Deterministic, in the site language, only for what is missing."""
    ms = brief.language != "en"
    q: List[str] = []
    words = len((brief.description or "").split())
    if words < 40:
        q.append(
            "Ceritakan sikit lagi: apa yang istimewa tentang kedai anda, siapa pelanggan biasa, dan sejak bila anda beroperasi?"
            if ms else
            "Tell us a little more: what makes your shop special, who are your regulars, and since when have you been open?"
        )
    if brief.is_fnb and brief.menu_item_count == 0:
        q.append(
            "Apa 3 hidangan paling laris dan harganya?" if ms else "What are your 3 best-selling dishes and their prices?"
        )
    elif brief.vertical == "salon" and brief.menu_item_count == 0:
        q.append("Apa servis utama anda dan harga permulaannya?" if ms else "What are your main services and their starting prices?")
    elif brief.vertical == "services" and brief.menu_item_count == 0:
        q.append("Apa perkhidmatan yang anda tawarkan dan kawasan mana anda liputi?" if ms else "Which services do you offer and which areas do you cover?")
    elif brief.vertical in ("clothing", "general") and brief.menu_item_count == 0:
        q.append("Apa produk utama anda dan julat harganya?" if ms else "What are your main products and their price range?")
    if not brief.address:
        q.append("Di mana lokasi kedai anda (alamat penuh)?" if ms else "Where is your shop (full address)?")
    if not brief.hours:
        q.append("Apa waktu operasi anda?" if ms else "What are your opening hours?")
    if not brief.has_hero_image:
        q.append(
            "Ada gambar hidangan / kedai yang anda mahu jadikan gambar utama?" if ms and brief.is_fnb
            else ("Ada gambar kedai atau kerja anda untuk gambar utama?" if ms else "Do you have a photo of your food, shop or work for the main image?")
        )
    return q[:5]


# ============================================================================
# PLAN
# ============================================================================

@dataclass
class DesignPlan:
    direction: str  # library key or "custom:<slug>"
    direction_name: str
    why: str
    palette: Dict[str, str]
    type: Dict[str, Any]  # display, body, scale, display_weight
    hero_treatment: str
    signature_element: str
    layout_notes: str
    motion: str
    avoid: List[str]
    theme: str
    vertical: str
    sections: List[str]
    brief_quotes: List[str] = field(default_factory=list)
    custom: bool = False
    source: str = "ai"  # ai | fallback
    adjustments: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)
    image_cue: str = ""
    variant: int = 0

    # ---- serialisation ------------------------------------------------
    def as_dict(self) -> Dict[str, Any]:
        return {
            "version": PLAN_VERSION,
            "direction": self.direction,
            "direction_name": self.direction_name,
            "why": self.why,
            "palette": dict(self.palette),
            "type": dict(self.type),
            "hero_treatment": self.hero_treatment,
            "signature_element": self.signature_element,
            "layout_notes": self.layout_notes,
            "motion": self.motion,
            "avoid": list(self.avoid),
            "theme": self.theme,
            "vertical": self.vertical,
            "sections": list(self.sections),
            "brief_quotes": list(self.brief_quotes),
            "custom": self.custom,
            "source": self.source,
            "adjustments": list(self.adjustments),
            "notes": list(self.notes),
            "variant": self.variant,
        }

    @property
    def direction_key(self) -> str:
        return self.direction

    # ---- adapters -----------------------------------------------------
    def concept_palette(self) -> Dict[str, str]:
        """The plan palette in the design_system token shape the rest of
        the pipeline (tailwind config, colour-mode guard, contrast guard)
        already understands."""
        accent = self.palette["accent"]
        from app.services.contrast_guard import AA_TEXT, adjust_for_contrast
        surfaces = [self.palette["bg"], self.palette["surface"]]
        strong = adjust_for_contrast(self.palette["accent_2"], surfaces, AA_TEXT) or accent
        secondary = adjust_for_contrast(accent, surfaces, 6.0) or accent
        return {
            "primary": accent,
            "secondary": secondary,
            "accent": self.palette["accent_2"],
            "accent_strong": strong,
            "background": self.palette["bg"],
            "surface": self.palette["surface"],
            "text": self.palette["text"],
            "text_muted": self.palette["muted"],
            "border": "rgba(255,255,255,0.12)" if self.theme == "dark" else "rgba(17,24,39,0.08)",
        }

    def font_pairing(self) -> Dict[str, str]:
        display, body = self.type["display"], self.type["body"]
        dm = dd.ALLOWED_FONTS[display]
        bm = dd.ALLOWED_FONTS[body]
        cat_d = GOOGLE_FONTS.get(display, {}).get("category", "sans")
        cat_b = GOOGLE_FONTS.get(body, {}).get("category", "sans")
        return {
            "heading": display,
            "heading_weights": dm["weights"],
            "heading_fallback": FONT_FALLBACKS.get(cat_d, FONT_FALLBACKS["sans"]),
            "heading_category": cat_d,
            "body": body,
            "body_weights": bm["weights"],
            "body_fallback": FONT_FALLBACKS.get(cat_b, FONT_FALLBACKS["sans"]),
            "body_category": cat_b,
            "vibe": self.direction_name,
            "cdn_link": dd.google_fonts_link(display, body),
        }

    def to_concept(self, language: str = "ms") -> DesignConcept:
        titles = dd.SECTION_TITLES
        lang = "en" if str(language).lower().startswith("en") else "ms"
        sections = [
            ConceptSection(id=s, title=titles.get(s, {}).get(lang, s.replace("_", " ").title()))
            for s in self.sections
        ]
        return DesignConcept(
            name=self.direction_name,
            mood=[w.strip() for w in re.split(r"[,/]", self.direction_name) if w.strip()][:3],
            rationale=self.why,
            palette=self.concept_palette(),
            fonts=self.font_pairing(),
            typography_note=(
                f"Scale {self.type['scale']}; display weight {self.type['display_weight']}; "
                "headlines set whole — no italic or recoloured word, no eyebrow above every heading."
            ),
            hero_pattern=self.hero_treatment,
            hero_description=self.signature_element if self.hero_treatment != "typographic" else "typography-led hero",
            sections=sections,
            signature_details=[self.signature_element],
            copy_voice="",
            motion=self.motion,
            source=self.source,
            adjustments=list(self.adjustments),
        )

    # ---- prompt -------------------------------------------------------
    def to_prompt_block(self, language: str = "ms") -> str:
        """The binding spec Pass 2 reads. It restates the plan as rules the
        model may not change."""
        lang = "en" if str(language).lower().startswith("en") else "ms"
        titles = dd.SECTION_TITLES
        section_rows = "\n".join(
            f"  {i}. {titles.get(s, {}).get(lang, s)} (id: {s})" for i, s in enumerate(self.sections, 1)
        )
        pal = self.palette
        lines = [
            f"===== DESIGN PLAN — \"{self.direction_name}\" (BINDING SPEC — DO NOT CHANGE PALETTE, FONTS, HERO TREATMENT OR SIGNATURE ELEMENT) =====",
            f"Why this direction for THIS business: {self.why}",
        ]
        if self.brief_quotes:
            lines.append("Merchant brief sentences this plan honours (deliver each one visibly): "
                         + " | ".join(f"\"{q}\"" for q in self.brief_quotes))
        for note in self.notes:
            lines.append(f"Note: {note}")
        lines += [
            f"Theme: {'DARK page (dark background, light text)' if self.theme == 'dark' else 'BRIGHT page (light background, dark text) — warm, appetising, welcoming'}",
            (
                f"Palette (also wired into tailwind.config + CSS variables): page bg {pal['bg']}, surface {pal['surface']}, "
                f"text {pal['text']}, muted {pal['muted']}, accent {pal['accent']} (buttons, prices, one signature use), "
                f"accent_2 {pal['accent_2']} (fills, badges, one band — never body text)"
            ),
            (
                f"Type: display '{self.type['display']}' at weight {self.type['display_weight']} for the hero headline and section headings; "
                f"body '{self.type['body']}' 16–18px; modular scale {self.type['scale']} — set sizes with clamp() in the stylesheet, never inline font-size on headings; "
                "line length ≤ 75 characters; headlines are set whole (one colour, one style, no italic word, no coloured word)."
            ),
            f"Hero treatment: {self.hero_treatment.upper()} — {_HERO_TREATMENT_RULES[self.hero_treatment]}",
            f"Signature element (the ONE memorable thing on this page — build it exactly, and only once): {self.signature_element}",
            f"Layout: {self.layout_notes}",
            f"Motion: {self.motion}. No other animation anywhere: no data-aos on sections, no scroll reveals; hover states on interactive elements only.",
            "Deliberately avoided on this page: " + "; ".join(self.avoid),
            "Page sections, in this order (build ONLY these; a section that is not listed does not exist):",
            section_rows,
        ]
        return "\n".join(lines)


_HERO_TREATMENT_RULES: Dict[str, str] = {
    "photo-full-bleed": (
        "the hero photo fills the viewport width (min-height 70vh desktop, 60vh mobile) with a solid bottom or side panel / gradient scrim "
        "so the name and CTA read at 4.5:1; the dish or shop name is the headline; CTA row = the WhatsApp order button + the 'view menu/products' link, nothing else"
    ),
    "photo-split": (
        "a two-column hero: headline + one line + CTA row on one side, the photo on the other (stacks photo-first on mobile); "
        "text sits on the page background, never on the photo"
    ),
    "typographic": (
        "no photo in the first screen: the name at display size (clamp(3rem, 9vw, 7rem)), one line beneath, the CTA row; "
        "the first photo appears in the next section"
    ),
    "pattern": (
        "the first screen is a coloured or patterned band (SVG pattern, blob shapes or hand-drawn accents in accent colours) "
        "with the name, one line and the CTA row; the hero photo, if any, sits inside a shaped frame within the band"
    ),
    "menu-first": (
        "the menu highlights ARE the hero: the name and one line on top, then immediately the top items with large prices and the WhatsApp order buttons — "
        "the visitor sees what to order before scrolling"
    ),
}


# ============================================================================
# CANDIDATES + HISTORY
# ============================================================================

def candidates_for(brief: PlanBrief, history: Sequence[str] = ()) -> List[dd.Direction]:
    """Ranked candidate directions for this brief, with the last-N same
    category directions excluded (rotation)."""
    text = " ".join(filter(None, [brief.business_name, brief.description, brief.design_brief or ""]))
    pool = dd.candidate_directions(
        brief.vertical, theme=brief.theme, style=brief.style, exclude=list(history)[:DIRECTION_HISTORY_WINDOW]
    )
    return dd.rank_directions(pool, text=text, vertical=brief.vertical, seed=brief.business_name)


def sections_for(brief: PlanBrief) -> List[str]:
    """The section list the plan may build, from the vertical's section set
    and the feature toggles. A feature that is OFF has no section."""
    base = dd.section_set_for(brief.vertical)
    sections = list(base["required"])
    # Gallery only with ≥ 3 gallery images that are not menu images.
    if "gallery" in base["optional"] and brief.gallery_count >= 3:
        idx = sections.index("about") + 1 if "about" in sections else len(sections) - 2
        sections.insert(idx, "gallery")
    if "galeri_kerja" in base["optional"] and brief.gallery_count >= 3:
        sections.insert(len(sections) - 1, "galeri_kerja")
    if "testimoni" in base["optional"] and brief.testimonials > 0:
        sections.insert(len(sections) - 1, "testimoni")
    if "about" in base["optional"] and len((brief.description or "").split()) >= 40:
        sections.insert(1 if len(sections) > 1 else 0, "about")
    # Contact is one band — never a "Hantar Mesej" section plus a "Jumpa Kami"
    # section both with WhatsApp. With WhatsApp off and no form, contact
    # collapses into the location section (address text) and the footer.
    if not brief.whatsapp and not brief.contact_form:
        for key in ("contact", "hubungi"):
            if key in sections and "location" in sections:
                sections.remove(key)
    return sections


# ============================================================================
# PROMPT
# ============================================================================

_PLAN_JSON_SHAPE = """{
  "direction": "the key of one candidate direction below, or a custom name when allowed",
  "why": "2 sentences tying the choice to THIS business's food/audience/place; quote the brief sentences you honoured",
  "brief_quotes": ["exact sentences from the merchant's brief this plan honours (empty when there is no brief)"],
  "palette": {"bg":"#RRGGBB","surface":"#RRGGBB","text":"#RRGGBB","muted":"#RRGGBB","accent":"#RRGGBB","accent_2":"#RRGGBB"},
  "type": {"display":"Font Name","body":"Font Name","scale":"e.g. 1.25 major third","display_weight":700},
  "hero_treatment": "photo-full-bleed | photo-split | typographic | pattern | menu-first",
  "signature_element": "the ONE memorable thing on this page, described concretely (what, where, which colour, how big)",
  "layout_notes": "alignment, grid, card vs. no-card, section rhythm",
  "motion": "one page-load moment, described; nothing else",
  "avoid": ["default tells this plan deliberately does not use"]
}"""


def _direction_row(d: dd.Direction) -> str:
    p = d.palette
    return (
        f"- {d.key} — \"{d.name}\" ({d.feel}). For: {d.audience}. Styles: {', '.join(dd.STYLE_LABELS_MS[s] for s in d.styles)}. "
        f"Palette family: bg {p['bg']}, text {p['text']}, accent {p['accent']}, accent_2 {p['accent_2']}. "
        f"Type: {d.type['display']} + {d.type['body']}. Hero: {d.hero_treatment}. Signature: {d.signature_element}"
    )


def build_plan_prompt(
    brief: PlanBrief,
    candidates: Sequence[dd.Direction],
    history: Sequence[str] = (),
    n_plans: int = 1,
) -> str:
    """The Pass 1 prompt. Lists the eligible directions, the hard
    constraints from the merchant's form, the image colour hints and the
    exact JSON shape."""
    constraints: List[str] = []
    theme_line = (
        "DARK page — the merchant chose Gelap (or the brief asks for dark): only dark directions are eligible, deep colour not #111."
        if brief.theme == "dark" else
        "BRIGHT page — bright, appetising, warm, welcoming. Dark directions are NOT eligible."
    )
    if brief.theme_note:
        theme_line += f" ({brief.theme_note})"
    constraints.append(f"- Theme: {theme_line}")
    if brief.style:
        constraints.append(
            f"- Gaya design: the merchant picked {dd.STYLE_LABELS_MS[brief.style].upper()} — every candidate below carries that tag; the plan must read unmistakably as that style."
        )
    else:
        constraints.append("- Gaya design: Auto — pick freely among the candidates for the closest fit.")
    constraints.append(
        "- Designer bebas: you MAY propose a custom direction outside the list when none fits; name it and give it a full palette/type/hero/signature."
        if brief.custom_direction_allowed else
        "- Ikut sistem: choose ONLY from the candidate list; keep the BinaApp house section order."
    )
    constraints.append(
        f"- Jenis kedai: {brief.vertical.upper()} ({'merchant pick' if brief.vertical_source == 'merchant' else 'classified from the brief'}). "
        f"Sections for this plan (fixed): {', '.join(sections_for(brief))}."
    )
    constraints.append(f"- Language: {'Bahasa Malaysia' if brief.language != 'en' else 'English'} (write this plan in English).")
    if brief.hero_video:
        constraints.append("- Hero video is ON: hero_treatment MUST be photo-full-bleed (the video is the page-load moment; motion = the video itself).")
    elif brief.has_hero_image:
        constraints.append(
            "- A real hero photo exists"
            + (" (good quality; full-bleed allowed)." if brief.hero_full_bleed_ok else " but it is too small or portrait for full-bleed — use photo-split.")
        )
    else:
        constraints.append("- No hero photo: hero_treatment must be typographic, pattern or menu-first.")
    if brief.image_colours:
        constraints.append(
            f"- Dominant colours in the merchant's photos: {', '.join(brief.image_colours[:4])} — harmonise the palette with the food/products (accent_2 may borrow one)."
        )
    if brief.brand_colors:
        constraints.append("- Merchant brand colours (must be the core of the palette): " + ", ".join(f"{k} {v}" for k, v in brief.brand_colors.items()))
    if brief.menu_item_count:
        constraints.append(
            f"- {brief.menu_item_count} real item(s) with names/prices"
            + (" and photos." if brief.menu_has_images else " and NO photos: plan typographic tiles in the accent colour, never placeholder icons.")
        )
    if not brief.whatsapp:
        constraints.append("- No WhatsApp number: the plan has NO WhatsApp buttons anywhere.")
    if not brief.maps:
        constraints.append("- Google Maps OFF: location is address text only, no map.")
    if not brief.contact_form:
        constraints.append("- Borang Tempahan OFF: no contact form slot.")
    if history:
        constraints.append(
            f"- The last {len(list(history)[:DIRECTION_HISTORY_WINDOW])} {brief.vertical} site(s) used: {', '.join(list(history)[:DIRECTION_HISTORY_WINDOW])} — those are excluded; do not pick them."
        )

    brief_block = ""
    if brief.design_brief:
        brief_block = (
            "MERCHANT'S BRIEF — HIGHEST PRIORITY. Quote in `brief_quotes` every sentence you honour, and say in `why` how:\n"
            f"\"\"\"{brief.design_brief}\"\"\"\n\n"
        )

    fonts_line = (
        "Display (headline) fonts allowed: " + ", ".join(dd.DISPLAY_FONTS) + ". "
        "Body fonts allowed: " + ", ".join(dd.BODY_FONTS) + ". "
        "One family, or two clearly distinct families (serif + sans, grotesk + humanist, rounded + humanist). Never two similar sans."
    )
    multi = ""
    if n_plans > 1:
        multi = (
            f"\nReturn {n_plans} DIFFERENT plans (different directions, palettes and hero treatments) as a JSON array of {n_plans} plan objects. "
            "Each object has exactly the shape below.\n"
        )

    return f"""You are the senior designer at a boutique web studio in Kuala Lumpur. Write the DESIGN PLAN for this merchant's website — the decisions a real designer would make for THIS restaurant or shop, not a template with a new colour.

BUSINESS: {brief.business_name}
TYPE: {brief.vertical}
DESCRIPTION:
\"\"\"{brief.description}\"\"\"

{brief_block}CONSTRAINTS FROM THE MERCHANT'S FORM (every one is law):
{chr(10).join(constraints)}

CANDIDATE DIRECTIONS (pick the closest fit for the food, audience and place, then adapt the colours to the merchant's own photos):
{chr(10).join(_direction_row(d) for d in candidates)}

RULES:
- Palette: 6-digit hex. text on bg ≥ 4.5:1, accent on bg ≥ 3:1, muted on bg ≥ 3:1. Adapt the family, do not copy it blindly.
- The cream + serif + gold/terracotta combination is the default everything converges on: use it ONLY if the direction is Dapur Keluarga / Warisan Malam and say why.
- {fonts_line}
- One signature element. One motion moment. Headlines set whole — no italic word, no recoloured word, no ALL-CAPS eyebrow above every heading.
- Cards only where content is a set of equal items (menu/products). About, location and story use open layouts.
- Do not invent business facts (years, awards, ratings, hours, prices) — facts come only from the description and the merchant's data.
{multi}
Return ONLY the JSON, no markdown fences, no commentary, in exactly this shape:
{_PLAN_JSON_SHAPE}"""


# ============================================================================
# PARSING + VALIDATION
# ============================================================================

def _extract_json(raw: str) -> Optional[Any]:
    if not raw or not isinstance(raw, str):
        return None
    text = raw.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text)
    starts = [i for i in (text.find("{"), text.find("[")) if i != -1]
    if not starts:
        return None
    start = min(starts)
    end = max(text.rfind("}"), text.rfind("]"))
    if end <= start:
        return None
    candidate = text[start:end + 1]
    for attempt in (candidate, re.sub(r",\s*([}\]])", r"\1", candidate)):
        try:
            return json.loads(attempt)
        except json.JSONDecodeError:
            continue
    return None


def _clip(value: Any, n: int) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()[:n]


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (value or "").lower()).strip("-")[:40] or "custom"


def _hue_sat_light(hex_color: str) -> Tuple[float, float, float]:
    import colorsys
    h = normalize_hex(hex_color) or "#000000"
    r, g, b = int(h[1:3], 16) / 255, int(h[3:5], 16) / 255, int(h[5:7], 16) / 255
    hue, light, sat = colorsys.rgb_to_hls(r, g, b)
    return hue * 360, sat, light


def looks_cream(hex_color: str) -> bool:
    hue, sat, light = _hue_sat_light(hex_color)
    # Cream sits between near-white (#FAFAF8 is a white page, not cream)
    # and beige: warm hue, a visible tint, lightness in the 0.86–0.955 band.
    return 0.86 <= light <= 0.955 and sat >= 0.15 and 25 <= hue <= 65


def looks_gold_or_terracotta(hex_color: str) -> bool:
    hue, sat, light = _hue_sat_light(hex_color)
    return sat >= 0.3 and 15 <= hue <= 50 and 0.25 <= light <= 0.75


def uses_cream_serif_gold(palette: Dict[str, str], display_font: str) -> bool:
    """The default combo every site converged on."""
    serif = dd.font_class(display_font) == "serif"
    return serif and looks_cream(palette.get("bg", "")) and (
        looks_gold_or_terracotta(palette.get("accent", "")) or looks_gold_or_terracotta(palette.get("accent_2", ""))
    )


def _validate_palette(raw: Any, direction: dd.Direction, brief: PlanBrief, adjustments: List[str]) -> Dict[str, str]:
    from app.services.contrast_guard import adjust_for_contrast

    raw = raw if isinstance(raw, dict) else {}
    palette: Dict[str, str] = {}
    for key in PALETTE_KEYS:
        value = normalize_hex(raw.get(key))
        if value is None:
            value = direction.palette[key]
            if key in raw:
                adjustments.append(f"palette.{key}: invalid hex replaced from {direction.name}")
        palette[key] = value

    # Brand colours are the merchant's own — strongest override.
    if brief.brand_colors:
        primary = normalize_hex(brief.brand_colors.get("primary"))
        secondary = normalize_hex(brief.brand_colors.get("secondary") or brief.brand_colors.get("accent"))
        if primary and palette["accent"] != primary:
            palette["accent"] = primary
            adjustments.append("palette.accent: merchant brand colour applied")
        if secondary and palette["accent_2"] != secondary:
            palette["accent_2"] = secondary
            adjustments.append("palette.accent_2: merchant brand colour applied")

    # Theme is a wall: a plan that flips it has its neutrals reset.
    wants_dark = brief.theme == "dark"
    bg_ok = is_dark(palette["bg"]) if wants_dark else is_light(palette["bg"])
    if not bg_ok:
        for key in ("bg", "surface", "text", "muted"):
            palette[key] = direction.palette[key]
        adjustments.append(f"palette: background did not match the {brief.theme} theme — neutrals reset from {direction.name}")
    surface_ok = is_dark(palette["surface"]) if wants_dark else not is_dark(palette["surface"])
    if not surface_ok:
        palette["surface"] = direction.palette["surface"]
        adjustments.append("palette.surface: did not match the theme — reset")

    if contrast_ratio(palette["text"], palette["bg"]) < MIN_TEXT_CONTRAST or contrast_ratio(palette["text"], palette["surface"]) < MIN_TEXT_CONTRAST:
        palette["text"] = direction.palette["text"] if (
            contrast_ratio(direction.palette["text"], palette["bg"]) >= MIN_TEXT_CONTRAST
        ) else ("#F5F5F7" if wants_dark else "#111827")
        adjustments.append("palette.text: below 4.5:1 on background/surface — replaced")
    if contrast_ratio(palette["muted"], palette["bg"]) < MIN_MUTED_CONTRAST:
        repaired = adjust_for_contrast(palette["muted"], [palette["bg"], palette["surface"]], MIN_MUTED_CONTRAST)
        palette["muted"] = repaired or ("#B4B4C0" if wants_dark else "#4B5563")
        adjustments.append("palette.muted: below 3:1 — adjusted")
    if contrast_ratio(palette["accent"], palette["bg"]) < MIN_ACCENT_CONTRAST:
        repaired = adjust_for_contrast(palette["accent"], [palette["bg"], palette["surface"]], MIN_ACCENT_CONTRAST)
        if repaired:
            adjustments.append(f"palette.accent: {palette['accent']} below 3:1 — adjusted in-hue to {repaired}")
            palette["accent"] = repaired
        else:
            palette["accent"] = direction.palette["accent"]
            adjustments.append("palette.accent: unreadable — replaced from the direction")

    # Harmonise with the merchant's photos: accent_2 may borrow the most
    # saturated photo colour when it still reads as a fill on this page.
    if brief.image_colours and not brief.brand_colors and not raw.get("accent_2"):
        for colour in brief.image_colours:
            c = normalize_hex(colour)
            if c and contrast_ratio(c, palette["bg"]) >= 1.6:
                palette["accent_2"] = c
                adjustments.append(f"palette.accent_2: harmonised with photo colour {c}")
                break
    return palette


def _validate_type(raw: Any, direction: dd.Direction, adjustments: List[str]) -> Dict[str, Any]:
    raw = raw if isinstance(raw, dict) else {}
    display = dd.resolve_allowed_font(raw.get("display"), role="display")
    if display is None:
        adjustments.append(f"type.display: '{raw.get('display')}' not in the allowlist — using {direction.type['display']}")
        display = direction.type["display"]
    body_name = raw.get("body")
    body = dd.resolve_allowed_font(body_name, role="body")
    if body is None:
        # A single-family plan may set body = display when the display face
        # is a readable sans (Rubik, Outfit, Familjen Grotesk, Bricolage).
        same = dd.resolve_allowed_font(body_name)
        if same == display and dd.font_class(display) in ("rounded", "grotesk") and display not in ("Archivo Black", "Unbounded", "Syne", "Fredoka", "Baloo 2"):
            body = display
        else:
            adjustments.append(f"type.body: '{body_name}' not a body face — using {direction.type['body']}")
            body = direction.type["body"]
    if not dd.is_valid_pairing(display, body):
        adjustments.append(f"type: {display} + {body} are two similar sans — body reset to {direction.type['body']}")
        body = direction.type["body"] if dd.is_valid_pairing(display, direction.type["body"]) else "Source Sans 3"
    scale = dd.nearest_type_scale(raw.get("scale") or direction.type["scale"])
    weights = [int(w) for w in dd.ALLOWED_FONTS[display]["weights"].split(";")]
    try:
        wanted = int(raw.get("display_weight") or direction.type["display_weight"])
    except (TypeError, ValueError):
        wanted = int(direction.type["display_weight"])
    weight = min(weights, key=lambda w: abs(w - wanted))
    if weight != wanted:
        adjustments.append(f"type.display_weight: {wanted} not served for {display} — using {weight}")
    return {"display": display, "body": body, "scale": scale, "display_weight": weight}


def _validate_hero(raw: Any, direction: dd.Direction, brief: PlanBrief, adjustments: List[str]) -> str:
    treatment = _clip(raw, 40).lower().replace(" ", "-").replace("_", "-")
    if treatment not in dd.HERO_TREATMENTS:
        if treatment:
            adjustments.append(f"hero_treatment: '{treatment}' unknown — using {direction.hero_treatment}")
        treatment = direction.hero_treatment
    if brief.hero_video:
        if treatment != "photo-full-bleed":
            adjustments.append("hero_treatment: hero video is on — forced to photo-full-bleed")
        return "photo-full-bleed"
    if treatment.startswith("photo") and not brief.has_hero_image:
        fallback = "menu-first" if (brief.is_fnb and brief.menu_item_count) else "typographic"
        adjustments.append(f"hero_treatment: no hero photo — {treatment} replaced with {fallback}")
        return fallback
    if treatment == "photo-full-bleed" and brief.has_hero_image and not brief.hero_full_bleed_ok:
        adjustments.append("hero_treatment: hero photo too small/portrait for full-bleed — using photo-split")
        return "photo-split"
    return treatment


def _string_list(raw: Any, n: int, each: int) -> List[str]:
    if isinstance(raw, str):
        raw = [raw]
    if not isinstance(raw, list):
        return []
    out = []
    for item in raw:
        text = _clip(item, each)
        if text and text not in out:
            out.append(text)
        if len(out) >= n:
            break
    return out


def _sentences(text: str) -> List[str]:
    parts = re.split(r"(?<=[.!?])\s+|\n+", text or "")
    return [p.strip() for p in parts if len(p.strip()) >= 6]


def _validate_brief_quotes(raw: Any, why: str, design_brief: Optional[str], adjustments: List[str]) -> List[str]:
    """Quotes must actually come from the brief. Missing quotes are filled
    with the brief sentences the plan text mentions; if none match, every
    brief sentence is carried so Pass 2 still delivers it."""
    if not design_brief:
        return []
    sentences = _sentences(design_brief)
    lowered_brief = design_brief.lower()
    quotes: List[str] = []
    for q in _string_list(raw, 6, 240):
        if q.lower() in lowered_brief:
            quotes.append(q)
        else:
            adjustments.append("brief_quotes: dropped a quote that is not in the brief")
    if not quotes:
        why_l = (why or "").lower()
        for s in sentences:
            words = [w for w in re.findall(r"[a-zÀ-ɏ]{4,}", s.lower())]
            if words and sum(1 for w in words if w in why_l) >= max(1, len(words) // 3):
                quotes.append(s)
        if not quotes:
            quotes = sentences[:4]
            adjustments.append("brief_quotes: none supplied — carrying the whole brief")
    return quotes[:6]


def _resolve_direction(
    raw: Any,
    brief: PlanBrief,
    candidates: Sequence[dd.Direction],
    history: Sequence[str],
    adjustments: List[str],
) -> Tuple[dd.Direction, str, str, bool]:
    """(anchor direction, key, name, custom)."""
    name = _clip(raw, 80)
    key = re.sub(r"[^a-z0-9_]+", "_", name.lower()).strip("_")
    recent = set(list(history)[:DIRECTION_HISTORY_WINDOW])
    candidate_keys = {d.key: d for d in candidates}
    by_name = {d.name.lower(): d for d in candidates}
    chosen = candidate_keys.get(key) or by_name.get(name.lower())
    if chosen is None and key in dd.DIRECTION_BY_KEY:
        lib = dd.DIRECTION_BY_KEY[key]
        # A library direction outside the eligible set: wrong theme/style or
        # excluded by history. Only history can be argued with (pool never
        # empty), theme and style cannot.
        if lib.theme == brief.theme and (not brief.style or brief.style in lib.styles):
            chosen = lib  # history is handled below (rotation), theme/style are walls
        else:
            adjustments.append(f"direction: '{key}' not eligible for this theme/style — using {candidates[0].name}")
            chosen = candidates[0]
    if chosen is not None:
        if chosen.key in recent:
            alt = next((d for d in candidates if d.key not in recent), candidates[0])
            adjustments.append(f"direction: {chosen.name} used by a recent {brief.vertical} site — rotated to {alt.name}")
            chosen = alt
        return chosen, chosen.key, chosen.name, False
    if name and brief.custom_direction_allowed:
        anchor = candidates[0]
        return anchor, f"custom:{_slug(name)}", name, True
    if name:
        adjustments.append(f"direction: custom '{name}' not allowed under Ikut sistem — using {candidates[0].name}")
    else:
        adjustments.append(f"direction: none given — using {candidates[0].name}")
    return candidates[0], candidates[0].key, candidates[0].name, False


def _plan_from_dict(
    data: Dict[str, Any],
    brief: PlanBrief,
    candidates: Sequence[dd.Direction],
    history: Sequence[str],
    variant: int = 0,
) -> DesignPlan:
    adjustments: List[str] = []
    notes: List[str] = []
    anchor, key, name, custom = _resolve_direction(data.get("direction"), brief, candidates, history, adjustments)
    palette = _validate_palette(data.get("palette"), anchor, brief, adjustments)
    typ = _validate_type(data.get("type"), anchor, adjustments)
    why = _clip(data.get("why"), _LONG) or anchor.audience
    if uses_cream_serif_gold(palette, typ["display"]) and not anchor.cream_allowed:
        palette = dict(anchor.palette) if not custom else {**palette, "bg": "#FFFFFF", "surface": "#F5F5F5"}
        palette = _validate_palette(palette, anchor, brief, [])
        adjustments.append("palette: cream + serif + gold default combo rejected — this direction does not justify it")
    hero = _validate_hero(data.get("hero_treatment"), anchor, brief, adjustments)
    signature = _clip(data.get("signature_element"), _LONG) or anchor.signature_element
    layout = _clip(data.get("layout_notes"), _LONG) or anchor.layout_notes
    if brief.hero_video:
        motion = "the hero background video itself is the page-load moment; no other animation"
    else:
        motion = _clip(data.get("motion"), _SHORT) or anchor.motion
    avoid = _string_list(data.get("avoid"), 10, 120)
    for default in dd._DEFAULT_AVOID:
        if default not in avoid:
            avoid.append(default)
    if brief.theme_note:
        notes.append(brief.theme_note)
    quotes = _validate_brief_quotes(data.get("brief_quotes"), why, brief.design_brief, adjustments)
    return DesignPlan(
        direction=key,
        direction_name=name,
        why=why,
        palette=palette,
        type=typ,
        hero_treatment=hero,
        signature_element=signature,
        layout_notes=layout,
        motion=motion,
        avoid=avoid[:10],
        theme=brief.theme,
        vertical=brief.vertical,
        sections=sections_for(brief),
        brief_quotes=quotes,
        custom=custom,
        source="ai",
        adjustments=adjustments,
        notes=notes,
        image_cue=anchor.image_cue,
        variant=variant,
    )


def parse_plans(
    raw: Optional[str],
    brief: PlanBrief,
    candidates: Sequence[dd.Direction],
    history: Sequence[str] = (),
    n_plans: int = 1,
) -> List[DesignPlan]:
    """Model reply → validated plans (possibly fewer than asked; possibly
    empty when the reply carries no JSON). Multi-plan replies are kept
    distinct: a repeated direction is rotated to the next candidate."""
    data = _extract_json(raw or "")
    if data is None:
        return []
    items = data if isinstance(data, list) else [data]
    plans: List[DesignPlan] = []
    used: List[str] = list(history)[:DIRECTION_HISTORY_WINDOW]
    for i, item in enumerate(items[:max(1, n_plans)]):
        if not isinstance(item, dict):
            continue
        plan = _plan_from_dict(item, brief, candidates, used, variant=i)
        if n_plans > 1 and not plan.custom:
            used = [plan.direction] + used
        plans.append(plan)
        if plan.adjustments:
            logger.info("🎨 Plan adjusted during validation: %s", "; ".join(plan.adjustments))
    return plans


def parse_plan(raw: Optional[str], brief: PlanBrief, candidates: Sequence[dd.Direction], history: Sequence[str] = ()) -> Optional[DesignPlan]:
    plans = parse_plans(raw, brief, candidates, history, n_plans=1)
    return plans[0] if plans else None


def fallback_plan(
    brief: PlanBrief,
    candidates: Optional[Sequence[dd.Direction]] = None,
    history: Sequence[str] = (),
    variant: int = 0,
) -> DesignPlan:
    """A complete plan from the library alone — what Pass 2 gets when the
    plan model is off, slow or unparseable. Same validation as an AI plan."""
    candidates = list(candidates) if candidates else candidates_for(brief, history)
    anchor = candidates[min(variant, len(candidates) - 1)]
    data = {
        "direction": anchor.key,
        "why": f"{anchor.name}: {anchor.feel}. Chosen for {brief.business_name} because the brief reads as {anchor.audience.split(' — ')[0]}.",
        "palette": dict(anchor.palette),
        "type": dict(anchor.type),
        "hero_treatment": anchor.hero_treatment,
        "signature_element": anchor.signature_element,
        "layout_notes": anchor.layout_notes,
        "motion": anchor.motion,
        "avoid": list(anchor.avoid),
        "brief_quotes": [],
    }
    plan = _plan_from_dict(data, brief, candidates, history, variant=variant)
    plan.source = "fallback"
    return plan


def plans_are_distinct(plans: Sequence[DesignPlan]) -> bool:
    keys = [p.direction for p in plans]
    return len(keys) == len(set(keys))
