"""Read the HTML a published subdomain is ACTUALLY serving.

The subdomain middleware serves the Supabase Storage snapshot, not the
`websites.html_content` column. Those two can silently diverge — the DB blob
may be stale or truncated — so any in-place edit of a live page must be made
against the storage snapshot, never blindly against the DB row. (Publishing a
truncated DB blob over a good live snapshot is exactly how a merchant's
injected widgets once vanished.)

Extracted so every credit-free edit path (contact details, theme repaint, …)
reads the live page the same way instead of each re-implementing it.
"""

from __future__ import annotations

from typing import Optional

import httpx
from loguru import logger

from app.core.config import settings


async def fetch_published_snapshot(
    subdomain: str, cache_bust: str = "edit", timeout: float = 10.0
) -> Optional[str]:
    """Fetch `{subdomain}/index.html` from Supabase Storage, or None.

    `cache_bust` is appended as a query param so an edge cache can never hand
    back a stale copy of the page we are about to rewrite. Both the current
    serving key and the legacy `demo-user/` path are tried, mirroring the
    subdomain middleware's own lookup order.
    """
    supabase_url = settings.SUPABASE_URL
    bucket = settings.STORAGE_BUCKET_NAME
    if not supabase_url or not subdomain:
        return None

    base = f"{supabase_url}/storage/v1/object/public/{bucket}"
    for path in (f"{subdomain}/index.html", f"demo-user/{subdomain}/index.html"):
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.get(f"{base}/{path}?cb={cache_bust}")
            if resp.status_code == 200 and resp.text:
                return resp.text
        except Exception as exc:
            logger.warning(f"[snapshot] fetch failed for {path}: {exc}")
    return None
