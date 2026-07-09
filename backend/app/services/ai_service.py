"""
AI Service - Strict No-Placeholder Mode
Ensures real images and real content - NO placeholders allowed
"""

import os
import httpx
import uuid
import asyncio
import time
import json
import re
from collections import Counter
from contextlib import contextmanager
from loguru import logger
from typing import Optional, List, Dict, Tuple, Callable, Awaitable
from app.models.schemas import WebsiteGenerationRequest, AIGenerationResponse
from app.services.business_types import detect_business_type, get_design_type
from app.services.design_system import DesignSystem
from app.services.widget_catalogue import (
    widgets_for_request,
    build_prompt_context_block,
)
from difflib import SequenceMatcher
import cloudinary
import cloudinary.uploader


# Per-call timeout for the DeepSeek primary generation in
# generate_website / generate_multi_style. Bounded by asyncio.wait_for
# so a hung provider can't burn the entire endpoint budget. On timeout
# we raise asyncio.TimeoutError directly — the legacy Qwen fallback path
# was removed (DeepSeek-only as of this branch).
# Raised 120 -> 300 alongside the larger output cap below: a 24000-token
# completion can legitimately take longer to stream than the old 8000 cap.
AI_PRIMARY_TIMEOUT_SECONDS = float(os.getenv("AI_PRIMARY_TIMEOUT_SECONDS", "300"))

# Output-token cap for DeepSeek HTML generation. deepseek-reasoner
# (deepseek-v4-flash) tops out at 384K output tokens, so the previous
# hardcoded 8000 was far below ceiling and the most common truncation cause.
# 24000 ≈ 80-96K chars of HTML — comfortably covers a full multi-section page
# with 15+ cards while staying well under the provider ceiling.
AI_DEEPSEEK_MAX_TOKENS = int(os.getenv("AI_DEEPSEEK_MAX_TOKENS", "24000"))

# Output-token cap for GLM (Z.ai) HTML generation. Mirrors
# AI_DEEPSEEK_MAX_TOKENS above; env-overridable so the cap can be tuned in
# Render without a redeploy.
AI_GLM_MAX_TOKENS = int(os.getenv("AI_GLM_MAX_TOKENS", "16000"))

# Per-call timeout for the GLM primary generation. Tighter than
# AI_PRIMARY_TIMEOUT_SECONDS: GLM is a fall-through tier — a hung Z.ai must
# not burn the full 300s budget before DeepSeek even starts. On timeout we
# log and fall back to DeepSeek (never raise).
AI_GLM_TIMEOUT_SECONDS = float(os.getenv("AI_GLM_TIMEOUT_SECONDS", "240"))

# Feature flag: route primary HTML generation through GLM (Z.ai) FIRST, with
# the existing DeepSeek path as an untouched fallback. Ships dark (default
# OFF). Flip USE_GLM_FOR_HTML=true in Render to enable; flip it off for an
# instant rollback to pure DeepSeek — no code change or rollback deploy needed.
USE_GLM_FOR_HTML = os.getenv("USE_GLM_FOR_HTML", "false").strip().lower() in ("1", "true", "yes", "on")

# AI image provider selection: 'stability' (default — existing behaviour,
# byte-for-byte) or 'zai' (CogView / GLM-Image via the Z.ai images API, with
# the Stability path as automatic fallback when STABILITY_API_KEY is set).
# Read at call time so an env flip (or test patch) needs no re-import/redeploy.
def image_provider() -> str:
    return os.getenv("IMAGE_PROVIDER", "stability").strip().lower()


# Hard cap for the Z.ai image call (generation + download of the returned
# URL). Raised 30 -> 120: production showed glm-image legitimately taking
# longer than 30s; the per-build phase budget below (not this per-call cap)
# is what protects total generation time now.
ZAI_IMAGE_TIMEOUT_SECONDS = float(os.getenv("ZAI_IMAGE_TIMEOUT_SECONDS", "120"))

# The Z.ai image endpoint tolerates far less concurrency than Stability:
# parallel requests trip its rate limiter (HTTP 429, code 1302). When
# IMAGE_PROVIDER=zai, image requests are therefore SERIALIZED (concurrency 1)
# with a small spacing delay between requests, 429s are retried with the
# backoff below, and the total Z.ai image time per build is bounded by the
# phase budget — once spent, remaining images go straight to Stability.
# The Stability path keeps its original parallel behaviour.
ZAI_IMAGE_RETRY_BACKOFF_SECONDS = (3.0, 8.0)  # waits before 429 retries (max 2)


def zai_image_request_delay_seconds() -> float:
    """Minimum spacing between consecutive Z.ai image requests. Read at call
    time so an env flip / test patch needs no re-import."""
    try:
        return max(0.0, float(os.getenv("ZAI_IMAGE_REQUEST_DELAY_SECONDS", "1.0")))
    except (TypeError, ValueError):
        return 1.0


def zai_image_phase_budget_seconds() -> float:
    """Cap on the CUMULATIVE time a single build may spend inside Z.ai image
    calls (auto-fill + food-image pass combined). Once exceeded, remaining
    images go straight to the Stability fallback. Read at call time."""
    try:
        return max(0.0, float(os.getenv("ZAI_IMAGE_PHASE_BUDGET_SECONDS", "300")))
    except (TypeError, ValueError):
        return 300.0


def free_ai_images_per_site(default: int = 6) -> int:
    """Free-by-default AI-image budget per generated site.

    Used by the auto-fill pass in generate_website as the cap when the caller
    supplied NO max_ai_images quota (None). An explicit zero quota is honoured
    as zero — see _resolve_autofill_image_cap. Read at call time (same
    rationale as image_provider). Never negative; a malformed env value falls
    back to the default.
    """
    try:
        value = int(os.getenv("FREE_AI_IMAGES_PER_SITE", str(default)))
    except (TypeError, ValueError):
        return default
    return max(0, value)


# Premium design critique loop. Ships dark (default OFF). When ON, a
# successful GLM generation is reviewed by DeepSeek against the same 8 hard
# rules the GLM prompt carries; if the reviewer reports violations or
# improvements, GLM gets exactly ONE revision request (thinking disabled,
# same AI_GLM_TIMEOUT_SECONDS budget). The loop is strictly best-effort:
# a reviewer failure/timeout, unparseable critique, or bad revision ships
# the original HTML unchanged. With the flag OFF the loop makes zero calls.
PREMIUM_DESIGN_LOOP = os.getenv("PREMIUM_DESIGN_LOOP", "false").strip().lower() in ("1", "true", "yes", "on")
# Reviewer model — a fast non-thinking tier; the review is a rules checklist,
# not generation, so it must stay cheap and quick.
DESIGN_REVIEW_MODEL = os.getenv("DESIGN_REVIEW_MODEL", "deepseek-v4-flash")


def generation_outer_timeout_seconds(base: float = 180.0) -> float:
    """Outer wait_for budget for a full generate_website call.

    Callers that guard generation with their own asyncio.wait_for use this
    instead of a hardcoded number so the guard tracks the feature flags:
    with the premium design loop active on the GLM path, a healthy
    generation can legitimately take GLM (AI_GLM_TIMEOUT_SECONDS) + review
    (DESIGN_REVIEW_TIMEOUT_SECONDS) + one GLM revision, and the outer guard
    must not kill it mid-revision. Normal generations keep the tighter
    `base` budget. Reads the module flags at call time so env flips and
    test patches take effect without re-import.
    """
    budget = base
    if USE_GLM_FOR_HTML and PREMIUM_DESIGN_LOOP:
        # Two full GLM calls + the review cap + post-processing headroom.
        budget = max(budget, AI_GLM_TIMEOUT_SECONDS * 2 + DESIGN_REVIEW_TIMEOUT_SECONDS + 90.0)
    if image_provider() == "zai":
        # Serialized Z.ai images add up to the phase budget, plus one
        # in-flight image admitted just before the budget ran out (its own
        # generation + download timeouts + 429 retry backoffs).
        budget += (
            zai_image_phase_budget_seconds()
            + ZAI_IMAGE_TIMEOUT_SECONDS * 2
            + sum(ZAI_IMAGE_RETRY_BACKOFF_SECONDS)
        )
    return budget
# Hard cap on the DeepSeek review call. Deliberately tight: the review is
# optional polish and must never meaningfully delay generation.
DESIGN_REVIEW_TIMEOUT_SECONDS = float(os.getenv("DESIGN_REVIEW_TIMEOUT_SECONDS", "30"))
# Output cap for the critique JSON — {pass, violations, improvements} never
# legitimately needs more than this.
DESIGN_REVIEW_MAX_TOKENS = int(os.getenv("DESIGN_REVIEW_MAX_TOKENS", "2000"))


# Per-call timeout for the optional Qwen copywriting refinement pass in
# generate_website. Deliberately well under the 240s httpx client default so a
# slow polish pass can never delay (or fail) an otherwise-working generation —
# on timeout we ship the un-refined DeepSeek HTML.
AI_QWEN_REFINE_TIMEOUT_SECONDS = float(os.getenv("AI_QWEN_REFINE_TIMEOUT_SECONDS", "60"))

# Optional second Qwen pass that refines ONLY the CSS/visual styling of the
# finished page (spacing, type scale, colour restraint, shadows, hierarchy)
# while keeping all HTML structure, ids, JS, and image src byte-identical.
# Ships dark: default OFF. Enable via env only against a verified-clean
# baseline. Like the copy-refine pass it is non-blocking — bounded by its own
# short timeout and falling back to the un-refined HTML on any failure.
AI_QWEN_CSS_REFINE_ENABLED = os.getenv("AI_QWEN_CSS_REFINE_ENABLED", "false").strip().lower() in ("1", "true", "yes", "on")
AI_QWEN_CSS_REFINE_TIMEOUT_SECONDS = float(os.getenv("AI_QWEN_CSS_REFINE_TIMEOUT_SECONDS", "60"))


@contextmanager
def _timed_step(step_name: str, timings: Dict[str, float]):
    """
    Measure wall-clock duration of a block and record it on `timings`.

    Works around `await` calls because only the enter/exit points read the
    clock — the event loop can suspend inside the block and the measurement
    remains accurate.
    """
    start = time.time()
    try:
        yield
    finally:
        elapsed = time.time() - start
        # If the same step runs multiple times (e.g. two extract passes),
        # sum the durations rather than overwriting.
        timings[step_name] = round(timings.get(step_name, 0.0) + elapsed, 3)
        logger.info(f"⏱️  {step_name}: {elapsed:.2f}s")


# Patterns for extracting theme tokens out of the generated HTML, so the
# injected widgets can inherit the site's palette via CSS variables. We
# look in three places (in order): explicit --primary / --primary-color
# CSS variables, Tailwind config `colors: { primary: '...', secondary:
# '...' }` blocks (the quoted-hex patterns match both inline tailwind.config
# scripts and generated CSS-in-JS), and named `--bg-color` /
# `--surface-color` from our own _build_strict_prompt preamble. First
# match wins.
_THEME_PRIMARY_PATTERNS = [
    re.compile(r"--primary-color\s*:\s*(#[0-9a-fA-F]{3,8})"),
    re.compile(r"--primary\s*:\s*(#[0-9a-fA-F]{3,8})"),
    re.compile(r"primary\s*:\s*['\"](#[0-9a-fA-F]{3,8})['\"]"),
]
_THEME_SECONDARY_PATTERNS = [
    re.compile(r"--secondary-color\s*:\s*(#[0-9a-fA-F]{3,8})"),
    re.compile(r"--secondary\s*:\s*(#[0-9a-fA-F]{3,8})"),
    re.compile(r"secondary\s*:\s*['\"](#[0-9a-fA-F]{3,8})['\"]"),
]
_THEME_ACCENT_PATTERNS = [
    re.compile(r"--accent-color\s*:\s*(#[0-9a-fA-F]{3,8})"),
    re.compile(r"--accent\s*:\s*(#[0-9a-fA-F]{3,8})"),
    re.compile(r"accent\s*:\s*['\"](#[0-9a-fA-F]{3,8})['\"]"),
]
_THEME_SURFACE_PATTERNS = [
    re.compile(r"--surface-color\s*:\s*(#[0-9a-fA-F]{3,8})"),
    re.compile(r"--bg-color\s*:\s*(#[0-9a-fA-F]{3,8})"),
]


def extract_theme_tokens(html: str) -> Dict[str, str]:
    """Pull primary / secondary / accent / surface colours out of generated
    HTML (CSS variables or Tailwind config colour blocks).

    Best-effort: returns whatever it can find. Callers should treat
    missing keys as "fall back to widget default". Used by the injection
    layer so widgets inherit the AI-chosen palette instead of hard-coding
    the orange/green defaults.
    """
    if not html:
        return {}

    tokens: Dict[str, str] = {}
    for label, patterns in (
        ("primary", _THEME_PRIMARY_PATTERNS),
        ("secondary", _THEME_SECONDARY_PATTERNS),
        ("accent", _THEME_ACCENT_PATTERNS),
        ("surface", _THEME_SURFACE_PATTERNS),
    ):
        for pattern in patterns:
            match = pattern.search(html)
            if match:
                tokens[label] = match.group(1)
                break
    return tokens


# Import Stability AI service
try:
    from app.services.stability_service import (
        generate_malaysian_image,
        save_image_to_storage,
        get_malaysian_prompt,  # noqa: F401  (re-exported / availability guard)
        MALAYSIAN_PROMPTS,  # noqa: F401  (re-exported / availability guard)
    )
    STABILITY_AVAILABLE = True
except ImportError:
    logger.warning("⚠️ Stability AI service not available")
    STABILITY_AVAILABLE = False


