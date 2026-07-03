"""
Merchant analytics API — powers the "Analitik" dashboard tab.

Every read goes through the service-role key here (never the browser anon
client — see migration 049), with three guarantees enforced on every
endpoint:

1. Auth + ownership: the caller must own the website they're querying
   (websites.user_id == JWT sub), else 403/404.
2. Server-side tier clamp: free/starter see 7 days of history, basic 30,
   pro 90 — the `days` query param is clamped here, not in the UI. Every
   response echoes {tier, max_days, clamped} so the UI can render honest
   lock states.
3. No PII in logs: log website ids and row counts only — never customer
   names/phones/addresses, IPs, or user agents.

Aggregation happens in Python over narrow PostgREST selects (per-merchant
volumes are modest; keeps the logic unit-testable without Postgres).
All daily bucketing uses Asia/Kuala_Lumpur — BM merchants think in MYT.
"""
import csv
import io
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from loguru import logger

from app.core.config import settings
from app.core.security import get_current_user
from app.services.subscription_service import subscription_service

router = APIRouter(prefix="/analytics", tags=["Analytics"])

MYT = ZoneInfo("Asia/Kuala_Lumpur")

# History window per plan tier, in days. Enforced server-side.
TIER_MAX_DAYS = {"free": 7, "starter": 7, "basic": 30, "pro": 90, "enterprise": 90}
DEFAULT_MAX_DAYS = 7
EXPORT_TIERS = {"pro", "enterprise"}

# Orders that count toward revenue: everything the merchant booked except
# cancellations/rejections. Flip here if "realized revenue" (delivered/
# completed only) is ever preferred.
EXCLUDED_REVENUE_STATUSES = {"cancelled", "rejected"}
DELIVERED_STATUSES = {"delivered", "completed"}

FETCH_LIMIT = 10000
IN_LIST_CHUNK = 100


# ---------------------------------------------------------------------------
# Pure helpers (unit-tested directly)
# ---------------------------------------------------------------------------

def max_days_for_tier(tier: Optional[str]) -> int:
    return TIER_MAX_DAYS.get((tier or "free").lower(), DEFAULT_MAX_DAYS)


def clamp_days(requested: int, tier: Optional[str]) -> Tuple[int, bool]:
    """Clamp a requested history window to the tier's allowance."""
    allowed = max_days_for_tier(tier)
    requested = max(1, requested)
    if requested > allowed:
        return allowed, True
    return requested, False


def pct_change(current: float, previous: float) -> Optional[float]:
    """Percent change; None when there is no previous baseline."""
    if previous == 0:
        return None
    return round((current - previous) / previous * 100, 1)


def parse_ts_myt(value: Optional[str]) -> Optional[datetime]:
    """PostgREST timestamptz string → aware datetime in MYT."""
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(MYT)


def myt_day_start(days_back: int = 0) -> datetime:
    """Midnight (MYT) `days_back` days before today, as an aware datetime."""
    today = datetime.now(MYT).date()
    return datetime.combine(today - timedelta(days=days_back), datetime.min.time(), tzinfo=MYT)


def window_start_iso(days: int) -> str:
    """UTC ISO timestamp for the start of an N-day window ending today (MYT)."""
    return myt_day_start(days - 1).astimezone(timezone.utc).isoformat()


def order_revenue(order: Dict[str, Any]) -> float:
    if (order.get("status") or "") in EXCLUDED_REVENUE_STATUSES:
        return 0.0
    try:
        return float(order.get("total_amount") or 0)
    except (TypeError, ValueError):
        return 0.0


def sum_window(orders: List[Dict[str, Any]], start: datetime, end: Optional[datetime] = None) -> Dict[str, Any]:
    """Revenue + order count for orders whose created_at falls in [start, end)."""
    revenue = 0.0
    count = 0
    for o in orders:
        ts = parse_ts_myt(o.get("created_at"))
        if ts is None or ts < start or (end is not None and ts >= end):
            continue
        if (o.get("status") or "") in EXCLUDED_REVENUE_STATUSES:
            continue
        revenue += order_revenue(o)
        count += 1
    return {"revenue": round(revenue, 2), "orders": count}


