"""Admin make-good endpoint: regenerate a published site's product-card
images with proper business context + strip biased food icons.

Background (the gogoo bug, website 709f3a99-b988-4b14-b321-d9c42ab16d86):
the auto-fill image path used to send ONLY the gallery card title to the
image model — a generic fallback title like "Koleksi Terbaru" carries no
subject, so a phone shop's four product cards came back as a handbag,
cosmetic bottles, a cream jar and a mug. The generator's icon guidance also
recommended food glyphs for every vertical, so the same site shipped
fa-bowl-food on its "Smart Line" feature cards.

The generator is fixed forward (business context in every auto-fill prompt,
business-type-aware icon guidance + lint_food_icon_bias). This endpoint is
the backfill for already-published sites:

  1. Re-generates each AI product-card image with the FIXED prompt builder
     (card title + business name + description + business type).
  2. Runs the food-icon bias pass (fa-bowl-food on a phone shop →
     fa-mobile-screen).
  3. Runs the full post-edit guard suite (app.services.edit_guards) on the
     result — this is a guarded rewrite, not a raw HTML write.
  4. Backup-before-overwrite, storage + DB write, same guarantees as
     /admin/repair-websites.

MAKE-GOOD BY CONSTRUCTION: this endpoint never calls
subscription_service.increment_usage, so regenerated images do not consume
the merchant's AI-image quota (quota accounting lives in the user-facing
generate endpoints only).

Endpoint: POST /api/v1/admin/make-good-regen
  ?website_id=<uuid>          target site (required)
  &dry_run=true|false         default TRUE — image regeneration spends real
                              provider budget, so writing must be opted into
  &max_images=4               cap on card images to regenerate
  &skip_images=false          icons/guards only, keep current images
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Dict, List

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, status
from loguru import logger

from app.core.config import settings
from app.core.security import get_current_user
from app.services.business_types import detect_business_type
from app.services.edit_guards import apply_edit_guards
from app.services.generation_linter import lint_food_icon_bias
from app.services.subscription_service import subscription_service
from app.services.supabase_client import supabase_service

router = APIRouter()


# ---------------------------------------------------------------------------
# Pure helpers — no I/O, unit-testable
# ---------------------------------------------------------------------------

# AI-generated images are hosted on Cloudinary; stock/pool fallbacks are
# Unsplash etc. Only Cloudinary images are regeneration candidates.
_AI_IMG_RE = re.compile(
    r'<img\b[^>]*\bsrc\s*=\s*["\'](?P<src>https?://res\.cloudinary\.com/[^"\']+)["\'][^>]*>',
    re.IGNORECASE,
)

_HEADING_RE = re.compile(r"<h([2-4])\b[^>]*>(.*?)</h\1>", re.IGNORECASE | re.DOTALL)
_TAG_RE = re.compile(r"<[^>]+>")
_ALT_RE = re.compile(r'\balt\s*=\s*["\']([^"\']*)["\']', re.IGNORECASE)

# How far past the <img> tag we look for the card's title heading. Card
# markup puts the <h3> right after the image wrapper, well within this.
_TITLE_SEARCH_WINDOW = 800


def _clean_text(fragment: str) -> str:
    return re.sub(r"\s+", " ", _TAG_RE.sub(" ", fragment or "")).strip()


def find_card_images(html: str, max_images: int = 4) -> List[Dict[str, str]]:
    """Locate AI-generated (Cloudinary) product/gallery card images.

    The FIRST Cloudinary image in document order is treated as the hero
    (correct on generated layouts — the hero section always precedes the
    cards) and excluded. For each card image the title is taken from the
    first <h2-4> heading within the following window (card layout puts the
    item name right after its photo), falling back to the img alt text.

    Returns up to max_images dicts: {"url", "title"} — title may be "".
    """
    if not html:
        return []

    matches = list(_AI_IMG_RE.finditer(html))
    if len(matches) <= 1:
        return []  # hero only (or nothing) — no card images to regenerate

    cards: List[Dict[str, str]] = []
    seen_urls = {matches[0].group("src")}  # hero excluded + dedup
    for m in matches[1:]:
        url = m.group("src")
        if url in seen_urls:
            continue
        seen_urls.add(url)

        window = html[m.end(): m.end() + _TITLE_SEARCH_WINDOW]
        # Never read past the next image — that heading belongs to the
        # NEXT card, not this one.
        next_img = window.find("<img")
        if next_img != -1:
            window = window[:next_img]
        heading = _HEADING_RE.search(window)
        title = _clean_text(heading.group(2)) if heading else ""
        if not title:
            alt = _ALT_RE.search(m.group(0))
            title = _clean_text(alt.group(1)) if alt else ""

        cards.append({"url": url, "title": title})
        if len(cards) >= max_images:
            break
    return cards


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

# Lazy singleton — AIService construction is not free and admin repairs are
# rare; don't pay for it at import time.
_ai_service = None


def _get_ai_service():
    global _ai_service
    if _ai_service is None:
        from app.services.ai_service import AIService
        _ai_service = AIService()
    return _ai_service


@router.post("/admin/make-good-regen")
async def make_good_regen(
    website_id: str = Query(..., description="Target website id (UUID)."),
    dry_run: bool = Query(
        True,
        description=(
            "TRUE (default): report what would be regenerated/changed without "
            "calling the image provider or writing. Set false to execute."
        ),
    ),
    max_images: int = Query(4, ge=0, le=4, description="Card images to regenerate."),
    skip_images: bool = Query(
        False, description="Only fix icons + run guards; keep current images."
    ),
    current_user: dict = Depends(get_current_user),
):
    """Guarded make-good rewrite of one published website (admin only).

    Regenerated images are NOT charged to the merchant's AI-image quota —
    no usage counter is touched anywhere in this endpoint.
    """
    user_id = current_user.get("sub") or current_user.get("id")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")

    if not await subscription_service._is_admin(user_id):
        logger.warning(f"🛑 make-good-regen called by non-admin user_id={user_id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required for this operation.",
        )

    website_id = (website_id or "").strip()
    if not website_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="website_id required")

    # Fetch the website row (same REST pattern as /admin/repair-websites).
    rest_url = f"{supabase_service.url}/rest/v1/websites"
    select_cols = "id,user_id,subdomain,status,html_content,business_name,description,location_address"
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                rest_url,
                headers=supabase_service.headers,
                params={"id": f"eq.{website_id}", "select": select_cols, "limit": "1"},
            )
        if resp.status_code != 200:
            logger.error(f"❌ make-good-regen: lookup failed: {resp.status_code} {resp.text[:200]}")
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Website lookup failed.")
        rows = resp.json() or []
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("❌ make-good-regen: lookup threw")
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Website lookup failed: {e}")

    if not rows:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Website not found.")
    site = rows[0]

    if site.get("status") != "published":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Website status is '{site.get('status')}', not published.",
        )
    html = site.get("html_content") or ""
    if not html:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Website has empty html_content.")

    sub = site.get("subdomain") or "?"
    business_name = site.get("business_name") or ""
    description = site.get("description") or ""

    svc = _get_ai_service()
    business_type = detect_business_type(description)
    category = svc._autofill_prompt_category(description)
    # Same convention as _autofill_missing_images: business grounding comes
    # from biz_context; "general" gets a neutral grammatical noun.
    biz_type_label = business_type if business_type != "general" else "retail shop"
    biz_context = svc._autofill_business_context(business_name, description)
    icon_context = f"{business_name} {description}"

    report: Dict[str, Any] = {
        "website_id": website_id,
        "subdomain": sub,
        "dry_run": dry_run,
        "business_type": business_type,
        "prompt_category": category,
        "cards": [],
        "images_regenerated": 0,
        "icon_replacements": [],
        "quota_charged": False,  # make-good: never charged
        "backup_path": None,
        "uploaded_to_storage": False,
        "db_updated": False,
    }

    # ---- 1. Product-card image regeneration (with business context) ----
    work = html
    if not skip_images and max_images > 0:
        cards = find_card_images(work, max_images=max_images)
        for i, card in enumerate(cards, 1):
            title = card["title"] or f"Produk {i}"
            prompt = svc._autofill_item_prompt(category, title, biz_type_label, biz_context)
            entry = {"old_url": card["url"], "title": title, "prompt": prompt, "new_url": None}
            report["cards"].append(entry)
            if dry_run:
                continue
            try:
                new_url = await svc._generate_image(prompt, food=(category == "food"))
            except Exception as e:
                logger.warning(f"⚠️ make-good-regen: generation failed for '{title}': {e}")
                new_url = None
            if new_url:
                # Replace every occurrence so srcset/duplicate uses stay in sync.
                work = work.replace(card["url"], new_url)
                entry["new_url"] = new_url
                report["images_regenerated"] += 1
            # On failure the old image stays — never ship an empty slot.

    # ---- 2. Icon-sanity pass (food glyphs off non-F&B sites) ----
    work, icon_repl = lint_food_icon_bias(work, business_type, icon_context)
    report["icon_replacements"] = icon_repl

    if dry_run:
        # Report the icon swaps the pass WOULD make, but don't write.
        report["would_change"] = bool(report["cards"]) or bool(icon_repl)
        return report

    # ---- 3. Guarded pipeline — same suite as the editor AI-edit path ----
    work = apply_edit_guards(work, svc, website=site, previous_html=html)

    if work == html:
        report["skipped_unchanged"] = True
        return report

    # ---- 4. Backup, then storage + DB write (repair-websites pattern) ----
    bucket = settings.STORAGE_BUCKET_NAME
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_path = f"{sub}/index.pre-makegood-{ts}.html"
    try:
        await supabase_service.upload_file(
            bucket=bucket,
            path=backup_path,
            file_data=html.encode("utf-8"),
            content_type="text/html; charset=utf-8",
        )
        report["backup_path"] = backup_path
    except Exception as e:
        logger.exception(f"❌ make-good-regen: backup failed for {sub}, refusing to write")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Backup failed, write aborted: {e}",
        )

    try:
        await supabase_service.upload_file(
            bucket=bucket,
            path=f"{sub}/index.html",
            file_data=work.encode("utf-8"),
            content_type="text/html; charset=utf-8",
        )
        report["uploaded_to_storage"] = True
        site_user_id = site.get("user_id")
        if site_user_id:
            try:
                await supabase_service.upload_file(
                    bucket=bucket,
                    path=f"{site_user_id}/{sub}/index.html",
                    file_data=work.encode("utf-8"),
                    content_type="text/html; charset=utf-8",
                )
            except Exception as e:
                logger.warning(f"⚠️ make-good-regen: mirror upload failed for {sub}: {e}")
    except Exception as e:
        logger.exception(f"❌ make-good-regen: storage write failed for {sub}")
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Storage write failed: {e}")

    try:
        ok = await supabase_service.update_website(
            website_id,
            {
                "html_content": work,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        report["db_updated"] = bool(ok)
    except Exception as e:
        logger.exception(f"❌ make-good-regen: DB update failed for {sub}")
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"DB update failed: {e}")

    logger.info(
        f"✅ make-good-regen {sub}: {report['images_regenerated']} image(s) regenerated, "
        f"{len(icon_repl)} icon(s) fixed, quota_charged=False"
    )
    return report
