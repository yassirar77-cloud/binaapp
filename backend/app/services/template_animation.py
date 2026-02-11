"""
Template Animation Service

Adds animated background effects to websites generated from animated templates.
This runs as a SEPARATE step AFTER the main generation flow (DeepSeek → Qwen copywriting).
It calls Qwen API to generate CSS + JS animation code and injects it into the final HTML.

Only runs for templates in the ANIMATED_TEMPLATES list. Non-animated templates skip this entirely.
"""

import os
import re
import httpx
from typing import Optional
from loguru import logger


# ============================================================================
# ANIMATED TEMPLATE IDs (from /create/templates gallery)
# ============================================================================
ANIMATED_TEMPLATES = [
    "particle-globe",
    "gradient-wave",
    "floating-food",
    "neon-grid",
    "morphing-blob",
    "matrix-code",
    "aurora",
    "spotlight",
    "parallax-layers",
    "word-explosion",
    "ghost-restaurant",
]

# ============================================================================
# ANIMATION PROMPTS PER TEMPLATE
# Each prompt asks Qwen to generate ONLY <style> and <script> blocks
# ============================================================================
ANIMATION_PROMPTS = {
    "matrix-code": (
        "Generate CSS and JavaScript for a Matrix-style falling green characters animation "
        "using HTML5 canvas. The canvas must be fixed position, full viewport, behind all content "
        "(z-index: -1). Use green monospace characters (#00ff00) on transparent background. "
        "Include random Japanese katakana and Latin characters falling at varying speeds and sizes. "
        "The animation must not block user interaction with page content. "
        "Return ONLY: 1) A single <style> block 2) A single <script> block. No HTML structure, no explanation."
    ),
    "floating-food": (
        "Generate CSS and JavaScript for floating food items animation. "
        "Create 15-20 food emoji characters (🍕🍔🍣🍜🍩🍰🍗🥗🌮🍱) that float upward continuously "
        "with gentle swaying left-right motion and subtle 3D rotation using CSS transforms. "
        "Items should be semi-transparent (opacity 0.3-0.6), various sizes (20px-50px), "
        "start from random positions below viewport, and reset when they go above viewport. "
        "Use position:fixed container with z-index:-1 and pointer-events:none so content stays clickable. "
        "Return ONLY: 1) A single <style> block 2) A single <script> block. No HTML structure, no explanation."
    ),
    "morphing-blob": (
        "Generate CSS and JavaScript for a morphing blob animation background. "
        "Create 3 large gradient blobs (purple #8B5CF6, blue #3B82F6, pink #EC4899) that slowly "
        "morph shape using CSS border-radius animation and move around the viewport. "
        "Blobs should be 300-500px, heavily blurred (filter: blur(80px)), semi-transparent (opacity 0.15), "
        "in a fixed container behind content (z-index:-1, pointer-events:none). "
        "Use CSS @keyframes for smooth organic morphing transitions (20-30s duration). "
        "Return ONLY: 1) A single <style> block 2) A single <script> block. No HTML structure, no explanation."
    ),
    "particle-globe": (
        "Generate CSS and JavaScript for an interactive particle globe animation using HTML5 canvas. "
        "Create a 3D rotating wireframe globe made of connected dots/particles in cyan (#06B6D4) "
        "and purple (#8B5CF6). Globe should be centered, ~300px diameter, slowly rotating. "
        "Particles connected by thin lines when close to each other. "
        "Canvas must be fixed position, full viewport, behind content (z-index:-1). "
        "Return ONLY: 1) A single <style> block 2) A single <script> block. No HTML structure, no explanation."
    ),
    "gradient-wave": (
        "Generate CSS and JavaScript for animated gradient wave background. "
        "Create 3-4 overlapping sine wave layers at the bottom of the viewport using HTML5 canvas or SVG. "
        "Waves should use vibrant gradient colors (purple #8B5CF6, cyan #06B6D4, pink #EC4899) "
        "with smooth flowing animation. Each wave at different speed and amplitude. "
        "Semi-transparent waves (opacity 0.2-0.4). Canvas/container fixed, full width, behind content. "
        "z-index:-1, pointer-events:none. "
        "Return ONLY: 1) A single <style> block 2) A single <script> block. No HTML structure, no explanation."
    ),
    "neon-grid": (
        "Generate CSS and JavaScript for an animated neon grid floor effect. "
        "Create a perspective 3D grid that stretches into the horizon (like Tron/cyberpunk aesthetic). "
        "Grid lines in neon purple (#8B5CF6) and cyan (#06B6D4) on dark background. "
        "Grid should slowly scroll forward creating an infinite tunnel effect. "
        "Use CSS perspective and transforms. Fixed container, z-index:-1, pointer-events:none. "
        "Return ONLY: 1) A single <style> block 2) A single <script> block. No HTML structure, no explanation."
    ),
    "aurora": (
        "Generate CSS and JavaScript for aurora borealis (northern lights) animation. "
        "Create flowing, undulating bands of color (green #00FF87, blue #00D4FF, purple #8B5CF6) "
        "that wave across the top portion of the viewport. Use CSS gradients with @keyframes "
        "animation for smooth color shifting and position movement. Semi-transparent (opacity 0.2-0.4). "
        "Fixed container behind content, z-index:-1, pointer-events:none. "
        "Return ONLY: 1) A single <style> block 2) A single <script> block. No HTML structure, no explanation."
    ),
    "spotlight": (
        "Generate CSS and JavaScript for a smooth spotlight/cursor-following light effect. "
        "Create a large radial gradient circle (300px, warm white/gold) that follows the mouse cursor "
        "with smooth easing. On mobile, slowly animate the spotlight in a figure-8 pattern. "
        "The light should illuminate the dark background subtly (opacity 0.15). "
        "Fixed overlay, z-index:-1, pointer-events:none. "
        "Return ONLY: 1) A single <style> block 2) A single <script> block. No HTML structure, no explanation."
    ),
    "parallax-layers": (
        "Generate CSS and JavaScript for a parallax scrolling layers effect. "
        "Create 3-4 decorative layers (geometric shapes, circles, lines) at different depths "
        "that move at different speeds on scroll, creating a depth/parallax effect. "
        "Shapes should be subtle and semi-transparent (opacity 0.1-0.2) in brand colors. "
        "Use transform: translateY() driven by scroll position with requestAnimationFrame. "
        "Fixed container, z-index:-1, pointer-events:none. "
        "Return ONLY: 1) A single <style> block 2) A single <script> block. No HTML structure, no explanation."
    ),
    "word-explosion": (
        "Generate CSS and JavaScript for a word explosion/tornado animation. "
        "Find all elements with class 'fly-word' on the page. On page load, scatter them "
        "to random positions with random rotations, then animate them flying into their "
        "correct positions over 1.5 seconds with elastic easing. "
        "Add a subtle hover effect that makes words slightly lift and glow. "
        "Use CSS transforms and transitions, triggered by JS IntersectionObserver for sections. "
        "Return ONLY: 1) A single <style> block 2) A single <script> block. No HTML structure, no explanation."
    ),
    "ghost-restaurant": (
        "Generate CSS and JavaScript for a ghost/vanishing restaurant effect. "
        "Target the element with id 'ghost-wrapper'. After page loads, wait 60 seconds, "
        "then fade out all content over 3 seconds. Show a spooky message 'The restaurant has vanished... "
        "or has it?' for 4 seconds. Then fade everything back in over 2 seconds. "
        "Add a subtle flickering effect (opacity pulse) every 30 seconds to build tension. "
        "Also add floating ghost emoji (👻) particles in the background, semi-transparent. "
        "Return ONLY: 1) A single <style> block 2) A single <script> block. No HTML structure, no explanation."
    ),
}


