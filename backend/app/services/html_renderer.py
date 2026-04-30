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
                        <i class="fa-solid fa-certificate"></i> Halal Certified
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
                <i class="fa-solid fa-certificate"></i> Halal Certified
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
                    <i class="fa-solid fa-certificate"></i> Halal Certified
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
                        <i class="fa-solid fa-certificate"></i> Halal Certified
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
    paras = p.get("paragraphs", [])
    # First paragraph as pull-quote if there are multiple
    pull_quote = ""
    body_paras = paras
    if len(paras) > 1:
        pull_quote = f"""            <blockquote class="text-xl sm:text-2xl font-medium italic leading-snug pl-5 mt-6"
                style="font-family: var(--font-heading); color: var(--color-text); border-left: 3px solid var(--color-primary);">
                {_esc(paras[0])}
            </blockquote>"""
        body_paras = paras[1:]

    paragraphs = "\n".join(
        f'            <p class="text-base sm:text-lg leading-relaxed" style="color: var(--color-text-muted);">{_esc(para)}</p>'
        for para in body_paras
    )

    signature = ""
    if p.get("signature"):
        signature = f"""            <div class="mt-8 pt-6" style="border-top: 1px solid var(--color-border);">
                <p class="text-sm font-semibold tracking-wide uppercase" style="color: var(--color-primary);">{_esc(p['signature'])}</p>
            </div>"""

    img_html = ""
    if p.get("image_url"):
        img_html = f"""        <div class="relative lg:-ml-6 lg:mt-8">
            <img src="{_esc(p['image_url'])}" alt="{_esc(p.get('image_alt', ''))}"
                 class="w-full rounded-2xl object-cover relative z-10"
                 style="max-height: 500px; box-shadow: 0 20px 40px -12px rgba(0,0,0,0.15);" loading="lazy">
            <div class="hidden lg:block absolute -top-4 -left-4 w-3/4 h-3/4 rounded-2xl z-0"
                 style="background-color: var(--color-accent); opacity: 0.3;"></div>
        </div>"""

    pos = p.get("image_position", "left")
    text_cell = f"""        <div class="flex flex-col justify-center">
            <div class="accent-line mb-6"></div>
            <h2 class="text-4xl md:text-5xl font-bold tracking-tight" style="font-family: var(--font-heading); color: var(--color-text);">
                {_esc(p['heading'])}
            </h2>
{pull_quote}
            <div class="mt-6 space-y-4">
{paragraphs}
            </div>
{signature}
        </div>"""

    cells = [img_html, text_cell]
    if pos == "right":
        cells = list(reversed(cells))

    return f"""        <div class="grid grid-cols-1 lg:grid-cols-2 gap-12 lg:gap-20 items-center">
{cells[0]}
{cells[1]}
        </div>"""


@_component("AboutStats")
def _about_stats(p: Dict[str, Any]) -> str:
    """Metrics row (years, dishes served, ratings) with brief text below.
    Data-driven trust — numbers speak louder."""
    stats = p.get("stats", [])
    stat_items = []
    for idx, stat in enumerate(stats):
        delay = idx * 100
        stat_items.append(f"""            <div class="text-center p-6" data-aos="fade-up" data-aos-delay="{delay}">
                <div class="text-4xl sm:text-5xl md:text-6xl font-black"
                     style="font-family: var(--font-heading); color: var(--color-primary); line-height: 1;">
                    {_esc(stat.get('value', ''))}
                </div>
                <p class="mt-3 text-sm sm:text-base font-medium uppercase tracking-wider"
                   style="color: var(--color-text-muted); letter-spacing: 0.1em;">
                    {_esc(stat.get('label', ''))}
                </p>
            </div>""")

    stats_grid = "\n".join(stat_items)

    description = ""
    if p.get("description"):
        description = f"""        <p class="mt-10 text-base sm:text-lg leading-relaxed text-center max-w-2xl mx-auto"
           style="color: var(--color-text-muted);">
            {_esc(p['description'])}
        </p>"""

    quote = ""
    if p.get("quote") and p.get("quote_author"):
        quote = f"""        <div class="mt-12 text-center">
            <blockquote class="text-xl sm:text-2xl font-medium italic leading-snug max-w-xl mx-auto"
                        style="font-family: var(--font-heading); color: var(--color-text);">
                &ldquo;{_esc(p['quote'])}&rdquo;
            </blockquote>
            <p class="mt-4 text-sm font-semibold tracking-wide uppercase"
               style="color: var(--color-primary);">
                — {_esc(p['quote_author'])}
            </p>
        </div>"""

    return f"""        <div class="text-center mb-12">
            <div class="accent-line mx-auto mb-6"></div>
            <h2 class="text-4xl md:text-5xl font-bold tracking-tight"
                style="font-family: var(--font-heading); color: var(--color-text);">
                {_esc(p['heading'])}
            </h2>
        </div>
        <div class="grid grid-cols-2 md:grid-cols-4 gap-6 lg:gap-10 py-8 px-4 rounded-3xl"
             style="background-color: var(--color-surface); box-shadow: var(--shadow-lg);">
{stats_grid}
        </div>
{description}
{quote}"""


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
    """3 value-proposition cards (Halal, Fresh, Family) with icons.
    Quick-scan values for busy users who skip paragraphs."""
    cards = p.get("cards", [])
    card_items = []
    for idx, card in enumerate(cards):
        delay = idx * 100
        icon = card.get("icon", "fa-solid fa-star")
        card_items.append(f"""        <div class="p-8 rounded-2xl text-center transition-all duration-300 hover:-translate-y-1"
             style="background-color: var(--color-surface); box-shadow: var(--shadow);"
             data-aos="fade-up" data-aos-delay="{delay}">
            <div class="w-16 h-16 mx-auto rounded-2xl flex items-center justify-center mb-6"
                 style="background: linear-gradient(135deg, var(--color-primary), var(--color-secondary));">
                <i class="{_esc(icon)} text-2xl text-white"></i>
            </div>
            <h3 class="text-xl font-bold mb-3"
                style="font-family: var(--font-heading); color: var(--color-text);">
                {_esc(card.get('title', ''))}
            </h3>
            <p class="text-sm sm:text-base leading-relaxed"
               style="color: var(--color-text-muted);">
                {_esc(card.get('description', ''))}
            </p>
        </div>""")

    cards_html = "\n".join(card_items)

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
        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-8">
{cards_html}
        </div>"""


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
