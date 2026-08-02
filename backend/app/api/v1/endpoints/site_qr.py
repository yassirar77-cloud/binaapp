"""QR toolkit for a published site — codes and print-ready posters.

    GET /api/v1/websites/{id}/qr.svg          the code on its own (SVG)
    GET /api/v1/websites/{id}/qr-poster.html  an A4 poster in the site's colours

Both are owner-only. The URL they encode is public, but which website_id maps
to which subdomain is the merchant's business, and the poster is generated
from their stored page.

Rendered offline (segno) — no third-party image service sits between a
merchant and their own QR code.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.responses import HTMLResponse
from loguru import logger

from app.core.config import settings
from app.core.security import get_current_user
from app.services.qr_service import build_poster_html, build_site_url, qr_svg
from app.services.supabase_client import supabase_service
from app.services.theme_patcher import detect_palette

# Mounted under /websites in router.py.
router = APIRouter()

#: Cap on caller-supplied label text that ends up in the poster.
_MAX_LABEL = 120


async def _load_owned_published_site(website_id: str, user_id: str) -> dict:
    website = await supabase_service.get_website(website_id)
    if not website:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Website not found"
        )
    if website.get("user_id") != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this website",
        )
    if not website.get("subdomain"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": "not_published",
                "message": (
                    "Laman web ini belum diterbitkan, jadi tiada pautan untuk "
                    "kod QR. Terbitkan dahulu."
                ),
            },
        )
    return website


@router.get("/{website_id}/qr.svg")
async def get_website_qr(
    website_id: str,
    table: Optional[str] = Query(
        None, max_length=16, description="Table number — one unique QR per table"
    ),
    campaign: Optional[str] = Query(
        None, max_length=32, description="Campaign marker, e.g. a flyer batch"
    ),
    scale: int = Query(8, ge=2, le=24, description="Pixels per QR module"),
    dark: str = Query("#111827", description="Module colour (hex)"),
    current_user: dict = Depends(get_current_user),
):
    """The site's QR code as an SVG — crisp at any print size."""
    user_id = current_user.get("sub")
    website = await _load_owned_published_site(website_id, user_id)

    url = build_site_url(
        website["subdomain"], settings.MAIN_DOMAIN, table=table, campaign=campaign
    )
    svg = qr_svg(url, scale=scale, border=2, dark=dark, light="#FFFFFF")
    if not svg:
        # segno missing: better an honest 503 than a broken <img> in a print job.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="QR renderer unavailable",
        )

    return Response(
        content=svg,
        media_type="image/svg+xml",
        headers={
            # The encoded URL only changes when the subdomain does.
            "Cache-Control": "private, max-age=3600",
            "Content-Disposition": f'inline; filename="{website["subdomain"]}-qr.svg"',
        },
    )


@router.get("/{website_id}/qr-poster.html", response_class=HTMLResponse)
async def get_website_qr_poster(
    website_id: str,
    table: Optional[str] = Query(None, max_length=16),
    campaign: Optional[str] = Query(None, max_length=32),
    headline: Optional[str] = Query(None, max_length=_MAX_LABEL),
    language: str = Query("ms", pattern="^(ms|en)$"),
    current_user: dict = Depends(get_current_user),
):
    """A print-ready A4 poster wearing the site's own palette.

    Table tents (`?table=5`), counter standees, flyer inserts. Open it and hit
    the Print button — the page carries its own `@page size: A4` rules.
    """
    user_id = current_user.get("sub")
    website = await _load_owned_published_site(website_id, user_id)

    url = build_site_url(
        website["subdomain"], settings.MAIN_DOMAIN, table=table, campaign=campaign
    )
    palette = detect_palette(website.get("html_content") or "")

    html = build_poster_html(
        business_name=website.get("name") or website["subdomain"],
        url=url,
        palette=palette,
        language=language,
        table=table,
        headline=headline,
    )
    logger.info(
        f"🖨️ QR poster generated for {website['subdomain']}"
        f"{f' (meja {table})' if table else ''}"
    )
    return HTMLResponse(
        content=html,
        headers={"Cache-Control": "private, max-age=600"},
    )
