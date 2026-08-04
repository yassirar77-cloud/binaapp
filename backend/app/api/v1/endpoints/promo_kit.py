"""Promo Kit for a published site — share images, vCard QR, Wi-Fi QR.

    GET /api/v1/websites/{id}/share-card.png    the og:image, for preview/download
    GET /api/v1/websites/{id}/story.png         1080x1920 WhatsApp-Status poster
    GET /api/v1/websites/{id}/vcard-qr.svg      scan-to-save-contact QR
    GET /api/v1/websites/{id}/vcard-poster.html printable A4 "save our number"
    GET /api/v1/websites/{id}/wifi-poster.html  printable A4 "free Wi-Fi"

All owner-only, all rendered offline (Pillow + segno), all free — nothing
here touches the AI or a usage counter. The public, crawler-facing copy of
the share card is served by the subdomain middleware at
``https://<sub>.binaapp.my/share-card.png``; the endpoint here is the
merchant's own preview/download of the same image.

The Wi-Fi endpoint takes the SSID and password as query parameters and
returns them inside the poster only. They are deliberately never persisted
and never logged.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.responses import HTMLResponse
from loguru import logger

from app.core.config import settings
from app.core.security import get_current_user
from app.services.promo_kit import (
    build_vcard,
    build_vcard_poster_html,
    build_wifi_poster_html,
    extract_email,
    extract_phone,
    extract_tagline,
)
from app.services.qr_service import build_site_url, qr_svg
from app.services.share_card import render_share_card, render_story_card
from app.services.theme_patcher import detect_palette

# Reuse the QR toolkit's owner+published gate so every promo-kit surface
# behaves identically (404 unknown, 403 not-yours, 409 unpublished).
from app.api.v1.endpoints.site_qr import _load_owned_published_site

# Mounted under /websites in router.py.
router = APIRouter()

#: Wi-Fi limits straight from 802.11: SSIDs are at most 32 octets and a
#: WPA passphrase is 8–63 characters. Anything outside that cannot be a
#: real network, so reject it at the edge.
_MAX_SSID = 32
_MAX_WIFI_PASSWORD = 63


def _site_context(website: dict) -> dict:
    """Everything the renderers need, read from the merchant's own data."""
    html = website.get("html_content") or ""
    return {
        "name": website.get("name") or website["subdomain"],
        "url": build_site_url(website["subdomain"], settings.MAIN_DOMAIN),
        "palette": detect_palette(html),
        "tagline": extract_tagline(html),
        "html": html,
    }


def _png_response(png: bytes, filename: str) -> Response:
    if not png:
        # Pillow missing or draw failed: an honest 503 beats a broken image.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Image renderer unavailable",
        )
    return Response(
        content=png,
        media_type="image/png",
        headers={
            "Cache-Control": "private, max-age=600",
            "Content-Disposition": f'inline; filename="{filename}"',
        },
    )


@router.get("/{website_id}/share-card.png")
async def get_share_card(
    website_id: str,
    current_user: dict = Depends(get_current_user),
):
    """The 1200x630 link-preview image, exactly as crawlers will see it."""
    website = await _load_owned_published_site(website_id, current_user.get("sub"))
    ctx = _site_context(website)
    png = render_share_card(ctx["name"], ctx["url"], ctx["palette"], ctx["tagline"])
    return _png_response(png, f"{website['subdomain']}-share-card.png")


@router.get("/{website_id}/story.png")
async def get_story_card(
    website_id: str,
    language: str = Query("ms", pattern="^(ms|en)$"),
    campaign: Optional[str] = Query(None, max_length=32),
    current_user: dict = Depends(get_current_user),
):
    """A 1080x1920 poster for WhatsApp Status / Instagram Story, QR included."""
    website = await _load_owned_published_site(website_id, current_user.get("sub"))
    ctx = _site_context(website)
    url = build_site_url(website["subdomain"], settings.MAIN_DOMAIN, campaign=campaign)
    png = render_story_card(
        ctx["name"], url, ctx["palette"], ctx["tagline"], language=language
    )
    logger.info(f"📲 Story card generated for {website['subdomain']}")
    return _png_response(png, f"{website['subdomain']}-story.png")


@router.get("/{website_id}/vcard-qr.svg")
async def get_vcard_qr(
    website_id: str,
    phone: Optional[str] = Query(None, max_length=20, pattern=r"^\+?[\d\s().-]{7,20}$"),
    scale: int = Query(8, ge=2, le=24),
    current_user: dict = Depends(get_current_user),
):
    """A QR that saves the business straight into a customer's contacts."""
    website = await _load_owned_published_site(website_id, current_user.get("sub"))
    ctx = _site_context(website)

    resolved_phone = (phone or "").strip() or extract_phone(ctx["html"])
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
    vcard = build_vcard(
        ctx["name"],
        phone=resolved_phone,
        url=ctx["url"],
        email=extract_email(ctx["html"]),
    )
    svg = qr_svg(vcard, scale=scale, border=2, dark="#111827", light="#FFFFFF")
    if not svg:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="QR renderer unavailable",
        )
    return Response(
        content=svg,
        media_type="image/svg+xml",
        headers={
            "Cache-Control": "private, max-age=600",
            "Content-Disposition": f'inline; filename="{website["subdomain"]}-vcard-qr.svg"',
        },
    )


@router.get("/{website_id}/vcard-poster.html", response_class=HTMLResponse)
async def get_vcard_poster(
    website_id: str,
    phone: Optional[str] = Query(None, max_length=20, pattern=r"^\+?[\d\s().-]{7,20}$"),
    language: str = Query("ms", pattern="^(ms|en)$"),
    current_user: dict = Depends(get_current_user),
):
    """Print-ready A4 "save our number" poster in the site's palette."""
    website = await _load_owned_published_site(website_id, current_user.get("sub"))
    ctx = _site_context(website)

    resolved_phone = (phone or "").strip() or extract_phone(ctx["html"])
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
    vcard = build_vcard(
        ctx["name"],
        phone=resolved_phone,
        url=ctx["url"],
        email=extract_email(ctx["html"]),
    )
    html = build_vcard_poster_html(
        ctx["name"], vcard, resolved_phone, ctx["palette"], language
    )
    logger.info(f"📇 vCard poster generated for {website['subdomain']}")
    return HTMLResponse(content=html, headers={"Cache-Control": "private, max-age=600"})


@router.get("/{website_id}/wifi-poster.html", response_class=HTMLResponse)
async def get_wifi_poster(
    website_id: str,
    ssid: str = Query(..., min_length=1, max_length=_MAX_SSID),
    password: str = Query("", max_length=_MAX_WIFI_PASSWORD),
    security: str = Query("WPA", pattern="^(WPA|WEP|nopass)$"),
    language: str = Query("ms", pattern="^(ms|en)$"),
    show_password: bool = Query(True),
    current_user: dict = Depends(get_current_user),
):
    """Print-ready A4 "scan to join our Wi-Fi" poster.

    The credentials exist only in this request/response pair — they are not
    stored, and this handler intentionally logs the subdomain only.
    """
    website = await _load_owned_published_site(website_id, current_user.get("sub"))
    ctx = _site_context(website)

    html = build_wifi_poster_html(
        ctx["name"],
        ssid=ssid,
        password=password,
        security=security,
        palette=ctx["palette"],
        language=language,
        show_password=show_password,
    )
    logger.info(f"📶 Wi-Fi poster generated for {website['subdomain']}")
    return HTMLResponse(
        content=html,
        headers={
            # Never let a shared cache hold a page containing Wi-Fi credentials.
            "Cache-Control": "private, no-store",
        },
    )
