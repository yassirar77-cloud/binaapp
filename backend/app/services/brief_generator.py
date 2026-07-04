"""M1 Stage-1: user description + design intent → validated DesignBrief.

This is the "brief_generator.py" the V2 architecture doc planned but never
built. One DeepSeek JSON call produces a DesignBrief (section plan, style
DNA choice, copy in the target language); Pydantic + catalog + wording
validation gate it, with ONE corrective retry. Any remaining failure raises
BriefGenerationError — the caller (recipe_pipeline) lets that propagate so
ai_service falls back to the legacy pipeline.

The LLM is only offered section variants that actually have renderers
(IMPLEMENTED_VARIANTS below) — several declared variants in VALID_VARIANTS
have no renderer and would silently produce `<!-- Unknown component -->`.
"""

from __future__ import annotations

import json
import logging
from typing import Dict, List, Optional

from pydantic import ValidationError

from app.models.schemas import WebsiteGenerationRequest
from app.schemas.recipe import (
    VALID_VARIANTS,
    VARIANT_TO_COMPONENT,
    DesignBrief,
)
from app.services.html_renderer import COMPONENT_RENDERERS
from app.services.intent_extractor import DNA_RUBRIC, DesignIntent
from app.utils.llm_json import LLMJSONError, call_deepseek_json
from app.utils.output_lint import find_forbidden_wording

logger = logging.getLogger(__name__)


class BriefGenerationError(Exception):
    """Brief could not be produced/validated — caller falls back to legacy."""


# Only variants with a real renderer are offered to the LLM.
IMPLEMENTED_VARIANTS: Dict[str, List[str]] = {
    section.value: [
        variant for variant in variants
        if VARIANT_TO_COMPONENT[f"{section.value}:{variant}"] in COMPONENT_RENDERERS
    ]
    for section, variants in VALID_VARIANTS.items()
}

# Image keys the brief may reference when no images were uploaded —
# recipe_builder auto-fills these from the curated cuisine pools when
# cuisine_type is set and image_map is left empty.
CUISINE_POOL_KEYS = ["hero", "gallery_1", "gallery_2", "gallery_3", "gallery_4", "interior"]

_CONTENT_SPEC = """SECTION CONTENT SLOTS (write copy in the TARGET LANGUAGE; keep it specific to THIS business):
- hero (variants: {hero}): headline (short, punchy — sell the vibe, not "Welcome"), subheadline,
  cta_text, cta_link ("#menu" or the WhatsApp link), image_key ("hero"),
  halal_certified (boolean — set true ONLY if the business is Muslim-owned; this renders a
  "Pengusaha Muslim" badge)
- about (variants: {about}):
  - story: heading, paragraphs (2-3 short paragraphs telling THIS business's story), image_key ("interior")
  - stats: heading, description (include founding year if known), stats [{{"value","label"}}] (3-4)
  - timeline: heading, milestones [{{"year","title","description"}}] (3-4) — only when the business has real history
- menu (variants: {menu}): heading, subheading, fallback_items
  [{{"name","description","price","is_popular"}}] (4-6 real dishes from the description; prices in RM;
  invent plausible prices only if none given)
- gallery (variants: {gallery}): heading, subtitle, image_keys (subset of the available image keys)
- testimonial (variants: {testimonial}): heading, reviews [{{"name","text","rating"}}] (2-3, Malaysian names,
  natural voice matching the register)
- hours (variants: {hours}): heading, hours_structured [{{"day","time"}}] (7 rows, target language day names;
  use "Tutup"/"Closed" for off days)
- contact (variants: {contact}): heading, address, whatsapp_number, hours (one-line summary),
  show_map (boolean), map_query (address for Google Maps, only if show_map)
- cta (variants: {cta}): headline, subheadline, whatsapp_message (pre-filled order/booking text)
- footer (variants: {footer}): tagline, powered_by (true), social_links (object with instagram/facebook/tiktok
  URLs, only if given)"""


def _catalog_block() -> str:
    return _CONTENT_SPEC.format(**{
        section: ", ".join(variants) for section, variants in IMPLEMENTED_VARIANTS.items()
    })


def _dna_block(intent: DesignIntent, color_mode: str) -> str:
    lines = "\n".join(f"- {key}: {vibe}" for key, vibe in DNA_RUBRIC.items())
    hint = ""
    if intent.recommended_style_dna:
        hint = f"\nIntent analysis recommends: {intent.recommended_style_dna} — follow it unless the description clearly contradicts it."
    return (
        f"STYLE DNA (pick exactly one key):\n{lines}\n"
        f"Requested color mode: {color_mode} — prefer a DNA whose vibe says '{color_mode}'.{hint}"
    )


