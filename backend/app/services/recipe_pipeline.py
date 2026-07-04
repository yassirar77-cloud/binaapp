"""M1 recipe pipeline: intent → DesignBrief → deterministic HTML assembly.

Flag-gated alternative to the legacy monolithic-prompt generator. Wired in
exactly one place — the top of AIService.generate_website() — and returns
the same AIGenerationResponse shape, so job handling, quotas, publish,
widget injection, and serving are untouched (see
docs/plans/GENERATION_UPGRADE_PLAN.md §1.6 do-not-break zones).

Flags (read at call time, never at import):
  GENERATION_RECIPE_PIPELINE_ENABLED   master switch, default off
  RECIPE_PIPELINE_USER_ALLOWLIST       comma-separated emails/user ids, or "*"

Failure policy: ANY exception here is caught by ai_service, which logs and
continues with the legacy pipeline — a broken flag never becomes an outage.

Note on image_choice="none": image references are stripped from the brief
and cuisine auto-fill is disabled; menu-item pool images are additionally
stripped downstream by run_generation_task's existing image safety guard —
the same guard the legacy pipeline relies on.
"""

from __future__ import annotations

import logging
import os
import time
from typing import Awaitable, Callable, Dict, Optional

from app.models.schemas import AIGenerationResponse, WebsiteGenerationRequest
from app.schemas.recipe import DesignBrief
from app.services.brief_generator import CUISINE_POOL_KEYS, generate_brief
from app.services.html_renderer import render_html
from app.services.intent_extractor import extract_intent
from app.services.recipe_builder import build_recipe
from app.utils.output_lint import lint_html

logger = logging.getLogger(__name__)

FLAG_ENV = "GENERATION_RECIPE_PIPELINE_ENABLED"
ALLOWLIST_ENV = "RECIPE_PIPELINE_USER_ALLOWLIST"

_TRUTHY = ("1", "true", "yes", "on")


class RecipePipelineError(Exception):
    """Pipeline produced unusable output — caller falls back to legacy."""


def is_enabled() -> bool:
    return os.getenv(FLAG_ENV, "").strip().lower() in _TRUTHY


def _allowlist() -> list:
    raw = os.getenv(ALLOWLIST_ENV, "")
    return [entry.strip().lower() for entry in raw.split(",") if entry.strip()]


def is_enabled_for(request: WebsiteGenerationRequest) -> bool:
    """Master flag AND per-user allowlist ('*' = everyone)."""
    if not is_enabled():
        return False
    allowed = _allowlist()
    if "*" in allowed:
        return True
    identities = {
        (getattr(request, "user_email", None) or "").strip().lower(),
        (getattr(request, "user_id", None) or "").strip().lower(),
    }
    identities.discard("")
    return bool(identities & set(allowed))


def _language_of(request: WebsiteGenerationRequest) -> str:
    lang = request.language.value if hasattr(request.language, "value") else str(request.language)
    return "ms" if lang == "ms" else "en"


def _uploaded_image_map(request: WebsiteGenerationRequest) -> Dict[str, str]:
    """Map uploaded images to brief image keys (hero + gallery_1..4),
    mirroring the legacy pipeline's hero-only-if-named-hero rule."""
    image_map: Dict[str, str] = {}
    uploads = request.uploaded_images or []

    def url_of(img):
        if isinstance(img, dict):
            return img.get("url") or img.get("URL") or ""
        return str(img)

    def name_of(img):
        return (img.get("name", "") if isinstance(img, dict) else "").strip().lower()

    start = 0
    if uploads and "hero" in name_of(uploads[0]):
        image_map["hero"] = url_of(uploads[0])
        start = 1
    for i, img in enumerate(uploads[start:start + 4], 1):
        url = url_of(img)
        if url:
            image_map[f"gallery_{i}"] = url
    return {k: v for k, v in image_map.items() if v}


def _strip_image_refs(brief: DesignBrief) -> DesignBrief:
    """image_choice='none': drop image references + cuisine auto-fill."""
    sections = []
    for section in brief.sections:
        content = {
            k: v for k, v in section.content.items()
            if k not in ("image_key", "image_keys", "background_image_key")
        }
        sections.append(section.model_copy(update={"content": content}))
    return brief.model_copy(update={"sections": sections, "image_map": {}, "cuisine_type": None})


async def generate(
    request: WebsiteGenerationRequest,
    image_choice: str = "upload",
    progress_callback: Optional[Callable[[int, str], Awaitable[None]]] = None,
    max_ai_images: Optional[int] = None,  # unused: this path generates 0 AI images
) -> AIGenerationResponse:
    """Full recipe-pipeline generation. Raises on failure (caller falls back)."""
    t0 = time.time()
    step_timings: Dict[str, float] = {}
    language = _language_of(request)

    async def progress(percent: int, message: str):
        if progress_callback:
            try:
                await progress_callback(percent, message)
            except Exception as exc:
                logger.warning("progress callback failed: %s", exc)

    logger.info("🧪 RECIPE PIPELINE start: %s (lang=%s, images=%s)",
                request.business_name, language, image_choice)

    await progress(30, "Analyzing design intent")
    t = time.time()
    intent = await extract_intent(request.description, language, request.business_name)
    step_timings["intent_extraction"] = round(time.time() - t, 2)

    uploaded_map = {} if image_choice == "none" else _uploaded_image_map(request)
    available_keys = sorted(uploaded_map) if uploaded_map else list(CUISINE_POOL_KEYS)

    await progress(50, "Designing your website plan")
    t = time.time()
    brief = await generate_brief(request, intent, available_keys)
    step_timings["brief_generation"] = round(time.time() - t, 2)

    if uploaded_map:
        brief = brief.model_copy(update={"image_map": {**uploaded_map, **brief.image_map}})
    if image_choice == "none":
        brief = _strip_image_refs(brief)

    await progress(75, "Assembling your website")
    t = time.time()
    recipe = build_recipe(brief)
    html = render_html(recipe)
    step_timings["assembly"] = round(time.time() - t, 2)

    if "<!-- Unknown component" in html:
        raise RecipePipelineError("renderer emitted an unknown-component placeholder")

    report = lint_html(html, language=language)
    if not report.ok:
        raise RecipePipelineError(f"output failed lint: {report.issues}")

    await progress(90, "Finalizing")
    step_timings["total"] = round(time.time() - t0, 2)
    logger.info("🧪 RECIPE PIPELINE done in %.1fs: dna=%s sections=%s",
                step_timings["total"], brief.style_dna.value,
                [s.id for s in recipe.sections])

    integrations = ["whatsapp"] if (request.include_whatsapp and request.whatsapp_number) else []
    return AIGenerationResponse(
        html_content=html,
        meta_title=recipe.meta.title,
        meta_description=recipe.meta.description,
        sections=[s.id for s in recipe.sections],
        integrations_included=integrations,
        ai_images_count=0,
        was_truncated=False,
        truncation_retries=0,
        needs_manual_review=False,
        step_timings=step_timings,
    )
