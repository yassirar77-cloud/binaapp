"""Menu Import — the merchant's existing menu, read by AI into rows.

    POST /api/v1/menu/import/extract                         file or text → DRAFT items (nothing saved)
    POST /api/v1/menu/websites/{website_id}/menu-items/bulk  reviewed rows → menu_items (+ categories)

TWO STEPS ON PURPOSE
--------------------
``extract`` returns a draft and writes nothing. The merchant ticks, unticks
and fixes prices in the UI, then either keeps the rows on the create page
(they travel with the generation request as ``menu_items``) or, for a site
that already exists, commits them with ``bulk``. The AI never puts a row on a
live menu by itself.

COST GUARDS
-----------
``extract`` is the only AI call. A per-user hourly cap (MENU_IMPORT_MAX_PER_HOUR,
default 30, in-memory) and the 10 MB / 12-page limits in the service keep a
runaway client from burning model credit. The deterministic parser answers
when no model is reachable, so a merchant with a plain PDF is never blocked
on an API outage.

QUOTA
-----
``extract`` does not touch usage counters (nothing is created). ``bulk``
enforces the plan's menu-item limit exactly like ``create_menu_item`` does,
once for the whole batch, and increments ``menu_items_count`` by the number
of rows actually inserted.
"""

from __future__ import annotations

import asyncio
import os
import re
import time
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from loguru import logger
from pydantic import BaseModel, Field, field_validator
from supabase import Client

from app.core.security import get_current_user
from app.core.supabase import get_supabase_client
from app.services import menu_import
from app.services.subscription_service import subscription_service

router = APIRouter()

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_PASTED_CHARS = menu_import.MAX_TEXT_CHARS


def _enabled() -> bool:
    return os.getenv("MENU_IMPORT_ENABLED", "true").strip().lower() not in ("0", "false", "no", "off")


def _max_per_hour() -> int:
    try:
        return max(1, int(os.getenv("MENU_IMPORT_MAX_PER_HOUR", "30")))
    except ValueError:
        return 30


#: Process-local hourly counter: {user_id: [monotonic timestamps]}. A cost
#: guard, not an entitlement ledger — it resets on restart.
_requests: Dict[str, List[float]] = {}


def _count_recent(user_id: str) -> int:
    cutoff = time.monotonic() - 3600
    stamps = [t for t in _requests.get(user_id, []) if t >= cutoff]
    _requests[user_id] = stamps
    return len(stamps)


def _record(user_id: str) -> None:
    _requests.setdefault(user_id, []).append(time.monotonic())


def _reset_rate_limits() -> None:
    """Test hook."""
    _requests.clear()


def _feature_gate() -> None:
    if not _enabled():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")


def _error(status_code: int, code: str, message: str) -> HTTPException:
    return HTTPException(status_code=status_code, detail={"error": code, "message": message})


# ---------------------------------------------------------------------------
# POST /menu/import/extract
# ---------------------------------------------------------------------------

