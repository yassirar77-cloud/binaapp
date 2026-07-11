"""Post-edit guard pipeline for the editor's AI quick-edit path.

Every full generation path (GLM primary, DeepSeek fallback, template
pipeline, multi-style) runs a set of deterministic post-generation guards
before its HTML reaches the user. The editor's AI Assistant quick-edit path
(POST /api/edit-html — the "Apa anda nak ubah?" box) used to return raw
model output with NONE of them, so an edit could introduce a new invented
sensitive claim, leave a previously-invented one standing, ship an empty
image slot, or keep content hidden by broken AOS animations.

This module holds every AI edit result to the same standard as a fresh
generation. Guards applied, in the same relative order as the generation
pipeline (ai_service.generate_website):

1. PHOTO_SLOT binding (_replace_photo_slots) — an edit has no per-slot
   image URLs, so any PHOTO_SLOT_N token the model emits is emptied and
   handed to the broken-image fixer, exactly like a no-uploads generation.
2. Broken-image URL fixer (_fix_broken_image_urls) — empty/#/undefined/
   placeholder src values are replaced with context-appropriate fallbacks.
3. Sensitive-claim sanitizer (claim_sanitizer.sanitize_sensitive_claims) —
   each matched claim is verified against the merchant's business data and
   stripped when unverified, with a "🛡 Removed unverified claim" log per
   removal.
4. Layout/AOS safety guard (template_service.apply_layout_safety_guard) —
   injects the binaapp-layout-safety CSS (AOS visibility rescue, bounded
   min-h-screen sections, empty-image placeholders).

All four guards are idempotent: PHOTO_SLOT binding no-ops without tokens,
the image fixer only rewrites broken src values, the sanitizer only removes
claims absent from the source data (re-running removes nothing), and the
layout guard is explicitly self-upgrading (strip + re-inject).

Deliberately NOT applied here (audited):
- template_service.apply_image_safety_guard — needs the original
  image_choice (unknown for a stored site) and its banned-stock-domain pass
  would delete the very Unsplash fallbacks the broken-image fixer installs.
  The v1 generation pipeline editor sites go through never runs it either.
- _fix_placeholders / _fix_menu_item_images / gallery normalizer — content
  fixers, not safety guards; re-running them on an edit can fight the
  user's explicit instruction (e.g. "buang butang WhatsApp" would be
  undone by the WhatsApp-button re-injection).
"""

import re
from typing import Any, Dict, List, Optional

from loguru import logger

from app.services.claim_sanitizer import sanitize_sensitive_claims
from app.services.templates import template_service

# The already-injected layout-safety block (any version). Stripped before the
# fixers run — its CSS contains selectors like img[src=""] that the
# broken-image fixer would otherwise "fix" — and re-injected fresh at the end.
# Same shape as the strip in template_service.apply_layout_safety_guard.
_LAYOUT_GUARD_BLOCK_RE = re.compile(
    r'\s*(?:<!-- BinaApp Layout Safety Guard -->\s*)?'
    r'<style id="binaapp-layout-safety">.*?</style>\s*',
    re.DOTALL,
)


def claim_sources_for_website(
    website: Optional[Dict[str, Any]], previous_html: str = ""
) -> List[str]:
    """Merchant-provided ground-truth texts a sensitive claim must appear in.

    With a website row, mirrors AIService._sanitize_sensitive_claims's
    source-of-truth fields: business name, description, address.

    Without a row (legacy caller that sent no website_id, or the row could
    not be loaded), falls back to the visible text of the PRE-edit HTML:
    an edit can then never INTRODUCE a new unverified claim, while claims
    already standing on the page are left for the next full verification
    (any guarded edit or regeneration with the row available).
    """
    if website:
        sources = [
            website.get("business_name") or "",
            website.get("description") or "",
            str(website.get("location_address") or ""),
        ]
        return [s for s in sources if s]
    if previous_html:
        return [re.sub(r"<[^>]*>", " ", previous_html)]
    return []


def apply_edit_guards(
    html: str,
    ai_service,
    website: Optional[Dict[str, Any]] = None,
    previous_html: str = "",
) -> str:
    """Run the post-generation guard suite on an AI edit result.

    Args:
        html: the edited HTML returned by the model.
        ai_service: the AIService instance (owns the photo-slot and
            broken-image guards used by the generation pipeline).
        website: the merchant's stored website row (source of business
            data for claim verification), or None when unavailable.
        previous_html: the pre-edit HTML, used as the claim-verification
            fallback when no website row is available.
    """
    if not html:
        return html

    description = (website or {}).get("description") or ""

    # 0. Remove any layout-safety CSS already baked into the page (edits on
    # saved sites carry it) so the image fixer below never touches guard
    # CSS. Step 4 re-injects the current version — this is also what makes
    # the whole pipeline idempotent.
    html = _LAYOUT_GUARD_BLOCK_RE.sub("", html)

    # 1. PHOTO_SLOT tokens: no ordered image URLs exist on the edit path,
    # so tokens are emptied for the broken-image fixer (no-op otherwise).
    html = ai_service._replace_photo_slots(html, [])

    # 2. Broken/empty image slots get the same final safety net as
    # generation output.
    html = ai_service._fix_broken_image_urls(html, description)

    # 3. Sensitive-claim sanitizer — verify against merchant business data.
    sources = claim_sources_for_website(website, previous_html)
    html, removed = sanitize_sensitive_claims(html, sources)
    if removed:
        logger.info(
            f"🛡 Edit-path sanitizer removed {len(removed)} "
            f"unverified claim(s): {removed}"
        )

    # 4. Layout/AOS safety CSS (idempotent + self-upgrading).
    html = template_service.apply_layout_safety_guard(html)

    return html
