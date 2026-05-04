"""
V2 Recipe Builder — Stage 2 (deterministic, no AI).

Converts a DesignBrief into a PageRecipe by:
  1. Resolving style_dna → full ThemeTokens
  2. Resolving image_key references → actual URLs
  3. Resolving section type + variant → component names
  4. Building nav links from sections
  5. Generating page meta from business info
"""

from __future__ import annotations

import hashlib
from typing import Any, Dict, List

from app.data.malaysian_food_images import build_image_map as build_cuisine_image_map

from app.schemas.recipe import (
    AnimationConfig,
    ColorTokens,
    ComponentStyles,
    DesignBrief,
    DesignTokens,
    FontTokens,
    NavConfig,
    NavCTA,
    NavLink,
    PageMeta,
    PageRecipe,
    RenderedSection,
    TailwindConfig,
    ThemeTokens,
    resolve_component_name,
)
from app.schemas.style_dna import get_style_dna, StyleDNADef


# Section type → nav label (Bahasa / English)
NAV_LABELS = {
    "ms": {
        "hero": "Laman Utama",
        "about": "Tentang",
        "menu": "Menu",
        "gallery": "Galeri",
        "testimonial": "Testimoni",
        "contact": "Hubungi",
        "hours": "Waktu",
        "cta": None,  # CTA sections don't appear in nav
    },
    "en": {
        "hero": "Home",
        "about": "About",
        "menu": "Menu",
        "gallery": "Gallery",
        "testimonial": "Testimonials",
        "contact": "Contact",
        "hours": "Hours",
        "cta": None,
    },
}


def build_recipe(brief: DesignBrief) -> PageRecipe:
    """Convert a validated DesignBrief into a fully-resolved PageRecipe."""
    # If cuisine_type is set and image_map is sparse, auto-fill from cuisine pool
    if brief.cuisine_type and not brief.image_map.get("hero"):
        cuisine_images = build_cuisine_image_map(
            brief.cuisine_type.value,
            gallery_count=4,
            menu_count=3,
            seed=int(hashlib.md5(brief.business.name.encode()).hexdigest()[:8], 16) % 10000,
        )
        # Merge: explicit image_map entries take priority over cuisine pool
        merged = {**cuisine_images, **brief.image_map}
        brief = brief.model_copy(update={"image_map": merged})

    dna = get_style_dna(brief.style_dna.value)

    theme = _build_theme(dna)
    meta = _build_meta(brief)
    nav = _build_nav(brief)
    sections = _build_sections(brief)

    return PageRecipe(
        **{"$schema": "page_recipe_v1"},
        version="1.0",
        meta=meta,
        theme=theme,
        nav=nav,
        sections=sections,
        head_assets=[
            dna.font_cdn,
            "https://unpkg.com/aos@2.3.4/dist/aos.css",
            "https://cdn.tailwindcss.com",
            "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css",
        ],
        tailwind_config=TailwindConfig(theme={
            "extend": {
                "colors": {
                    "primary": "var(--color-primary)",
                    "secondary": "var(--color-secondary)",
                    "accent": "var(--color-accent)",
                    "surface": "var(--color-surface)",
                },
                "fontFamily": {
                    "heading": [dna.heading_font, "serif"],
                    "body": [dna.body_font, "sans-serif"],
                },
            }
        }),
        body_scripts=["https://unpkg.com/aos@2.3.4/dist/aos.js"],
        init_scripts=["AOS.init({ duration: 800, once: true, offset: 100 });"],
    )


def _build_theme(dna: StyleDNADef) -> ThemeTokens:
    return ThemeTokens(
        style_dna=dna.key,
        fonts=FontTokens(
            heading=dna.heading_font,
            heading_weight=dna.heading_weight,
            body=dna.body_font,
            body_weight=dna.body_weight,
            cdn_url=dna.font_cdn,
        ),
        colors=ColorTokens(
            primary=dna.primary,
            primary_hover=dna.primary_hover,
            secondary=dna.secondary,
            accent=dna.accent,
            background=dna.background,
            surface=dna.surface,
            text=dna.text,
            text_muted=dna.text_muted,
            border=dna.border,
            gradient_from=dna.gradient_from,
            gradient_to=dna.gradient_to,
        ),
        tokens=DesignTokens(
            shadow=dna.shadow,
            shadow_lg=dna.shadow_lg,
        ),
        component_styles=ComponentStyles(
            button_primary=dna.button_primary,
            button_secondary=dna.button_secondary,
            card=dna.card,
            nav=dna.nav,
        ),
    )


