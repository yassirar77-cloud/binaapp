"""
Marketing attribution for binaapp.my itself (migration 067).

Two jobs:
  * count daily visits to the marketing site by source, and
  * remember which source a signup came from.

Everything the browser sends is untrusted free text, so it is normalised
here to short lowercase labels before it reaches the database. No visitor
identifier, IP or user agent is ever stored.
"""
import re
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

import httpx
from loguru import logger

MYT = ZoneInfo("Asia/Kuala_Lumpur")

MAX_LABEL_LEN = 60
MAX_PATH_LEN = 200
MAX_SOURCES_PER_DAY = 200

OWN_DOMAINS = {"binaapp.my"}

# Referrer domain (or utm_source alias) -> one canonical channel name, so
# "m.facebook.com", "fb" and "l.facebook.com" do not become three rows.
_SOURCE_ALIASES = (
    ("tiktok", ("tiktok.com", "tiktok", "tt")),
    ("facebook", ("facebook.com", "fb.com", "fb.me", "facebook", "fb")),
    ("instagram", ("instagram.com", "instagram", "ig")),
    ("whatsapp", ("whatsapp.com", "wa.me", "whatsapp", "wa", "wasap")),
    ("google", ("google.com", "google.com.my", "google")),
    ("youtube", ("youtube.com", "youtu.be", "youtube", "yt")),
    ("threads", ("threads.net", "threads.com", "threads")),
    ("x", ("twitter.com", "x.com", "t.co", "twitter")),
    ("telegram", ("t.me", "telegram.org", "telegram")),
    ("bing", ("bing.com",)),
)

_LABEL_RE = re.compile(r"[^a-z0-9._-]+")
_REF_CODE_RE = re.compile(r"^BINA-[A-Z0-9]{4}-[A-Z0-9]{4}$")


def clean_label(value: Any, max_len: int = MAX_LABEL_LEN) -> str:
    """Free text -> short lowercase label of [a-z0-9._-]; '' when unusable."""
    if not isinstance(value, str):
        return ""
    label = _LABEL_RE.sub("-", value.strip().lower()).strip("-.")
    return label[:max_len]


def referrer_domain(referrer: Any) -> str:
    """Referrer URL -> bare lowercase domain; '' for none, junk or our own site."""
    if not isinstance(referrer, str) or not referrer.strip():
        return ""
    raw = referrer.strip()
    if "://" not in raw:
        raw = "https://" + raw
    try:
        domain = urlparse(raw).netloc.lower()
    except ValueError:
        return ""
    domain = domain.split("@")[-1].split(":", 1)[0]
    if domain.startswith("www."):
        domain = domain[4:]
    if not domain or "." not in domain:
        return ""
    if domain in OWN_DOMAINS or any(domain.endswith("." + own) for own in OWN_DOMAINS):
        return ""
    return clean_label(domain, 100)


def canonical_source(label: str) -> str:
    """Collapse known aliases/domains to one channel name."""
    if not label:
        return ""
    for name, aliases in _SOURCE_ALIASES:
        for alias in aliases:
            if label == alias or label.endswith("." + alias):
                return name
    return label


