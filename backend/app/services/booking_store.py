"""Booking engine storage — service-role PostgREST calls for the three
booking tables (migration 065). Rules live in ``booking_engine.py``.

Reads return ``None`` when the database could not be reached (so callers
can answer 503 rather than pretend there is nothing), and a list / dict
when it could.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from loguru import logger

from app.services.supabase_client import supabase_service

SETTINGS = "booking_settings"
SERVICES = "booking_services"
BOOKINGS = "bookings"


class SlotFull(Exception):
    """create_booking() refused: the slot filled up first."""


class DuplicateBooking(Exception):
    """This phone already holds an overlapping active booking."""


class DuplicateReference(Exception):
    """Reference collision — retry with a new code."""


def _url(table: str) -> str:
    return f"{supabase_service.url}/rest/v1/{table}"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _get(table: str, params: Dict[str, str]) -> Optional[List[Dict[str, Any]]]:
    try:
        async with supabase_service._client() as client:
            resp = await client.get(_url(table), headers=supabase_service.headers, params=params)
        if resp.status_code == 200:
            return resp.json()
        logger.error(f"📅 booking read {table} failed: {resp.status_code} {resp.text[:200]}")
    except Exception as exc:  # noqa: BLE001
        logger.error(f"📅 booking read {table} failed: {exc}")
    return None


async def _write(method: str, table: str, *, params=None, json=None, prefer="return=representation"):
    headers = {**supabase_service.headers, "Prefer": prefer}
    try:
        async with supabase_service._client() as client:
            resp = await client.request(
                method, _url(table), headers=headers, params=params, json=json
            )
        if resp.status_code in (200, 201, 204):
            if resp.status_code == 204 or not resp.content:
                return []
            return resp.json()
        logger.error(f"📅 booking write {method} {table} failed: {resp.status_code} {resp.text[:200]}")
    except Exception as exc:  # noqa: BLE001
        logger.error(f"📅 booking write {method} {table} failed: {exc}")
    return None


# -- settings ---------------------------------------------------------------

async def get_settings(website_id: str) -> Optional[Dict[str, Any]]:
    """The stored row, ``{}`` when the site has none yet, None on failure."""
    rows = await _get(SETTINGS, {"website_id": f"eq.{website_id}", "limit": "1"})
    if rows is None:
        return None
    return rows[0] if rows else {}


async def save_settings(website_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    row = {**data, "website_id": website_id, "updated_at": _now()}
    rows = await _write(
        "POST", SETTINGS, params={"on_conflict": "website_id"}, json=row,
        prefer="resolution=merge-duplicates,return=representation",
    )
    return rows[0] if rows else None


# -- services ---------------------------------------------------------------

async def list_services(website_id: str, *, active_only: bool = False) -> Optional[List[Dict[str, Any]]]:
    params = {
        "website_id": f"eq.{website_id}",
        "order": "sort_order.asc,created_at.asc",
    }
    if active_only:
        params["active"] = "eq.true"
    return await _get(SERVICES, params)


async def get_service(website_id: str, service_id: str) -> Optional[Dict[str, Any]]:
    rows = await _get(
        SERVICES, {"id": f"eq.{service_id}", "website_id": f"eq.{website_id}", "limit": "1"}
    )
    return rows[0] if rows else None


async def create_service(website_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    rows = await _write("POST", SERVICES, json={**data, "website_id": website_id})
    return rows[0] if rows else None


async def update_service(website_id: str, service_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    rows = await _write(
        "PATCH", SERVICES,
        params={"id": f"eq.{service_id}", "website_id": f"eq.{website_id}"},
        json={**data, "updated_at": _now()},
    )
    return rows[0] if rows else None


async def delete_service(website_id: str, service_id: str) -> bool:
    rows = await _write(
        "DELETE", SERVICES,
        params={"id": f"eq.{service_id}", "website_id": f"eq.{website_id}"},
    )
    return bool(rows)


# -- bookings ---------------------------------------------------------------

async def list_bookings_for_date(website_id: str, booking_date: str) -> Optional[List[Dict[str, Any]]]:
    """Active bookings that can occupy a slot on ``booking_date``."""
    return await _get(BOOKINGS, {
        "website_id": f"eq.{website_id}",
        "booking_date": f"eq.{booking_date}",
        "status": "in.(pending,confirmed)",
        "select": "id,start_at,end_at,status",
    })


async def list_bookings(
    website_id: str,
    *,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 200,
) -> Optional[List[Dict[str, Any]]]:
    params: List[tuple] = [
        ("website_id", f"eq.{website_id}"),
        ("order", "start_at.asc"),
        ("limit", str(limit)),
    ]
    if date_from:
        params.append(("booking_date", f"gte.{date_from}"))
    if date_to:
        params.append(("booking_date", f"lte.{date_to}"))
    if status:
        params.append(("status", f"eq.{status}"))
    try:
        async with supabase_service._client() as client:
            resp = await client.get(_url(BOOKINGS), headers=supabase_service.headers, params=params)
        if resp.status_code == 200:
            return resp.json()
        logger.error(f"📅 booking list failed: {resp.status_code} {resp.text[:200]}")
    except Exception as exc:  # noqa: BLE001
        logger.error(f"📅 booking list failed: {exc}")
    return None


async def get_booking(website_id: str, booking_id: str) -> Optional[Dict[str, Any]]:
    rows = await _get(
        BOOKINGS, {"id": f"eq.{booking_id}", "website_id": f"eq.{website_id}", "limit": "1"}
    )
    return rows[0] if rows else None


async def get_booking_by_reference(website_id: str, reference: str) -> Optional[Dict[str, Any]]:
    rows = await _get(
        BOOKINGS, {"reference": f"eq.{reference}", "website_id": f"eq.{website_id}", "limit": "1"}
    )
    return rows[0] if rows else None


async def insert_booking(args: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Insert through the locked create_booking() function.

    Raises SlotFull / DuplicateBooking / DuplicateReference for the three
    refusals the function can make; returns None on any other failure.
    """
    url = f"{supabase_service.url}/rest/v1/rpc/create_booking"
    try:
        async with supabase_service._client() as client:
            resp = await client.post(url, headers=supabase_service.headers, json=args)
    except Exception as exc:  # noqa: BLE001
        logger.error(f"📅 create_booking call failed: {exc}")
        return None
    if resp.status_code in (200, 201):
        data = resp.json()
        return data[0] if isinstance(data, list) and data else data
    body = resp.text or ""
    if "SLOT_FULL" in body:
        raise SlotFull()
    if "DUPLICATE_BOOKING" in body:
        raise DuplicateBooking()
    if "23505" in body or "duplicate key" in body.lower():
        raise DuplicateReference()
    logger.error(f"📅 create_booking failed: {resp.status_code} {body[:300]}")
    return None


