"""
V2 Component-Recipe Schemas

Two core schemas:
  - DesignBrief: AI output from Stage 1 (structured plan for a website)
  - PageRecipe:  Deterministic input to the HTML assembler (Stage 2)

See docs/V2_ARCHITECTURE.md Section 12 for full examples.
"""

from __future__ import annotations

import re
from enum import Enum
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class SectionType(str, Enum):
    hero = "hero"
    about = "about"
    menu = "menu"
    gallery = "gallery"
    testimonial = "testimonial"
    contact = "contact"
    footer = "footer"
    hours = "hours"
    cta = "cta"


class CuisineType(str, Enum):
    mamak = "mamak"
    malay_fusion = "malay_fusion"
    malay_traditional = "malay_traditional"
    fine_dining_malay = "fine_dining_malay"
    kopitiam_chinese = "kopitiam_chinese"
    fast_food_halal = "fast_food_halal"
    warung_kampung = "warung_kampung"
    cafe_modern = "cafe_modern"
    western_halal = "western_halal"
    thai_halal = "thai_halal"
    indian_halal = "indian_halal"
    nyonya = "nyonya"


class StyleDNA(str, Enum):
    teh_tarik_warm = "teh_tarik_warm"
    pandan_fresh = "pandan_fresh"
    kopi_hitam = "kopi_hitam"
    sambal_berani = "sambal_berani"
    sutera_putih = "sutera_putih"
    lampu_neon = "lampu_neon"
    warisan_emas = "warisan_emas"
    ombak_biru = "ombak_biru"


VALID_VARIANTS: Dict[SectionType, List[str]] = {
    SectionType.hero: ["centered", "split", "video", "minimal", "slider", "fullscreen-image", "split-reverse", "asymmetric-card"],
    SectionType.about: ["story", "stats", "timeline", "cards", "minimal"],
    SectionType.menu: ["grid", "cards", "list", "categorized", "featured"],
    SectionType.gallery: ["masonry", "grid", "carousel", "lightbox", "full-width"],
    SectionType.testimonial: ["cards", "slider", "quote", "grid", "minimal"],
    SectionType.contact: ["simple", "form", "map", "split", "cards"],
    SectionType.footer: ["simple", "columns", "cta", "minimal", "brand"],
    SectionType.hours: ["simple-table", "today-focus"],
    SectionType.cta: ["booking-prominent", "whatsapp-first"],
}

# Component name = SectionType title + Variant title, e.g. "HeroSplit"
VARIANT_TO_COMPONENT: Dict[str, str] = {}
for _sec_type, _variants in VALID_VARIANTS.items():
    for _v in _variants:
        _component = _sec_type.value.title() + _v.title().replace("-", "")
        VARIANT_TO_COMPONENT[f"{_sec_type.value}:{_v}"] = _component


def resolve_component_name(section_type: str, variant: str) -> str:
    key = f"{section_type}:{variant}"
    if key not in VARIANT_TO_COMPONENT:
        raise ValueError(f"Unknown variant '{variant}' for section type '{section_type}'")
    return VARIANT_TO_COMPONENT[key]


# ---------------------------------------------------------------------------
# Design Brief (Stage 1 — AI output)
# ---------------------------------------------------------------------------

class SocialMedia(BaseModel):
    instagram: Optional[str] = None
    facebook: Optional[str] = None
    tiktok: Optional[str] = None


