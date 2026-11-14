"""Voucher codes and loyalty points for customer orders.

The checkout used to show a hardcoded "BINAAPP10" discount that the server
never applied. Everything about money now happens here, on the server:

  * the maths (`voucher_discount`, `loyalty_redemption`, `points_for`) and
    the eligibility rules (`voucher_problem`) are pure functions;
  * `apply_to_order` claims the voucher use and spends the points through
    the race-safe SQL functions from migration 063 BEFORE the order row is
    written, and `rollback` hands both back if the order then fails to save.

The order endpoint only calls into this module when the customer actually
sent a voucher code or asked to spend points, so order creation keeps
working unchanged on a database that has not run migration 063 yet.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import ROUND_DOWN, ROUND_HALF_UP, Decimal
from typing import Any, Awaitable, Callable, Dict, Optional, Tuple

from loguru import logger

CODE_RE = re.compile(r"^[A-Z0-9]{3,20}$")
CENT = Decimal("0.01")

DEFAULT_LOYALTY = {
    "enabled": False,
    "points_per_rm": 1,
    "redeem_points": 100,
    "redeem_value": 5,
}


class PromoError(Exception):
    """A promotion the customer asked for cannot be applied.

    `code` is a stable machine tag; `message` is the Malay text shown to
    the customer.
    """

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass
class PromoResult:
    """What was applied to one order, and what to undo if it fails."""

    voucher_code: Optional[str] = None
    voucher_discount: Decimal = Decimal("0")
    redemption_id: Optional[str] = None
    points_redeemed: int = 0
    loyalty_discount: Decimal = Decimal("0")
    ledger_id: Optional[str] = None

    @property
    def total_discount(self) -> Decimal:
        return self.voucher_discount + self.loyalty_discount

    @property
    def applied(self) -> bool:
        return bool(self.redemption_id or self.ledger_id)


# ---------------------------------------------------------------------------
# Pure logic
# ---------------------------------------------------------------------------

def normalize_code(raw: Any) -> str:
    """Customers type codes with spaces, dashes and lower case."""
    return re.sub(r"[\s\-]", "", str(raw or "")).upper()


def _dec(value: Any, default: str = "0") -> Decimal:
    if value is None or value == "":
        return Decimal(default)
    try:
        return Decimal(str(value))
    except Exception:
        return Decimal(default)


def _parse_ts(value: Any) -> Optional[datetime]:
    if not value:
        return None
    if isinstance(value, datetime):
        dt = value
    else:
        try:
            dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError:
            return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def voucher_problem(
    voucher: Optional[Dict[str, Any]],
    subtotal: Decimal,
    *,
    now: Optional[datetime] = None,
    customer_uses: Optional[int] = None,
) -> Optional[str]:
    """Why this voucher cannot be used on this order, in Malay. None = usable.

    `customer_uses` is how many times this customer already used it; pass
    None when the customer is not known yet (the per-customer limit is then
    enforced at claim time).
    """
    if not voucher or not voucher.get("is_active", True):
        return "Kod promo tidak sah"
    now = now or datetime.now(timezone.utc)
    starts_at = _parse_ts(voucher.get("starts_at"))
    expires_at = _parse_ts(voucher.get("expires_at"))
    if starts_at and now < starts_at:
        return "Kod promo ini belum bermula"
    if expires_at and now >= expires_at:
        return "Kod promo ini telah tamat tempoh"
    limit = voucher.get("usage_limit")
    if limit is not None and int(voucher.get("used_count") or 0) >= int(limit):
        return "Kod promo ini telah habis ditebus"
    per_customer = voucher.get("per_customer_limit")
    if (
        per_customer is not None
        and customer_uses is not None
        and customer_uses >= int(per_customer)
    ):
        return "Anda telah menggunakan kod promo ini"
    min_order = _dec(voucher.get("min_order"))
    if subtotal < min_order:
        return f"Pesanan minimum RM{min_order:.2f} untuk kod promo ini"
    return None


def voucher_discount(voucher: Dict[str, Any], subtotal: Decimal) -> Decimal:
    """RM off the food subtotal. Never more than the subtotal itself."""
    value = _dec(voucher.get("discount_value"))
    if voucher.get("discount_type") == "percent":
        raw = subtotal * value / Decimal(100)
        cap = voucher.get("max_discount")
        if cap is not None:
            raw = min(raw, _dec(cap))
    else:
        raw = value
    raw = max(Decimal("0"), min(raw, subtotal))
    return raw.quantize(CENT, rounding=ROUND_HALF_UP)


def describe_voucher(voucher: Dict[str, Any]) -> str:
    """Short Malay summary, e.g. "10% diskaun (maks RM5.00)"."""
    value = _dec(voucher.get("discount_value"))
    if voucher.get("discount_type") == "percent":
        text = f"{value.normalize():f}% diskaun"
        if voucher.get("max_discount") is not None:
            text += f" (maks RM{_dec(voucher['max_discount']):.2f})"
    else:
        text = f"RM{value:.2f} diskaun"
    min_order = _dec(voucher.get("min_order"))
    if min_order > 0:
        text += f" · min. RM{min_order:.2f}"
    return text


def clean_loyalty_settings(row: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Settings with defaults filled in; a missing row means 'off'."""
    row = row or {}
    return {
        "enabled": bool(row.get("enabled", DEFAULT_LOYALTY["enabled"])),
        "points_per_rm": float(_dec(row.get("points_per_rm"), "1")),
        "redeem_points": int(row.get("redeem_points") or DEFAULT_LOYALTY["redeem_points"]),
        "redeem_value": float(_dec(row.get("redeem_value"), "5")),
    }