def build_daily_series(orders: List[Dict[str, Any]], days: int) -> List[Dict[str, Any]]:
    """Zero-filled per-MYT-day [{date, revenue, orders}] for the last N days."""
    by_day: Dict[str, Dict[str, Any]] = {}
    today = datetime.now(MYT).date()
    for i in range(days - 1, -1, -1):
        d = (today - timedelta(days=i)).isoformat()
        by_day[d] = {"date": d, "revenue": 0.0, "orders": 0}
    for o in orders:
        if (o.get("status") or "") in EXCLUDED_REVENUE_STATUSES:
            continue
        ts = parse_ts_myt(o.get("created_at"))
        if ts is None:
            continue
        key = ts.date().isoformat()
        if key in by_day:
            by_day[key]["revenue"] = round(by_day[key]["revenue"] + order_revenue(o), 2)
            by_day[key]["orders"] += 1
    return list(by_day.values())


def build_heatmap(orders: List[Dict[str, Any]]) -> List[Dict[str, int]]:
    """7x24 order-count matrix keyed by MYT day-of-week (0=Monday) and hour."""
    counts: Dict[Tuple[int, int], int] = defaultdict(int)
    for o in orders:
        if (o.get("status") or "") in EXCLUDED_REVENUE_STATUSES:
            continue
        ts = parse_ts_myt(o.get("created_at"))
        if ts is None:
            continue
        counts[(ts.weekday(), ts.hour)] += 1
    return [
        {"dow": dow, "hour": hour, "count": counts.get((dow, hour), 0)}
        for dow in range(7)
        for hour in range(24)
    ]


def aggregate_top_items(items: List[Dict[str, Any]], limit: int = 10) -> List[Dict[str, Any]]:
    """order_items rows → top N by quantity, with revenue per item."""
    grouped: Dict[str, Dict[str, Any]] = {}
    for it in items:
        name = (it.get("item_name") or "Item").strip() or "Item"
        entry = grouped.setdefault(name, {"item_name": name, "quantity": 0, "revenue": 0.0})
        try:
            entry["quantity"] += int(it.get("quantity") or 0)
        except (TypeError, ValueError):
            pass
        try:
            entry["revenue"] = round(entry["revenue"] + float(it.get("total_price") or 0), 2)
        except (TypeError, ValueError):
            pass
    return sorted(grouped.values(), key=lambda e: (-e["quantity"], -e["revenue"]))[:limit]


# ---------------------------------------------------------------------------
# Service-role DB access
# ---------------------------------------------------------------------------

def _service_headers() -> Dict[str, str]:
    key = settings.SUPABASE_SERVICE_ROLE_KEY
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }


async def _db_query(table: str, params: Dict[str, str]) -> List[Dict[str, Any]]:
    params = {"limit": str(FETCH_LIMIT), **params}
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(
            f"{settings.SUPABASE_URL}/rest/v1/{table}",
            headers=_service_headers(),
            params=params,
        )
    if resp.status_code != 200:
        logger.warning(f"[analitik] {table} query failed: HTTP {resp.status_code}")
        return []
    rows = resp.json()
    # No silent caps: if a bulk fetch hits the row ceiling the aggregation is
    # undercounting the oldest days (rows come back created_at.desc). Only
    # applies to the default bulk limit — intentional small limits (e.g. the
    # limit=1 ownership lookup) are not truncation.
    effective_limit = int(params.get("limit", FETCH_LIMIT))
    if effective_limit >= FETCH_LIMIT and len(rows) >= effective_limit:
        logger.warning(
            f"[analitik] {table} hit the {effective_limit}-row cap; "
            f"older rows in the window are not aggregated"
        )
    return rows


async def _db_count(table: str, params: Dict[str, str]) -> int:
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(
            f"{settings.SUPABASE_URL}/rest/v1/{table}",
            headers={**_service_headers(), "Prefer": "count=exact"},
            params={"select": "id", "limit": "1", **params},
        )
    if resp.status_code != 200:
        return 0
    content_range = resp.headers.get("content-range", "")
    if "/" in content_range:
        total = content_range.split("/")[1]
        if total != "*":
            return int(total)
    return len(resp.json())


