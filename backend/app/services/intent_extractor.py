"""M1 Stage-0: extract design intent from the user's free-text description.

The legacy pipeline collapses the description into ~9 business-type buckets
and drops every mood adjective ("retro neon", "nostalgia", "banyak white
space"). This module preserves that intent as a small structured object the
brief generator can act on.

One cheap DeepSeek JSON call; ALWAYS returns a DesignIntent — on any LLM
failure it degrades to a deterministic keyword-based fallback (intent
extraction must never be the reason a generation falls back to the legacy
pipeline; only brief generation/validation failures do that).
"""

from __future__ import annotations

import logging
from typing import List, Literal, Optional

from pydantic import BaseModel, Field, ValidationError

from app.schemas.style_dna import STYLE_DNAS
from app.utils.llm_json import LLMJSONError, call_deepseek_json

logger = logging.getLogger(__name__)

# One-line vibe rubric per Style DNA — used by both the intent prompt and
# the keyword fallback. Keys must stay in sync with schemas/style_dna.py
# (guarded by a test).
DNA_RUBRIC: dict = {
    "teh_tarik_warm": "warm, friendly, everyday family restaurant; cream + burnt orange; light",
    "pandan_fresh": "fresh, healthy, green, modern-clean; light",
    "kopi_hitam": "dark moody coffee, gold on near-black, intimate; dark",
    "sambal_berani": "bold, fiery, high-energy red; light",
    "sutera_putih": "minimalist, airy, lots of white space, quiet luxury; light",
    "lampu_neon": "electric neon on dark, nightlife energy; dark",
    "warisan_emas": "grand heritage, royal gold + deep tones, ceremonial/kenduri; dark",
    "ombak_biru": "coastal blue, breezy, seafood; light",
    "pasar_malam_neon": "retro night-market neon pink/teal on dark plum, youthful street vibe; dark",
    "kampung_serene": "serene traditional village elegance, soft earth tones, heritage serif; light",
    "kopitiam_nostalgia": "old-school kopitiam nostalgia, warm sepia, vintage classical serif; light",
    "streetfood_bold": "loud fast street-food energy, impact type, high contrast; light",
    "fine_dining_obsidian": "fine dining, obsidian black + gold, deliberate and luxurious; dark",
}

# Deterministic keyword → DNA fallback (checked in order; first hit wins).
_KEYWORD_DNA: List[tuple] = [
    (("neon", "retro", "pasar malam", "24 jam", "24 hours", "malam", "night"), "pasar_malam_neon"),
    (("kopitiam", "nostalgia", "vintage", "old school", "old town", "zaman dulu", "klasik"), "kopitiam_nostalgia"),
    (("fine dining", "degustasi", "degustation", "mewah", "premium", "eksklusif", "atas", "luxury", "elegan", "elegant"), "fine_dining_obsidian"),
    (("minimalis", "minimalist", "white space", "bersih", "clean", "simple", "tenang", "calm"), "sutera_putih"),
    (("katering", "catering", "kenduri", "majlis", "wedding", "perkahwinan", "grand"), "warisan_emas"),
    (("kampung", "warung", "tradisional", "traditional", "warisan", "heritage"), "kampung_serene"),
    (("seafood", "ikan bakar", "pantai", "laut"), "ombak_biru"),
    (("street food", "food truck", "gerai", "burger"), "streetfood_bold"),
    (("kopi", "coffee", "cafe", "kafe", "espresso"), "kopi_hitam"),
    (("pedas", "sambal", "spicy", "berapi"), "sambal_berani"),
    (("sihat", "healthy", "vegan", "salad"), "pandan_fresh"),
]

_DEFAULT_DNA = "teh_tarik_warm"


class DesignIntent(BaseModel):
    """Structured design intent distilled from the user's own words."""
    mood_words: List[str] = Field(default_factory=list)
    style_direction: str = ""
    audience: str = ""
    era: Optional[str] = None
    color_hints: List[str] = Field(default_factory=list)
    voice: Literal["casual", "neutral", "formal"] = "neutral"
    recommended_style_dna: Optional[str] = None
    source: Literal["llm", "fallback"] = "llm"


def keyword_intent(description: str) -> DesignIntent:
    """Deterministic fallback: keyword-scan the description."""
    lowered = description.lower()
    dna = _DEFAULT_DNA
    for keywords, candidate in _KEYWORD_DNA:
        if any(k in lowered for k in keywords):
            dna = candidate
            break
    mood = [k for keywords, _ in _KEYWORD_DNA for k in keywords if k in lowered]
    return DesignIntent(
        mood_words=mood[:6],
        style_direction="",
        recommended_style_dna=dna,
        source="fallback",
    )


def _build_prompt(description: str, language: str, business_name: str) -> str:
    rubric = "\n".join(f"- {key}: {vibe}" for key, vibe in DNA_RUBRIC.items())
    return f"""Analyze this Malaysian F&B business description and extract the DESIGN INTENT.
Preserve the user's own aesthetic words — do not normalize them away.

BUSINESS NAME: {business_name}
DESCRIPTION: {description}
SITE LANGUAGE: {"Bahasa Malaysia" if language == "ms" else "English"}

Available style DNAs (pick the single best match for recommended_style_dna):
{rubric}

Return ONLY a JSON object:
{{
  "mood_words": ["up to 6 aesthetic/mood words the user used or clearly implied"],
  "style_direction": "one sentence describing the visual direction in the user's spirit",
  "audience": "who the customers are, in a few words",
  "era": "a period reference if any (e.g. '1960s kopitiam', '90s retro'), else null",
  "color_hints": ["colors the user mentioned or that are strongly implied, as words"],
  "voice": "casual | neutral | formal — the copy voice that suits this business",
  "recommended_style_dna": "one key from the list above"
}}"""


async def extract_intent(
    description: str,
    language: str = "ms",
    business_name: str = "",
) -> DesignIntent:
    """Extract intent via LLM; degrade to keyword fallback on ANY failure."""
    try:
        raw = await call_deepseek_json(
            _build_prompt(description, language, business_name),
            system="You are a design director for Malaysian F&B websites. You extract intent; you never invent facts.",
            temperature=0.3,
            max_tokens=600,
        )
        if raw.get("recommended_style_dna") not in STYLE_DNAS:
            raw["recommended_style_dna"] = keyword_intent(description).recommended_style_dna
        if raw.get("voice") not in ("casual", "neutral", "formal"):
            raw["voice"] = "neutral"
        intent = DesignIntent(**{**raw, "source": "llm"})
        logger.info(
            "🎯 intent extracted: dna=%s mood=%s",
            intent.recommended_style_dna, intent.mood_words,
        )
        return intent
    except (LLMJSONError, ValidationError, TypeError) as exc:
        logger.warning("intent extraction failed (%s) — using keyword fallback", exc)
        return keyword_intent(description)
