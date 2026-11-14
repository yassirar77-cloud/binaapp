"""Promotions — voucher codes and loyalty points for customer orders.

Owner (login + must own the website):

    GET    /api/v1/promotions/websites/{id}/vouchers
    POST   /api/v1/promotions/websites/{id}/vouchers
    PATCH  /api/v1/promotions/vouchers/{voucher_id}
    DELETE /api/v1/promotions/vouchers/{voucher_id}
    GET    /api/v1/promotions/websites/{id}/loyalty
    PUT    /api/v1/promotions/websites/{id}/loyalty
    GET    /api/v1/promotions/websites/{id}/loyalty/members
    POST   /api/v1/promotions/websites/{id}/loyalty/adjust

Customer (no login, rate-limited per IP):

    POST   /api/v1/promotions/quote

The quote is a preview for the cart and checkout. It never changes
anything, and the order endpoint never trusts it: POST /delivery/orders
re-validates the code and recomputes every amount from the menu prices
(see services/promo_engine.py).
"""

from __future__ import annotations

import time
from collections import defaultdict, deque
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Deque, Dict, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.concurrency import run_in_threadpool
from loguru import logger
from pydantic import BaseModel, Field, field_validator, model_validator
from supabase import Client

from app.core.security import get_current_user
from app.core.supabase import get_supabase_client
from app.models.delivery_schemas import normalize_customer_phone
from app.services import promo_engine as pe

router = APIRouter(prefix="/promotions")

MAX_VOUCHERS_PER_SITE = 100

# Voucher codes are short; without a limit the quote endpoint would let
# anyone guess them at network speed.
_QUOTE_LIMIT = 30
_QUOTE_WINDOW_SECONDS = 60.0
_quote_hits: Dict[str, Deque[float]] = defaultdict(deque)


async def _db(query):
    """Run a sync Supabase query off the event loop (same as delivery.py)."""
    return await run_in_threadpool(query.execute)


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _rate_limited(ip: str) -> bool:
    now = time.monotonic()
    hits = _quote_hits[ip]
    while hits and now - hits[0] > _QUOTE_WINDOW_SECONDS:
        hits.popleft()
    if len(hits) >= _QUOTE_LIMIT:
        return True
    hits.append(now)
    return False


def reset_rate_limits() -> None:
    """Test hook: the window lives in process memory."""
    _quote_hits.clear()


def _user_id(current_user: dict) -> str:
    user_id = current_user.get("sub") or current_user.get("id")
    if not user_id:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User ID not found in token")
    return str(user_id)


async def _require_owner(supabase: Client, website_id: str, user_id: str) -> None:
    res = await _db(
        supabase.table("websites").select("id").eq("id", website_id).eq("user_id", user_id).limit(1)
    )
    if not res.data:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Bukan website anda")


async def _owned_voucher(supabase: Client, voucher_id: str, user_id: str) -> Dict[str, Any]:
    res = await _db(supabase.table("vouchers").select("*").eq("id", voucher_id).limit(1))
    if not res.data:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Baucar tidak ditemui")
    voucher = res.data[0]
    await _require_owner(supabase, voucher["website_id"], user_id)
    return voucher


def _iso(dt: Optional[datetime]) -> Optional[str]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class VoucherBase(BaseModel):
    description: str = Field(default="", max_length=200)
    discount_type: Literal["percent", "fixed"]
    discount_value: Decimal = Field(gt=0, le=10000)
    max_discount: Optional[Decimal] = Field(default=None, gt=0, le=10000)
    min_order: Decimal = Field(default=Decimal("0"), ge=0, le=100000)
    starts_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    usage_limit: Optional[int] = Field(default=None, gt=0, le=1_000_000)
    per_customer_limit: Optional[int] = Field(default=None, gt=0, le=1000)
    is_active: bool = True

    @model_validator(mode="after")
    def check_shape(self):
        if self.discount_type == "percent" and self.discount_value > 100:
            raise ValueError("Diskaun peratus mesti antara 1 hingga 100")
        if self.discount_type == "fixed":
            # A cap only means something for a percentage.
            self.max_discount = None
        if self.starts_at and self.expires_at and self.expires_at <= self.starts_at:
            raise ValueError("Tarikh tamat mesti selepas tarikh mula")
        return self