def build_brief_prompt(
    request: WebsiteGenerationRequest,
    intent: DesignIntent,
    available_image_keys: List[str],
    feedback: Optional[str] = None,
) -> str:
    language = "ms" if str(request.language.value if hasattr(request.language, "value") else request.language) == "ms" else "en"
    lang_name = "Bahasa Malaysia" if language == "ms" else "English"
    intent_json = intent.model_dump(exclude={"source"})

    correction = ""
    if feedback:
        correction = f"""

YOUR PREVIOUS ATTEMPT WAS REJECTED. Fix these problems and return the corrected JSON:
{feedback}"""

    return f"""Design a single-page website plan (a "Design Brief") for this Malaysian F&B business.

BUSINESS NAME: {request.business_name}
DESCRIPTION: {request.description}
TARGET LANGUAGE: {lang_name} — ALL copy (headlines, paragraphs, menu descriptions, hours, buttons) in {lang_name}.
WHATSAPP: {request.whatsapp_number or "not provided"}
DESIGN INTENT (extracted from the user's own words — honor it):
{json.dumps(intent_json, ensure_ascii=False)}

{_dna_block(intent, request.color_mode or "light")}

{_catalog_block()}

RULES:
1. 5 to 8 sections. First = hero, last = footer. A food business needs menu, hours, contact.
   Choose variants that fit the STORY (heritage → about:timeline or about:stats; youthful → punchy hero).
2. Copy must be specific and evocative — use the voice "{intent.voice}". Mention real dishes,
   the neighbourhood, the founding year when the description gives them. Never write generic filler
   like "Welcome to our website".
3. PROHIBITED WORDS (Trade Descriptions Act 2011): never write "Halal", "Halal Certified",
   "Sijil Halal" or "JAKIM" anywhere. Muslim-owned is expressed ONLY via halal_certified: true
   (renders a "Pengusaha Muslim" badge) or the words "Pengusaha Muslim".
4. Available image keys (reference ONLY these in image_key/image_keys): {available_image_keys}.
   Set "image_map" to {{}} — images are resolved from curated pools afterwards.
5. cuisine_type: one of mamak, malay_fusion, malay_traditional, fine_dining_malay, kopitiam_chinese,
   fast_food_halal, warung_kampung, cafe_modern, western_halal, thai_halal, indian_halal, nyonya.
6. business.about = list of 1-3 short paragraphs. business.whatsapp = the WhatsApp number digits.

Return ONLY a JSON object with this shape:
{{
  "language": "{language}",
  "business": {{"name", "type", "tagline", "about": [..], "address", "whatsapp", "operating_hours"}},
  "style_dna": "<dna key>",
  "color_mode": "{request.color_mode or "light"}",
  "cuisine_type": "<cuisine key>",
  "specific_dishes": ["dishes named in the description"],
  "sections": [{{"type", "variant", "content": {{...}}}}, ...],
  "image_map": {{}},
  "features": {{"whatsapp": {str(bool(request.include_whatsapp)).lower()}, "operating_hours": true, "price_list": true}}
}}{correction}"""


def _validate_brief_dict(data: dict, request: WebsiteGenerationRequest) -> DesignBrief:
    """Normalize + validate. Raises ValueError with actionable feedback text."""
    # Server-side truths override whatever the model wrote.
    language = "ms" if str(request.language.value if hasattr(request.language, "value") else request.language) == "ms" else "en"
    data["language"] = language
    data.setdefault("image_map", {})
    if request.whatsapp_number and isinstance(data.get("business"), dict):
        data["business"].setdefault("whatsapp", request.whatsapp_number)

    try:
        brief = DesignBrief(**data)
    except ValidationError as exc:
        raise ValueError(f"schema validation failed: {exc.errors()[:5]}") from exc

    unknown = [
        f"{s.type.value}:{s.variant}"
        for s in brief.sections
        if s.variant not in IMPLEMENTED_VARIANTS.get(s.type.value, [])
    ]
    if unknown:
        raise ValueError(
            f"unimplemented section variants {unknown}; allowed: "
            + json.dumps(IMPLEMENTED_VARIANTS)
        )

    forbidden = find_forbidden_wording(json.dumps(data, ensure_ascii=False))
    if forbidden:
        raise ValueError(
            f"forbidden wording {forbidden} — use 'Pengusaha Muslim' only, never Halal/JAKIM wording"
        )

    return brief


async def generate_brief(
    request: WebsiteGenerationRequest,
    intent: DesignIntent,
    available_image_keys: Optional[List[str]] = None,
) -> DesignBrief:
    """Produce a validated DesignBrief; one corrective retry, then raise."""
    keys = available_image_keys or CUISINE_POOL_KEYS
    system = (
        "You are an award-winning art director and copywriter for Malaysian F&B websites. "
        "You output only strict JSON."
    )

    feedback: Optional[str] = None
    last_error: Optional[Exception] = None
    for attempt in (1, 2):
        prompt = build_brief_prompt(request, intent, keys, feedback=feedback)
        try:
            data = await call_deepseek_json(
                prompt, system=system, temperature=0.6 if attempt == 1 else 0.3,
                max_tokens=4000, timeout=90.0,
            )
            brief = _validate_brief_dict(data, request)
            logger.info(
                "📋 brief generated (attempt %d): dna=%s sections=%s",
                attempt, brief.style_dna.value,
                [f"{s.type.value}:{s.variant}" for s in brief.sections],
            )
            return brief
        except (LLMJSONError, ValueError) as exc:
            logger.warning("brief attempt %d rejected: %s", attempt, exc)
            feedback = str(exc)
            last_error = exc

    raise BriefGenerationError(f"brief generation failed after retry: {last_error}")