class BusinessInfo(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    type: str = Field(..., min_length=1, max_length=50)
    tagline: str = Field(..., min_length=1, max_length=300)
    about: List[str] = Field(..., min_length=1, max_length=5)
    address: Optional[str] = None
    whatsapp: Optional[str] = None
    email: Optional[str] = None
    social_media: Optional[SocialMedia] = None
    operating_hours: Optional[str] = None

    @field_validator("whatsapp")
    @classmethod
    def normalise_whatsapp(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        digits = re.sub(r"\D", "", v)
        if digits.startswith("0"):
            digits = "6" + digits
        elif digits.startswith("1") and len(digits) <= 11:
            digits = "60" + digits
        return digits or None


class SectionContent(BaseModel):
    """Flexible content bag — validated per section type at the component level."""
    model_config = {"extra": "allow"}


class SectionSpec(BaseModel):
    type: SectionType
    variant: str
    content: Dict[str, Any]

    @model_validator(mode="after")
    def check_variant_valid(self) -> "SectionSpec":
        allowed = VALID_VARIANTS.get(self.type, [])
        if self.variant not in allowed:
            raise ValueError(
                f"Variant '{self.variant}' invalid for section '{self.type.value}'. "
                f"Allowed: {allowed}"
            )
        return self


class FeatureFlags(BaseModel):
    whatsapp: bool = True
    google_map: bool = False
    delivery_system: bool = False
    gallery: bool = True
    price_list: bool = True
    operating_hours: bool = True
    testimonials: bool = False
    social_media: bool = False


class DesignBrief(BaseModel):
    schema_id: str = Field("design_brief_v1", alias="$schema")
    version: str = "1.0"
    language: Literal["ms", "en"] = "ms"

    business: BusinessInfo
    style_dna: StyleDNA
    color_mode: Literal["light", "dark"] = "light"

    cuisine_type: Optional[CuisineType] = None
    specific_dishes: List[str] = Field(default_factory=list)

    sections: List[SectionSpec] = Field(..., min_length=2, max_length=10)
    image_map: Dict[str, str] = Field(default_factory=dict)
    features: FeatureFlags = Field(default_factory=FeatureFlags)

    @field_validator("sections")
    @classmethod
    def must_have_hero_and_footer(cls, v: List[SectionSpec]) -> List[SectionSpec]:
        types = {s.type for s in v}
        if SectionType.hero not in types:
            raise ValueError("Sections must include a 'hero' section")
        if SectionType.footer not in types:
            raise ValueError("Sections must include a 'footer' section")
        return v

    @model_validator(mode="after")
    def image_keys_must_resolve(self) -> "DesignBrief":
        """Every image_key referenced in section content must exist in image_map."""
        available = set(self.image_map.keys())
        if not available:
            return self  # no images mode
        for section in self.sections:
            content = section.content
            # Check single image_key
            key = content.get("image_key")
            if key and key not in available:
                raise ValueError(
                    f"Section '{section.type.value}' references image_key '{key}' "
                    f"not found in image_map. Available: {sorted(available)}"
                )
            # Check image_keys list
            for k in content.get("image_keys", []):
                if k not in available:
                    raise ValueError(
                        f"Section '{section.type.value}' references image_key '{k}' "
                        f"not found in image_map. Available: {sorted(available)}"
                    )
            # Check fallback_items with image_key
            for item in content.get("fallback_items", []):
                ik = item.get("image_key")
                if ik and ik not in available:
                    raise ValueError(
                        f"Menu item '{item.get('name', '?')}' references image_key "
                        f"'{ik}' not found in image_map."
                    )
        return self

    model_config = {"populate_by_name": True}


# ---------------------------------------------------------------------------
# Page Recipe (Stage 2 — assembler input, deterministically derived)
# ---------------------------------------------------------------------------

class PageMeta(BaseModel):
    title: str
    description: str
    language: Literal["ms", "en"] = "ms"
    favicon: Optional[str] = None
    og_image: Optional[str] = None


class FontTokens(BaseModel):
    heading: str
    heading_weight: str = "700"
    body: str
    body_weight: str = "400"
    cdn_url: str


class ColorTokens(BaseModel):
    primary: str
    primary_hover: str
    secondary: str
    accent: str
    background: str
    surface: str
    text: str
    text_muted: str
    border: str
    gradient_from: str
    gradient_to: str


class DesignTokens(BaseModel):
    border_radius_sm: str = "0.75rem"
    border_radius_md: str = "1rem"
    border_radius_lg: str = "1.5rem"
    shadow: str = "0 4px 6px -1px rgba(0,0,0,0.07), 0 2px 4px -2px rgba(0,0,0,0.05)"
    shadow_lg: str = "0 10px 15px -3px rgba(0,0,0,0.08), 0 4px 6px -4px rgba(0,0,0,0.04)"
    spacing_section: str = "5rem"
    max_width: str = "1280px"


class ComponentStyles(BaseModel):
    button_primary: str
    button_secondary: str
    card: str
    nav: str
    section_padding: str = "py-20 px-4 sm:px-6 lg:px-8"


class ThemeTokens(BaseModel):
    style_dna: StyleDNA
    fonts: FontTokens
    colors: ColorTokens
    tokens: DesignTokens = Field(default_factory=DesignTokens)
    component_styles: ComponentStyles


class NavLink(BaseModel):
    label: str
    href: str


class NavCTA(BaseModel):
    label: str
    href: str


class NavConfig(BaseModel):
    logo_text: str
    links: List[NavLink] = Field(default_factory=list)
    cta: Optional[NavCTA] = None


class AnimationConfig(BaseModel):
    type: str = "fade-up"
    delay: int = 0


class RenderedSection(BaseModel):
    id: str
    component: str
    props: Dict[str, Any]
    animation: AnimationConfig = Field(default_factory=AnimationConfig)


class TailwindConfig(BaseModel):
    theme: Dict[str, Any]


class PageRecipe(BaseModel):
    schema_id: str = Field("page_recipe_v1", alias="$schema")
    version: str = "1.0"

    meta: PageMeta
    theme: ThemeTokens
    nav: NavConfig
    sections: List[RenderedSection] = Field(..., min_length=2)

    head_assets: List[str] = Field(default_factory=list)
    tailwind_config: Optional[TailwindConfig] = None
    body_scripts: List[str] = Field(default_factory=list)
    init_scripts: List[str] = Field(default_factory=list)

    model_config = {"populate_by_name": True}
