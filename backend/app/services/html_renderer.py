"""
V2 HTML Renderer — converts a PageRecipe into a complete HTML page.

This is the final stage of the pipeline. It is deterministic (no AI).
Each component has an HTML template method that produces its markup.
The renderer stitches them together with the nav, theme CSS, and scripts.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List

from app.schemas.recipe import PageRecipe, RenderedSection, NavConfig, ThemeTokens


def render_html(recipe: PageRecipe) -> str:
    """Render a PageRecipe into a complete, self-contained HTML string."""
    css_vars = _theme_to_css(recipe.theme)
    tw_config_script = _tailwind_config_script(recipe)
    head_links = _head_links(recipe)
    nav_html = _render_nav(recipe.nav, recipe.theme)
    sections_html = "\n\n".join(
        _render_section(s) for s in recipe.sections
    )
    body_scripts = _body_scripts(recipe)

    return f"""<!DOCTYPE html>
<html lang="{recipe.meta.language}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{_esc(recipe.meta.title)}</title>
    <meta name="description" content="{_esc(recipe.meta.description)}">
    {f'<meta property="og:image" content="{_esc(recipe.meta.og_image)}">' if recipe.meta.og_image else ''}
    {head_links}
    {tw_config_script}
    <style>
{css_vars}
    </style>
</head>
<body class="antialiased">

{nav_html}

<!-- Spacer for fixed nav -->
<div style="height: 72px;"></div>

{sections_html}

{body_scripts}
</body>
</html>"""


# ---------------------------------------------------------------------------
# Theme → CSS custom properties
# ---------------------------------------------------------------------------

def _theme_to_css(theme: ThemeTokens) -> str:
    c = theme.colors
    f = theme.fonts
    t = theme.tokens
    return f"""        :root {{
            --color-primary: {c.primary};
            --color-primary-hover: {c.primary_hover};
            --color-secondary: {c.secondary};
            --color-accent: {c.accent};
            --color-background: {c.background};
            --color-surface: {c.surface};
            --color-text: {c.text};
            --color-text-muted: {c.text_muted};
            --color-border: {c.border};
            --color-gradient-from: {c.gradient_from};
            --color-gradient-to: {c.gradient_to};
            --font-heading: '{f.heading}', serif;
            --font-body: '{f.body}', sans-serif;
            --radius-sm: {t.border_radius_sm};
            --radius-md: {t.border_radius_md};
            --radius-lg: {t.border_radius_lg};
            --shadow: {t.shadow};
            --shadow-lg: {t.shadow_lg};
            --spacing-section: {t.spacing_section};
            --max-width: {t.max_width};
        }}
        html {{ scroll-behavior: smooth; }}
        body {{
            background-color: var(--color-background);
            color: var(--color-text);
            font-family: var(--font-body);
            margin: 0;
        }}
        h1, h2, h3, h4, h5, h6 {{
            font-family: var(--font-heading);
        }}"""


# ---------------------------------------------------------------------------
# Head assets
# ---------------------------------------------------------------------------

def _head_links(recipe: PageRecipe) -> str:
    lines = []
    for url in recipe.head_assets:
        if url.endswith(".css"):
            lines.append(f'    <link rel="stylesheet" href="{url}">')
        elif url.endswith(".js") or "tailwindcss" in url:
            lines.append(f'    <script src="{url}"></script>')
        else:
            # Google Fonts or unknown — treat as stylesheet
            lines.append(f'    <link rel="stylesheet" href="{url}">')
    return "\n".join(lines)


def _tailwind_config_script(recipe: PageRecipe) -> str:
    if not recipe.tailwind_config:
        return ""
    config = json.dumps(recipe.tailwind_config.theme, indent=2)
    return f"""    <script>
    tailwind.config = {{ theme: {config} }};
    </script>"""


# ---------------------------------------------------------------------------
# Nav
# ---------------------------------------------------------------------------

def _render_nav(nav: NavConfig, theme: ThemeTokens) -> str:
    links_html = ""
    for link in nav.links:
        links_html += f'        <a href="{_esc(link.href)}" class="text-sm font-medium hover:opacity-80 transition-opacity" style="color: var(--color-text);">{_esc(link.label)}</a>\n'

    cta_html = ""
    if nav.cta:
        cta_html = f"""        <a href="{_esc(nav.cta.href)}" target="_blank" rel="noopener noreferrer"
           class="text-sm font-semibold text-white rounded-xl px-5 py-2.5 transition-colors duration-200"
           style="background-color: var(--color-primary);">
            {_esc(nav.cta.label)}
        </a>"""

    return f"""<nav class="{theme.component_styles.nav}" style="transition: all 0.3s;">
    <div class="mx-auto flex items-center justify-between py-4 px-4 sm:px-6 lg:px-8" style="max-width: var(--max-width, 1280px);">
        <a href="#hero" class="text-xl font-bold" style="font-family: var(--font-heading); color: var(--color-text);">
            {_esc(nav.logo_text)}
        </a>
        <div class="hidden md:flex items-center gap-8">
{links_html}
{cta_html}
        </div>
        <button class="md:hidden p-2" onclick="document.getElementById('mobile-menu').classList.toggle('hidden')" aria-label="Menu">
            <i class="fa-solid fa-bars text-xl" style="color: var(--color-text);"></i>
        </button>
    </div>
    <div id="mobile-menu" class="hidden md:hidden px-4 pb-4 space-y-3">
{links_html.replace('hidden md:flex', 'flex flex-col')}
{cta_html}
    </div>