class VoucherCreate(VoucherBase):
    code: str

    @field_validator("code", mode="before")
    @classmethod
    def clean_code(cls, v):
        code = pe.normalize_code(v)
        if not pe.CODE_RE.match(code):
            raise ValueError("Kod mesti 3–20 huruf atau nombor (tanpa simbol)")
        return code


class VoucherUpdate(BaseModel):
    """Every field optional. The code itself cannot be changed: customers
    may already hold it, and redemptions are counted against it."""

    description: Optional[str] = Field(default=None, max_length=200)
    discount_type: Optional[Literal["percent", "fixed"]] = None
    discount_value: Optional[Decimal] = Field(default=None, gt=0, le=10000)
    max_discount: Optional[Decimal] = Field(default=None, gt=0, le=10000)
    min_order: Optional[Decimal] = Field(default=None, ge=0, le=100000)
    starts_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    usage_limit: Optional[int] = Field(default=None, gt=0, le=1_000_000)
    per_customer_limit: Optional[int] = Field(default=None, gt=0, le=1000)
    is_active: Optional[bool] = None


class LoyaltySettingsBody(BaseModel):
    enabled: bool
    points_per_rm: Decimal = Field(default=Decimal("1"), gt=0, le=100)
    redeem_points: int = Field(default=100, gt=0, le=1_000_000)
    redeem_value: Decimal = Field(default=Decimal("5"), gt=0, le=10000)


class LoyaltyAdjustBody(BaseModel):
    customer_phone: str = Field(min_length=6, max_length=20)
    points: int = Field(ge=-1_000_000, le=1_000_000)

    @field_validator("points")
    @classmethod
    def non_zero(cls, v):
        if v == 0:
            raise ValueError("Mata tidak boleh sifar")
        return v


class QuoteRequest(BaseModel):
    website_id: str = Field(min_length=1, max_length=64)
    subtotal: Decimal = Field(ge=0, le=1_000_000)
    customer_phone: Optional[str] = Field(default=None, max_length=20)
    voucher_code: Optional[str] = Field(default=None, max_length=40)
    redeem_points: bool = False


def _voucher_row(body: VoucherBase) -> Dict[str, Any]:
    return {
        "description": body.description.strip(),
        "discount_type": body.discount_type,
        "discount_value": float(body.discount_value),
        "max_discount": float(body.max_discount) if body.max_discount is not None else None,
        "min_order": float(body.min_order),
        "starts_at": _iso(body.starts_at),
        "expires_at": _iso(body.expires_at),
        "usage_limit": body.usage_limit,
        "per_customer_limit": body.per_customer_limit,
        "is_active": body.is_active,
    }


def _public_voucher(row: Dict[str, Any]) -> Dict[str, Any]:
    return {**row, "summary": pe.describe_voucher(row)}


# ---------------------------------------------------------------------------
# Owner: vouchers
# ---------------------------------------------------------------------------

@router.get("/websites/{website_id}/vouchers")
async def list_vouchers(
    website_id: str,
    current_user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client),
):
    await _require_owner(supabase, website_id, _user_id(current_user))
    res = await _db(
        supabase.table("vouchers").select("*").eq("website_id", website_id).order("created_at", desc=True)
    )
    return {"vouchers": [_public_voucher(v) for v in (res.data or [])]}


