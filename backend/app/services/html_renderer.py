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
            line-height: 1.7;
        }}
        h1, h2, h3, h4, h5, h6 {{
            font-family: var(--font-heading);
            line-height: 1.1;
        }}
        /* Scroll-triggered fade-in */
        [data-aos="fade-up"] {{
            transition-timing-function: cubic-bezier(0.22, 1, 0.36, 1);
        }}
        /* Subtle image frame */
        .img-frame {{
            position: relative;
        }}
        .img-frame::after {{
            content: '';
            position: absolute;
            inset: -8px;
            border: 1px solid var(--color-border);
            border-radius: inherit;
            pointer-events: none;
        }}
        /* Menu card hover */
        .menu-card {{
            transition: transform 0.3s cubic-bezier(0.22, 1, 0.36, 1), box-shadow 0.3s ease;
        }}
        .menu-card:hover {{
            transform: translateY(-4px) scale(1.02);
            box-shadow: 0 20px 40px -12px rgba(0,0,0,0.15);
        }}
        /* Testimonial card hover */
        .testimonial-card {{
            transition: transform 0.3s ease, box-shadow 0.3s ease;
        }}
        .testimonial-card:hover {{
            transform: translateY(-2px);
            box-shadow: 0 12px 24px -8px rgba(0,0,0,0.12);
        }}
        /* Accent line */
        .accent-line {{
            width: 48px;
            height: 3px;
            background: linear-gradient(90deg, var(--color-primary), var(--color-accent));
            border-radius: 2px;
        }}
        /* Hide Tailwind CDN play mode badge — nuclear approach for PDF */
        #__tailwind_play__, .tw-play-btn,
        [style*="position: fixed"][style*="z-index: 2147483647"],
        [style*="position: fixed"][style*="z-index: 99999"],
        [style*="position: fixed"][style*="z-index: 999999"],
        [style*="position:fixed"][style*="z-index"] {{
            display: none !important;
            visibility: hidden !important;
            opacity: 0 !important;
            width: 0 !important;
            height: 0 !important;
            overflow: hidden !important;
            pointer-events: none !important;
        }}
        /* Catch-all: any fixed element in the bottom-right quadrant (badges, overlays) */
        [style*="position: fixed"][style*="bottom"][style*="right"] {{
            display: none !important;
            visibility: hidden !important;
        }}
        /* Prevent Google Maps SDK overlay messages */
        .map-container iframe {{
            pointer-events: none;
        }}
        .map-container:hover iframe {{
            pointer-events: auto;
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

    # Vary vertical padding per section for visual rhythm
    padding_map = {
        "about": "py-24 md:py-32",
        "menu": "py-20 md:py-28",
        "gallery": "py-16 md:py-24",
        "testimonial": "py-20 md:py-28",
        "contact": "py-24 md:py-32",
    }
    pad = padding_map.get(section.id, "py-20")

    return f"""<section id="{section.id}" class="{pad} px-4 sm:px-6 lg:px-8" {aos_attr} {delay_attr}>
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
        img_html = f"""        <div class="relative flex items-center justify-center py-8 lg:py-0 lg:-mr-8">
            <div class="relative w-full max-w-lg lg:max-w-none">
                <img src="{_esc(p['image_url'])}" alt="{_esc(p.get('image_alt', ''))}"
                     class="w-full rounded-2xl object-cover relative z-10"
                     style="max-height: 580px; box-shadow: 0 25px 50px -12px rgba(0,0,0,0.2);" loading="eager">
                <div class="absolute inset-0 rounded-2xl z-20 pointer-events-none"
                     style="background: linear-gradient(135deg, var(--color-primary) 0%, transparent 40%); opacity: 0.08;"></div>
                <div class="hidden lg:block absolute -bottom-4 -right-4 w-full h-full rounded-2xl z-0"
                     style="background-color: var(--color-accent); opacity: 0.4;"></div>
            </div>
        </div>"""
    else:
        img_html = """        <div class="flex items-center justify-center py-8 lg:py-0">
            <div class="w-full max-w-lg lg:max-w-none rounded-2xl flex items-center justify-center"
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

    halal_badge = ""
    if p.get("halal_certified"):
        halal_badge = """                    <div class="inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-semibold uppercase tracking-wider mb-6"
                         style="background-color: var(--color-accent); color: var(--color-secondary);">
                        <i class="fa-solid fa-store"></i> Pengusaha Muslim
                    </div>"""

    pos = p.get("image_position", "right")
    order = "lg:order-last" if pos == "left" else ""

    return f"""    <div class="min-h-[85vh] flex items-center" style="background-color: var(--color-background);">
        <div class="mx-auto w-full px-4 sm:px-6 lg:px-8" style="max-width: var(--max-width, 1280px);">
            <div class="grid grid-cols-1 lg:grid-cols-2 gap-8 lg:gap-12 items-center">
                <div class="flex flex-col justify-center py-12 lg:py-24 {order}">
{halal_badge}
                    <h1 class="text-4xl sm:text-5xl md:text-7xl lg:text-8xl font-black tracking-tight sm:tracking-tight"
                        style="font-family: var(--font-heading); color: var(--color-text); line-height: 0.95;">
                        {_esc(p['headline'])}
                    </h1>
                    <p class="mt-8 text-lg sm:text-xl leading-relaxed max-w-md"
                       style="color: var(--color-text-muted);">
                        {_esc(p['subheadline'])}
                    </p>
                    <div class="mt-10 flex flex-wrap gap-4">
                        <a href="{_esc(p['cta_link'])}"
                           class="inline-block bg-[var(--color-primary)] hover:bg-[var(--color-primary-hover)] text-white font-semibold rounded-2xl px-8 py-4 transition-all duration-200 hover:shadow-lg"
                           style="font-size: 1.05rem;">
                            {_esc(p['cta_text'])}
                        </a>
{cta2}
                    </div>
                </div>
{img_html}
            </div>
        </div>
    </div>"""


@_component("HeroCentered")
def _hero_centered(p: Dict[str, Any]) -> str:
    """Full-width centered text over background image with gradient overlay."""
    halal_badge = ""
    if p.get("halal_certified"):
        halal_badge = """            <div class="inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-semibold uppercase tracking-wider mb-6"
                 style="background-color: rgba(255,255,255,0.2); color: #fff; backdrop-filter: blur(4px);">
                <i class="fa-solid fa-store"></i> Pengusaha Muslim
            </div>"""

    cta2 = ""
    if p.get("cta_secondary_text") and p.get("cta_secondary_link"):
        cta2 = f"""                <a href="{_esc(p['cta_secondary_link'])}"
                   class="inline-block border-2 border-white/60 text-white hover:bg-white/20 font-semibold rounded-2xl px-7 py-3.5 transition-all duration-200">
                    {_esc(p['cta_secondary_text'])}
                </a>"""

    bg_img = p.get("image_url", "")
    bg_style = f'background-image: url({_esc(bg_img)});' if bg_img else 'background: linear-gradient(135deg, var(--color-primary), var(--color-secondary));'

    return f"""    <div class="relative min-h-[90vh] flex items-center justify-center overflow-hidden">
        <!-- Background image -->
        <div class="absolute inset-0 bg-cover bg-center" style="{bg_style}"></div>
        <!-- Gradient overlay -->
        <div class="absolute inset-0" style="background: linear-gradient(to top, rgba(0,0,0,0.7) 0%, rgba(0,0,0,0.3) 40%, rgba(0,0,0,0.15) 100%);"></div>
        <!-- Content -->
        <div class="relative z-10 text-center px-4 sm:px-6 lg:px-8 max-w-4xl mx-auto py-20">
{halal_badge}
            <h1 class="text-4xl sm:text-5xl md:text-6xl lg:text-7xl font-black tracking-tight text-white"
                style="font-family: var(--font-heading); line-height: 0.95;">
                {_esc(p['headline'])}
            </h1>
            <p class="mt-6 text-lg sm:text-xl leading-relaxed text-white/80 max-w-2xl mx-auto">
                {_esc(p['subheadline'])}
            </p>
            <div class="mt-10 flex flex-wrap justify-center gap-4">
                <a href="{_esc(p['cta_link'])}"
                   class="inline-block text-white font-semibold rounded-2xl px-8 py-4 transition-all duration-200 hover:shadow-lg hover:brightness-110"
                   style="background-color: var(--color-primary); font-size: 1.05rem;">
                    {_esc(p['cta_text'])}
                </a>
{cta2}
            </div>
        </div>
    </div>"""


@_component("HeroFullscreenImage")
def _hero_fullscreen_image(p: Dict[str, Any]) -> str:
    """100vh hero, dramatic photo, headline bottom-left with backdrop blur card."""
    halal_badge = ""
    if p.get("halal_certified"):
        halal_badge = """                <div class="inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-semibold uppercase tracking-wider mb-4"
                     style="background-color: var(--color-accent); color: var(--color-secondary);">
                    <i class="fa-solid fa-store"></i> Pengusaha Muslim
                </div>"""

    cta2 = ""
    if p.get("cta_secondary_text") and p.get("cta_secondary_link"):
        cta2 = f"""                    <a href="{_esc(p['cta_secondary_link'])}"
                       class="inline-block border-2 border-white/40 text-white hover:bg-white/10 font-semibold rounded-2xl px-7 py-3.5 transition-all duration-200">
                        {_esc(p['cta_secondary_text'])}
                    </a>"""

    bg_img = p.get("image_url", "")
    bg_style = f'background-image: url({_esc(bg_img)});' if bg_img else 'background: linear-gradient(135deg, var(--color-primary), var(--color-secondary));'

    return f"""    <div class="relative h-screen min-h-[600px] max-h-[1000px] overflow-hidden">
        <!-- Full background -->
        <div class="absolute inset-0 bg-cover bg-center" style="{bg_style}"></div>
        <div class="absolute inset-0" style="background: linear-gradient(to top, rgba(0,0,0,0.65) 0%, transparent 50%);"></div>
        <!-- Bottom-left content card -->
        <div class="absolute bottom-0 left-0 right-0 z-10 p-4 sm:p-8 lg:p-12">
            <div class="max-w-2xl rounded-2xl p-8 sm:p-10"
                 style="background: rgba(0,0,0,0.4); backdrop-filter: blur(16px); -webkit-backdrop-filter: blur(16px); border: 1px solid rgba(255,255,255,0.1);">
{halal_badge}
                <h1 class="text-3xl sm:text-4xl md:text-5xl lg:text-6xl font-black tracking-tight text-white"
                    style="font-family: var(--font-heading); line-height: 0.95;">
                    {_esc(p['headline'])}
                </h1>
                <p class="mt-4 text-base sm:text-lg leading-relaxed text-white/70 max-w-lg">
                    {_esc(p['subheadline'])}
                </p>
                <div class="mt-8 flex flex-wrap gap-4">
                    <a href="{_esc(p['cta_link'])}"
                       class="inline-block text-white font-semibold rounded-2xl px-8 py-4 transition-all duration-200 hover:shadow-lg hover:brightness-110"
                       style="background-color: var(--color-primary); font-size: 1.05rem;">
                        {_esc(p['cta_text'])}
                    </a>
{cta2}
                </div>
            </div>
        </div>
    </div>"""


@_component("HeroSplitReverse")
def _hero_split_reverse(p: Dict[str, Any]) -> str:
    """Minimal text hero — huge serif typography on cream, no hero image. Aesop-inspired."""
    cta2 = ""
    if p.get("cta_secondary_text") and p.get("cta_secondary_link"):
        cta2 = f"""                <a href="{_esc(p['cta_secondary_link'])}"
                   class="inline-block border-b-2 font-medium pb-1 transition-colors duration-200"
                   style="border-color: var(--color-primary); color: var(--color-primary);">
                    {_esc(p['cta_secondary_text'])}
                </a>"""

    # Split headline into words for typographic control
    headline = _esc(p['headline'])

    return f"""    <div class="min-h-[90vh] flex items-center" style="background-color: var(--color-background);">
        <div class="mx-auto w-full px-4 sm:px-6 lg:px-8" style="max-width: var(--max-width, 1280px);">
            <div class="max-w-5xl py-20 lg:py-32">
                <!-- Thin accent line -->
                <div class="w-16 mb-10" style="height: 1px; background-color: var(--color-primary);"></div>
                <!-- Massive headline -->
                <h1 class="text-5xl sm:text-6xl md:text-7xl lg:text-[6.5rem] xl:text-[8rem] font-normal tracking-tight"
                    style="font-family: var(--font-heading); color: var(--color-text); line-height: 0.9; font-style: italic;">
                    {headline}
                </h1>
                <!-- Subheadline in a constrained column -->
                <div class="mt-10 lg:mt-14 max-w-md lg:ml-auto lg:mr-24">
                    <p class="text-base sm:text-lg leading-relaxed"
                       style="color: var(--color-text-muted);">
                        {_esc(p['subheadline'])}
                    </p>
                    <div class="mt-8 flex flex-wrap items-center gap-6">
                        <a href="{_esc(p['cta_link'])}"
                           class="inline-block bg-[var(--color-primary)] hover:bg-[var(--color-primary-hover)] text-white font-semibold rounded-full px-8 py-4 transition-all duration-200 hover:shadow-lg"
                           style="font-size: 0.95rem; letter-spacing: 0.03em;">
                            {_esc(p['cta_text'])}
                        </a>
{cta2}
                    </div>
                </div>
            </div>
        </div>
    </div>"""


@_component("HeroAsymmetricCard")
def _hero_asymmetric_card(p: Dict[str, Any]) -> str:
    """White card overlapping a 2x2 image grid — editorial magazine layout.
    Image grid takes ~60% right. Card anchored bottom-left, overlapping the grid."""
    halal_badge = ""
    if p.get("halal_certified"):
        halal_badge = """                    <div class="inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-semibold uppercase tracking-wider mb-4"
                         style="background-color: var(--color-accent); color: var(--color-secondary);">
                        <i class="fa-solid fa-store"></i> Pengusaha Muslim
                    </div>"""

    cta2 = ""
    if p.get("cta_secondary_text") and p.get("cta_secondary_link"):
        cta2 = f"""                        <a href="{_esc(p['cta_secondary_link'])}"
                           class="inline-block border-b-2 font-medium pb-1 transition-colors duration-200"
                           style="border-color: var(--color-primary); color: var(--color-primary);">
                            {_esc(p['cta_secondary_text'])}
                        </a>"""

    bg_img = p.get("image_url", "")

    return f"""    <div class="relative min-h-[90vh] overflow-hidden" style="background-color: var(--color-background);">
        <div class="mx-auto w-full px-4 sm:px-6 lg:px-8 py-12 lg:py-0" style="max-width: var(--max-width, 1280px);">
            <!-- Mobile: stacked. Desktop: image grid right, card overlapping from left -->
            <div class="relative lg:min-h-[85vh] lg:flex lg:items-center">
                <!-- 2x2 Image grid — positioned right, takes ~60% -->
                <div class="lg:absolute lg:right-0 lg:top-[8%] lg:bottom-[8%] lg:w-[58%]">
                    <div class="grid grid-cols-2 gap-2 h-full">
                        <div class="rounded-xl overflow-hidden">
                            <img src="{_esc(bg_img)}" alt="{_esc(p.get('image_alt', ''))}"
                                 class="w-full h-full object-cover" style="min-height: 220px;" loading="eager">
                        </div>
                        <div class="rounded-xl overflow-hidden">
                            <img src="{_esc(bg_img)}" alt=""
                                 class="w-full h-full object-cover object-left" style="min-height: 220px; filter: saturate(1.15);" loading="eager">
                        </div>
                        <div class="rounded-xl overflow-hidden">
                            <img src="{_esc(bg_img)}" alt=""
                                 class="w-full h-full object-cover object-bottom" style="min-height: 220px; filter: brightness(0.95);" loading="eager">
                        </div>
                        <div class="rounded-xl overflow-hidden">
                            <img src="{_esc(bg_img)}" alt=""
                                 class="w-full h-full object-cover object-right" style="min-height: 220px; filter: saturate(0.9) brightness(1.05);" loading="eager">
                        </div>
                    </div>
                </div>
                <!-- Overlapping text card — anchored left, overlaps image grid -->
                <div class="relative z-10 mt-6 lg:mt-0 lg:w-[52%]">
                    <div class="rounded-2xl p-8 sm:p-10 lg:p-12"
                         style="background-color: var(--color-surface); box-shadow: 0 30px 60px -15px rgba(0,0,0,0.2);">
{halal_badge}
                        <h1 class="text-3xl sm:text-4xl md:text-5xl lg:text-6xl font-black tracking-tight"
                            style="font-family: var(--font-heading); color: var(--color-text); line-height: 0.95;">
                            {_esc(p['headline'])}
                        </h1>
                        <p class="mt-5 text-base sm:text-lg leading-relaxed max-w-md"
                           style="color: var(--color-text-muted);">
                            {_esc(p['subheadline'])}
                        </p>
                        <div class="mt-8 flex flex-wrap items-center gap-5">
                            <a href="{_esc(p['cta_link'])}"
                               class="inline-block bg-[var(--color-primary)] hover:bg-[var(--color-primary-hover)] text-white font-semibold rounded-2xl px-8 py-4 transition-all duration-200 hover:shadow-lg"
                               style="font-size: 1.05rem;">
                                {_esc(p['cta_text'])}
                            </a>
{cta2}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>"""


@_component("AboutStory")
def _about_story(p: Dict[str, Any]) -> str:
    """Editorial asymmetric story: full-bleed photo left, narrow text column right.
    Founder gravitas treatment — NOT a symmetric 50/50 dental clinic split."""
    paras = p.get("paragraphs", [])
    # First paragraph becomes large pull-quote; rest are body
    pull_quote_text = ""
    body_paras = paras
    if paras:
        pull_quote_text = paras[0]
        body_paras = paras[1:]

    pull_quote_html = ""
    if pull_quote_text:
        pull_quote_html = f"""                <blockquote class="italic leading-snug mb-8"
                            style="font-family: var(--font-heading); color: var(--color-text); font-size: clamp(1.4rem, 2.2vw, 2rem); line-height: 1.25;">
                    {_esc(pull_quote_text)}
                </blockquote>"""

    body_html = "\n".join(
        f'                <p class="text-base leading-relaxed" style="color: var(--color-text-muted);">{_esc(para)}</p>'
        for para in body_paras
    )

    # Founder gravitas — parse "— Yassir Ar., Pengasas" signature
    signature_html = ""
    if p.get("signature"):
        sig = p['signature'].lstrip('—').strip()
        parts = [s.strip() for s in sig.split(',', 1)]
        name = _esc(parts[0]) if parts else _esc(sig)
        role = _esc(parts[1]) if len(parts) > 1 else ""
        role_line = f'<p class="text-sm mt-0.5" style="color: var(--color-text-muted);">{role}</p>' if role else ""
        signature_html = f"""                <div class="mt-10 pt-8 flex items-center gap-4" style="border-top: 1px solid var(--color-border);">
                    <div class="shrink-0 w-11 h-11 rounded-full flex items-center justify-center"
                         style="background: linear-gradient(135deg, var(--color-primary), var(--color-secondary));">
                        <i class="fa-solid fa-user text-white text-sm"></i>
                    </div>
                    <div>
                        <p class="text-base font-semibold" style="font-family: var(--font-heading); color: var(--color-text);">{name}</p>
                        {role_line}
                    </div>
                </div>"""

    # Full-bleed photo — breaks out of section padding via negative margins
    img_html = ""
    if p.get("image_url"):
        img_html = f"""            <!-- Photo column: bleeds off left edge, full section height on desktop -->
            <div class="relative -ml-4 sm:-ml-6 lg:-ml-8 mb-8 lg:mb-0 lg:absolute lg:inset-y-0 lg:left-0 lg:w-[44%] overflow-hidden">
                <img src="{_esc(p['image_url'])}" alt="{_esc(p.get('image_alt', ''))}"
                     class="w-full object-cover"
                     style="height: 360px; min-height: 360px; object-position: center;" loading="lazy">
                <!-- Soft right edge fade on desktop -->
                <div class="hidden lg:block absolute inset-y-0 right-0 w-20"
                     style="background: linear-gradient(to right, transparent, var(--color-background));"></div>
            </div>"""

    text_offset = "lg:ml-[46%] lg:pl-12" if p.get("image_url") else ""

    return f"""        <!-- Editorial asymmetric story layout -->
        <div class="relative">
{img_html}
            <!-- Text column: right side, offset from photo, generous top padding on desktop -->
            <div class="{text_offset} py-0 lg:py-16">
                <div class="max-w-xl">
                    <div class="accent-line mb-6"></div>
                    <h2 class="text-4xl md:text-5xl font-bold tracking-tight mb-8"
                        style="font-family: var(--font-heading); color: var(--color-text);">
                        {_esc(p['heading'])}
                    </h2>
{pull_quote_html}
                    <div class="space-y-4">
{body_html}
                    </div>
{signature_html}
                </div>
            </div>
        </div>"""


@_component("AboutStats")
def _about_stats(p: Dict[str, Any]) -> str:
    """Editorial year monument + founder quote centrepiece + compact stat row.
    Boutique-restaurant register — NOT a B2B SaaS dashboard."""
    import re as _re
    # Extract hero year from description text
    hero_year = "2018"
    desc_text = p.get("description", "")
    yr_match = _re.search(r'\b(19|20)\d{2}\b', desc_text)
    if yr_match:
        hero_year = yr_match.group(0)

    # Compact supporting stats
    stats = p.get("stats", [])
    stat_items = []
    for idx, stat in enumerate(stats):
        stat_items.append(f"""                <div class="text-center py-4">
                    <div class="text-2xl sm:text-3xl md:text-4xl font-black"
                         style="font-family: var(--font-heading); color: var(--color-primary); line-height: 1;">
                        {_esc(stat.get('value', ''))}
                    </div>
                    <p class="mt-2 text-xs sm:text-sm font-medium uppercase tracking-wider"
                       style="color: var(--color-text-muted); letter-spacing: 0.08em;">
                        {_esc(stat.get('label', ''))}
                    </p>
                </div>""")
    stats_row = "\n".join(stat_items)

    # Founder quote as editorial centrepiece
    quote_block = ""
    if p.get("quote") and p.get("quote_author"):
        quote_block = f"""        <!-- Founder quote — editorial centrepiece with ghost year -->
        <div class="relative py-20 lg:py-28 overflow-hidden" data-aos="fade-up">
            <!-- Ghost year — monumental background typography -->
            <div class="absolute inset-0 flex items-center justify-center pointer-events-none select-none overflow-hidden">
                <span class="block italic leading-none"
                      style="font-family: var(--font-heading); font-size: clamp(140px, 22vw, 240px); color: var(--color-text); opacity: 0.07; white-space: nowrap;">{hero_year}</span>
            </div>
            <!-- Quote content -->
            <div class="relative z-10 max-w-3xl mx-auto text-center px-4">
                <blockquote class="italic leading-tight"
                            style="font-family: var(--font-heading); color: var(--color-text); font-size: clamp(1.75rem, 3.5vw, 3rem); line-height: 1.2;">
                    &ldquo;{_esc(p['quote'])}&rdquo;
                </blockquote>
                <div class="mt-8 flex items-center justify-center gap-4">
                    <div style="width: 48px; height: 1px; background-color: var(--color-primary);"></div>
                    <p class="text-sm font-semibold tracking-wider uppercase"
                       style="color: var(--color-primary);">
                        {_esc(p['quote_author'])}
                    </p>
                    <div style="width: 48px; height: 1px; background-color: var(--color-primary);"></div>
                </div>
            </div>
        </div>"""

    description = ""
    if p.get("description"):
        description = f"""        <p class="mt-6 text-sm sm:text-base leading-relaxed text-center max-w-2xl mx-auto"
           style="color: var(--color-text-muted);">
            {_esc(p['description'])}
        </p>"""

    return f"""        <div class="text-center mb-4">
            <div class="accent-line mx-auto mb-6"></div>
            <h2 class="text-4xl md:text-5xl font-bold tracking-tight"
                style="font-family: var(--font-heading); color: var(--color-text);">
                {_esc(p['heading'])}
            </h2>
        </div>
{quote_block}
        <!-- Supporting stats — compact row -->
        <div class="grid grid-cols-2 sm:grid-cols-4 gap-4 py-8 px-6 rounded-3xl"
             style="background-color: var(--color-surface); box-shadow: var(--shadow-lg);"
             data-aos="fade-up">
{stats_row}
        </div>
{description}"""


@_component("AboutTimeline")
def _about_timeline(p: Dict[str, Any]) -> str:
    """Editorial horizontal-panel timeline with monumental year typography.
    Replaces generic vertical zigzag with boutique-editorial four-panel layout.
    Heritage restaurants showing evolution — Malaysian context required."""
    milestones = p.get("milestones", [])
    panels = []
    for idx, m in enumerate(milestones):
        year = _esc(m.get('year', ''))
        title = _esc(m.get('title', ''))
        description = _esc(m.get('description', ''))
        image_url = m.get('image_url', '')
        delay = idx * 150

        # Alternate photo left/right within content area across panels
        text_order = "md:order-1" if idx % 2 == 0 else "md:order-2"
        photo_order = "md:order-2" if idx % 2 == 0 else "md:order-1"

        # Photo block — real photograph or gradient fallback
        if image_url:
            photo_block = f"""                <div class="w-full md:w-[55%] shrink-0 overflow-hidden rounded-xl {photo_order}">
                    <img src="{_esc(image_url)}" alt="{title}"
                         class="w-full h-64 md:h-80 lg:h-96 object-cover" loading="lazy">
                </div>"""
        else:
            photo_block = f"""                <div class="w-full md:w-[55%] shrink-0 rounded-xl flex items-center justify-center {photo_order}"
                     style="background: linear-gradient(135deg, var(--color-primary), var(--color-secondary)); min-height: 16rem;">
                    <i class="fa-solid fa-image text-5xl text-white/30"></i>
                </div>"""

        # Personal artifact caption — only for first milestone (2018)
        artifact_html = ""
        if idx == 0:
            artifact_html = """\n                <p class="mt-3 text-sm italic" style="color: var(--color-text-muted); font-size: 14px;">— Buku tempahan pertama, Ramadan 2018</p>"""

        # Separator between panels
        border_class = "border-b" if idx < len(milestones) - 1 else ""
        border_style = 'style="border-color: var(--color-accent);"' if idx < len(milestones) - 1 else ""

        panels.append(f"""        <!-- Editorial Panel {idx + 1} — {year} -->
        <div class="grid grid-cols-1 lg:grid-cols-[220px_1fr] gap-6 lg:gap-20 items-center py-16 lg:py-32 {border_class}" {border_style}
             data-aos="fade-up" data-aos-delay="{delay}">
            <!-- Year — monumental display typography -->
            <div class="shrink-0 select-none">
                <span class="block italic leading-none text-[72px] sm:text-[100px] lg:text-[160px]"
                      style="font-family: var(--font-heading); color: var(--color-text); opacity: 0.12;">{year}</span>{artifact_html}
            </div>
            <!-- Content: headline + story + photograph (photo side alternates) -->
            <div class="flex flex-col md:flex-row gap-8 items-center">
                <!-- Text content -->
                <div class="flex-1 {text_order}">
                    <h3 class="font-bold leading-tight mb-4"
                        style="font-family: var(--font-heading); color: var(--color-text); font-size: clamp(1.5rem, 2.5vw, 2rem);">
                        {title}
                    </h3>
                    <p class="leading-relaxed text-base md:text-lg"
                       style="color: var(--color-text-muted);">
                        {description}
                    </p>
                </div>
                <!-- Photograph -->
{photo_block}
            </div>
        </div>""")

    panels_html = "\n".join(panels)

    return f"""        <div class="text-center mb-16" data-aos="fade-up">
            <div class="accent-line mx-auto mb-6"></div>
            <h2 class="text-4xl md:text-5xl font-bold tracking-tight"
                style="font-family: var(--font-heading); color: var(--color-text);">
                {_esc(p['heading'])}
            </h2>
        </div>
        <!-- Editorial timeline panels -->
        <div>
{panels_html}
        </div>"""


@_component("AboutCards")
def _about_cards(p: Dict[str, Any]) -> str:
    """Asymmetric value-proposition layout: dominant first card + secondary pair.
    Heritage restaurant register — breaks 3-equal-SaaS symmetry."""
    cards = p.get("cards", [])

    # First card: DOMINANT — full-width hero with photo background or gradient
    dominant_html = ""
    secondary_items = []

    if cards:
        first = cards[0]
        icon = _esc(first.get("icon", "fa-solid fa-star"))
        title = _esc(first.get("title", ""))
        desc = _esc(first.get("description", ""))
        img_url = first.get("image_url", "")

        if img_url:
            dominant_bg = f'background-image: url({_esc(img_url)}); background-size: cover; background-position: center;'
            overlay = '<div class="absolute inset-0 rounded-2xl" style="background: linear-gradient(to top, rgba(0,0,0,0.72) 40%, rgba(0,0,0,0.25) 100%);"></div>'
            icon_block = f'<i class="{icon} text-3xl text-white/80 mb-6 relative z-10"></i>'
            text_color = "text-white"
            desc_color = "text-white/75"
        else:
            dominant_bg = 'background: linear-gradient(135deg, var(--color-primary), var(--color-secondary));'
            overlay = ""
            icon_block = f'<i class="{icon} text-3xl text-white/80 mb-6"></i>'
            text_color = "text-white"
            desc_color = "text-white/75"

        dominant_html = f"""        <!-- Dominant first card -->
        <div class="relative rounded-2xl overflow-hidden flex flex-col justify-end p-8 sm:p-10"
             style="min-height: 340px; {dominant_bg}"
             data-aos="fade-up">
            {overlay}
            <div class="relative z-10">
                {icon_block}
                <h3 class="text-2xl sm:text-3xl font-bold mb-3 {text_color}"
                    style="font-family: var(--font-heading);">
                    {title}
                </h3>
                <p class="text-sm sm:text-base leading-relaxed {desc_color}">
                    {desc}
                </p>
            </div>
        </div>"""

    for idx, card in enumerate(cards[1:], start=1):
        delay = idx * 120
        icon = _esc(card.get("icon", "fa-solid fa-star"))
        img_url = card.get("image_url", "")

        if img_url:
            bg_style = f'background-image: url({_esc(img_url)}); background-size: cover; background-position: center;'
            overlay = '<div class="absolute inset-0 rounded-2xl" style="background: linear-gradient(to top, rgba(0,0,0,0.68) 40%, rgba(0,0,0,0.2) 100%);"></div>'
            icon_block = f'<i class="{icon} text-2xl text-white/75 mb-4 relative z-10"></i>'
            text_color = "text-white"
            desc_color = "text-white/70"
            bg_card = ""
        else:
            bg_style = ""
            overlay = ""
            icon_block = f"""<div class="w-12 h-12 rounded-xl flex items-center justify-center mb-4"
                         style="background: linear-gradient(135deg, var(--color-primary), var(--color-secondary));">
                        <i class="{icon} text-lg text-white"></i>
                    </div>"""
            text_color = ""
            desc_color = ""
            bg_card = 'background-color: var(--color-surface); box-shadow: var(--shadow);'

        secondary_items.append(f"""            <div class="relative rounded-2xl overflow-hidden flex flex-col justify-end p-7 transition-all duration-300 hover:-translate-y-1"
                 style="min-height: 260px; {bg_style}{bg_card}"
                 data-aos="fade-up" data-aos-delay="{delay}">
                {overlay}
                <div class="relative z-10">
                    {icon_block}
                    <h3 class="text-xl font-bold mb-2 {text_color}"
                        style="font-family: var(--font-heading); {'color: var(--color-text);' if not text_color else ''}">
                        {_esc(card.get('title', ''))}
                    </h3>
                    <p class="text-sm leading-relaxed {desc_color}"
                       style="{'color: var(--color-text-muted);' if not desc_color else ''}">
                        {_esc(card.get('description', ''))}
                    </p>
                </div>
            </div>""")

    secondary_html = "\n".join(secondary_items)
    secondary_grid = ""
    if secondary_items:
        secondary_grid = f"""        <!-- Secondary cards: side-by-side below dominant -->
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-6 mt-6">
{secondary_html}
        </div>"""

    subtitle = ""
    if p.get("subtitle"):
        subtitle = f"""        <p class="mt-4 text-lg leading-relaxed" style="color: var(--color-text-muted);">{_esc(p['subtitle'])}</p>"""

    return f"""        <div class="text-center mb-14">
            <div class="accent-line mx-auto mb-6"></div>
            <h2 class="text-4xl md:text-5xl font-bold tracking-tight"
                style="font-family: var(--font-heading); color: var(--color-text);">
                {_esc(p['heading'])}
            </h2>
{subtitle}
        </div>
{dominant_html}
{secondary_grid}"""


@_component("MenuGrid")
def _menu_grid(p: Dict[str, Any]) -> str:
    subheading = ""
    if p.get("subheading"):
        subheading = f'        <p class="mt-4 text-lg leading-relaxed" style="color: var(--color-text-muted);">{_esc(p["subheading"])}</p>'

    items = p.get("items", [])
    cards = []
    for idx, item in enumerate(items):
        is_featured = idx == 0 and item.get("badge")  # First popular item is featured

        badge_html = ""
        if item.get("badge"):
            badge_html = f"""                    <span class="absolute top-4 left-4 text-white text-xs font-bold px-4 py-1.5 rounded-full uppercase tracking-wider z-10"
                          style="background-color: var(--color-primary); letter-spacing: 0.05em;">{_esc(item['badge'])}</span>"""

        img_h = "h-56" if is_featured else "h-48"
        fallback_js = "this.onerror=null;this.parentElement.innerHTML=\\'<div class=&quot;w-full {0} flex items-center justify-center&quot; style=&quot;background:linear-gradient(135deg,var(--color-primary),var(--color-secondary))&quot;><i class=&quot;fa-solid fa-bowl-food text-4xl text-white/40&quot;></i></div>\\'".format(img_h)
        if item.get("image_url"):
            img = f"""            <div class="relative overflow-hidden">
                <img src="{_esc(item['image_url'])}" alt="{_esc(item['name'])}"
                     class="w-full {img_h} object-cover transition-transform duration-500 hover:scale-110" loading="lazy"
                     onerror="this.onerror=null;this.style.display='none';this.nextElementSibling.style.display='flex';">
                <div class="w-full {img_h} items-center justify-center" style="display:none;background:linear-gradient(135deg,var(--color-primary),var(--color-secondary));">
                    <i class="fa-solid fa-bowl-food text-4xl text-white/40"></i>
                </div>
{badge_html}
            </div>"""
        else:
            img = f"""            <div class="relative w-full {img_h} flex items-center justify-center"
                 style="background: linear-gradient(135deg, var(--color-primary), var(--color-secondary));">
                <i class="fa-solid fa-bowl-food text-4xl text-white/40"></i>
{badge_html}
            </div>"""

        featured_class = "sm:col-span-2 lg:col-span-1" if is_featured else ""

        cards.append(f"""        <div class="menu-card rounded-2xl overflow-hidden {featured_class}"
             style="background-color: var(--color-surface); box-shadow: var(--shadow);">
{img}
            <div class="p-6">
                <h3 class="text-lg font-semibold" style="font-family: var(--font-heading); color: var(--color-text);">
                    {_esc(item['name'])}
                </h3>
                <p class="mt-2 text-sm leading-relaxed" style="color: var(--color-text-muted);">
                    {_esc(item['description'])}
                </p>
                <p class="mt-4 text-xl font-bold" style="color: var(--color-primary);">
                    {_esc(item['price'])}
                </p>
            </div>
        </div>""")

    return f"""        <div class="text-center mb-14">
            <div class="accent-line mx-auto mb-6"></div>
            <h2 class="text-4xl md:text-5xl font-bold tracking-tight" style="font-family: var(--font-heading); color: var(--color-text);">
                {_esc(p['heading'])}
            </h2>
{subheading}
        </div>
        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-8">
{chr(10).join(cards)}
        </div>"""


@_component("GalleryMasonry")
def _gallery_masonry(p: Dict[str, Any]) -> str:
    imgs = p.get("images", [])

    # Bento grid: first image is large (2x2), rest fill in
    bento_cells = []
    for idx, img in enumerate(imgs):
        if idx == 0:
            # Large featured image — spans 2 cols and 2 rows
            bento_cells.append(
                f"""            <div class="col-span-2 row-span-2 overflow-hidden rounded-2xl group">
                <img src="{_esc(img['url'])}" alt="{_esc(img['alt'])}"
                     class="w-full h-full object-cover transition-all duration-500 group-hover:scale-105" loading="lazy"
                     style="min-height: 400px;"
                     onerror="this.onerror=null;this.style.display='none';this.nextElementSibling.style.display='flex';">
                <div class="w-full items-center justify-center rounded-2xl" style="display:none;min-height:400px;background:linear-gradient(135deg,var(--color-primary),var(--color-secondary));">
                    <i class="fa-solid fa-image text-4xl text-white/30"></i>
                </div>
            </div>""")
        else:
            bento_cells.append(
                f"""            <div class="overflow-hidden rounded-2xl group">
                <img src="{_esc(img['url'])}" alt="{_esc(img['alt'])}"
                     class="w-full h-full object-cover transition-all duration-500 group-hover:scale-105" loading="lazy"
                     style="min-height: 190px;"
                     onerror="this.onerror=null;this.style.display='none';this.nextElementSibling.style.display='flex';">
                <div class="w-full items-center justify-center rounded-2xl" style="display:none;min-height:190px;background:linear-gradient(135deg,var(--color-primary),var(--color-secondary));">
                    <i class="fa-solid fa-image text-3xl text-white/30"></i>
                </div>
            </div>""")

    cells_html = "\n".join(bento_cells)

    subtitle = ""
    if p.get("subtitle"):
        subtitle = f"""        <p class="mt-3 text-lg leading-relaxed" style="color: var(--color-text-muted);">{_esc(p['subtitle'])}</p>"""

    return f"""        <div class="mb-12 md:mb-16">
            <div class="accent-line mb-6"></div>
            <h2 class="text-4xl md:text-5xl font-bold tracking-tight"
                style="font-family: var(--font-heading); color: var(--color-text);">
                {_esc(p['heading'])}
            </h2>
{subtitle}
        </div>
        <div class="grid grid-cols-2 md:grid-cols-3 auto-rows-[190px] gap-2">
{cells_html}
        </div>"""


@_component("TestimonialCards")
def _testimonial_cards(p: Dict[str, Any]) -> str:
    cards = []
    for idx, r in enumerate(p.get("reviews", [])):
        stars = "".join(
            f'<i class="fa-{"solid" if i < r.get("rating", 5) else "regular"} fa-star text-sm" style="color: {"#F59E0B" if i < r.get("rating", 5) else "var(--color-text-muted)"};"></i>'
            for i in range(5)
        )
        initial = r.get("avatar_fallback", r.get("name", "?")[0].upper())
        # Alternate background: first card uses accent, others use surface
        bg = "var(--color-accent)" if idx == 0 else "var(--color-surface)"
        cards.append(f"""        <div class="testimonial-card p-8 rounded-2xl" style="background-color: {bg}; box-shadow: var(--shadow);">
            <div class="flex gap-1 mb-5">{stars}</div>
            <p class="text-base sm:text-lg leading-relaxed" style="font-family: var(--font-heading); color: var(--color-text); font-style: italic;">
                &ldquo;{_esc(r['text'])}&rdquo;
            </p>
            <div class="mt-8 flex items-center gap-3">
                <div class="w-11 h-11 rounded-full flex items-center justify-center text-sm font-bold text-white"
                     style="background-color: var(--color-primary);">{initial}</div>
                <span class="text-sm font-semibold" style="color: var(--color-text);">{_esc(r['name'])}</span>
            </div>
        </div>""")

    return f"""        <div class="text-center mb-14">
            <h2 class="text-4xl md:text-5xl font-bold tracking-tight"
                style="font-family: var(--font-heading); color: var(--color-text);">
                {_esc(p['heading'])}
            </h2>
        </div>
        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-8">
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

    if p.get("hours_structured"):
        hours_rows = "\n".join(
            f'                        <div class="flex justify-between py-1.5" style="border-bottom: 1px solid var(--color-border);"><span class="font-medium" style="color: var(--color-text);">{_esc(h["day"])}</span><span style="color: var(--color-text-muted);">{_esc(h["time"])}</span></div>'
            for h in p["hours_structured"]
        )
        items.append(f"""            <div class="flex items-start gap-3">
                <i class="fa-solid fa-clock mt-1" style="color: var(--color-primary);"></i>
                <div class="flex-1">
                    <p class="font-semibold mb-2" style="color: var(--color-text);">Waktu Operasi</p>
{hours_rows}
                </div>
            </div>""")
    elif p.get("hours"):
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
        map_html = f"""        <div class="map-container rounded-2xl overflow-hidden" style="box-shadow: var(--shadow-lg);">
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
                <div class="accent-line mb-6"></div>
                <h2 class="text-4xl md:text-5xl font-bold tracking-tight" style="font-family: var(--font-heading); color: var(--color-text);">
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
        powered = '            <p class="flex items-center justify-center gap-1.5">Dibina dengan <a href="https://binaapp.my" target="_blank" rel="noopener noreferrer" class="font-semibold tracking-wide hover:opacity-100 transition-opacity" style="opacity: 0.85;">Bina<span style="color: var(--color-primary);">App</span></a></p>'

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

# ---------------------------------------------------------------------------
# Menu Variants — editorial_list, chef_picks, category_tabs
# ---------------------------------------------------------------------------

@_component("MenuList")
def _menu_list(p: Dict[str, Any]) -> str:
    """Type-led editorial menu — dish name (display serif), description, price.
    Categorized by section. Dotted leader between name and price. No images."""
    items = p.get("items", [])

    # Group items by category; ungrouped items go under a default heading
    categories: Dict[str, list] = {}
    for item in items:
        cat = item.get("category", "Hidangan")
        categories.setdefault(cat, []).append(item)
    if not categories:
        categories = {"Hidangan Pilihan": items}

    cat_blocks = []
    for cat_name, cat_items in categories.items():
        rows = []
        for item in cat_items:
            badge = (
                f'<span class="ml-3 text-xs font-bold uppercase tracking-widest px-2 py-0.5 rounded-full text-white"'
                f' style="background-color: var(--color-primary); letter-spacing: 0.08em;">{_esc(item["badge"])}</span>'
                if item.get("badge") else ""
            )
            desc_html = (
                f'<p class="mt-1 text-sm leading-relaxed max-w-xl" style="color: var(--color-text-muted);">{_esc(item["description"])}</p>'
                if item.get("description") else ""
            )
            rows.append(f"""            <div class="py-5" style="border-bottom: 1px dashed var(--color-border);">
                <div class="flex items-baseline justify-between gap-4">
                    <h3 class="text-xl leading-tight flex items-center flex-wrap gap-1"
                        style="font-family: var(--font-heading); color: var(--color-text); font-weight: 600;">
                        {_esc(item['name'])}{badge}
                    </h3>
                    <span class="shrink-0 text-xl font-bold tabular-nums" style="color: var(--color-primary);">
                        {_esc(item.get('price', ''))}
                    </span>
                </div>
{desc_html}
            </div>""")

        cat_blocks.append(f"""        <div class="mb-10">
            <div class="flex items-center gap-4 mb-2">
                <span class="text-xs font-bold uppercase tracking-widest" style="color: var(--color-primary); letter-spacing: 0.15em;">{_esc(cat_name)}</span>
                <div class="flex-1 h-px" style="background-color: var(--color-border);"></div>
            </div>
{chr(10).join(rows)}
        </div>""")

    heading = _esc(p.get('heading', 'Menu'))
    subheading = (
        f'        <p class="mt-3 text-lg leading-relaxed max-w-2xl mx-auto" style="color: var(--color-text-muted);">{_esc(p["subheading"])}</p>'
        if p.get("subheading") else ""
    )

    return f"""        <div class="text-center mb-14">
            <div class="accent-line mx-auto mb-6"></div>
            <h2 class="text-4xl md:text-5xl font-bold tracking-tight" style="font-family: var(--font-heading); color: var(--color-text);">
                {heading}
            </h2>
{subheading}
        </div>
        <div class="max-w-3xl mx-auto">
{chr(10).join(cat_blocks)}
        </div>"""


@_component("MenuFeatured")
def _menu_featured(p: Dict[str, Any]) -> str:
    """Chef's picks — 1 hero dish (60% width) + 3 supporting in vertical stack."""
    items = p.get("items", [])
    hero_item = items[0] if items else {}
    support_items = items[1:4]

    def _dish_badge(item: dict) -> str:
        if item.get("badge"):
            return f'<span class="inline-block text-xs font-bold uppercase tracking-widest px-3 py-1 rounded-full text-white mb-3" style="background-color: var(--color-primary);">{_esc(item["badge"])}</span>'
        return ""

    hero_img = ""
    if hero_item.get("image_url"):
        hero_img = f"""                <div class="overflow-hidden rounded-2xl" style="height: 340px;">
                    <img src="{_esc(hero_item['image_url'])}" alt="{_esc(hero_item.get('name',''))}"
                         class="w-full h-full object-cover transition-transform duration-700 hover:scale-105" loading="lazy"
                         onerror="this.onerror=null;this.style.display='none';this.nextElementSibling.style.display='flex';">
                    <div class="w-full items-center justify-center rounded-2xl" style="display:none;height:340px;background:linear-gradient(135deg,var(--color-primary),var(--color-secondary));">
                        <i class="fa-solid fa-bowl-food text-4xl text-white/40"></i>
                    </div>
                </div>"""

    support_cards = []
    for item in support_items:
        img_html = ""
        if item.get("image_url"):
            img_html = f"""                    <div class="shrink-0 w-20 h-20 overflow-hidden rounded-xl">
                        <img src="{_esc(item['image_url'])}" alt="{_esc(item.get('name',''))}"
                             class="w-full h-full object-cover" loading="lazy"
                             onerror="this.onerror=null;this.style.display='none';this.nextElementSibling.style.display='flex';">
                        <div class="w-20 h-20 items-center justify-center rounded-xl" style="display:none;background:linear-gradient(135deg,var(--color-primary),var(--color-secondary));">
                            <i class="fa-solid fa-bowl-food text-white/40 text-lg"></i>
                        </div>
                    </div>"""

        support_cards.append(f"""            <div class="flex gap-5 p-5 rounded-2xl" style="background-color: var(--color-surface); box-shadow: var(--shadow);">
{img_html}
                <div class="min-w-0 flex-1">
                    <p class="text-base font-semibold leading-tight" style="font-family: var(--font-heading); color: var(--color-text);">{_esc(item.get('name',''))}</p>
                    <p class="text-xs mt-1 leading-relaxed line-clamp-2" style="color: var(--color-text-muted);">{_esc(item.get('description',''))}</p>
                    <p class="mt-2 font-bold" style="color: var(--color-primary);">{_esc(item.get('price',''))}</p>
                </div>
            </div>""")

    heading = _esc(p.get('heading', 'Chef\'s Picks'))
    subheading = (
        f'        <p class="mt-3 text-lg" style="color: var(--color-text-muted);">{_esc(p["subheading"])}</p>'
        if p.get("subheading") else ""
    )

    return f"""        <div class="mb-14">
            <div class="accent-line mb-6"></div>
            <h2 class="text-4xl md:text-5xl font-bold tracking-tight" style="font-family: var(--font-heading); color: var(--color-text);">
                {heading}
            </h2>
{subheading}
        </div>
        <div class="grid grid-cols-1 lg:grid-cols-5 gap-8 items-start">
            <!-- Hero dish: 3/5 width -->
            <div class="lg:col-span-3">
                <div class="rounded-2xl overflow-hidden" style="background-color: var(--color-surface); box-shadow: var(--shadow-lg);">
{hero_img}
                    <div class="p-8">
                        {_dish_badge(hero_item)}
                        <h3 class="text-3xl font-bold leading-tight mb-3" style="font-family: var(--font-heading); color: var(--color-text);">{_esc(hero_item.get('name',''))}</h3>
                        <p class="text-base leading-relaxed" style="color: var(--color-text-muted);">{_esc(hero_item.get('description',''))}</p>
                        <p class="mt-5 text-2xl font-bold" style="color: var(--color-primary);">{_esc(hero_item.get('price',''))}</p>
                    </div>
                </div>
            </div>
            <!-- Supporting dishes: 2/5 width -->
            <div class="lg:col-span-2 space-y-4">
                <p class="text-xs font-bold uppercase tracking-widest mb-4" style="color: var(--color-text-muted); letter-spacing: 0.12em;">Hidangan Lain</p>
{chr(10).join(support_cards)}
            </div>
        </div>"""


@_component("MenuCategorized")
def _menu_categorized(p: Dict[str, Any]) -> str:
    """Category tabs — click switches grid. JS-driven tab filter with fade transition."""
    items = p.get("items", [])
    categories = p.get("categories", [])

    # Auto-detect categories from items if not explicitly provided
    if not categories:
        seen: list = []
        for item in items:
            c = item.get("category", "Lain-lain")
            if c not in seen:
                seen.append(c)
        categories = seen or ["Semua"]

    # Build category tab buttons
    tab_buttons = []
    for i, cat in enumerate(categories):
        active_style = "style=\"background-color: var(--color-primary); color: white;\""
        inactive_style = "style=\"background-color: var(--color-surface); color: var(--color-text);\""
        tab_buttons.append(
            f'<button onclick="filterMenu(\'{_esc(cat)}\')" id="tab-{i}" '
            f'class="tab-btn px-5 py-2 rounded-full text-sm font-semibold transition-all duration-200 whitespace-nowrap" '
            f'{active_style if i == 0 else inactive_style}>'
            f'{_esc(cat)}</button>'
        )

    # Build all menu cards with data-category attribute
    cards = []
    for item in items:
        cat = item.get("category", categories[0] if categories else "Semua")
        badge_html = (
            f'<span class="absolute top-3 left-3 text-white text-xs font-bold px-3 py-1 rounded-full uppercase tracking-wide z-10"'
            f' style="background-color: var(--color-primary);">{_esc(item["badge"])}</span>'
            if item.get("badge") else ""
        )
        img_html = ""
        if item.get("image_url"):
            img_html = f"""            <div class="relative overflow-hidden h-44">
                <img src="{_esc(item['image_url'])}" alt="{_esc(item.get('name',''))}"
                     class="w-full h-full object-cover transition-transform duration-500 hover:scale-110" loading="lazy"
                     onerror="this.onerror=null;this.style.display='none';this.nextElementSibling.style.display='flex';">
                <div class="w-full h-44 items-center justify-center" style="display:none;background:linear-gradient(135deg,var(--color-primary),var(--color-secondary));">
                    <i class="fa-solid fa-bowl-food text-3xl text-white/40"></i>
                </div>
{badge_html}
            </div>"""
        cards.append(f"""        <div class="menu-card rounded-2xl overflow-hidden" data-cat="{_esc(cat)}"
             style="background-color: var(--color-surface); box-shadow: var(--shadow);">
{img_html}
            <div class="p-5">
                <h3 class="text-base font-semibold leading-tight" style="font-family: var(--font-heading); color: var(--color-text);">{_esc(item.get('name',''))}</h3>
                <p class="mt-1.5 text-xs leading-relaxed" style="color: var(--color-text-muted);">{_esc(item.get('description',''))}</p>
                <p class="mt-3 text-lg font-bold" style="color: var(--color-primary);">{_esc(item.get('price',''))}</p>
            </div>
        </div>""")

    heading = _esc(p.get('heading', 'Menu'))
    first_cat = _esc(categories[0]) if categories else "Semua"

    return f"""        <div class="text-center mb-10">
            <div class="accent-line mx-auto mb-6"></div>
            <h2 class="text-4xl md:text-5xl font-bold tracking-tight" style="font-family: var(--font-heading); color: var(--color-text);">{heading}</h2>
        </div>
        <!-- Category tabs -->
        <div class="flex gap-3 overflow-x-auto pb-3 mb-10 -mx-2 px-2 scrollbar-none">
            {"".join(tab_buttons)}
        </div>
        <!-- Menu grid -->
        <div id="menu-grid" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
{chr(10).join(cards)}
        </div>
        <script>
        function filterMenu(cat) {{
            const cards = document.querySelectorAll('#menu-grid [data-cat]');
            cards.forEach(function(card) {{
                card.style.opacity = '0';
                card.style.transition = 'opacity 0.25s';
                setTimeout(function() {{
                    card.style.display = (cat === 'Semua' || card.dataset.cat === cat) ? '' : 'none';
                    card.style.opacity = '1';
                }}, 150);
            }});
            document.querySelectorAll('.tab-btn').forEach(function(btn) {{
                btn.style.backgroundColor = btn.textContent.trim() === cat ? 'var(--color-primary)' : 'var(--color-surface)';
                btn.style.color = btn.textContent.trim() === cat ? 'white' : 'var(--color-text)';
            }});
        }}
        filterMenu('{first_cat}');
        </script>"""


# ---------------------------------------------------------------------------
# Gallery Variants — carousel, grid, full-width story
# ---------------------------------------------------------------------------

@_component("GalleryCarousel")
def _gallery_carousel(p: Dict[str, Any]) -> str:
    """Full-bleed immersive carousel. Each slide 16:9, caption overlay, auto-advance."""
    imgs = p.get("images", [])
    if not imgs:
        return '<div class="text-center py-20" style="color:var(--color-text-muted);">No images</div>'

    slides_html = []
    dots_html = []
    for i, img in enumerate(imgs):
        caption = img.get("caption", img.get("alt", ""))
        slides_html.append(f"""            <div class="carousel-slide absolute inset-0 transition-opacity duration-700" style="opacity: {'1' if i == 0 else '0'}; z-index: {'1' if i == 0 else '0'};">
                <img src="{_esc(img['url'])}" alt="{_esc(img['alt'])}"
                     class="w-full h-full object-cover" loading="{'eager' if i == 0 else 'lazy'}"
                     onerror="this.onerror=null;this.style.display='none';this.nextElementSibling.style.display='flex';">
                <div class="w-full h-full items-center justify-center" style="display:none;background:linear-gradient(135deg,var(--color-primary),var(--color-secondary));">
                    <i class="fa-solid fa-image text-5xl text-white/30"></i>
                </div>
                <!-- Caption overlay -->
                {f'<div class="absolute bottom-0 left-0 right-0 px-6 py-5 bg-gradient-to-t from-black/60 to-transparent"><p class="text-white text-sm font-medium">{_esc(caption)}</p></div>' if caption else ''}
            </div>""")
        active_dot = "style=\"background-color: white; opacity: 1;\"" if i == 0 else "style=\"background-color: white; opacity: 0.4;\""
        dots_html.append(f'<button class="carousel-dot w-2 h-2 rounded-full transition-all duration-300 cursor-pointer" data-slide="{i}" {active_dot} onclick="goSlide({i})"></button>')

    subtitle = ""
    if p.get("subtitle"):
        subtitle = f'        <p class="mt-3 text-lg" style="color: var(--color-text-muted);">{_esc(p["subtitle"])}</p>'

    total = len(imgs)
    return f"""        <div class="mb-12">
            <div class="accent-line mb-6"></div>
            <h2 class="text-4xl md:text-5xl font-bold tracking-tight" style="font-family: var(--font-heading); color: var(--color-text);">{_esc(p.get('heading','Galeri'))}</h2>
{subtitle}
        </div>
        <!-- Full-bleed carousel wrapper -->
        <div id="carousel-wrap" class="relative overflow-hidden rounded-2xl"
             style="padding-bottom: 56.25%; background: var(--color-surface);">
{chr(10).join(slides_html)}
            <!-- Prev/Next arrows -->
            <button onclick="prevSlide()" class="absolute left-4 top-1/2 -translate-y-1/2 z-20 w-10 h-10 rounded-full flex items-center justify-center transition-all hover:scale-110"
                    style="background: rgba(0,0,0,0.45); color: white;">
                <i class="fa-solid fa-chevron-left"></i>
            </button>
            <button onclick="nextSlide()" class="absolute right-4 top-1/2 -translate-y-1/2 z-20 w-10 h-10 rounded-full flex items-center justify-center transition-all hover:scale-110"
                    style="background: rgba(0,0,0,0.45); color: white;">
                <i class="fa-solid fa-chevron-right"></i>
            </button>
            <!-- Dots -->
            <div class="absolute bottom-4 left-1/2 -translate-x-1/2 z-20 flex gap-2">
                {"".join(dots_html)}
            </div>
        </div>
        <script>
        (function(){{
            var cur = 0;
            var total = {total};
            var timer = null;
            function showSlide(n) {{
                var slides = document.querySelectorAll('.carousel-slide');
                var dots = document.querySelectorAll('.carousel-dot');
                cur = (n + total) % total;
                slides.forEach(function(s, i) {{
                    s.style.opacity = i === cur ? '1' : '0';
                    s.style.zIndex = i === cur ? '1' : '0';
                }});
                dots.forEach(function(d, i) {{
                    d.style.opacity = i === cur ? '1' : '0.4';
                }});
            }}
            window.goSlide = showSlide;
            window.nextSlide = function() {{ showSlide(cur + 1); resetTimer(); }};
            window.prevSlide = function() {{ showSlide(cur - 1); resetTimer(); }};
            function resetTimer() {{
                clearInterval(timer);
                timer = setInterval(function() {{ showSlide(cur + 1); }}, 6000);
            }}
            var wrap = document.getElementById('carousel-wrap');
            if (wrap) {{
                wrap.addEventListener('mouseenter', function() {{ clearInterval(timer); }});
                wrap.addEventListener('mouseleave', function() {{ resetTimer(); }});
            }}
            resetTimer();
        }})();
        </script>"""


@_component("GalleryGrid")
def _gallery_grid(p: Dict[str, Any]) -> str:
    """Uniform 3×3 Instagram-style grid. Equal sizing, 2px gutter. Hover: zoom + caption."""
    imgs = p.get("images", [])

    cells = []
    for img in imgs:
        caption = img.get("caption", img.get("alt", ""))
        caption_html = ""
        if caption:
            caption_html = f"""                <!-- Caption fade on hover -->
                <div class="absolute inset-0 flex items-end p-3 opacity-0 group-hover:opacity-100 transition-opacity duration-300"
                     style="background: linear-gradient(to top, rgba(0,0,0,0.65), transparent);">
                    <p class="text-white text-xs font-medium leading-tight">{_esc(caption)}</p>
                </div>"""
        cells.append(f"""            <div class="relative overflow-hidden group" style="aspect-ratio: 1;">
                <img src="{_esc(img['url'])}" alt="{_esc(img['alt'])}"
                     class="w-full h-full object-cover transition-transform duration-500 group-hover:scale-110" loading="lazy"
                     onerror="this.onerror=null;this.style.display='none';this.nextElementSibling.style.display='flex';">
                <div class="w-full h-full items-center justify-center" style="display:none;background:linear-gradient(135deg,var(--color-primary),var(--color-secondary));">
                    <i class="fa-solid fa-image text-3xl text-white/30"></i>
                </div>
{caption_html}
            </div>""")

    subtitle = ""
    if p.get("subtitle"):
        subtitle = f'        <p class="mt-3 text-lg" style="color: var(--color-text-muted);">{_esc(p["subtitle"])}</p>'

    return f"""        <div class="text-center mb-12">
            <div class="accent-line mx-auto mb-6"></div>
            <h2 class="text-4xl md:text-5xl font-bold tracking-tight" style="font-family: var(--font-heading); color: var(--color-text);">{_esc(p.get('heading','Galeri'))}</h2>
{subtitle}
        </div>
        <div class="grid grid-cols-3" style="gap: 2px;">
{chr(10).join(cells)}
        </div>"""


@_component("GalleryFullWidth")
def _gallery_full_width(p: Dict[str, Any]) -> str:
    """Vertical magazine-feature narrative. Photo → paragraph → half-photo → text → photo."""
    imgs = p.get("images", [])
    paragraphs = p.get("paragraphs", [])

    # Build alternating layout blocks
    blocks = []
    img_idx = 0

    # Block 1: full-width hero image
    if img_idx < len(imgs):
        img = imgs[img_idx]; img_idx += 1
        blocks.append(f"""        <!-- Full-width opening photo -->
        <div class="overflow-hidden rounded-2xl" style="max-height: 520px;">
            <img src="{_esc(img['url'])}" alt="{_esc(img['alt'])}"
                 class="w-full object-cover transition-transform duration-700 hover:scale-105" loading="lazy"
                 style="max-height: 520px; object-position: center;">
        </div>""")

    # Block 2: first paragraph
    if paragraphs:
        para = paragraphs[0]
        blocks.append(f"""        <div class="max-w-2xl">
            <p class="text-lg leading-relaxed" style="color: var(--color-text-muted);">{_esc(para)}</p>
        </div>""")

    # Block 3: half-image left + text right
    if img_idx < len(imgs) and len(paragraphs) > 1:
        img = imgs[img_idx]; img_idx += 1
        para2 = paragraphs[1]
        blocks.append(f"""        <!-- Half-image + text -->
        <div class="grid grid-cols-1 md:grid-cols-2 gap-8 items-center">
            <div class="overflow-hidden rounded-2xl">
                <img src="{_esc(img['url'])}" alt="{_esc(img['alt'])}"
                     class="w-full object-cover" style="height: 360px;" loading="lazy">
            </div>
            <div>
                <p class="text-lg leading-relaxed" style="color: var(--color-text-muted);">{_esc(para2)}</p>
            </div>
        </div>""")

    # Block 4: closing full-width image
    if img_idx < len(imgs):
        img = imgs[img_idx]; img_idx += 1
        blocks.append(f"""        <!-- Closing full-width photo -->
        <div class="overflow-hidden rounded-2xl" style="max-height: 440px;">
            <img src="{_esc(img['url'])}" alt="{_esc(img['alt'])}"
                 class="w-full object-cover" style="max-height: 440px; object-position: center;" loading="lazy">
        </div>""")

    subtitle = ""
    if p.get("subtitle"):
        subtitle = f'        <p class="mt-3 text-lg" style="color: var(--color-text-muted);">{_esc(p["subtitle"])}</p>'

    return f"""        <div class="mb-14">
            <div class="accent-line mb-6"></div>
            <h2 class="text-4xl md:text-5xl font-bold tracking-tight" style="font-family: var(--font-heading); color: var(--color-text);">{_esc(p.get('heading','Kisah Kami'))}</h2>
{subtitle}
        </div>
        <div class="space-y-10">
{chr(10).join(blocks)}
        </div>"""


# ---------------------------------------------------------------------------
# Contact Variants — form, simple, cards overlay
# ---------------------------------------------------------------------------

@_component("ContactForm")
def _contact_form(p: Dict[str, Any]) -> str:
    """Booking form centered — Name, Phone, Date, Time, Pax. WhatsApp secondary. Map below."""
    wa_num = p.get("whatsapp_number", "")
    wa_msg = p.get("whatsapp_message", "Saya ingin membuat tempahan meja di restoran anda.")

    # WhatsApp submission — builds pre-filled message from form
    form_html = f"""        <div class="max-w-2xl mx-auto">
            <form id="booking-form" class="rounded-2xl p-8 md:p-10 space-y-5" style="background-color: var(--color-surface); box-shadow: var(--shadow-lg);">
                <div class="grid grid-cols-1 sm:grid-cols-2 gap-5">
                    <div>
                        <label class="block text-sm font-semibold mb-1.5" style="color: var(--color-text);">Nama</label>
                        <input type="text" id="bk-name" placeholder="Nama penuh" required
                               class="w-full rounded-xl px-4 py-3 text-sm outline-none transition-shadow focus:ring-2"
                               style="background: var(--color-background); border: 1px solid var(--color-border); color: var(--color-text); --tw-ring-color: var(--color-primary);">
                    </div>
                    <div>
                        <label class="block text-sm font-semibold mb-1.5" style="color: var(--color-text);">No. Telefon</label>
                        <input type="tel" id="bk-phone" placeholder="01X-XXXXXXXX" required
                               class="w-full rounded-xl px-4 py-3 text-sm outline-none"
                               style="background: var(--color-background); border: 1px solid var(--color-border); color: var(--color-text);">
                    </div>
                    <div>
                        <label class="block text-sm font-semibold mb-1.5" style="color: var(--color-text);">Tarikh</label>
                        <input type="date" id="bk-date" required
                               class="w-full rounded-xl px-4 py-3 text-sm outline-none"
                               style="background: var(--color-background); border: 1px solid var(--color-border); color: var(--color-text);">
                    </div>
                    <div>
                        <label class="block text-sm font-semibold mb-1.5" style="color: var(--color-text);">Masa</label>
                        <select id="bk-time" class="w-full rounded-xl px-4 py-3 text-sm outline-none appearance-none"
                                style="background: var(--color-background); border: 1px solid var(--color-border); color: var(--color-text);">
                            <option value="">Pilih masa</option>
                            <option>11:00 pagi</option><option>12:00 tengah hari</option>
                            <option>1:00 petang</option><option>2:00 petang</option>
                            <option>6:00 petang</option><option>7:00 petang</option>
                            <option>8:00 malam</option><option>9:00 malam</option>
                        </select>
                    </div>
                    <div class="sm:col-span-2">
                        <label class="block text-sm font-semibold mb-1.5" style="color: var(--color-text);">Bilangan Tetamu</label>
                        <div class="flex items-center gap-3">
                            <button type="button" onclick="document.getElementById('bk-pax').stepDown()" class="w-10 h-10 rounded-full flex items-center justify-center font-bold text-lg transition-colors hover:opacity-80" style="background-color: var(--color-primary); color: white;">−</button>
                            <input type="number" id="bk-pax" value="2" min="1" max="20"
                                   class="w-20 text-center rounded-xl px-2 py-3 text-lg font-bold outline-none"
                                   style="background: var(--color-background); border: 1px solid var(--color-border); color: var(--color-text);">
                            <button type="button" onclick="document.getElementById('bk-pax').stepUp()" class="w-10 h-10 rounded-full flex items-center justify-center font-bold text-lg transition-colors hover:opacity-80" style="background-color: var(--color-primary); color: white;">+</button>
                        </div>
                    </div>
                </div>
                <button type="submit" class="w-full py-4 rounded-xl font-bold text-white text-base transition-opacity hover:opacity-90" style="background-color: var(--color-primary);">
                    Hantar Tempahan
                </button>
            </form>
            <!-- WhatsApp secondary -->
            <div class="mt-5 text-center">
                <p class="text-sm mb-3" style="color: var(--color-text-muted);">atau tempah terus melalui</p>
                <a href="https://wa.me/{_esc(wa_num)}?text={_esc(wa_msg)}" target="_blank" rel="noopener noreferrer"
                   class="inline-flex items-center gap-2 font-semibold rounded-xl px-6 py-3 text-white transition-opacity hover:opacity-90"
                   style="background-color: #25D366;">
                    <i class="fa-brands fa-whatsapp text-xl"></i> WhatsApp
                </a>
            </div>
        </div>"""

    map_html = ""
    if p.get("show_map") and (p.get("map_query") or p.get("address")):
        query = p.get("map_query") or p.get("address", "")
        map_html = f"""        <div class="map-container mt-10 rounded-2xl overflow-hidden" style="box-shadow: var(--shadow);">
            <iframe src="https://maps.google.com/maps?q={_esc(query)}&output=embed"
                    width="100%" height="300" style="border:0;" allowfullscreen loading="lazy"
                    referrerpolicy="no-referrer-when-downgrade" title="Location map"></iframe>
        </div>"""

    return f"""        <div class="text-center mb-12">
            <div class="accent-line mx-auto mb-6"></div>
            <h2 class="text-4xl md:text-5xl font-bold tracking-tight" style="font-family: var(--font-heading); color: var(--color-text);">{_esc(p.get('heading','Tempahan'))}</h2>
        </div>
{form_html}
{map_html}
        <script>
        document.getElementById('booking-form').addEventListener('submit', function(e) {{
            e.preventDefault();
            var name = document.getElementById('bk-name').value;
            var phone = document.getElementById('bk-phone').value;
            var date = document.getElementById('bk-date').value;
            var time = document.getElementById('bk-time').value;
            var pax = document.getElementById('bk-pax').value;
            var msg = 'Salam, saya ' + name + ' ingin membuat tempahan meja.%0A%0ATarikh: ' + date + '%0AMasa: ' + time + '%0ABilangan: ' + pax + ' orang%0ATelefon: ' + phone;
            window.open('https://wa.me/{_esc(wa_num)}?text=' + msg, '_blank');
        }});
        </script>"""


@_component("ContactSimple")
def _contact_simple(p: Dict[str, Any]) -> str:
    """Minimal essential — hours + WhatsApp CTA + address. No map, no form. Centered."""
    wa_num = p.get("whatsapp_number", "")
    wa_msg = p.get("whatsapp_message", "Salam! Saya nak dapatkan maklumat lanjut.")

    hours_html = ""
    if p.get("hours_structured"):
        rows = "\n".join(
            f'                <div class="flex justify-between items-center py-3" style="border-bottom: 1px solid var(--color-border);">'
            f'<span class="font-medium" style="color: var(--color-text);">{_esc(h["day"])}</span>'
            f'<span class="text-sm" style="color: var(--color-text-muted);">{_esc(h["time"])}</span></div>'
            for h in p["hours_structured"]
        )
        hours_html = f"""            <div class="rounded-2xl p-6" style="background-color: var(--color-surface); box-shadow: var(--shadow);">
                <div class="flex items-center gap-2 mb-4">
                    <i class="fa-solid fa-clock" style="color: var(--color-primary);"></i>
                    <p class="font-bold" style="color: var(--color-text);">Waktu Operasi</p>
                </div>
{rows}
            </div>"""
    elif p.get("hours"):
        hours_html = f"""            <p class="text-base" style="color: var(--color-text-muted);">
                <i class="fa-solid fa-clock mr-2" style="color: var(--color-primary);"></i>{_esc(p['hours'])}
            </p>"""

    address_html = ""
    if p.get("address"):
        address_html = f"""            <div class="flex items-start gap-3">
                <i class="fa-solid fa-location-dot mt-1 shrink-0" style="color: var(--color-primary);"></i>
                <p class="text-base" style="color: var(--color-text-muted);">{_esc(p['address'])}</p>
            </div>"""

    return f"""        <div class="max-w-lg mx-auto text-center">
            <div class="accent-line mx-auto mb-6"></div>
            <h2 class="text-4xl md:text-5xl font-bold tracking-tight mb-10" style="font-family: var(--font-heading); color: var(--color-text);">{_esc(p.get('heading','Hubungi Kami'))}</h2>
            <!-- Big WhatsApp CTA -->
            <a href="https://wa.me/{_esc(wa_num)}?text={_esc(wa_msg)}" target="_blank" rel="noopener noreferrer"
               class="inline-flex items-center gap-3 text-white font-bold text-lg rounded-2xl px-10 py-5 transition-transform hover:scale-105 mb-10"
               style="background-color: #25D366; box-shadow: 0 8px 24px -4px rgba(37,211,102,0.4);">
                <i class="fa-brands fa-whatsapp text-2xl"></i>
                {_esc(p.get('whatsapp_cta', 'WhatsApp Kami'))}
            </a>
            <div class="space-y-6 text-left">
{hours_html}
{address_html}
            </div>
        </div>"""


@_component("ContactCards")
def _contact_cards(p: Dict[str, Any]) -> str:
    """Glassmorphic contact card over restaurant interior background photo."""
    bg_url = p.get("background_image_url", "")
    wa_num = p.get("whatsapp_number", "")
    wa_msg = p.get("whatsapp_message", "Salam! Saya ingin hubungi restoran anda.")

    hours_html = ""
    if p.get("hours_structured"):
        rows = "\n".join(
            f'                    <div class="flex justify-between py-1.5 text-sm">'
            f'<span class="font-medium text-white/90">{_esc(h["day"])}</span>'
            f'<span class="text-white/70">{_esc(h["time"])}</span></div>'
            for h in p["hours_structured"]
        )
        hours_html = f"""                <div class="mt-5 pt-5" style="border-top: 1px solid rgba(255,255,255,0.2);">
                    <p class="text-xs font-bold uppercase tracking-widest text-white/60 mb-3">Waktu Operasi</p>
{rows}
                </div>"""

    bg_style = f'background-image: url("{_esc(bg_url)}"); background-size: cover; background-position: center;' if bg_url else f'background: linear-gradient(135deg, var(--color-primary), var(--color-secondary));'

    return f"""        <div class="relative min-h-96 flex items-center justify-center rounded-2xl overflow-hidden py-16 px-4"
             style="{bg_style}">
            <!-- Dark overlay for readability -->
            <div class="absolute inset-0" style="background: rgba(0,0,0,0.45); backdrop-filter: blur(0px);"></div>
            <!-- Glassmorphic card -->
            <div class="relative z-10 w-full max-w-md rounded-2xl p-8 text-white"
                 style="background: rgba(255,255,255,0.12); backdrop-filter: blur(16px); border: 1px solid rgba(255,255,255,0.25); box-shadow: 0 20px 60px rgba(0,0,0,0.3);">
                <div class="accent-line mb-5" style="background: rgba(255,255,255,0.6);"></div>
                <h2 class="text-3xl font-bold mb-6 text-white" style="font-family: var(--font-heading);">{_esc(p.get('heading','Hubungi Kami'))}</h2>
                <!-- WhatsApp CTA -->
                <a href="https://wa.me/{_esc(wa_num)}?text={_esc(wa_msg)}" target="_blank" rel="noopener noreferrer"
                   class="inline-flex items-center gap-3 font-bold rounded-xl px-6 py-3.5 text-white transition-opacity hover:opacity-90 mb-5"
                   style="background-color: #25D366;">
                    <i class="fa-brands fa-whatsapp text-xl"></i>
                    {_esc(p.get('whatsapp_cta', 'WhatsApp Kami'))}
                </a>
                <!-- Address -->
                {f'<div class="flex items-start gap-3 mt-4"><i class="fa-solid fa-location-dot mt-0.5 text-white/70"></i><p class="text-sm text-white/80">{_esc(p["address"])}</p></div>' if p.get("address") else ""}
{hours_html}
            </div>
        </div>"""


# ---------------------------------------------------------------------------
# Footer Variants — minimal, columns (rich)
# ---------------------------------------------------------------------------

@_component("FooterMinimal")
def _footer_minimal(p: Dict[str, Any]) -> str:
    """Compact footer — name, tagline, social icons, copyright."""
    year = p.get("copyright_year", 2026)

    social_html = ""
    if p.get("social_links"):
        icons = " ".join(
            f'<a href="{_esc(link["url"])}" target="_blank" rel="noopener noreferrer"'
            f' class="opacity-60 hover:opacity-100 transition-opacity"'
            f' style="color: var(--color-background);" aria-label="{_esc(link["platform"])}">'
            f'<i class="{_esc(link["icon"])} text-lg"></i></a>'
            for link in p["social_links"]
        )
        social_html = f'            <div class="flex gap-4">{icons}</div>'

    powered = ""
    if p.get("powered_by", True):
        powered = '<span class="opacity-50"> · Dibina dengan <a href="https://binaapp.my" target="_blank" class="font-semibold hover:opacity-100" style="opacity: 0.7;">BinaApp</a></span>'

    return f"""    <footer class="py-8 px-4 sm:px-6 lg:px-8" style="background-color: var(--color-text); color: var(--color-background);">
        <div class="mx-auto" style="max-width: var(--max-width, 1280px);">
            <div class="flex flex-col sm:flex-row items-center justify-between gap-4">
                <div class="text-center sm:text-left">
                    <p class="font-bold text-lg" style="font-family: var(--font-heading);">{_esc(p.get('business_name',''))}</p>
                    {f'<p class="text-xs opacity-50 mt-0.5">{_esc(p["tagline"])}</p>' if p.get("tagline") else ""}
                </div>
{social_html}
                <p class="text-xs opacity-40">&copy; {year} {_esc(p.get('business_name',''))}{powered}</p>
            </div>
        </div>
    </footer>"""


@_component("FooterColumns")
def _footer_columns(p: Dict[str, Any]) -> str:
    """Rich footer — newsletter, social icons, 3 link columns, copyright + BinaApp credit."""
    year = p.get("copyright_year", 2026)
    wa_num = p.get("whatsapp_number", "")

    # Social icons
    social_html = ""
    if p.get("social_links"):
        icons = "\n".join(
            f'                <a href="{_esc(link["url"])}" target="_blank" rel="noopener noreferrer"'
            f' class="w-9 h-9 rounded-full flex items-center justify-center transition-opacity hover:opacity-80"'
            f' style="background-color: rgba(255,255,255,0.15);" aria-label="{_esc(link["platform"])}">'
            f'<i class="{_esc(link["icon"])} text-sm text-white"></i></a>'
            for link in p["social_links"]
        )
        social_html = f'            <div class="flex gap-3 mt-4">\n{icons}\n            </div>'

    # Newsletter
    newsletter_html = ""
    if p.get("newsletter", True):
        subscribe_label = _esc(p.get("newsletter_cta", "Sertai"))
        newsletter_html = f"""            <div class="mt-8 lg:mt-0">
                <p class="text-sm font-semibold text-white/80 mb-3">Dapatkan Tawaran Terkini</p>
                <form class="flex gap-2" onsubmit="event.preventDefault(); alert('Terima kasih!');">
                    <input type="email" placeholder="emel@contoh.com" required
                           class="flex-1 rounded-xl px-4 py-2.5 text-sm outline-none"
                           style="background: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.2); color: white; min-width: 0;">
                    <button type="submit" class="px-5 py-2.5 rounded-xl text-sm font-bold transition-opacity hover:opacity-90 whitespace-nowrap"
                            style="background-color: var(--color-primary); color: white;">{subscribe_label}</button>
                </form>
            </div>"""

    # Link columns
    link_cols = p.get("link_columns", [
        {"title": "Menu", "links": [{"label": "Hidangan Utama", "href": "#menu"}, {"label": "Minuman", "href": "#menu"}, {"label": "Manisan", "href": "#menu"}]},
        {"title": "Tentang", "links": [{"label": "Kisah Kami", "href": "#about"}, {"label": "Galeri", "href": "#gallery"}]},
        {"title": "Hubungi", "links": [{"label": "Lokasi", "href": "#contact"}, {"label": "Tempahan", "href": "#contact"}]},
    ])
    cols_html = "\n".join(
        f"""            <div>
                <p class="text-sm font-bold uppercase tracking-widest mb-4 text-white/60">{_esc(col['title'])}</p>
                <ul class="space-y-2">
                    {''.join(f"<li><a href='{_esc(lnk.get('href','#'))}' class='text-sm text-white/60 hover:text-white transition-colors'>{_esc(lnk.get('label',''))}</a></li>" for lnk in col.get('links', []))}
                </ul>
            </div>"""
        for col in link_cols
    )

    powered = ""
    if p.get("powered_by", True):
        powered = '<span> · Dibina dengan <a href="https://binaapp.my" target="_blank" class="font-semibold hover:opacity-100 transition-opacity" style="opacity: 0.7;">BinaApp</a></span>'

    return f"""    <footer style="background-color: var(--color-text); color: white;">
        <!-- Top bar -->
        <div class="px-4 sm:px-6 lg:px-8 py-14 border-b" style="border-color: rgba(255,255,255,0.08);">
            <div class="mx-auto grid grid-cols-1 lg:grid-cols-5 gap-12" style="max-width: var(--max-width, 1280px);">
                <!-- Brand col (2/5) -->
                <div class="lg:col-span-2">
                    <h3 class="text-2xl font-bold text-white" style="font-family: var(--font-heading);">{_esc(p.get('business_name',''))}</h3>
                    {f'<p class="mt-1 text-sm opacity-50">{_esc(p["tagline"])}</p>' if p.get("tagline") else ""}
{social_html}
{newsletter_html}
                </div>
                <!-- Link columns (3/5) -->
                <div class="lg:col-span-3 grid grid-cols-2 sm:grid-cols-3 gap-8">
{cols_html}
                </div>
            </div>
        </div>
        <!-- Bottom bar -->
        <div class="px-4 sm:px-6 lg:px-8 py-5">
            <div class="mx-auto flex flex-col sm:flex-row items-center justify-between gap-2 text-xs text-white/40"
                 style="max-width: var(--max-width, 1280px);">
                <p>&copy; {year} {_esc(p.get('business_name',''))}{powered}</p>
                {f'<a href="https://wa.me/{_esc(wa_num)}" target="_blank" class="flex items-center gap-1.5 opacity-50 hover:opacity-80 transition-opacity text-white"><i class="fa-brands fa-whatsapp"></i> +{_esc(wa_num)}</a>' if wa_num else ""}
            </div>
        </div>
    </footer>"""


# ---------------------------------------------------------------------------
# Testimonial Variants — slider (reviews_carousel), quote (reviews_pull_quote)
# ---------------------------------------------------------------------------

@_component("TestimonialSlider")
def _testimonial_slider(p: Dict[str, Any]) -> str:
    """Rotating testimonial carousel — auto-advance every 6s, pause on hover."""
    reviews = p.get("reviews", [])
    if not reviews:
        return '<div class="text-center py-16" style="color:var(--color-text-muted);">Tiada ulasan lagi.</div>'

    cards = []
    for i, r in enumerate(reviews):
        stars = "".join(
            f'<i class="fa-{"solid" if j < r.get("rating", 5) else "regular"} fa-star text-sm" style="color: {"#F59E0B" if j < r.get("rating", 5) else "var(--color-text-muted)"};"></i>'
            for j in range(5)
        )
        initial = r.get("avatar_fallback", r.get("name", "?")[0].upper())
        cards.append(
            f'<div class="review-slide absolute inset-0 flex items-center justify-center px-4 transition-opacity duration-500"'
            f' style="opacity: {"1" if i == 0 else "0"}; z-index: {"1" if i == 0 else "0"};">'
            f'<div class="max-w-xl w-full mx-auto text-center">'
            f'<div class="flex justify-center gap-1 mb-5">{stars}</div>'
            f'<p class="text-xl sm:text-2xl leading-relaxed italic" style="font-family: var(--font-heading); color: var(--color-text);">&ldquo;{_esc(r["text"])}&rdquo;</p>'
            f'<div class="mt-8 flex items-center justify-center gap-3">'
            f'<div class="w-11 h-11 rounded-full flex items-center justify-center text-sm font-bold text-white" style="background-color: var(--color-primary);">{initial}</div>'
            f'<span class="font-semibold" style="color: var(--color-text);">{_esc(r.get("name",""))}</span>'
            f'</div>'
            f'</div></div>'
        )

    dots_html = " ".join(
        f'<button class="rev-dot w-2 h-2 rounded-full transition-all duration-300 cursor-pointer" data-idx="{i}" '
        f'style="background-color: var(--color-primary); opacity: {"1" if i == 0 else "0.3"};" onclick="goRev({i})"></button>'
        for i in range(len(reviews))
    )

    total = len(reviews)
    return f"""        <div class="text-center mb-14">
            <h2 class="text-4xl md:text-5xl font-bold tracking-tight" style="font-family: var(--font-heading); color: var(--color-text);">{_esc(p.get('heading','Kata Pelanggan Kami'))}</h2>
        </div>
        <div id="rev-wrap" class="relative" style="min-height: 260px;">
{chr(10).join(cards)}
        </div>
        <div class="flex justify-center gap-3 mt-8">{dots_html}</div>
        <script>
        (function(){{
            var cur = 0; var total = {total}; var timer = null;
            function show(n) {{
                cur = (n + total) % total;
                document.querySelectorAll('.review-slide').forEach(function(s, i) {{
                    s.style.opacity = i === cur ? '1' : '0';
                    s.style.zIndex = i === cur ? '1' : '0';
                }});
                document.querySelectorAll('.rev-dot').forEach(function(d, i) {{
                    d.style.opacity = i === cur ? '1' : '0.3';
                }});
            }}
            window.goRev = show;
            function reset() {{ clearInterval(timer); timer = setInterval(function() {{ show(cur + 1); }}, 6000); }}
            var wrap = document.getElementById('rev-wrap');
            if (wrap) {{
                wrap.addEventListener('mouseenter', function() {{ clearInterval(timer); }});
                wrap.addEventListener('mouseleave', reset);
            }}
            reset();
        }})();
        </script>"""


@_component("TestimonialQuote")
def _testimonial_quote(p: Dict[str, Any]) -> str:
    """Single elevated review — large display serif pull-quote with brand background."""
    reviews = p.get("reviews", [])
    r = reviews[0] if reviews else {}

    stars = "".join(
        f'<i class="fa-solid fa-star text-base" style="color: #F59E0B;"></i>'
        for _ in range(r.get("rating", 5))
    )
    initial = r.get("avatar_fallback", r.get("name", "?")[0].upper())

    return f"""        <div class="rounded-3xl px-8 py-16 md:px-20 text-center relative overflow-hidden"
             style="background: linear-gradient(135deg, var(--color-accent), var(--color-surface));">
            <!-- Ghost typography backdrop -->
            <div class="absolute -top-8 left-1/2 -translate-x-1/2 text-[12rem] leading-none font-black select-none pointer-events-none"
                 style="color: var(--color-primary); opacity: 0.04; font-family: var(--font-heading);">&ldquo;</div>
            <div class="relative z-10 max-w-3xl mx-auto">
                <div class="flex justify-center gap-1 mb-8">{stars}</div>
                <blockquote class="text-2xl sm:text-3xl md:text-4xl leading-snug italic mb-10"
                            style="font-family: var(--font-heading); color: var(--color-text);">
                    &ldquo;{_esc(r.get('text',''))}&rdquo;
                </blockquote>
                <div class="flex items-center justify-center gap-4">
                    <div class="w-14 h-14 rounded-full flex items-center justify-center text-lg font-bold text-white shrink-0"
                         style="background-color: var(--color-primary);">{initial}</div>
                    <div class="text-left">
                        <p class="font-bold" style="font-family: var(--font-heading); color: var(--color-text);">{_esc(r.get('name',''))}</p>
                        {f'<p class="text-sm" style="color: var(--color-text-muted);">{_esc(r.get("role","Pelanggan"))}</p>'}
                    </div>
                </div>
            </div>
        </div>"""


# ---------------------------------------------------------------------------
# Hours Section — simple_table, today_focus
# ---------------------------------------------------------------------------

@_component("HoursSimpleTable")
def _hours_simple_table(p: Dict[str, Any]) -> str:
    """Clean operating hours table — day/time pairs in a well-spaced table."""
    hours = p.get("hours_structured", [])

    rows = []
    for h in hours:
        is_closed = "tutup" in h.get("time", "").lower() or "closed" in h.get("time", "").lower()
        time_style = "color: var(--color-text-muted); opacity: 0.5;" if is_closed else "color: var(--color-text-muted);"
        rows.append(f"""                <tr style="border-bottom: 1px solid var(--color-border);">
                    <td class="py-3.5 font-medium pr-8" style="color: var(--color-text);">{_esc(h['day'])}</td>
                    <td class="py-3.5 text-right" style="{time_style}">{_esc(h['time'])}</td>
                </tr>""")

    return f"""        <div class="max-w-sm mx-auto text-center">
            <div class="accent-line mx-auto mb-6"></div>
            <h2 class="text-4xl md:text-5xl font-bold tracking-tight mb-10" style="font-family: var(--font-heading); color: var(--color-text);">{_esc(p.get('heading','Waktu Operasi'))}</h2>
            <div class="rounded-2xl p-6 text-left" style="background-color: var(--color-surface); box-shadow: var(--shadow);">
                <table class="w-full">
                    <tbody>
{chr(10).join(rows)}
                    </tbody>
                </table>
            </div>
        </div>"""


@_component("HoursTodayFocus")
def _hours_today_focus(p: Dict[str, Any]) -> str:
    """Today-focus hours — big status banner + full week table below."""
    hours = p.get("hours_structured", [])
    status_text = p.get("status_text", "Kami Buka Sekarang")
    status_sub = p.get("status_sub", "")
    is_open = p.get("is_open", True)

    status_color = "#22c55e" if is_open else "#ef4444"
    status_icon = "fa-circle-check" if is_open else "fa-circle-xmark"

    rows = []
    for h in hours:
        is_closed = "tutup" in h.get("time", "").lower() or "closed" in h.get("time", "").lower()
        row_opacity = " opacity-50" if is_closed else ""
        rows.append(f"""                <div class="flex justify-between py-2.5{row_opacity}" style="border-bottom: 1px solid var(--color-border);">
                    <span class="text-sm font-medium" style="color: var(--color-text);">{_esc(h['day'])}</span>
                    <span class="text-sm" style="color: var(--color-text-muted);">{_esc(h['time'])}</span>
                </div>""")

    sub_html = f'<p class="text-lg mt-2 opacity-80">{_esc(status_sub)}</p>' if status_sub else ""

    return f"""        <div class="max-w-md mx-auto text-center">
            <div class="accent-line mx-auto mb-8"></div>
            <!-- Big status banner -->
            <div class="rounded-2xl py-10 px-8 mb-8" style="background-color: var(--color-surface); box-shadow: var(--shadow-lg);">
                <i class="{status_icon} text-4xl mb-4" style="color: {status_color};"></i>
                <h2 class="text-3xl md:text-4xl font-bold" style="font-family: var(--font-heading); color: var(--color-text);">{_esc(status_text)}</h2>
{sub_html}
            </div>
            <!-- Full week table -->
            <h3 class="text-lg font-bold mb-4 text-left" style="color: var(--color-text);">{_esc(p.get('week_heading','Waktu Operasi Mingguan'))}</h3>
            <div class="rounded-2xl p-6 text-left" style="background-color: var(--color-surface); box-shadow: var(--shadow);">
{chr(10).join(rows)}
            </div>
        </div>"""


# ---------------------------------------------------------------------------
# CTA Section — booking_prominent, whatsapp_first
# ---------------------------------------------------------------------------

@_component("CtaBookingProminent")
def _cta_booking_prominent(p: Dict[str, Any]) -> str:
    """Large reservation CTA — headline, date/time/pax, WhatsApp pre-fill. Mobile-first."""
    wa_num = p.get("whatsapp_number", "")
    headline = _esc(p.get("headline", "Tempah Meja Sekarang"))
    subheadline = _esc(p.get("subheadline", "Jangan lepas peluang menikmati hidangan terbaik kami."))

    return f"""        <div class="rounded-3xl px-6 py-16 md:px-16 text-center relative overflow-hidden"
             style="background: linear-gradient(135deg, var(--color-primary), var(--color-secondary));">
            <!-- Ghost oversized numeral backdrop -->
            <div class="absolute top-0 right-0 text-[20rem] leading-none font-black select-none pointer-events-none opacity-5 text-white"
                 style="font-family: var(--font-heading);">T</div>
            <div class="relative z-10 max-w-xl mx-auto">
                <h2 class="text-4xl md:text-5xl font-bold text-white mb-4 leading-tight" style="font-family: var(--font-heading);">{headline}</h2>
                <p class="text-white/80 text-lg mb-10">{subheadline}</p>
                <!-- Quick booking form -->
                <div class="rounded-2xl p-6 mb-6" style="background: rgba(255,255,255,0.12); backdrop-filter: blur(8px); border: 1px solid rgba(255,255,255,0.2);">
                    <div class="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-5">
                        <div>
                            <label class="block text-xs font-bold text-white/70 mb-1.5 uppercase tracking-wider">Tarikh</label>
                            <input type="date" id="cta-date" class="w-full rounded-xl px-3 py-2.5 text-sm outline-none"
                                   style="background: rgba(255,255,255,0.15); border: 1px solid rgba(255,255,255,0.25); color: white;">
                        </div>
                        <div>
                            <label class="block text-xs font-bold text-white/70 mb-1.5 uppercase tracking-wider">Masa</label>
                            <select id="cta-time" class="w-full rounded-xl px-3 py-2.5 text-sm outline-none appearance-none"
                                    style="background: rgba(255,255,255,0.15); border: 1px solid rgba(255,255,255,0.25); color: white;">
                                <option value="">Pilih masa</option>
                                <option>12:00 tgh</option><option>1:00 ptg</option><option>6:00 ptg</option>
                                <option>7:00 mlm</option><option>8:00 mlm</option>
                            </select>
                        </div>
                        <div>
                            <label class="block text-xs font-bold text-white/70 mb-1.5 uppercase tracking-wider">Tetamu</label>
                            <select id="cta-pax" class="w-full rounded-xl px-3 py-2.5 text-sm outline-none appearance-none"
                                    style="background: rgba(255,255,255,0.15); border: 1px solid rgba(255,255,255,0.25); color: white;">
                                {"".join(f'<option value="{i}">{i} orang</option>' for i in range(1, 13))}
                            </select>
                        </div>
                    </div>
                    <button onclick="ctaBook()" class="w-full py-4 rounded-xl font-bold text-base transition-opacity hover:opacity-90"
                            style="background-color: white; color: var(--color-primary);">
                        <i class="fa-brands fa-whatsapp mr-2"></i>Tempah via WhatsApp
                    </button>
                </div>
            </div>
        </div>
        <script>
        function ctaBook() {{
            var date = document.getElementById('cta-date').value || 'Belum dipilih';
            var time = document.getElementById('cta-time').value || 'Belum dipilih';
            var pax = document.getElementById('cta-pax').value || '2';
            var msg = 'Salam! Saya ingin tempah meja.%0ATarikh: ' + date + '%0AMasa: ' + time + '%0AJumlah tetamu: ' + pax + ' orang';
            window.open('https://wa.me/{_esc(wa_num)}?text=' + msg, '_blank');
        }}
        </script>"""


@_component("CtaWhatsappFirst")
def _cta_whatsapp_first(p: Dict[str, Any]) -> str:
    """Single huge WhatsApp CTA — pre-filled message, mobile-first. Minimal design."""
    wa_num = p.get("whatsapp_number", "")
    wa_msg = p.get("whatsapp_message", "Salam Khulafa Bistro, saya nak tempah meja...")
    headline = _esc(p.get("headline", "Bercakap Terus dengan Kami"))
    subheadline = _esc(p.get("subheadline", "Tempah meja, tanya menu, atau sebarang pertanyaan — kami sentiasa bersedia."))

    supporting = p.get("supporting_info", [])
    info_html = ""
    if supporting:
        items_html = "".join(
            f'<div class="flex items-center gap-2 text-sm" style="color: var(--color-text-muted);"><i class="{_esc(item.get("icon","fa-solid fa-check"))} text-xs" style="color: var(--color-primary);"></i>{_esc(item.get("text",""))}</div>'
            for item in supporting
        )
        info_html = f'<div class="flex flex-wrap justify-center gap-x-6 gap-y-2 mb-8">{items_html}</div>'

    return f"""        <div class="max-w-lg mx-auto text-center">
            <div class="accent-line mx-auto mb-6"></div>
            <h2 class="text-4xl md:text-5xl font-bold tracking-tight mb-4" style="font-family: var(--font-heading); color: var(--color-text);">{headline}</h2>
            <p class="text-lg leading-relaxed mb-8" style="color: var(--color-text-muted);">{subheadline}</p>
{info_html}
            <!-- Oversized WhatsApp button -->
            <a href="https://wa.me/{_esc(wa_num)}?text={_esc(wa_msg)}" target="_blank" rel="noopener noreferrer"
               class="inline-flex items-center justify-center gap-4 font-bold text-2xl text-white rounded-3xl px-12 py-7 transition-transform hover:scale-105 active:scale-95 w-full sm:w-auto"
               style="background-color: #25D366; box-shadow: 0 16px 40px -8px rgba(37,211,102,0.45);">
                <i class="fa-brands fa-whatsapp text-4xl"></i>
                WhatsApp Kami
            </a>
            <p class="mt-5 text-xs" style="color: var(--color-text-muted);">Respon dalam masa 15 minit &bull; Buka {p.get('hours_short', 'Sel-Ahad 11pg-10mlm')}</p>
        </div>"""


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