</nav>"""


# ---------------------------------------------------------------------------
# Section rendering — maps component name → HTML template function
# ---------------------------------------------------------------------------

COMPONENT_RENDERERS = {}


def _component(name: str):
    def decorator(fn):
        COMPONENT_RENDERERS[name] = fn
        return fn
    return decorator


def _render_section(section: RenderedSection) -> str:
    renderer = COMPONENT_RENDERERS.get(section.component)
    if not renderer:
        return f'<!-- Unknown component: {section.component} -->'

    inner = renderer(section.props)
    aos_attr = f'data-aos="{section.animation.type}"'
    delay_attr = f'data-aos-delay="{section.animation.delay}"' if section.animation.delay else ""

    # Hero gets no extra padding (it manages its own)
    if section.id == "hero":
        return f'<div id="{section.id}" {aos_attr} {delay_attr}>\n{inner}\n</div>'

    # Footer gets no section wrapper padding either
    if section.id == "footer":
        return f'<div id="{section.id}" {aos_attr} {delay_attr}>\n{inner}\n</div>'

    return f"""<section id="{section.id}" class="py-20 px-4 sm:px-6 lg:px-8" {aos_attr} {delay_attr}>
    <div class="mx-auto" style="max-width: var(--max-width, 1280px);">
{inner}
    </div>