class AIService:
    """AI Service with strict anti-placeholder enforcement"""

    # FOOD IMAGES - Unique Unsplash images for each dish category
    FOOD_IMAGES = {
        "nasi kandar": "https://images.unsplash.com/photo-1563379091339-03b21ab4a4f8?w=600&q=80",
        "nasi lemak": "https://images.unsplash.com/photo-1590301157890-4810ed352733?w=600&q=80",
        "nasi goreng": "https://images.unsplash.com/photo-1603133872878-684f208fb84b?w=600&q=80",
        "nasi kerabu": "https://images.unsplash.com/photo-1596040033229-a0b3b7b43107?w=600&q=80",
        "nasi ayam": "https://images.unsplash.com/photo-1603360946369-dc9bb6258143?w=600&q=80",
        "nasi briyani": "https://images.unsplash.com/photo-1589302168068-964664d93dc0?w=600&q=80",

        "ayam goreng": "https://images.unsplash.com/photo-1626645738196-c2a7c87a8f58?w=600&q=80",
        "ayam percik": "https://images.unsplash.com/photo-1598103442097-8b74394b95c6?w=600&q=80",
        "rendang": "https://images.unsplash.com/photo-1574484284002-952d92456975?w=600&q=80",

        "ikan bakar": "https://images.unsplash.com/photo-1580476262798-bddd9f4b7369?w=600&q=80",
        "ikan": "https://images.unsplash.com/photo-1519708227418-c8fd9a32b7a2?w=600&q=80",

        "mee goreng": "https://images.unsplash.com/photo-1617093727343-374698b1b08d?w=600&q=80",
        "char kway teow": "https://images.unsplash.com/photo-1569718212165-3a8278d5f624?w=600&q=80",
        "laksa": "https://images.unsplash.com/photo-1582878826629-29b7ad1cdc43?w=600&q=80",
        "hokkien mee": "https://images.unsplash.com/photo-1612927601601-6638404737ce?w=600&q=80",
        "mee rebus": "https://images.unsplash.com/photo-1585032226651-759b368d7246?w=600&q=80",

        "roti canai": "https://images.unsplash.com/photo-1589301760014-d929f3979dbc?w=600&q=80",
        "roti": "https://images.unsplash.com/photo-1601050690597-df0568f70950?w=600&q=80",
        "murtabak": "https://images.unsplash.com/photo-1599020792689-9fde458e7e17?w=600&q=80",

        "satay": "https://images.unsplash.com/photo-1529563021893-cc83c992d75d?w=600&q=80",

        "pelbagai lauk": "https://images.unsplash.com/photo-1504674900247-0877df9cc836?w=600&q=80",
        "lauk": "https://images.unsplash.com/photo-1555939594-58d7cb561ad1?w=600&q=80",

        "teh tarik": "https://images.unsplash.com/photo-1594631661960-17f1e5fc3d08?w=600&q=80",
        "kopi": "https://images.unsplash.com/photo-1509042239860-f550ce710b93?w=600&q=80",

        "cendol": "https://images.unsplash.com/photo-1563805042-7684c019e1cb?w=600&q=80",
        "ais kacang": "https://images.unsplash.com/photo-1488477181946-6428a0291777?w=600&q=80",

        # Generic fallback
        "default": "https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=600&q=80"
    }

    # COMPREHENSIVE BUSINESS IMAGES - Verified URLs for Malaysian Businesses
    BUSINESS_IMAGES = {
        # ===== MALAYSIAN FASHION & CLOTHING =====
        "baju kurung": "https://images.unsplash.com/photo-1583623025817-d180a2221d0a?w=600&q=80",  # Traditional Malay dress
        "baju melayu": "https://images.unsplash.com/photo-1583623025817-d180a2221d0a?w=600&q=80",
        "kurung": "https://images.unsplash.com/photo-1583623025817-d180a2221d0a?w=600&q=80",

        "tudung": "https://images.unsplash.com/photo-1601924357840-3e2a98b997f5?w=600&q=80",  # Hijab/headscarf
        "hijab": "https://images.unsplash.com/photo-1601924357840-3e2a98b997f5?w=600&q=80",
        "shawl": "https://images.unsplash.com/photo-1610976215686-875f2da6f249?w=600&q=80",
        "scarf": "https://images.unsplash.com/photo-1610976215686-875f2da6f249?w=600&q=80",

        "kebaya": "https://images.unsplash.com/photo-1594633312681-425c7b97ccd1?w=600&q=80",  # Traditional blouse
        "baju kebaya": "https://images.unsplash.com/photo-1594633312681-425c7b97ccd1?w=600&q=80",

        "pakaian": "https://images.unsplash.com/photo-1489987707025-afc232f7ea0f?w=600&q=80",  # General clothing
        "fashion": "https://images.unsplash.com/photo-1489987707025-afc232f7ea0f?w=600&q=80",
        "clothing": "https://images.unsplash.com/photo-1489987707025-afc232f7ea0f?w=600&q=80",
        "boutique": "https://images.unsplash.com/photo-1441986300917-64674bd600d8?w=600&q=80",

        # Fashion accessories
        "brooch": "https://images.unsplash.com/photo-1515562141207-7a88fb7ce338?w=600&q=80",
        "accessories": "https://images.unsplash.com/photo-1492707892479-7bc8d5a4ee93?w=600&q=80",
        "jewelry": "https://images.unsplash.com/photo-1515562141207-7a88fb7ce338?w=600&q=80",
        "anting": "https://images.unsplash.com/photo-1535632066927-ab7c9ab60908?w=600&q=80",  # Earrings
        "rantai": "https://images.unsplash.com/photo-1599643478518-a784e5dc4c8f?w=600&q=80",  # Necklace

        # ===== HAIR SALON SERVICES =====
        "salon": "https://images.unsplash.com/photo-1560066984-138dadb4c035?w=600&q=80",
        "hair salon": "https://images.unsplash.com/photo-1560066984-138dadb4c035?w=600&q=80",
        "salon rambut": "https://images.unsplash.com/photo-1560066984-138dadb4c035?w=600&q=80",

        "haircut": "https://images.unsplash.com/photo-1522337360788-8b13dee7a37e?w=600&q=80",
        "potong rambut": "https://images.unsplash.com/photo-1522337360788-8b13dee7a37e?w=600&q=80",
        "gunting rambut": "https://images.unsplash.com/photo-1522337360788-8b13dee7a37e?w=600&q=80",

        "hair coloring": "https://images.unsplash.com/photo-1559599101-f09722fb4948?w=600&q=80",
        "hair color": "https://images.unsplash.com/photo-1559599101-f09722fb4948?w=600&q=80",
        "cat rambut": "https://images.unsplash.com/photo-1559599101-f09722fb4948?w=600&q=80",
        "warna rambut": "https://images.unsplash.com/photo-1559599101-f09722fb4948?w=600&q=80",

        "hair treatment": "https://images.unsplash.com/photo-1521590832167-7bcbfaa6381f?w=600&q=80",
        "rawatan rambut": "https://images.unsplash.com/photo-1521590832167-7bcbfaa6381f?w=600&q=80",
        "hair spa": "https://images.unsplash.com/photo-1521590832167-7bcbfaa6381f?w=600&q=80",

        "hair styling": "https://images.unsplash.com/photo-1562322140-8baeececf3df?w=600&q=80",
        "styling": "https://images.unsplash.com/photo-1562322140-8baeececf3df?w=600&q=80",
        "blowdry": "https://images.unsplash.com/photo-1562322140-8baeececf3df?w=600&q=80",

        # ===== BEAUTY & SPA SERVICES =====
        "beauty": "https://images.unsplash.com/photo-1570172619644-dfd03ed5d881?w=600&q=80",
        "kecantikan": "https://images.unsplash.com/photo-1570172619644-dfd03ed5d881?w=600&q=80",
        "beauty salon": "https://images.unsplash.com/photo-1570172619644-dfd03ed5d881?w=600&q=80",

        "facial": "https://images.unsplash.com/photo-1616394584738-fc6e612e71b9?w=600&q=80",
        "facial treatment": "https://images.unsplash.com/photo-1616394584738-fc6e612e71b9?w=600&q=80",
        "rawatan muka": "https://images.unsplash.com/photo-1616394584738-fc6e612e71b9?w=600&q=80",

        "spa": "https://images.unsplash.com/photo-1544161515-4ab6ce6db874?w=600&q=80",
        "massage": "https://images.unsplash.com/photo-1519823551278-64ac92734fb1?w=600&q=80",
        "urut": "https://images.unsplash.com/photo-1519823551278-64ac92734fb1?w=600&q=80",
        "body massage": "https://images.unsplash.com/photo-1519823551278-64ac92734fb1?w=600&q=80",

        "manicure": "https://images.unsplash.com/photo-1604654894610-df63bc536371?w=600&q=80",
        "pedicure": "https://images.unsplash.com/photo-1604654894610-df63bc536371?w=600&q=80",
        "nails": "https://images.unsplash.com/photo-1604654894610-df63bc536371?w=600&q=80",
        "nail salon": "https://images.unsplash.com/photo-1604654894610-df63bc536371?w=600&q=80",

        "makeup": "https://images.unsplash.com/photo-1487412947147-5cebf100ffc2?w=600&q=80",
        "makeover": "https://images.unsplash.com/photo-1487412947147-5cebf100ffc2?w=600&q=80",
        "solek": "https://images.unsplash.com/photo-1487412947147-5cebf100ffc2?w=600&q=80",

        # ===== CAR & AUTOMOTIVE SERVICES =====
        "car wash": "https://images.unsplash.com/photo-1601362840469-51e4d8d58785?w=600&q=80",
        "cuci kereta": "https://images.unsplash.com/photo-1601362840469-51e4d8d58785?w=600&q=80",
        "auto wash": "https://images.unsplash.com/photo-1601362840469-51e4d8d58785?w=600&q=80",

        "bengkel": "https://images.unsplash.com/photo-1486262715619-67b85e0b08d3?w=600&q=80",
        "workshop": "https://images.unsplash.com/photo-1486262715619-67b85e0b08d3?w=600&q=80",
        "car repair": "https://images.unsplash.com/photo-1486262715619-67b85e0b08d3?w=600&q=80",
        "auto repair": "https://images.unsplash.com/photo-1486262715619-67b85e0b08d3?w=600&q=80",
        "mechanic": "https://images.unsplash.com/photo-1486262715619-67b85e0b08d3?w=600&q=80",

        "car service": "https://images.unsplash.com/photo-1625047509168-a7026f36de04?w=600&q=80",
        "servis kereta": "https://images.unsplash.com/photo-1625047509168-a7026f36de04?w=600&q=80",
        "auto service": "https://images.unsplash.com/photo-1625047509168-a7026f36de04?w=600&q=80",

        "tire service": "https://images.unsplash.com/photo-1592840496694-26d035b52b48?w=600&q=80",
        "tayar": "https://images.unsplash.com/photo-1592840496694-26d035b52b48?w=600&q=80",
        "tyre": "https://images.unsplash.com/photo-1592840496694-26d035b52b48?w=600&q=80",

        "kereta": "https://images.unsplash.com/photo-1492144534655-ae79c964c9d7?w=600&q=80",  # General car
        "car": "https://images.unsplash.com/photo-1492144534655-ae79c964c9d7?w=600&q=80",
        "automotive": "https://images.unsplash.com/photo-1492144534655-ae79c964c9d7?w=600&q=80",

        # ===== GENERAL BUSINESS CATEGORIES =====
        "bakery": "https://images.unsplash.com/photo-1509440159596-0249088772ff?w=600&q=80",
        # Fix malformed Unsplash URL (was breaking image loads)
        "kedai roti": "https://images.unsplash.com/photo-1509440159596-0249088772ff?w=600&q=80",
        "cake": "https://images.unsplash.com/photo-1578985545062-69928b1d9587?w=600&q=80",
        "kek": "https://images.unsplash.com/photo-1578985545062-69928b1d9587?w=600&q=80",

        "florist": "https://images.unsplash.com/photo-1490750967868-88aa4486c946?w=600&q=80",
        "bunga": "https://images.unsplash.com/photo-1490750967868-88aa4486c946?w=600&q=80",
        "flowers": "https://images.unsplash.com/photo-1490750967868-88aa4486c946?w=600&q=80",

        "pet shop": "https://images.unsplash.com/photo-1514888286974-6c03e2ca1dba?w=600&q=80",
        "kedai haiwan": "https://images.unsplash.com/photo-1514888286974-6c03e2ca1dba?w=600&q=80",
        "pet": "https://images.unsplash.com/photo-1514888286974-6c03e2ca1dba?w=600&q=80",

        "grocery": "https://images.unsplash.com/photo-1534723452862-4c874018d66d?w=600&q=80",
        "kedai runcit": "https://images.unsplash.com/photo-1534723452862-4c874018d66d?w=600&q=80",
        "mini market": "https://images.unsplash.com/photo-1534723452862-4c874018d66d?w=600&q=80",

        "laundry": "https://images.unsplash.com/photo-1517677208171-0bc6725a3e60?w=600&q=80",
        "dobi": "https://images.unsplash.com/photo-1517677208171-0bc6725a3e60?w=600&q=80",

        "cafe": "https://images.unsplash.com/photo-1554118811-1e0d58224f24?w=600&q=80",
        "kafe": "https://images.unsplash.com/photo-1554118811-1e0d58224f24?w=600&q=80",
        "coffee": "https://images.unsplash.com/photo-1509042239860-f550ce710b93?w=600&q=80",

        "restaurant": "https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?w=600&q=80",
        # Fix malformed Unsplash URL (was breaking image loads)
        "restoran": "https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?w=600&q=80",

        # ===== PHOTOGRAPHY & GALLERY =====
        "photography": "https://images.unsplash.com/photo-1542038784456-1ea8e935640e?w=600&q=80",
        "fotografi": "https://images.unsplash.com/photo-1542038784456-1ea8e935640e?w=600&q=80",
        "photographer": "https://images.unsplash.com/photo-1542038784456-1ea8e935640e?w=600&q=80",
        "jurugambar": "https://images.unsplash.com/photo-1542038784456-1ea8e935640e?w=600&q=80",

        "gallery": "https://images.unsplash.com/photo-1513364776144-60967b0f800f?w=600&q=80",  # Art gallery
        "galeri": "https://images.unsplash.com/photo-1513364776144-60967b0f800f?w=600&q=80",
        "portfolio": "https://images.unsplash.com/photo-1460925895917-afdab827c52f?w=600&q=80",

        "studio": "https://images.unsplash.com/photo-1598488035139-bdbb2231ce04?w=600&q=80",

        # Generic fallback
        "business": "https://images.unsplash.com/photo-1497366216548-37526070297c?w=600&q=80",
        "perniagaan": "https://images.unsplash.com/photo-1497366216548-37526070297c?w=600&q=80",
        "default": "https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=600&q=80"
    }

    # ROTATING FALLBACK POOLS - when no specific keyword matches, pick deterministically
    # from a pool so different items get different images instead of all sharing one fallback.
    # Each pool has 5-6 distinct, high-quality Unsplash photos for its category.
    FALLBACK_IMAGE_POOLS = {
        "photography": [
            "https://images.unsplash.com/photo-1542038784456-1ea8e935640e?w=600&q=80",
            "https://images.unsplash.com/photo-1452587925148-ce544e77e70d?w=600&q=80",
            "https://images.unsplash.com/photo-1554048612-b6a482bc67e5?w=600&q=80",
            "https://images.unsplash.com/photo-1500051638674-ff996a0ec29e?w=600&q=80",
            "https://images.unsplash.com/photo-1516035069371-29a1b244cc32?w=600&q=80",
            "https://images.unsplash.com/photo-1502920917128-1aa500764cbd?w=600&q=80",
        ],
        "events": [
            "https://images.unsplash.com/photo-1519167758481-83f550bb49b3?w=600&q=80",
            "https://images.unsplash.com/photo-1464366400600-7168b8af9bc3?w=600&q=80",
            "https://images.unsplash.com/photo-1511795409834-ef04bbd61622?w=600&q=80",
            "https://images.unsplash.com/photo-1478146896981-b80fe463b330?w=600&q=80",
            "https://images.unsplash.com/photo-1530023367847-a683933f4172?w=600&q=80",
            "https://images.unsplash.com/photo-1505373877841-8d25f7d46678?w=600&q=80",
        ],
        "wedding": [
            "https://images.unsplash.com/photo-1519741497674-611481863552?w=600&q=80",
            "https://images.unsplash.com/photo-1465495976277-4387d4b0e4a6?w=600&q=80",
            "https://images.unsplash.com/photo-1511795409834-ef04bbd61622?w=600&q=80",
            "https://images.unsplash.com/photo-1520854221256-17451cc331bf?w=600&q=80",
            "https://images.unsplash.com/photo-1606216794074-735e91aa2c92?w=600&q=80",
            "https://images.unsplash.com/photo-1519225421980-715cb0215aed?w=600&q=80",
        ],
        "corporate": [
            "https://images.unsplash.com/photo-1515187029135-18ee286d815b?w=600&q=80",
            "https://images.unsplash.com/photo-1540575467063-178a50c2df87?w=600&q=80",
            "https://images.unsplash.com/photo-1560439514-4e9645039924?w=600&q=80",
            "https://images.unsplash.com/photo-1511578314322-379afb476865?w=600&q=80",
            "https://images.unsplash.com/photo-1556761175-5973dc0f32e7?w=600&q=80",
            "https://images.unsplash.com/photo-1552664730-d307ca884978?w=600&q=80",
        ],
        "food": [
            "https://images.unsplash.com/photo-1504674900247-0877df9cc836?w=600&q=80",
            "https://images.unsplash.com/photo-1555939594-58d7cb561ad1?w=600&q=80",
            "https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=600&q=80",
            "https://images.unsplash.com/photo-1565299624946-b28f40a0ae38?w=600&q=80",
            "https://images.unsplash.com/photo-1540189549336-e6e99c3679fe?w=600&q=80",
            "https://images.unsplash.com/photo-1432139509613-5c4255815697?w=600&q=80",
        ],
        "services": [
            "https://images.unsplash.com/photo-1497366216548-37526070297c?w=600&q=80",
            "https://images.unsplash.com/photo-1521791136064-7986c2920216?w=600&q=80",
            "https://images.unsplash.com/photo-1556761175-b413da4baf72?w=600&q=80",
            "https://images.unsplash.com/photo-1542744173-8e7e53415bb0?w=600&q=80",
            "https://images.unsplash.com/photo-1517245386807-bb43f82c33c4?w=600&q=80",
            "https://images.unsplash.com/photo-1551836022-deb4988cc6c0?w=600&q=80",
        ],
        "retail": [
            "https://images.unsplash.com/photo-1441986300917-64674bd600d8?w=600&q=80",
            "https://images.unsplash.com/photo-1555529669-e69e7aa0ba9a?w=600&q=80",
            "https://images.unsplash.com/photo-1472851294608-062f824d29cc?w=600&q=80",
            "https://images.unsplash.com/photo-1483985988355-763728e1935b?w=600&q=80",
            "https://images.unsplash.com/photo-1490481651871-ab68de25d43d?w=600&q=80",
            "https://images.unsplash.com/photo-1489987707025-afc232f7ea0f?w=600&q=80",
        ],
        "beauty": [
            "https://images.unsplash.com/photo-1570172619644-dfd03ed5d881?w=600&q=80",
            "https://images.unsplash.com/photo-1596462502278-27bfdc403348?w=600&q=80",
            "https://images.unsplash.com/photo-1487412947147-5cebf100ffc2?w=600&q=80",
            "https://images.unsplash.com/photo-1560066984-138dadb4c035?w=600&q=80",
            "https://images.unsplash.com/photo-1516975080664-ed2fc6a32937?w=600&q=80",
            "https://images.unsplash.com/photo-1522337360788-8b13dee7a37e?w=600&q=80",
        ],
        "fashion": [
            "https://images.unsplash.com/photo-1489987707025-afc232f7ea0f?w=600&q=80",
            "https://images.unsplash.com/photo-1441984904996-e0b6ba687e04?w=600&q=80",
            "https://images.unsplash.com/photo-1469334031218-e382a71b716b?w=600&q=80",
            "https://images.unsplash.com/photo-1483985988355-763728e1935b?w=600&q=80",
            "https://images.unsplash.com/photo-1445205170230-053b83016050?w=600&q=80",
            "https://images.unsplash.com/photo-1525507119028-ed4c629a60a3?w=600&q=80",
        ],
        "automotive": [
            "https://images.unsplash.com/photo-1492144534655-ae79c964c9d7?w=600&q=80",
            "https://images.unsplash.com/photo-1486262715619-67b85e0b08d3?w=600&q=80",
            "https://images.unsplash.com/photo-1601362840469-51e4d8d58785?w=600&q=80",
            "https://images.unsplash.com/photo-1625047509168-a7026f36de04?w=600&q=80",
            "https://images.unsplash.com/photo-1503376780353-7e6692767b70?w=600&q=80",
            "https://images.unsplash.com/photo-1533473359331-0135ef1b58bf?w=600&q=80",
        ],
    }

    # MALAY KEYWORD DICTIONARY - maps Malay/BM terms to fallback pool categories.
    # Covers terms that kept slipping through the English-only matcher in production
    # (e.g. "upacara", "majlis", "jaringan", "korporat", "perkahwinan").
    MALAY_KEYWORD_TO_POOL = {
        # Events, ceremonies, gatherings
        "upacara": "events",          # ceremony
        "majlis": "events",           # formal gathering/ceremony
        "acara": "events",            # event
        "sambutan": "events",         # celebration
        "perayaan": "events",         # festival/celebration
        "keraian": "events",          # festivity
        "perhimpunan": "events",      # assembly
        "perjumpaan": "events",       # meeting/gathering
        "jamuan": "events",           # banquet/feast
        "pertemuan": "events",        # meeting

        # Wedding specific
        "perkahwinan": "wedding",     # wedding
        "kahwin": "wedding",          # marry
        "pengantin": "wedding",       # bride/groom
        "nikah": "wedding",           # nuptials
        "resepsi": "wedding",         # reception
        "bertunang": "wedding",       # engagement
        "pertunangan": "wedding",     # engagement

        # Corporate / business
        "korporat": "corporate",      # corporate
        "jaringan": "corporate",      # networking
        "syarikat": "corporate",      # company
        "perniagaan": "corporate",    # business
        "persidangan": "corporate",   # conference
        "mesyuarat": "corporate",     # meeting
        "seminar": "corporate",
        "bengkel korporat": "corporate",

        # Photography / media (Malay phrasing)
        "gambar": "photography",      # picture
        "foto": "photography",        # photo
        "jurufoto": "photography",    # photographer
        "jurugambar": "photography",  # photographer
        "rakaman": "photography",     # recording/shoot
        "penggambaran": "photography",# filming/shooting session

        # Modifiers / context (not category-specific; resolved via business_type)
        "intim": None,                # intimate - context-dependent
        "butiran": None,              # details
        "detail": None,

        # Food & beverage (Malay)
        "makanan": "food",
        "minuman": "food",
        "hidangan": "food",           # dish/serving
        "menu": "food",
        "masakan": "food",            # cuisine
        "juadah": "food",             # meal/feast food

        # Fashion
        "baju": "fashion",
        "pakaian": "fashion",
        "fesyen": "fashion",
        "butik": "fashion",

        # Services
        "perkhidmatan": "services",
        "servis": "services",
    }

    # MALAYSIAN FOOD PROMPTS - 60+ Authentic Malaysian Dishes
    MALAYSIAN_FOOD_PROMPTS = {
        # Rice Dishes
        "nasi lemak": "Malaysian nasi lemak plate with fragrant coconut rice, crispy fried anchovies (ikan bilis), roasted peanuts, hard-boiled egg, cucumber slices, and spicy sambal sauce",
        "nasi kandar": "Malaysian nasi kandar plate with steamed white rice, rich curry gravy, fried chicken, okra in curry sauce, and pickled vegetables",
        "nasi kerabu": "Malaysian nasi kerabu blue rice dish with herbs, kerisik (toasted coconut), fish crackers, salted egg, and ulam (raw vegetables)",
        "nasi dagang": "Malaysian nasi dagang brown rice with tuna curry, pickled vegetables, and hard-boiled egg",
        "nasi goreng": "Malaysian nasi goreng fried rice with egg, vegetables, chicken, shrimp paste, and cucumber garnish",
        "nasi ayam": "Malaysian chicken rice with poached chicken slices, fragrant rice, cucumber, and chili sauce",
        "nasi tomato": "Malaysian nasi tomato red rice cooked with tomatoes, spices, raisins, and cashew nuts",
        "nasi minyak": "Malaysian nasi minyak ghee rice with aromatic spices, garnished with fried onions and cashews",
        "nasi briyani": "Malaysian nasi briyani spiced rice with tender chicken or lamb, yogurt, and aromatic spices",
        "nasi hujan panas": "Malaysian nasi hujan panas rice with anchovies, peanuts, and spicy sambal",

        # Noodle Dishes
        "mee goreng": "Malaysian mee goreng yellow noodles stir-fried with tofu, vegetables, egg, and spicy sauce",
        "char kway teow": "Malaysian char kway teow flat rice noodles wok-fried with prawns, cockles, egg, bean sprouts, and soy sauce",
        "laksa": "Malaysian laksa spicy noodle soup with thick rice noodles, fish broth, tamarind, and coconut milk",
        "assam laksa": "Malaysian assam laksa sour fish noodle soup with mackerel, tamarind, mint, and pineapple",
        "curry laksa": "Malaysian curry laksa coconut curry noodle soup with tofu puffs, prawns, and bean sprouts",
        "mee rebus": "Malaysian mee rebus yellow noodles in thick sweet potato gravy with egg, tofu, and lime",
        "mee bandung": "Malaysian mee bandung noodles in spicy tomato-based gravy with prawns and vegetables",
        "hokkien mee": "Malaysian Hokkien mee thick noodles braised in dark soy sauce with pork, seafood, and cabbage",
        "pan mee": "Malaysian pan mee handmade flat noodles in anchovy broth with minced pork, mushrooms, and fried anchovies",
        "wantan mee": "Malaysian wantan mee egg noodles with char siu (BBQ pork), wonton dumplings, and dark soy sauce",
        "kolo mee": "Malaysian kolo mee Sarawak-style springy noodles with char siu, minced pork, and fried shallots",
        "maggi goreng": "Malaysian maggi goreng instant noodles stir-fried with egg, vegetables, and spicy sauce",
        "mihun goreng": "Malaysian mihun goreng rice vermicelli stir-fried with vegetables, egg, and meat",
        "kuey teow goreng": "Malaysian kuey teow goreng flat rice noodles stir-fried with prawns and vegetables",

        # Meat Dishes
        "rendang": "Malaysian beef rendang slow-cooked in thick spicy coconut curry with lemongrass and galangal",
        "ayam percik": "Malaysian ayam percik grilled chicken with spicy coconut gravy",
        "ayam masak merah": "Malaysian ayam masak merah chicken in red tomato chili gravy",
        "ayam goreng berempah": "Malaysian ayam goreng berempah spiced fried chicken with turmeric and herbs",
        "gulai kambing": "Malaysian gulai kambing lamb curry in spicy coconut gravy",
        "daging masak hitam": "Malaysian daging masak hitam beef in thick dark soy sauce with spices",
        "sambal udang": "Malaysian sambal udang prawns in spicy chili sambal sauce",
        "ikan bakar": "Malaysian ikan bakar grilled fish with sambal and lime",
        "ikan patin masak tempoyak": "Malaysian ikan patin fish curry with fermented durian paste",
        "asam pedas": "Malaysian asam pedas sour and spicy fish stew with tamarind and chilies",
        "gulai ikan": "Malaysian gulai ikan fish curry in turmeric coconut gravy",

        # Satay & Grilled
        "satay": "Malaysian chicken satay skewers grilled over charcoal with peanut sauce, cucumber, and onions",
        "satay ayam": "Malaysian chicken satay marinated skewers with thick peanut dipping sauce",
        "satay daging": "Malaysian beef satay grilled meat skewers with spicy peanut sauce",
        "satay kambing": "Malaysian lamb satay skewers with aromatic peanut sauce",

        # Soups
        "soto": "Malaysian soto chicken soup with turmeric, rice vermicelli, bean sprouts, and hard-boiled egg",
        "sup tulang": "Malaysian sup tulang bone marrow soup with beef bones and spices",
        "bakso": "Malaysian bakso meatball soup with noodles and vegetables",

        # Snacks & Appetizers
        "roti canai": "Malaysian roti canai crispy flaky flatbread with curry dipping sauce",
        "roti telur": "Malaysian roti telur flatbread with egg filling",
        "roti tissue": "Malaysian roti tissue paper-thin crispy flatbread cone with sugar",
        "murtabak": "Malaysian murtabak stuffed pancake with minced meat, egg, and onions",
        "curry puff": "Malaysian curry puff pastry filled with spiced potato and chicken",
        "epok epok": "Malaysian epok epok crispy fried curry puff with sardine filling",
        "kuih": "Malaysian traditional kuih colorful sweet cakes and pastries",
        "onde onde": "Malaysian onde onde pandan glutinous rice balls with palm sugar filling",
        "kuih lapis": "Malaysian kuih lapis colorful layered steamed cake",
        "kuih ketayap": "Malaysian kuih ketayap green pandan crepes with coconut filling",
        "pisang goreng": "Malaysian pisang goreng crispy fried banana fritters",
        "cempedak goreng": "Malaysian cempedak goreng fried jackfruit fritters",
        "keropok lekor": "Malaysian keropok lekor fish crackers from Terengganu",
        "otak otak": "Malaysian otak otak grilled fish cake wrapped in banana leaf",

        # Desserts
        "cendol": "Malaysian cendol iced dessert with pandan jelly noodles, coconut milk, and gula melaka",
        "ais kacang": "Malaysian ais kacang shaved ice with red beans, corn, jelly, and colorful syrups",
        "bubur chacha": "Malaysian bubur chacha warm coconut dessert soup with sweet potato and sago pearls",
        "pengat": "Malaysian pengat sweet banana in coconut milk and palm sugar",
        "sago gula melaka": "Malaysian sago gula melaka sago pearls with coconut milk and palm sugar syrup",
        "kuih talam": "Malaysian kuih talam two-layer steamed coconut pandan cake",

        # Beverages
        "teh tarik": "Malaysian teh tarik pulled milk tea being poured between two containers creating foam",
        "kopi o": "Malaysian kopi o black coffee in traditional coffee shop",
        "milo ais": "Malaysian milo ais iced chocolate malt drink",
        "air bandung": "Malaysian air bandung pink rose syrup milk drink",
        "sirap": "Malaysian sirap rose syrup drink with ice",

        # Special & Regional
        "nasi ambeng": "Malaysian nasi ambeng Javanese rice platter with fried chicken, bergedel, serunding, and sambal",
        "nasi tumpang": "Malaysian nasi tumpang cone-shaped rice wrapped in banana leaf with curry",
        "nasi kukus": "Malaysian nasi kukus steamed rice with fried chicken and sambal",
        "lontong": "Malaysian lontong rice cakes in coconut vegetable curry",
        "ketupat": "Malaysian ketupat rice dumplings wrapped in woven palm leaves",
        "lemang": "Malaysian lemang glutinous rice cooked in bamboo with coconut milk",
    }

    def __init__(self):
        self.qwen_api_key = os.getenv("QWEN_API_KEY") or os.getenv("DASHSCOPE_API_KEY")
        self.qwen_base_url = os.getenv("QWEN_BASE_URL", "https://dashscope-intl.aliyuncs.com/compatible-mode/v1")
        self.deepseek_api_key = os.getenv("DEEPSEEK_API_KEY")
        self.deepseek_base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
        self.deepseek_model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
        self.deepseek_model_pro = os.getenv("DEEPSEEK_MODEL_PRO", "deepseek-reasoner")
        # GLM / Z.ai — primary HTML generator when USE_GLM_FOR_HTML is on.
        # The existing Render env var is named ZAI_BASE_URL; ZAI_API_URL is
        # also accepted (and wins if both are set).
        self.zai_api_key = os.getenv("ZAI_API_KEY")
        self.zai_base_url = (
            os.getenv("ZAI_API_URL")
            or os.getenv("ZAI_BASE_URL")
            or "https://api.z.ai/api/paas/v4"
        )
        self.zai_model = os.getenv("ZAI_MODEL", "glm-5.2")
        # Z.ai IMAGE model (images/generations endpoint) — separate from the
        # HTML-generation chat model above. Valid model codes on that
        # endpoint are 'glm-image' (default) and 'cogview-4-250304'; plain
        # 'cogview-4' is rejected by the API (error 1211 "Unknown Model").
        self.zai_image_model = os.getenv("ZAI_IMAGE_MODEL", "glm-image")
        # Z.ai image serialization state (its endpoint rejects concurrent
        # requests with 429/1302): a lock enforcing concurrency 1, created
        # lazily inside the event loop, plus the last-request timestamp used
        # to space consecutive requests. The Stability path never touches it.
        self._zai_image_lock: Optional[asyncio.Lock] = None
        self._zai_last_request_at: float = 0.0
        self.stability_api_key = os.getenv("STABILITY_API_KEY")
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv("SUPABASE_ANON_KEY")

        # Per-call API-boundary state: set by every _call_<provider> method so
        # generate_website / _call_qwen_with_truncation_retry can see whether
        # the model hit its output cap (finish_reason ∈ {length, max_tokens}).
        # Mirrors the _last_extract_info pattern below. NOT thread-safe — but
        # neither is _last_extract_info; the service is awaited serially per
        # request from FastAPI.
        self._last_api_call: Dict = {
            "provider": None,
            "finish_reason": None,
            "truncated": False,
        }

        logger.info("=" * 80)
        logger.info("🚀 AI SERVICE - STRICT NO-PLACEHOLDER MODE")
        logger.info(
            f"   GLM (Z.ai): {'✅ Ready' if self.zai_api_key else '❌ NOT SET'} "
            f"(USE_GLM_FOR_HTML={'on' if USE_GLM_FOR_HTML else 'off'}, model={self.zai_model})"
        )
        logger.info(f"   DeepSeek: {'✅ Ready' if self.deepseek_api_key else '❌ NOT SET'}")
        logger.info(f"   Qwen: {'✅ Ready' if self.qwen_api_key else '❌ NOT SET'}")
        logger.info(f"   Stability AI: {'✅ Ready' if self.stability_api_key and STABILITY_AVAILABLE else '❌ NOT SET'}")
        logger.info(
            f"   Image provider: {image_provider()} "
            f"(Z.ai image model={self.zai_image_model}, "
            f"free images/site={free_ai_images_per_site()})"
        )
        logger.info(f"   Supabase Storage: {'✅ Ready' if self.supabase_url and self.supabase_key else '❌ NOT SET'}")
        logger.info("   Mode: Real images only, no placeholders allowed")
        logger.info("=" * 80)

    def get_food_image(self, dish_name: str) -> str:
        """
        Get unique food image URL for a dish name

        Uses fuzzy matching to find the best image for a dish.
        Ensures different dishes get different images.
        """
        if not dish_name:
            return self.FOOD_IMAGES["default"]

        dish_lower = dish_name.lower().strip()

        # Direct exact match
        if dish_lower in self.FOOD_IMAGES:
            return self.FOOD_IMAGES[dish_lower]

        # Fuzzy matching - check if dish name contains any key
        best_match = None
        best_score = 0.0

        for key, url in self.FOOD_IMAGES.items():
            if key == "default":
                continue

            # Check if key is in dish name or vice versa
            if key in dish_lower:
                score = len(key) / len(dish_lower)
                if score > best_score:
                    best_score = score
                    best_match = url
            elif dish_lower in key:
                score = len(dish_lower) / len(key)
                if score > best_score:
                    best_score = score
                    best_match = url

        if best_match and best_score >= 0.3:
            return best_match

        # Keyword fallback
        if "nasi kandar" in dish_lower:
            return self.FOOD_IMAGES["nasi kandar"]
        if "nasi lemak" in dish_lower:
            return self.FOOD_IMAGES["nasi lemak"]
        if "nasi" in dish_lower:
            return self.FOOD_IMAGES["nasi goreng"]
        if "ayam" in dish_lower or "chicken" in dish_lower:
            return self.FOOD_IMAGES["ayam goreng"]
        if "ikan" in dish_lower or "fish" in dish_lower:
            return self.FOOD_IMAGES["ikan bakar"]
        if "mee" in dish_lower or "noodle" in dish_lower:
            return self.FOOD_IMAGES["mee goreng"]
        if "laksa" in dish_lower:
            return self.FOOD_IMAGES["laksa"]
        if "roti" in dish_lower:
            return self.FOOD_IMAGES["roti canai"]
        if "satay" in dish_lower:
            return self.FOOD_IMAGES["satay"]
        if "rendang" in dish_lower:
            return self.FOOD_IMAGES["rendang"]
        if "lauk" in dish_lower or "side" in dish_lower:
            return self.FOOD_IMAGES["pelbagai lauk"]
        if "teh" in dish_lower or "tea" in dish_lower:
            return self.FOOD_IMAGES["teh tarik"]
        if "kopi" in dish_lower or "coffee" in dish_lower:
            return self.FOOD_IMAGES["kopi"]
        if "cendol" in dish_lower:
            return self.FOOD_IMAGES["cendol"]

        return self.FOOD_IMAGES["default"]

    def _pool_pick(self, pool_name: str, item_name: str, used_urls: Optional[set] = None) -> Optional[str]:
        """
        Deterministically pick one image from a fallback pool using the item name.

        Different items map to different images in the pool (zlib.crc32 is stable
        across processes, unlike Python's randomized hash()). Same item always
        returns the same image — important for regeneration idempotency.

        If `used_urls` is provided, walk forward from the deterministic start to
        find a slot that hasn't been used yet — gives the dedup pass truly unique
        images when CRC32 would otherwise collide.
        """
        pool = self.FALLBACK_IMAGE_POOLS.get(pool_name)
        if not pool:
            return None
        import zlib
        key = (item_name or "").strip().lower().encode("utf-8")
        start = zlib.crc32(key) % len(pool)
        if not used_urls:
            return pool[start]
        for offset in range(len(pool)):
            candidate = pool[(start + offset) % len(pool)]
            if candidate not in used_urls:
                return candidate
        return pool[start]

    def _malay_pool_for(self, text_lower: str) -> Optional[str]:
        """Check if the text contains any Malay keyword and return its pool category."""
        for keyword, pool in self.MALAY_KEYWORD_TO_POOL.items():
            if keyword in text_lower:
                return pool
        return None

    def get_matching_image(self, text: str, category: str = "all", business_type: str = "", used_urls: Optional[set] = None) -> str:
        """
        Get matching image URL for any Malaysian business product/service

        Uses smart keyword matching to find the best image from BUSINESS_IMAGES
        Combines FOOD_IMAGES and BUSINESS_IMAGES for comprehensive coverage

        Args:
            text: Product/service name or description (e.g., "Baju Kurung", "Tudung", "Haircut")
            category: Optional category hint ("fashion", "salon", "beauty", "food", "auto", "all")
            business_type: Optional business description for context-aware fallback
            used_urls: Optional set of already-assigned URLs to avoid when rotating
                through fallback pools (used by the dedup pass in _fix_menu_item_images).

        Returns:
            Best matching image URL
        """
        if not text:
            return self.BUSINESS_IMAGES["default"]

        text_lower = text.lower().strip()

        # Combine food and business images for comprehensive matching
        all_images = {**self.FOOD_IMAGES, **self.BUSINESS_IMAGES}

        # Direct exact match
        if text_lower in all_images:
            logger.info(f"🎯 Exact match for '{text}': {all_images[text_lower][:60]}...")
            return all_images[text_lower]

        # Fuzzy matching - check if text contains any key or vice versa
        best_match = None
        best_score = 0.0
        best_url = None

        for key, url in all_images.items():
            if key == "default":
                continue

            # Check if key is in text or vice versa
            if key in text_lower:
                score = len(key) / len(text_lower)
                if score > best_score:
                    best_score = score
                    best_match = key
                    best_url = url
            elif text_lower in key:
                score = len(text_lower) / len(key)
                if score > best_score:
                    best_score = score
                    best_match = key
                    best_url = url

        # Return if we have a good match (30% similarity or higher)
        if best_url and best_score >= 0.3:
            logger.info(f"🎯 Fuzzy match for '{text}' → '{best_match}' (score: {best_score:.2f})")
            return best_url

        # Malay keyword → rotating pool (runs before English keyword fallbacks so
        # terms like "upacara", "perkahwinan", "jaringan" don't slip through).
        malay_pool = self._malay_pool_for(text_lower)
        if malay_pool:
            pool_img = self._pool_pick(malay_pool, text, used_urls=used_urls)
            if pool_img:
                logger.info(f"🎯 Malay keyword match for '{text}' → {malay_pool} pool: {pool_img[:60]}...")
                return pool_img

        # Keyword-based fallback for common categories
        # Fashion & Clothing
        if any(word in text_lower for word in ['baju', 'kurung', 'melayu', 'traditional', 'dress']):
            return self.BUSINESS_IMAGES.get("baju kurung", self.BUSINESS_IMAGES["clothing"])
        if any(word in text_lower for word in ['tudung', 'hijab', 'headscarf', 'shawl']):
            return self.BUSINESS_IMAGES.get("tudung", self.BUSINESS_IMAGES["default"])
        if any(word in text_lower for word in ['kebaya', 'blouse']):
            return self.BUSINESS_IMAGES.get("kebaya", self.BUSINESS_IMAGES["clothing"])
        if any(word in text_lower for word in ['pakaian', 'clothing', 'fashion', 'boutique']):
            return self.BUSINESS_IMAGES.get("clothing", self.BUSINESS_IMAGES["default"])
        if any(word in text_lower for word in ['jewelry', 'brooch', 'anting', 'necklace', 'rantai', 'accessories']):
            return self.BUSINESS_IMAGES.get("accessories", self.BUSINESS_IMAGES["default"])

        # Hair Salon
        if any(word in text_lower for word in ['haircut', 'potong rambut', 'gunting', 'cut']):
            return self.BUSINESS_IMAGES.get("haircut", self.BUSINESS_IMAGES["salon"])
        if any(word in text_lower for word in ['hair color', 'cat rambut', 'warna', 'coloring', 'dye']):
            return self.BUSINESS_IMAGES.get("hair coloring", self.BUSINESS_IMAGES["salon"])
        if any(word in text_lower for word in ['hair treatment', 'rawatan rambut', 'hair spa']):
            return self.BUSINESS_IMAGES.get("hair treatment", self.BUSINESS_IMAGES["salon"])
        if any(word in text_lower for word in ['styling', 'blowdry', 'blow dry']):
            return self.BUSINESS_IMAGES.get("hair styling", self.BUSINESS_IMAGES["salon"])
        if any(word in text_lower for word in ['salon', 'rambut', 'hair']):
            return self.BUSINESS_IMAGES.get("salon", self.BUSINESS_IMAGES["default"])

        # Beauty & Spa
        if any(word in text_lower for word in ['facial', 'rawatan muka', 'face treatment']):
            return self.BUSINESS_IMAGES.get("facial", self.BUSINESS_IMAGES["beauty"])
        if any(word in text_lower for word in ['massage', 'urut', 'body massage']):
            return self.BUSINESS_IMAGES.get("massage", self.BUSINESS_IMAGES["spa"])
        if any(word in text_lower for word in ['manicure', 'pedicure', 'nail', 'nails']):
            return self.BUSINESS_IMAGES.get("manicure", self.BUSINESS_IMAGES["beauty"])
        if any(word in text_lower for word in ['makeup', 'makeover', 'solek']):
            return self.BUSINESS_IMAGES.get("makeup", self.BUSINESS_IMAGES["beauty"])
        if any(word in text_lower for word in ['spa', 'beauty', 'kecantikan']):
            return self.BUSINESS_IMAGES.get("beauty", self.BUSINESS_IMAGES["default"])

        # Automotive
        if any(word in text_lower for word in ['car wash', 'cuci kereta', 'auto wash', 'wash']):
            return self.BUSINESS_IMAGES.get("car wash", self.BUSINESS_IMAGES["car"])
        if any(word in text_lower for word in ['bengkel', 'workshop', 'repair', 'mechanic']):
            return self.BUSINESS_IMAGES.get("bengkel", self.BUSINESS_IMAGES["car"])
        if any(word in text_lower for word in ['car service', 'servis kereta', 'auto service', 'servicing']):
            return self.BUSINESS_IMAGES.get("car service", self.BUSINESS_IMAGES["car"])
        if any(word in text_lower for word in ['tire', 'tyre', 'tayar']):
            return self.BUSINESS_IMAGES.get("tire service", self.BUSINESS_IMAGES["car"])
        if any(word in text_lower for word in ['kereta', 'car', 'automotive', 'auto']):
            return self.BUSINESS_IMAGES.get("car", self.BUSINESS_IMAGES["default"])

        # Food (use existing get_food_image for better food matching)
        if any(word in text_lower for word in ['nasi', 'mee', 'rice', 'noodle', 'food', 'makan', 'dish']):
            food_img = self.get_food_image(text)
            if food_img != self.FOOD_IMAGES["default"]:
                return food_img

        # Other categories
        if any(word in text_lower for word in ['bakery', 'roti', 'bread', 'cake', 'kek']):
            return self.BUSINESS_IMAGES.get("bakery", self.BUSINESS_IMAGES["default"])
        if any(word in text_lower for word in ['flower', 'bunga', 'florist']):
            return self.BUSINESS_IMAGES.get("florist", self.BUSINESS_IMAGES["default"])
        if any(word in text_lower for word in ['pet', 'haiwan', 'cat', 'dog']):
            return self.BUSINESS_IMAGES.get("pet shop", self.BUSINESS_IMAGES["default"])
        if any(word in text_lower for word in ['grocery', 'runcit', 'mini market', 'mart']):
            return self.BUSINESS_IMAGES.get("grocery", self.BUSINESS_IMAGES["default"])
        if any(word in text_lower for word in ['laundry', 'dobi']):
            return self.BUSINESS_IMAGES.get("laundry", self.BUSINESS_IMAGES["default"])
        if any(word in text_lower for word in ['cafe', 'kafe', 'coffee', 'kopi']):
            return self.BUSINESS_IMAGES.get("cafe", self.BUSINESS_IMAGES["default"])
        if any(word in text_lower for word in ['restaurant', 'restoran']):
            return self.BUSINESS_IMAGES.get("restaurant", self.BUSINESS_IMAGES["default"])

        # Photography, Gallery & Portfolio
        if any(word in text_lower for word in ['galeri', 'gallery', 'portfolio', 'imej', 'foto', 'photo', 'gambar', 'image']):
            return self.BUSINESS_IMAGES.get("gallery", self.BUSINESS_IMAGES["default"])
        if any(word in text_lower for word in ['photography', 'fotografi', 'photographer', 'jurugambar', 'camera', 'kamera']):
            return self.BUSINESS_IMAGES.get("photography", self.BUSINESS_IMAGES["default"])
        if any(word in text_lower for word in ['studio']):
            return self.BUSINESS_IMAGES.get("studio", self.BUSINESS_IMAGES["default"])

        # Context-aware final fallback using business_type — rotate through pools
        # so different items get different images (hash(item_name) % pool_length)
        # instead of all unmatched items sharing a single fallback photo.
        if business_type:
            biz_lower = business_type.lower()

            pool_name: Optional[str] = None
            if any(word in biz_lower for word in ['photo', 'foto', 'gambar', 'jurugambar', 'photographer', 'fotografi', 'studio', 'gallery', 'galeri']):
                pool_name = "photography"
            elif any(word in biz_lower for word in ['kahwin', 'perkahwinan', 'wedding', 'pengantin', 'nikah']):
                pool_name = "wedding"
            elif any(word in biz_lower for word in ['event', 'acara', 'majlis', 'upacara', 'sambutan']):
                pool_name = "events"
            elif any(word in biz_lower for word in ['korporat', 'corporate', 'syarikat', 'company', 'business event']):
                pool_name = "corporate"
            elif any(word in biz_lower for word in ['salon', 'rambut', 'hair', 'beauty', 'kecantikan', 'spa']):
                pool_name = "beauty"
            elif any(word in biz_lower for word in ['fashion', 'fesyen', 'pakaian', 'clothing', 'boutique', 'baju', 'tudung']):
                pool_name = "fashion"
            elif any(word in biz_lower for word in ['kereta', 'car', 'auto', 'bengkel', 'workshop', 'mechanic']):
                pool_name = "automotive"
            elif any(word in biz_lower for word in ['makan', 'food', 'restoran', 'restaurant', 'nasi', 'cafe', 'warung']):
                pool_name = "food"
            elif not any(word in biz_lower for word in ['makan', 'food', 'restoran', 'restaurant', 'nasi', 'cafe', 'warung']):
                pool_name = "services"

            if pool_name:
                pool_img = self._pool_pick(pool_name, text, used_urls=used_urls)
                if pool_img:
                    logger.info(f"🎨 No specific match for '{text}', rotating {pool_name} pool → {pool_img[:60]}... (business: {business_type})")
                    return pool_img

        # Final fallback — still rotate rather than returning the same default every time
        default_pool_img = self._pool_pick("services", text, used_urls=used_urls)
        if default_pool_img:
            logger.info(f"⚠️ No specific match for '{text}', rotating services pool → {default_pool_img[:60]}...")
            return default_pool_img
        return self.BUSINESS_IMAGES["default"]

    async def get_product_image(
        self,
        item_name: str,
        business_type: str = "",
        use_ai: bool = True,
        aspect_ratio: str = "1:1"
    ) -> str:
        """
        Get image for a product - try AI generation first, fallback to stock.

        Args:
            item_name: Product/service name (e.g., "Nasi Kandar", "Baju Kurung")
            business_type: Business category
            use_ai: Whether to try AI generation first
            aspect_ratio: Image aspect ratio for AI generation

        Returns:
            Image URL (either AI-generated from storage or stock Unsplash)
        """
        if use_ai and STABILITY_AVAILABLE and self.stability_api_key:
            try:
                logger.info(f"🎨 Attempting AI generation for: {item_name}")

                # Generate image with Stability AI
                image_base64 = await generate_malaysian_image(
                    item_name,
                    business_type,
                    aspect_ratio
                )

                if image_base64 and self.supabase_url and self.supabase_key:
                    # Save to storage and get URL
                    filename = f"{item_name.lower().replace(' ', '-')}-{uuid.uuid4().hex[:8]}.webp"
                    image_url = await save_image_to_storage(
                        image_base64,
                        filename,
                        self.supabase_url,
                        self.supabase_key
                    )

                    if image_url:
                        logger.info(f"✅ AI image generated and saved: {item_name}")
                        return image_url
                    else:
                        logger.warning(f"⚠️ Failed to save AI image for: {item_name}")
                else:
                    logger.warning(f"⚠️ AI generation failed for: {item_name}")

            except Exception as e:
                logger.error(f"❌ AI generation error for {item_name}: {e}")

        # Fallback to stock Unsplash image
        logger.info(f"📸 Using stock image for: {item_name}")
        return self.get_matching_image(item_name, "all", business_type=business_type)

    def get_smart_image_prompt(self, text: str) -> Tuple[str, float]:
        """
        Get smart image prompt using fuzzy matching for Malaysian food

        Returns: (prompt, confidence_score)
        """
        if not text:
            return ("", 0.0)

        text_lower = text.lower().strip()

        # Direct exact match
        if text_lower in self.MALAYSIAN_FOOD_PROMPTS:
            logger.info(f"🎯 Exact match found: {text_lower}")
            return (self.MALAYSIAN_FOOD_PROMPTS[text_lower], 1.0)

        # Fuzzy matching - find best match
        best_match = None
        best_score = 0.0
        best_prompt = ""

        for dish_name, prompt in self.MALAYSIAN_FOOD_PROMPTS.items():
            # Calculate similarity score
            score = SequenceMatcher(None, text_lower, dish_name).ratio()

            # Also check if text contains the dish name or vice versa
            if dish_name in text_lower:
                score = max(score, 0.9)
            elif text_lower in dish_name:
                score = max(score, 0.85)

            # Check word-by-word matching for partial matches
            text_words = set(text_lower.split())
            dish_words = set(dish_name.split())
            common_words = text_words & dish_words
            if common_words:
                word_match_score = len(common_words) / max(len(text_words), len(dish_words))
                score = max(score, word_match_score * 0.8)

            if score > best_score:
                best_score = score
                best_match = dish_name
                best_prompt = prompt

        # Only use fuzzy match if confidence is high enough
        if best_score >= 0.6:
            logger.info(f"🎯 Fuzzy match: '{text}' → '{best_match}' (confidence: {best_score:.2f})")
            return (best_prompt, best_score)
        else:
            logger.info(f"⚠️ No good match for '{text}' (best: {best_match} at {best_score:.2f})")
            return ("", best_score)

    async def analyze_uploaded_image(self, image_url: str) -> Dict:
        """
        Analyze an uploaded image using AI Vision to detect its content.
        
        This helps:
        1. Suggest names for images without user-provided names
        2. Detect image content type (food, salon service, product, etc.)
        3. Warn about mismatches between image content and business type
        
        Args:
            image_url: URL of the uploaded image (Cloudinary or other CDN)
            
        Returns:
            Dict with:
            - suggested_name: Suggested item name
            - category: Detected category (food, salon, clothing, etc.)
            - description: Short description of the image
            - confidence: Confidence level (high, medium, low)
            - is_food: Boolean indicating if this appears to be food
        """
        logger.info(f"🔍 Analyzing uploaded image: {image_url[:60]}...")
        
        default_result = {
            "suggested_name": None,
            "category": "unknown",
            "description": "Unable to analyze image",
            "confidence": "low",
            "is_food": False
        }
        
        try:
            # Use Qwen VL (Vision-Language) for image analysis
            # Qwen-VL-Max supports image input via URL
            if self.qwen_api_key:
                logger.info("🟡 Using Qwen-VL for image analysis...")
                async with httpx.AsyncClient(timeout=60.0) as client:
                    response = await client.post(
                        f"{self.qwen_base_url}/chat/completions",
                        headers={
                            "Authorization": f"Bearer {self.qwen_api_key}",
                            "Content-Type": "application/json"
                        },
                        json={
                            "model": "qwen-vl-max",
                            "messages": [
                                {
                                    "role": "user",
                                    "content": [
                                        {
                                            "type": "image_url",
                                            "image_url": {"url": image_url}
                                        },
                                        {
                                            "type": "text",
                                            "text": """Analyze this image and respond in JSON format:
{
  "suggested_name": "Item name in Malay or English (e.g., 'Nasi Lemak Special', 'Haircut Men')",
  "category": "food|salon|clothing|product|other",
  "description": "Brief description of what you see",
  "is_food": true/false,
  "food_type": "malaysian|western|asian|dessert|beverage|none"
}

If it's Malaysian food, suggest authentic Malay names.
If it's a service (haircut, treatment), describe the service.
Respond ONLY with valid JSON, no other text."""
                                        }
                                    ]
                                }
                            ],
                            "temperature": 0.3,
                            "max_tokens": 200
                        }
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        content = result["choices"][0]["message"]["content"].strip()
                        logger.info(f"🟡 Qwen-VL response: {content[:100]}...")
                        
                        # Parse JSON response
                        import json as json_module
                        try:
                            # Clean up response - remove markdown code blocks if present
                            if content.startswith("```"):
                                content = content.split("```")[1]
                                if content.startswith("json"):
                                    content = content[4:]
                            content = content.strip()
                            
                            analysis = json_module.loads(content)
                            analysis["confidence"] = "high"
                            logger.info(f"✅ Image analyzed: {analysis.get('suggested_name')} - {analysis.get('category')}")
                            return analysis
                        except json_module.JSONDecodeError:
                            logger.warning("⚠️ Could not parse Qwen-VL response as JSON")
                    else:
                        logger.warning(f"⚠️ Qwen-VL failed: {response.status_code}")
            
            # Fallback to DeepSeek (if it supports vision)
            if self.deepseek_api_key:
                logger.info("🔷 Trying DeepSeek for image analysis...")
                # Note: DeepSeek chat doesn't support vision, but we can try
                # to describe based on URL patterns or use a different approach
                
            return default_result
            
        except Exception as e:
            logger.error(f"❌ Error analyzing image: {e}")
            return default_result

    async def analyze_images_batch(self, images: List[Dict]) -> List[Dict]:
        """
        Analyze a batch of uploaded images.
        
        Args:
            images: List of image dicts with 'url' and optional 'name'
            
        Returns:
            List of analysis results with suggested names and categories
        """
        results = []
        for img in images:
            url = img.get('url', '') if isinstance(img, dict) else str(img)
            existing_name = img.get('name', '') if isinstance(img, dict) else ''
            
            if not url:
                continue
                
            # Skip if user already provided a valid name
            if existing_name and existing_name.strip() and existing_name != 'Hero Image':
                results.append({
                    "url": url,
                    "user_name": existing_name,
                    "suggested_name": existing_name,
                    "category": "user_provided",
                    "analyzed": False
                })
                continue
            
            # Analyze the image
            analysis = await self.analyze_uploaded_image(url)
            results.append({
                "url": url,
                "user_name": existing_name,
                "suggested_name": analysis.get("suggested_name"),
                "category": analysis.get("category", "unknown"),
                "description": analysis.get("description"),
                "is_food": analysis.get("is_food", False),
                "analyzed": True
            })
            
            # Small delay between API calls
            await asyncio.sleep(0.5)
        
        return results

    async def test_api_connectivity(self) -> Dict[str, any]:
        """Test connectivity to both AI APIs"""
        results = {
            "qwen": {"status": "not_configured", "error": None},
            "deepseek": {"status": "not_configured", "error": None}
        }

        # Test Qwen API
        if self.qwen_api_key:
            try:
                logger.info("🟡 Testing Qwen API connectivity...")
                async with httpx.AsyncClient(timeout=30.0) as client:
                    r = await client.post(
                        f"{self.qwen_base_url}/chat/completions",
                        headers={
                            "Authorization": f"Bearer {self.qwen_api_key}",
                            "Content-Type": "application/json"
                        },
                        json={
                            "model": "qwen-max",
                            "messages": [{"role": "user", "content": "Hello"}],
                            "max_tokens": 10
                        }
                    )
                    if r.status_code == 200:
                        results["qwen"]["status"] = "connected"
                        logger.info("🟡 Qwen API ✅ Connection successful")
                    else:
                        results["qwen"]["status"] = "error"
                        results["qwen"]["error"] = f"HTTP {r.status_code}: {r.text}"
                        logger.error(f"🟡 Qwen API ❌ Status {r.status_code}")
            except Exception as e:
                results["qwen"]["status"] = "error"
                results["qwen"]["error"] = str(e)
                logger.error(f"🟡 Qwen API ❌ Exception: {e}")

        # Test DeepSeek API
        if self.deepseek_api_key:
            try:
                logger.info("🔷 Testing DeepSeek API connectivity...")
                async with httpx.AsyncClient(timeout=30.0) as client:
                    r = await client.post(
                        f"{self.deepseek_base_url}/chat/completions",
                        headers={
                            "Authorization": f"Bearer {self.deepseek_api_key}",
                            "Content-Type": "application/json"
                        },
                        json={
                            "model": self.deepseek_model,
                            "messages": [{"role": "user", "content": "Hello"}],
                            "max_tokens": 10
                        }
                    )
                    if r.status_code == 200:
                        results["deepseek"]["status"] = "connected"
                        logger.info("🔷 DeepSeek API ✅ Connection successful")
                    else:
                        results["deepseek"]["status"] = "error"
                        results["deepseek"]["error"] = f"HTTP {r.status_code}: {r.text}"
                        logger.error(f"🔷 DeepSeek API ❌ Status {r.status_code}")
            except Exception as e:
                results["deepseek"]["status"] = "error"
                results["deepseek"]["error"] = str(e)
                logger.error(f"🔷 DeepSeek API ❌ Exception: {e}")

        return results

    # ==================== STABILITY AI IMAGE GENERATION ====================
    async def generate_image(self, prompt: str) -> Optional[str]:
        """Generate image using Stability AI"""
        if not self.stability_api_key:
            logger.info("🎨 No Stability API key")
            return None

        try:
            logger.info(f"🎨 Generating: {prompt[:40]}...")

            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    "https://api.stability.ai/v1/generation/stable-diffusion-xl-1024-v1-0/text-to-image",
                    headers={
                        "Authorization": f"Bearer {self.stability_api_key}",
                        "Content-Type": "application/json",
                        "Accept": "application/json"
                    },
                    json={
                        "text_prompts": [
                            {"text": f"{prompt}, professional photography, high quality, realistic", "weight": 1},
                            {"text": "blurry, bad quality, cartoon, illustration, drawing, anime", "weight": -1}
                        ],
                        "cfg_scale": 7,
                        "width": 1024,
                        "height": 576,
                        "steps": 30,
                        "samples": 1,
                        "style_preset": "photographic"
                    }
                )

                if response.status_code == 200:
                    data = response.json()
                    base64_img = data["artifacts"][0]["base64"]
                    logger.info("🎨 ✅ Image generated")
                    return f"data:image/png;base64,{base64_img}"
                else:
                    logger.error(f"🎨 ❌ Failed: {response.status_code}")
        except Exception as e:
            logger.error(f"🎨 ❌ Error: {e}")

        return None

    def get_image_prompts(self, description: str) -> Dict:
        """Get image prompts based on business description - WITH MALAYSIAN FOOD SUPPORT"""
        d = description.lower()

        # Check for Malaysian food dishes using smart matching
        logger.info(f"🍽️ Analyzing description for Malaysian food: {description[:100]}...")

        # Try to find Malaysian food mentions in the description
        words = d.split()
        detected_dishes = []

        # Check for multi-word dish names (like "nasi lemak", "char kway teow")
        for i in range(len(words)):
            for j in range(i + 1, min(i + 5, len(words) + 1)):  # Check up to 4-word phrases
                phrase = " ".join(words[i:j])
                prompt, confidence = self.get_smart_image_prompt(phrase)
                if prompt and confidence >= 0.6:
                    detected_dishes.append((phrase, prompt, confidence))

        # If we found Malaysian dishes, use them!
        if detected_dishes:
            # Use the best match
            detected_dishes.sort(key=lambda x: x[2], reverse=True)
            best_dish, best_prompt, confidence = detected_dishes[0]

            logger.info(f"🎯 MALAYSIAN FOOD DETECTED: '{best_dish}' (confidence: {confidence:.2f})")

            # Generate 4 different prompts for gallery
            gallery_prompts = [best_prompt]

            # Add variations
            if "nasi" in best_dish:
                gallery_prompts.extend([
                    best_prompt.replace("plate", "serving platter"),
                    f"Close-up of {best_dish} showing delicious details",
                    f"Traditional Malaysian {best_dish} in authentic setting"
                ])
            elif "mee" in best_dish or "laksa" in best_dish or "noodle" in best_dish:
                gallery_prompts.extend([
                    best_prompt.replace("noodles", "noodle bowl close-up"),
                    f"Steaming hot bowl of {best_dish}",
                    f"Traditional {best_dish} with all toppings"
                ])
            else:
                gallery_prompts.extend([
                    best_prompt + ", close-up view",
                    f"Traditional {best_dish} presentation",
                    f"Authentic Malaysian {best_dish}"
                ])

            return {
                "hero": best_prompt,
                "gallery": gallery_prompts[:4]
            }

        # Fallback to existing logic for non-Malaysian food
        if "teddy" in d or "bear" in d or "plush" in d or "patung" in d:
            return {
                "hero": "Cute teddy bear shop with soft plush toys on shelves, warm cozy lighting",
                "gallery": [
                    "Adorable brown teddy bear sitting, soft fluffy plush toy",
                    "Collection of colorful teddy bears on display",
                    "Giant pink teddy bear in gift shop",
                    "Small cute teddy bears with ribbon bows"
                ]
            }

        if "ikan" in d or "fish" in d or "seafood" in d:
            return {
                "hero": "Fresh fish market with seafood on ice display",
                "gallery": [
                    "Fresh red snapper fish on ice",
                    "Fresh prawns and shrimp display",
                    "Fresh salmon fillets at counter",
                    "Variety of tropical fish"
                ]
            }

        if "makan" in d or "restoran" in d or "food" in d or "nasi" in d:
            return {
                "hero": "Modern Malaysian restaurant interior with warm lighting",
                "gallery": [
                    "Delicious nasi lemak with sambal",
                    "Chef cooking in restaurant kitchen",
                    "Elegant restaurant table setting",
                    "Malaysian cuisine dishes spread"
                ]
            }

        if any(w in d for w in ['salon', 'rambut', 'hair', 'beauty']):
            return {
                "hero": "Modern luxury hair salon interior",
                "gallery": [
                    "Hairstylist cutting hair in salon",
                    "Hair coloring treatment",
                    "Hair washing station",
                    "Hair styling products"
                ]
            }

        if any(w in d for w in ['kucing', 'cat', 'pet']):
            return {
                "hero": "Modern pet shop with cute cats",
                "gallery": [
                    "Adorable orange tabby cat",
                    "Cat food and supplies",
                    "Playful kittens",
                    "Cat grooming service"
                ]
            }

        if "bakery" in d or "roti" in d or "kek" in d or "cake" in d:
            return {
                "hero": "Artisan bakery with fresh bread and pastries",
                "gallery": [
                    "Fresh baked bread loaves",
                    "Decorated birthday cakes",
                    "Croissants and pastries",
                    "Baker preparing dough"
                ]
            }

        if "kereta" in d or "car" in d or "bengkel" in d or "workshop" in d:
            return {
                "hero": "Modern car workshop garage",
                "gallery": [
                    "Mechanic working on car engine",
                    "Car tire service",
                    "Auto mechanic under car",
                    "Automotive service center"
                ]
            }

        # Default
        return {
            "hero": f"{description} business storefront, professional",
            "gallery": [
                f"{description} products",
                f"{description} service",
                f"Customer at {description}",
                f"{description} interior"
            ]
        }

    async def generate_business_images(self, description: str) -> Optional[Dict]:
        """Generate all images for a business"""
        if not self.stability_api_key:
            return None

        prompts = self.get_image_prompts(description)

        logger.info("🎨 GENERATING IMAGES WITH STABILITY AI...")

        # Generate hero
        import asyncio
        hero = await self.generate_image(prompts["hero"])
        if not hero:
            return None

        # Generate gallery
        gallery = []
        for i, prompt in enumerate(prompts["gallery"]):
            logger.info(f"🎨 Gallery {i+1}/4...")
            img = await self.generate_image(prompt)
            if img:
                gallery.append(img)
            await asyncio.sleep(0.3)

        if len(gallery) < 3:
            return None

        logger.info(f"🎨 ✅ Generated {len(gallery) + 1} images")
        return {"hero": hero, "gallery": gallery}

    async def generate_food_image(
        self, food_name: str, zai_phase: Optional[Dict] = None
    ) -> Optional[str]:
        """
        Generate AI image for a food item using the full pipeline:
        1. DeepSeek/Qwen generates detailed English description
        2. Stability AI generates image from description
        3. Image uploaded to Cloudinary

        Args:
            food_name: Name of the food item (e.g., "Nasi Kandar Special", "Ayam Goreng Berempah")

        Returns:
            Cloudinary URL of generated image, or None if generation fails
        """
        if not self._image_generation_available():
            logger.warning("🎨 No image-generation API key configured")
            return None

        try:
            logger.info(f"🎨 Generating AI image for: {food_name}")

            # Step 1: Check if it's a known Malaysian dish - prioritize Malaysian prompts
            malaysian_prompt = self._get_malaysian_prompt(food_name)
            if malaysian_prompt and "Malaysian" in malaysian_prompt:
                # Known Malaysian dish - use predefined prompt for accuracy
                detailed_description = malaysian_prompt
                logger.info(f"🇲🇾 Using Malaysian-specific prompt: {detailed_description[:100]}...")
            else:
                # Unknown dish - generate description using AI
                detailed_description = await self._generate_food_description(food_name)
                if not detailed_description:
                    logger.warning("⚠️ Failed to generate description, using generic fallback")
                    detailed_description = malaysian_prompt or f"{food_name}, professional food photography, high quality, realistic"
                else:
                    logger.info(f"📝 AI Description: {detailed_description[:100]}...")

            # Step 2: Generate image with the selected provider (IMAGE_PROVIDER:
            # Z.ai with Stability fallback, or Stability directly) using the
            # detailed description
            image_url = await self._generate_image(detailed_description, zai_phase=zai_phase)

            if image_url:
                logger.info(f"✅ Generated image: {image_url[:60]}...")
            else:
                logger.warning(f"⚠️ Failed to generate image for: {food_name}")

            return image_url
        except Exception as e:
            logger.error(f"❌ Error generating food image: {e}")
            return None

    async def _generate_food_description(self, food_name: str) -> Optional[str]:
        """
        Use DeepSeek/Qwen to generate a detailed English description for Stability AI

        Args:
            food_name: Name of the food (e.g., "Nasi Kandar Special")

        Returns:
            Detailed English description for image generation, or None if failed
        """
        try:
            # Prepare prompt for AI to generate image description
            system_prompt = """You are an expert at creating detailed image prompts for AI image generation, specializing in Malaysian cuisine.

CRITICAL: Pay attention to the food's origin and style:
- Malaysian dishes (nasi kandar, ayam goreng, ikan bakar, etc.) should be described in authentic Malaysian/Mamak style
- Avoid confusing Malaysian food with Chinese, Thai, or other Asian cuisines
- Use specific Malaysian ingredients and presentation (banana leaf, curry gravy, sambal, etc.)

Focus on:
- Visual appearance (colors, textures, arrangement)
- Authentic traditional presentation (mamak style for Malaysian food)
- Serving method (banana leaf, plate, traditional serving)
- Specific ingredients visible (curry, rice, sambal for Malaysian)
- Photography style (food photography, professional lighting)

Keep the description concise (under 100 words) but highly descriptive and culturally accurate."""

            user_prompt = f"""Create a detailed image generation prompt for: "{food_name}"

IMPORTANT:
- If this contains "nasi", "ayam", "ikan", "mee" or other Malay words, it's MALAYSIAN food
- Describe Malaysian dishes authentically with curry, rice, sambal, banana leaf
- DO NOT describe Malaysian food as Chinese food
- Use "Malaysian" explicitly in the description for Malaysian dishes

Format: Just the image description, no explanations."""

            # Try DeepSeek first (better for descriptions)
            if self.deepseek_api_key:
                logger.info(f"🔷 Using DeepSeek to generate description for: {food_name}")
                try:
                    async with httpx.AsyncClient(timeout=30) as client:
                        response = await client.post(
                            f"{self.deepseek_base_url}/chat/completions",
                            headers={
                                "Authorization": f"Bearer {self.deepseek_api_key}",
                                "Content-Type": "application/json"
                            },
                            json={
                                "model": self.deepseek_model,
                                "messages": [
                                    {"role": "system", "content": system_prompt},
                                    {"role": "user", "content": user_prompt}
                                ],
                                "temperature": 0.7,
                                "max_tokens": 200
                            }
                        )

                        if response.status_code == 200:
                            result = response.json()
                            description = result["choices"][0]["message"]["content"].strip()
                            logger.info("✅ DeepSeek generated description")
                            return description
                        else:
                            logger.warning(f"DeepSeek failed: {response.status_code}")
                except Exception as e:
                    logger.warning(f"DeepSeek error: {e}")

            # Fallback to Qwen
            if self.qwen_api_key:
                logger.info(f"🟡 Using Qwen to generate description for: {food_name}")
                try:
                    async with httpx.AsyncClient(timeout=30) as client:
                        response = await client.post(
                            f"{self.qwen_base_url}/chat/completions",
                            headers={
                                "Authorization": f"Bearer {self.qwen_api_key}",
                                "Content-Type": "application/json"
                            },
                            json={
                                "model": "qwen-max",
                                "messages": [
                                    {"role": "system", "content": system_prompt},
                                    {"role": "user", "content": user_prompt}
                                ],
                                "temperature": 0.7,
                                "max_tokens": 200
                            }
                        )

                        if response.status_code == 200:
                            result = response.json()
                            description = result["choices"][0]["message"]["content"].strip()
                            logger.info("✅ Qwen generated description")
                            return description
                        else:
                            logger.warning(f"Qwen failed: {response.status_code}")
                except Exception as e:
                    logger.warning(f"Qwen error: {e}")

            # No AI available
            logger.warning("No AI service available for description generation")
            return None

        except Exception as e:
            logger.error(f"Error generating food description: {e}")
            return None

    async def _generate_stability_image(self, prompt: str, food: bool = True) -> Optional[str]:
        """Generate image with Stability AI and upload to Cloudinary.

        Args:
            prompt: the image prompt seed.
            food: when True (default, food path) the prompt is routed through
                _get_malaysian_prompt() which maps known dish names to curated
                food prompts and otherwise appends "Malaysian style, food
                photography, appetizing". Non-food callers pass food=False to
                skip that food-oriented mapping — the prompt is used verbatim —
                so e.g. a toy-shop product isn't turned into a food photo.
        """
        stability_key = os.getenv("STABILITY_API_KEY")
        if not stability_key:
            logger.warning("🎨 No STABILITY_API_KEY")
            return None

        try:
            # Smart prompt for Malaysian context (food path only). Non-food
            # callers pass the prompt through unchanged.
            smart_prompt = self._get_malaysian_prompt(prompt) if food else prompt
            logger.info(f"🎨 Prompt: {smart_prompt[:80]}...")

            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.post(
                    "https://api.stability.ai/v2beta/stable-image/generate/core",
                    headers={
                        "Authorization": f"Bearer {stability_key}",
                        "Accept": "image/*"
                    },
                    files={"none": ""},
                    data={
                        "prompt": smart_prompt,
                        "output_format": "png",
                        "aspect_ratio": "16:9"
                    }
                )

                if response.status_code == 200:
                    # Upload to Cloudinary
                    result = cloudinary.uploader.upload(
                        response.content,
                        folder="binaapp"
                    )
                    url = result.get("secure_url")
                    logger.info(f"☁️ Uploaded to Cloudinary: {url[:50]}...")
                    return url
                else:
                    logger.error(f"🎨 Stability AI failed: {response.status_code} - {response.text[:200]}")
                    return None
        except Exception as e:
            logger.error(f"🎨 Error generating image: {e}")
            return None

    async def _generate_image_zai(self, prompt: str) -> Optional[str]:
        """Generate an image with Z.ai (CogView / GLM-Image) and upload to Cloudinary.

        POSTs the OpenAI-style images payload to {zai_base_url}/images/generations.
        The response carries a hosted image URL (data[0].url) — we download it
        and push the bytes through the same Cloudinary upload the Stability
        path uses, so downstream behaviour (PHOTO_SLOT binding, prompt wiring)
        is identical regardless of provider. Each HTTP call is bounded by
        ZAI_IMAGE_TIMEOUT_SECONDS; a 429 (Z.ai code 1302 rate limit) is
        retried with ZAI_IMAGE_RETRY_BACKOFF_SECONDS backoff before giving up.
        Returns the Cloudinary secure URL, or None on any failure — the
        _generate_image dispatcher decides the fallback. Callers must go
        through _generate_image, which serializes Z.ai requests (the endpoint
        rejects concurrency) and enforces the per-build phase budget.
        """
        if not self.zai_api_key:
            logger.warning("🎨 No ZAI_API_KEY — cannot generate Z.ai image")
            return None

        try:
            logger.info(f"🎨 Z.ai ({self.zai_image_model}) prompt: {prompt[:80]}...")
            backoffs = ZAI_IMAGE_RETRY_BACKOFF_SECONDS
            async with httpx.AsyncClient(timeout=ZAI_IMAGE_TIMEOUT_SECONDS) as client:
                response = None
                for attempt in range(1 + len(backoffs)):
                    response = await client.post(
                        f"{self.zai_base_url}/images/generations",
                        headers={
                            "Authorization": f"Bearer {self.zai_api_key}",
                            "Content-Type": "application/json",
                        },
                        json={
                            "model": self.zai_image_model,
                            "prompt": prompt,
                            "size": "1024x1024",
                        },
                    )
                    # Rate limit (HTTP 429, Z.ai code 1302): back off and
                    # retry — its image endpoint rejects request bursts.
                    if response.status_code != 429:
                        break
                    if attempt < len(backoffs):
                        wait = backoffs[attempt]
                        logger.warning(
                            f"🎨 Z.ai image rate-limited (429/code 1302) — "
                            f"retry {attempt + 1}/{len(backoffs)} in {wait:.0f}s"
                        )
                        await asyncio.sleep(wait)
                if response.status_code == 429:
                    logger.error(
                        f"🎨 Z.ai image rate limit persisted after "
                        f"{len(backoffs)} retries — giving up: {response.text[:200]}"
                    )
                    return None
                if response.status_code != 200:
                    logger.error(
                        f"🎨 Z.ai image failed: {response.status_code} - {response.text[:200]}"
                    )
                    return None

                data = response.json()
                items = data.get("data") or []
                image_url = (items[0] or {}).get("url") if items else None
                if not image_url:
                    logger.error("🎨 Z.ai image response had no data[0].url")
                    return None

                download = await client.get(image_url)
                if download.status_code != 200:
                    logger.error(f"🎨 Z.ai image download failed: {download.status_code}")
                    return None
                image_bytes = download.content

            result = cloudinary.uploader.upload(image_bytes, folder="binaapp")
            url = result.get("secure_url")
            if url:
                logger.info(f"☁️ Z.ai image uploaded to Cloudinary: {url[:50]}...")
            return url
        except httpx.TimeoutException:
            logger.error(f"🎨 Z.ai image timed out ({ZAI_IMAGE_TIMEOUT_SECONDS:.0f}s cap)")
            return None
        except Exception as e:
            logger.error(f"🎨 Z.ai image error: {e}")
            return None

    def _get_zai_image_lock(self) -> asyncio.Lock:
        """Lazily create the Z.ai serialization lock inside the event loop."""
        if self._zai_image_lock is None:
            self._zai_image_lock = asyncio.Lock()
        return self._zai_image_lock

    @staticmethod
    def _new_zai_image_phase() -> Dict:
        """Per-build Z.ai image phase state, threaded through every image call
        of one generate_website build (auto-fill + food-image pass share it).
        `spent` accumulates the time spent INSIDE Z.ai image calls — HTML
        generation between the two passes doesn't count against the budget.
        """
        return {
            "spent": 0.0,
            "budget": zai_image_phase_budget_seconds(),
            "exhausted": False,
        }

    def _zai_phase_exhausted(self, zai_phase: Optional[Dict]) -> bool:
        """True once this build's Z.ai image budget is spent (logged once)."""
        if not zai_phase:
            return False
        if zai_phase.get("exhausted"):
            return True
        if zai_phase["spent"] >= zai_phase["budget"]:
            zai_phase["exhausted"] = True
            logger.warning(
                f"⏰ Z.ai image phase budget exhausted "
                f"({zai_phase['spent']:.0f}s >= {zai_phase['budget']:.0f}s) — "
                f"remaining images go straight to Stability"
            )
            return True
        return False

    async def _pace_zai_image_request(self) -> None:
        """Sleep so consecutive Z.ai requests are at least
        ZAI_IMAGE_REQUEST_DELAY_SECONDS apart. Called under the lock."""
        delay = zai_image_request_delay_seconds()
        if delay <= 0 or not self._zai_last_request_at:
            return
        wait = delay - (time.monotonic() - self._zai_last_request_at)
        if wait > 0:
            await asyncio.sleep(wait)

    async def _generate_image(
        self,
        prompt: str,
        food: bool = True,
        zai_phase: Optional[Dict] = None,
    ) -> Optional[str]:
        """Provider-selecting wrapper around single-image generation.

        IMAGE_PROVIDER=zai routes through Z.ai first and falls back to the
        untouched Stability path when STABILITY_API_KEY is set; the default
        'stability' keeps the existing path exactly as before. Z.ai requests
        are SERIALIZED (its endpoint 429s on concurrency) with a spacing
        delay, and honour the per-build phase budget in `zai_phase` — once
        spent, the image goes straight to Stability. The Stability fallback
        itself runs OUTSIDE the lock, so fallback images keep their original
        concurrency. Logs which provider actually served each image. Returns
        a Cloudinary URL, or None when every configured provider fails
        (existing no-image behaviour applies downstream).
        """
        if image_provider() == "zai":
            # Same Malaysian-food prompt mapping the Stability path applies
            # internally, so a raw dish name still becomes a curated prompt.
            zai_prompt = self._get_malaysian_prompt(prompt) if food else prompt
            url = None
            if not self._zai_phase_exhausted(zai_phase):
                async with self._get_zai_image_lock():
                    # Re-check after queueing: images ahead of us in the lock
                    # queue may have spent the remaining budget.
                    if not self._zai_phase_exhausted(zai_phase):
                        await self._pace_zai_image_request()
                        _zai_started = time.monotonic()
                        try:
                            url = await self._generate_image_zai(zai_prompt)
                        finally:
                            self._zai_last_request_at = time.monotonic()
                            if zai_phase is not None:
                                zai_phase["spent"] += time.monotonic() - _zai_started
            if url:
                logger.info(f"🖼️ Image served by provider=zai: {url[:60]}...")
                return url
            if self.stability_api_key:
                logger.warning("🎨 Z.ai image failed/skipped — falling back to Stability")
                url = await self._generate_stability_image(prompt, food=food)
                if url:
                    logger.info(f"🖼️ Image served by provider=stability (fallback): {url[:60]}...")
                return url
            return None

        url = await self._generate_stability_image(prompt, food=food)
        if url:
            logger.info(f"🖼️ Image served by provider=stability: {url[:60]}...")
        return url

    def _image_generation_available(self) -> bool:
        """True when the selected provider (or its fallback) has a key set."""
        if image_provider() == "zai":
            return bool(self.zai_api_key or self.stability_api_key)
        return bool(self.stability_api_key)

    def _get_malaysian_prompt(self, item: str) -> str:
        """Convert Malaysian food names to detailed prompts"""
        prompts = {
            "nasi kandar": "Malaysian nasi kandar with rice, curry chicken, vegetables, banana leaf, food photography, high quality, realistic",
            "nasi lemak": "Malaysian nasi lemak coconut rice, sambal, egg, anchovies, peanuts, banana leaf, food photography, high quality",
            "nasi goreng": "Malaysian nasi goreng fried rice, egg, vegetables, sambal, food photography, high quality",
            "nasi ayam": "Malaysian chicken rice hainanese nasi ayam, roasted chicken, rice, cucumber, food photography",
            "nasi briyani": "Malaysian nasi briyani biryani rice, spiced rice, chicken, raita, food photography",
            "nasi kerabu": "Malaysian nasi kerabu blue rice, herbs, vegetables, fish, food photography, traditional",

            "mee goreng": "Malaysian mee goreng yellow noodles, egg, vegetables, spicy, food photography, high quality",
            "char kway teow": "Malaysian char kway teow flat noodles, prawns, cockles, wok fried, food photography",
            "laksa": "Malaysian laksa spicy noodle soup, coconut milk, shrimp, food photography, traditional",
            "hokkien mee": "Malaysian hokkien mee dark noodles, prawns, pork, food photography, high quality",
            "mee rebus": "Malaysian mee rebus noodles, thick gravy, egg, food photography",

            "ayam goreng": "Malaysian fried chicken ayam goreng berempah, crispy, golden, turmeric, food photography, close up",
            "ayam percik": "Malaysian ayam percik grilled chicken, coconut sauce, food photography, traditional",
            "rendang": "Malaysian beef rendang curry, coconut milk, spicy, food photography, close up, high quality",

            "ikan bakar": "Malaysian ikan bakar grilled fish, sambal, banana leaf, food photography, traditional",
            "ikan": "Malaysian grilled fish, sambal sauce, food photography, high quality",

            "roti canai": "Malaysian roti canai flatbread crispy, served with curry, food photography, close up",
            "roti": "Malaysian roti flatbread, curry, food photography",
            "murtabak": "Malaysian murtabak stuffed pancake, egg, meat, curry, food photography",

            "satay": "Malaysian satay skewered meat, peanut sauce, cucumber, food photography, traditional, close up",

            "teh tarik": "Malaysian teh tarik pulled milk tea, frothy, glass, food photography, traditional",
            "kopi": "Malaysian kopi coffee traditional, glass cup, food photography",

            "cendol": "Malaysian cendol dessert, shaved ice, coconut milk, gula melaka, green jelly, food photography",
            "ais kacang": "Malaysian ais kacang shaved ice dessert, colorful toppings, food photography",

            "pelbagai lauk": "Malaysian mixed side dishes, variety of curries and vegetables, food photography",
            "lauk": "Malaysian side dishes curry vegetables, food photography",
        }

        item_lower = item.lower().strip()

        # Direct exact match
        if item_lower in prompts:
            return prompts[item_lower]

        # Fuzzy matching - check if item contains any key
        for key, prompt in prompts.items():
            if key in item_lower:
                return prompt

        # Generic food prompt
        return f"Professional close-up photo of {item}, Malaysian style, food photography, high quality, realistic, appetizing"

    def _extract_menu_items(self, description: str) -> list:
        """Extract menu items from description"""
        common_items = ["nasi kandar", "nasi lemak", "mee goreng", "ayam goreng",
                        "roti canai", "teh tarik", "ikan bakar", "pelbagai lauk", "satay"]
        found = []
        desc_lower = description.lower()
        for item in common_items:
            if item in desc_lower:
                found.append(item)
        return found if found else ["hero image"]

    def _detect_business_category(self, description: str) -> str:
        """Detect if business is food/restaurant or clothing/fashion"""
        desc_lower = description.lower()

        # Clothing/Fashion keywords
        clothing_keywords = [
            "baju", "shirt", "t-shirt", "kemeja", "fashion", "boutique", "clothing",
            "pakaian", "tudung", "hijab", "scarf", "shawl", "dress", "pants",
            "seluar", "skirt", "jacket", "blazer", "apparel", "garment",
            "butik", "koleksi", "collection", "wear", "attire"
        ]

        # Food/Restaurant keywords
        food_keywords = [
            "nasi", "mee", "ayam", "ikan", "restaurant", "restoran", "cafe",
            "kafe", "kedai makan", "food", "makan", "masak", "cook", "menu",
            "roti", "satay", "rendang", "curry", "mamak", "warung"
        ]

        # Count matches
        clothing_score = sum(1 for keyword in clothing_keywords if keyword in desc_lower)
        food_score = sum(1 for keyword in food_keywords if keyword in desc_lower)

        if clothing_score > food_score:
            return "clothing"
        elif food_score > 0:
            return "food"
        else:
            return "general"

    def _extract_clothing_items(self, description: str) -> list:
        """Extract clothing/fashion items from description"""
        common_items = ["shirt", "baju", "t-shirt", "kemeja", "seluar", "pants",
                        "dress", "tudung", "hijab", "koleksi", "collection"]
        found = []
        desc_lower = description.lower()
        for item in common_items:
            if item in desc_lower:
                found.append(item)
        # If nothing found, return generic clothing items
        return found if found else ["shirt", "baju", "koleksi", "collection"]

    def _get_clothing_prompt(self, item: str) -> str:
        """Get appropriate Stability AI prompt for clothing items"""
        item_lower = item.lower()

        prompts = {
            "shirt": "Premium men's dress shirt on mannequin, elegant fabric, professional product photography, boutique setting",
            "baju": "Malaysian men's traditional and modern clothing, baju melayu and casual shirts, fashion photography",
            "t-shirt": "Stylish men's t-shirt on display, modern casual wear, product photography",
            "kemeja": "Elegant men's formal shirt, crisp fabric, professional fashion photography",
            "seluar": "Men's premium pants on display, formal and casual wear, boutique photography",
            "pants": "Men's premium pants on display, formal and casual wear, boutique photography",
            "dress": "Elegant dress on mannequin, luxury boutique setting, fashion photography",
            "tudung": "Elegant hijab tudung collection display, various styles, Malaysian fashion photography",
            "hijab": "Elegant hijab collection display, various colors and styles, fashion photography",
            "koleksi": "Stylish men's clothing collection display, premium shirts and apparel, boutique setting",
            "collection": "Premium men's clothing collection, modern boutique display, fashion photography",
        }

        for key, prompt in prompts.items():
            if key in item_lower:
                return prompt

        return f"Professional {item} display, Malaysian boutique, fashion photography"

    # Malay to English translation for Stability AI
    MALAY_TO_ENGLISH = {
        "jam tangan": "wristwatch timepiece",
        "jam": "watch clock",
        "baju": "shirt clothing garment",
        "kasut": "shoes footwear",
        "tudung": "hijab headscarf",
        "makanan": "food cuisine",
        "restoran": "restaurant dining",
        "kedai": "shop store",
        "perkhidmatan": "services",
        "kecantikan": "beauty cosmetics",
        "salon": "hair salon beauty parlor",
        "nasi": "rice dish",
        "mee": "noodles",
        "ayam": "chicken",
        "ikan": "fish seafood",
        "daging": "beef meat",
        "sayur": "vegetables",
        "kuih": "traditional cakes pastries",
        "minuman": "beverages drinks",
    }

    def _translate_for_stability(self, text: str) -> str:
        """Translate Malay keywords to English for Stability AI"""
        text_lower = text.lower()
        for malay, english in self.MALAY_TO_ENGLISH.items():
            if malay in text_lower:
                text_lower = text_lower.replace(malay, english)
        return text_lower

    def _get_product_prompts(self, description: str, business_category: str) -> list:
        """Generate smart product image prompts based on business type"""
        desc_lower = description.lower()

        # Translate Malay to English for better detection
        desc_english = self._translate_for_stability(description)

        # WATCHES / JEWELRY
        if any(word in desc_lower for word in ["watch", "jam tangan", "timepiece", "jam"]):
            return [
                "Luxury silver wristwatch on white background, product photography, elegant timepiece, professional lighting",
                "Black sports watch with rubber strap, waterproof dive watch, product photography, studio lighting",
                "Rose gold women's watch with diamond bezel, luxury feminine timepiece, product photography, elegant display",
                "Chronograph watch with leather strap, men's luxury watch, detailed product photography, white background"
            ]

        # JEWELRY / ACCESSORIES
        elif any(word in desc_lower for word in ["jewelry", "necklace", "bracelet", "ring", "earing", "perhiasan"]):
            return [
                "Gold necklace on display, luxury jewelry, product photography, elegant presentation",
                "Silver bracelet on white background, premium jewelry, professional product photography",
                "Diamond ring on velvet cushion, luxury engagement ring, professional jewelry photography",
                "Pearl earrings on display, elegant jewelry, product photography, studio lighting"
            ]

        # CLOTHING / FASHION (already handled but adding here for completeness)
        elif business_category == "clothing":
            return [
                "Premium men's dress shirt on mannequin, business formal, product photography",
                "Casual men's polo shirt, modern style, product photography",
                "Traditional baju melayu, elegant Malaysian menswear, product photography",
                "Men's casual jacket, modern fashion, product photography"
            ]

        # FOOD / RESTAURANT (already handled but adding here for completeness)
        elif business_category == "food":
            return [
                "Malaysian nasi kandar with curry, food photography, professional lighting",
                "Crispy fried chicken ayam goreng, food photography, delicious presentation",
                "Grilled fish ikan bakar on banana leaf, food photography, authentic Malaysian",
                "Malaysian curry dishes assortment, food photography, colorful spread"
            ]

        # BEAUTY / SALON
        elif any(word in desc_lower for word in ["beauty", "salon", "kecantikan", "spa", "facial", "makeup"]):
            return [
                "Professional hair styling service, modern salon interior, beauty photography",
                "Facial treatment spa session, relaxing ambiance, professional beauty photography",
                "Makeup application service, cosmetics display, professional beauty photography",
                "Manicure pedicure service, nail salon, professional beauty photography"
            ]

        # GENERIC FALLBACK - use business type
        else:
            business_type = self.request.business_type if hasattr(self, 'request') else "product"
            return [
                f"Professional product photo, {business_type}, clean white background, studio lighting",
                f"Premium {business_type} showcase, commercial photography, professional presentation",
                f"Elegant {business_type} display, professional product photography, modern style",
                f"High-end {business_type} product, studio photography, luxury presentation"
            ]

    async def generate_smart_image_prompts(self, description: str) -> dict:
        """Use AI to generate appropriate image prompts for ANY business type"""

        # Check if this is a Malaysian food business - use specific prompts
        desc_lower = description.lower()
        if any(word in desc_lower for word in ['nasi', 'mee', 'ayam', 'ikan', 'restoran', 'restaurant', 'kedai makan', 'warung', 'mamak', 'kandar', 'lemak', 'goreng']):
            logger.info("🍽️ Detected Malaysian food business - using Malaysian food prompts")
            return self._get_malaysian_food_prompts(description)

        prompt = f"""You are an expert at creating image prompts for Stability AI.

BUSINESS DESCRIPTION:
{description}

TASK:
Analyze this business and generate 5 specific image prompts that match this EXACT business type.

IMPORTANT FOR MALAYSIAN FOOD BUSINESSES:
- If it's a Malaysian restaurant/food business, use specific Malaysian dish names
- Examples: "nasi kandar", "nasi lemak", "mee goreng", "char kway teow", "roti canai"
- Each prompt must describe the ACTUAL Malaysian dish, not generic food

RULES:
1. If it's a PHOTOGRAPHER business → generate prompts for cameras, wedding photos, portrait sessions
2. If it's a RESTAURANT/FOOD → generate prompts for SPECIFIC dishes mentioned in description
3. If it's a FASHION store → generate prompts for clothing items, boutique display
4. If it's a SALON → generate prompts for hairstyling, beauty treatments
5. If it's a WATCH/JEWELRY store → generate prompts for watches, jewelry products
6. If it's an AUTOMOTIVE business → generate prompts for cars, workshop, mechanics
7. NEVER generate food images for non-food businesses
8. NEVER generate random/generic images - they must match the EXACT business
9. All prompts must be in ENGLISH for Stability AI
10. Each prompt should be detailed (20-50 words)
11. Include "professional photography" or "food photography" in each prompt
12. For food businesses: Describe the SPECIFIC dishes, not just "food" or "restaurant interior"

OUTPUT FORMAT (JSON only, no explanation):
{{
    "hero": "detailed prompt for hero/banner image",
    "image1": "detailed prompt for first product/service image",
    "image2": "detailed prompt for second product/service image",
    "image3": "detailed prompt for third product/service image",
    "image4": "detailed prompt for fourth product/service image"
}}

Generate prompts now:"""

        try:
            # Use DeepSeek to analyze and generate prompts
            api_key = os.getenv("DEEPSEEK_API_KEY")

            if not api_key:
                logger.warning("🧠 No DEEPSEEK_API_KEY, using fallback prompts")
                return self._get_fallback_prompts(description)

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "https://api.deepseek.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.deepseek_model,
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": 1000,
                        "temperature": 0.3
                    }
                )

                if response.status_code == 200:
                    data = response.json()
                    content = data["choices"][0]["message"]["content"]

                    # Parse JSON from response - extract JSON from response
                    json_match = re.search(r'\{[\s\S]*\}', content)
                    if json_match:
                        prompts = json.loads(json_match.group())
                        logger.info(f"🧠 AI Generated prompts for: {description[:50]}")
                        logger.info(f"🧠 Hero: {prompts.get('hero', '')[:50]}...")
                        return prompts
                else:
                    logger.error(f"🧠 DeepSeek API failed: {response.status_code}")

        except Exception as e:
            logger.error(f"🧠 Smart prompt generation failed: {e}")

        # Fallback - use specific prompts based on business type
        return self._get_fallback_prompts(description)

    def _is_food_business(self, description: str) -> bool:
        """True if the description looks like a food / restaurant business."""
        desc_lower = description.lower()
        return any(word in desc_lower for word in [
            'nasi', 'mee', 'ayam', 'ikan', 'restoran', 'restaurant',
            'kedai makan', 'warung', 'mamak', 'kandar', 'lemak', 'goreng',
            'makanan', 'cafe', 'kafe', 'seafood', 'udang', 'ketam', 'sotong',
            'food', 'masakan', 'catering', 'bakery', 'roti', 'kuih',
        ])

    def _fallback_item_names(self, description: str, n: int) -> list:
        """Deterministic item-name fallback for when AI extraction fails.

        Never raises; always returns exactly n non-empty, de-duplicated names.
        Prefers real dishes named in the description, then pads with sensible
        generic Malaysian dishes so a DeepSeek outage can never blank the
        gallery (requirement: graceful degradation).
        """
        found = [d for d in self._extract_menu_items(description)
                 if d and d != "hero image"]
        generic = ["Nasi Lemak", "Ayam Goreng", "Mee Goreng", "Roti Canai",
                   "Teh Tarik", "Nasi Goreng"]
        names = []
        for src_list in (found, generic):
            for name in src_list:
                title = str(name).strip().title()
                if title and title not in names:
                    names.append(title)
                if len(names) >= n:
                    break
            if len(names) >= n:
                break
        i = 1
        while len(names) < n:
            names.append(f"Menu {i}")
            i += 1
        return names[:n]

    # Possessive / promo filler tokens that leak into extracted item names but
    # don't change the dish/product identity. Stripped whole-word before dedup
    # so "Nasi Kandar Saya" / "Saya Nasi Kandar" collapse onto "Nasi Kandar"
    # ("saya" = Malay "my"). Conservative set — only words that are never a
    # dish identity on their own.
    _NAME_FILLER_TOKENS = frozenset({
        "saya", "kami", "kita", "anda", "aku",
        "my", "our", "your", "the",
        "special", "istimewa", "original", "asli", "premium", "signature",
    })
    # Floor for how many gallery cards we render. If semantic dedup leaves fewer
    # than this, we top up to the floor with DISTINCT generics; if it leaves more
    # (>= floor) we keep all the real items up to n. Never pad with near-dupes.
    _MIN_GALLERY_ITEMS = 3

    @staticmethod
    def _strip_name_punct(token: str) -> str:
        return token.strip(".,;:!?\"'()[]")

    def _clean_item_name(self, name: str, business_name: str = "") -> Tuple[str, frozenset]:
        """Strip business-name + possessive/promo noise from one item name.

        Returns (display_name, key_tokens):
          - display_name keeps the original casing of the surviving tokens.
          - key_tokens is a frozenset of the significant lowercased tokens, used
            for semantic dedup.
        The business name is removed only as a CONTIGUOUS prefix/suffix phrase
        (never token-by-token) so a business literally named after its dish
        (e.g. "Nasi Kandar Saya") can't nuke the dish words. If cleaning would
        empty the name, the original is kept.
        """
        raw = (name or "").strip()
        if not raw:
            return "", frozenset()
        tokens = raw.split()
        low = [self._strip_name_punct(t.lower()) for t in tokens]

        # Business-name phrase strip at prefix/suffix only (whole sequence).
        btoks = [self._strip_name_punct(t) for t in (business_name or "").lower().split()]
        btoks = [t for t in btoks if t]
        if btoks and len(low) > len(btoks):
            if low[:len(btoks)] == btoks:
                tokens, low = tokens[len(btoks):], low[len(btoks):]
            elif low[-len(btoks):] == btoks:
                tokens, low = tokens[:-len(btoks)], low[:-len(btoks)]

        # Filler strip (whole-word), but never strip ALL tokens away.
        kept = [(t, lw) for t, lw in zip(tokens, low) if lw and lw not in self._NAME_FILLER_TOKENS]
        if not kept:
            kept = [(t, self._strip_name_punct(t.lower())) for t in raw.split()]

        display = " ".join(t for t, _ in kept).strip()
        key = frozenset(lw for _, lw in kept if lw)
        if not key:
            return raw, frozenset({raw.lower()})
        return display, key

    @staticmethod
    def _keys_similar(k1: frozenset, k2: frozenset) -> bool:
        """Two item-name token sets are 'the same item' if equal, one is a
        subset of the other (e.g. "nasi kandar" ⊂ "nasi kandar penang"), or
        they're a near-typo match (SequenceMatcher ≥ 0.85)."""
        if not k1 or not k2:
            return k1 == k2
        if k1 == k2 or k1 <= k2 or k2 <= k1:
            return True
        return SequenceMatcher(None, " ".join(sorted(k1)), " ".join(sorted(k2))).ratio() >= 0.85

    def _dedupe_item_names(self, names: list, business_name: str = "") -> list:
        """Clean + semantically de-duplicate extracted item names.

        Strips business-name/possessive noise from each name, then collapses
        names that refer to the same item (subset or near-match), keeping the
        cleanest representative (fewest tokens, then shortest). Returns the
        unique display names in first-seen order. Does NOT pad — the caller
        decides how to fill up to the floor.
        """
        groups: list = []  # each: [key_tokens, display_name]
        for nm in names:
            display, key = self._clean_item_name(nm, business_name)
            if not display:
                continue
            hit = None
            for g in groups:
                if self._keys_similar(key, g[0]):
                    hit = g
                    break
            if hit is None:
                groups.append([key, display])
            elif (len(key) < len(hit[0])) or (len(key) == len(hit[0]) and len(display) < len(hit[1])):
                # Prefer the cleaner representative of the group.
                hit[0], hit[1] = key, display
        return [display for _, display in groups]

    def _finalize_item_names(
        self, unique: list, fallback_names: list, business_name: str, n: int
    ) -> list:
        """Cap the unique real items at n, then top up to the floor (3) with
        DISTINCT generics only. Floor, not ceiling: if unique already has >=
        floor items we keep them all (up to n) and add nothing."""
        floor = min(self._MIN_GALLERY_ITEMS, n)
        out = list(unique[:n])
        keys = [self._clean_item_name(x, business_name)[1] for x in out]
        if len(out) < floor:
            for extra in fallback_names:
                ed, ek = self._clean_item_name(extra, business_name)
                if not ed or any(self._keys_similar(ek, k) for k in keys):
                    continue
                out.append(ed)
                keys.append(ek)
                if len(out) >= floor:
                    break
        return out

    async def extract_menu_item_names(self, description: str, n: int = 4, business_name: str = "") -> list:
        """Extract EXACTLY n concise menu/dish names from the description.

        One DeepSeek call. Degrades gracefully on missing key, API failure
        (e.g. 402 Insufficient Balance), timeout, parse error, or bad count ->
        falls back to _fallback_item_names() and never raises.
        """
        api_key = os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            logger.warning("🍽️ No DEEPSEEK_API_KEY - using fallback item names")
            return self._fallback_item_names(description, n)

        biz_line = f"\nBUSINESS NAME (never include this, or any part of it, in an item name): {business_name}\n" if business_name else ""
        prompt = f"""From the business description below, list EXACTLY {n} menu/dish item names.

BUSINESS DESCRIPTION:
{description}
{biz_line}
STRICT RULES:
1. Output ONLY real, orderable menu items (specific dishes/drinks/products).
2. Each name must be concise - 1 to 4 words, the dish name itself.
3. DO NOT include ambience/interior/atmosphere entries (e.g. "Suasana Kedai",
   "Restaurant Interior", "Shop Ambience", "Dining Area"). Items only.
4. DO NOT append the business name, branch, address, city, location, or
   possessives like "saya"/"kami" to any name (e.g. NOT "Ikan Bakar Damansara",
   NOT "Nasi Kandar Saya" - just "Ikan Bakar", "Nasi Kandar").
5. Use the language of the description (Bahasa Malaysia or English).
6. If the description names specific dishes, use those exact dishes.

OUTPUT FORMAT - a JSON array of exactly {n} strings, nothing else:
["Name 1", "Name 2", "Name 3", "Name 4"]"""

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "https://api.deepseek.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.deepseek_model,
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": 300,
                        "temperature": 0.2,
                    },
                )
            if response.status_code != 200:
                logger.error(f"🍽️ Item-name extraction failed: {response.status_code} - using fallback")
                return self._fallback_item_names(description, n)

            content = response.json()["choices"][0]["message"]["content"]
            match = re.search(r'\[[\s\S]*\]', content)
            if not match:
                logger.error("🍽️ Item-name extraction returned no JSON array - using fallback")
                return self._fallback_item_names(description, n)

            raw = json.loads(match.group())
            banned = ["suasana", "interior", "ambience", "ambiance",
                      "dining area", "exterior", "storefront", "atmosphere"]
            names = []
            for item in raw:
                name = str(item).strip()
                low = name.lower()
                if not name or any(b in low for b in banned):
                    continue  # requirement: forbid ambience/interior cards
                names.append(name)

            # Strip business-name/possessive/location noise and collapse
            # semantically-similar names (the "Nasi Kandar / Saya Nasi Kandar /
            # Nasi Kandar Penang" → one dish fix). Then floor-to-3 top-up with
            # DISTINCT generics — never pad with near-dupes that collapse to the
            # same image.
            unique = self._dedupe_item_names(names, business_name)
            result = self._finalize_item_names(
                unique, self._fallback_item_names(description, n), business_name, n
            )
            return result if result else self._fallback_item_names(description, n)
        except Exception as e:
            logger.error(f"🍽️ Item-name extraction error: {e} - using fallback")
            return self._fallback_item_names(description, n)

    def _fallback_category_names(self, description: str, n: int) -> list:
        """Deterministic product-category fallback for the NON-food path.

        Non-food sibling of _fallback_item_names. Never raises; always returns
        exactly n non-empty, de-duplicated, banned-word-free category names so a
        DeepSeek outage (e.g. 402 Insufficient Balance) can never blank the
        gallery. Generic Malay retail categories that read sensibly for any
        shop/service business.
        """
        generic = ["Produk Pilihan", "Koleksi Terbaru", "Tawaran Istimewa",
                   "Barangan Popular", "Jualan Hangat", "Pilihan Utama"]
        names = []
        for name in generic:
            if name not in names:
                names.append(name)
            if len(names) >= n:
                break
        i = 1
        while len(names) < n:
            names.append(f"Produk {i}")
            i += 1
        return names[:n]

    async def extract_product_category_names(self, description: str, n: int = 4, business_name: str = "") -> list:
        """Extract EXACTLY n concise product/category names for NON-food shops.

        Non-food sibling of extract_menu_item_names. One DeepSeek call. Degrades
        gracefully on missing key, API failure (e.g. 402 Insufficient Balance),
        timeout, parse error, or bad count -> falls back to
        _fallback_category_names() and never raises. Applies the same
        banned-word filter as the food path so ambience/interior/storefront
        shots never become product cards.
        """
        api_key = os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            logger.warning("🛍️ No DEEPSEEK_API_KEY - using fallback category names")
            return self._fallback_category_names(description, n)

        biz_line = f"\nBUSINESS NAME (never include this, or any part of it, in a product name): {business_name}\n" if business_name else ""
        prompt = f"""From the business description below, list EXACTLY {n} concise product/category names sold by this business.

BUSINESS DESCRIPTION:
{description}
{biz_line}
STRICT RULES:
1. Output ONLY real product types/categories this business sells (e.g. for a toy shop: "Mainan Edukatif", "Blok Binaan", "Mainan Lembut", "Permainan Papan").
2. Each name must be concise - 1 to 4 words, the product/category itself.
3. DO NOT include ambience/interior/atmosphere/storefront entries (e.g. "Suasana Kedai", "Shop Interior", "Storefront", "Dining Area"). Products only.
4. DO NOT append the business name, branch, address, city, location, or possessives like "saya"/"kami" to any name.
5. Use the language of the description (Bahasa Malaysia or English).
6. If the description names specific products, use those exact products.

OUTPUT FORMAT - a JSON array of exactly {n} strings, nothing else:
["Name 1", "Name 2", "Name 3", "Name 4"]"""

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "https://api.deepseek.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.deepseek_model,
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": 300,
                        "temperature": 0.2,
                    },
                )
            if response.status_code != 200:
                logger.error(f"🛍️ Category-name extraction failed: {response.status_code} - using fallback")
                return self._fallback_category_names(description, n)

            content = response.json()["choices"][0]["message"]["content"]
            match = re.search(r'\[[\s\S]*\]', content)
            if not match:
                logger.error("🛍️ Category-name extraction returned no JSON array - using fallback")
                return self._fallback_category_names(description, n)

            raw = json.loads(match.group())
            banned = ["suasana", "interior", "ambience", "ambiance",
                      "dining area", "exterior", "storefront", "atmosphere"]
            names = []
            for item in raw:
                name = str(item).strip()
                low = name.lower()
                if not name or any(b in low for b in banned):
                    continue  # requirement: forbid ambience/interior cards
                names.append(name)

            # Same strip + semantic-dedup + floor-to-3 top-up as the food path.
            unique = self._dedupe_item_names(names, business_name)
            result = self._finalize_item_names(
                unique, self._fallback_category_names(description, n), business_name, n
            )
            return result if result else self._fallback_category_names(description, n)
        except Exception as e:
            logger.error(f"🛍️ Category-name extraction error: {e} - using fallback")
            return self._fallback_category_names(description, n)

    def _get_malaysian_food_prompts(self, description: str) -> dict:
        """Generate Malaysian food-specific prompts using MALAYSIAN_FOOD_PROMPTS database"""
        desc_lower = description.lower()

        # Find specific Malaysian dishes mentioned in description
        dishes_found = []
        for dish_name, prompt in self.MALAYSIAN_FOOD_PROMPTS.items():
            if dish_name in desc_lower:
                dishes_found.append((dish_name, prompt))

        # Use whatever specific dishes were found, then pad remaining slots with
        # sensible defaults. (Previously this required >=4 EXACT matches or it
        # dumped ALL slots to generic nasi kandar/lemak/mee goreng/roti canai -
        # which is why e.g. a seafood menu got unrelated images.)
        default_prompts = [
            self.MALAYSIAN_FOOD_PROMPTS["nasi kandar"],
            self.MALAYSIAN_FOOD_PROMPTS["nasi lemak"],
            self.MALAYSIAN_FOOD_PROMPTS["mee goreng"],
            self.MALAYSIAN_FOOD_PROMPTS["roti canai"],
        ]
        chosen = [p for _, p in dishes_found]
        for d in default_prompts:
            if len(chosen) >= 4:
                break
            if d not in chosen:
                chosen.append(d)
        chosen = (chosen + default_prompts)[:4]
        logger.info(f"🍽️ Food prompts: {len(dishes_found)} specific dish(es) matched, padded to 4")
        return {
            "hero": "Malaysian restaurant interior, food stall with hanging menu, authentic atmosphere, people eating, warm lighting, food photography",
            "image1": chosen[0] + ", professional food photography, high quality, appetizing",
            "image2": chosen[1] + ", professional food photography, high quality, delicious",
            "image3": chosen[2] + ", professional food photography, high quality, authentic",
            "image4": chosen[3] + ", professional food photography, high quality, traditional",
        }

    def _get_fallback_prompts(self, description: str) -> dict:
        """Generate fallback prompts when AI fails"""
        desc_lower = description.lower()

        # Check if it's a Malaysian food business
        if any(word in desc_lower for word in ['nasi', 'mee', 'ayam', 'ikan', 'restoran', 'restaurant', 'kedai makan', 'warung', 'mamak']):
            return self._get_malaysian_food_prompts(description)

        # Check for other business types
        if any(word in desc_lower for word in ['salon', 'rambut', 'hair', 'beauty', 'kecantikan']):
            return {
                "hero": "Modern hair salon interior, styling chairs, mirrors, professional lighting, commercial photography",
                "image1": "Professional haircut service, stylist cutting hair, modern salon, beauty photography",
                "image2": "Hair coloring treatment, professional hair color application, salon interior, beauty photography",
                "image3": "Hair treatment service, professional hair spa, relaxing atmosphere, beauty photography",
                "image4": "Hair styling service, blow dry, professional salon, beauty photography"
            }

        if any(word in desc_lower for word in ['baju', 'pakaian', 'fashion', 'clothing', 'boutique', 'tudung']):
            return {
                "hero": "Modern fashion boutique interior, clothing displays, elegant atmosphere, commercial photography",
                "image1": "Traditional baju kurung display, elegant Malaysian clothing, product photography, boutique setting",
                "image2": "Hijab and tudung collection, colorful scarves, product photography, elegant display",
                "image3": "Fashion accessories display, jewelry and brooches, product photography, luxury presentation",
                "image4": "Clothing boutique interior, modern retail space, professional photography"
            }

        # Generic business fallback
        desc_short = description[:50]
        return {
            "hero": f"Professional business establishment for {desc_short}, modern interior, welcoming atmosphere, commercial photography",
            "image1": f"Professional service showcase for {desc_short}, high quality, commercial photography",
            "image2": f"Business products and services, {desc_short}, professional setting, product photography",
            "image3": f"Customer experience at business, {desc_short}, professional photography",
            "image4": f"Quality service delivery, {desc_short}, commercial photography"
        }

    async def _improve_with_qwen(self, html: str, description: str) -> str:
        """Use Qwen to improve content while preserving design elements"""
        prompt = (
            "Improve the copywriting in this HTML for a Malaysian business.\n"
            "STRICT RULES:\n"
            "- Do NOT add new facts (no invented addresses, phone numbers, awards, years, prices, or claims).\n"
            "- Do NOT change any links (especially WhatsApp wa.me links).\n"
            "- Keep all image URLs unchanged.\n"
            "- Keep the language consistent with the existing page (if it's Bahasa Malaysia, keep it fully Bahasa Malaysia; do NOT introduce English headings).\n"
            "- Only improve wording/clarity while preserving meaning.\n"
            "- Do NOT remove or modify any <script> tags (especially tailwind.config).\n"
            "- Do NOT remove or modify any data-aos attributes.\n"
            "- Do NOT remove or modify any <link> tags in <head> (Google Fonts, AOS CSS, Font Awesome).\n"
            "- Do NOT change any CSS classes, Tailwind utility classes, or inline styles.\n"
            "- Do NOT change any CSS custom properties (--bg-color, --surface-color, etc.).\n"
            "- ONLY improve the visible TEXT content (headings, paragraphs, descriptions, button labels).\n\n"
            f"{html}"
        )
        try:
            improved = await self._call_qwen(prompt, temperature=0.7)
            if improved:
                return improved
            logger.warning("🟡 Qwen copywriting returned None — falling back to original HTML")
            return html
        except Exception as e:
            logger.warning(f"🟡 Qwen copywriting failed ({e}) — falling back to original HTML")
            return html

    async def _improve_css_with_qwen(self, html: str, description: str) -> str:
        """Use Qwen to refine ONLY the CSS/visual styling of a finished page.

        Sibling to _improve_with_qwen, but with the inverse invariant: the copy
        pass freezes styling and edits text; this pass freezes text/structure
        and edits styling. Qwen sees the real, finished selectors so it can make
        targeted visual improvements (spacing rhythm, type scale, colour
        restraint, shadow depth, hierarchy) rather than a from-scratch CSS split.

        Returns the SAME object on any internal None/error so the caller's
        identity check (`refined is original`) reads as "skipped". The caller is
        responsible for the truncation/length/structure gates before publishing.
        """
        prompt = (
            "Improve ONLY the visual styling of this finished HTML page for a Malaysian business.\n"
            "You MAY edit: CSS inside <style>, inline style=\"\" values, Tailwind utility class\n"
            "lists, the tailwind.config <script>, and CSS custom properties (--bg-color, etc.).\n"
            "Improve: spacing/whitespace rhythm, type scale, colour restraint, shadow depth,\n"
            "visual hierarchy, and alignment. Aim for a calmer, more professional look.\n\n"
            "STRICT RULES — return the SAME page, identical except styling:\n"
            "- Do NOT add, remove, reorder, or rename any HTML element, class NAME, or id.\n"
            "- Do NOT change any visible TEXT, heading, label, or any attribute other than class/style.\n"
            "- Do NOT modify, remove, or reorder any <script> logic (especially tailwind.config and any JS).\n"
            "- Do NOT change any data-aos attributes.\n"
            "- Do NOT remove or modify any <link> tags in <head> (Google Fonts, AOS CSS, Font Awesome).\n"
            "- Do NOT change any src or href value (image URLs, WhatsApp wa.me links) — keep them byte-identical.\n"
            "- Do NOT drop any section. Output the COMPLETE page from <!DOCTYPE html> to </html>.\n"
            "- Editing which Tailwind utilities apply is allowed, but every author-defined class name\n"
            "  that a <style> rule or the JS references MUST still be present on its element.\n"
            "Output ONLY HTML.\n\n"
            f"{html}"
        )
        try:
            improved = await self._call_qwen(
                prompt,
                temperature=0.4,
                max_tokens=self.QWEN_HTML_MAX_TOKENS,
            )
            if improved:
                return improved
            logger.warning("🎨 Qwen CSS refine returned None — falling back to original HTML")
            return html
        except Exception as e:
            logger.warning(f"🎨 Qwen CSS refine failed ({e}) — falling back to original HTML")
            return html

    @staticmethod
    def _hooked_selectors(html: str) -> frozenset:
        """Class names that a <style> rule or the page JS *references*.

        These are the names whose disappearance from the markup causes the
        "unstyled section" failure mode. We collect references from:
          - class selectors used in any <style> block (.foo, .foo:hover, .a.b)
          - names referenced by JS via querySelector(All) / classList /
            getElementsByClassName.
        Note this reads what the CSS/JS *asks for*, not what the markup carries
        — the caller intersects this with the classes actually applied on
        elements so that stripping a class off an element is detectable.
        Conservative by construction: anything we cannot confidently parse is
        simply not added (so it cannot trigger a false "structure changed").
        """
        names: set = set()

        # Class selectors inside <style> blocks. We deliberately ignore the
        # cascade/combinators and just harvest every `.name` token.
        for style_block in re.findall(r"<style[^>]*>(.*?)</style>", html, re.S | re.I):
            for m in re.findall(r"\.(-?[_a-zA-Z][_a-zA-Z0-9-]*)", style_block):
                names.add(m)

        # JS hooks. Scan all <script> blocks for the common DOM lookups.
        for script_block in re.findall(r"<script[^>]*>(.*?)</script>", html, re.S | re.I):
            # querySelector('.x' or '#x') / querySelectorAll(...)
            for q in re.findall(r"""querySelector(?:All)?\(\s*['"]([^'"]+)['"]""", script_block):
                for m in re.findall(r"\.(-?[_a-zA-Z][_a-zA-Z0-9-]*)", q):
                    names.add(m)
            # classList.add/remove/toggle/contains('x'), getElementsByClassName('x')
            for m in re.findall(
                r"""(?:classList\.(?:add|remove|toggle|contains|replace)|getElementsByClassName)\(\s*['"]([^'"]+)['"]""",
                script_block,
            ):
                for token in m.split():
                    names.add(token)

        return frozenset(names)

    @staticmethod
    def _applied_class_tokens(html: str) -> frozenset:
        """Every class token actually applied via a class="..." attribute."""
        tokens: set = set()
        for attr in re.findall(r'\bclass\s*=\s*"([^"]*)"', html, re.I):
            tokens.update(attr.split())
        return frozenset(tokens)

    def _structure_signature(self, html: str) -> dict:
        """Deterministic structural fingerprint for before/after equivalence.

        Invariant under any pure-styling edit (Tailwind utility churn, CSS rule
        changes, custom-property tweaks) but breaks the instant real structure
        is touched. Compared by the CSS-refine gate: any mismatch ⇒ discard
        Qwen's version and keep the prior HTML.
        """
        return {
            # Tag histogram — catches added/dropped/duplicated elements.
            "tag_counts": Counter(
                t.lower() for t in re.findall(r"<\s*([a-zA-Z][a-zA-Z0-9]*)", html)
            ),
            # id set — JS hooks and in-page anchor targets must be preserved.
            "ids": frozenset(re.findall(r'\bid\s*=\s*"([^"]+)"', html)),
            # Ordered img src sequence — defense-in-depth on image binding.
            "img_srcs": tuple(re.findall(r'<img[^>]+src\s*=\s*"([^"]*)"', html, re.I)),
            # href set — WhatsApp wa.me links and nav anchors must be preserved.
            "hrefs": frozenset(re.findall(r'\bhref\s*=\s*"([^"]*)"', html)),
            # Hooked classes still PRESENT on the markup: the intersection of
            # names a <style> rule / the JS references with the class tokens
            # actually applied to elements. Tailwind utility churn doesn't move
            # this (utilities aren't hooked), but stripping a hooked class off
            # an element — the unstyled-section mode — shrinks it and trips the
            # gate.
            "hooked_present": self._hooked_selectors(html) & self._applied_class_tokens(html),
        }

    def get_fallback_images(self, description: str) -> Dict:
        """Get fallback stock images using comprehensive image matching"""
        d = description.lower()

        # Use get_matching_image for smart image selection
        hero_img = self.get_matching_image(description, business_type=description)

        # Generate gallery images based on description keywords
        gallery_images = []

        # Extract key products/services from description
        # Split into words and try to match each phrase
        words = d.split()

        # Try to find specific products/services mentioned
        for i in range(len(words)):
            if len(gallery_images) >= 4:
                break
            for j in range(min(i + 3, len(words)), i, -1):  # Check up to 3-word phrases
                phrase = " ".join(words[i:j])
                if len(phrase) >= 3:  # Skip very short words
                    img = self.get_matching_image(phrase, business_type=description)
                    if img not in gallery_images and img != self.BUSINESS_IMAGES["default"]:
                        gallery_images.append(img)
                        break

        # If we didn't find enough specific images, add category-based defaults
        if len(gallery_images) < 4:
            # Detect business type and add relevant category images
            if any(w in d for w in ['baju', 'tudung', 'fashion', 'pakaian']):
                fallback_imgs = [
                    self.BUSINESS_IMAGES.get("baju kurung", self.BUSINESS_IMAGES["clothing"]),
                    self.BUSINESS_IMAGES.get("tudung", self.BUSINESS_IMAGES["clothing"]),
                    self.BUSINESS_IMAGES.get("kebaya", self.BUSINESS_IMAGES["clothing"]),
                    self.BUSINESS_IMAGES.get("accessories", self.BUSINESS_IMAGES["clothing"])
                ]
            elif any(w in d for w in ['salon', 'rambut', 'hair']):
                fallback_imgs = [
                    self.BUSINESS_IMAGES.get("haircut", self.BUSINESS_IMAGES["salon"]),
                    self.BUSINESS_IMAGES.get("hair coloring", self.BUSINESS_IMAGES["salon"]),
                    self.BUSINESS_IMAGES.get("hair treatment", self.BUSINESS_IMAGES["salon"]),
                    self.BUSINESS_IMAGES.get("hair styling", self.BUSINESS_IMAGES["salon"])
                ]
            elif any(w in d for w in ['beauty', 'kecantikan', 'spa']):
                fallback_imgs = [
                    self.BUSINESS_IMAGES.get("facial", self.BUSINESS_IMAGES["beauty"]),
                    self.BUSINESS_IMAGES.get("massage", self.BUSINESS_IMAGES["spa"]),
                    self.BUSINESS_IMAGES.get("manicure", self.BUSINESS_IMAGES["beauty"]),
                    self.BUSINESS_IMAGES.get("makeup", self.BUSINESS_IMAGES["beauty"])
                ]
            elif any(w in d for w in ['kereta', 'car', 'bengkel', 'automotive']):
                fallback_imgs = [
                    self.BUSINESS_IMAGES.get("car wash", self.BUSINESS_IMAGES["car"]),
                    self.BUSINESS_IMAGES.get("bengkel", self.BUSINESS_IMAGES["car"]),
                    self.BUSINESS_IMAGES.get("car service", self.BUSINESS_IMAGES["car"]),
                    self.BUSINESS_IMAGES.get("tire service", self.BUSINESS_IMAGES["car"])
                ]
            elif any(w in d for w in ['nasi', 'makan', 'restoran', 'food']):
                fallback_imgs = [
                    self.FOOD_IMAGES.get("nasi lemak", self.FOOD_IMAGES["default"]),
                    self.FOOD_IMAGES.get("nasi kandar", self.FOOD_IMAGES["default"]),
                    self.FOOD_IMAGES.get("mee goreng", self.FOOD_IMAGES["default"]),
                    self.FOOD_IMAGES.get("roti canai", self.FOOD_IMAGES["default"])
                ]
            else:
                # Use existing IMAGES dict for other types
                biz_type = self._detect_type(description)
                imgs = self.IMAGES.get(biz_type, self.IMAGES["default"])
                fallback_imgs = imgs["gallery"]

            # Add fallback images that aren't already in the list
            for img in fallback_imgs:
                if img not in gallery_images:
                    gallery_images.append(img)
                if len(gallery_images) >= 4:
                    break

        # Ensure we have exactly 4 gallery images
        while len(gallery_images) < 4:
            gallery_images.append(self.BUSINESS_IMAGES["default"])

        return {
            "hero": hero_img,
            "gallery": gallery_images[:4]
        }

    # HARDCODED WORKING IMAGES - Guaranteed to work
    IMAGES = {
        "pet_shop": {
            "hero": "https://images.unsplash.com/photo-1514888286974-6c03e2ca1dba?w=1920&q=80",
            "gallery": [
                "https://images.unsplash.com/photo-1573865526739-10659fec78a5?w=800&q=80",
                "https://images.unsplash.com/photo-1495360010541-f48722b34f7d?w=800&q=80",
                "https://images.unsplash.com/photo-1518791841217-8f162f1e1131?w=800&q=80",
                "https://images.unsplash.com/photo-1574158622682-e40e69881006?w=800&q=80"
            ]
        },
        "salon": {
            "hero": "https://images.unsplash.com/photo-1560066984-138dadb4c035?w=1920&q=80",
            "gallery": [
                "https://images.unsplash.com/photo-1522337360788-8b13dee7a37e?w=800&q=80",
                "https://images.unsplash.com/photo-1559599101-f09722fb4948?w=800&q=80",
                "https://images.unsplash.com/photo-1521590832167-7bcbfaa6381f?w=800&q=80",
                "https://images.unsplash.com/photo-1562322140-8baeececf3df?w=800&q=80"
            ]
        },
        "restaurant": {
            "hero": "https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?w=1920&q=80",
            "gallery": [
                "https://images.unsplash.com/photo-1504674900247-0877df9cc836?w=800&q=80",
                "https://images.unsplash.com/photo-1555939594-58d7cb561ad1?w=800&q=80",
                "https://images.unsplash.com/photo-1565299624946-b28f40a0ae38?w=800&q=80",
                "https://images.unsplash.com/photo-1476224203421-9ac39bcb3327?w=800&q=80"
            ]
        },
        "clothing": {
            "hero": "https://images.unsplash.com/photo-1441986300917-64674bd600d8?w=1920&q=80",
            "gallery": [
                "https://images.unsplash.com/photo-1489987707025-afc232f7ea0f?w=800&q=80",
                "https://images.unsplash.com/photo-1558171813-4c088753af8f?w=800&q=80",
                "https://images.unsplash.com/photo-1467043237213-65f2da53396f?w=800&q=80",
                "https://images.unsplash.com/photo-1525507119028-ed4c629a60a3?w=800&q=80"
            ]
        },
        "photography": {
            "hero": "https://images.unsplash.com/photo-1542038784456-1ea8e935640e?w=1920&q=80",
            "gallery": [
                "https://images.unsplash.com/photo-1513364776144-60967b0f800f?w=800&q=80",
                "https://images.unsplash.com/photo-1460925895917-afdab827c52f?w=800&q=80",
                "https://images.unsplash.com/photo-1598488035139-bdbb2231ce04?w=800&q=80",
                "https://images.unsplash.com/photo-1554048612-b6a482bc67e5?w=800&q=80"
            ]
        },
        "default": {
            "hero": "https://images.unsplash.com/photo-1497366216548-37526070297c?w=1920&q=80",
            "gallery": [
                "https://images.unsplash.com/photo-1460925895917-afdab827c52f?w=800&q=80",
                "https://images.unsplash.com/photo-1497215728101-856f4ea42174?w=800&q=80",
                "https://images.unsplash.com/photo-1542744173-8e7e53415bb0?w=800&q=80",
                "https://images.unsplash.com/photo-1521737711867-e3b97375f902?w=800&q=80"
            ]
        }
    }

    def _detect_type(self, desc: str) -> str:
        """Detect business type"""
        d = desc.lower()
        if any(w in d for w in ['kucing', 'cat', 'pet', 'haiwan', 'anjing', 'dog']):
            return "pet_shop"
        if any(w in d for w in ['salon', 'rambut', 'hair', 'haircut', 'beauty', 'spa', 'kecantikan', 'gunting']):
            return "salon"
        if any(w in d for w in ['makan', 'restoran', 'restaurant', 'food', 'nasi', 'cafe', 'kafe', 'warung']):
            return "restaurant"
        if any(w in d for w in ['pakaian', 'clothing', 'fashion', 'baju', 'boutique', 'fesyen', 'tudung', 'hijab']):
            return "clothing"
        if any(w in d for w in ['photo', 'foto', 'fotografi', 'photography', 'jurugambar', 'photographer', 'studio', 'gallery', 'galeri']):
            return "photography"
        return "default"

    def _build_strict_prompt(
        self,
        name: str,
        desc: str,
        style: str,
        user_images: list = None,
        language: str = "ms",
        whatsapp_number: Optional[str] = None,
        location_address: Optional[str] = None,
        image_choice: str = "upload",
        images: Optional[dict] = None,  # generated images: {hero, gallery1..4}
        include_ecommerce: bool = False,
        color_mode: str = "light",
        include_whatsapp: bool = True,
        include_maps: bool = False,
        include_contact_form: bool = True,
        include_chat: bool = True,
    ) -> str:
        """Build STRICT prompt with premium design system"""
        biz_type = self._detect_type(desc)
        imgs = self.IMAGES.get(biz_type, self.IMAGES["default"])

        # Detect business type and get design type
        try:
            detected_biz_type = detect_business_type(desc)
        except Exception:
            detected_biz_type = "general"

        design_type = get_design_type(detected_biz_type, desc)

        # Initialize design system
        try:
            design = DesignSystem()
            fonts = design.get_font_pairing(design_type)
            palette = design.get_color_palette(design_type, color_mode)
            layout = design.get_layout_template(design_type)
            hero_variant = design.get_hero_variant(design_type, has_images=(image_choice != "none"))
            animations = design.get_animation_config()
            tw_config = design.get_tailwind_config(design_type, color_mode)
            typography = design.get_typography_rules()
            design_patterns = design.get_design_patterns(color_mode)
        except Exception as e:
            logger.error(f"DesignSystem error: {e}")
            # Fallback to basic values
            fonts = {
                "cdn_link": (
                    '<link rel="preconnect" href="https://fonts.googleapis.com">\n'
                    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
                    '<link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@500;600;700;800'
                    '&family=Mulish:wght@400;500;600;700&display=swap" rel="stylesheet">'
                ),
                "heading": "Plus Jakarta Sans",
                "body": "Mulish",
                "heading_fallback": "system-ui, sans-serif",
                "body_fallback": "Helvetica Neue, sans-serif",
            }
            palette = {"primary": "#3b82f6", "secondary": "#1e40af", "accent": "#dbeafe", "background": "#ffffff", "surface": "#ffffff", "text": "#0f172a", "text_muted": "#64748b"}
            layout = ""
            hero_variant = ""
            animations = ""
            tw_config = ""
            typography = ""
            design_patterns = ""

        logger.info(f"🎨 Design: type={design_type}, mode={color_mode}, fonts={fonts.get('heading')}/{fonts.get('body')}")

        # ---- IMAGE HANDLING (unchanged logic) ----
        if image_choice == "none":
            logger.info("🚫 _build_strict_prompt: image_choice='none' - NO IMAGES MODE")
            hero = ""
            g1 = g2 = g3 = g4 = ""
        else:
            def get_url(img):
                if isinstance(img, dict):
                    return img.get('url', img.get('URL', ''))
                return str(img) if img else ''

            def get_name(img):
                if isinstance(img, dict):
                    return img.get('name', '')
                return ''

            # Image-slot precedence (lowest → highest):
            #   1. hardcoded self.IMAGES defaults (Unsplash placeholders)
            #   2. generated `images` dict from generate_website
            #      ({hero, gallery1..4} — real Cloudinary URLs OR _slot_image()
            #      pool fallbacks). This is the core fix: previously the body
            #      always used the Unsplash defaults, so the freshly generated
            #      gallery URLs never reached the model and only the hero (wired
            #      in separately below) survived.
            #   3. user-uploaded images (named "hero" → hero, rest → gallery)
            hero = imgs["hero"]
            g1, g2, g3, g4 = imgs["gallery"][0], imgs["gallery"][1], imgs["gallery"][2], imgs["gallery"][3]

            if images:
                if images.get("hero"):
                    hero = images["hero"]
                if images.get("gallery1"):
                    g1 = images["gallery1"]
                if images.get("gallery2"):
                    g2 = images["gallery2"]
                if images.get("gallery3"):
                    g3 = images["gallery3"]
                if images.get("gallery4"):
                    g4 = images["gallery4"]

            gallery_start_index = 0
            if user_images and len(user_images) > 0:
                first_img_name = get_name(user_images[0])
                if first_img_name == 'Hero Image' or 'hero' in first_img_name.lower():
                    hero = get_url(user_images[0])
                    gallery_start_index = 1
                # Uploaded images fill gallery slots in order; slots without an
                # upload keep whatever was resolved above (generated or default).
                if len(user_images) > gallery_start_index:
                    g1 = get_url(user_images[gallery_start_index])
                if len(user_images) > gallery_start_index + 1:
                    g2 = get_url(user_images[gallery_start_index + 1])
                if len(user_images) > gallery_start_index + 2:
                    g3 = get_url(user_images[gallery_start_index + 2])
                if len(user_images) > gallery_start_index + 3:
                    g4 = get_url(user_images[gallery_start_index + 3])

        # ---- LANGUAGE ----
        if language == "ms":
            language_instruction = """LANGUAGE - BAHASA MALAYSIA (WAJIB):
PENTING: Hasilkan SEMUA kandungan dalam BAHASA MELAYU sepenuhnya!
✅ Semua teks MESTI dalam Bahasa Melayu
✅ Gunakan: "Selamat Datang", "Tentang Kami", "Hubungi Kami", "Menu", "Perkhidmatan"
✅ Navigasi: "Laman Utama", "Menu", "Tentang", "Hubungi"
✅ Butang: "Pesan Sekarang", "Hubungi Kami", "Lihat Menu"
❌ JANGAN gunakan Bahasa Inggeris untuk kandungan
❌ JANGAN tulis tajuk/navigasi dalam English"""
        else:
            language_instruction = """LANGUAGE - ENGLISH:
Generate ALL content in English.
✅ Use: "Welcome", "About Us", "Contact Us", "Menu", "Services"
✅ Navigation: "Home", "Menu", "About", "Contact"
✅ Buttons: "Order Now", "Contact Us", "View Menu"
Keep all text consistent in English throughout."""

        # ---- WHATSAPP ----
        wa_raw = whatsapp_number or "60123456789"
        wa_digits = re.sub(r"\D", "", str(wa_raw))
        if wa_digits.startswith("0"):
            wa_digits = "6" + wa_digits
        elif wa_digits.startswith("1"):
            wa_digits = "60" + wa_digits
        if not wa_digits:
            wa_digits = "60123456789"

        # ---- WHATSAPP LINK RULES ----
        # Digits-only (no leading '+'): the '+' form fails to open on some
        # Android WhatsApp clients. For non-ecommerce sites, each menu/dish CTA
        # deep-links WhatsApp with the item name prefilled (higher conversion
        # than a generic #hubungi anchor). Ecommerce sites keep bare cards — a
        # separate ordering system is stitched on later.
        if language == "ms":
            _wa_prefill = "Assalamualaikum, saya nak pesan"
        else:
            _wa_prefill = "Hi, I would like to order"
        if include_ecommerce:
            wa_rules = f"""WHATSAPP LINKS:
- Use ONLY the digits-only form: https://wa.me/{wa_digits} (NO leading '+', no spaces or dashes).
- WhatsApp contact belongs ONLY in the footer/contact area. Do NOT add order buttons on menu/product cards."""
        else:
            wa_rules = f"""WHATSAPP LINKS:
- Use ONLY the digits-only form: https://wa.me/{wa_digits} (NO leading '+', no spaces or dashes). NEVER write wa.me/+... anywhere.
- EACH menu/dish/service card's CTA button (e.g. "Pesan", "Order") MUST deep-link WhatsApp with that item prefilled:
  https://wa.me/{wa_digits}?text=<URL-ENCODED "{_wa_prefill} DISH_NAME">
  Example for "Tomyam Campur": https://wa.me/{wa_digits}?text={_wa_prefill.replace(' ', '%20')}%20Tomyam%20Campur
- URL-encode the text (spaces as %20). Do NOT point dish CTAs at a bare #hubungi anchor."""

        # ---- ADDRESS ----
        address_line = ""
        if location_address and str(location_address).strip():
            address_line = f"✅ Address (use EXACTLY, do not invent): {str(location_address).strip()}"

        # ---- IMAGE INSTRUCTIONS ----
        if image_choice == "none":
            image_section = """IMAGE MODE: NO IMAGES
🚫 DO NOT include ANY <img> tags
🚫 DO NOT use background-image CSS with URLs
🚫 DO NOT use any image URLs (Unsplash, Cloudinary, Pexels, etc.)
✅ Use gradient backgrounds, Font Awesome icons, and text-only design
✅ Use colored placeholder divs with icons for cards: bg-gradient-to-br from-primary to-secondary with icon"""
        else:
            # Build the gallery pool from the REAL resolved images, not a fixed
            # set of four. Two bugs this prevents:
            #   1. A phantom 4th slot: when fewer than four images were generated
            #      /uploaded, the unfilled slots still held the hardcoded Unsplash
            #      fallback, which rendered as an extra (often blank) card.
            #   2. The same photo appearing twice across the page (service cards
            #      reused in the gallery/portfolio section).
            # When any real image exists we drop slots that still hold the
            # hardcoded default; only when NOTHING real was provided do we keep
            # the defaults (total image-generation failure fallback).
            _defaults = imgs["gallery"]
            _resolved = [g1, g2, g3, g4]
            _has_real = bool(images) or bool(user_images)
            if _has_real:
                _gallery_pool = [u for u, d in zip(_resolved, _defaults) if u and u != d]
                if not _gallery_pool:  # safety: real path but nothing matched
                    _gallery_pool = [u for u in _resolved if u]
            else:
                _gallery_pool = [u for u in _resolved if u]
            # De-duplicate by URL, preserving order, so a repeated URL can never
            # produce two cards.
            _seen = set()
            _gallery_urls = []
            for _u in _gallery_pool:
                if _u not in _seen:
                    _seen.add(_u)
                    _gallery_urls.append(_u)
            _n = len(_gallery_urls)
            _gallery_lines = "\n".join(
                f"- GALLERY IMAGE {_i}: {_u}" for _i, _u in enumerate(_gallery_urls, 1)
            )
            image_section = f"""IMAGE MODE: USE EXACT URLS
USE THESE EXACT IMAGE URLS (copy-paste exactly):
- HERO IMAGE: {hero}
{_gallery_lines}

RULES:
- Use ONLY the exact URLs provided above
- Do NOT modify the URLs or use other sources
- There are EXACTLY {_n} gallery image(s). Treat them as ONE shared image pool for the WHOLE page.
- Use each image AT MOST ONCE across the entire page. NEVER show the same photo in two places (e.g. a service card and the gallery/portfolio).
- Render EXACTLY {_n} image card(s) total. Do NOT pad with empty, placeholder, or duplicate cards.
- If a section (such as a portfolio/gallery) cannot be filled with UNUSED images, OMIT that section entirely rather than reusing a photo.
- Gallery/product card image areas: EVERY card MUST use the IDENTICAL size classes `w-full aspect-[4/3] object-cover` — never per-card pixel heights (no h-48/h-52/h-56/h-60/h-64/h-72) — so the grid stays perfectly even on mobile (375px) and desktop
- If you add a small category/label tag to gallery cards, each tag MUST be unique across the cards — never repeat the same label (e.g. two "Color" tags) unless there are genuinely more cards than distinct categories; otherwise omit the tag"""

        # ---- ECOMMERCE MODE ----
        ecommerce_section = ""
        if include_ecommerce:
            ecommerce_section = """DELIVERY MODE:
🛒 DO NOT add WhatsApp order buttons in menu/product cards
🛒 Menu items show product name, description, and price ONLY
🛒 A separate ordering system will be integrated later
✅ WhatsApp button is ONLY for contact/inquiries in footer section"""

        # ---- DARK MODE EXTRA RULES ----
        dark_mode_section = ""
        if color_mode == "dark":
            dark_mode_section = f"""
DARK MODE STYLING (CRITICAL):
- Page body background: {palette['background']}
- Card/surface backgrounds: {palette['surface']} with backdrop-blur
- Heading text: {palette['text']}
- Body text: {palette['text_muted']}
- Borders: {palette.get('border', 'rgba(255,255,255,0.1)')}
- Navigation: bg-[{palette['surface']}]/90 backdrop-blur-xl (NOT white!)
- Set CSS variables in <style>: --bg-color: {palette['background']}; --surface-color: {palette['surface']}; --text-color: {palette['text']}; --text-muted-color: {palette['text_muted']};"""
        else:
            dark_mode_section = f"""
LIGHT MODE STYLING:
- Page body background: {palette['background']} (NOT pure white #fff)
- Card backgrounds: {palette['surface']}
- Heading text: {palette['text']}
- Body text: {palette['text_muted']}
- Navigation: bg-white/90 backdrop-blur-xl shadow-sm
- Set CSS variables in <style>: --bg-color: {palette['background']}; --surface-color: {palette['surface']}; --text-color: {palette['text']}; --text-muted-color: {palette['text_muted']};"""

        # ---- STYLE-SPECIFIC ADDITIONS ----
        style_note = ""
        if style == "minimal":
            style_note = """STYLE NOTE - MINIMAL:
- Keep the design system colors but use them sparingly
- Focus on typography hierarchy, generous whitespace
- Cards: minimal shadows (shadow-sm), thin borders
- NO gradients on buttons, use solid primary color only"""
        elif style == "bold":
            style_note = """STYLE NOTE - BOLD:
- Make colors more saturated and vivid
- Use larger typography (increase heading sizes by one step)
- Stronger shadows: shadow-2xl
- Bolder buttons: px-10 py-4 text-lg font-bold uppercase tracking-wider"""

        # ---- WIDGET CONTEXT (E from spec — design AROUND injected widgets) ----
        # Tells the AI which floating/inline widgets will be stitched on
        # after generation, so it can leave room and emit optional slot
        # divs for inline ones (maps, contact form, pesanan).
        injected_widgets = widgets_for_request(
            include_whatsapp=include_whatsapp,
            include_maps=include_maps,
            include_ecommerce=include_ecommerce,
            include_contact=include_contact_form,
            include_chat=include_chat,
        )
        widget_context_block = build_prompt_context_block(
            injected_widgets,
            primary_color=palette.get("primary"),
        )

        # ---- ASSEMBLE PROMPT ----
        return f"""Generate a COMPLETE production-ready HTML website.

BUSINESS: {name}
DESCRIPTION: {desc}
STYLE: {style.upper()}
COLOR MODE: {color_mode.upper()}
TARGET LANGUAGE: {"BAHASA MALAYSIA" if language == "ms" else "ENGLISH"}

===== HEAD SECTION (MUST INCLUDE ALL) =====
{fonts['cdn_link']}
<link href="https://unpkg.com/aos@2.3.4/dist/aos.css" rel="stylesheet">
<script src="https://cdn.tailwindcss.com"></script>
{tw_config}
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
<style>
html {{ scroll-behavior: smooth; }}
:root {{ --bg-color: {palette['background']}; --surface-color: {palette['surface']}; --text-color: {palette['text']}; --text-muted-color: {palette['text_muted']}; }}
body {{ background-color: var(--bg-color); font-family: '{fonts['body']}', {fonts['body_fallback']}; }}
</style>

===== BEFORE </body> (MUST INCLUDE) =====
<script src="https://unpkg.com/aos@2.3.4/dist/aos.js"></script>
<script>AOS.init({{ duration: 800, once: true, offset: 100 }}); document.documentElement.classList.add('aos-initialized');</script>

===== DESIGN SYSTEM =====

===== ART DIRECTION (NON-NEGOTIABLE) =====
TYPE SCALE — use a clear modular scale, never ad-hoc sizes. Keep a strict hierarchy, at most these five steps:
- Display/hero: 48-72px (3rem-4.5rem), font-bold, tracking-tight, tight leading
- H2 section heading: 32-40px (2rem-2.5rem), font-bold
- H3 card/title: 20-24px (1.25rem-1.5rem), font-semibold
- Body: 16-18px (1rem-1.125rem), leading-relaxed
- Caption/meta: 13-14px, muted colour

COLOUR — ONE dominant colour + ONE accent only:
- Pick a single dominant brand colour for primary surfaces and CTAs.
- Use exactly one accent colour for small highlights (badges, links, details).
- Everything else stays neutral: background, surface, text, borders.
- Do NOT spread 3+ saturated colours across the page.
- FORBIDDEN: purple/violet text or fills on a white or near-white background (low contrast, generic SaaS look).

TYPOGRAPHY — fonts (FONT LOCK, non-negotiable):
- Do NOT use Inter or Roboto — they read as generic defaults.
- Use ONLY the heading/body fonts provided in the HEAD section above.
- Do NOT add any other <link> to fonts.googleapis.com — the only font <link> allowed is the one already in the HEAD section.
- NEVER write font-family: Inter, Roboto, or system-ui anywhere — not in <style>, not in the Tailwind config, not in inline styles, not in class names. The page's base font is already set; do not override it.

SPACING — strict 8px system:
- Every margin, padding and gap is a multiple of 8px (8 / 16 / 24 / 32 / 48 / 64 / 96).
- Generous, consistent section rhythm — never cramped.

DEPTH and SHADOWS:
- Create depth with layered soft shadows (shadow-lg / shadow-xl), subtle borders, and slight elevation on hover.
- Cards lift on hover. Avoid flat, borderless boxes that blend into the background.

CARDS MUST STAY READABLE EVEN IF AN IMAGE FAILS:
- Every card has its own solid surface background and padding. Never place text directly on an image without a background layer.
- If a card image fails to load, the card must remain legible — real text colour on the surface, never white text on a white background.
- Give every img a neutral background colour and a fixed aspect ratio so a missing image leaves a clean placeholder block instead of collapsed or overlapping layout.

ICONS — Font Awesome FREE 6.x ONLY (non-negotiable):
- Only the Font Awesome FREE stylesheet is loaded (6.4.0 all.min.css). Use ONLY free solid (fa-solid / fas) and free brand (fa-brands / fab) glyphs.
- NEVER use Pro-only or Pro-tier icons — they render as blank squares. Examples of FORBIDDEN Pro icons: fa-pot-food, fa-pan-frying, fa-plate-utensils, fa-burger-soda, fa-salad, fa-bowl-chopsticks. When unsure whether an icon is free, DO NOT use it.
- Safe free food/service glyphs to prefer: fa-utensils, fa-bowl-food, fa-bowl-rice, fa-mug-hot, fa-burger, fa-drumstick-bite, fa-fish, fa-pizza-slice, fa-ice-cream, fa-truck, fa-star, fa-location-dot, fa-phone, fa-clock, fa-heart.

BRAND / LOGO (non-negotiable):
- The logo and footer brand text MUST be the FULL business name exactly: "{name}".
- NEVER truncate the name to a single word or a fragment (e.g. do NOT render "kedai." for "Kedai Tomyam"). A styled dot or accent colour is allowed only AFTER the complete name.

FOOTER:
- Render the copyright year DYNAMICALLY, never a hardcoded year. Use:
  &copy; <script>document.write(new Date().getFullYear())</script> {name}

{typography}

{design_patterns}

{animations}

{dark_mode_section}

{style_note}

===== {layout} =====

===== {image_section} =====

{widget_context_block}

===== CONTENT RULES =====
ABSOLUTELY FORBIDDEN:
❌ via.placeholder.com, placeholder.com, example.com
❌ [PLACEHOLDER] or any [ ] brackets
❌ Any invented facts, phone numbers, addresses, awards

MUST WRITE REAL CONTENT:
✅ Real business name: {name}
✅ Real catchy tagline based on description
✅ Real about section (2-3 sentences)
✅ Real service names and descriptions (3-4 services)
✅ Real contact message
{"✅ WhatsApp contact ONLY in footer: https://wa.me/" + wa_digits if include_ecommerce else "✅ WhatsApp button: https://wa.me/" + wa_digits}
{address_line}
🚫 DO NOT invent phone numbers, addresses, cities, awards

{wa_rules}

{ecommerce_section}

===== {language_instruction} =====

TECHNICAL:
- Single complete HTML file
- Mobile responsive (critical!)
- Use font-heading for all headings, font-body for all body text
- Use the primary, secondary, accent, surface colors from tailwind.config

Generate ONLY the complete HTML code. No explanations. No markdown. Just pure HTML."""

    # System prompt for the GLM HTML call, structured as GOAL → HARD RULES →
    # FREEDOM: one objective, a short checkable rule list (every rule is
    # verifiable, none stylistic), then explicit creative freedom for
    # everything else. Assembled per-call: GOAL + rules 1-4 + ONE image rule
    # (rule 5) chosen by image availability (GLM is single-shot, so the
    # pipeline must tell it up front which world it's in) + rules 6-8 +
    # FREEDOM.
    _GLM_PROMPT_GOAL = (
        "GOAL: Produce a complete, production-ready, single-file HTML website "
        "for this Malaysian business that a paying merchant would be proud to "
        "publish.\n\n"
    )
    _GLM_PROMPT_RULES_HEAD = (
        "HARD RULES — every one must be satisfied:\n"
        "1. Output ONLY raw HTML starting with <!DOCTYPE html> — the first "
        "character of your reply is '<'. No preamble, no explanations, no "
        "markdown fences.\n"
        "2. Include at minimum these sections: hero, menu highlights (or "
        "services), about, location, and an order CTA. Always end the page "
        "with the order CTA. Never omit the required sections.\n"
        "3. All headings, taglines and menu/dish descriptions in natural "
        "Malaysian Malay/Manglish with local mamak/F&B terms, unless the "
        "business context is clearly English-market. Prices in RM. Warm "
        "local tone, not corporate English.\n"
        "4. Use ONLY the real business data provided in the prompt (name, "
        "address, phone, hours, menu items, prices). NEVER invent founder "
        "names, phone numbers, addresses, ratings, review counts, awards, or "
        "statistics that were not supplied. If a detail was not provided, "
        "omit that content rather than fabricate it.\n"
    )
    # Rule 5, images-available branch: the PHOTO_SLOT contract. GLM outputs
    # PHOTO_SLOT_N tokens which _replace_photo_slots() then binds to the real
    # Cloudinary/Stability URLs deterministically — same boundary where the
    # DeepSeek pipeline's exact-URL instructions get enforced.
    _GLM_PHOTO_SLOT_CLAUSE = (
        "5. For ALL images use exactly src='PHOTO_SLOT_1', "
        "src='PHOTO_SLOT_2', ... in order of appearance — never invent image "
        "URLs.\n"
    )
    # Rule 5, no-images branch: photo-less design mode. Without this,
    # PHOTO_SLOT tokens resolve to empty URLs and the image safety net paints
    # grey fallback blocks — a bare, broken-looking site. Deliberately avoids
    # the literal token name so the model never sees it in this mode.
    _GLM_NO_PHOTO_CLAUSE = (
        "5. No photographs are available for this site. Build a polished, "
        "typography-led design: use bold headings, color blocks, gradients, "
        "generous whitespace, icon accents, and strong layout to create "
        "visual interest. Do NOT use any <img> tags, do NOT use "
        "background-image: url(...) with photo URLs, and do NOT use any "
        "placeholder photo tokens. The page must look complete and "
        "intentional without any photographs — like a clean modern brand "
        "site.\n"
    )
    _GLM_PROMPT_RULES_TAIL = (
        "6. Mobile-first responsive: nothing may overflow horizontally on a "
        "375px-wide screen.\n"
        "7. Every navigation anchor must point to a section id that exists "
        "in the page.\n"
        "8. No external JS/CSS beyond what the prompt's HTML skeleton "
        "already loads (Tailwind CDN, AOS, Font Awesome, Google Fonts).\n\n"
    )
    _GLM_PROMPT_FREEDOM = (
        "FREEDOM: Everything not covered by the hard rules is yours — colour "
        "palette, typography pairing, layout patterns, section order (except "
        "the order CTA last), animations, section backgrounds, copy tone and "
        "personality — and you may add tasteful extra sections or design "
        "flourishes. Make the site feel individually designed, not "
        "templated. Surprise us — within the rules."
    )
    # Back-compat alias: the has-images composition (previous single-string form).
    _GLM_HTML_SYSTEM_PROMPT = (
        _GLM_PROMPT_GOAL
        + _GLM_PROMPT_RULES_HEAD
        + _GLM_PHOTO_SLOT_CLAUSE
        + _GLM_PROMPT_RULES_TAIL
        + _GLM_PROMPT_FREEDOM
    )

    # src="PHOTO_SLOT_3" / src='PHOTO_SLOT_3' (either quote style).
    _PHOTO_SLOT_SRC_RE = re.compile(r"""(src=["'])PHOTO_SLOT_(\d+)(["'])""", re.IGNORECASE)
    # Any leftover bare token (e.g. inside CSS url(PHOTO_SLOT_1)).
    _PHOTO_SLOT_BARE_RE = re.compile(r"PHOTO_SLOT_(\d+)", re.IGNORECASE)

    @staticmethod
    def _ordered_prompt_image_urls(image_urls: Dict) -> List[str]:
        """Flatten the prompt's image_urls dict into PHOTO_SLOT order:
        hero first (slot 1), then gallery1..4 — the order the images are
        presented to the model in the prompt."""
        ordered: List[str] = []
        if image_urls.get("hero"):
            ordered.append(image_urls["hero"])
        for i in range(1, 5):
            u = image_urls.get(f"gallery{i}")
            if u:
                ordered.append(u)
        return ordered

    def _replace_photo_slots(self, html: str, ordered_urls: List[str]) -> str:
        """Deterministically bind GLM's PHOTO_SLOT_N tokens to real image URLs.

        PHOTO_SLOT_1 → first URL, PHOTO_SLOT_2 → second, etc. A slot number
        beyond the available URLs reuses the last URL rather than 404ing.
        With no URLs at all (image_choice='none'), src attributes are emptied
        so the existing _fix_broken_image_urls final safety net fills them
        with context-appropriate fallbacks — same net that catches src=""
        from the DeepSeek path. No-op when GLM used the exact URLs directly.
        """
        if not html or "PHOTO_SLOT_" not in html.upper():
            return html

        def _url_for(n: int) -> Optional[str]:
            if not ordered_urls:
                return None
            if 1 <= n <= len(ordered_urls):
                return ordered_urls[n - 1]
            return ordered_urls[-1]

        replaced = 0

        def _sub_src(m):
            nonlocal replaced
            replaced += 1
            url = _url_for(int(m.group(2)))
            # Empty src → picked up by _fix_broken_image_urls downstream.
            return f"{m.group(1)}{url or ''}{m.group(3)}"

        html = self._PHOTO_SLOT_SRC_RE.sub(_sub_src, html)

        def _sub_bare(m):
            nonlocal replaced
            replaced += 1
            return _url_for(int(m.group(1))) or ""

        html = self._PHOTO_SLOT_BARE_RE.sub(_sub_bare, html)
        if replaced:
            logger.info(
                f"🟣 GLM: bound {replaced} PHOTO_SLOT token(s) to "
                f"{len(ordered_urls)} available image URL(s)"
            )
        return html

    async def _call_glm(
        self,
        prompt: str,
        temperature: float = 0.2,
        model: Optional[str] = None,
        has_images: bool = True,
    ) -> Optional[str]:
        """Call GLM (Z.ai) API. Mirrors _call_deepseek: same signature (plus
        has_images), same return shape, same _last_api_call truncation
        tracking and headroom logging.

        has_images selects the system-prompt image clause: True (default,
        preserves prior behaviour) applies the PHOTO_SLOT contract; False
        applies the no-photo typography-led design instruction instead —
        callers pass bool(ordered image URLs) so a generation with no real
        images never emits <img> tags pointing nowhere.

        GLM-specific differences:

        - Request body carries `"thinking": {"type": "disabled"}` — without
          it glm-5.2 spends the whole output budget on reasoning and returns
          empty content.
        - Any preamble before the first '<' is stripped (GLM sometimes adds
          explanation text before the HTML despite instructions).
        - Empty/whitespace-only content returns None so the fallback chain
          proceeds to DeepSeek.
        """
        # Reset per-call API state — see _call_qwen for rationale.
        self._last_api_call = {"provider": "glm", "finish_reason": None, "truncated": False}
        if not self.zai_api_key:
            logger.warning("❌ ZAI_API_KEY not configured")
            return None

        chosen_model = model or self.zai_model
        system_prompt = (
            self._GLM_PROMPT_GOAL
            + self._GLM_PROMPT_RULES_HEAD
            + (self._GLM_PHOTO_SLOT_CLAUSE if has_images else self._GLM_NO_PHOTO_CLAUSE)
            + self._GLM_PROMPT_RULES_TAIL
            + self._GLM_PROMPT_FREEDOM
        )
        try:
            logger.info(
                f"🟣 Calling GLM (Z.ai) API ({chosen_model})... "
                f"(prompt length: {len(prompt)} chars, "
                f"image mode: {'photo-slots' if has_images else 'no-photo'})"
            )
            # Client timeout tracks the GLM budget (+30s grace), same pattern
            # as _call_deepseek's primary-budget+30 — the outer wait_for at
            # AI_GLM_TIMEOUT_SECONDS is the effective bound either way.
            async with httpx.AsyncClient(timeout=AI_GLM_TIMEOUT_SECONDS + 30) as client:
                r = await client.post(
                    f"{self.zai_base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.zai_api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": chosen_model,
                        "messages": [
                            {
                                "role": "system",
                                "content": system_prompt,
                            },
                            {"role": "user", "content": prompt},
                        ],
                        "temperature": temperature,
                        "max_tokens": AI_GLM_MAX_TOKENS,
                        # CRITICAL: without this glm-5.2 burns the entire
                        # token budget on reasoning and returns empty content.
                        "thinking": {"type": "disabled"},
                    }
                )
                if r.status_code == 200:
                    payload = r.json()
                    choice = (payload.get("choices") or [{}])[0]
                    content = (choice.get("message") or {}).get("content", "") or ""
                    finish_reason = choice.get("finish_reason") or "unknown"
                    usage = payload.get("usage") or {}
                    completion_tokens = usage.get("completion_tokens")
                    logger.info(
                        f"🟣 GLM ✅ Generated {len(content)} chars "
                        f"(finish_reason={finish_reason}, completion_tokens={completion_tokens})"
                    )
                    # Output-cap headroom logging — same rationale as DeepSeek:
                    # near-cap completions signal the cap may need raising.
                    if completion_tokens is not None:
                        _pct = completion_tokens / AI_GLM_MAX_TOKENS * 100
                        logger.info(
                            f"🟣 GLM output usage: {completion_tokens}/{AI_GLM_MAX_TOKENS} "
                            f"tokens ({_pct:.0f}% of cap)"
                        )
                    truncated_at_api = finish_reason in self._TRUNCATED_FINISH_REASONS
                    self._last_api_call = {
                        "provider": "glm",
                        "finish_reason": finish_reason,
                        "truncated": truncated_at_api,
                    }
                    if truncated_at_api:
                        logger.error(
                            f"🚨 GLM hit output cap (finish_reason={finish_reason}, "
                            f"max_tokens={AI_GLM_MAX_TOKENS}). Response was truncated at generation time."
                        )
                    # GLM sometimes prepends explanation text before the HTML
                    # despite instructions — slice from the first '<'.
                    i = content.find("<")
                    if i > 0:
                        logger.info(f"🟣 GLM: stripped {i} chars of preamble before first '<'")
                    content = content[i:] if i >= 0 else content
                    # Empty/whitespace-only content is a failure — return None
                    # so the caller falls through to DeepSeek.
                    if not content.strip():
                        logger.error("🟣 GLM ❌ Empty content — treating as failure (fallback to DeepSeek)")
                        return None
                    return content
                else:
                    try:
                        error_body = r.text[:500]
                    except Exception:
                        error_body = "(unable to read response)"
                    logger.error(f"🟣 GLM ❌ Status {r.status_code}: {error_body}")
        except httpx.TimeoutException as e:
            logger.error(f"🟣 GLM ❌ Timeout: {e}")
        except httpx.ConnectError as e:
            logger.error(f"🟣 GLM ❌ Connection error: {e}")
        except Exception as e:
            logger.error(f"🟣 GLM ❌ Exception: {e}")
        return None

    # Reviewer prompt for the premium design critique loop. The rule list is
    # composed from the SAME _GLM_PROMPT_* fragments the generator saw, so the
    # reviewer can never drift out of sync with the generation contract.
    _DESIGN_REVIEW_INSTRUCTIONS = (
        "You are a strict website design reviewer for a Malaysian small-"
        "business website builder. You will receive the full HTML of a "
        "generated single-file website. Check it against every HARD RULE "
        "below, then suggest at most 5 specific, actionable design "
        "improvements (visual hierarchy, spacing, colour restraint, "
        "typography, section flow). Do NOT suggest changing business facts, "
        "prices, or order/checkout behaviour.\n\n"
        "Respond with ONLY a JSON object, no markdown fences, in exactly "
        "this shape:\n"
        '{"pass": true|false, "violations": ["rule N: what is violated"], '
        '"improvements": ["specific actionable fix", ...]}\n'
        '"pass" is true only when there are no rule violations. '
        '"improvements" has at most 5 entries.\n\n'
    )

    def _build_design_review_prompt(self, has_images: bool = True) -> str:
        """System prompt for the DeepSeek design review: reviewer instructions
        + the exact 8 hard rules the generator was given."""
        return (
            self._DESIGN_REVIEW_INSTRUCTIONS
            + self._GLM_PROMPT_RULES_HEAD
            + (self._GLM_PHOTO_SLOT_CLAUSE if has_images else self._GLM_NO_PHOTO_CLAUSE)
            + self._GLM_PROMPT_RULES_TAIL
        )

    @staticmethod
    def _parse_design_critique(content: str) -> Optional[Dict]:
        """Parse the reviewer's JSON critique. Tolerates markdown fences and
        surrounding prose; normalises to {pass: bool, violations: [str],
        improvements: [str≤5]}. Returns None when no usable JSON is found."""
        if not content or not content.strip():
            return None
        text = content.strip()
        # Strip ```json ... ``` fences if the model added them despite rules.
        fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
        if fence:
            text = fence.group(1).strip()
        # Slice to the outermost JSON object in case of stray prose.
        start, end = text.find("{"), text.rfind("}")
        if start == -1 or end <= start:
            return None
        try:
            raw = json.loads(text[start:end + 1])
        except (json.JSONDecodeError, ValueError):
            return None
        if not isinstance(raw, dict):
            return None
        violations = [str(v) for v in raw.get("violations") or [] if str(v).strip()]
        improvements = [str(i) for i in raw.get("improvements") or [] if str(i).strip()][:5]
        return {
            # A review with violations can never pass, whatever the reviewer's
            # own (occasionally inconsistent) pass flag claims.
            "pass": bool(raw.get("pass", not violations)) and not violations,
            "violations": violations,
            "improvements": improvements,
        }

    async def _review_design_with_deepseek(
        self, html: str, has_images: bool = True
    ) -> Optional[Dict]:
        """Send generated HTML to the DeepSeek reviewer and return the parsed
        critique dict, or None on ANY failure (no key, HTTP error, timeout,
        unparseable JSON). Never raises — the critique loop is best-effort."""
        if not self.deepseek_api_key:
            logger.warning("🎨 Design review skipped: DEEPSEEK_API_KEY not configured")
            return None
        try:
            logger.info(
                f"🎨 Design review: sending {len(html)} chars to "
                f"{DESIGN_REVIEW_MODEL} (cap {DESIGN_REVIEW_TIMEOUT_SECONDS:.0f}s)"
            )
            body = {
                "model": DESIGN_REVIEW_MODEL,
                "messages": [
                    {
                        "role": "system",
                        "content": self._build_design_review_prompt(has_images),
                    },
                    {"role": "user", "content": html},
                ],
                "temperature": 0.0,
                "max_tokens": DESIGN_REVIEW_MAX_TOKENS,
                "response_format": {"type": "json_object"},
                # Non-thinking review — same contract as the GLM generation
                # call: reasoning would burn the budget.
                "thinking": {"type": "disabled"},
            }
            headers = {
                "Authorization": f"Bearer {self.deepseek_api_key}",
                "Content-Type": "application/json",
            }
            async with httpx.AsyncClient(timeout=DESIGN_REVIEW_TIMEOUT_SECONDS) as client:
                r = await asyncio.wait_for(
                    client.post(
                        f"{self.deepseek_base_url}/chat/completions",
                        headers=headers,
                        json=body,
                    ),
                    timeout=DESIGN_REVIEW_TIMEOUT_SECONDS,
                )
                # Some DeepSeek deployments reject the GLM-style `thinking`
                # field as an unknown parameter. Retry once without it so an
                # API-contract mismatch can't silently disable the loop.
                if r.status_code == 400 and "thinking" in body:
                    logger.warning(
                        "🎨 Design review got 400 with `thinking` param — retrying without it"
                    )
                    body.pop("thinking")
                    r = await asyncio.wait_for(
                        client.post(
                            f"{self.deepseek_base_url}/chat/completions",
                            headers=headers,
                            json=body,
                        ),
                        timeout=DESIGN_REVIEW_TIMEOUT_SECONDS,
                    )
            if r.status_code != 200:
                logger.error(f"🎨 Design review ❌ Status {r.status_code}: {r.text[:300]}")
                return None
            payload = r.json()
            content = ((payload.get("choices") or [{}])[0].get("message") or {}).get("content", "")
            critique = self._parse_design_critique(content)
            if critique is None:
                logger.error(f"🎨 Design review ❌ Unparseable critique: {content[:300]}")
            return critique
        except (asyncio.TimeoutError, httpx.TimeoutException):
            logger.error(f"🎨 Design review ❌ Timed out (cap {DESIGN_REVIEW_TIMEOUT_SECONDS:.0f}s)")
        except Exception as e:
            logger.error(f"🎨 Design review ❌ {e}")
        return None

    async def _run_premium_design_loop(self, html: str, has_images: bool = True) -> str:
        """Premium design critique loop: DeepSeek reviews the GLM HTML against
        the 8 hard rules; if the critique lists violations or improvements,
        GLM gets exactly ONE revision request. Returns the revised HTML, or
        the original on flag-off / clean review / any failure.

        Runs BEFORE PHOTO_SLOT binding so a revision keeps the slot contract.
        Reads the module-level PREMIUM_DESIGN_LOOP flag at call time so it is
        env-flippable and test-patchable; with the flag off this makes zero
        network calls.
        """
        if not PREMIUM_DESIGN_LOOP:
            return html

        critique = await self._review_design_with_deepseek(html, has_images=has_images)
        if critique is None:
            logger.info("🎨 Design review unavailable — shipping original HTML")
            return html

        # The critique JSON is the loop's observability contract — always log it.
        logger.info(f"🎨 Design critique: {json.dumps(critique, ensure_ascii=False)}")

        # Gate the revision on the actionable content, not the reviewer's
        # pass flag: no violations AND no improvements means there is nothing
        # to feed a revision, whatever the flag says.
        if not critique["violations"] and not critique["improvements"]:
            logger.info("🎨 Design review passed clean — no revision needed")
            return html

        feedback_lines = [f"- VIOLATION: {v}" for v in critique["violations"]]
        feedback_lines += [f"- IMPROVE: {i}" for i in critique["improvements"]]
        revision_prompt = (
            "You previously generated the website HTML below. A design "
            "reviewer checked it and returned the critique that follows. "
            "Produce a REVISED version of the SAME website that fixes every "
            "violation and applies the improvements. Keep all business facts, "
            "prices, section content, image placeholders and ids unchanged "
            "unless a critique point requires otherwise. All HARD RULES "
            "still apply.\n\n"
            "=== CRITIQUE ===\n"
            + "\n".join(feedback_lines)
            + "\n\n=== YOUR PREVIOUS HTML ===\n"
            + html
        )

        # Preserve the original call's truncation state: if the revision is
        # rejected, upstream truncation checks must reflect the HTML we ship.
        original_api_call = dict(self._last_api_call)
        logger.info(
            f"🎨 Requesting ONE GLM revision "
            f"({len(critique['violations'])} violation(s), "
            f"{len(critique['improvements'])} improvement(s))"
        )
        try:
            revised = await asyncio.wait_for(
                self._call_glm(revision_prompt, has_images=has_images),
                timeout=AI_GLM_TIMEOUT_SECONDS,
            )
        except asyncio.TimeoutError:
            logger.error("🎨 GLM revision timed out — shipping original HTML")
            self._last_api_call = original_api_call
            return html

        if not revised or "<" not in revised or self._last_api_call.get("truncated"):
            logger.error("🎨 GLM revision unusable (empty/non-HTML/truncated) — shipping original HTML")
            self._last_api_call = original_api_call
            return html

        # The revision must keep the PHOTO_SLOT contract: if the original
        # carried slot tokens but the revision dropped them (e.g. swapped in
        # hallucinated image URLs), _replace_photo_slots downstream would
        # no-op and ship broken images — reject and keep the original.
        if "PHOTO_SLOT_" in html.upper() and "PHOTO_SLOT_" not in revised.upper():
            logger.error("🎨 GLM revision dropped PHOTO_SLOT tokens — shipping original HTML")
            self._last_api_call = original_api_call
            return html

        logger.info(f"🎨 Design revision applied ({len(revised)} chars)")
        return revised

    async def _call_deepseek(
        self,
        prompt: str,
        temperature: float = 0.2,
        model: Optional[str] = None,
    ) -> Optional[str]:
        """Call DeepSeek API. Pass model=self.deepseek_model_pro for Expert (V4-Pro).

        Surfaces the response's `finish_reason` on `self._last_api_call` so
        upstream can detect an output-cap hit. max_tokens is
        AI_DEEPSEEK_MAX_TOKENS (default 24000, overridable via env); well under
        deepseek-reasoner's 384K output ceiling.
        """
        # Reset per-call API state — see _call_qwen for rationale.
        self._last_api_call = {"provider": "deepseek", "finish_reason": None, "truncated": False}
        if not self.deepseek_api_key:
            logger.warning("❌ DEEPSEEK_API_KEY not configured")
            return None

        chosen_model = model or self.deepseek_model
        try:
            logger.info(f"🔷 Calling DeepSeek API ({chosen_model})... (prompt length: {len(prompt)} chars)")
            async with httpx.AsyncClient(timeout=AI_PRIMARY_TIMEOUT_SECONDS + 30) as client:
                r = await client.post(
                    f"{self.deepseek_base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.deepseek_api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": chosen_model,
                        "messages": [
                            {
                                "role": "system",
                                "content": "You generate production-ready HTML only. Follow constraints exactly. Do not invent facts. Output ONLY HTML.",
                            },
                            {"role": "user", "content": prompt},
                        ],
                        "temperature": temperature,
                        "max_tokens": AI_DEEPSEEK_MAX_TOKENS,
                    }
                )
                if r.status_code == 200:
                    payload = r.json()
                    choice = (payload.get("choices") or [{}])[0]
                    content = (choice.get("message") or {}).get("content", "")
                    finish_reason = choice.get("finish_reason") or "unknown"
                    usage = payload.get("usage") or {}
                    completion_tokens = usage.get("completion_tokens")
                    logger.info(
                        f"🔷 DeepSeek ✅ Generated {len(content)} chars "
                        f"(finish_reason={finish_reason}, completion_tokens={completion_tokens})"
                    )
                    # Output-cap headroom: how close did this completion get to
                    # the configured max? Makes truncation pressure visible in
                    # prod even when finish_reason='stop' (a near-cap completion
                    # is a signal the cap may need raising further).
                    if completion_tokens is not None:
                        _pct = completion_tokens / AI_DEEPSEEK_MAX_TOKENS * 100
                        logger.info(
                            f"🔷 DeepSeek output usage: {completion_tokens}/{AI_DEEPSEEK_MAX_TOKENS} "
                            f"tokens ({_pct:.0f}% of cap)"
                        )
                    truncated_at_api = finish_reason in self._TRUNCATED_FINISH_REASONS
                    self._last_api_call = {
                        "provider": "deepseek",
                        "finish_reason": finish_reason,
                        "truncated": truncated_at_api,
                    }
                    if truncated_at_api:
                        logger.error(
                            f"🚨 DeepSeek hit output cap (finish_reason={finish_reason}, "
                            f"max_tokens={AI_DEEPSEEK_MAX_TOKENS}). Response was truncated at generation time."
                        )
                    return content
                else:
                    try:
                        error_body = r.text[:500]
                    except Exception:
                        error_body = "(unable to read response)"
                    logger.error(f"🔷 DeepSeek ❌ Status {r.status_code}: {error_body}")
        except httpx.TimeoutException as e:
            logger.error(f"🔷 DeepSeek ❌ Timeout after 120s: {e}")
        except httpx.ConnectError as e:
            logger.error(f"🔷 DeepSeek ❌ Connection error: {e}")
        except Exception as e:
            logger.error(f"🔷 DeepSeek ❌ Exception: {e}")
        return None

    # Default Qwen config for HTML generation.
    # qwen-plus-latest is used for HTML because it has a higher output-token cap
    # than qwen-max (qwen-max tops out at ~8K output on DashScope compatible mode,
    # which is where the 31997-char truncation came from). 12000 tokens ≈ 40-48K
    # chars of HTML, enough for 15+ menu cards plus template structure.
    # Overridable from the environment so the HTML model can be A/B-tested
    # (e.g. qwen3.7-max vs qwen-plus) from Render without a redeploy.
    # Default intentionally stays qwen-plus-latest until a swap is validated.
    QWEN_HTML_MODEL = os.getenv("QWEN_HTML_MODEL", "qwen-plus-latest")
    QWEN_HTML_MAX_TOKENS = 12000
    # Finish reasons that mean the model hit its output cap (vs. natural stop).
    # OpenAI-compatible providers (DashScope/Qwen, DeepSeek) all use either
    # "length" or "max_tokens". Kept as one constant so every provider caller
    # checks the same set.
    _TRUNCATED_FINISH_REASONS = {"length", "max_tokens"}
    _QWEN_TRUNCATED_FINISH_REASONS = _TRUNCATED_FINISH_REASONS  # back-compat alias

    async def _call_qwen(
        self,
        prompt: str,
        temperature: float = 0.2,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
    ) -> Optional[str]:
        """Call Qwen API.

        Args:
            prompt: user message
            temperature: sampling temperature
            model: override model (defaults to QWEN_HTML_MODEL for HTML generation)
            max_tokens: override output cap (defaults to QWEN_HTML_MAX_TOKENS)

        Also surfaces DashScope's `finish_reason` on `self._last_api_call` so
        upstream (generate_website, _call_qwen_with_truncation_retry) can detect
        an output-cap hit without parsing logs.
        """
        # Reset per-call API state before every attempt — even early-return
        # paths must not leak a stale "truncated=True" from a prior call.
        self._last_api_call = {"provider": "qwen", "finish_reason": None, "truncated": False}
        if not self.qwen_api_key:
            logger.warning("❌ QWEN_API_KEY not configured")
            return None

        model_id = model or self.QWEN_HTML_MODEL
        mt = max_tokens or self.QWEN_HTML_MAX_TOKENS

        try:
            logger.info(
                f"🟡 Calling Qwen API... model={model_id} max_tokens={mt} "
                f"prompt_chars={len(prompt)}"
            )
            async with httpx.AsyncClient(timeout=240.0) as client:
                r = await client.post(
                    f"{self.qwen_base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.qwen_api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": model_id,
                        "messages": [
                            {
                                "role": "system",
                                "content": "You generate production-ready HTML only. Follow constraints exactly. Do not invent facts. Output ONLY HTML.",
                            },
                            {"role": "user", "content": prompt},
                        ],
                        "temperature": temperature,
                        "max_tokens": mt,
                    }
                )
                if r.status_code == 200:
                    payload = r.json()
                    choice = (payload.get("choices") or [{}])[0]
                    content = (choice.get("message") or {}).get("content", "")
                    finish_reason = choice.get("finish_reason") or "unknown"
                    usage = payload.get("usage") or {}
                    completion_tokens = usage.get("completion_tokens")
                    logger.info(
                        f"🟡 Qwen ✅ Generated {len(content)} chars "
                        f"(finish_reason={finish_reason}, completion_tokens={completion_tokens})"
                    )
                    truncated_at_api = finish_reason in self._TRUNCATED_FINISH_REASONS
                    self._last_api_call = {
                        "provider": "qwen",
                        "finish_reason": finish_reason,
                        "truncated": truncated_at_api,
                    }
                    if truncated_at_api:
                        logger.error(
                            f"🚨 Qwen hit output cap (finish_reason={finish_reason}, "
                            f"max_tokens={mt}). Response was truncated at generation time."
                        )
                    return content
                else:
                    try:
                        error_body = r.text[:500]
                    except Exception:
                        error_body = "(unable to read response)"
                    logger.error(f"🟡 Qwen ❌ Status {r.status_code}: {error_body}")
        except httpx.TimeoutException as e:
            logger.error(f"🟡 Qwen ❌ Timeout after 240s: {e}")
        except httpx.ConnectError as e:
            logger.error(f"🟡 Qwen ❌ Connection error: {e}")
        except Exception as e:
            logger.error(f"🟡 Qwen ❌ Exception: {e}")
        return None

    # Balance helpers moved to app.utils.html_balance so the publish endpoints
    # can reuse them (Item 5 / Option B of the truncation follow-up).
    # Thin instance delegators kept for the existing call sites within this
    # file — no external callers, so no signature compatibility concerns.
    def _find_unclosed_tags(self, html: str) -> List[str]:
        from app.utils.html_balance import find_unclosed_tags
        return find_unclosed_tags(html)

    def _compress_prompt(self, prompt: str) -> str:
        """
        Produce a shorter version of an HTML-generation prompt for retry after
        truncation. Strips example sections and bulky instruction preambles while
        preserving the business context, menu items, image URLs, and phone/address.

        Heuristics:
          - Drop lines that are pure headings for EXAMPLE/OUTPUT FORMAT sections
            and the blocks beneath them until the next all-caps heading.
          - Collapse runs of blank lines.
          - Truncate any remaining content past 12K chars (the important details
            for a Malaysian SMB site fit comfortably in that budget).
        """
        if not prompt:
            return prompt

        lines = prompt.split("\n")
        out: List[str] = []
        drop_section = False
        drop_headers = re.compile(
            r"^\s*(#+\s*)?(EXAMPLE|EXAMPLES|SAMPLE OUTPUT|OUTPUT FORMAT|"
            r"REFERENCE|INSPIRATION|FULL EXAMPLE)[:\s]*$",
            re.IGNORECASE,
        )
        section_header = re.compile(r"^\s*={2,}|^\s*#{1,6}\s+\S|^\s*[A-Z][A-Z _\-]{3,}:?\s*$")
        for line in lines:
            if drop_headers.match(line):
                drop_section = True
                continue
            if drop_section:
                # End the drop when we hit a new section header
                if section_header.match(line):
                    drop_section = False
                else:
                    continue
            out.append(line)

        compressed = "\n".join(out)
        # Collapse 3+ blank lines to just 1 blank line
        compressed = re.sub(r"\n\s*\n\s*\n+", "\n\n", compressed)
        # Hard ceiling — keep the tail (business-specific fields are usually last)
        if len(compressed) > 12000:
            head = compressed[:2000]
            tail = compressed[-9000:]
            compressed = head + "\n\n[...examples trimmed for retry...]\n\n" + tail
        logger.info(
            f"📉 Compressed prompt: {len(prompt)} → {len(compressed)} chars "
            f"(dropped {len(prompt) - len(compressed)} chars)"
        )
        return compressed

    def _extract_html(self, text: str) -> Optional[str]:
        """Extract only HTML from AI response, remove explanations.

        If the output is truncated (no closing </html>), this still auto-closes
        so the page is renderable, but logs loudly and records diagnostic info
        (last 200 chars + list of unclosed tags) on `self._last_extract_info`
        so callers can decide to retry.
        """
        import re

        # Reset per-call diagnostic state (single call site at a time per request)
        self._last_extract_info: Dict = {"was_truncated": False, "unclosed_tags": [], "tail": ""}

        if not text:
            return None

        # Remove markdown code blocks
        if "```html" in text:
            match = re.search(r'```html\s*(.*?)\s*```', text, re.DOTALL)
            if match:
                text = match.group(1)
        elif "```" in text:
            match = re.search(r'```\s*(.*?)\s*```', text, re.DOTALL)
            if match:
                text = match.group(1)

        # Remove any text before <!DOCTYPE or <html
        if "<!DOCTYPE" in text:
            text = text[text.find("<!DOCTYPE"):]
        elif "<html" in text:
            text = text[text.find("<html"):]

        # Remove any text after </html>
        if "</html>" in text:
            text = text[:text.find("</html>") + 7]

        # Remove common AI explanation patterns
        patterns_to_remove = [
            r"Here's an improved version.*?(?=<!DOCTYPE|<html)",
            r"(?<=</html>).*?###.*",
            r"(?<=</html>).*?Key Improvements:.*",
            r"(?<=</html>).*?\*\*Engaging Descriptions\*\*.*",
            r"^---\s*",  # Remove markdown separators at start
            r"\s*---$",  # Remove markdown separators at end
        ]

        for pattern in patterns_to_remove:
            text = re.sub(pattern, '', text, flags=re.DOTALL | re.IGNORECASE)

        text = text.strip()

        # Detect truncation. Two flavours, both treated as truncated:
        #   (1) The response doesn't end with </html> — classic end-of-stream cut.
        #   (2) The response DOES end with </html>, but the body has mid-document
        #       unclosed tags — i.e. the model gracefully wrote </body></html> at
        #       the tail but dropped one or more intermediate </section>/</div>
        #       closers mid-body. This is the silent failure that put broken
        #       sites in production: every boundary check passed, the page
        #       looked valid, but the splice in inject_ordering_system inherited
        #       unbalanced markup.
        # We still auto-close so the caller gets a renderable page, but we shout
        # about it so downstream can trigger a retry and flag the job.
        if text:
            tail = text[-200:]
            ends_with_html = text.rstrip().endswith('</html>')

            # Two scans: stack on the raw text (for case 1), and stack on the
            # text with trailing </body></html> stripped (for case 2). The
            # forgiving "pop matching tag if present" loop in _find_unclosed_tags
            # means trailing </body></html> would otherwise consume any
            # intermediate unclosed tags by walking backwards through the stack,
            # hiding case 2 entirely. Strip the wrapper closers first so what's
            # left on the stack is genuine mid-body imbalance.
            unclosed = self._find_unclosed_tags(text)
            unclosed_body_raw = self._find_unclosed_tags(
                self._strip_trailing_wrapper_closers(text)
            )
            # Stripping </body></html> for the re-scan leaves <body> and <html>
            # openers on the stack; those are expected — filter them out so what
            # remains is genuine mid-body imbalance (the testimonials <section>,
            # the layout <div>, etc).
            unclosed_body = [t for t in unclosed_body_raw if t not in ("html", "body")]

            if not ends_with_html:
                # Case 1: classic truncation. unclosed is the full stack from a
                # forward scan, typically [..., 'html', 'body', 'div', 'section'].
                # Emit closers innermost-first for everything between body and
                # the end, then close </body></html> as the wrapper.
                self._last_extract_info = {
                    "was_truncated": True,
                    "unclosed_tags": unclosed,
                    "tail": tail,
                }
                logger.error(f"🚨 HTML TRUNCATED at {len(text)} chars (no </html>)")
                logger.error(f"   Last 200 chars: {tail!r}")
                logger.error(f"   Unclosed tags ({len(unclosed)}): {unclosed}")
                # Inner-tag closers (everything except html/body, which the
                # wrapper handles). reversed() = innermost-first.
                inner_closers = "".join(
                    f"</{t}>" for t in reversed(unclosed) if t not in ("html", "body")
                )
                if '</body>' not in text:
                    text += "\n" + inner_closers + "\n</body>\n</html>"
                else:
                    text += "\n" + inner_closers + "\n</html>"
                if inner_closers:
                    logger.info(
                        f"   🔧 Auto-emitted {len(unclosed) - sum(1 for t in unclosed if t in ('html','body'))} "
                        f"missing closer(s): {inner_closers}"
                    )
            elif unclosed_body:
                # Case 2: silent mid-body imbalance — </html> present, but the
                # body section is missing closers. Inserting closers AFTER
                # </body></html> would just add stray markup outside the
                # document; instead, splice them BEFORE the existing </body>
                # (or before </html> if no </body>).
                self._last_extract_info = {
                    "was_truncated": True,
                    "unclosed_tags": unclosed_body,
                    "tail": tail,
                }
                logger.error(
                    f"🚨 HTML UNBALANCED at {len(text)} chars (</html> present but "
                    f"{len(unclosed_body)} mid-body tag(s) unclosed) — silent truncation"
                )
                logger.error(f"   Last 200 chars: {tail!r}")
                logger.error(f"   Unclosed body tags: {unclosed_body}")
                # Innermost-first: reversed stack order. e.g. stack
                # ['div', 'section'] → close </section> first, then </div>.
                inner_closers = "".join(f"</{t}>" for t in reversed(unclosed_body))
                # Splice before </body> (preferred) or </html> as fallback.
                body_match = re.search(r'</\s*body\s*>', text, flags=re.IGNORECASE)
                html_match = re.search(r'</\s*html\s*>', text, flags=re.IGNORECASE)
                if body_match:
                    insert_at = body_match.start()
                    text = text[:insert_at] + inner_closers + "\n" + text[insert_at:]
                    logger.info(
                        f"   🔧 Inserted {len(unclosed_body)} closer(s) before </body>: {inner_closers}"
                    )
                elif html_match:
                    insert_at = html_match.start()
                    text = text[:insert_at] + inner_closers + "\n" + text[insert_at:]
                    logger.info(
                        f"   🔧 Inserted {len(unclosed_body)} closer(s) before </html>: {inner_closers}"
                    )
                # If neither match somehow (shouldn't happen — ends_with_html
                # implied </html> exists), fall through unmodified; the flag
                # is still set so downstream knows.

        # Deterministic gallery post-pass: enforce uniform card-image heights
        # and drop duplicate category tags regardless of what the model emitted.
        # Runs after truncation detection/closer insertion so it can't affect
        # those signals; never raises.
        try:
            from app.services.gallery_normalizer import normalize_gallery_html
            text = normalize_gallery_html(text)
        except Exception as _gn_err:
            logger.warning(f"gallery normalize skipped: {_gn_err}")

        return text

    @staticmethod
    def _strip_trailing_wrapper_closers(text: str) -> str:
        # Delegator — implementation lives in app.utils.html_balance.
        from app.utils.html_balance import strip_trailing_wrapper_closers
        return strip_trailing_wrapper_closers(text)

    def _log_timing_breakdown(self, step_timings: Dict[str, float], total_time: float) -> None:
        """
        Log a human-readable timing breakdown sorted by duration (largest first).
        Used by generate_website to highlight which pipeline step dominated total
        wall-clock time — diagnostic only (see Bug 3).
        """
        if not step_timings:
            logger.info("⏱️  Step timings: (none recorded)")
            return
        measured = sum(step_timings.values())
        logger.info(
            f"⏱️  TIMING BREAKDOWN (measured: {measured:.2f}s, total including overhead: {total_time:.2f}s):"
        )
        for step, duration in sorted(step_timings.items(), key=lambda kv: -kv[1]):
            pct = (duration / total_time * 100) if total_time > 0 else 0
            logger.info(f"    {step}: {duration:.2f}s ({pct:.1f}% of total)")

    async def _call_qwen_with_truncation_retry(
        self,
        prompt: str,
        temperature: float = 0.2,
    ) -> Tuple[Optional[str], Dict]:
        """
        Call Qwen → extract → if truncated, retry ONCE with a compressed prompt.

        Returns (html, flags) where flags is a dict suitable for persisting on
        the generation_jobs row:
            { "was_truncated": bool, "truncation_retries": int,
              "needs_manual_review": bool, "unclosed_tags": [...] }

        "needs_manual_review" is true only if BOTH attempts truncated.
        """
        flags: Dict = {
            "was_truncated": False,
            "truncation_retries": 0,
            "needs_manual_review": False,
            "unclosed_tags": [],
        }

        raw = await self._call_qwen(prompt, temperature=temperature)
        # Capture API-boundary truncation BEFORE _extract_html runs (which resets
        # _last_extract_info but not _last_api_call). Either signal counts.
        api_truncated_first = bool(self._last_api_call.get("truncated")) if raw else False
        html = self._extract_html(raw) if raw else None
        first_info = dict(self._last_extract_info) if raw else {"was_truncated": False, "unclosed_tags": [], "tail": ""}

        first_truncated = first_info.get("was_truncated") or api_truncated_first
        if not first_truncated:
            return html, flags

        # First attempt truncated — retry once with a compressed prompt
        flags["was_truncated"] = True
        flags["truncation_retries"] = 1
        flags["unclosed_tags"] = first_info.get("unclosed_tags", [])
        logger.warning(
            f"🟠 HTML truncated on first attempt — retrying once with compressed prompt "
            f"(unclosed={flags['unclosed_tags']}, api_truncated={api_truncated_first})"
        )
        compressed = self._compress_prompt(prompt)
        retry_raw = await self._call_qwen(compressed, temperature=temperature)
        api_truncated_retry = bool(self._last_api_call.get("truncated")) if retry_raw else False
        retry_html = self._extract_html(retry_raw) if retry_raw else None
        retry_info = dict(self._last_extract_info) if retry_raw else {"was_truncated": True, "unclosed_tags": [], "tail": ""}

        retry_truncated = retry_info.get("was_truncated") or api_truncated_retry
        if retry_html and not retry_truncated:
            logger.info("✅ Retry succeeded with complete HTML")
            return retry_html, flags

        # Both attempts truncated — flag for review, fall back to whichever we have
        flags["needs_manual_review"] = True
        logger.error(
            f"🔴 DOUBLE TRUNCATION - flagging for review. "
            f"first_unclosed={first_info.get('unclosed_tags')}, "
            f"retry_unclosed={retry_info.get('unclosed_tags')}"
        )
        # Prefer the retry result if it has more content, else the first
        if retry_html and (not html or len(retry_html) > len(html)):
            return retry_html, flags
        return html, flags

    def _validate_generated_html(
        self,
        html: str,
        required_image_urls: List[str],
        required_wa_digits: str,
    ) -> List[str]:
        """
        Validate AI output and detect hallucinations we CAN'T fix deterministically.

        Most rules that used to live here have been moved to _fix_placeholders
        (2026-04-18 optimization audit):
          - R1 (<html> wrapper)   → redundant; _extract_html auto-closes.
          - R2 (Tailwind CDN)     → fixed by _fix_placeholders if missing.
          - R3 (forbidden hosts)  → fixed by _fix_placeholders (via/example/…).
          - R5 (bracket regex)    → too high false-positive rate, dropped.
          - R6 (wa.me link)       → fixed by _fix_placeholders if missing + digits known.

        What remains is required_image_urls (R7) — the only signal we can't
        deterministically patch because we don't know which gallery slot to
        inject into without knowing the HTML structure the AI produced. If this
        fires, it's almost always a genuine AI miss worth regenerating.
        """
        errors: List[str] = []
        if not html or not isinstance(html, str):
            return ["Empty HTML output"]

        # Required image URLs (when user supplied)
        for url in required_image_urls:
            if url and url not in html:
                errors.append(f"Missing required image URL in HTML: {url}")

        return errors

    def _fix_menu_item_images(self, html: str, business_description: str = "") -> str:
        """
        Fix duplicate product/service images - ensure each item has a unique image

        This function finds product/service items with duplicate images and replaces them
        with unique images based on the product/service name.
        Works for food, fashion, salon services, and all Malaysian business products.

        Args:
            html: The HTML content to fix
            business_description: Business description for context-aware image selection
        """
        if not html:
            return html

        import re

        logger.info("🖼️ Fixing product/service images to ensure uniqueness...")

        # Track image URLs we've seen
        image_usage = {}
        replacements = []

        # Pattern to match product/service items with images
        # This matches common HTML patterns for menu/product items:
        # - <img src="..."> followed by text (product name)
        # - Or text followed by <img>
        patterns = [
            # Pattern 1: <img src="URL"> ... <h3>Product Name</h3>
            r'<img[^>]*src="([^"]+)"[^>]*>[\s\S]{0,200}?<h[2-4][^>]*>(.*?)</h[2-4]>',
            # Pattern 2: <h3>Product Name</h3> ... <img src="URL">
            r'<h[2-4][^>]*>(.*?)</h[2-4]>[\s\S]{0,200}?<img[^>]*src="([^"]+)"[^>]*>',
            # Pattern 3: Direct img with alt containing product name
            r'<img[^>]*src="([^"]+)"[^>]*alt="([^"]*)"[^>]*>',
        ]

        for pattern in patterns:
            matches = re.finditer(pattern, html, re.IGNORECASE)
            for match in matches:
                if len(match.groups()) == 2:
                    if 'src=' in match.group(0)[:30]:  # Pattern 1 or 3
                        img_url = match.group(1)
                        item_name = match.group(2).strip()
                    else:  # Pattern 2
                        item_name = match.group(1).strip()
                        img_url = match.group(2)

                    # Clean item name (remove HTML tags)
                    item_name = re.sub(r'<[^>]+>', '', item_name).strip()

                    if not item_name or not img_url:
                        continue

                    # Never "fix" user-provided/CDN images (Cloudinary, etc.).
                    # Only dedupe/replace known stock/placeholder sources.
                    img_url_lower = img_url.lower()
                    if (
                        "images.unsplash.com" not in img_url_lower
                        and "via.placeholder.com" not in img_url_lower
                        and "placeholder.com" not in img_url_lower
                    ):
                        continue

                    # Track this image URL
                    if img_url not in image_usage:
                        image_usage[img_url] = []
                    image_usage[img_url].append(item_name)

        # Find duplicate image URLs
        duplicate_images = {url: items for url, items in image_usage.items() if len(items) > 1}

        if duplicate_images:
            logger.warning(f"⚠️ Found {len(duplicate_images)} image URLs used for multiple items!")
            for url, items in duplicate_images.items():
                logger.warning(f"   {url[:60]}... used for: {', '.join(items[:3])}")

            # Fix duplicates - use comprehensive image matching
            for dup_url, items in duplicate_images.items():
                # Skip the first occurrence, replace others
                for i, item in enumerate(items):
                    if i == 0:
                        continue  # Keep first usage

                    # Get unique image for this item using comprehensive matching
                    new_url = self.get_matching_image(item, business_type=business_description)
                    logger.info(f"   🔄 Replacing image for '{item}': {new_url}")

            # Simpler approach: Scan for common product/service item patterns and fix images
            fixed_html = html
            seen_urls = set()

            def replace_image(match):
                full_match = match.group(0)
                img_url = match.group(1)

                # Try to extract product/service name from context
                # Look for nearby h2, h3, h4 tags
                context_start = max(0, match.start() - 300)
                context_end = min(len(html), match.end() + 300)
                context = html[context_start:context_end]

                item_name = None
                heading_match = re.search(r'<h[2-4][^>]*>(.*?)</h[2-4]>', context)
                if heading_match:
                    item_name = re.sub(r'<[^>]+>', '', heading_match.group(1)).strip()

                # If we've seen this URL before and we have an item name, replace it.
                # Pass seen_urls so pool rotation skips any URL already on the page.
                if img_url in seen_urls and item_name:
                    new_url = self.get_matching_image(
                        item_name,
                        business_type=business_description,
                        used_urls=seen_urls,
                    )
                    logger.info(f"   🔄 '{item_name}': {img_url[:50]}... → {new_url[:50]}...")
                    seen_urls.add(new_url)
                    return full_match.replace(img_url, new_url)
                else:
                    seen_urls.add(img_url)
                    return full_match

            # Replace images
            fixed_html = re.sub(r'<img[^>]*src="([^"]+)"[^>]*>', replace_image, fixed_html)

            logger.info("✅ Product/service images fixed")
            return fixed_html

        logger.info("✅ No duplicate product/service images found")
        return html

    async def _generate_ai_food_images(
        self,
        html: str,
        max_images: Optional[int] = None,
        zai_phase: Optional[Dict] = None,
    ) -> tuple:
        """
        Replace Unsplash food images with AI-generated images

        - Scans HTML for Malaysian food items
        - Generates AI images using DeepSeek/Qwen → Stability AI → Cloudinary pipeline
        - Replaces Unsplash URLs with Cloudinary URLs

        Args:
            max_images: Optional hard cap on how many food images to generate
                (the caller's remaining AI-image quota). None means no cap.
                When 0 or less, no food images are generated.

        Returns tuple of (html_with_ai_images, count_of_images_generated)
        """
        if not html or not self._image_generation_available():
            logger.info("   ⚠️ Skipping AI image generation (no image provider API key)")
            return html, 0

        import re

        logger.info("🎨 GENERATING AI IMAGES FOR MALAYSIAN FOOD ITEMS...")

        # Pattern to find images with food names
        # Matches: <img src="URL"> near <h3>Food Name</h3>
        patterns = [
            r'(<img[^>]*src=")([^"]+unsplash[^"]+)("[^>]*>[\s\S]{0,200}?<h[2-4][^>]*>)(.*?)(</h[2-4]>)',
            r'(<h[2-4][^>]*>)(.*?)(</h[2-4]>[\s\S]{0,200}?<img[^>]*src=")([^"]+unsplash[^"]+)("[^>]*>)',
        ]

        replacements = {}
        food_items_found = []

        for pattern in patterns:
            matches = re.finditer(pattern, html, re.IGNORECASE)
            for match in matches:
                groups = match.groups()

                # Extract item name and URL based on pattern
                if 'src=' in groups[0]:  # Pattern 1
                    img_url = groups[1]
                    item_name = groups[3].strip()
                else:  # Pattern 2
                    item_name = groups[1].strip()
                    img_url = groups[3]

                # Clean item name
                item_name = re.sub(r'<[^>]+>', '', item_name).strip()
                item_name = re.sub(r'[🍛🍗🐟🥤]', '', item_name).strip()  # Remove emojis

                # Check if it's Malaysian food
                is_food = any(word in item_name.lower() for word in [
                    'nasi', 'mee', 'ayam', 'ikan', 'roti', 'satay', 'rendang', 'laksa',
                    'rice', 'noodle', 'chicken', 'fish', 'bread', 'curry', 'teh', 'kopi',
                    'cendol', 'kuih', 'goreng', 'lemak', 'kandar', 'bakar'
                ])

                if is_food and 'unsplash' in img_url.lower():
                    food_items_found.append((item_name, img_url))

        if not food_items_found:
            logger.info("   ℹ️ No Malaysian food items found that need AI generation")
            return html, 0

        # Hard-cap food image generation to the caller's remaining AI-image
        # quota so a single build never overshoots the user's plan limit.
        if max_images is not None:
            if max_images <= 0:
                logger.info(
                    f"   🚫 AI image quota exhausted — skipping all "
                    f"{len(food_items_found)} food image(s)"
                )
                return html, 0
            if len(food_items_found) > max_images:
                logger.info(
                    f"   ✂️ Capping food images to remaining quota: "
                    f"{max_images} of {len(food_items_found)}"
                )
                food_items_found = food_items_found[:max_images]

        logger.info(f"   🍽️ Found {len(food_items_found)} food items to generate:")
        for name, _ in food_items_found:
            logger.info(f"      - {name}")

        # Generate AI images for each food item in parallel, bounded by a
        # semaphore so we don't burst Stability AI's per-second rate limit.
        # Start at 4 concurrent calls; lower to 2 if rate limits appear.
        food_image_semaphore = asyncio.Semaphore(4)

        async def _bounded_food_image(item_name: str, old_url: str):
            """Return (old_url, item_name, new_url_or_None) — never raises."""
            async with food_image_semaphore:
                try:
                    logger.info(f"   🎨 Generating AI image for: {item_name}")
                    ai_url = await self.generate_food_image(item_name, zai_phase=zai_phase)
                    if ai_url and 'cloudinary' in ai_url.lower():
                        logger.info(f"   ✅ Generated: {ai_url[:60]}...")
                        return (old_url, item_name, ai_url)
                    logger.warning(f"   ⚠️ AI generation failed for: {item_name}, using fallback image")
                except Exception as e:
                    logger.error(f"   ❌ Error generating image for {item_name}: {e}")
                # Fall through to Bug-2 pool fallback on either failure path
                try:
                    fallback_url = self.get_matching_image(item_name)
                    if fallback_url and old_url != fallback_url:
                        logger.info(f"   🔄 Fallback image: {fallback_url[:60]}...")
                        return (old_url, item_name, fallback_url)
                except Exception:
                    pass
                return (old_url, item_name, None)

        results = await asyncio.gather(
            *[_bounded_food_image(name, url) for name, url in food_items_found],
            return_exceptions=False,
        )
        for old_url, _item, new_url in results:
            if new_url:
                replacements[old_url] = new_url

        # Apply replacements
        ai_food_images_count = len(replacements)
        if replacements:
            logger.info(f"   🔄 Replacing {ai_food_images_count} Unsplash URLs with AI-generated images...")
            for old_url, new_url in replacements.items():
                html = html.replace(old_url, new_url)
            logger.info(f"   ✅ AI image generation complete! ({ai_food_images_count} images)")
        else:
            logger.warning("   ⚠️ No AI images were generated")

        return html, ai_food_images_count

    def _fix_placeholders(self, html: str, name: str, desc: str, wa_digits: str = "") -> str:
        """Fix any remaining placeholders as a safety net.

        Also absorbs the deterministic fixes that used to live in
        _validate_generated_html (R2/R3/R6). This makes the validation step
        redundant for those rules, eliminating a ~100s Qwen retry.
        """
        if not html:
            return html

        biz_type = self._detect_type(desc)
        imgs = self.IMAGES.get(biz_type, self.IMAGES["default"])

        # Fix placeholder image URLs
        html = html.replace("via.placeholder.com/400x300", imgs["gallery"][0].replace("?w=800&q=80", "?w=400&h=300&q=80"))
        html = html.replace("via.placeholder.com/600x400", imgs["gallery"][1].replace("?w=800&q=80", "?w=600&h=400&q=80"))
        html = html.replace("via.placeholder.com/300", imgs["gallery"][2].replace("?w=800&q=80", "?w=300&q=80"))
        html = html.replace("https://via.placeholder.com", imgs["gallery"][0].split("?")[0])
        html = html.replace("placeholder.com", "images.unsplash.com")

        # R3 extension: example.com in image src attributes → real stock image.
        # Only rewrite src="…example.com…" so we don't trample genuine anchor
        # refs or legal boilerplate that happens to mention example.com.
        html = re.sub(
            r'src="[^"]*example\.com[^"]*"',
            f'src="{imgs["gallery"][0]}"',
            html,
            flags=re.IGNORECASE,
        )

        # Fix text placeholders
        html = html.replace("[BUSINESS_TAGLINE]", f"Selamat Datang ke {name}!")
        html = html.replace("[ABOUT_TEXT]", f"{name} adalah destinasi utama untuk semua keperluan anda. Kami menyediakan perkhidmatan berkualiti tinggi dengan harga berpatutan.")
        html = html.replace("[SERVICE_1_NAME]", "Perkhidmatan Premium")
        html = html.replace("[SERVICE_1_DESC]", "Perkhidmatan berkualiti tinggi untuk kepuasan anda.")
        html = html.replace("[SERVICE_2_NAME]", "Harga Berpatutan")
        html = html.replace("[SERVICE_2_DESC]", "Harga yang kompetitif tanpa mengorbankan kualiti.")
        html = html.replace("[SERVICE_3_NAME]", "Sokongan Pelanggan")
        html = html.replace("[SERVICE_3_DESC]", "Pasukan kami sentiasa bersedia membantu anda.")
        html = html.replace("[CONTACT_TEXT]", "Hubungi kami untuk sebarang pertanyaan. Kami sentiasa bersedia membantu!")

        # R2 (moved from _validate_generated_html): ensure Tailwind CDN is loaded.
        # The strict prompt includes the script tag, but models occasionally
        # rewrite or strip it. Insert right before </head> if absent.
        if "cdn.tailwindcss.com" not in html.lower() and "</head>" in html:
            html = html.replace(
                "</head>",
                '<script src="https://cdn.tailwindcss.com"></script>\n</head>',
                1,
            )
            logger.info("   🔧 Injected missing Tailwind CDN script")

        # R6 (moved from _validate_generated_html): ensure a wa.me/ link exists.
        # If caller provided wa_digits and no wa.me link is in the HTML,
        # append a minimal floating WhatsApp button right before </body>.
        if wa_digits and "wa.me/" not in html.lower() and "</body>" in html:
            wa_button = (
                f'<a href="https://wa.me/{wa_digits}" target="_blank" rel="noopener" '
                f'aria-label="WhatsApp" '
                f'style="position:fixed;bottom:20px;right:20px;background:#25D366;color:white;'
                f'padding:14px;border-radius:50%;font-size:24px;text-decoration:none;'
                f'box-shadow:0 4px 12px rgba(0,0,0,0.15);z-index:9997;display:flex;'
                f'align-items:center;justify-content:center;width:56px;height:56px;">'
                f'<span>💬</span></a>'
            )
            html = html.replace("</body>", f"{wa_button}\n</body>", 1)
            logger.info(f"   🔧 Injected missing WhatsApp link (wa.me/{wa_digits})")

        # Normalize wa.me links to digits-only (no leading '+', no spaces/dashes).
        # The '+' form (wa.me/+60123456789) fails to open on some Android
        # WhatsApp clients; a page can end up with both forms. Rewrite the phone
        # segment of every wa.me/ URL to bare digits while preserving any query
        # string (?text=...).
        html = self._normalize_wa_links(html)

        # Post-generation linter: strip Pro-only Font Awesome icons (blank
        # squares on free-6.x) and rewrite out-of-scale Tailwind opacity/spacing
        # utilities the Play CDN silently drops. Deterministic + logged.
        try:
            from app.services.generation_linter import lint_html
            html, lint_report = lint_html(html, context=f"{name} {desc}")
            if lint_report.changed:
                logger.info(
                    f"   🧹 Generation linter: {len(lint_report.fa_replacements)} FA icon(s), "
                    f"{len(lint_report.tw_rewrites)} Tailwind class(es) fixed"
                )
        except Exception as e:
            logger.warning(f"   ⚠️ Generation linter skipped: {e}")

        return html

    @staticmethod
    def _normalize_wa_links(html: str) -> str:
        """Rewrite every wa.me/ phone segment to bare digits (no '+', spaces or
        dashes). Preserves the path's query string. Idempotent."""
        if not html or "wa.me/" not in html:
            return html

        def _repl(m: re.Match) -> str:
            digits = re.sub(r"\D", "", m.group("phone"))
            return f"wa.me/{digits}"

        # Match wa.me/ followed by a phone-ish segment (digits, +, spaces, dashes)
        # up to the query string, fragment, quote, or whitespace.
        return re.sub(
            r"wa\.me/(?P<phone>[+\d][\d\s\-+]*)",
            _repl,
            html,
        )

    def _fix_broken_image_urls(self, html: str, business_description: str = "") -> str:
        """
        Fix empty, broken, or invalid image URLs to ensure all images display correctly.

        This is the FINAL safety net to catch any images that slipped through:
        - Empty src attributes (src="", src="#", src="undefined")
        - Invalid/broken URLs
        - Placeholder patterns that weren't caught earlier
        - Any img tags without valid URLs

        Returns HTML with all broken images replaced with valid fallback images.
        """
        if not html:
            return html

        import re

        logger.info("🔧 Final check: Fixing any broken/empty image URLs...")

        # Detect business type for context-appropriate fallbacks
        biz_type = self._detect_type(business_description)
        fallback_imgs = self.IMAGES.get(biz_type, self.IMAGES["default"])
        default_fallback = fallback_imgs.get("hero", self.BUSINESS_IMAGES["default"])

        # Patterns for broken/invalid image URLs
        broken_patterns = [
            r'src=""',                                    # Empty src
            r"src=''",                                    # Empty src (single quotes)
            r'src="#"',                                   # Hash placeholder
            r'src="undefined"',                           # JavaScript undefined
            r'src="null"',                                # null value
            r'src="javascript:[^"]*"',                    # JavaScript URLs
            r'src="data:image/[^"]*;base64,"',           # Empty base64 (no actual data after comma)
            r'src="[^"]*placeholder\.com[^"]*"',         # placeholder.com URLs
            r'src="[^"]*via\.placeholder[^"]*"',         # via.placeholder URLs
            r'src="[^"]*placehold\.it[^"]*"',            # placehold.it URLs
            r'src="[^"]*placekitten[^"]*"',              # placekitten URLs
            r'src="[^"]*dummyimage[^"]*"',               # dummyimage URLs
        ]

        fixed_count = 0
        for pattern in broken_patterns:
            matches = re.findall(pattern, html, re.IGNORECASE)
            if matches:
                for match in matches:
                    # Try to extract nearby context to get a better fallback
                    context_match = re.search(
                        r'<[^>]*' + re.escape(match) + r'[^>]*>[\s\S]{0,300}?<h[2-4][^>]*>(.*?)</h[2-4]>',
                        html,
                        re.IGNORECASE
                    )

                    if context_match:
                        item_name = re.sub(r'<[^>]+>', '', context_match.group(1)).strip()
                        fallback_url = self.get_matching_image(item_name, business_type=business_description)
                    else:
                        # Use gallery images in rotation
                        gallery_imgs = fallback_imgs.get("gallery", [default_fallback])
                        fallback_url = gallery_imgs[fixed_count % len(gallery_imgs)] if gallery_imgs else default_fallback

                    # Replace the broken src with fallback
                    new_src = f'src="{fallback_url}"'
                    html = html.replace(match, new_src, 1)  # Replace one at a time
                    fixed_count += 1
                    logger.info(f"   🔄 Fixed broken image: {match[:40]}... → {fallback_url[:50]}...")

        # Also check for img tags that might have slipped through without any src
        img_without_src = re.findall(r'<img(?![^>]*src=)[^>]*>', html, re.IGNORECASE)
        for img_tag in img_without_src:
            # Add a src attribute with fallback
            gallery_imgs = fallback_imgs.get("gallery", [default_fallback])
            fallback_url = gallery_imgs[fixed_count % len(gallery_imgs)] if gallery_imgs else default_fallback
            new_img_tag = img_tag.replace('<img', f'<img src="{fallback_url}"', 1)
            html = html.replace(img_tag, new_img_tag, 1)
            fixed_count += 1
            logger.info("   🔄 Added missing src to img tag")

        if fixed_count > 0:
            logger.info(f"✅ Fixed {fixed_count} broken/missing image URLs")
        else:
            logger.info("✅ All image URLs are valid")

        return html

    # ===================================================================
    # PRE-BUILT TEMPLATE SYSTEM
    # Instead of asking AI to generate HTML/CSS from scratch, we load
    # pre-built HTML templates and only use AI to generate text content.
    # ===================================================================

    def _load_template_html(self, template_filename: str) -> Optional[str]:
        """Load a pre-built HTML template file from app/templates/designs/."""
        template_dir = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "templates", "designs"
        )
        template_path = os.path.join(template_dir, template_filename)
        try:
            with open(template_path, "r", encoding="utf-8") as f:
                html = f.read()
            logger.info(f"📄 Loaded pre-built template: {template_filename} ({len(html)} chars)")
            return html
        except FileNotFoundError:
            logger.warning(f"⚠️ Pre-built template not found: {template_path}")
            return None
        except Exception as e:
            logger.error(f"❌ Failed to load template {template_filename}: {e}")
            return None

    async def _generate_content_only(
        self,
        business_name: str,
        description: str,
        phone: str,
        address: str,
        operating_hours: list,
        language: str = "ms",
        menu_items: list = None,
    ) -> Optional[dict]:
        """
        Ask AI to generate ONLY text content for the website, returned as JSON.
        The AI does NOT generate any HTML, CSS, or design — only copywriting.
        """
        lang_name = "Bahasa Malaysia" if language == "ms" else "English"

        # Build menu items context
        menu_context = ""
        if menu_items and len(menu_items) > 0:
            menu_lines = []
            for i, item in enumerate(menu_items):
                if isinstance(item, dict):
                    name = item.get("name", item.get("item_name", f"Item {i+1}"))
                    price = item.get("price", item.get("item_price", ""))
                    menu_lines.append(f"  - {name}: RM{price}")
                elif isinstance(item, str):
                    menu_lines.append(f"  - {item}")
            menu_context = "Menu items provided:\n" + "\n".join(menu_lines)
        else:
            menu_context = "No menu items provided. Generate 4-6 sample menu items appropriate for this business type."

        hours_context = ""
        if operating_hours and len(operating_hours) > 0:
            hours_lines = []
            for h in operating_hours:
                if isinstance(h, dict):
                    days = h.get("days", h.get("day", ""))
                    hrs = h.get("hours", h.get("time", ""))
                    hours_lines.append(f"  - {days}: {hrs}")
                elif isinstance(h, str):
                    hours_lines.append(f"  - {h}")
            hours_context = "Operating hours:\n" + "\n".join(hours_lines)
        else:
            hours_context = "No operating hours provided. Generate reasonable operating hours for this business type."

        prompt = f"""You are a professional copywriter. Generate website text content for this business.
Return ONLY valid JSON, no markdown code fences, no explanation.

Business Name: {business_name}
Business Description: {description}
Language: {lang_name}
Phone: {phone}
Address: {address}
{menu_context}
{hours_context}

Return this EXACT JSON structure:
{{
    "hero_title": "A catchy headline for the hero section (include business name)",
    "hero_description": "2-3 sentence engaging description for hero section",
    "tagline": "Short tagline for browser tab title (3-5 words)",
    "cta_primary_text": "Primary button text (e.g., Lihat Menu / View Menu)",
    "cta_secondary_text": "Secondary button text (e.g., Hubungi Kami / Contact Us)",
    "menu_section_title": "Menu section heading",
    "menu_section_description": "Short description for menu section",
    "menu_items": [
        {{
            "item_name": "Menu item name",
            "item_price": "price without RM prefix",
            "item_description": "Short appetizing description (1 sentence)"
        }}
    ],
    "about_title": "About section heading",
    "about_description": "2-3 paragraphs about the business, engaging and warm",
    "contact_title": "Contact section heading",
    "footer_description": "Short footer tagline",
    "operating_hours": [
        {{
            "days": "Day range (e.g., Isnin - Jumaat)",
            "hours": "Time range (e.g., 10:00 AM - 10:00 PM)"
        }}
    ]
}}

IMPORTANT RULES:
- Write ALL text in {lang_name}
- Be creative, professional, and appetizing
- Menu item descriptions should be short and enticing
- Use the EXACT business name provided: {business_name}
- If menu items were provided, use their exact names and prices
- Generate 4-6 menu items if none were provided
- Generate 2-3 operating hours entries if none were provided
"""

        # Try DeepSeek first, then Qwen as fallback
        response = await self._call_deepseek(prompt, temperature=0.3)
        if not response:
            logger.warning("⚠️ DeepSeek failed for content generation, trying Qwen...")
            response = await self._call_qwen(prompt, temperature=0.3)

        if not response:
            logger.error("❌ Both AIs failed to generate content")
            return None

        # Parse JSON from response
        try:
            # Clean response: remove markdown fences if present
            cleaned = response.strip()
            if cleaned.startswith("```"):
                # Remove first line with ```json and last line with ```
                lines = cleaned.split("\n")
                cleaned = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
            content = json.loads(cleaned)
            logger.info(f"✅ AI content generated: {len(content)} fields")
            return content
        except json.JSONDecodeError as e:
            logger.error(f"❌ Failed to parse AI content JSON: {e}")
            logger.error(f"   Response preview: {response[:300]}")
            # Try to extract JSON from the response
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                try:
                    content = json.loads(json_match.group())
                    logger.info(f"✅ Extracted JSON from response: {len(content)} fields")
                    return content
                except json.JSONDecodeError:
                    pass
            return None

    def _fill_template(self, template_html: str, content: dict) -> str:
        """
        Replace {{placeholder}} tokens in template HTML with content values.
        Handles simple string fields only (not loops).
        """
        result = template_html

        simple_fields = [
            'business_name', 'tagline', 'hero_title', 'hero_description',
            'cta_primary_text', 'cta_secondary_text', 'menu_section_title',
            'menu_section_description', 'about_title', 'about_description',
            'contact_title', 'whatsapp_number', 'phone_display', 'address',
            'footer_description',
            # Rendered HTML blocks (menu cards, operating hours)
            'menu_items_html', 'operating_hours_html',
            # Word explosion template variants
            'hero_title_words', 'hero_description_words',
            'menu_section_title_words', 'menu_section_description_words',
            'about_title_words', 'about_description_words',
        ]

        for field in simple_fields:
            value = content.get(field, '')
            if value:
                result = result.replace('{{' + field + '}}', str(value))

        # Safety net: remove any remaining {{placeholder}} tokens so they
        # never appear on the published site.
        result = re.sub(r'\{\{[a-zA-Z_]+\}\}', '', result)

        return result

    def _render_menu_card_html(self, item: dict, template_id: str, image_url: str = "") -> str:
        """Render a single menu item card HTML snippet matching the template's design."""
        name = item.get("item_name", item.get("name", ""))
        price = item.get("item_price", item.get("price", ""))
        desc = item.get("item_description", item.get("description", ""))

        # Determine card CSS classes based on template type
        # Dark templates
        dark_templates = [
            "aurora", "gradient-wave", "gradient_wave", "neon-grid", "neon_grid",
            "matrix-code", "matrix", "morphing-blob", "morphing_blob",
            "spotlight", "particle-globe", "particle_globe",
            "ghost-restaurant", "ghost", "neon_night", "elegance_dark",
            "ghost_restaurant",
        ]

        is_dark = any(t in (template_id or "").lower().replace(" ", "_").replace("-", "_")
                       for t in [x.replace("-", "_") for x in dark_templates])

        if is_dark:
            # Get color scheme from template
            if "aurora" in (template_id or ""):
                card_cls = "menu-card bg-[#0a0a2e]/80 backdrop-blur-xl border border-white/10 rounded-2xl overflow-hidden"
                price_cls = "text-[#34d399]"
                desc_cls = "text-[#8888bb]"
            elif "ghost" in (template_id or ""):
                card_cls = "ghost-card rounded-2xl overflow-hidden"
                price_cls = "text-[#00E5A0]"
                desc_cls = "text-[#8A8A8A]"
            elif "matrix" in (template_id or ""):
                card_cls = "matrix-card rounded-2xl overflow-hidden"
                price_cls = "text-[#00FF41]"
                desc_cls = "text-[#00FF41]/60"
            elif "morphing" in (template_id or "") or "spotlight" in (template_id or ""):
                card_cls = "menu-card bg-[#1A1A1A]/80 backdrop-blur-xl border border-white/10 rounded-2xl overflow-hidden"
                price_cls = "text-[#D4AF37]"
                desc_cls = "text-[#A0998C]"
            elif "particle" in (template_id or ""):
                card_cls = "menu-card rounded-2xl overflow-hidden"
                price_cls = "text-[#3B82F6]"
                desc_cls = "text-[#9CA3AF]"
            else:
                # neon_grid, gradient_wave, neon_night
                card_cls = "menu-card bg-[#111827]/80 backdrop-blur-xl border border-[#8B5CF6]/20 rounded-2xl overflow-hidden"
                price_cls = "text-[#8B5CF6]"
                desc_cls = "text-[#9CA3AF]"
        else:
            # Light templates
            if "floating" in (template_id or "") or "warm" in (template_id or ""):
                card_cls = "menu-card bg-white rounded-3xl shadow-md shadow-orange-900/5 border border-orange-100/50 overflow-hidden"
                price_cls = "text-[#EA580C]"
                desc_cls = "text-[#78716C]"
            elif "word" in (template_id or ""):
                card_cls = "menu-card bg-white rounded-2xl shadow-md shadow-orange-900/5 border border-[#E85D3A]/10 overflow-hidden"
                price_cls = "text-[#E85D3A]"
                desc_cls = "text-[#7A7A7A]"
            elif "parallax" in (template_id or "") or "fresh" in (template_id or ""):
                card_cls = "menu-card bg-white rounded-2xl shadow-lg shadow-black/5 border border-gray-100 overflow-hidden"
                price_cls = "text-[#16A34A]"
                desc_cls = "text-[#6B8068]"
            else:
                # default
                card_cls = "menu-card bg-white rounded-2xl shadow-lg shadow-black/5 border border-gray-100 overflow-hidden"
                price_cls = "text-[#3B82F6]"
                desc_cls = "text-[#64748B]"

        # Build image HTML if we have an image URL
        image_html = ""
        if image_url:
            image_html = f'''<div class="aspect-video overflow-hidden">
                        <img src="{image_url}" alt="{name}" class="w-full h-full object-cover">
                    </div>'''

        return f'''<div class="{card_cls}">
                    {image_html}
                    <div class="p-6">
                        <div class="flex justify-between items-start mb-3">
                            <h3 class="text-xl font-heading font-bold">{name}</h3>
                            <span class="{price_cls} font-bold text-lg">RM{price}</span>
                        </div>
                        <p class="{desc_cls}">{desc}</p>
                    </div>
                </div>'''

    def _render_operating_hours_html(self, hours: list, template_id: str) -> str:
        """Render operating hours list items matching the template's design."""
        if not hours:
            return ""

        dark_templates = [
            "aurora", "gradient-wave", "gradient_wave", "neon-grid", "neon_grid",
            "matrix-code", "matrix", "morphing-blob", "morphing_blob",
            "spotlight", "particle-globe", "particle_globe",
            "ghost-restaurant", "ghost", "neon_night", "elegance_dark",
            "ghost_restaurant",
        ]

        is_dark = any(t in (template_id or "").lower().replace(" ", "_").replace("-", "_")
                       for t in [x.replace("-", "_") for x in dark_templates])

        items_html = []
        for h in hours:
            if isinstance(h, dict):
                days = h.get("days", h.get("day", ""))
                hrs = h.get("hours", h.get("time", ""))
            elif isinstance(h, str):
                days = h
                hrs = ""
            else:
                continue

            if is_dark:
                if "aurora" in (template_id or ""):
                    accent = "text-[#34d399]"
                elif "ghost" in (template_id or ""):
                    accent = "text-[#00E5A0]"
                elif "matrix" in (template_id or ""):
                    accent = "text-[#00FF41]"
                elif "morphing" in (template_id or "") or "spotlight" in (template_id or ""):
                    accent = "text-[#D4AF37]"
                elif "particle" in (template_id or ""):
                    accent = "text-[#3B82F6]"
                else:
                    accent = "text-[#8B5CF6]"
                border = "border-white/10"
            else:
                if "floating" in (template_id or "") or "warm" in (template_id or ""):
                    accent = "text-[#EA580C]"
                elif "word" in (template_id or ""):
                    accent = "text-[#E85D3A]"
                elif "parallax" in (template_id or "") or "fresh" in (template_id or ""):
                    accent = "text-[#16A34A]"
                else:
                    accent = "text-[#3B82F6]"
                border = "border-gray-200"

            items_html.append(
                f'<li class="flex justify-between items-center pb-4 border-b {border}">'
                f'<span class="text-lg">{days}</span>'
                f'<span class="{accent} font-bold">{hrs}</span>'
                f'</li>'
            )

        return "\n                            ".join(items_html)

    def _wrap_words_fly(self, text: str) -> str:
        """Wrap each word in <span class='fly-word'> for the word explosion template."""
        if not text:
            return ""
        words = text.split()
        return " ".join(f'<span class="fly-word">{w}</span>' for w in words)

    async def _generate_website_from_template(
        self,
        request: WebsiteGenerationRequest,
        template_id: str,
        template_filename: str,
        image_choice: str = "upload",
        progress_callback: Optional[Callable[[int, str], Awaitable[None]]] = None,
    ) -> Optional[str]:
        """
        Generate a website by filling a pre-built HTML template with AI-generated content.
        The AI only generates text content (copywriting), NOT HTML/CSS/design.
        """
        import time
        start_time = time.time()

        async def update_progress(percent: int, message: str):
            if progress_callback:
                try:
                    await progress_callback(percent, message)
                except Exception as e:
                    logger.warning(f"Progress callback failed: {e}")

        logger.info("=" * 80)
        logger.info("📄 PRE-BUILT TEMPLATE GENERATION PIPELINE")
        logger.info(f"   Template: {template_id} -> {template_filename}")
        logger.info(f"   Business: {request.business_name}")
        logger.info("=" * 80)

        # Step 1: Load the pre-built template HTML
        await update_progress(30, "Loading template design")
        template_html = self._load_template_html(template_filename)
        if not template_html:
            logger.warning(f"⚠️ Could not load template {template_filename}, falling back to AI generation")
            return None

        # Step 2: Generate content-only with AI
        await update_progress(40, "AI generating text content")
        language = request.language.value if hasattr(request, 'language') and request.language else "ms"

        # Extract phone number
        wa_raw = request.whatsapp_number or "60123456789"
        wa_digits = re.sub(r"\D", "", str(wa_raw))
        if wa_digits.startswith("0"):
            wa_digits = "6" + wa_digits
        elif wa_digits.startswith("1"):
            wa_digits = "60" + wa_digits
        if not wa_digits:
            wa_digits = "60123456789"

        # Build menu items from uploaded images if available
        menu_items_input = []
        if request.uploaded_images:
            for img in request.uploaded_images:
                if isinstance(img, dict):
                    name = img.get("name", "")
                    if name and name.lower() != "hero image" and "hero" not in name.lower():
                        menu_items_input.append({"name": name, "price": ""})

        content = await self._generate_content_only(
            business_name=request.business_name,
            description=request.description,
            phone=wa_raw,
            address=request.location_address or "",
            operating_hours=[],
            language=language,
            menu_items=menu_items_input if menu_items_input else None,
        )

        if not content:
            logger.warning("⚠️ AI content generation failed, falling back to AI HTML generation")
            return None

        await update_progress(60, "Filling template with content")

        # Step 3: Add non-AI fields to content
        content['business_name'] = request.business_name
        content['whatsapp_number'] = wa_digits
        content['phone_display'] = wa_raw
        content['address'] = request.location_address or content.get('address', '')

        # Step 4: Build image URLs
        image_urls = {}
        if image_choice != "none" and request.uploaded_images and len(request.uploaded_images) > 0:
            def get_image_url(img):
                if isinstance(img, dict):
                    return img.get('url', img.get('URL', ''))
                return str(img)

            def get_image_name(img):
                if isinstance(img, dict):
                    return img.get('name', '')
                return ''

            gallery_start_index = 0
            first_name = (get_image_name(request.uploaded_images[0]) or "").strip().lower()
            if first_name == "hero image" or "hero" in first_name:
                image_urls["hero"] = get_image_url(request.uploaded_images[0])
                gallery_start_index = 1

            for i in range(1, 5):
                idx = gallery_start_index + (i - 1)
                if idx < len(request.uploaded_images):
                    image_urls[f"gallery{i}"] = get_image_url(request.uploaded_images[idx])

        # Step 5: Render menu items HTML
        menu_items = content.get('menu_items', [])
        menu_cards = []
        for i, item in enumerate(menu_items):
            img_url = image_urls.get(f"gallery{i+1}", "")
            card_html = self._render_menu_card_html(item, template_id, img_url)
            menu_cards.append(card_html)

        content['menu_items_html'] = "\n                ".join(menu_cards)

        # Step 6: Render operating hours HTML
        op_hours = content.get('operating_hours', [])
        content['operating_hours_html'] = self._render_operating_hours_html(op_hours, template_id)

        # Step 7: Handle word explosion special placeholders
        if "word" in (template_id or "").lower() or "word_explosion" in (template_filename or "").lower():
            content['hero_title_words'] = self._wrap_words_fly(content.get('hero_title', ''))
            content['hero_description_words'] = self._wrap_words_fly(content.get('hero_description', ''))
            content['menu_section_title_words'] = self._wrap_words_fly(content.get('menu_section_title', ''))
            content['menu_section_description_words'] = self._wrap_words_fly(content.get('menu_section_description', ''))
            content['about_title_words'] = self._wrap_words_fly(content.get('about_title', ''))
            content['about_description_words'] = self._wrap_words_fly(content.get('about_description', ''))

        # Step 8: Fill template with content
        final_html = self._fill_template(template_html, content)

        await update_progress(80, "Finalizing website")

        total_time = time.time() - start_time
        logger.info("✅ Template generation complete")
        logger.info(f"   Final size: {len(final_html)} characters")
        logger.info(f"   ⏱️  Total time: {total_time:.1f}s")

        return final_html

    # ==================== FREE AUTO-FILL (missing image slots) ====================

    def _resolve_autofill_image_cap(self, max_ai_images: Optional[int]) -> int:
        """Effective AI-image cap for the auto-fill pass.

        Caller quota None/absent → no plan constraint applies → the
        free-by-default budget (FREE_AI_IMAGES_PER_SITE, default 6). An
        EXPLICIT zero (or negative) means the plan system said no — quota
        exhausted this month, or the plan forbids AI images — so auto-fill
        generates NOTHING; the free default must never silently override
        that decision. A positive quota lower than the free budget still
        wins (min). Plan quota COMPUTATION (websites.py) is untouched: this
        only interprets the value it is handed.
        """
        free_default = free_ai_images_per_site()
        if max_ai_images is None:
            return free_default
        return min(max(0, max_ai_images), free_default)

    # Keywords marking creative-services businesses (photography, videography,
    # event coverage) whose sellable output is the WORK itself — a wedding
    # moment, a portrait session — not a physical good on a shelf.
    _CREATIVE_BUSINESS_KEYWORDS = (
        "photograph",      # photography / photographer
        "fotografi",
        "jurugambar",
        "videograf",       # videografi / videographer
        "videography",
        "cinematograph",
        "photo booth",
        "event coverage",
    )

    def _autofill_prompt_category(self, description: str) -> str:
        """Prompt-template category for auto-fill images.

        Returns 'food' | 'creative' | 'retail' | 'generic'. The subject of
        every auto-fill image must be the business's OUTPUT — the dish, the
        shot, the product — never its premises or equipment, so the template
        set is chosen by what the business produces.
        """
        if self._is_food_business(description):
            return "food"
        low = (description or "").lower()
        if any(k in low for k in self._CREATIVE_BUSINESS_KEYWORDS):
            return "creative"
        # Goods-selling types (and undetected businesses, whose gallery names
        # come from the product-category extractor) get clean product shots;
        # service types fall through to the generic subject-first template.
        if detect_business_type(description) in ("clothing", "bakery", "general"):
            return "retail"
        return "generic"

    def _autofill_hero_prompt(self, category: str, biz_type: str) -> str:
        """Hero banner prompt per category.

        Always a lively showcase of the business's output — never an empty
        premises or equipment shot. (The food hero keeps the established
        stall-ambience prompt: it is full of people and food, not empty.)
        """
        if category == "food":
            return (
                "Malaysian restaurant interior, food stall with hanging menu, "
                "authentic atmosphere, people eating, warm lighting, food photography"
            )
        if category == "creative":
            return (
                f"Artistic showcase of {biz_type} work, cinematic silhouette "
                f"composition at golden hour, elegant venue backdrop, "
                f"professional photography"
            )
        if category == "retail":
            return (
                f"Attractive arrangement of {biz_type} products, lifestyle "
                f"commercial photography, warm inviting lighting, clean modern styling"
            )
        return (
            f"Professional photography showcasing {biz_type} work in action, "
            f"warm lighting, high quality"
        )

    def _autofill_item_prompt(self, category: str, name: str, biz_type: str) -> str:
        """Per-item prompt: the item itself is ALWAYS the subject.

        Never prompts for studios, equipment, or empty premises — those can
        only appear when the item name itself names them (the name IS the
        subject, verbatim).

        food returns the raw item name: _generate_image(food=True) maps it
        through _get_malaysian_prompt, which yields a curated appetizing
        plated-dish prompt for known dishes and a food-photography fallback
        otherwise.
        """
        if category == "food":
            return name
        if category == "creative":
            # The type of work named by the item is the subject; favour
            # artistic compositions (silhouettes, candid details, venue)
            # over close-up faces.
            return (
                f"{name}, artistic professional photography, cinematic "
                f"composition, silhouette and candid detail shots, beautiful "
                f"venue backdrop, golden hour lighting, emotional storytelling"
            )
        if category == "retail":
            return (
                f"Professional product photography of {name}, clean background, "
                f"soft studio lighting, high detail, commercial product shot"
            )
        return f"Professional photography of {name}, {biz_type}, high quality, sharp focus"

    async def _autofill_missing_images(
        self,
        request: WebsiteGenerationRequest,
        image_urls: Dict,
        max_ai_images: Optional[int] = None,
        zai_phase: Optional[Dict] = None,
    ) -> int:
        """Auto-fill hero/gallery slots that uploads didn't cover (free-by-default).

        Mutates image_urls in place: the hero slot and any empty gallery1..4
        slots get AI-generated images via _generate_image (so IMAGE_PROVIDER
        selection + Stability fallback apply), one image per REAL menu/product
        item extracted from the merchant's own description — items are never
        invented (the extractors fall back to safe generic category labels,
        not fabricated products). Generation is hard-capped by
        _resolve_autofill_image_cap. A failed generation falls back to the
        Bug-2 stock-image pool so the slot never ships blank; pool-filled
        slots do NOT count toward the returned AI-image count.

        Returns the number of images actually AI-generated (for usage
        accounting upstream).
        """
        hero_missing = not image_urls.get("hero")
        missing_slots = [i for i in range(1, 5) if not image_urls.get(f"gallery{i}")]
        if not hero_missing and not missing_slots:
            logger.info("🖼️ All image slots covered by uploads — no auto-fill needed")
            return 0

        cap = self._resolve_autofill_image_cap(max_ai_images)
        if cap <= 0:
            logger.info("🚫 Auto-fill image cap is 0 — skipping AI image auto-fill")
            return 0

        category = self._autofill_prompt_category(request.description)
        is_food = category == "food"

        # Item names already covered by uploads — never generate a duplicate
        # card for something the merchant photographed themselves.
        uploaded_names = set()
        for i in range(1, 5):
            _n = (image_urls.get(f"gallery{i}_name") or "").strip().lower()
            if _n:
                uploaded_names.add(_n)

        def _covered(name: str) -> bool:
            low = name.strip().lower()
            return any(low == u or low in u or u in low for u in uploaded_names)

        # STEP 0: real item/category names for the missing gallery slots so
        # names and images stay paired (same contract as the original
        # no-upload path).
        slot_names: List[str] = []
        if missing_slots:
            if is_food:
                logger.info("🍽️ Auto-fill STEP 0: extracting menu item names...")
                extracted = await self.extract_menu_item_names(
                    request.description, n=4, business_name=request.business_name
                )
            else:
                logger.info("🛍️ Auto-fill STEP 0: extracting product category names...")
                extracted = await self.extract_product_category_names(
                    request.description, n=4, business_name=request.business_name
                )
            slot_names = [n for n in (extracted or []) if n and not _covered(n)]
            logger.info(
                f"{'🍽️' if is_food else '🛍️'} Auto-fill items: {', '.join(slot_names) or '(none)'}"
            )

        # Human-readable business type for grounding the prompts; fall back
        # to a short description slice when detection is generic.
        _biz_type = detect_business_type(request.description)
        if _biz_type == "general":
            _biz_type = request.description[:50]

        # Hero is a banner/showcase shot — NEVER a menu/product card, and
        # never empty premises or equipment (see _autofill_hero_prompt).
        hero_prompt = self._autofill_hero_prompt(category, _biz_type)

        # Work list: hero first, then one image per (missing slot, real item
        # name) pair — truncated to the cap, so the hero always wins the
        # budget and later items are the ones dropped. Item prompts always
        # make the item itself the subject (see _autofill_item_prompt).
        work: List[Tuple[str, Optional[str], str]] = []  # (slot_key, item_name, prompt)
        if hero_missing:
            work.append(("hero", None, hero_prompt))
        for slot_no, name in zip(missing_slots, slot_names):
            work.append(
                (f"gallery{slot_no}", name, self._autofill_item_prompt(category, name, _biz_type))
            )

        if len(work) > cap:
            logger.info(f"✂️ Auto-fill capped at {cap} of {len(work)} missing image slot(s)")
            work = work[:cap]
        if not work:
            return 0

        logger.info(
            f"🎨 Auto-filling {len(work)} image slot(s) in PARALLEL "
            f"[provider={image_provider()}, category={category}, cap={cap}]: "
            + ", ".join(slot for slot, _, _ in work)
        )

        # gather still fires the coroutines together, but with provider=zai
        # the dispatcher's lock serializes the Z.ai requests (concurrency 1
        # with spacing) — only Stability calls actually run in parallel.
        _gen_started = time.monotonic()
        results = await asyncio.gather(
            *[self._generate_image(_p, food=is_food, zai_phase=zai_phase) for _, _, _p in work],
            return_exceptions=True,
        )
        _gen_elapsed = time.monotonic() - _gen_started

        generated = 0
        for (slot_key, item_name, _p), result in zip(work, results):
            url = result if (result and not isinstance(result, Exception)) else None
            if url:
                generated += 1
            else:
                # Bug-2 pool fallback so a provider failure (rate limit, 500,
                # timeout) doesn't leave the slot empty.
                try:
                    url = self.get_matching_image(
                        item_name or _p, business_type=request.description
                    )
                    logger.info(f"   🔄 Auto-fill pool fallback for {slot_key}: {url[:60]}...")
                except Exception as fb_err:
                    logger.warning(f"   ⚠️ Auto-fill pool fallback failed for {slot_key}: {fb_err}")
                    url = None
            if url:
                image_urls[slot_key] = url
                if item_name:
                    # Same key contract as before: gallery{i}_name pairs the
                    # slot's image with its real item name for the HTML prompt.
                    image_urls[f"{slot_key}_name"] = item_name

        logger.info(
            f"🖼️ Auto-fill complete in {_gen_elapsed:.1f}s: {generated}/{len(work)} "
            f"AI-generated (cap={cap}); {len(image_urls)} image URL(s) ready for HTML generation"
        )
        return generated

    async def generate_website(
        self,
        request: WebsiteGenerationRequest,
        style: Optional[str] = None,
        image_choice: str = "upload",  # NEW: none, upload, or ai
        progress_callback: Optional[Callable[[int, str], Awaitable[None]]] = None,  # NEW: callback for progress updates
        max_ai_images: Optional[int] = None  # NEW: hard cap on AI images (caller's remaining quota)
    ) -> AIGenerationResponse:
        """Generate website with Stability AI + Cloudinary + DeepSeek + Qwen

        Args:
            progress_callback: Optional async callback(progress_percent, status_message)
            max_ai_images: Optional hard cap on the number of AI images this build
                may generate (the user's remaining AI-image quota). For the
                hero/gallery AUTO-FILL pass, an absent quota (None) falls back
                to the free-by-default budget (FREE_AI_IMAGES_PER_SITE,
                default 6); an EXPLICIT zero disables auto-fill (the plan said
                no); a lower positive quota still wins — see
                _resolve_autofill_image_cap. For the food-image post-pass, None
                still means no cap; generation there is capped to whatever
                budget remains after the auto-fill, so a single build never
                overshoots the plan limit.
        """

        import time
        start_time = time.time()

        # Step-by-step timing breakdown — instrumented to identify the bottleneck
        # behind the 651s generations seen in production (see Bug 3).
        step_timings: Dict[str, float] = {}

        # Helper to safely call progress callback
        async def update_progress(percent: int, message: str):
            if progress_callback:
                try:
                    await progress_callback(percent, message)
                except Exception as e:
                    logger.warning(f"Progress callback failed: {e}")

        await update_progress(25, "Starting website generation")

        logger.info("=" * 80)
        logger.info("🌐 WEBSITE GENERATION - FULL AI PIPELINE")
        logger.info(f"   Business: {request.business_name}")
        logger.info(f"   Style: {style or 'modern'}")
        logger.info(f"   🖼️ Image Choice: {image_choice}")
        logger.info(f"   User Images: {len(request.uploaded_images) if request.uploaded_images else 0}")
        logger.info(f"   ⏰ Start Time: {time.strftime('%H:%M:%S')}")
        logger.info("=" * 80)

        # Check image_choice - skip ALL image generation if "none"
        image_urls = {}
        ai_images_generated = 0  # Track how many AI images were successfully generated
        # One Z.ai image phase per build, shared by the auto-fill pass and the
        # food-image post-pass, so their combined Z.ai time is bounded by
        # ZAI_IMAGE_PHASE_BUDGET_SECONDS. No-op when IMAGE_PROVIDER=stability.
        _zai_image_phase = self._new_zai_image_phase()

        if image_choice == "none":
            logger.info("🚫 Image choice='none' - SKIPPING ALL image generation")
            # Don't generate or use any images
            pass
        elif request.uploaded_images and len(request.uploaded_images) > 0:
            # User uploaded images - use them directly, skip AI generation
            logger.info(f"☁️ User uploaded {len(request.uploaded_images)} images - SKIPPING AI image generation")
            logger.info("   Using user-uploaded Cloudinary URLs...")

            # Helper function to extract URL from image (can be string or dict with 'url' key)
            def get_image_url(img):
                if isinstance(img, dict):
                    return img.get('url', img.get('URL', ''))
                return str(img)

            # Helper function to extract name from image metadata
            def get_image_name(img):
                if isinstance(img, dict):
                    return img.get('name', '')
                return ''

            # Map uploaded images to expected keys
            # IMPORTANT: Only treat an uploaded image as HERO if explicitly named as hero.
            gallery_start_index = 0
            first_name = (get_image_name(request.uploaded_images[0]) or "").strip().lower()
            if first_name == "hero image" or "hero" in first_name:
                image_urls["hero"] = get_image_url(request.uploaded_images[0])
                gallery_start_index = 1

            # Gallery images start after hero (if present)
            for i in range(1, 5):
                idx = gallery_start_index + (i - 1)
                if idx < len(request.uploaded_images):
                    image_urls[f"gallery{i}"] = get_image_url(request.uploaded_images[idx])
                    image_urls[f"gallery{i}_name"] = get_image_name(request.uploaded_images[idx])

            logger.info(f"   ✅ Using {len(image_urls)} user-uploaded images with metadata")
            await update_progress(35, "Processing uploaded images")

            # AUTO-FILL (free-by-default): a merchant who uploaded FEWER
            # images than the layout needs gets the remaining hero/gallery
            # slots AI-generated instead of shipping empty. Runs BEFORE the
            # has_images decision downstream so a partially-covered site
            # still takes the photo-slots prompt branch.
            with _timed_step("stability_images", step_timings):
                ai_images_generated = await self._autofill_missing_images(
                    request, image_urls, max_ai_images, zai_phase=_zai_image_phase
                )
            if ai_images_generated:
                await update_progress(45, "AI images generated")

        else:
            # No user images — AUTO-FILL every slot (free-by-default): 1 hero
            # + 1 per real menu/product item, capped by FREE_AI_IMAGES_PER_SITE
            # (or a lower caller quota). Runs BEFORE the has_images decision so
            # zero-upload merchants get generated images and the photo-slots
            # prompt branch; the no-photo typography branch remains the final
            # fallback when image generation fails entirely.
            logger.info(
                f"🎨 No user images - auto-filling with AI-generated images... "
                f"[{time.time() - start_time:.1f}s elapsed]"
            )

            with _timed_step("stability_images", step_timings):
                ai_images_generated = await self._autofill_missing_images(
                    request, image_urls, max_ai_images, zai_phase=_zai_image_phase
                )

            await update_progress(45, "AI images generated")

        # ===================================================================
        # PRE-BUILT TEMPLATE PATH: If user selected a template that has a
        # pre-built HTML file, use the template injection pipeline instead
        # of asking the AI to generate HTML/CSS from scratch.
        # ===================================================================
        _tpl_id = getattr(request, "template_id", None)
        if _tpl_id:
            try:
                from app.services.template_gallery import get_prebuilt_template_filename
                _prebuilt_file = get_prebuilt_template_filename(_tpl_id)
                if _prebuilt_file:
                    logger.info(f"📄 Pre-built template found for '{_tpl_id}': {_prebuilt_file}")
                    with _timed_step("template_pipeline", step_timings):
                        template_html = await self._generate_website_from_template(
                            request=request,
                            template_id=_tpl_id,
                            template_filename=_prebuilt_file,
                            image_choice=image_choice,
                            progress_callback=progress_callback,
                        )
                    if template_html:
                        # Post-processing: inject images if needed
                        if not (request.uploaded_images and len(request.uploaded_images) > 0):
                            with _timed_step("ai_food_images", step_timings):
                                _food_budget = (
                                    None if max_ai_images is None
                                    else max(0, max_ai_images - ai_images_generated)
                                )
                                template_html, food_images_count = await self._generate_ai_food_images(
                                    template_html,
                                    max_images=_food_budget,
                                    zai_phase=_zai_image_phase,
                                )
                                ai_images_generated += food_images_count
                        with _timed_step("final_cleanup", step_timings):
                            template_html = self._fix_broken_image_urls(template_html, request.description)

                        total_time = time.time() - start_time
                        logger.info(f"✅ PRE-BUILT TEMPLATE PIPELINE COMPLETE in {total_time:.1f}s")
                        self._log_timing_breakdown(step_timings, total_time)

                        await update_progress(90, "Finalizing website")

                        if request.include_ecommerce:
                            integrations = ["Delivery System (to be injected)", "WhatsApp Contact", "Mobile Responsive", "Cloudinary Images"]
                        else:
                            integrations = ["WhatsApp", "Contact Form", "Mobile Responsive", "Cloudinary Images"]

                        return AIGenerationResponse(
                            html_content=template_html,
                            css_content=None,
                            js_content=None,
                            meta_title=request.business_name,
                            meta_description=f"{request.business_name} - {request.description[:150]}",
                            sections=["Header", "Hero", "About", "Services", "Gallery", "Contact", "Footer"],
                            integrations_included=integrations,
                            ai_images_count=ai_images_generated,
                            step_timings=step_timings,
                        )
                    else:
                        logger.warning(f"⚠️ Pre-built template pipeline failed for '{_tpl_id}', falling back to AI generation")
            except Exception as e:
                logger.warning(f"⚠️ Pre-built template check failed: {e}, falling back to AI generation")

        # ===================================================================
        # FALLBACK: Original AI generation pipeline (when no pre-built template
        # is available or the template pipeline failed)
        # ===================================================================

        # Build prompt WITH image URLs (or NO images if image_choice='none')
        await update_progress(50, "Generating website HTML")
        logger.info(f"🔷 STEP 2: DeepSeek generating HTML... [{time.time() - start_time:.1f}s elapsed]")
        _prompt_build_started = time.time()
        # Get language from request (default to "ms" for Bahasa Malaysia)
        language = request.language.value if hasattr(request, 'language') and request.language else "ms"
        logger.info(f"   Language: {language}")
        # Get color_mode from request (default to "light")
        color_mode = getattr(request, 'color_mode', 'light') or 'light'
        if color_mode not in ('light', 'dark'):
            color_mode = 'light'

        # CRITICAL: Override color_mode based on selected template's color_mode
        # Without this, a dark template like "matrix-code" gets a light DesignSystem palette
        if _tpl_id:
            try:
                from app.services.template_gallery import TEMPLATES, ANIMATED_TO_DESIGN_MAP
                _design_key = _tpl_id if _tpl_id in TEMPLATES else ANIMATED_TO_DESIGN_MAP.get(_tpl_id)
                _tpl_def = TEMPLATES.get(_design_key) if _design_key else None
                if _tpl_def and _tpl_def.get("color_mode"):
                    color_mode = _tpl_def["color_mode"]
                    logger.info(f"🎨 Template '{_tpl_id}' overrides color_mode to '{color_mode}'")
            except Exception as e:
                logger.warning(f"⚠️ Failed to read template color_mode: {e}")

        prompt = self._build_strict_prompt(
            request.business_name,
            request.description,
            style or "modern",
            request.uploaded_images,
            language,
            whatsapp_number=request.whatsapp_number,
            location_address=request.location_address,
            image_choice=image_choice,  # CRITICAL: Pass image_choice to prompt builder
            images=image_urls,  # CRITICAL: feed generated hero+gallery URLs into the body
            include_ecommerce=request.include_ecommerce,  # CRITICAL: Pass delivery mode flag
            color_mode=color_mode,
            include_whatsapp=request.include_whatsapp,
            include_maps=request.include_maps,
        )

        # Add image URLs to prompt with STRONG emphasis.
        # gallery_count is logged right before the AI call (below) so prod
        # shows how many gallery URLs were actually wired into the prompt.
        gallery_count = 0
        if image_urls:
            # Label wording is conditional on business type (decision 2): food
            # businesses keep "Dish/Menu"; non-food shops use "Product". The
            # food-path strings below are byte-identical to the previous code so
            # food sites are unchanged.
            _is_food_biz = self._is_food_business(request.description)
            item_label = "Dish" if _is_food_biz else "Product"
            section_label = "MENU ITEMS" if _is_food_biz else "PRODUCT ITEMS"
            card_label = "menu card" if _is_food_biz else "product card"
            # Build gallery section with item names
            gallery_items = []
            dish_names_list = []
            menu_items_structured = []

            for i in range(1, 5):
                key = f'gallery{i}'
                name_key = f'gallery{i}_name'
                if key in image_urls:
                    dish_name = image_urls.get(name_key, '')
                    if dish_name:
                        gallery_items.append(f"- Product/Gallery image {i}: {image_urls[key]} ({item_label}: {dish_name})")
                        dish_names_list.append(dish_name)
                        menu_items_structured.append(f"""ITEM {i}:
- Image URL: {image_urls[key]}
- Title: "{dish_name}" (COPY EXACTLY - DO NOT MODIFY)
- Generate description in Malay based on the title""")
                    else:
                        gallery_items.append(f"- Product/Gallery image {i}: {image_urls[key]}")

            gallery_count = len(gallery_items)

            # Build structured items section (wording conditional on business type)
            menu_items_section = ""
            if menu_items_structured:
                if _is_food_biz:
                    _prefix_rule = '3. DO NOT add prefixes like "Nasi Kandar" if not in the original title'
                    _examples = (
                        '❌ WRONG: Title is "Ayam Penyet" → AI writes <h3>Nasi Kandar Ayam Goreng</h3>\n'
                        '✅ CORRECT: Title is "Ayam Penyet" → AI writes <h3>Ayam Penyet</h3>\n\n'
                        '❌ WRONG: Title is "Mee Goreng Mamak" → AI writes <h3>Nasi Kandar Ikan Bakar</h3>\n'
                        '✅ CORRECT: Title is "Mee Goreng Mamak" → AI writes <h3>Mee Goreng Mamak</h3>'
                    )
                else:
                    _prefix_rule = '3. DO NOT add prefixes or swap the category for a different product type'
                    _examples = (
                        '❌ WRONG: Title is "Mainan Edukatif" → AI writes <h3>Action Figures</h3>\n'
                        '✅ CORRECT: Title is "Mainan Edukatif" → AI writes <h3>Mainan Edukatif</h3>\n\n'
                        '❌ WRONG: Title is "Blok Binaan" → AI writes <h3>Mainan Lembut</h3>\n'
                        '✅ CORRECT: Title is "Blok Binaan" → AI writes <h3>Blok Binaan</h3>'
                    )
                menu_items_section = f"""

{section_label} - USE EXACTLY AS SPECIFIED:

{chr(10).join(menu_items_structured)}

CRITICAL RULES:
1. The HTML <h3> for each {card_label} MUST contain the EXACT title text specified above
2. DO NOT modify, translate, or change the title in any way
{_prefix_rule}
4. ONLY generate the description in Malay - the title stays EXACTLY as written
5. Copy-paste the title EXACTLY into your HTML <h3> tags

EXAMPLES:
{_examples}
"""

            # Explicit gallery block (Option A): list EVERY gallery/product
            # slot URL — whatever _slot_image() put there, real Cloudinary OR
            # pool fallback — so the model can never silently drop a slot to a
            # CSS placeholder. Emitted even with no dish names (the
            # AI-generation path), which is exactly the case that previously
            # lost all four gallery images.
            gallery_section = ""
            if gallery_items:
                gallery_section = (
                    "GALLERY/PRODUCT IMAGES — USE THESE EXACT URLS "
                    "(one per gallery/product card, in order):\n"
                    + "\n".join(gallery_items)
                )

            image_instructions = f"""
USE THESE EXACT IMAGE URLS IN THE HTML:
- Hero/Banner image: {image_urls.get('hero', 'generate appropriate image')}
{gallery_section}
{menu_items_section}

IMPORTANT INSTRUCTIONS:
1. Use these EXACT URLs in the img src attributes. Do NOT use placeholder or Unsplash URLs.
2. Every gallery/product card MUST render an <img> whose src is one of the GALLERY/PRODUCT IMAGE URLs above, used in the order given. Do NOT replace them with CSS gradients, icons, emojis, or placeholder divs.
3. Create EXACTLY {gallery_count} product/menu card(s) - one per GALLERY/PRODUCT IMAGE above. Do NOT invent extra cards, and do NOT reuse/duplicate an image across multiple cards.
4. Do NOT create any card for ambience, interior, atmosphere, decor, or storefront. The hero/banner image is for the page header ONLY - never use it as a product/menu card (e.g. no "Suasana Kedai" card).
5. Use the EXACT menu item titles shown above - DO NOT modify them, and do NOT append the business name or location to a title.
6. Write compelling descriptions in Malay for each dish, but keep the dish NAME/TITLE exactly as provided.
7. Make sure ALL images with URLs are displayed in the menu/gallery section.
8. Gallery/product card image areas MUST all use the IDENTICAL size classes `w-full aspect-[4/3] object-cover` — never per-card pixel heights (no h-48/h-56/h-60/h-64/h-72) — so the grid stays even on mobile (375px) and desktop.
9. If gallery cards show a small category/label tag, every tag MUST be distinct — never repeat the same label (e.g. two "Color" tags) unless there are genuinely more cards than distinct categories.
"""

            prompt += image_instructions

        # Template Gallery: inject design tokens if a template was selected
        # _tpl_id was already resolved above (before _build_strict_prompt)
        if _tpl_id:
            try:
                from app.services.template_gallery import get_template_prompt_injection
                _tpl_injection = get_template_prompt_injection(_tpl_id)
                if _tpl_injection:
                    prompt += "\n\nCRITICAL — OVERRIDE ALL DEFAULT DESIGN INSTRUCTIONS ABOVE.\nThe user selected a specific template. You MUST follow the template design system below.\nIGNORE any conflicting colors, fonts, or styles from earlier in this prompt.\n"
                    prompt += _tpl_injection
                    logger.info(f"🎨 Template gallery: injected design for '{_tpl_id}'")
                else:
                    logger.warning(f"⚠️ Template '{_tpl_id}' returned empty injection")
            except Exception as _tpl_err:
                logger.warning(f"⚠️ Template injection failed: {_tpl_err}")

        step_timings["prompt_build"] = round(time.time() - _prompt_build_started, 3)
        logger.info(f"⏱️  prompt_build: {step_timings['prompt_build']:.2f}s")

        # Visibility: how many image URLs were actually wired into the prompt.
        # If gallery drops below 4 here, the model never saw those slots.
        logger.info(
            f"🖼️ Image URLs wired into prompt: "
            f"hero={'yes' if image_urls.get('hero') else 'no'} gallery={gallery_count}/4"
        )

        await update_progress(55, "Calling AI to generate HTML")
        # Track truncation flags across the main AI call so they can be persisted
        # on generation_jobs (see Bug 1 fix).
        truncation_flags: Dict = {
            "was_truncated": False,
            "truncation_retries": 0,
            "needs_manual_review": False,
            "unclosed_tags": [],
        }

        with _timed_step("ai_html_generation", step_timings):
            # API-boundary truncation flag from the DeepSeek call.
            api_truncated_provider: Optional[str] = None
            api_finish_reason: Optional[str] = None

            # GLM (Z.ai) primary path — strictly PREPENDED to the DeepSeek
            # path below, gated by USE_GLM_FOR_HTML (ships dark). On ANY GLM
            # failure — no key, HTTP error, empty content, non-HTML output,
            # API-boundary truncation, or timeout — html_raw stays None and
            # the DeepSeek path below runs completely unchanged. Flipping the
            # env flag off restores pure-DeepSeek behaviour with no deploy.
            html_raw = None
            if USE_GLM_FOR_HTML and self.zai_api_key:
                # Image availability picks GLM's prompt mode up front (GLM is
                # single-shot): with URLs, the PHOTO_SLOT contract; with none,
                # the no-photo typography-led instruction — otherwise empty
                # slots become grey fallback blocks downstream.
                _glm_image_urls = self._ordered_prompt_image_urls(image_urls)
                try:
                    html_raw = await asyncio.wait_for(
                        self._call_glm(prompt, has_images=bool(_glm_image_urls)),
                        timeout=AI_GLM_TIMEOUT_SECONDS,
                    )
                except asyncio.TimeoutError:
                    logger.error(
                        f"⏰ GLM timed out (budget={AI_GLM_TIMEOUT_SECONDS}s) "
                        f"— falling back to DeepSeek"
                    )
                    html_raw = None
                if html_raw and self._last_api_call.get("truncated"):
                    logger.error("🚨 GLM output truncated — discarding, falling back to DeepSeek")
                    html_raw = None
                if html_raw and "<" not in html_raw:
                    logger.error("🟣 GLM returned non-HTML output — discarding, falling back to DeepSeek")
                    html_raw = None
                if html_raw:
                    # Premium design critique loop (PREMIUM_DESIGN_LOOP, ships
                    # dark): one DeepSeek review + at most one GLM revision.
                    # Runs before PHOTO_SLOT binding so a revision keeps the
                    # slot contract; no-op (zero calls) with the flag off.
                    html_raw = await self._run_premium_design_loop(
                        html_raw, has_images=bool(_glm_image_urls)
                    )
                    # Bind PHOTO_SLOT_N tokens to the real image URLs at the
                    # same boundary where the DeepSeek pipeline's exact-URL
                    # contract is enforced (before _extract_html/validation).
                    # No-op in no-photo mode (no tokens to replace).
                    html_raw = self._replace_photo_slots(html_raw, _glm_image_urls)
                    logger.info("🟣 GLM primary path succeeded — skipping DeepSeek")

            # DeepSeek primary path — DeepSeek-only as of the
            # deepseek-only-no-qwen branch. Bounded by
            # AI_PRIMARY_TIMEOUT_SECONDS so a hung provider doesn't burn
            # the entire endpoint budget. On timeout we raise
            # asyncio.TimeoutError straight up; the endpoint's existing
            # handler turns that into the user-facing "AI generation
            # timed out" message.
            if not html_raw:
                html_raw = await asyncio.wait_for(
                    self._call_deepseek(prompt, model=self.deepseek_model_pro),
                    timeout=AI_PRIMARY_TIMEOUT_SECONDS,
                )

            if html_raw and self._last_api_call.get("truncated"):
                api_truncated_provider = self._last_api_call.get("provider")
                api_finish_reason = self._last_api_call.get("finish_reason")

            if not html_raw:
                logger.error("❌ DeepSeek failed to generate")
                raise Exception("Failed to generate website")

            html = html_raw

            await update_progress(75, "Processing generated HTML")

            html = self._extract_html(html)
            if self._last_extract_info.get("was_truncated"):
                truncation_flags["was_truncated"] = True
                truncation_flags["unclosed_tags"] = self._last_extract_info.get("unclosed_tags", [])

            # API-boundary signal: if the provider reported finish_reason=length
            # but the post-hoc HTML scan didn't catch it (model gracefully closed
            # </html> despite the cap hit), we still flag truncation. This is
            # exactly the silent-failure mode that put broken sites in prod.
            if api_truncated_provider and not truncation_flags["was_truncated"]:
                logger.error(
                    f"🚨 API-boundary truncation undetected by HTML scan — "
                    f"provider={api_truncated_provider} finish_reason={api_finish_reason}. "
                    f"Flagging was_truncated=True regardless."
                )
                truncation_flags["was_truncated"] = True
                # Mark for manual review — there's no retry path here yet for
                # DeepSeek (Item 4 deferred), so a human needs to look.
                truncation_flags["needs_manual_review"] = True

        # Validate and retry once if the model ignored hard constraints
        # Compute wa_digits up-front — used by both validation (R7 image check)
        # and _fix_placeholders (R6 WhatsApp link injection).
        wa_raw = request.whatsapp_number or "60123456789"
        wa_digits = re.sub(r"\D", "", str(wa_raw))
        if wa_digits.startswith("0"):
            wa_digits = "6" + wa_digits
        elif wa_digits.startswith("1"):
            wa_digits = "60" + wa_digits
        if not wa_digits:
            wa_digits = "60123456789"

        if html:
            required_urls: List[str] = []
            if request.uploaded_images and len(request.uploaded_images) > 0:
                def _url(img):
                    if isinstance(img, dict):
                        return img.get("url", img.get("URL", ""))
                    return str(img) if img else ""

                def _name(img):
                    if isinstance(img, dict):
                        return img.get("name", "")
                    return ""

                gallery_start_index = 0
                first_name = (_name(request.uploaded_images[0]) or "").strip().lower()
                if first_name == "hero image" or "hero" in first_name:
                    required_urls.append(_url(request.uploaded_images[0]))
                    gallery_start_index = 1
                for i in range(4):
                    idx = gallery_start_index + i
                    if idx < len(request.uploaded_images):
                        required_urls.append(_url(request.uploaded_images[idx]))

            errors = self._validate_generated_html(
                html,
                required_image_urls=[u for u in required_urls if u],
                required_wa_digits=wa_digits,
            )
            if errors:
                logger.warning(f"⚠️ HTML validation failed; retrying once with stricter constraints — issues: {errors}")
                with _timed_step("validation_retry", step_timings):
                    retry_prompt = (
                        prompt
                        + "\n\n=== VALIDATION FAILURES (MUST FIX) ===\n"
                        + "\n".join(f"- {e}" for e in errors)
                        + "\nRegenerate the FULL HTML from scratch. Output ONLY HTML."
                    )
                    retry = await self._call_deepseek(retry_prompt, temperature=0.1, model=self.deepseek_model_pro)
                    if not retry:
                        retry = await self._call_qwen(retry_prompt, temperature=0.1)
                    retry_html = self._extract_html(retry) if retry else None
                    if retry_html:
                        html = retry_html

        # ── Qwen copywriting refinement (polish pass) ─────────────────────────
        # Runs AFTER DeepSeek has produced the HTML text but BEFORE the
        # deterministic image-binding steps below (_fix_menu_item_images,
        # _generate_ai_food_images, _fix_broken_image_urls). Those steps pair
        # real menu names with matching images and inject Cloudinary URLs
        # (commits 39c95e0 + ad0f4df); keeping them LAST guarantees Qwen can
        # never clobber the name↔image pairs or the Cloudinary URLs.
        #
        # Non-blocking by design: bounded by its own short timeout and wrapped
        # in try/except. If it's slow, errors, returns nothing, or returns a
        # truncated / materially-shorter result, we ship the un-refined DeepSeek
        # HTML. A polish pass must NEVER fail or delay a working generation.
        if html:
            with _timed_step("qwen_refine", step_timings):
                original_html = html
                refine_status = "skipped"
                try:
                    refined_raw = await asyncio.wait_for(
                        self._improve_with_qwen(original_html, request.description),
                        timeout=AI_QWEN_REFINE_TIMEOUT_SECONDS,
                    )
                    # _improve_with_qwen returns the SAME object on its own
                    # internal None/error fallback — treat that as "skipped".
                    if not refined_raw or refined_raw is original_html:
                        refine_status = "skipped"
                    else:
                        # Same truncation gate we apply to primary output: the
                        # API-boundary finish_reason flag from the Qwen call AND
                        # the post-hoc HTML scan in _extract_html. Never publish
                        # a truncated refinement.
                        qwen_api_truncated = bool(self._last_api_call.get("truncated"))
                        refined_html = self._extract_html(refined_raw)
                        refined_truncated = bool(self._last_extract_info.get("was_truncated"))
                        if not refined_html or qwen_api_truncated or refined_truncated:
                            refine_status = "fallback (truncated)"
                        elif len(refined_html) < len(original_html) * 0.9:
                            # Materially shorter than the input — Qwen likely
                            # dropped sections. Discard, keep the DeepSeek HTML.
                            refine_status = "fallback (truncated)"
                        else:
                            html = refined_html
                            refine_status = "success"
                except asyncio.TimeoutError:
                    refine_status = "fallback (error)"
                except Exception as e:
                    logger.warning(f"✨ Qwen refine raised — keeping DeepSeek HTML ({e})")
                    refine_status = "fallback (error)"
                logger.info(f"✨ Qwen refine: {refine_status}")

        # STEP 3b: Qwen CSS/visual refinement — sibling to the copy-refine above.
        # Runs on the SAME side of the image-binding boundary, so Cloudinary URLs
        # and name↔image pairs are never in Qwen's input. Same non-blocking
        # contract (own short timeout + truncation + length gates), PLUS a
        # structure-equivalence gate: if Qwen alters element counts, ids, image
        # srcs, hrefs, or drops a class a stylesheet/JS hooks onto, we discard its
        # version and keep the prior HTML — the safety net against the
        # "unstyled section" failure mode. Ships dark (flag default OFF).
        if AI_QWEN_CSS_REFINE_ENABLED and html:
            with _timed_step("qwen_css_refine", step_timings):
                original_html = html
                css_status = "skipped"
                try:
                    refined_raw = await asyncio.wait_for(
                        self._improve_css_with_qwen(original_html, request.description),
                        timeout=AI_QWEN_CSS_REFINE_TIMEOUT_SECONDS,
                    )
                    # _improve_css_with_qwen returns the SAME object on its own
                    # internal None/error fallback — treat that as "skipped".
                    if not refined_raw or refined_raw is original_html:
                        css_status = "skipped"
                    else:
                        # Same truncation gates as the primary output and the
                        # copy pass: API-boundary finish_reason flag plus the
                        # post-hoc _extract_html scan. Never publish a truncated
                        # refinement.
                        qwen_api_truncated = bool(self._last_api_call.get("truncated"))
                        refined_html = self._extract_html(refined_raw)
                        refined_truncated = bool(self._last_extract_info.get("was_truncated"))
                        if not refined_html or qwen_api_truncated or refined_truncated:
                            css_status = "fallback (truncated)"
                        elif len(refined_html) < len(original_html) * 0.9:
                            # Materially shorter — Qwen likely dropped sections.
                            css_status = "fallback (truncated)"
                        elif (
                            self._structure_signature(refined_html)
                            != self._structure_signature(original_html)
                        ):
                            # Structure changed — discard, keep the prior HTML.
                            css_status = "fallback (structure changed)"
                        else:
                            html = refined_html
                            css_status = "success"
                except asyncio.TimeoutError:
                    css_status = "fallback (error)"
                except Exception as e:
                    logger.warning(f"🎨 Qwen CSS refine raised — keeping prior HTML ({e})")
                    css_status = "fallback (error)"
                logger.info(f"🎨 Qwen CSS refine: {css_status}")

        # Fix any remaining issues
        with _timed_step("image_matching", step_timings):
            html = self._fix_placeholders(html, request.business_name, request.description, wa_digits=wa_digits)
            html = self._fix_menu_item_images(html, request.description)

        # CRITICAL FIX: Generate AI images for Malaysian food items
        # This replaces Unsplash URLs with Cloudinary URLs from Stability AI.
        # Never override user-provided images.
        if not (request.uploaded_images and len(request.uploaded_images) > 0):
            with _timed_step("ai_food_images", step_timings):
                _food_budget = (
                    None if max_ai_images is None
                    else max(0, max_ai_images - ai_images_generated)
                )
                html, food_images_count = await self._generate_ai_food_images(
                    html, max_images=_food_budget, zai_phase=_zai_image_phase
                )
                ai_images_generated += food_images_count

        # FINAL SAFETY NET: Fix any remaining broken/empty image URLs
        # This ensures no images are left blank or with invalid URLs
        with _timed_step("final_cleanup", step_timings):
            html = self._fix_broken_image_urls(html, request.description)
            # Safety net: remove any remaining {{placeholder}} tokens so they
            # never appear on the published site (AI sometimes outputs these).
            html = re.sub(r'\{\{[a-zA-Z_]+\}\}', '', html)

        total_time = time.time() - start_time
        logger.info("✅ ALL STEPS COMPLETE")
        logger.info(f"   Final size: {len(html)} characters")
        logger.info(f"   ⏱️  Total generation time: {total_time:.1f}s")
        self._log_timing_breakdown(step_timings, total_time)

        await update_progress(90, "Finalizing website")

        # Determine integrations based on mode
        if request.include_ecommerce:
            integrations = ["Delivery System (to be injected)", "WhatsApp Contact", "Mobile Responsive", "Cloudinary Images"]
        else:
            integrations = ["WhatsApp", "Contact Form", "Mobile Responsive", "Cloudinary Images"]

        return AIGenerationResponse(
            html_content=html,
            css_content=None,
            js_content=None,
            meta_title=request.business_name,
            meta_description=f"{request.business_name} - {request.description[:150]}",
            sections=["Header", "Hero", "About", "Services", "Gallery", "Contact", "Footer"],
            integrations_included=integrations,
            ai_images_count=ai_images_generated,
            was_truncated=truncation_flags.get("was_truncated", False),
            truncation_retries=truncation_flags.get("truncation_retries", 0),
            needs_manual_review=truncation_flags.get("needs_manual_review", False),
            step_timings=step_timings,
        )

    async def generate_multi_style(
        self,
        request: WebsiteGenerationRequest
    ) -> Dict[str, AIGenerationResponse]:
        """Generate 3 style variations"""

        logger.info("=" * 80)
        logger.info("🎨 MULTI-STYLE GENERATION - 3 VARIATIONS")
        logger.info("=" * 80)

        results = {}

        for style in ("modern", "minimal", "bold"):
            logger.info(f"\n--- Generating {style.upper()} style ---")

            # Get language from request
            language = request.language.value if hasattr(request, 'language') and request.language else "ms"

            # Get color_mode from request
            color_mode = getattr(request, 'color_mode', 'light') or 'light'
            if color_mode not in ('light', 'dark'):
                color_mode = 'light'

            prompt = self._build_strict_prompt(
                request.business_name,
                request.description,
                style,
                request.uploaded_images,
                language,
                whatsapp_number=request.whatsapp_number,
                location_address=request.location_address,
                color_mode=color_mode,
                include_whatsapp=request.include_whatsapp,
                include_maps=request.include_maps,
                include_ecommerce=request.include_ecommerce,
            )

            # GLM (Z.ai) primary path — strictly PREPENDED, gated by
            # USE_GLM_FOR_HTML. Any GLM failure (no key, error, empty/non-HTML
            # content, truncation, timeout) leaves html=None and the DeepSeek
            # path below runs unchanged. Mirrors generate_website.
            html = None
            if USE_GLM_FOR_HTML and self.zai_api_key:
                # Uploaded images are the only real URLs on the multi-style
                # path (no Stability step). Flattened up front because their
                # presence picks GLM's prompt mode: PHOTO_SLOT contract vs
                # no-photo typography-led design.
                _ordered_urls: List[str] = []
                for _img in (request.uploaded_images or []):
                    if isinstance(_img, dict):
                        _u = _img.get("url", _img.get("URL", ""))
                    else:
                        _u = str(_img) if _img else ""
                    if _u:
                        _ordered_urls.append(_u)
                try:
                    html = await asyncio.wait_for(
                        self._call_glm(prompt, has_images=bool(_ordered_urls)),
                        timeout=AI_GLM_TIMEOUT_SECONDS,
                    )
                except asyncio.TimeoutError:
                    logger.error(
                        f"⏰ GLM timed out (style={style}, "
                        f"budget={AI_GLM_TIMEOUT_SECONDS}s) — falling back to DeepSeek"
                    )
                    html = None
                if html and self._last_api_call.get("truncated"):
                    logger.error(f"🚨 GLM output truncated (style={style}) — falling back to DeepSeek")
                    html = None
                if html and "<" not in html:
                    logger.error(f"🟣 GLM returned non-HTML output (style={style}) — falling back to DeepSeek")
                    html = None
                if html:
                    # Premium design critique loop — same contract as the
                    # generate_website hook: one review, max one revision,
                    # zero calls with the flag off.
                    html = await self._run_premium_design_loop(
                        html, has_images=bool(_ordered_urls)
                    )
                    # Bind PHOTO_SLOT_N tokens to the uploaded image URLs in
                    # order of appearance. No-op in no-photo mode.
                    html = self._replace_photo_slots(html, _ordered_urls)
                    logger.info(f"🟣 GLM primary path succeeded (style={style}) — skipping DeepSeek")

            # DeepSeek-only path. The legacy Qwen fallback was removed
            # on the deepseek-only-no-qwen branch. wait_for still bounds
            # the call so a hung style doesn't burn the budget for the
            # other two — but on timeout we simply skip the style rather
            # than retrying with another provider.
            if not html:
                try:
                    html = await asyncio.wait_for(
                        self._call_deepseek(prompt, model=self.deepseek_model_pro),
                        timeout=AI_PRIMARY_TIMEOUT_SECONDS,
                    )
                except asyncio.TimeoutError:
                    logger.error(
                        f"⏰ DeepSeek timed out (style={style}, "
                        f"budget={AI_PRIMARY_TIMEOUT_SECONDS}s) — skipping this style"
                    )
                    html = None

            if html:
                html = self._extract_html(html)

                # Validate and retry once if constraints were ignored
                if html:
                    required_urls: List[str] = []
                    if request.uploaded_images and len(request.uploaded_images) > 0:
                        def _url(img):
                            if isinstance(img, dict):
                                return img.get("url", img.get("URL", ""))
                            return str(img) if img else ""

                        def _name(img):
                            if isinstance(img, dict):
                                return img.get("name", "")
                            return ""

                        gallery_start_index = 0
                        first_name = (_name(request.uploaded_images[0]) or "").strip().lower()
                        if first_name == "hero image" or "hero" in first_name:
                            required_urls.append(_url(request.uploaded_images[0]))
                            gallery_start_index = 1
                        for i in range(4):
                            idx = gallery_start_index + i
                            if idx < len(request.uploaded_images):
                                required_urls.append(_url(request.uploaded_images[idx]))

                    wa_raw = request.whatsapp_number or "60123456789"
                    wa_digits = re.sub(r"\D", "", str(wa_raw))
                    if wa_digits.startswith("0"):
                        wa_digits = "6" + wa_digits
                    elif wa_digits.startswith("1"):
                        wa_digits = "60" + wa_digits
                    if not wa_digits:
                        wa_digits = "60123456789"

                    errors = self._validate_generated_html(
                        html,
                        required_image_urls=[u for u in required_urls if u],
                        required_wa_digits=wa_digits,
                    )
                    if errors:
                        logger.warning(f"⚠️ {style} HTML validation failed; retrying once")
                        retry_prompt = (
                            prompt
                            + "\n\n=== VALIDATION FAILURES (MUST FIX) ===\n"
                            + "\n".join(f"- {e}" for e in errors)
                            + "\nRegenerate the FULL HTML from scratch. Output ONLY HTML."
                        )
                        retry = await self._call_deepseek(retry_prompt, temperature=0.1, model=self.deepseek_model_pro)
                        if not retry:
                            retry = await self._call_qwen(retry_prompt, temperature=0.1)
                        retry_html = self._extract_html(retry) if retry else None
                        if retry_html:
                            html = retry_html

                # ── Qwen copywriting refinement (polish pass) ─────────────────
                # AFTER DeepSeek HTML, BEFORE the deterministic image steps below
                # (_fix_menu_item_images, _generate_ai_food_images,
                # _fix_broken_image_urls) so Qwen can never clobber the
                # name↔image pairs or Cloudinary URLs. Non-blocking: own short
                # timeout + try/except, and a truncation/short-output gate. On
                # anything other than a clean improvement we keep the DeepSeek
                # HTML. (Mirrors generate_website.)
                refine_status = "skipped"
                original_html = html
                try:
                    refined_raw = await asyncio.wait_for(
                        self._improve_with_qwen(original_html, request.description),
                        timeout=AI_QWEN_REFINE_TIMEOUT_SECONDS,
                    )
                    if not refined_raw or refined_raw is original_html:
                        refine_status = "skipped"
                    else:
                        qwen_api_truncated = bool(self._last_api_call.get("truncated"))
                        refined_html = self._extract_html(refined_raw)
                        refined_truncated = bool(self._last_extract_info.get("was_truncated"))
                        if not refined_html or qwen_api_truncated or refined_truncated:
                            refine_status = "fallback (truncated)"
                        elif len(refined_html) < len(original_html) * 0.9:
                            refine_status = "fallback (truncated)"
                        else:
                            html = refined_html
                            refine_status = "success"
                except asyncio.TimeoutError:
                    refine_status = "fallback (error)"
                except Exception as e:
                    logger.warning(f"✨ Qwen refine raised ({style}) — keeping DeepSeek HTML ({e})")
                    refine_status = "fallback (error)"
                logger.info(f"✨ Qwen refine ({style}): {refine_status}")

                html = self._fix_placeholders(html, request.business_name, request.description, wa_digits=wa_digits)
                html = self._fix_menu_item_images(html, request.description)

                # CRITICAL FIX: Generate AI images for Malaysian food items
                # This replaces Unsplash URLs with Cloudinary URLs from Stability AI
                style_ai_images = 0
                if not (request.uploaded_images and len(request.uploaded_images) > 0):
                    html, style_ai_images = await self._generate_ai_food_images(html)

                # FINAL SAFETY NET: Fix any remaining broken/empty image URLs
                html = self._fix_broken_image_urls(html, request.description)

                results[style] = AIGenerationResponse(
                    html_content=html,
                    css_content=None,
                    js_content=None,
                    meta_title=f"{request.business_name} - {style.title()}",
                    meta_description=f"{request.business_name} - {request.description[:150]}",
                    sections=["Header", "Hero", "About", "Services", "Gallery", "Contact", "Footer"],
                    integrations_included=["WhatsApp", "Contact Form", "Mobile Responsive"],
                    ai_images_count=style_ai_images,
                )
                logger.info(f"✅ {style} style complete")
            else:
                logger.error(f"❌ {style} style failed")

        logger.info(f"\n✅ Generated {len(results)}/3 styles successfully")
        return results


# Create singleton instance
ai_service = AIService()
