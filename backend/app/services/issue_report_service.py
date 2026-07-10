"""
Issue Report Service — "Report Issue → Free Regeneration" make-good flow.

Feature-flagged behind ISSUE_REPORT_ENABLED (env, default false, read at
call time). Within a per-site cap (ISSUE_FREE_REGEN_CAP, default 2) a report
auto-grants ONE free regeneration; the grant is its own explicit mechanism
(websites.free_regens_granted + the report row) and NEVER touches the user's
usage_tracking counters, subscription rows, or addon credits — see the
regenerate endpoint in api/v1/endpoints/websites.py for how the bypass flag
is threaded through.

Storage: website_issue_reports table (migration 052), accessed with the
service-role key via PostgREST — same pattern as subscription_service.
"""

import hashlib
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import httpx
from loguru import logger

from app.core.config import settings

# Category enum — mirrors the CHECK constraint in migration 052.
REPORT_CATEGORIES = (
    "images_wrong",
    "text_wrong",
    "page_broken",
    "sensitive_content",
    "other",
)

# Statuses that count as "still open" for the duplicate-report check.
OPEN_STATUSES = ("open", "auto_regen_granted")

# Rate limits. Fixed 24h windows counted from the DB (the token-bucket
# middleware in production/rate_limiter.py is per-IP-per-minute — wrong
# shape for a per-site/per-user daily cap, so we count rows instead).
MAX_REPORTS_PER_SITE_24H = 3
MAX_REPORTS_PER_USER_24H = 10


def issue_report_enabled() -> bool:
    """Feature flag for the whole report-issue flow. Read at call time so
    env flips take effect without a redeploy/re-import (same rationale as
    ai_service.image_provider)."""
    return os.getenv("ISSUE_REPORT_ENABLED", "false").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


def issue_free_regen_cap(default: int = 2) -> int:
    """Max free regenerations auto-granted per site, ever. Read at call
    time; never negative; malformed env value falls back to the default."""
    try:
        value = int(os.getenv("ISSUE_FREE_REGEN_CAP", str(default)))
    except (TypeError, ValueError):
        return default
    return max(0, value)


def build_diagnostics(website: Dict[str, Any]) -> Dict[str, Any]:
    """Lightweight bug-radar snapshot stored on the report row.

    IDs, hashes and small metadata only — never the HTML itself (the
    existing storage pattern keeps published HTML in Supabase Storage;
    the hash is enough to correlate a report with the exact content the
    user saw).
    """
    # Imported at call time so the module-level flags reflect the current
    # process state and tests can patch them.
    from app.services import ai_service as ai_service_module

    html = website.get("html_content") or ""
    return {
        "html_sha256": hashlib.sha256(html.encode("utf-8")).hexdigest() if html else None,
        "html_length": len(html),
        "generation_provider": "glm" if ai_service_module.USE_GLM_FOR_HTML else "deepseek",
        "image_provider": ai_service_module.image_provider(),
        "generation_count": website.get("generation_count"),
        "website_status": website.get("status"),
        "last_error_message": website.get("error_message"),
        "last_generated_at": website.get("updated_at"),
        "captured_at": datetime.utcnow().isoformat(),
    }