def clean_path(value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        return ""
    path = value.strip().split("?", 1)[0].split("#", 1)[0]
    if not path.startswith("/"):
        path = "/" + path
    return path[:MAX_PATH_LEN]


def normalize_attribution(raw: Optional[Dict[str, Any]]) -> Dict[str, str]:
    """Browser attribution payload -> clean, bounded fields.

    Source priority: explicit utm_source, then a referral code (`ref`),
    then the referrer domain, else 'direct'.
    """
    raw = raw if isinstance(raw, dict) else {}
    ref_domain = referrer_domain(raw.get("referrer"))
    utm_source = clean_label(raw.get("utm_source") or raw.get("source"))
    medium = clean_label(raw.get("utm_medium") or raw.get("medium"))
    ref_code = clean_label(raw.get("ref"))

    if utm_source:
        source = canonical_source(utm_source)
    elif ref_code:
        source = "referral"
    elif ref_domain:
        source = canonical_source(ref_domain)
    else:
        source = "direct"

    if not medium:
        if ref_code and not utm_source:
            medium = "referral"
        elif ref_domain and not utm_source:
            medium = "organic"

    campaign = clean_label(raw.get("utm_campaign") or raw.get("campaign"))
    if not campaign and ref_code:
        campaign = ref_code

    return {
        "source": source,
        "medium": medium,
        "campaign": campaign,
        "content": clean_label(raw.get("utm_content") or raw.get("content")),
        "referrer": ref_domain,
        "landing_path": clean_path(raw.get("landing_path")),
        "ref_code": referral_code(raw.get("ref")),
    }


def referral_code(value: Any) -> str:
    """A well-formed BINA-XXXX-XXXX referral code, upper-cased; '' otherwise."""
    if not isinstance(value, str):
        return ""
    code = value.strip().upper()
    return code if _REF_CODE_RE.match(code) else ""


def profile_columns(attribution: Dict[str, str]) -> Dict[str, Optional[str]]:
    """Normalised attribution -> profiles.signup_* update payload."""
    return {
        "signup_source": attribution.get("source") or "direct",
        "signup_medium": attribution.get("medium") or None,
        "signup_campaign": attribution.get("campaign") or None,
        "signup_content": attribution.get("content") or None,
        "signup_referrer": attribution.get("referrer") or None,
        "signup_landing_path": attribution.get("landing_path") or None,
        "signup_ref_code": attribution.get("ref_code") or None,
    }


def myt_today() -> str:
    return datetime.now(MYT).date().isoformat()


def summarize(
    visit_rows: List[Dict[str, Any]],
    signup_rows: List[Dict[str, Any]],
    paid_user_ids: Optional[set] = None,
) -> List[Dict[str, Any]]:
    """Roll visits, signups and paying signups up per source, busiest first."""
    paid_user_ids = paid_user_ids or set()
    by_source: Dict[str, Dict[str, Any]] = defaultdict(
        lambda: {"visits": 0, "signups": 0, "paid": 0}
    )
    for row in visit_rows:
        by_source[row.get("source") or "direct"]["visits"] += int(row.get("visits") or 0)
    for row in signup_rows:
        bucket = by_source[row.get("signup_source") or "unknown"]
        bucket["signups"] += 1
        if row.get("id") in paid_user_ids:
            bucket["paid"] += 1

    out = []
    for source, b in by_source.items():
        rate = round(b["signups"] / b["visits"] * 100, 1) if b["visits"] else None
        out.append({"source": source, **b, "signup_rate": rate})
    out.sort(key=lambda r: (-r["signups"], -r["visits"], r["source"]))
    return out


# ---------------------------------------------------------------------------
# Database (service role)
# ---------------------------------------------------------------------------

async def record_visit(raw: Optional[Dict[str, Any]]) -> bool:
    """Bump today's counter for this visit's source. Never raises."""
    try:
        from app.services.supabase_client import supabase_service

        attribution = normalize_attribution(raw)
        payload = {
            "p_date": myt_today(),
            "p_source": attribution["source"],
            "p_medium": attribution["medium"],
            "p_campaign": attribution["campaign"],
        }
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(
                f"{supabase_service.url}/rest/v1/rpc/track_marketing_visit",
                json=payload,
                headers=supabase_service.service_headers,
            )
            resp.raise_for_status()
        return True
    except Exception as e:
        logger.warning(f"marketing visit not recorded: {type(e).__name__}")
        return False


async def save_signup_attribution(user_id: str, raw: Optional[Dict[str, Any]]) -> bool:
    """Write profiles.signup_* for a new account. Never raises: a missing
    column or a DB hiccup must not fail a registration."""
    try:
        from app.services.supabase_client import supabase_service

        columns = profile_columns(normalize_attribution(raw))
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.patch(
                f"{supabase_service.url}/rest/v1/profiles",
                params={"id": f"eq.{user_id}"},
                json=columns,
                headers={**supabase_service.service_headers, "Prefer": "return=minimal"},
            )
            resp.raise_for_status()
        return True
    except Exception as e:
        logger.warning(f"signup attribution not saved for {user_id}: {type(e).__name__}")
        return False


async def load_summary(days: int) -> Dict[str, Any]:
    """Visits, signups and paying signups per source over the last `days`."""
    from app.services.supabase_client import supabase_service

    days = max(1, min(int(days), 365))
    start_date = (datetime.now(MYT).date() - timedelta(days=days - 1))
    start_ts = datetime.combine(start_date, datetime.min.time(), MYT).isoformat()
    base = f"{supabase_service.url}/rest/v1"
    headers = supabase_service.service_headers

    async with httpx.AsyncClient(timeout=10.0) as client:
        visits_resp = await client.get(
            f"{base}/marketing_visits_daily",
            params={
                "select": "date,source,medium,campaign,visits",
                "date": f"gte.{start_date.isoformat()}",
                "order": "date.asc",
                "limit": "10000",
            },
            headers=headers,
        )
        visits_resp.raise_for_status()
        signups_resp = await client.get(
            f"{base}/profiles",
            params={
                "select": "id,signup_source,signup_campaign,created_at",
                "created_at": f"gte.{start_ts}",
                "limit": "10000",
            },
            headers=headers,
        )
        signups_resp.raise_for_status()
        paid_resp = await client.get(
            f"{base}/payments",
            params={"select": "user_id", "status": "eq.successful", "limit": "10000"},
            headers=headers,
        )
        paid_ids = (
            {r.get("user_id") for r in paid_resp.json()}
            if paid_resp.status_code == 200
            else set()
        )

    visit_rows = visits_resp.json()
    signup_rows = signups_resp.json()

    daily: Dict[str, int] = defaultdict(int)
    campaigns: Dict[tuple, int] = defaultdict(int)
    for row in visit_rows:
        daily[row["date"]] += int(row.get("visits") or 0)
        if row.get("campaign"):
            campaigns[(row.get("source") or "direct", row["campaign"])] += int(row.get("visits") or 0)

    return {
        "days": days,
        "total_visits": sum(daily.values()),
        "total_signups": len(signup_rows),
        "sources": summarize(visit_rows, signup_rows, paid_ids),
        "campaigns": [
            {"source": s, "campaign": c, "visits": v}
            for (s, c), v in sorted(campaigns.items(), key=lambda kv: -kv[1])[:20]
        ],
        "daily": [{"date": d, "visits": v} for d, v in sorted(daily.items())],
    }