def is_animated_template(template_id: Optional[str]) -> bool:
    """Check if a template_id is in the animated templates list."""
    return template_id is not None and template_id in ANIMATED_TEMPLATES


async def add_template_animation(html: str, template_id: str) -> str:
    """
    Call Qwen API to generate animation CSS/JS for the given template,
    then inject it into the final HTML.

    This function is called AFTER the main generation flow completes.
    It only runs for animated templates.

    Args:
        html: The final HTML from the main generation flow
        template_id: The animated template ID (e.g. 'matrix-code')

    Returns:
        Enhanced HTML with animation injected, or original HTML if animation fails
    """
    if template_id not in ANIMATION_PROMPTS:
        logger.warning(f"🎭 No animation prompt for template '{template_id}' - skipping")
        return html

    prompt = ANIMATION_PROMPTS[template_id]
    logger.info(f"🎭 Generating animation for template '{template_id}'...")

    # Call Qwen API
    qwen_api_key = os.getenv("QWEN_API_KEY") or os.getenv("DASHSCOPE_API_KEY")
    qwen_base_url = os.getenv("QWEN_BASE_URL", "https://dashscope-intl.aliyuncs.com/compatible-mode/v1")

    if not qwen_api_key:
        logger.error("🎭 ❌ QWEN_API_KEY not configured - cannot generate animation")
        return html

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{qwen_base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {qwen_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "qwen-max",
                    "messages": [
                        {
                            "role": "system",
                            "content": (
                                "You are a CSS/JavaScript animation specialist. "
                                "Output ONLY raw <style> and <script> blocks. "
                                "No markdown, no code fences, no explanation. "
                                "The animation must not interfere with page content or user interaction."
                            ),
                        },
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.7,
                    "max_tokens": 16000,
                },
            )

        if response.status_code != 200:
            logger.error(f"🎭 ❌ Qwen animation API error: {response.status_code}")
            return html

        animation_code = response.json()["choices"][0]["message"]["content"]
        logger.info(f"🎭 ✅ Qwen returned {len(animation_code)} chars of animation code")

        # Clean up: remove markdown code fences if present
        animation_code = _clean_animation_code(animation_code)

        # Inject animation into HTML
        html = _inject_animation(html, animation_code)
        logger.info(f"🎭 ✅ Animation injected for template '{template_id}'")

    except httpx.TimeoutException:
        logger.error(f"🎭 ❌ Qwen animation request timed out for '{template_id}'")
    except httpx.ConnectError as e:
        logger.error(f"🎭 ❌ Qwen animation connection error: {e}")
    except Exception as e:
        logger.error(f"🎭 ❌ Qwen animation error for '{template_id}': {e}")

    return html


def _clean_animation_code(code: str) -> str:
    """Remove markdown code fences and other non-HTML artifacts from Qwen's response."""
    # Remove ```html ... ``` or ```css ... ``` or ```javascript ... ``` wrappers
    code = re.sub(r'```(?:html|css|javascript|js)?\s*\n?', '', code)
    code = re.sub(r'\n?```', '', code)
    return code.strip()


def _inject_animation(html: str, animation_code: str) -> str:
    """
    Inject animation <style> and <script> blocks into the HTML.

    - <style> blocks go before </head>
    - <script> blocks go before </body>
    """
    # Extract <style> blocks from animation code
    style_blocks = re.findall(r'<style[^>]*>[\s\S]*?</style>', animation_code, re.IGNORECASE)
    # Extract <script> blocks from animation code
    script_blocks = re.findall(r'<script[^>]*>[\s\S]*?</script>', animation_code, re.IGNORECASE)

    style_code = '\n'.join(style_blocks)
    script_code = '\n'.join(script_blocks)

    # If Qwen returned raw CSS/JS without tags, wrap them
    if not style_blocks and not script_blocks:
        # Try to split by detecting CSS vs JS patterns
        logger.warning("🎭 Animation code has no <style>/<script> tags - attempting to wrap")
        # Just inject everything before </body> wrapped in a script
        html = html.replace('</body>', f'\n<script>\n{animation_code}\n</script>\n</body>', 1)
        return html

    # Inject <style> before </head>
    if style_code:
        if '</head>' in html:
            html = html.replace('</head>', f'\n<!-- Template Animation Styles -->\n{style_code}\n</head>', 1)
        elif '<body' in html:
            # Fallback: inject before <body>
            html = re.sub(r'(<body[^>]*>)', f'\n{style_code}\n\\1', html, count=1)

    # Inject <script> before </body>
    if script_code:
        if '</body>' in html:
            html = html.replace('</body>', f'\n<!-- Template Animation Scripts -->\n{script_code}\n</body>', 1)
        else:
            # Fallback: append at end
            html += f'\n{script_code}'

    return html
