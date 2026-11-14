"""Website version history — the undo behind every page overwrite.

A bad regenerate or a wrong editor save used to be permanent: the only copy
of the page was the one that had just been replaced. Every path that
overwrites a site's HTML now calls :func:`snapshot` FIRST with the page as it
was, and the merchant can put any of those back from the editor.

Rules this module keeps:

  * A version is the page BEFORE the change named in ``source``.
  * :func:`snapshot` NEVER raises. A failed snapshot must not block a save —
    the save is what the merchant asked for; history is a safety net.
  * Empty or structurally unbalanced HTML is never stored (restoring it would
    republish a broken page — the mimba failure shape).
  * A snapshot identical to the newest one is skipped (SHA-256 compare), and
    a burst of same-kind edits (ten theme shuffles, autosaves) collapses to
    the first one: that row already holds the page from before the burst.
  * Only the newest ``MAX_VERSIONS`` rows per site are kept.

Credit-free: nothing here touches quota, usage tracking or the AI.
Table: migration 066_website_versions.sql (service role only).
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from loguru import logger

from app.services.supabase_client import supabase_service

TABLE = "website_versions"
MAX_VERSIONS = 20
LABEL_MAX = 80

SOURCES = (
    "manual_save",
    "regenerate",
    "theme",
    "contact",
    "hero_video",
    "restore",
    "publish",
)

#: Sources where several edits in a row are one sitting, not several
#: decisions. Within the window only the first snapshot is kept.
BURST_SOURCES = frozenset({"manual_save", "theme", "contact", "hero_video"})
BURST_WINDOW_SECONDS = 600

META_COLUMNS = "id,website_id,source,label,size_bytes,content_hash,created_at,created_by"


def content_hash(html: str) -> str:
    return hashlib.sha256((html or "").encode("utf-8")).hexdigest()


def _age_seconds(created_at: Any) -> Optional[float]:
    try:
        stamp = datetime.fromisoformat(str(created_at).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    if stamp.tzinfo is None:
        stamp = stamp.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - stamp).total_seconds()


# ---------------------------------------------------------------------------
# Storage (PostgREST with the service role). Kept as four small functions so
# tests replace the table with a list.
# ---------------------------------------------------------------------------

def _rest_url() -> str:
    return f"{supabase_service.url}/rest/v1/{TABLE}"


async def _select(params: Dict[str, str]) -> List[Dict[str, Any]]:
    async with supabase_service._client() as client:
        response = await client.get(_rest_url(), headers=supabase_service.headers, params=params)
    if response.status_code != 200:
        raise RuntimeError(f"{TABLE} select failed: {response.status_code} {response.text[:200]}")
    return response.json() or []


async def _insert(row: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    async with supabase_service._client() as client:
        response = await client.post(
            _rest_url(),
            headers={**supabase_service.headers, "Prefer": "return=representation"},
            json=row,
        )
    if response.status_code not in (200, 201):
        raise RuntimeError(f"{TABLE} insert failed: {response.status_code} {response.text[:200]}")
    data = response.json()
    return data[0] if isinstance(data, list) and data else (data or None)


async def _delete(ids: List[str]) -> None:
    if not ids:
        return
    async with supabase_service._client() as client:
        response = await client.delete(
            _rest_url(),
            headers=supabase_service.headers,
            params={"id": f"in.({','.join(ids)})"},
        )
    if response.status_code not in (200, 204):
        raise RuntimeError(f"{TABLE} delete failed: {response.status_code} {response.text[:200]}")


async def _update(version_id: str, website_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    async with supabase_service._client() as client:
        response = await client.patch(
            _rest_url(),
            headers={**supabase_service.headers, "Prefer": "return=representation"},
            params={
                "id": f"eq.{version_id}",
                "website_id": f"eq.{website_id}",
                "select": META_COLUMNS,
            },
            json=data,
        )
    if response.status_code not in (200, 204):
        raise RuntimeError(f"{TABLE} update failed: {response.status_code} {response.text[:200]}")
    rows = response.json() if response.content else []
    return rows[0] if rows else None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def list_versions(website_id: str, limit: int = MAX_VERSIONS) -> List[Dict[str, Any]]:
    """Metadata only (no html), newest first. Raises on a storage failure."""
    return await _select({
        "website_id": f"eq.{website_id}",
        "select": META_COLUMNS,
        "order": "created_at.desc",
        "limit": str(limit),
    })


async def get_version(website_id: str, version_id: str) -> Optional[Dict[str, Any]]:
    """One version with its html, or None. Scoped to the website so a
    version id from another merchant's site can never be read."""
    rows = await _select({
        "id": f"eq.{version_id}",
        "website_id": f"eq.{website_id}",
        "select": "*",
        "limit": "1",
    })
    return rows[0] if rows else None


async def set_label(website_id: str, version_id: str, label: Optional[str]) -> Optional[Dict[str, Any]]:
    cleaned = (label or "").strip()[:LABEL_MAX] or None
    return await _update(version_id, website_id, {"label": cleaned})


async def prune(website_id: str, keep: int = MAX_VERSIONS) -> int:
    """Delete everything older than the newest ``keep`` rows."""
    rows = await _select({
        "website_id": f"eq.{website_id}",
        "select": "id",
        "order": "created_at.desc",
        "offset": str(keep),
        "limit": "200",
    })
    ids = [str(r["id"]) for r in rows if r.get("id")]
    await _delete(ids)
    return len(ids)


async def snapshot(
    website_id: str,
    html: Optional[str],
    source: str,
    user_id: Optional[str] = None,
    label: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Store ``html`` — the page as it was before a ``source`` change.

    Returns the stored row's metadata, or None when nothing was stored
    (empty / unbalanced / duplicate / burst / storage failure). Never raises.
    """
    try:
        if not website_id or not html or not html.strip():
            return None
        if source not in SOURCES:
            source = "manual_save"

        from app.utils.html_balance import is_html_balanced

        if not is_html_balanced(html)[0]:
            logger.info(f"[versions] skip unbalanced snapshot for {website_id} ({source})")
            return None

        digest = content_hash(html)
        newest = await _select({
            "website_id": f"eq.{website_id}",
            "select": "id,content_hash,source,created_at",
            "order": "created_at.desc",
            "limit": "1",
        })
        if newest:
            last = newest[0]
            if last.get("content_hash") == digest:
                return None
            if source in BURST_SOURCES and last.get("source") == source:
                age = _age_seconds(last.get("created_at"))
                if age is not None and 0 <= age < BURST_WINDOW_SECONDS:
                    return None

        row: Dict[str, Any] = {
            "website_id": website_id,
            "html": html,
            "content_hash": digest,
            "source": source,
            "size_bytes": len(html.encode("utf-8")),
        }
        if user_id:
            row["created_by"] = user_id
        if label:
            row["label"] = label.strip()[:LABEL_MAX]

        stored = await _insert(row)
        try:
            await prune(website_id)
        except Exception as prune_err:
            logger.warning(f"[versions] prune failed for {website_id}: {prune_err}")

        logger.info(f"[versions] snapshot stored for {website_id} ({source}, {row['size_bytes']} bytes)")
        if stored:
            stored = {k: v for k, v in stored.items() if k != "html"}
        return stored
    except Exception as err:
        logger.warning(f"[versions] snapshot failed for {website_id} ({source}) — save continues: {err}")
        return None