class IssueReportService:
    """Service-role PostgREST access for website_issue_reports."""

    TABLE = "website_issue_reports"

    def __init__(self):
        self.url = settings.SUPABASE_URL
        self.service_key = settings.SUPABASE_SERVICE_ROLE_KEY
        self.headers = {
            "apikey": self.service_key,
            "Authorization": f"Bearer {self.service_key}",
            "Content-Type": "application/json",
        }

    # ------------------------------------------------------------------
    # Report creation path
    # ------------------------------------------------------------------

    async def find_existing_open_report(
        self, website_id: str, category: str
    ) -> Optional[Dict[str, Any]]:
        """An open/auto_regen_granted report of the same category on the
        same site — the duplicate the endpoint returns instead of a new row."""
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{self.url}/rest/v1/{self.TABLE}",
                    headers=self.headers,
                    params={
                        "website_id": f"eq.{website_id}",
                        "category": f"eq.{category}",
                        "status": f"in.({','.join(OPEN_STATUSES)})",
                        "order": "created_at.desc",
                        "limit": "1",
                    },
                )
            if resp.status_code == 200 and resp.json():
                return resp.json()[0]
            return None
        except Exception as e:
            logger.error(f"[ISSUE REPORT] duplicate lookup failed for {website_id}: {e}")
            return None

    async def _count_since(self, filters: Dict[str, str], since_iso: str) -> int:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.url}/rest/v1/{self.TABLE}",
                headers={**self.headers, "Prefer": "count=exact"},
                params={
                    **filters,
                    "created_at": f"gte.{since_iso}",
                    "select": "id",
                },
            )
        if resp.status_code != 200:
            raise RuntimeError(
                f"count query failed: status={resp.status_code} body={resp.text[:200]}"
            )
        content_range = resp.headers.get("content-range", "")
        if "/" in content_range:
            try:
                return int(content_range.split("/")[1])
            except (ValueError, IndexError):
                pass
        return len(resp.json())

    async def count_recent_reports(
        self, *, website_id: Optional[str] = None, user_id: Optional[str] = None
    ) -> int:
        """Reports created in the last 24h for a site or a user.

        Raises on query failure — the caller treats that as 'cannot verify
        the rate limit' and REJECTS the report (fail closed): this path
        mints quota-bypassing grants, so an outage must not become an
        unlimited-grant hole.
        """
        since = (datetime.utcnow() - timedelta(hours=24)).isoformat()
        filters: Dict[str, str] = {}
        if website_id:
            filters["website_id"] = f"eq.{website_id}"
        if user_id:
            filters["user_id"] = f"eq.{user_id}"
        return await self._count_since(filters, since)

    async def create_report(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{self.url}/rest/v1/{self.TABLE}",
                    headers={**self.headers, "Prefer": "return=representation"},
                    json=data,
                )
            if resp.status_code in (200, 201):
                rows = resp.json()
                return rows[0] if isinstance(rows, list) and rows else rows
            logger.error(
                f"[ISSUE REPORT] insert failed: status={resp.status_code} body={resp.text[:300]}"
            )
            return None
        except Exception as e:
            logger.error(f"[ISSUE REPORT] insert error: {e}")
            return None

    async def increment_free_regens_granted(
        self, website_id: str, current_value: int
    ) -> bool:
        """Bump websites.free_regens_granted. Read-modify-write like the
        rest of the codebase (increment_usage); the per-site 24h rate limit
        plus the cap check keep any theoretical race a one-off, and the
        counter only ever gates FREE make-goods — it cannot touch paid quota."""
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.patch(
                    f"{self.url}/rest/v1/websites",
                    headers={**self.headers, "Prefer": "return=minimal"},
                    params={"id": f"eq.{website_id}"},
                    json={"free_regens_granted": current_value + 1},
                )
            return resp.status_code in (200, 204)
        except Exception as e:
            logger.error(
                f"[ISSUE REPORT] failed to bump free_regens_granted for {website_id}: {e}"
            )
            return False

    # ------------------------------------------------------------------
    # Free-regeneration path
    # ------------------------------------------------------------------

    async def get_unused_granted_report(
        self, website_id: str
    ) -> Optional[Dict[str, Any]]:
        """Oldest unconsumed granted report for this site, if any. This is
        the entitlement the regenerate endpoint checks before falling back
        to the normal quota path."""
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{self.url}/rest/v1/{self.TABLE}",
                    headers=self.headers,
                    params={
                        "website_id": f"eq.{website_id}",
                        "status": "eq.auto_regen_granted",
                        "regen_used": "eq.false",
                        "order": "created_at.asc",
                        "limit": "1",
                    },
                )
            if resp.status_code == 200 and resp.json():
                return resp.json()[0]
            return None
        except Exception as e:
            logger.error(
                f"[ISSUE REPORT] granted-report lookup failed for {website_id}: {e}"
            )
            return None

    async def mark_regen_completed(self, report_id: str) -> bool:
        """Consume the grant: regen_used=true + status=resolved. Called
        ONLY after the regeneration succeeded — a failed generation leaves
        the report untouched so the user can retry.

        The filter re-asserts regen_used=false so a stray double call
        can't re-resolve an already-consumed report.
        """
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.patch(
                    f"{self.url}/rest/v1/{self.TABLE}",
                    headers={**self.headers, "Prefer": "return=representation"},
                    params={
                        "id": f"eq.{report_id}",
                        "regen_used": "eq.false",
                    },
                    json={
                        "regen_used": True,
                        "status": "resolved",
                        "resolved_at": datetime.utcnow().isoformat(),
                    },
                )
            if resp.status_code in (200, 204):
                return True
            logger.error(
                f"[ISSUE REPORT] mark_regen_completed failed for {report_id}: "
                f"status={resp.status_code} body={resp.text[:200]}"
            )
            return False
        except Exception as e:
            logger.error(f"[ISSUE REPORT] mark_regen_completed error for {report_id}: {e}")
            return False

    # ------------------------------------------------------------------
    # Admin
    # ------------------------------------------------------------------

    async def list_reports(
        self,
        status_filter: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """Reports newest-first with embedded site + user metadata."""
        params = {
            "select": (
                "*,websites(id,subdomain,business_name,status,free_regens_granted),"
                "profiles(id,email)"
            ),
            "order": "created_at.desc",
            "limit": str(limit),
            "offset": str(offset),
        }
        if status_filter:
            params["status"] = f"eq.{status_filter}"
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.url}/rest/v1/{self.TABLE}",
                headers=self.headers,
                params=params,
            )
        if resp.status_code == 200:
            return resp.json()
        raise RuntimeError(
            f"list_reports failed: status={resp.status_code} body={resp.text[:200]}"
        )

    async def get_report(self, report_id: str) -> Optional[Dict[str, Any]]:
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{self.url}/rest/v1/{self.TABLE}",
                    headers=self.headers,
                    params={"id": f"eq.{report_id}", "limit": "1"},
                )
            if resp.status_code == 200 and resp.json():
                return resp.json()[0]
            return None
        except Exception as e:
            logger.error(f"[ISSUE REPORT] get_report failed for {report_id}: {e}")
            return None

    async def update_report(self, report_id: str, data: Dict[str, Any]) -> bool:
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.patch(
                    f"{self.url}/rest/v1/{self.TABLE}",
                    headers={**self.headers, "Prefer": "return=minimal"},
                    params={"id": f"eq.{report_id}"},
                    json=data,
                )
            return resp.status_code in (200, 204)
        except Exception as e:
            logger.error(f"[ISSUE REPORT] update_report failed for {report_id}: {e}")
            return False


# Singleton, matching subscription_service / supabase_service style.
issue_report_service = IssueReportService()