async def set_booking_status(
    website_id: str,
    booking_id: str,
    *,
    from_status: str,
    to_status: str,
    cancelled_by: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Conditional update (WHERE status = from_status): two people acting
    on one booking at once cannot both win."""
    patch: Dict[str, Any] = {"status": to_status, "updated_at": _now()}
    if cancelled_by:
        patch["cancelled_by"] = cancelled_by
    rows = await _write(
        "PATCH", BOOKINGS,
        params={
            "id": f"eq.{booking_id}",
            "website_id": f"eq.{website_id}",
            "status": f"eq.{from_status}",
        },
        json=patch,
    )
    return rows[0] if rows else None


async def notify_owner(owner_id: str, website_id: str, title: str, body: str, data: Dict[str, Any]) -> None:
    """In-app notification for the merchant. Never raises: a booking that
    was saved must not fail because the bell could not ring."""
    try:
        await _write(
            "POST", "notifications",
            json={
                "user_type": "owner",
                "user_id": owner_id,
                "website_id": website_id,
                "type": "new_booking",
                "title": title,
                "body": body,
                "data": data,
            },
            prefer="return=minimal",
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"📅 booking notification failed: {exc}")


# -- website ----------------------------------------------------------------

async def get_site(website_id: str) -> Optional[Dict[str, Any]]:
    """The few website columns the booking engine needs (never the HTML).
    ``{}`` when no such website, None when the database is unreachable."""
    rows = await _get("websites", {
        "id": f"eq.{website_id}",
        "select": "id,user_id,business_name,subdomain,status",
        "limit": "1",
    })
    if rows is None:
        return None
    return rows[0] if rows else {}


async def get_owner_phone(owner_id: str) -> Optional[str]:
    rows = await _get("profiles", {"id": f"eq.{owner_id}", "select": "phone", "limit": "1"})
    return (rows[0].get("phone") if rows else None) or None
