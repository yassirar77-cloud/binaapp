"""Assemble a full document from the spec, theme and copy."""

from __future__ import annotations

from typing import List, Optional

from app.services.sections.copy import Copy
from app.services.sections.render import (
    render_about, render_banners, render_coming_soon, render_contact, render_footer, render_hero,
    render_location, render_menu_section, render_nav, render_options_strip,
)
from app.services.sections.spec import SiteSpec
from app.services.sections.theme import Theme, esc, render_css

COMPOSER_MARKER = "binaapp-composer"
COMPOSER_VERSION = "1"

FONT_AWESOME = '<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">'


def section_order(spec: SiteSpec) -> List[str]:
    """Which sections, in which order, for this vertical."""
    order = ["nav", "hero"]
    if spec.is_food:
        order += ["options", "banners", "menu", "coming_soon", "about"]
    else:
        order += ["banners", "menu", "about", "coming_soon"]
    order += ["location", "contact", "footer"]
    return order


def compose_page(spec: SiteSpec, theme: Theme, copy: Copy, *, description: Optional[str] = None) -> str:
    renderers = {
        "nav": lambda: render_nav(spec),
        "hero": lambda: render_hero(spec, copy),
        "options": lambda: render_options_strip(spec),
        "banners": lambda: render_banners(spec),
        "menu": lambda: render_menu_section(spec, copy),
        "coming_soon": lambda: render_coming_soon(spec),
        "about": lambda: render_about(spec, copy),
        "location": lambda: render_location(spec),
        "contact": lambda: render_contact(spec, copy),
        "footer": lambda: render_footer(spec, copy),
    }
    body = "\n".join(renderers[name]() for name in section_order(spec) if renderers[name]())
    meta_desc = (description or copy.subheadline or spec.business_name)[:160]
    lang = "en" if spec.lang == "en" else "ms"
    return (
        f'<!DOCTYPE html>\n<html lang="{lang}">\n<head>\n<meta charset="UTF-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f"<title>{esc(spec.business_name)}</title>\n"
        f'<meta name="description" content="{esc(meta_desc)}">\n'
        f'<meta name="theme-color" content="{esc(theme.primary)}">\n'
        f'<meta name="generator" content="{COMPOSER_MARKER} v{COMPOSER_VERSION}" data-variant="{esc(theme.variant)}">\n'
        '<link rel="preconnect" href="https://fonts.googleapis.com">\n'
        '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
        f'<link href="{esc(theme.fonts_href)}" rel="stylesheet">\n'
        f"{FONT_AWESOME}\n{render_css(theme)}\n</head>\n<body>\n{body}\n</body>\n</html>\n"
    )


def is_composed(html: str) -> bool:
    return bool(html) and COMPOSER_MARKER in html[:4000]