def points_for(settings: Dict[str, Any], amount: Decimal) -> int:
    """Points an order of `amount` (discounted food subtotal) will earn."""
    if not settings.get("enabled"):
        return 0
    rate = _dec(settings.get("points_per_rm"), "1")
    return int((max(amount, Decimal("0")) * rate).to_integral_value(rounding=ROUND_DOWN))


def loyalty_redemption(
    settings: Dict[str, Any],
    balance: int,
    payable: Decimal,
) -> Tuple[int, Decimal]:
    """The most a customer can spend right now: (points, RM off).

    Points are spent in whole blocks of `redeem_points`. The discount never
    exceeds `payable` (the food subtotal left after any voucher), and no
    block is spent that would be worth nothing.
    """
    if not settings.get("enabled") or balance <= 0 or payable <= 0:
        return 0, Decimal("0")
    block_points = int(settings.get("redeem_points") or 0)
    block_value = _dec(settings.get("redeem_value"))
    if block_points <= 0 or block_value <= 0:
        return 0, Decimal("0")
    blocks_by_balance = balance // block_points
    # Enough blocks to cover the payable amount, the last one possibly partial.
    blocks_needed = int((payable / block_value).to_integral_value(rounding=ROUND_DOWN))
    if blocks_needed * block_value < payable:
        blocks_needed += 1
    blocks = min(blocks_by_balance, blocks_needed)
    if blocks <= 0:
        return 0, Decimal("0")
    discount = min(blocks * block_value, payable).quantize(CENT, rounding=ROUND_HALF_UP)
    return blocks * block_points, discount


# ---------------------------------------------------------------------------
# Database access (the caller passes its own executor so queries run in the
# threadpool the same way the rest of the order endpoint does)
# ---------------------------------------------------------------------------

Db = Callable[[Any], Awaitable[Any]]


async def find_voucher(supabase, db: Db, website_id: str, code: str) -> Optional[Dict[str, Any]]:
    code = normalize_code(code)
    if not CODE_RE.match(code):
        return None
    res = await db(
        supabase.table("vouchers").select("*").eq("website_id", website_id).eq("code", code).limit(1)
    )
    rows = res.data or []
    return rows[0] if rows else None


async def customer_voucher_uses(supabase, db: Db, voucher_id: str, phone: str) -> int:
    res = await db(
        supabase.table("voucher_redemptions")
        .select("id", count="exact")
        .eq("voucher_id", voucher_id)
        .eq("customer_phone", phone)
    )
    if getattr(res, "count", None) is not None:
        return int(res.count)
    return len(res.data or [])


async def get_loyalty_settings(supabase, db: Db, website_id: str) -> Dict[str, Any]:
    res = await db(
        supabase.table("loyalty_settings").select("*").eq("website_id", website_id).limit(1)
    )
    rows = res.data or []
    return clean_loyalty_settings(rows[0] if rows else None)


