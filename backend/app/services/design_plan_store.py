"""
Persistence for the design-plan learning loop (migration 057).

Two jobs:

1. **Rolling direction history.** ``recent_directions(category)`` returns the
   last N direction keys used for a vertical so Pass 1 can exclude them —
   two same-category sites in a row never share a direction.
2. **Outcomes.** ``record_plan`` stores the plan, its critique scores, the
   lint report and the HTML hash; ``mark_outcome`` stamps what the merchant
   did next (published / edited / regenerated). The weekly stats job reads
   these.

Everything is best-effort: no Supabase, a missing table, or a network
error never raises into the generation path. A process-local ring buffer
mirrors the history so rotation still works in tests and in environments
without a database.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from collections import defaultdict, deque
from datetime import datetime, timezone
from typing import Any, Deque, Dict, List, Optional

logger = logging.getLogger(__name__)

TABLE = "design_plans"
HISTORY_WINDOW = 3

_local_history: Dict[str, Deque[str]] = defaultdict(lambda: deque(maxlen=HISTORY_WINDOW * 4))
_disabled_reason: Optional[str] = None


def _enabled() -> bool:
    if os.getenv("DESIGN_PLAN_STORE_ENABLED", "true").strip().lower() in ("0", "false", "no", "off"):
        return False
    return bool(os.getenv("SUPABASE_URL")) and bool(
        os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY")
    )


def _headers() -> Dict[str, str]:
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY") or ""
    return {"apikey": key, "Authorization": f"Bearer {key}", "Content-Type": "application/json"}


def _url() -> str:
    return f"{os.getenv('SUPABASE_URL', '').rstrip('/')}/rest/v1/{TABLE}"


def html_hash(html: str) -> str:
    return hashlib.sha256((html or "").encode("utf-8")).hexdigest()


def remember_locally(category: str, direction: str) -> None:
    if direction:
        _local_history[category or "general"].appendleft(direction)


def local_recent(category: str, n: int = HISTORY_WINDOW) -> List[str]:
    out: List[str] = []
    for key in _local_history.get(category or "general", ()):
        if key not in out:
            out.append(key)
        if len(out) >= n:
            break
    return out


def reset_local_history() -> None:
    _local_history.clear()


async def recent_directions(category: str, n: int = HISTORY_WINDOW) -> List[str]:
    """Last ``n`` distinct direction keys for ``category``, newest first.
    DB first (cross-process), merged with the local ring."""
    global _disabled_reason
    found: List[str] = []
    if _enabled() and _disabled_reason is None:
        try:
            import httpx

            params = {
                "select": "direction,created_at",
                "category": f"eq.{category or 'general'}",
                "order": "created_at.desc",
                "limit": str(n * 3),
            }
            async with httpx.AsyncClient(timeout=6.0) as client:
                r = await client.get(_url(), headers=_headers(), params=params)
            if r.status_code == 200:
                for row in r.json() or []:
                    key = (row or {}).get("direction")
                    if key and key not in found:
                        found.append(key)
                    if len(found) >= n:
                        break
            elif r.status_code == 404:
                _disabled_reason = "design_plans table missing (run migration 057)"
                logger.warning(f"🎨 Plan store disabled: {_disabled_reason}")
        except Exception as err:  # never into the generation path
            logger.warning(f"🎨 Plan history read failed: {err}")
    for key in local_recent(category, n):
        if key not in found:
            found.append(key)
    return found[:n]


async def record_plan(
    *,
    plan: Dict[str, Any],
    category: str,
    job_id: Optional[str] = None,
    website_id: Optional[str] = None,
    user_id: Optional[str] = None,
    critique: Optional[Dict[str, Any]] = None,
    lint: Optional[Dict[str, Any]] = None,
    html: Optional[str] = None,
    attempts: int = 1,
) -> Optional[str]:
    """Persist one generation's plan + scores. Returns the row id or None."""
    direction = str(plan.get("direction") or "")
    remember_locally(category, direction)
    if not _enabled() or _disabled_reason is not None:
        return None
    row = {
        "job_id": job_id,
        "website_id": website_id,
        "user_id": user_id,
        "category": category or "general",
        "direction": direction,
        "plan": plan,
        "plan_source": plan.get("source") or "ai",
        "critique": critique,
        "critique_avg": (critique or {}).get("average"),
        "lint": lint,
        "html_sha256": html_hash(html) if html else None,
        "attempts": attempts,
    }
    try:
        import httpx

        async with httpx.AsyncClient(timeout=8.0) as client:
            r = await client.post(_url(), headers={**_headers(), "Prefer": "return=representation"}, json=row)
        if r.status_code in (200, 201):
            data = r.json()
            first = data[0] if isinstance(data, list) and data else data
            return (first or {}).get("id")
        logger.warning(f"🎨 Plan record failed: {r.status_code} {r.text[:200]}")
    except Exception as err:
        logger.warning(f"🎨 Plan record failed: {err}")
    return None


async def attach_website(job_id: str, website_id: str) -> None:
    """Stamp the website id onto the job's plan row once the draft exists."""
    if not (job_id and website_id) or not _enabled() or _disabled_reason is not None:
        return
    try:
        import httpx

        async with httpx.AsyncClient(timeout=6.0) as client:
            await client.patch(
                _url(), headers=_headers(), params={"job_id": f"eq.{job_id}"}, json={"website_id": website_id}
            )
    except Exception as err:
        logger.warning(f"🎨 Plan attach failed: {err}")


async def mark_outcome(website_id: Optional[str], outcome: str, job_id: Optional[str] = None) -> None:
    """published | edited | regenerated | discarded — best-effort."""
    if outcome not in ("generated", "published", "edited", "regenerated", "discarded"):
        return
    if not (website_id or job_id) or not _enabled() or _disabled_reason is not None:
        return
    try:
        import httpx

        params = {"website_id": f"eq.{website_id}"} if website_id else {"job_id": f"eq.{job_id}"}
        async with httpx.AsyncClient(timeout=6.0) as client:
            await client.patch(
                _url(),
                headers=_headers(),
                params=params,
                json={"outcome": outcome, "outcome_at": datetime.now(timezone.utc).isoformat()},
            )
    except Exception as err:
        logger.warning(f"🎨 Plan outcome update failed: {err}")


async def fetch_all(limit: int = 5000) -> List[Dict[str, Any]]:
    """Every row (for the weekly stats job)."""
    if not _enabled():
        return []
    try:
        import httpx

        params = {"select": "category,direction,plan_source,critique_avg,outcome,created_at", "order": "created_at.desc", "limit": str(limit)}
        async with httpx.AsyncClient(timeout=20.0) as client:
            r = await client.get(_url(), headers=_headers(), params=params)
        if r.status_code == 200:
            return r.json() or []
    except Exception as err:
        logger.warning(f"🎨 Plan fetch failed: {err}")
    return []
