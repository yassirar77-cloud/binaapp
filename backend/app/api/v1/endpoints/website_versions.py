"""Version history — list, preview and restore earlier copies of a page.

    GET   /api/v1/websites/{id}/versions                   metadata, newest first
    GET   /api/v1/websites/{id}/versions/{version_id}      one version + html
    PATCH /api/v1/websites/{id}/versions/{version_id}      name a version
    POST  /api/v1/websites/{id}/versions/{version_id}/restore

Snapshots are taken by the paths that overwrite a page (editor save,
regenerate, theme, contact, hero video) — see services/website_versions.py.

QUOTA NOTE (protected zone): nothing here touches check_limit,
subscription_service, usage_tracking or any credit counter. A restore is a
credit-free write in the same shape as PATCH /websites/{id}/theme.

PUBLISH SAFETY
--------------
A restore republishes over a live site, so it follows the contact/theme
rules: only a structurally BALANCED version may be restored, the page being
replaced is snapshotted first (so a restore is itself undoable), and the
response is honest about whether the live site actually changed.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger
from pydantic import BaseModel, Field

from app.core.security import get_current_user
from app.services import website_versions as versions
from app.services.storage_service import storage_service
from app.services.supabase_client import supabase_service

# Mounted under /websites in router.py.
router = APIRouter()


class LabelRequest(BaseModel):
    label: Optional[str] = Field(default=None, max_length=versions.LABEL_MAX)


async def _fetch_serving_snapshot(subdomain: str) -> Optional[str]:
    """The live storage snapshot — see services/serving_snapshot.py."""
    from app.services.serving_snapshot import fetch_published_snapshot

    return await fetch_published_snapshot(subdomain, cache_bust="version-restore")


async def _load_owned_website(website_id: str, user_id: str) -> dict:
    website = await supabase_service.get_website(website_id)
    if not website:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Website not found")
    if website.get("user_id") != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this website",
        )
    return website


def _history_unavailable(err: Exception) -> HTTPException:
    logger.warning(f"[versions] history unavailable: {err}")
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail={
            "error": "version_history_unavailable",
            "message": "Sejarah versi tidak dapat dimuatkan sekarang. Sila cuba lagi.",
        },
    )


async def _load_version(website_id: str, version_id: str) -> dict:
    try:
        version = await versions.get_version(website_id, version_id)
    except Exception as err:
        raise _history_unavailable(err)
    if not version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "version_not_found", "message": "Versi ini tidak ditemui."},
        )
    return version


def _meta(row: dict) -> dict:
    return {k: v for k, v in row.items() if k not in ("html", "content_hash")}


@router.get("/{website_id}/versions")
async def list_website_versions(
    website_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Earlier copies of this page, newest first. Metadata only."""
    await _load_owned_website(website_id, current_user.get("sub"))
    try:
        rows = await versions.list_versions(website_id)
    except Exception as err:
        raise _history_unavailable(err)
    return {
        "success": True,
        "website_id": website_id,
        "max_versions": versions.MAX_VERSIONS,
        "versions": [_meta(r) for r in rows],
    }


@router.get("/{website_id}/versions/{version_id}")
async def get_website_version(
    website_id: str,
    version_id: str,
    current_user: dict = Depends(get_current_user),
):
    """One version with its HTML, for the preview iframe."""
    await _load_owned_website(website_id, current_user.get("sub"))
    version = await _load_version(website_id, version_id)
    return {"success": True, "version": _meta(version), "html_content": version.get("html") or ""}


@router.patch("/{website_id}/versions/{version_id}")
async def label_website_version(
    website_id: str,
    version_id: str,
    body: LabelRequest,
    current_user: dict = Depends(get_current_user),
):
    """Give a version a name ("sebelum promosi raya"). Empty clears it."""
    await _load_owned_website(website_id, current_user.get("sub"))
    try:
        row = await versions.set_label(website_id, version_id, body.label)
    except Exception as err:
        raise _history_unavailable(err)
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "version_not_found", "message": "Versi ini tidak ditemui."},
        )
    return {"success": True, "version": _meta(row)}


@router.post("/{website_id}/versions/{version_id}/restore")
async def restore_website_version(
    website_id: str,
    version_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Put an earlier copy of the page back. Credit-FREE, and undoable:
    the page being replaced is stored as a new version first."""
    user_id = current_user.get("sub")
    website = await _load_owned_website(website_id, user_id)

    if website.get("status") == "generating":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": "generation_in_progress",
                "message": "Laman web sedang dijana. Sila tunggu sehingga siap.",
            },
        )

    version = await _load_version(website_id, version_id)
    target_html = version.get("html") or ""

    from app.utils.html_balance import is_html_balanced

    balanced, unbalanced = is_html_balanced(target_html) if target_html.strip() else (False, [])
    if not balanced:
        # Never republish a broken document over a live site.
        logger.error(
            f"[versions] refusing to restore unbalanced version {version_id} "
            f"for {website.get('subdomain')} (tags: {unbalanced})"
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": "version_html_unbalanced",
                "message": "Versi ini tidak lengkap dan tidak boleh dipulihkan.",
            },
        )

    is_published = bool(website.get("status") == "published" and website.get("subdomain"))
    db_html = website.get("html_content") or ""

    # What is about to be replaced: the page visitors see when live (the
    # storage snapshot and the DB blob can diverge), else the draft.
    current_html = None
    if is_published:
        current_html = await _fetch_serving_snapshot(website["subdomain"])
    if not current_html:
        current_html = db_html

    if current_html == target_html and db_html == target_html:
        return {
            "success": True,
            "changed": False,
            "message": "Tiada perubahan — laman web sudah sama dengan versi ini.",
            "website_id": website_id,
            "version_id": version_id,
            "live_site_updated": False,
            "html_content": target_html,
        }

    saved = await versions.snapshot(website_id, current_html, "restore", user_id)
    if current_html != db_html:
        # Diverged draft: keep it too, so nothing the merchant had is lost.
        await versions.snapshot(website_id, db_html, "restore", user_id)

    live_site_updated = False
    warning = None
    if is_published:
        try:
            await storage_service.publish_website(
                subdomain=website["subdomain"],
                html_content=target_html,
                website_id=website_id,
                user_id=user_id,
            )
            live_site_updated = True
        except Exception as storage_err:
            warning = "storage_refresh_failed"
            logger.warning(
                f"⚠️ Version restore: storage refresh failed "
                f"(DB will still be updated): {storage_err}"
            )

    if not await supabase_service.update_website(
        website_id,
        {"html_content": target_html, "updated_at": datetime.utcnow().isoformat()},
    ):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Gagal memulihkan versi. Sila cuba lagi.",
        )

    logger.info(
        f"⏪ Version {version_id} restored credit-free for {website_id} "
        f"(live={live_site_updated}, undo_saved={bool(saved)})"
    )

    if is_published and not live_site_updated:
        message = (
            "Versi dipulihkan, tetapi laman web langsung belum dikemas kini. "
            "Sila cuba lagi sebentar."
        )
    else:
        message = "Versi dipulihkan."

    response = {
        "success": True,
        "changed": True,
        "message": message,
        "website_id": website_id,
        "version_id": version_id,
        "undo_version_id": (saved or {}).get("id"),
        "live_site_updated": live_site_updated,
        "html_content": target_html,
    }
    if warning:
        response["warning"] = warning
    return response