@router.post("/websites/{website_id}/vouchers", status_code=status.HTTP_201_CREATED)
async def create_voucher(
    website_id: str,
    body: VoucherCreate,
    current_user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client),
):
    await _require_owner(supabase, website_id, _user_id(current_user))

    existing = await _db(
        supabase.table("vouchers").select("id, code").eq("website_id", website_id)
    )
    rows = existing.data or []
    if any(r.get("code") == body.code for r in rows):
        raise HTTPException(status.HTTP_409_CONFLICT, f"Kod {body.code} sudah wujud")
    if len(rows) >= MAX_VOUCHERS_PER_SITE:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Had {MAX_VOUCHERS_PER_SITE} baucar dicapai. Padam baucar lama dahulu.",
        )

    row = {"website_id": website_id, "code": body.code, **_voucher_row(body)}
    res = await _db(supabase.table("vouchers").insert(row))
    if not res.data:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Gagal menyimpan baucar")
    return _public_voucher(res.data[0])


@router.patch("/vouchers/{voucher_id}")
async def update_voucher(
    voucher_id: str,
    body: VoucherUpdate,
    current_user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client),
):
    voucher = await _owned_voucher(supabase, voucher_id, _user_id(current_user))

    # exclude_unset: a field the client did not send is left alone, while an
    # explicit null clears an optional limit or date.
    changes = body.model_dump(exclude_unset=True)
    if not changes:
        return _public_voucher(voucher)
    for required in ("discount_type", "discount_value", "min_order", "is_active", "description"):
        if required in changes and changes[required] is None:
            raise HTTPException(422, f"{required} tidak boleh kosong")

    # Validate the voucher as it will be after the change, not the patch alone.
    merged = {**voucher, **changes}
    try:
        checked = VoucherBase(**{k: merged.get(k) for k in VoucherBase.model_fields})
    except ValueError as exc:
        raise HTTPException(422, str(exc))

    row = _voucher_row(checked)
    row["updated_at"] = datetime.now(timezone.utc).isoformat()
    res = await _db(supabase.table("vouchers").update(row).eq("id", voucher_id))
    if not res.data:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Gagal mengemas kini baucar")
    return _public_voucher(res.data[0])


@router.delete("/vouchers/{voucher_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_voucher(
    voucher_id: str,
    current_user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client),
):
    await _owned_voucher(supabase, voucher_id, _user_id(current_user))
    await _db(supabase.table("vouchers").delete().eq("id", voucher_id))
    return None


# ---------------------------------------------------------------------------
# Owner: loyalty
# ---------------------------------------------------------------------------

@router.get("/websites/{website_id}/loyalty")
async def get_loyalty(
    website_id: str,
    current_user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client),
):
    await _require_owner(supabase, website_id, _user_id(current_user))
    return await pe.get_loyalty_settings(supabase, _db, website_id)


@router.put("/websites/{website_id}/loyalty")
async def put_loyalty(
    website_id: str,
    body: LoyaltySettingsBody,
    current_user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client),
):
    await _require_owner(supabase, website_id, _user_id(current_user))
    row = {
        "website_id": website_id,
        "enabled": body.enabled,
        "points_per_rm": float(body.points_per_rm),
        "redeem_points": body.redeem_points,
        "redeem_value": float(body.redeem_value),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    res = await _db(supabase.table("loyalty_settings").upsert(row, on_conflict="website_id"))
    return pe.clean_loyalty_settings((res.data or [row])[0])


@router.get("/websites/{website_id}/loyalty/members")
async def list_loyalty_members(
    website_id: str,
    limit: int = 50,
    current_user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client),
):
    await _require_owner(supabase, website_id, _user_id(current_user))
    limit = max(1, min(int(limit), 200))
    res = await _db(
        supabase.table("loyalty_balances")
        .select("customer_phone, balance, lifetime_earned, last_activity_at")
        .eq("website_id", website_id)
        .order("balance", desc=True)
        .limit(limit)
    )
    return {"members": res.data or []}