</section>"""


# ---------------------------------------------------------------------------
# Component templates
# ---------------------------------------------------------------------------

@_component("HeroSplit")
def _hero_split(p: Dict[str, Any]) -> str:
    img_html = ""
    if p.get("image_url"):
        img_html = f"""        <div class="flex items-center justify-center py-8 lg:py-0">
            <img src="{_esc(p['image_url'])}" alt="{_esc(p.get('image_alt', ''))}"
                 class="w-full max-w-lg lg:max-w-none rounded-3xl object-cover"
                 style="max-height: 550px; box-shadow: var(--shadow-lg);" loading="eager">
        </div>"""
    else:
        img_html = """        <div class="flex items-center justify-center py-8 lg:py-0">
            <div class="w-full max-w-lg lg:max-w-none rounded-3xl flex items-center justify-center"
                 style="height: 400px; background: linear-gradient(135deg, var(--color-primary), var(--color-secondary));">
                <i class="fa-solid fa-utensils text-6xl text-white/30"></i>
            </div>
        </div>"""

    cta2 = ""
    if p.get("cta_secondary_text") and p.get("cta_secondary_link"):
        cta2 = f"""            <a href="{_esc(p['cta_secondary_link'])}"
               class="inline-block border-2 border-[var(--color-primary)] text-[var(--color-primary)] hover:bg-[var(--color-primary)] hover:text-white font-semibold rounded-2xl px-7 py-3.5 transition-colors duration-200">
                {_esc(p['cta_secondary_text'])}
            </a>"""

    pos = p.get("image_position", "right")
    order = "lg:order-last" if pos == "left" else ""

    return f"""    <div class="min-h-[80vh] flex items-center" style="background-color: var(--color-background);">
        <div class="mx-auto w-full px-4 sm:px-6 lg:px-8" style="max-width: var(--max-width, 1280px);">
            <div class="grid grid-cols-1 lg:grid-cols-2 gap-8 lg:gap-16 items-center">
                <div class="flex flex-col justify-center py-12 lg:py-20 {order}">
                    <h1 class="text-4xl sm:text-5xl lg:text-6xl font-bold leading-tight"
                        style="font-family: var(--font-heading); color: var(--color-text);">
                        {_esc(p['headline'])}
                    </h1>
                    <p class="mt-6 text-lg sm:text-xl leading-relaxed max-w-lg"
                       style="color: var(--color-text-muted);">
                        {_esc(p['subheadline'])}
                    </p>
                    <div class="mt-8 flex flex-wrap gap-4">
                        <a href="{_esc(p['cta_link'])}"
                           class="inline-block bg-[var(--color-primary)] hover:bg-[var(--color-primary-hover)] text-white font-semibold rounded-2xl px-7 py-3.5 transition-colors duration-200">
                            {_esc(p['cta_text'])}
                        </a>
{cta2}
                    </div>
                </div>
{img_html}
            </div>
        </div>
    </div>"""


@_component("AboutStory")
def _about_story(p: Dict[str, Any]) -> str:
    paragraphs = "\n".join(
        f'            <p class="text-base sm:text-lg leading-relaxed" style="color: var(--color-text-muted);">{_esc(para)}</p>'
        for para in p.get("paragraphs", [])
    )

    img_html = ""
    if p.get("image_url"):
        img_html = f"""        <div class="flex items-center justify-center">
            <img src="{_esc(p['image_url'])}" alt="{_esc(p.get('image_alt', ''))}"
                 class="w-full rounded-2xl object-cover"
                 style="max-height: 450px; box-shadow: var(--shadow-lg);" loading="lazy">
        </div>"""

    pos = p.get("image_position", "left")
    cells = [img_html, f"""        <div class="flex flex-col justify-center">
            <h2 class="text-3xl sm:text-4xl font-bold" style="font-family: var(--font-heading); color: var(--color-text);">
                {_esc(p['heading'])}
            </h2>
            <div class="mt-6 space-y-4">
{paragraphs}
            </div>
        </div>"""]

    if pos == "right":
        cells = list(reversed(cells))

    return f"""        <div class="grid grid-cols-1 lg:grid-cols-2 gap-12 lg:gap-16 items-center">
{cells[0]}
{cells[1]}
        </div>"""


@_component("MenuGrid")
def _menu_grid(p: Dict[str, Any]) -> str:
    subheading = ""
    if p.get("subheading"):
        subheading = f'        <p class="mt-3 text-lg" style="color: var(--color-text-muted);">{_esc(p["subheading"])}</p>'

    cards = []
    for item in p.get("items", []):
        badge_html = ""
        if item.get("badge"):
            badge_html = f"""                    <span class="absolute top-3 right-3 text-white text-xs font-bold px-3 py-1 rounded-full"
                          style="background-color: var(--color-primary);">{_esc(item['badge'])}</span>"""

        if item.get("image_url"):
            img = f"""            <div class="relative">
                <img src="{_esc(item['image_url'])}" alt="{_esc(item['name'])}"
                     class="w-full h-48 object-cover" loading="lazy">
{badge_html}
            </div>"""
        else:
            img = f"""            <div class="relative w-full h-48 flex items-center justify-center"
                 style="background: linear-gradient(135deg, var(--color-primary), var(--color-secondary));">
                <i class="fa-solid fa-bowl-food text-4xl text-white/40"></i>
{badge_html}
            </div>"""

        cards.append(f"""        <div class="rounded-2xl overflow-hidden transition-shadow duration-200 hover:shadow-lg"
             style="background-color: var(--color-surface); box-shadow: var(--shadow);">
{img}
            <div class="p-5">
                <div class="flex items-start justify-between gap-3">
                    <h3 class="text-lg font-semibold" style="font-family: var(--font-heading); color: var(--color-text);">
                        {_esc(item['name'])}
                    </h3>
                    <span class="text-sm font-bold whitespace-nowrap" style="color: var(--color-primary);">
                        {_esc(item['price'])}
                    </span>
                </div>
                <p class="mt-2 text-sm leading-relaxed" style="color: var(--color-text-muted);">
                    {_esc(item['description'])}
                </p>
            </div>
        </div>""")

    return f"""        <div class="text-center mb-12">
            <h2 class="text-3xl sm:text-4xl font-bold" style="font-family: var(--font-heading); color: var(--color-text);">
                {_esc(p['heading'])}
            </h2>
{subheading}
        </div>
        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
{chr(10).join(cards)}
        </div>"""


@_component("GalleryMasonry")
def _gallery_masonry(p: Dict[str, Any]) -> str:
    images = "\n".join(
        f"""            <div class="mb-4 break-inside-avoid overflow-hidden rounded-2xl">
                <img src="{_esc(img['url'])}" alt="{_esc(img['alt'])}"
                     class="w-full object-cover hover:scale-105 transition-transform duration-300" loading="lazy">
            </div>"""
        for img in p.get("images", [])
    )

    return f"""        <h2 class="text-3xl sm:text-4xl font-bold text-center mb-12"
            style="font-family: var(--font-heading); color: var(--color-text);">
            {_esc(p['heading'])}
        </h2>
        <style>
            .v2-masonry {{ column-count: 1; column-gap: 1rem; }}
            @media (min-width: 640px) {{ .v2-masonry {{ column-count: 2; }} }}
            @media (min-width: 1024px) {{ .v2-masonry {{ column-count: 3; }} }}
        </style>
        <div class="v2-masonry">
{images}
        </div>"""


@_component("TestimonialCards")
def _testimonial_cards(p: Dict[str, Any]) -> str:
    cards = []
    for r in p.get("reviews", []):
        stars = "".join(
            f'<i class="fa-{"solid" if i < r.get("rating", 5) else "regular"} fa-star text-sm" style="color: {"#F59E0B" if i < r.get("rating", 5) else "var(--color-text-muted)"};"></i>'
            for i in range(5)
        )
        initial = r.get("avatar_fallback", r.get("name", "?")[0].upper())
        cards.append(f"""        <div class="p-6 rounded-2xl" style="background-color: var(--color-surface); box-shadow: var(--shadow);">
            <div class="flex gap-1">{stars}</div>
            <p class="mt-4 text-base leading-relaxed italic" style="color: var(--color-text-muted);">
                &ldquo;{_esc(r['text'])}&rdquo;
            </p>
            <div class="mt-6 flex items-center gap-3">
                <div class="w-10 h-10 rounded-full flex items-center justify-center text-sm font-bold text-white"
                     style="background-color: var(--color-primary);">{initial}</div>
                <span class="text-sm font-semibold" style="color: var(--color-text);">{_esc(r['name'])}</span>
            </div>
        </div>""")

    return f"""        <h2 class="text-3xl sm:text-4xl font-bold text-center mb-12"
            style="font-family: var(--font-heading); color: var(--color-text);">
            {_esc(p['heading'])}
        </h2>
        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
{chr(10).join(cards)}
        </div>"""


@_component("ContactSplit")
def _contact_split(p: Dict[str, Any]) -> str:
    items = []
    if p.get("whatsapp_number"):
        items.append(f"""            <a href="https://wa.me/{_esc(p['whatsapp_number'])}" target="_blank" rel="noopener noreferrer"
               class="inline-flex items-center gap-3 text-white font-semibold rounded-2xl px-7 py-3.5 transition-colors duration-200"
               style="background-color: #25D366;">
                <i class="fa-brands fa-whatsapp text-xl"></i>
                {_esc(p.get('whatsapp_cta', 'WhatsApp'))}
            </a>""")

    if p.get("address"):
        items.append(f"""            <div class="flex items-start gap-3">
                <i class="fa-solid fa-location-dot mt-1" style="color: var(--color-primary);"></i>
                <p style="color: var(--color-text-muted);">{_esc(p['address'])}</p>
            </div>""")

    if p.get("hours"):
        items.append(f"""            <div class="flex items-start gap-3">
                <i class="fa-solid fa-clock mt-1" style="color: var(--color-primary);"></i>
                <p style="color: var(--color-text-muted);">{_esc(p['hours'])}</p>
            </div>""")

    if p.get("email"):
        items.append(f"""            <div class="flex items-start gap-3">
                <i class="fa-solid fa-envelope mt-1" style="color: var(--color-primary);"></i>
                <a href="mailto:{_esc(p['email'])}" class="hover:underline" style="color: var(--color-text-muted);">{_esc(p['email'])}</a>
            </div>""")

    map_html = ""
    if p.get("show_map") and (p.get("map_query") or p.get("address")):
        query = p.get("map_query") or p.get("address", "")
        map_html = f"""        <div class="rounded-2xl overflow-hidden" style="box-shadow: var(--shadow-lg);">
            <iframe src="https://maps.google.com/maps?q={_esc(query)}&output=embed"
                    width="100%" height="350" style="border:0;" allowfullscreen loading="lazy"
                    referrerpolicy="no-referrer-when-downgrade" title="Location map"></iframe>
        </div>"""
    else:
        map_html = """        <div class="rounded-2xl flex items-center justify-center"
             style="height: 350px; background-color: var(--color-surface); box-shadow: var(--shadow);">
            <i class="fa-solid fa-map text-5xl" style="color: var(--color-text-muted); opacity: 0.3;"></i>
        </div>"""

    return f"""        <div class="grid grid-cols-1 lg:grid-cols-2 gap-12 lg:gap-16 items-start">
            <div>
                <h2 class="text-3xl sm:text-4xl font-bold" style="font-family: var(--font-heading); color: var(--color-text);">
                    {_esc(p['heading'])}
                </h2>
                <div class="mt-8 space-y-6">
{chr(10).join(items)}
                </div>
            </div>
{map_html}
        </div>"""


@_component("FooterBrand")
def _footer_brand(p: Dict[str, Any]) -> str:
    year = p.get("copyright_year", 2026)

    social_html = ""
    if p.get("social_links"):
        icons = "\n".join(
            f'                <a href="{_esc(link["url"])}" target="_blank" rel="noopener noreferrer"'
            f' class="w-10 h-10 rounded-full flex items-center justify-center transition-opacity duration-200 hover:opacity-80"'
            f' style="background-color: var(--color-primary);" aria-label="{_esc(link["platform"])}">'
            f'<i class="{_esc(link["icon"])} text-white"></i></a>'
            for link in p["social_links"]
        )
        social_html = f"""            <div class="flex gap-4">
{icons}
            </div>"""

    wa_html = ""
    if p.get("whatsapp_number"):
        wa_html = f"""            <a href="https://wa.me/{_esc(p['whatsapp_number'])}" target="_blank" rel="noopener noreferrer"
               class="inline-flex items-center gap-2 text-sm opacity-80 hover:opacity-100 transition-opacity">
                <i class="fa-brands fa-whatsapp"></i> +{_esc(p['whatsapp_number'])}
            </a>"""

    powered = ""
    if p.get("powered_by", True):
        powered = '            <p>Dibina dengan <a href="https://binaapp.my" target="_blank" rel="noopener noreferrer" class="underline hover:opacity-100">BinaApp</a></p>'

    tagline_html = ""
    if p.get("tagline"):
        tagline_html = f'                <p class="mt-1 text-sm opacity-70">{_esc(p["tagline"])}</p>'

    return f"""    <footer class="py-12 px-4 sm:px-6 lg:px-8" style="background-color: var(--color-text); color: var(--color-background);">
        <div class="mx-auto" style="max-width: var(--max-width, 1280px);">
            <div class="flex flex-col items-center text-center gap-6">
                <div>
                    <h3 class="text-2xl font-bold" style="font-family: var(--font-heading);">
                        {_esc(p['business_name'])}
                    </h3>
{tagline_html}
                </div>
{social_html}
{wa_html}
                <hr class="w-full max-w-xs opacity-20">
                <div class="text-xs opacity-60 space-y-1">
                    <p>&copy; {year} {_esc(p['business_name'])}</p>
{powered}
                </div>
            </div>
        </div>
    </footer>"""


# ---------------------------------------------------------------------------
# Body scripts
# ---------------------------------------------------------------------------

def _body_scripts(recipe: PageRecipe) -> str:
    lines = []
    for url in recipe.body_scripts:
        lines.append(f'<script src="{url}"></script>')
    for code in recipe.init_scripts:
        lines.append(f"<script>{code}</script>")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _esc(text: Any) -> str:
    """Basic HTML escaping for user content."""
    if text is None:
        return ""
    s = str(text)
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