async def get_loyalty_balance(supabase, db: Db, website_id: str, phone: str) -> int:
    res = await db(
        supabase.table("loyalty_balances")
        .select("balance")
        .eq("website_id", website_id)
        .eq("customer_phone", phone)
        .limit(1)
    )
    rows = res.data or []
    return int(rows[0].get("balance") or 0) if rows else 0


def _rpc_scalar(res: Any) -> Optional[str]:
    """PostgREST returns a scalar function result bare, or wrapped in a list."""
    data = getattr(res, "data", None)
    if isinstance(data, list):
        data = data[0] if data else None
    if isinstance(data, dict):
        data = next(iter(data.values()), None)
    return str(data) if data else None


async def apply_to_order(
    supabase,
    db: Db,
    *,
    website_id: str,
    phone: str,
    subtotal: Decimal,
    voucher_code: Optional[str],
    redeem_points: bool,
) -> PromoResult:
    """Claim what the customer asked for. Raises PromoError if it cannot be
    honoured — the order must then NOT be created, so the customer is never
    charged a total they did not see."""
    result = PromoResult()

    code = normalize_code(voucher_code)
    if code:
        voucher = await find_voucher(supabase, db, website_id, code)
        uses = (
            await customer_voucher_uses(supabase, db, voucher["id"], phone)
            if voucher and voucher.get("per_customer_limit") is not None
            else None
        )
        problem = voucher_problem(voucher, subtotal, customer_uses=uses)
        if problem:
            raise PromoError("VOUCHER_INVALID", problem)
        discount = voucher_discount(voucher, subtotal)
        claimed = _rpc_scalar(await db(supabase.rpc(
            "claim_voucher",
            {"p_voucher_id": voucher["id"], "p_phone": phone, "p_discount": float(discount)},
        )))
        if not claimed:
            # Lost a race for the last use between the check and the claim.
            raise PromoError("VOUCHER_INVALID", "Kod promo ini telah habis ditebus")
        result.voucher_code = code
        result.voucher_discount = discount
        result.redemption_id = claimed

    if redeem_points:
        try:
            settings = await get_loyalty_settings(supabase, db, website_id)
            balance = await get_loyalty_balance(supabase, db, website_id, phone)
            points, discount = loyalty_redemption(
                settings, balance, subtotal - result.voucher_discount
            )
            if points > 0:
                ledger_id = _rpc_scalar(await db(supabase.rpc(
                    "redeem_loyalty_points",
                    {"p_website_id": website_id, "p_phone": phone, "p_points": points},
                )))
                if not ledger_id:
                    raise PromoError(
                        "LOYALTY_INSUFFICIENT",
                        "Mata ganjaran tidak mencukupi. Sila semak semula.",
                    )
                result.points_redeemed = points
                result.loyalty_discount = discount
                result.ledger_id = ledger_id
            else:
                raise PromoError(
                    "LOYALTY_INSUFFICIENT",
                    "Mata ganjaran belum cukup untuk ditebus.",
                )
        except Exception:
            # The voucher was already claimed above; do not leak that use.
            await rollback(supabase, db, result)
            raise

    return result


async def attach_order(supabase, db: Db, result: PromoResult, order_id: str) -> None:
    """Tie the claimed voucher use / spent points to the saved order, so a
    later cancellation can find and return them. Best effort."""
    try:
        if result.redemption_id:
            await db(
                supabase.table("voucher_redemptions")
                .update({"order_id": order_id})
                .eq("id", result.redemption_id)
            )
        if result.ledger_id:
            await db(
                supabase.table("loyalty_ledger")
                .update({"order_id": order_id})
                .eq("id", result.ledger_id)
            )
    except Exception as exc:  # pragma: no cover - logged, never fatal
        logger.warning(f"[Promo] could not attach promo to order {order_id}: {exc}")


async def rollback(supabase, db: Db, result: PromoResult) -> None:
    """Return a claimed voucher use and spent points. Never raises."""
    if result.redemption_id:
        try:
            await db(supabase.rpc("release_voucher", {"p_redemption_id": result.redemption_id}))
        except Exception as exc:
            logger.error(f"[Promo] release_voucher {result.redemption_id} failed: {exc}")
        result.redemption_id = None
    if result.ledger_id:
        try:
            await db(supabase.table("loyalty_ledger").delete().eq("id", result.ledger_id))
        except Exception as exc:
            logger.error(f"[Promo] loyalty refund {result.ledger_id} failed: {exc}")
        result.ledger_id = None