@router.post("/import/extract")
async def extract_menu(
    file: Optional[UploadFile] = File(None),
    text: Optional[str] = Form(None),
    mode: str = Form("all"),
    instruction: str = Form(""),
    max_items: int = Form(menu_import.DEFAULT_MAX_ITEMS),
    language: str = Form("ms"),
    business_type: str = Form(""),
    current_user: dict = Depends(get_current_user),
):
    """Read a menu file (PDF / Word / Excel / CSV / text / photo) or pasted
    text into draft menu rows. Nothing is saved — the merchant reviews first.

    ``mode``: ``all`` (every item), ``signature`` (marked / best-selling
    items only), ``custom`` (follow ``instruction``, e.g. "5 killer menu
    sahaja" or "set ayam dan minuman, kecuali add-on").
    """
    _feature_gate()
    user_id = current_user.get("id") or current_user.get("sub") or "anonymous"

    pasted = (text or "").strip()
    if file is None and not pasted:
        raise _error(400, "no_input", "Muat naik fail menu atau tampal teks menu.")
    if len(pasted) > MAX_PASTED_CHARS:
        raise _error(413, "text_too_long", f"Teks terlalu panjang (had {MAX_PASTED_CHARS:,} aksara).")

    if _count_recent(user_id) >= _max_per_hour():
        raise _error(429, "rate_limited", "Terlalu banyak import dalam sejam. Cuba lagi sebentar.")

    mode = (mode or "all").strip().lower()
    if mode not in menu_import.SELECTION_MODES:
        raise _error(400, "bad_mode", "mode mesti 'all', 'signature' atau 'custom'.")
    instruction = (instruction or "").strip()[:400]
    try:
        cap = max(1, min(int(max_items), menu_import.MAX_ITEMS_HARD_CAP))
    except (TypeError, ValueError):
        cap = menu_import.DEFAULT_MAX_ITEMS
    language = "en" if str(language or "ms").lower().startswith("en") else "ms"
    business_type = re.sub(r"[^a-z_ -]", "", (business_type or "").lower())[:40]

    # ---- source ---------------------------------------------------------
    try:
        if file is not None:
            data = await file.read()
            if len(data) > MAX_UPLOAD_BYTES:
                raise _error(413, "file_too_large", "Fail melebihi 10MB. Kecilkan fail atau muat naik gambar setiap muka surat.")
            if not data:
                raise _error(400, "empty_file", "Fail kosong.")
            # pypdf / zip parsing is CPU work — keep it off the event loop.
            source = await asyncio.to_thread(menu_import.extract_source, file.filename, file.content_type, data)
            if pasted:
                source.text = (source.text + "\n\n" + pasted).strip()
        else:
            source = menu_import.ExtractedSource(kind="text", text=pasted, pages=1)
    except menu_import.MenuImportError as err:
        raise _error(415 if err.code == "unsupported_type" else 422, err.code, err.message)

    if not source.has_text and not source.images:
        raise _error(422, "no_content", "Tiada teks atau gambar dapat dibaca daripada fail ini.")

    _record(user_id)
    logger.info(
        f"🍽️ Menu import: user={user_id} kind={source.kind} pages={source.pages} "
        f"chars={len(source.text)} images={len(source.images)} mode={mode} instruction={instruction[:60]!r}"
    )

    try:
        result = await menu_import.import_menu(
            source,
            mode=mode,
            instruction=instruction,
            language=language,
            max_items=cap,
            business_hint=business_type,
        )
    except menu_import.MenuImportError as err:
        raise _error(422, err.code, err.message)

    body = result.to_dict()
    body["plan"] = await _plan_snapshot(user_id)
    logger.info(f"🍽️ Menu import: engine={result.engine} found={result.total_found} returned={len(result.items)}")
    return body


async def _plan_snapshot(user_id: str) -> Optional[Dict[str, Any]]:
    """How many menu items the plan still allows — so the UI can warn before
    the merchant ticks 34 items on a 20-item plan. Best-effort."""
    try:
        check = await subscription_service.check_limit(user_id, "add_menu_item")
    except Exception as err:
        logger.debug(f"🍽️ Menu import: plan lookup skipped: {err}")
        return None
    limit = check.get("limit")
    used = check.get("current_usage") or 0
    unlimited = bool(check.get("unlimited")) or limit is None
    return {
        "menu_items_limit": None if unlimited else limit,
        "menu_items_used": used,
        "remaining": None if unlimited else max(0, int(limit) - int(used)),
        "unlimited": unlimited,
        "allowed": bool(check.get("allowed", True)),
        "requires_renewal": bool(check.get("requires_renewal")),
    }


# ---------------------------------------------------------------------------
# POST /menu/websites/{website_id}/menu-items/bulk
# ---------------------------------------------------------------------------

