"""Design Studio — credit-free colour & typography control for a live site.

    GET   /api/v1/websites/design/options        the palette / font / style catalogue
    GET   /api/v1/websites/{id}/theme            what the page is wearing right now
    PATCH /api/v1/websites/{id}/theme            repaint it

WHY THIS IS NOT REGENERATION
----------------------------
"Tukar warna jadi biru" used to cost a generation credit and two minutes, and
came back with different copy and different photos because the whole page was
rebuilt. A recolour is a token rewrite, not a redesign. This router rewrites
the colour/typography tokens in the page that is already live and republishes
it — no AI call, no quota, no content drift.

QUOTA NOTE (protected zone): nothing here touches check_limit,
subscription_service, usage_tracking, or any credit counter. It is a
credit-free edit path in the same shape as PATCH /websites/{id}/contact.

PUBLISH SAFETY
--------------
Identical rules to the contact-edit path, for the same reason (the mimba
regression, where republishing a truncated DB blob wiped a live site's
injected widgets):

  * rewrite against the LIVE storage snapshot when the site is published,
    falling back to the DB blob;
  * only ever accept a structurally BALANCED base;
  * refuse to publish a result that is not balanced;
  * when no safe base exists, change nothing and say so.
"""

from __future__ import annotations

from datetime import datetime
from typing import Dict, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from loguru import logger
from pydantic import BaseModel, Field, field_validator

from app.core.security import get_current_user
from app.services import design_system as ds
from app.services.storage_service import storage_service
from app.services.supabase_client import supabase_service
from app.services.theme_patcher import (
    PALETTE_ROLES,
    apply_theme,
    clean_palette,
    contrast_ratio,
    detect_fonts,
    detect_palette,
    normalize_hex,
)

# Mounted under /websites in router.py, so the public paths line up with the
# rest of the website endpoints.
router = APIRouter()


async def _fetch_serving_snapshot(subdomain: str) -> Optional[str]:
    """The live storage snapshot — see services/serving_snapshot.py."""
    from app.services.serving_snapshot import fetch_published_snapshot

    return await fetch_published_snapshot(subdomain, cache_bust="theme-edit")


class ThemeRequest(BaseModel):
    """Every field optional; at least one colour source must resolve.

    Precedence, strongest first:
        colors  >  palette  >  shuffle
    """

    #: A NAMED_COLOR_PALETTES key ("blue", "gold", "maroon", …).
    palette: Optional[str] = None
    #: Explicit brand hexes. Partial dicts are fine — unspecified roles keep
    #: whatever the resolved palette (or the live page) already has.
    colors: Optional[Dict[str, str]] = None
    color_mode: Literal["light", "dark"] = "light"
    #: A font-pairing slug from GET /websites/design/options.
    font_key: Optional[str] = None
    #: Advance to the next palette in the picker's display order. Seeded from
    #: the colour the page is wearing right now, so it never re-picks it.
    shuffle: bool = False
    #: How many steps to advance when shuffling.
    shuffle_step: int = Field(default=1, ge=1, le=24)

    @field_validator("colors")
    @classmethod
    def _validate_colors(cls, value):
        if value is None:
            return None
        cleaned = {}
        for role, raw in value.items():
            if role not in PALETTE_ROLES:
                continue
            normalized = normalize_hex(str(raw))
            if not normalized:
                raise ValueError(f"'{role}' must be a hex colour like #1E3A8A")
            cleaned[role] = normalized
        if not cleaned:
            raise ValueError(
                "colors must contain at least one of: " + ", ".join(PALETTE_ROLES)
            )
        return cleaned


async def _load_owned_website(website_id: str, user_id: str) -> dict:
    website = await supabase_service.get_website(website_id)
    if not website:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Website not found"
        )
    if website.get("user_id") != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this website",
        )
    return website


@router.get("/design/options")
async def get_design_options(
    color_mode: Literal["light", "dark"] = Query("light"),
    business_type: Optional[str] = Query(
        None, description="Limit font pairings to one business type"
    ),
):
    """The full design catalogue behind the picker UI.

    Public (no auth): it is a static catalogue of the looks BinaApp offers,
    with no merchant data in it, and the create-page picker renders before a
    website row exists.
    """
    return {
        "success": True,
        "color_mode": color_mode,
        "palettes": ds.list_named_palettes(color_mode),
        "fonts": ds.list_font_pairings(business_type),
        "styles": ds.list_styles(),
    }


@router.get("/{website_id}/theme")
async def get_website_theme(
    website_id: str,
    current_user: dict = Depends(get_current_user),
):
    """What colours and fonts the page is wearing right now.

    Read from the live serving snapshot when the site is published (that is
    what visitors see), otherwise from the stored draft.
    """
    user_id = current_user.get("sub")
    website = await _load_owned_website(website_id, user_id)

    html = ""
    source = "none"
    if website.get("status") == "published" and website.get("subdomain"):
        html = await _fetch_serving_snapshot(website["subdomain"]) or ""
        source = "storage" if html else source
    if not html:
        html = website.get("html_content") or ""
        source = "db" if html else source

    palette = detect_palette(html)
    fonts = detect_fonts(html)
    matched = ds.match_palette_key(palette.get("primary", ""))

    contrast = None
    if palette.get("text") and palette.get("background"):
        contrast = contrast_ratio(palette["text"], palette["background"])

    return {
        "success": True,
        "website_id": website_id,
        "source": source,
        "palette": palette,
        "palette_key": matched or None,
        "fonts": fonts,
        "text_contrast": contrast,
    }