# ---------------------------------------------------------------------------
# Shared endpoint plumbing
# ---------------------------------------------------------------------------

async def _get_tier(user_id: str) -> str:
    # Fails closed to "free" (never over-grants the paid export or a wider
    # history window). A transient lookup failure therefore downgrades a
    # paying merchant, so log it distinctly from a genuine no-subscription
    # so the intermittent case is diagnosable rather than invisible.
    try:
        sub = await subscription_service.get_user_subscription(user_id)
    except Exception as e:
        logger.warning(f"[analitik] tier lookup failed; defaulting to free: {type(e).__name__}")
        return "free"
    if not sub or sub.get("status") != "active":
        return "free"
    return (sub.get("tier") or "free").lower()


async def _authorize_website(website_id: str, current_user: dict) -> Dict[str, Any]:
    """404 if the website doesn't exist, 403 if the caller doesn't own it."""
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Token tidak sah")
    rows = await _db_query(
        "websites",
        {"id": f"eq.{website_id}", "select": "id,user_id,subdomain", "limit": "1"},
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Website tidak dijumpai")
    if str(rows[0].get("user_id")) != str(user_id):
        logger.warning(f"[analitik] ownership denied for website {website_id}")
        raise HTTPException(status_code=403, detail="Akses ditolak — website ini bukan milik anda")
    return rows[0]


async def _resolve_window(current_user: dict, website_id: str, days: int):
    """Common auth + tier-clamp preamble. Returns (website, tier, days, clamped)."""
    website = await _authorize_website(website_id, current_user)
    tier = await _get_tier(current_user.get("sub"))
    days, clamped = clamp_days(days, tier)
    return website, tier, days, clamped


def _meta(tier: str, days: int, clamped: bool) -> Dict[str, Any]:
    return {"tier": tier, "days": days, "max_days": max_days_for_tier(tier), "clamped": clamped}


async def _fetch_orders(website_id: str, days: int, select: str) -> List[Dict[str, Any]]:
    return await _db_query(
        "delivery_orders",
        {
            "website_id": f"eq.{website_id}",
            "created_at": f"gte.{window_start_iso(days)}",
            "select": select,
            "order": "created_at.desc",
        },
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/summary")
async def get_summary(
    website_id: str = Query(...),
    current_user: dict = Depends(get_current_user),
):
    """KPI header: today / 7 / 30 hari revenue+orders with % change."""
    website, tier, _, _ = await _resolve_window(current_user, website_id, 1)
    allowed = max_days_for_tier(tier)

    # One fetch covers every window: 2x the largest allowed block (for the
    # previous-window comparisons), capped at the tier allowance.
    largest_block = min(30, allowed)
    orders = await _fetch_orders(website_id, largest_block * 2, "total_amount,status,created_at")

    today_start = myt_day_start(0)
    blocks: Dict[str, Any] = {
        "today": {
            **sum_window(orders, today_start),
            "change_pct": pct_change(
                sum_window(orders, today_start)["revenue"],
                sum_window(orders, myt_day_start(1), today_start)["revenue"],
            ),
        }
    }
    for span in (7, 30):
        key = f"last_{span}d"
        if span > allowed:
            blocks[key] = {"locked": True}
            continue
        current = sum_window(orders, myt_day_start(span - 1))
        previous = sum_window(orders, myt_day_start(2 * span - 1), myt_day_start(span - 1))
        blocks[key] = {
            **current,
            "change_pct": pct_change(current["revenue"], previous["revenue"]),
            "orders_change_pct": pct_change(current["orders"], previous["orders"]),
        }

    chats_today = await _db_count(
        "chat_conversations",
        {
            "website_id": f"eq.{website_id}",
            "created_at": f"gte.{today_start.astimezone(timezone.utc).isoformat()}",
        },
    )
    visitor_rows = await _db_query(
        "site_analytics_daily",
        {
            "website_id": f"eq.{website_id}",
            "date": f"eq.{datetime.now(MYT).date().isoformat()}",
            "select": "total_views,unique_visitors",
            "limit": "1",
        },
    )
    visitors_today = visitor_rows[0] if visitor_rows else {"total_views": 0, "unique_visitors": 0}

    return {
        **_meta(tier, allowed, False),
        "summary": blocks,
        "chats_today": chats_today,
        "visitors_today": visitors_today,
    }


@router.get("/revenue-daily")
async def get_revenue_daily(
    website_id: str = Query(...),
    days: int = Query(30, ge=1, le=365),
    current_user: dict = Depends(get_current_user),
):
    """Zero-filled daily [{date, revenue, orders}] series (MYT days)."""
    _, tier, days, clamped = await _resolve_window(current_user, website_id, days)
    orders = await _fetch_orders(website_id, days, "total_amount,status,created_at")
    return {**_meta(tier, days, clamped), "series": build_daily_series(orders, days)}


@router.get("/orders-heatmap")
async def get_orders_heatmap(
    website_id: str = Query(...),
    days: int = Query(30, ge=1, le=365),
    current_user: dict = Depends(get_current_user),
):
    """7x24 order-count matrix (MYT day-of-week 0=Isnin, hour 0-23)."""
    _, tier, days, clamped = await _resolve_window(current_user, website_id, days)
    orders = await _fetch_orders(website_id, days, "status,created_at")
    return {**_meta(tier, days, clamped), "cells": build_heatmap(orders)}


@router.get("/top-items")
async def get_top_items(
    website_id: str = Query(...),
    days: int = Query(30, ge=1, le=365),
    current_user: dict = Depends(get_current_user),
):
    """Top 10 menu items by quantity (embedded join filters by website+window)."""
    _, tier, days, clamped = await _resolve_window(current_user, website_id, days)
    # Include NULL-status orders (status.is.null) so a rare untyped order is
    # counted here exactly as the revenue/heatmap/zone panels count it —
    # those use `(status or '') not in EXCLUDED`, which keeps NULL. A bare
    # `not.in.(...)` would drop NULL rows and desync top-items from revenue.
    excluded = ",".join(sorted(EXCLUDED_REVENUE_STATUSES))
    items = await _db_query(
        "order_items",
        {
            "select": "item_name,quantity,total_price,order:delivery_orders!inner(id)",
            "order.website_id": f"eq.{website_id}",
            "order.created_at": f"gte.{window_start_iso(days)}",
            "order.or": f"(status.is.null,status.not.in.({excluded}))",
        },
    )
    return {**_meta(tier, days, clamped), "items": aggregate_top_items(items)}


@router.get("/zones")
async def get_zone_stats(
    website_id: str = Query(...),
    days: int = Query(30, ge=1, le=365),
    current_user: dict = Depends(get_current_user),
):
    """Per-delivery-zone orders, revenue, fees and cancel rate."""
    _, tier, days, clamped = await _resolve_window(current_user, website_id, days)
    orders = await _fetch_orders(
        website_id, days, "delivery_zone,delivery_zone_id,status,total_amount,delivery_fee,created_at"
    )
    zones: Dict[str, Dict[str, Any]] = {}
    for o in orders:
        name = (o.get("delivery_zone") or "").strip() or "Tanpa zon"
        z = zones.setdefault(
            name,
            {"zone": name, "orders": 0, "cancelled": 0, "revenue": 0.0, "delivery_fees": 0.0},
        )
        status = o.get("status") or ""
        if status in EXCLUDED_REVENUE_STATUSES:
            z["cancelled"] += 1
            continue
        z["orders"] += 1
        z["revenue"] = round(z["revenue"] + order_revenue(o), 2)
        try:
            z["delivery_fees"] = round(z["delivery_fees"] + float(o.get("delivery_fee") or 0), 2)
        except (TypeError, ValueError):
            pass
    result = []
    for z in zones.values():
        total = z["orders"] + z["cancelled"]
        z["cancel_rate_pct"] = round(z["cancelled"] / total * 100, 1) if total else 0.0
        result.append(z)
    result.sort(key=lambda z: -z["revenue"])
    return {**_meta(tier, days, clamped), "zones": result}


@router.get("/riders")
async def get_rider_stats(
    website_id: str = Query(...),
    days: int = Query(30, ge=1, le=365),
    current_user: dict = Depends(get_current_user),
):
    """Per-rider deliveries + average pickup→delivered minutes in the window."""
    _, tier, days, clamped = await _resolve_window(current_user, website_id, days)
    orders = await _fetch_orders(
        website_id, days, "rider_id,status,picked_up_at,delivered_at,created_at"
    )
    riders_rows = await _db_query(
        "riders", {"website_id": f"eq.{website_id}", "select": "id,name,rating,total_deliveries"}
    )
    rider_info = {str(r["id"]): r for r in riders_rows if r.get("id")}

    stats: Dict[str, Dict[str, Any]] = {}
    for o in orders:
        rider_id = o.get("rider_id")
        if not rider_id:
            continue
        rider_id = str(rider_id)
        s = stats.setdefault(
            rider_id, {"rider_id": rider_id, "deliveries": 0, "_durations": []}
        )
        if (o.get("status") or "") in DELIVERED_STATUSES:
            s["deliveries"] += 1
            picked = parse_ts_myt(o.get("picked_up_at"))
            delivered = parse_ts_myt(o.get("delivered_at"))
            if picked and delivered and delivered > picked:
                s["_durations"].append((delivered - picked).total_seconds() / 60)

    result = []
    for rider_id, s in stats.items():
        durations = s.pop("_durations")
        info = rider_info.get(rider_id, {})
        result.append(
            {
                **s,
                "name": info.get("name") or "Penghantar",
                "rating": info.get("rating"),
                "total_deliveries_all_time": info.get("total_deliveries"),
                "avg_delivery_minutes": round(sum(durations) / len(durations), 1)
                if durations
                else None,
            }
        )
    result.sort(key=lambda r: -r["deliveries"])
    return {**_meta(tier, days, clamped), "riders": result}


@router.get("/chat")
async def get_chat_stats(
    website_id: str = Query(...),
    days: int = Query(30, ge=1, le=365),
    current_user: dict = Depends(get_current_user),
):
    """AI chat volume: conversations per day + total messages in the window."""
    _, tier, days, clamped = await _resolve_window(current_user, website_id, days)
    conversations = await _db_query(
        "chat_conversations",
        {
            "website_id": f"eq.{website_id}",
            "created_at": f"gte.{window_start_iso(days)}",
            "select": "id,created_at",
        },
    )

    today = datetime.now(MYT).date()
    per_day: Dict[str, int] = {
        (today - timedelta(days=i)).isoformat(): 0 for i in range(days - 1, -1, -1)
    }
    for c in conversations:
        ts = parse_ts_myt(c.get("created_at"))
        if ts and ts.date().isoformat() in per_day:
            per_day[ts.date().isoformat()] += 1

    total_messages = 0
    conv_ids = [str(c["id"]) for c in conversations if c.get("id")]
    for i in range(0, len(conv_ids), IN_LIST_CHUNK):
        chunk = conv_ids[i : i + IN_LIST_CHUNK]
        total_messages += await _db_count(
            "chat_messages", {"conversation_id": f"in.({','.join(chunk)})"}
        )

    return {
        **_meta(tier, days, clamped),
        "series": [{"date": d, "conversations": n} for d, n in per_day.items()],
        "total_conversations": len(conversations),
        "total_messages": total_messages,
    }


@router.get("/visitors")
async def get_visitor_stats(
    website_id: str = Query(...),
    days: int = Query(30, ge=1, le=365),
    current_user: dict = Depends(get_current_user),
):
    """Visitor rollups: daily series, totals, top pages, referrers, devices.

    Reads ONLY the site_analytics_* rollup tables (migration 050) — never
    raw events; there are none.
    """
    _, tier, days, clamped = await _resolve_window(current_user, website_id, days)
    start_date = (datetime.now(MYT).date() - timedelta(days=days - 1)).isoformat()
    date_filter = {"website_id": f"eq.{website_id}", "date": f"gte.{start_date}"}

    daily = await _db_query(
        "site_analytics_daily",
        {
            **date_filter,
            "select": "date,total_views,unique_visitors,mobile_views,tablet_views,desktop_views",
            "order": "date.asc",
        },
    )
    pages = await _db_query(
        "site_analytics_pages_daily", {**date_filter, "select": "page_path,views"}
    )
    referrers = await _db_query(
        "site_analytics_referrers_daily", {**date_filter, "select": "referrer_source,views"}
    )

    by_day = {row["date"]: row for row in daily}
    today = datetime.now(MYT).date()
    series = []
    for i in range(days - 1, -1, -1):
        d = (today - timedelta(days=i)).isoformat()
        row = by_day.get(d, {})
        series.append(
            {
                "date": d,
                "total_views": row.get("total_views", 0),
                "unique_visitors": row.get("unique_visitors", 0),
            }
        )

    page_totals: Dict[str, int] = defaultdict(int)
    for p in pages:
        page_totals[p.get("page_path") or "/"] += int(p.get("views") or 0)
    referrer_totals: Dict[str, int] = defaultdict(int)
    for r in referrers:
        referrer_totals[r.get("referrer_source") or "direct"] += int(r.get("views") or 0)

    return {
        **_meta(tier, days, clamped),
        "series": series,
        "totals": {
            "total_views": sum(r.get("total_views", 0) for r in daily),
            "unique_visitors": sum(r.get("unique_visitors", 0) for r in daily),
        },
        "devices": {
            "mobile": sum(r.get("mobile_views", 0) for r in daily),
            "tablet": sum(r.get("tablet_views", 0) for r in daily),
            "desktop": sum(r.get("desktop_views", 0) for r in daily),
        },
        "top_pages": sorted(
            ({"page_path": k, "views": v} for k, v in page_totals.items()),
            key=lambda p: -p["views"],
        )[:10],
        "top_referrers": sorted(
            ({"source": k, "views": v} for k, v in referrer_totals.items()),
            key=lambda p: -p["views"],
        )[:10],
    }


@router.get("/export")
async def export_csv(
    website_id: str = Query(...),
    days: int = Query(30, ge=1, le=365),
    dataset: str = Query("orders", pattern="^(orders|daily)$"),
    current_user: dict = Depends(get_current_user),
):
    """CSV export — Pro plan only (enforced here, not just in the UI)."""
    _, tier, days, clamped = await _resolve_window(current_user, website_id, days)
    if tier not in EXPORT_TIERS:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "tier_required",
                "required_plan": "pro",
                "message": "Eksport CSV memerlukan pelan Pro",
            },
        )

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    if dataset == "orders":
        # Deliberately PII-light: no customer name/phone/address in exports.
        orders = await _fetch_orders(
            website_id,
            days,
            "order_number,created_at,status,payment_method,payment_status,"
            "delivery_zone,subtotal,delivery_fee,total_amount",
        )
        writer.writerow(
            [
                "order_number", "created_at", "status", "payment_method",
                "payment_status", "delivery_zone", "subtotal", "delivery_fee",
                "total_amount",
            ]
        )
        for o in orders:
            writer.writerow(
                [
                    o.get("order_number"), o.get("created_at"), o.get("status"),
                    o.get("payment_method"), o.get("payment_status"),
                    o.get("delivery_zone"), o.get("subtotal"),
                    o.get("delivery_fee"), o.get("total_amount"),
                ]
            )
    else:
        orders = await _fetch_orders(website_id, days, "total_amount,status,created_at")
        revenue_by_day = {row["date"]: row for row in build_daily_series(orders, days)}
        start_date = (datetime.now(MYT).date() - timedelta(days=days - 1)).isoformat()
        visits = await _db_query(
            "site_analytics_daily",
            {
                "website_id": f"eq.{website_id}",
                "date": f"gte.{start_date}",
                "select": "date,total_views,unique_visitors",
            },
        )
        visits_by_day = {v["date"]: v for v in visits}
        writer.writerow(["date", "revenue", "orders", "views", "unique_visitors"])
        for d, row in revenue_by_day.items():
            v = visits_by_day.get(d, {})
            writer.writerow(
                [
                    d, row["revenue"], row["orders"],
                    v.get("total_views", 0), v.get("unique_visitors", 0),
                ]
            )

    buffer.seek(0)
    filename = f"analitik-{dataset}-{datetime.now(MYT).date().isoformat()}.csv"
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