class BulkMenuItem(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    price: Optional[str] = Field(default=None, max_length=40)
    description: Optional[str] = Field(default=None, max_length=400)
    category: Optional[str] = Field(default=None, max_length=60)
    image_url: Optional[str] = Field(default=None, max_length=1000)
    is_signature: bool = False
    is_available: bool = True

    @field_validator("name", "description", "category", "image_url")
    @classmethod
    def _strip(cls, v):
        if isinstance(v, str):
            v = v.strip()
            return v or None
        return v

    @field_validator("price", mode="before")
    @classmethod
    def _price_to_str(cls, v):
        if v is None:
            return None
        return str(v).strip() or None


class BulkMenuItemsRequest(BaseModel):
    items: List[BulkMenuItem] = Field(..., min_length=1, max_length=menu_import.MAX_ITEMS_HARD_CAP)
    #: Skip rows whose name already exists on this website (case-insensitive).
    skip_duplicates: bool = True
    #: Default description for rows without one. None → left empty.
    default_description: Optional[str] = Field(default=None, max_length=200)


def _norm(name: str) -> str:
    return re.sub(r"\s+", " ", (name or "").strip().lower())


@router.post("/websites/{website_id}/menu-items/bulk", status_code=status.HTTP_201_CREATED)
async def bulk_create_menu_items(
    website_id: str,
    body: BulkMenuItemsRequest,
    current_user: dict = Depends(get_current_user),
    supabase: Client = Depends(get_supabase_client),
):
    """Insert reviewed import rows into ``menu_items`` in one go, creating
    categories by name as needed. One quota check for the whole batch."""
    _feature_gate()
    user_id = current_user.get("id") or current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication token")

    website_check = supabase.table("websites").select("user_id").eq("id", website_id).execute()
    if not website_check.data or website_check.data[0]["user_id"] != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    # ---- rows worth inserting ------------------------------------------
    skipped: List[Dict[str, str]] = []
    candidates: List[BulkMenuItem] = []
    seen: set = set()
    for item in body.items:
        key = _norm(item.name)
        if key in seen:
            skipped.append({"name": item.name, "reason": "duplicate_in_request"})
            continue
        seen.add(key)
        if menu_import.canonical_price(item.price) is None:
            skipped.append({"name": item.name, "reason": "no_price"})
            continue
        candidates.append(item)

    if body.skip_duplicates and candidates:
        existing = supabase.table("menu_items").select("name").eq("website_id", website_id).execute()
        existing_names = {_norm(r.get("name", "")) for r in (existing.data or [])}
        kept: List[BulkMenuItem] = []
        for item in candidates:
            if _norm(item.name) in existing_names:
                skipped.append({"name": item.name, "reason": "already_exists"})
            else:
                kept.append(item)
        candidates = kept

    if not candidates:
        return {"created": 0, "skipped": skipped, "categories_created": [], "items": []}

    # ---- plan limit, once for the batch --------------------------------
    check = await subscription_service.check_limit(user_id, "add_menu_item")
    if not check.get("allowed", True):
        raise _error(
            status.HTTP_402_PAYMENT_REQUIRED if not check.get("requires_renewal") else status.HTTP_403_FORBIDDEN,
            "menu_item_limit",
            check.get("message") or "Had item menu pelan anda telah dicapai.",
        )
    limit = check.get("limit")
    if limit is not None and not check.get("unlimited"):
        remaining = max(0, int(limit) - int(check.get("current_usage") or 0))
        if len(candidates) > remaining:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "error": "menu_item_limit",
                    "message": f"Pelan anda membenarkan {remaining} lagi item menu; anda memilih {len(candidates)}.",
                    "remaining": remaining,
                    "limit": limit,
                    "requested": len(candidates),
                },
            )

    # ---- categories: find or create by name -----------------------------
    cat_rows = supabase.table("menu_categories").select("id,name,sort_order").eq("website_id", website_id).execute()
    categories: Dict[str, str] = {_norm(r["name"]): r["id"] for r in (cat_rows.data or []) if r.get("name")}
    next_sort = 1 + max([int(r.get("sort_order") or 0) for r in (cat_rows.data or [])] or [-1])
    created_categories: List[str] = []
    for item in candidates:
        if not item.category or _norm(item.category) in categories:
            continue
        ins = supabase.table("menu_categories").insert({
            "website_id": website_id,
            "name": item.category[:100],
            "name_en": item.category[:100],
            "sort_order": next_sort,
            "is_active": True,
        }).execute()
        if ins.data:
            categories[_norm(item.category)] = ins.data[0]["id"]
            created_categories.append(item.category)
            next_sort += 1

    # ---- insert ----------------------------------------------------------
    count_rows = supabase.table("menu_items").select("id").eq("website_id", website_id).execute()
    sort_base = len(count_rows.data or [])
    rows = []
    for idx, item in enumerate(candidates):
        rows.append({
            "website_id": website_id,
            "category_id": categories.get(_norm(item.category or "")),
            "name": item.name[:120],
            "description": item.description or body.default_description or None,
            "price": float(menu_import.canonical_price(item.price)),
            "image_url": item.image_url or None,
            "is_available": item.is_available,
            "is_popular": bool(item.is_signature),
            "preparation_time": 15,
            "sort_order": sort_base + idx,
        })
    result = supabase.table("menu_items").insert(rows).execute()
    inserted = result.data or []
    if not inserted:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to insert menu items")

    try:
        await subscription_service.increment_usage(user_id, "add_menu_item", count=len(inserted))
    except Exception as usage_err:
        logger.warning(f"⚠️ Menu import: usage tracking failed: {usage_err}")

    logger.info(f"🍽️ Menu import: bulk inserted {len(inserted)} items for website {website_id} (+{len(created_categories)} categories)")
    return {
        "created": len(inserted),
        "skipped": skipped,
        "categories_created": created_categories,
        "items": inserted,
    }