@router.patch("/{website_id}/theme")
async def update_website_theme(
    website_id: str,
    body: ThemeRequest,
    current_user: dict = Depends(get_current_user),
):
    """Repaint a website's palette and/or typography. Credit-FREE.

    Never calls the AI, never consumes a generation credit, never reorders or
    rewrites content — only colour and font tokens move.
    """
    user_id = current_user.get("sub")
    website = await _load_owned_website(website_id, user_id)

    is_published = bool(
        website.get("status") == "published" and website.get("subdomain")
    )
    db_html = website.get("html_content") or ""

    serving_html = None
    if is_published:
        serving_html = await _fetch_serving_snapshot(website["subdomain"])

    from app.utils.html_balance import is_html_balanced

    base_html = None
    base_source = None
    for candidate, source in ((serving_html, "storage"), (db_html, "db")):
        if candidate and is_html_balanced(candidate)[0]:
            base_html = candidate
            base_source = source
            break

    if base_html is None:
        # Same rule as the contact endpoint: never republish an unbalanced or
        # missing base over a live site.
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": "no_balanced_html_base",
                "message": (
                    "Laman web ini belum ada HTML yang lengkap untuk diubah "
                    "warnanya. Sila jana semula laman web anda dahulu."
                ),
            },
        )

    current_palette = detect_palette(base_html)

    # ---- Resolve the target palette (colors > palette > shuffle) ----------
    palette_key = None
    resolved: Dict[str, str] = {}

    if body.palette:
        resolved = ds.get_named_palette(body.palette, body.color_mode)
        if not resolved:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown palette '{body.palette}'",
            )
        palette_key = body.palette
    elif body.shuffle:
        current_key = ds.match_palette_key(current_palette.get("primary", ""))
        palette_key = ds.next_palette_key(current_key or None, body.shuffle_step)
        resolved = ds.get_named_palette(palette_key, body.color_mode)

    if body.colors:
        # Explicit brand hexes layer on top of (or entirely replace) the
        # resolved palette. Roles the merchant did not name keep the page's
        # current value so a single-colour tweak never blanks the rest.
        base_layer = resolved or current_palette
        resolved = {**base_layer, **body.colors}
        if not body.palette and not body.shuffle:
            palette_key = None

    fonts = {}
    if body.font_key:
        fonts = ds.get_font_pairing_by_key(body.font_key)
        if not fonts:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown font_key '{body.font_key}'",
            )

    if not resolved and not fonts:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide at least one of: palette, colors, shuffle, font_key",
        )

    # ---- Patch ------------------------------------------------------------
    result = apply_theme(base_html, palette=clean_palette(resolved), fonts=fonts or None)

    if not result.changed:
        return {
            "success": True,
            "changed": False,
            "message": "Tiada perubahan — laman web sudah menggunakan tema ini.",
            "website_id": website_id,
            "palette_key": palette_key,
            "palette": result.palette,
            "fonts": result.fonts,
            "base_source": base_source,
            "live_site_updated": False,
        }

    balanced, unbalanced = is_html_balanced(result.html)
    if not balanced:
        # A token rewrite must never unbalance HTML — refuse rather than ship it.
        logger.error(
            f"[theme] refusing to publish unbalanced HTML for "
            f"{website.get('subdomain')} (tags: {unbalanced})"
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": "rewrite_produced_unbalanced_html",
                "message": "Perubahan tema dibatalkan kerana struktur HTML tidak sah.",
            },
        )

    update_data = {
        "html_content": result.html,
        "updated_at": datetime.utcnow().isoformat(),
    }

    live_site_updated = False
    warning = None
    if is_published:
        try:
            await storage_service.publish_website(
                subdomain=website["subdomain"],
                html_content=result.html,
                website_id=website_id,
                user_id=user_id,
            )
            live_site_updated = True
        except Exception as storage_err:
            warning = "storage_refresh_failed"
            logger.warning(
                f"⚠️ Theme update: storage refresh failed "
                f"(DB will still be updated): {storage_err}"
            )

    await supabase_service.update_website(website_id, update_data)

    logger.info(
        f"🎨 Theme updated credit-free for {website_id} "
        f"(palette={palette_key or 'custom'}, base={base_source}, "
        f"live={live_site_updated}, {result.summary()})"
    )

    if is_published and not live_site_updated:
        message = (
            "Tema disimpan, tetapi laman web langsung belum dikemas kini. "
            "Sila cuba lagi sebentar."
        )
    else:
        message = "Tema laman web dikemas kini."

    response = {
        "success": True,
        "changed": True,
        "message": message,
        "website_id": website_id,
        "palette_key": palette_key,
        "palette": result.palette,
        "previous_palette": result.previous_palette,
        "fonts": result.fonts,
        "replacements": result.summary(),
        "base_source": base_source,
        "live_site_updated": live_site_updated,
        "html_content": result.html,
    }
    if result.notes:
        response["notes"] = result.notes
    if warning:
        response["warning"] = warning
    return response
