"""
PDPA-safe visitor tracking pipeline (write side).

Called as a FastAPI BackgroundTask from POST /api/analytics/track so the
endpoint can return 204 immediately. Everything that touches the database
happens here, after the visitor's request has already been answered.

Privacy properties (Polisi Privasi v3.0):
- Cookieless: no localStorage/cookie visitor id — uniqueness comes from a
  server-side hash the browser never sees.
- The visitor hash is sha256(salt | YYYY-MM-DD (MYT) | ip | user_agent |
  website_id): salted with a server secret and rotated at Asia/Kuala_Lumpur
  midnight, so hashes are unlinkable across days and across websites.
- The raw IP and user agent are used transiently in memory to compute the
  hash and are never stored and never logged.
- Only daily rollup counters are persisted (via the track_site_pageview
  RPC from migration 050); there is no raw event table.
"""
import hashlib
from datetime import datetime
from typing import Optional
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

import httpx
from loguru import logger

from app.core.config import settings

MYT = ZoneInfo("Asia/Kuala_Lumpur")

# Substrings that mark obvious bot/crawler user agents (cheap filter; the
# goal is keeping merchant numbers honest, not perfect bot detection).
BOT_UA_MARKERS = ("bot", "spider", "crawl", "preview", "curl", "wget", "python-requests")

MAX_PAGE_PATH_LEN = 200


def _hash_salt() -> str:
    return settings.ANALYTICS_HASH_SALT or settings.JWT_SECRET_KEY


def myt_today() -> str:
    """Current date in Asia/Kuala_Lumpur as YYYY-MM-DD."""
    return datetime.now(MYT).date().isoformat()


def compute_visitor_hash(
    ip: str,
    user_agent: str,
    website_id: str,
    date_str: Optional[str] = None,
    salt: Optional[str] = None,
) -> str:
    """Daily-rotating salted visitor hash. Never store or log the inputs."""
    date_str = date_str or myt_today()
    salt = salt or _hash_salt()
    raw = f"{salt}|{date_str}|{ip}|{user_agent}|{website_id}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


def is_bot_user_agent(user_agent: str) -> bool:
    ua = (user_agent or "").lower()
    return any(marker in ua for marker in BOT_UA_MARKERS)


def client_ip_from_headers(headers, fallback: str = "unknown") -> str:
    """Best visitor IP behind a proxy (Render/Cloudflare).

    request.client.host is the edge/proxy IP on hosted deploys, which would
    collapse distinct visitors sharing a user agent into one hash. Prefer
    the forwarded headers (same order rate_limiter.py trusts). Used only
    transiently to compute the daily hash — never stored or logged.
    """
    xff = headers.get("x-forwarded-for")
    if xff:
        # First entry is the originating client.
        first = xff.split(",")[0].strip()
        if first:
            return first
    for name in ("x-real-ip", "cf-connecting-ip"):
        value = headers.get(name)
        if value:
            return value.strip()
    return fallback


def normalize_page_path(page_path: Optional[str]) -> str:
    """Path only — strip query string / fragment, clamp length, default '/'."""
    if not page_path:
        return "/"
    path = page_path.split("?", 1)[0].split("#", 1)[0].strip()
    if not path:
        return "/"
    if not path.startswith("/"):
        path = "/" + path
    return path[:MAX_PAGE_PATH_LEN]


def normalize_referrer_source(referrer: Optional[str], own_hostname: str = "") -> str:
    """Referrer URL → bare lowercase domain, or 'direct'.

    Same-site referrers count as direct so internal navigation doesn't
    inflate a merchant's 'traffic sources' panel.
    """
    if not referrer:
        return "direct"
    try:
        domain = urlparse(referrer.strip()).netloc.lower()
    except ValueError:
        return "direct"
    if not domain:
        return "direct"
    domain = domain.split(":", 1)[0]
    if domain.startswith("www."):
        domain = domain[4:]
    if own_hostname and domain == own_hostname.lower().removeprefix("www."):
        return "direct"
    return domain[:100]


def classify_device(user_agent_string: str) -> str:
    """'mobile' | 'tablet' | 'desktop' via the user_agents parser."""
    try:
        from user_agents import parse as parse_ua

        ua = parse_ua(user_agent_string or "")
        if ua.is_tablet:
            return "tablet"
        if ua.is_mobile:
            return "mobile"
        return "desktop"
    except Exception:
        return "desktop"


async def _resolve_website(hostname: str) -> Optional[dict]:
    """hostname (subdomain or full host) → {id, analytics_enabled} or None.

    Falls back to selecting only `id` when the analytics_enabled column is
    missing (migration 038 not applied) — analytics is opt-out, so absence
    of the column means enabled, matching the old fail-open behaviour.
    """
    subdomain = hostname.split(".")[0] if "." in hostname else hostname
    if not subdomain:
        return None
    from app.services.supabase_client import supabase_service

    url = f"{supabase_service.url}/rest/v1/websites"
    async with httpx.AsyncClient(timeout=5.0) as client:
        for select in ("id,analytics_enabled", "id"):
            params = {
                "subdomain": f"eq.{subdomain}",
                "select": select,
                "limit": "1",
            }
            resp = await client.get(
                url, params=params, headers=supabase_service.service_headers
            )
            if resp.status_code == 400 and select != "id":
                continue  # column missing → retry without it (fail-open)
            resp.raise_for_status()
            rows = resp.json()
            return rows[0] if rows else None
    return None


async def process_pageview(
    hostname: str,
    page_path: Optional[str],
    referrer: Optional[str],
    ip: str,
    user_agent: str,
) -> bool:
    """Resolve the website, honour opt-out, and upsert the daily rollups.

    Returns True when a pageview was recorded (used by tests). Failures are
    swallowed with a PII-free warning — tracking must never surface errors.
    """
    try:
        website = await _resolve_website(hostname)
        if not website:
            # Unknown hostname: silently drop (could be a stale snippet or probe)
            return False
        if website.get("analytics_enabled", True) is False:
            return False

        website_id = str(website["id"])
        date_str = myt_today()
        payload = {
            "p_website_id": website_id,
            "p_date": date_str,
            "p_visitor_hash": compute_visitor_hash(ip, user_agent, website_id, date_str),
            "p_device": classify_device(user_agent),
            "p_page_path": normalize_page_path(page_path),
            "p_referrer_source": normalize_referrer_source(referrer, own_hostname=hostname),
        }

        from app.services.supabase_client import supabase_service

        rpc_url = f"{supabase_service.url}/rest/v1/rpc/track_site_pageview"
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(
                rpc_url, json=payload, headers=supabase_service.service_headers
            )
            resp.raise_for_status()
        return True
    except Exception as e:
        # No IP/UA/referrer in logs — hostname + error class only. Avoid
        # interpolating str(e): httpx errors embed the request URL, which is
        # safe today (only the public subdomain) but would leak if a future
        # query ever carried a hash/path in the querystring.
        logger.warning(f"[analytics] pageview rollup failed for {hostname}: {type(e).__name__}")
        return False
