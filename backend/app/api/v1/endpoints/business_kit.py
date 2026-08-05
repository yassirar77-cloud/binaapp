"""Business Kit for a published site — menu poster, review QR, WhatsApp QR.

    GET /api/v1/websites/{id}/menu-poster.html      A4 menu / price list
    GET /api/v1/websites/{id}/review-poster.html    "beri kami 5 bintang" QR
    GET /api/v1/websites/{id}/whatsapp-poster.html  scan → pre-typed order chat

Owner-only, offline, free — the same contract as the QR toolkit and Promo
Kit. Everything printed comes from the merchant's own data: the menu from
their menu table (or the menu baked into their page), the WhatsApp number
from their page, the review link from their own Google listing.
"""

from __future__ import annotations

from typing import Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import HTMLResponse
from loguru import logger

from app.core.config import settings
from app.core.security import get_current_user
from app.services.business_kit import (
    build_menu_poster_html,
    build_review_poster_html,
    build_whatsapp_poster_html,
    is_valid_review_url,
    normalize_db_menu,
    parse_menu_from_html,
)
from app.services.promo_kit import extract_phone
from app.services.qr_service import build_site_url
from app.services.supabase_client import supabase_service
from app.services.theme_patcher import detect_palette

# Reuse the QR toolkit's owner+published gate (404 unknown / 403 not-yours /
# 409 unpublished) so every printable surface behaves identically.
from app.api.v1.endpoints.site_qr import _load_owned_published_site

# Mounted under /websites in router.py.
router = APIRouter()


async def _load_menu_items(website_id: str, page_html: str) -> list:
    """The merchant's menu: the ``menu_items`` table first, page fallback.

    The table is the live source when the site manages its menu there (the
    delivery flow); older sites only carry the menu baked into the page as
    ``deliveryMenuData``. DB errors degrade to the page rather than failing
    the poster.
    """
    rows = None
    try:
        rows = await supabase_service.select_records(
            "menu_items", {"website_id": website_id}
        )
    except Exception as exc:
        logger.warning(f"menu_items lookup failed for {website_id}: {exc}")

    if rows:
        # Attach category names so the poster can group by real categories.
        names: Dict[str, str] = {}
        try:
            categories = await supabase_service.select_records(
                "menu_categories", {"website_id": website_id}
            )
            for cat in categories or []:
                if isinstance(cat, dict) and cat.get("id"):
                    names[str(cat["id"])] = str(cat.get("name") or "")
        except Exception as exc:
            logger.warning(f"menu_categories lookup failed for {website_id}: {exc}")
        for row in rows:
            if isinstance(row, dict) and row.get("category_id"):
                row.setdefault("category_name", names.get(str(row["category_id"]), ""))
        items = normalize_db_menu(rows)
        if items:
            return items

    return parse_menu_from_html(page_html)


@router.get("/{website_id}/menu-poster.html", response_class=HTMLResponse)
async def get_menu_poster(
    website_id: str,
    language: str = Query("ms", pattern="^(ms|en)$"),
    current_user: dict = Depends(get_current_user),
):
    """Print-ready A4 menu / price list in the site's own palette.

    Prices change in the dashboard → the next print is already correct.
    Works for any business: a salon's service list is the same shape.
    """
    user_id = current_user.get("sub")
    website = await _load_owned_published_site(website_id, user_id)
    page_html = website.get("html_content") or ""

    items = await _load_menu_items(website_id, page_html)
    if not items:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": "no_menu_found",
                "message": (
                    "Tiada item menu untuk laman web ini. Tambah menu anda "
                    "di papan pemuka dahulu."
                ),
            },
        )

    html = build_menu_poster_html(
        business_name=website.get("name") or website["subdomain"],
        items=items,
        url=build_site_url(website["subdomain"], settings.MAIN_DOMAIN),
        palette=detect_palette(page_html),
        language=language,
    )
    logger.info(f"📄 Menu poster generated for {website['subdomain']} ({len(items)} items)")
    return HTMLResponse(content=html, headers={"Cache-Control": "private, max-age=600"})


@router.get("/{website_id}/review-poster.html", response_class=HTMLResponse)
async def get_review_poster(
    website_id: str,
    review_url: str = Query(..., max_length=500),
    language: str = Query("ms", pattern="^(ms|en)$"),
    current_user: dict = Depends(get_current_user),
):
    """A4 "rate us 5 stars" poster. The QR points at the merchant's own
    Google review link — only Google-family URLs are accepted, because a
    printed QR is trusted by whoever scans it."""
    user_id = current_user.get("sub")
    website = await _load_owned_published_site(website_id, user_id)

    if not is_valid_review_url(review_url):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": "invalid_review_url",
                "message": (
                    "Pautan mesti pautan ulasan Google anda (google.com, "
                    "g.page, maps.app.goo.gl)."
                ),
            },
        )

    html = build_review_poster_html(
        business_name=website.get("name") or website["subdomain"],
        review_url=review_url.strip(),
        palette=detect_palette(website.get("html_content") or ""),
        language=language,
    )
    logger.info(f"⭐ Review poster generated for {website['subdomain']}")
    return HTMLResponse(content=html, headers={"Cache-Control": "private, max-age=600"})


@router.get("/{website_id}/whatsapp-poster.html", response_class=HTMLResponse)
async def get_whatsapp_poster(
    website_id: str,
    table: Optional[str] = Query(None, max_length=16),
    message: Optional[str] = Query(None, max_length=200),
    phone: Optional[str] = Query(None, max_length=20, pattern=r"^\+?[\d\s().-]{7,20}$"),
    language: str = Query("ms", pattern="^(ms|en)$"),
    current_user: dict = Depends(get_current_user),
):
    """A4 poster: scan → WhatsApp opens with the order message pre-typed.

    ``table`` makes one poster per table, so every incoming chat announces
    where it came from. The number comes from the merchant's own page
    (same rule as the vCard poster) unless explicitly overridden.
    """
    user_id = current_user.get("sub")
    website = await _load_owned_published_site(website_id, user_id)
    page_html = website.get("html_content") or ""

    resolved_phone = (phone or "").strip() or extract_phone(page_html)
    if not resolved_phone:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": "no_phone_found",
                "message": (
                    "Tiada nombor telefon di laman web anda. Tambah pautan "
                    "WhatsApp dahulu, atau berikan ?phone=+60..."
                ),
            },
        )

    html = build_whatsapp_poster_html(
        business_name=website.get("name") or website["subdomain"],
        phone=resolved_phone,
        palette=detect_palette(page_html),
        language=language,
        table=table,
        message=message,
    )
    logger.info(
        f"💬 WhatsApp poster generated for {website['subdomain']}"
        f"{f' (meja {table})' if table else ''}"
    )
    return HTMLResponse(content=html, headers={"Cache-Control": "private, max-age=600"})