def _build_meta(brief: DesignBrief) -> PageMeta:
    biz = brief.business
    title = f"{biz.name} | {biz.tagline}"
    desc = biz.about[0] if biz.about else biz.tagline
    og = brief.image_map.get("hero")

    return PageMeta(
        title=title[:120],
        description=desc[:300],
        language=brief.language,
        og_image=og,
    )


def _build_nav(brief: DesignBrief) -> NavConfig:
    labels = NAV_LABELS.get(brief.language, NAV_LABELS["en"])
    links = []
    for section in brief.sections:
        label = labels.get(section.type.value)
        if label and section.type.value != "footer":
            links.append(NavLink(label=label, href=f"#{section.type.value}"))

    cta = None
    if brief.features.whatsapp and brief.business.whatsapp:
        cta_label = "Tempah Sekarang" if brief.language == "ms" else "Book Now"
        cta = NavCTA(
            label=cta_label,
            href=f"https://wa.me/{brief.business.whatsapp}",
        )

    return NavConfig(
        logo_text=brief.business.name,
        links=links,
        cta=cta,
    )


def _build_sections(brief: DesignBrief) -> List[RenderedSection]:
    rendered = []
    for i, spec in enumerate(brief.sections):
        component = resolve_component_name(spec.type.value, spec.variant)
        props = _resolve_props(spec.type.value, spec.content, brief)

        rendered.append(RenderedSection(
            id=spec.type.value,
            component=component,
            props=props,
            animation=AnimationConfig(
                type="fade-up",
                delay=0 if i == 0 else 100,
            ),
        ))
    return rendered


def _resolve_props(
    section_type: str,
    content: Dict[str, Any],
    brief: DesignBrief,
) -> Dict[str, Any]:
    """Resolve image_key → image_url, add business context where needed."""
    props: Dict[str, Any] = {}

    for key, val in content.items():
        if key == "image_key" and isinstance(val, str):
            props["image_url"] = brief.image_map.get(val, "")
            props["image_alt"] = brief.business.name
        elif key == "background_image_key" and isinstance(val, str):
            props["background_image_url"] = brief.image_map.get(val, "")
        elif key == "image_keys" and isinstance(val, list):
            props["images"] = [
                {"url": brief.image_map.get(k, ""), "alt": brief.business.name}
                for k in val
            ]
        elif key == "fallback_items" and isinstance(val, list):
            from app.data.malaysian_food_images import get_dish_pool
            import random
            resolved_items = []
            for item in val:
                resolved = {**item}
                ik = resolved.pop("image_key", None)
                dish_name = resolved.get("name", "")
                dish_pool = get_dish_pool(dish_name)
                if dish_pool:
                    # Deterministic pick based on dish name — stable across runs
                    dish_seed = int(hashlib.md5(dish_name.encode()).hexdigest()[:8], 16)
                    rng = random.Random(dish_seed)
                    resolved["image_url"] = rng.choice(dish_pool).url
                elif ik:
                    resolved["image_url"] = brief.image_map.get(ik, "")
                else:
                    resolved["image_url"] = None
                if resolved.get("is_popular"):
                    resolved["badge"] = "Popular"
                    del resolved["is_popular"]
                resolved_items.append(resolved)
            props["items"] = resolved_items
        elif key == "source":
            # "supabase" source marker — skip, handled at render time
            continue
        elif key == "reviews" and isinstance(val, list):
            props["reviews"] = [
                {**r, "avatar_fallback": r.get("avatar_fallback", r.get("name", "?")[0].upper())}
                for r in val
            ]
        else:
            props[key] = val

    # Inject WhatsApp for contact and CTA sections
    if section_type in ("contact", "cta") and brief.business.whatsapp:
        props.setdefault("whatsapp_number", brief.business.whatsapp)

    # Inject business name for footer
    if section_type == "footer":
        props.setdefault("business_name", brief.business.name)

    return props
