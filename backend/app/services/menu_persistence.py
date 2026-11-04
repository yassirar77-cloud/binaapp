"""The merchant's menu, kept on the website row's tables so a regeneration
can never lose it.

Items used to reach ``menu_items`` only through the publish step, only when
delivery was on, and only for rows that carried a photo — a text-only item
never reached the database, and a regeneration rebuilt the request with
``menu_items`` unset, so every regenerated site shipped with no menu data
at all. Now every named item is written (categories included) when a draft
is persisted and again on publish, and ``load_menu_items`` reads them back
in the shape the generator takes.

The supabase-py sync client is what ``main.py`` uses; the v1 endpoints use
the httpx client in ``supabase_client``. Both are supported.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from loguru import logger

from app.services.data_consistency import parse_price

DEFAULT_CATEGORY = "Menu"


def _coerce(raw: Any) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for entry in (raw or []):
        if hasattr(entry, "model_dump"):
            entry = entry.model_dump()
        elif hasattr(entry, "dict") and not isinstance(entry, dict):
            entry = entry.dict()
        if not isinstance(entry, dict):
            continue
        name = str(entry.get("name") or "").strip()
        if not name:
            continue
        out.append({
            "name": name[:120],
            "price": entry.get("price"),
            "category": str(entry.get("category") or "").strip()[:60],
            "description": str(entry.get("description") or "").strip()[:400],
            "image_url": str(entry.get("image_url") or entry.get("url") or "").strip() or None,
            "signature": bool(entry.get("signature") or entry.get("is_signature") or entry.get("is_popular")),
        })
    return out


def rows_for(website_id: str, items: Any) -> Dict[str, Any]:
    """Pure part: the category and item rows to write. Items without a
    parseable price cannot be stored (``menu_items.price`` is NOT NULL and a
    price must never be invented); they are returned under ``skipped``."""
    coerced = _coerce(items)
    categories: List[str] = []
    for it in coerced:
        cat = it["category"] or DEFAULT_CATEGORY
        if cat not in categories:
            categories.append(cat)
    cat_rows = [
        {"website_id": website_id, "name": c, "name_en": c, "icon": "🍽️", "sort_order": i, "is_active": True}
        for i, c in enumerate(categories)
    ]
    item_rows: List[Dict[str, Any]] = []
    skipped: List[str] = []
    for idx, it in enumerate(coerced):
        dec = parse_price(it["price"])
        if dec is None:
            skipped.append(it["name"])
            continue
        item_rows.append({
            "website_id": website_id,
            "_category": it["category"] or DEFAULT_CATEGORY,
            "name": it["name"],
            "description": it["description"] or None,
            "price": float(dec),
            "image_url": it["image_url"],
            "is_available": True,
            "is_popular": it["signature"],
            "preparation_time": 15,
            "sort_order": idx,
        })
    return {"categories": cat_rows, "items": item_rows, "skipped": skipped}


def persist_menu_items(supabase, website_id: str, items: Any) -> Dict[str, Any]:
    """Replace the website's stored menu with ``items`` (sync supabase-py
    client). Best-effort: never raises; returns a small summary."""
    summary = {"categories": 0, "items": 0, "skipped": []}
    if supabase is None or not website_id:
        return summary
    plan = rows_for(website_id, items)
    if not plan["items"] and not plan["skipped"]:
        return summary
    try:
        supabase.table("menu_items").delete().eq("website_id", website_id).execute()
        supabase.table("menu_categories").delete().eq("website_id", website_id).execute()
        cat_ids: Dict[str, str] = {}
        for row in plan["categories"]:
            res = supabase.table("menu_categories").insert(row).execute()
            if res.data:
                cat_ids[row["name"]] = res.data[0]["id"]
        rows = []
        for it in plan["items"]:
            cat = it.pop("_category")
            it["category_id"] = cat_ids.get(cat)
            rows.append(it)
        if rows:
            supabase.table("menu_items").insert(rows).execute()
        summary.update(categories=len(cat_ids), items=len(rows), skipped=plan["skipped"])
        logger.info(
            f"🍽️ Menu persisted for website {website_id}: {len(rows)} item(s) in {len(cat_ids)} categor(ies)"
            + (f"; {len(plan['skipped'])} unpriced item(s) not stored: {plan['skipped'][:6]}" if plan["skipped"] else "")
        )
    except Exception as err:
        logger.warning(f"🍽️ Menu persistence failed for website {website_id}: {err}")
    return summary


def items_from_rows(item_rows: List[Dict[str, Any]], category_rows: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
    """DB rows → the generator's item shape ({name, price, category, ...}),
    in category then sort order."""
    cats = {c.get("id"): c for c in (category_rows or []) if isinstance(c, dict)}
    out = []
    for row in sorted(
        [r for r in (item_rows or []) if isinstance(r, dict)],
        key=lambda r: ((cats.get(r.get("category_id")) or {}).get("sort_order") or 0, r.get("sort_order") or 0),
    ):
        cat = cats.get(row.get("category_id")) or {}
        cat_name = str(cat.get("name") or "").strip()
        price = row.get("price")
        out.append({
            "name": row.get("name") or "",
            "price": f"{float(price):.2f}" if price is not None else "",
            "category": "" if cat_name == DEFAULT_CATEGORY else cat_name,
            "description": row.get("description") or "",
            "image_url": row.get("image_url") or "",
            "signature": bool(row.get("is_popular")),
        })
    return [i for i in out if i["name"]]


def load_menu_items(supabase, website_id: str) -> List[Dict[str, Any]]:
    """Sync supabase-py read of the stored menu."""
    if supabase is None or not website_id:
        return []
    try:
        items = supabase.table("menu_items").select("*").eq("website_id", website_id).execute().data or []
        cats = supabase.table("menu_categories").select("*").eq("website_id", website_id).execute().data or []
        return items_from_rows(items, cats)
    except Exception as err:
        logger.warning(f"🍽️ Could not load stored menu for {website_id}: {err}")
        return []