@router.post("/websites/{website_id}/loyalty/adjust")
async def adjust_loyalty_points(
    website_id: str,
    body: LoyaltyAdjustBody,
    current_user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client),
):
    """Grant or remove points by hand (a goodwill top-up, a correction)."""
    await _require_owner(supabase, website_id, _user_id(current_user))
    phone = normalize_customer_phone(body.customer_phone)
    balance = await pe.get_loyalty_balance(supabase, _db, website_id, phone)
    if balance + body.points < 0:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Baki pelanggan hanya {balance} mata",
        )
    await _db(supabase.table("loyalty_ledger").insert({
        "website_id": website_id,
        "customer_phone": phone,
        "points": body.points,
        "reason": "adjust",
    }))
    return {"customer_phone": phone, "balance": balance + body.points}


# ---------------------------------------------------------------------------
# Customer: quote
# ---------------------------------------------------------------------------

@router.post("/quote")
async def quote(
    body: QuoteRequest,
    request: Request,
    supabase: Client = Depends(get_supabase_client),
):
    """What a voucher code and/or the customer's points would take off this
    cart. A preview only — the order endpoint decides the real amounts."""
    if _rate_limited(_client_ip(request)):
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "Terlalu banyak percubaan. Sila cuba sebentar lagi.",
        )

    subtotal = body.subtotal
    phone = normalize_customer_phone(body.customer_phone) if body.customer_phone else ""
    code = pe.normalize_code(body.voucher_code)

    voucher_out: Optional[Dict[str, Any]] = None
    voucher_discount = Decimal("0")
    if code:
        voucher_out = {"code": code, "valid": False, "discount": 0.0, "summary": "",
                       "message": "Kod promo tidak sah"}
        try:
            voucher = await pe.find_voucher(supabase, _db, body.website_id, code)
            uses = None
            if voucher and phone and voucher.get("per_customer_limit") is not None:
                uses = await pe.customer_voucher_uses(supabase, _db, voucher["id"], phone)
            problem = pe.voucher_problem(voucher, subtotal, customer_uses=uses)
            if problem:
                voucher_out["message"] = problem
            else:
                voucher_discount = pe.voucher_discount(voucher, subtotal)
                voucher_out.update(
                    valid=True,
                    discount=float(voucher_discount),
                    summary=pe.describe_voucher(voucher),
                    message="Kod promo digunakan",
                )
        except Exception as exc:
            # Includes "relation does not exist" before migration 063 runs:
            # the code is simply not valid, the cart keeps working.
            logger.warning(f"[Promo] voucher quote failed for {body.website_id}: {exc}")

    loyalty_out: Dict[str, Any] = {
        "enabled": False, "balance": 0, "redeemable_points": 0,
        "redeem_discount": 0.0, "will_earn": 0,
        "redeem_points": pe.DEFAULT_LOYALTY["redeem_points"],
        "redeem_value": float(pe.DEFAULT_LOYALTY["redeem_value"]),
        "applied": False,
    }
    loyalty_discount = Decimal("0")
    try:
        settings = await pe.get_loyalty_settings(supabase, _db, body.website_id)
        if settings["enabled"]:
            balance = (
                await pe.get_loyalty_balance(supabase, _db, body.website_id, phone) if phone else 0
            )
            payable = subtotal - voucher_discount
            points, discount = pe.loyalty_redemption(settings, balance, payable)
            applied = bool(body.redeem_points and points > 0)
            if applied:
                loyalty_discount = discount
            loyalty_out = {
                "enabled": True,
                "balance": balance,
                "redeemable_points": points,
                "redeem_discount": float(discount),
                "will_earn": pe.points_for(settings, payable - loyalty_discount),
                "redeem_points": settings["redeem_points"],
                "redeem_value": settings["redeem_value"],
                "applied": applied,
            }
    except Exception as exc:
        logger.warning(f"[Promo] loyalty quote failed for {body.website_id}: {exc}")

    total_discount = voucher_discount + loyalty_discount
    return {
        "subtotal": float(subtotal),
        "voucher": voucher_out,
        "loyalty": loyalty_out,
        "discount_total": float(total_discount),
        "payable_subtotal": float(max(subtotal - total_discount, Decimal("0"))),
    }
