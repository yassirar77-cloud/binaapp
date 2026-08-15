"""Counter Kit for a published site — loyalty cards, business cards,
vouchers and a holiday-closure notice.

    GET /api/v1/websites/{id}/loyalty-cards.html    A4 sheet of 8 stamp cards
    GET /api/v1/websites/{id}/business-cards.html   A4 sheet of 10 name cards
    GET /api/v1/websites/{id}/voucher-sheet.html    A4 sheet of 6 vouchers
    GET /api/v1/websites/{id}/closure-poster.html   A4 "kami bercuti" notice

Owner-only, offline, free — the same contract as the QR toolkit, Promo Kit
and Business Kit. Everything printed comes from the merchant's own data:
name and palette from their page, the phone number from the links their
page already shows, offers and dates typed by the merchant and printed
verbatim (escaped, never interpreted).
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import HTMLResponse
from loguru import logger

from app.core.config import settings
from app.core.security import get_current_user
from app.services.counter_kit import (
    build_business_cards_html,
    build_closure_poster_html,
    build_loyalty_card_html,
    build_voucher_sheet_html,
)
from app.services.promo_kit import extract_phone, extract_tagline
from app.services.qr_service import build_site_url
from app.services.theme_patcher import detect_palette

# Reuse the QR toolkit's owner+published gate (404 unknown / 403 not-yours /
# 409 unpublished) so every printable surface behaves identically.
from app.api.v1.endpoints.site_qr import _load_owned_published_site

# Mounted under /websites in router.py.
router = APIRouter()


@router.get("/{website_id}/loyalty-cards.html", response_class=HTMLResponse)
async def get_loyalty_cards(
    website_id: str,
    stamps: int = Query(10, ge=4, le=20),
    reward: Optional[str] = Query(None, max_length=80),
    language: str = Query("ms", pattern="^(ms|en)$"),
    current_user: dict = Depends(get_current_user),
):
    """A4 sheet of eight cut-out loyalty stamp cards in the site's palette.

    ``stamps`` counts the reward stamp too: buy N-1, the Nth is the gift.
    Any chop or marker pen stamps a visit — no app, no account, no cost.
    """
    user_id = current_user.get("sub")
    website = await _load_owned_published_site(website_id, user_id)

    html = build_loyalty_card_html(
        business_name=website.get("name") or website["subdomain"],
        url=build_site_url(website["subdomain"], settings.MAIN_DOMAIN),
        stamps=stamps,
        reward=reward,
        palette=detect_palette(website.get("html_content") or ""),
        language=language,
    )
    logger.info(f"🎟️ Loyalty cards generated for {website['subdomain']} ({stamps} stamps)")
    return HTMLResponse(content=html, headers={"Cache-Control": "private, max-age=600"})


@router.get("/{website_id}/business-cards.html", response_class=HTMLResponse)
async def get_business_cards(
    website_id: str,
    tagline: Optional[str] = Query(None, max_length=120),
    language: str = Query("ms", pattern="^(ms|en)$"),
    current_user: dict = Depends(get_current_user),
):
    """A4 sheet of ten standard-size business cards with a QR to the site.

    The phone number is read from the merchant's own page (same rule as the
    vCard poster) and the default tagline is the page's own meta description
    — both optional, a card without them is still a card.
    """
    user_id = current_user.get("sub")
    website = await _load_owned_published_site(website_id, user_id)
    page_html = website.get("html_content") or ""

    html = build_business_cards_html(
        business_name=website.get("name") or website["subdomain"],
        url=build_site_url(website["subdomain"], settings.MAIN_DOMAIN),
        phone=extract_phone(page_html),
        tagline=(tagline or "").strip() or extract_tagline(page_html),
        palette=detect_palette(page_html),
        language=language,
    )
    logger.info(f"📇 Business cards generated for {website['subdomain']}")
    return HTMLResponse(content=html, headers={"Cache-Control": "private, max-age=600"})


@router.get("/{website_id}/voucher-sheet.html", response_class=HTMLResponse)
async def get_voucher_sheet(
    website_id: str,
    offer: str = Query(..., min_length=1, max_length=60),
    code: Optional[str] = Query(None, max_length=24),
    expiry: Optional[str] = Query(None, max_length=40),
    language: str = Query("ms", pattern="^(ms|en)$"),
    current_user: dict = Depends(get_current_user),
):
    """A4 sheet of six cut-out vouchers carrying the merchant's own offer.

    The offer text is printed verbatim (escaped) — BinaApp never invents a
    promotion. Redemption happens at the counter, between merchant and
    customer; the optional code is theirs to track however they like.
    """
    user_id = current_user.get("sub")
    website = await _load_owned_published_site(website_id, user_id)

    html = build_voucher_sheet_html(
        business_name=website.get("name") or website["subdomain"],
        url=build_site_url(website["subdomain"], settings.MAIN_DOMAIN),
        offer=offer,
        code=code,
        expiry=expiry,
        palette=detect_palette(website.get("html_content") or ""),
        language=language,
    )
    logger.info(f"🏷️ Voucher sheet generated for {website['subdomain']}")
    return HTMLResponse(content=html, headers={"Cache-Control": "private, max-age=600"})


@router.get("/{website_id}/closure-poster.html", response_class=HTMLResponse)
async def get_closure_poster(
    website_id: str,
    reopen: str = Query(..., min_length=1, max_length=40),
    closed_from: Optional[str] = Query(None, max_length=40),
    note: Optional[str] = Query(None, max_length=100),
    language: str = Query("ms", pattern="^(ms|en)$"),
    current_user: dict = Depends(get_current_user),
):
    """A4 "kami bercuti" notice with the reopening date and a QR to the site.

    Dates are free text printed as typed ("2 Jun", "selepas Raya") — that is
    how kedai actually announce closures. The QR earns its place: a closed
    door is the one time a customer genuinely needs the website.
    """
    user_id = current_user.get("sub")
    website = await _load_owned_published_site(website_id, user_id)

    html = build_closure_poster_html(
        business_name=website.get("name") or website["subdomain"],
        url=build_site_url(website["subdomain"], settings.MAIN_DOMAIN),
        reopen=reopen,
        closed_from=closed_from,
        note=note,
        palette=detect_palette(website.get("html_content") or ""),
        language=language,
    )
    logger.info(f"🏖️ Closure poster generated for {website['subdomain']}")
    return HTMLResponse(content=html, headers={"Cache-Control": "private, max-age=600"})
