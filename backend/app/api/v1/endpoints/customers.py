"""
BinaApp Customer Lookup API

Public read-only endpoint for the customer-facing /order flow. Given a
website_id and a phone number, returns whether a saved customer record
exists for that pair, and surfaces the saved name + address for the
"Selamat kembali" returning-customer card in the identify page.

Writes happen elsewhere — `get_or_create_customer()` in delivery.py is
called by `POST /api/v1/delivery/orders` when an order is actually placed.
This endpoint is a pure SELECT so we don't pollute `website_customers`
with empty-name rows for users who tap their phone but never order.
"""

import re
from fastapi import APIRouter, Depends, HTTPException, Query, status
from supabase import Client
from loguru import logger

from app.core.supabase import get_supabase_client

router = APIRouter(prefix="/customers", tags=["Customer Lookup"])

UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


def _normalize_phone(raw: str) -> str:
    """Strip every non-digit and return what's left.

    Storage convention in this codebase is the 10-digit Malaysian local
    form (e.g. `0176119872`) — see chat.py and the order-creation flow.
    Whatever the caller sends (`+60 17-611 9872`, `0176119872`, etc.),
    we collapse to digits-only and match against stored values that have
    been normalized the same way.
    """
    return re.sub(r"\D", "", raw or "")


@router.get("/lookup")
async def lookup_customer(
    website_id: str = Query(..., description="UUID of the restaurant website"),
    phone: str = Query(..., min_length=1, max_length=32, description="Customer phone (any format; normalized to digits-only server-side)"),
    supabase: Client = Depends(get_supabase_client),
):
    """Lookup a saved customer by (website_id, phone).

    **Public endpoint** — no auth, used by the customer-facing /order flow.

    Returns:
        - `{exists: false}` when no matching customer (200, not 404 — "not found"
          is a valid identify outcome that drives the new-customer UI branch).
        - `{exists: true, customer: {id, name, address}}` when matched.

    Raises:
        - 400 if website_id is not a UUID, or normalized phone is shorter
          than 9 digits.
        - 404 if the website itself does not exist.
        - 500 on database errors.
    """
    if not website_id or not UUID_RE.match(website_id.strip()):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "INVALID_WEBSITE_ID", "message": "website_id must be a valid UUID"},
        )

    normalized = _normalize_phone(phone)
    if len(normalized) < 9:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "INVALID_PHONE", "message": "phone must contain at least 9 digits"},
        )

    try:
        website_check = (
            supabase.table("websites").select("id").eq("id", website_id.strip()).execute()
        )
        if not website_check.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": "WEBSITE_NOT_FOUND", "message": "Website not found"},
            )

        result = (
            supabase.table("website_customers")
            .select("id, name, address, phone")
            .eq("website_id", website_id.strip())
            .eq("phone", normalized)
            .execute()
        )

        if not result.data:
            return {"exists": False}

        customer = result.data[0]
        return {
            "exists": True,
            "customer": {
                "id": customer["id"],
                "name": customer.get("name") or "",
                "address": customer.get("address") or "",
                "phone": customer.get("phone") or normalized,
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Customer Lookup] DB error for website={website_id} phone={normalized}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "LOOKUP_FAILED", "message": "Customer lookup failed"},
        )
