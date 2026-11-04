"""Read a menu from a photographed menu board.

Two test merchants uploaded a photo of their menu board in step 06 and
typed nothing, and both sites were built with no items. A menu board IS
the menu: the vision model (Qwen-VL, GLM-4.5V as fallback) reads it into
{name, price, category} rows. The create page offers this as "Baca menu
dari gambar" so the merchant reviews the rows before generating; the
generator also falls back to it when no items were supplied and a poster
was uploaded, so a menu-board photo never produces an invented menu.

Pure apart from the injected model call; ``ai_service`` owns the keys.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Awaitable, Callable, Dict, List, Optional

from app.services.data_consistency import format_price

logger = logging.getLogger(__name__)

MAX_ITEMS = 80
_JSON_SHAPE = (
    '{"is_menu": true|false, "items": [{"name": "exact item name as printed", "price": "12.50", "category": "section heading above it or empty"}]}'
)


def build_messages(image_url: str) -> List[Dict[str, Any]]:
    system = (
        "You transcribe restaurant menu boards and price lists for a website builder. Copy every item EXACTLY as "
        "printed (same spelling, same language, keep set names like 'Set A – Ayam Gepuk'), with its price as a "
        "plain decimal (RM12.50 → \"12.50\"; a size or quantity stays in the name, e.g. 'Air Mineral 500ml'). "
        "Use the section heading printed above an item as its category ('Set Ayam', 'Minuman'). Never invent an "
        "item or a price that is not printed; leave price empty when none is printed. Items marked coming soon or "
        "unavailable are still listed, with their note appended in brackets. Respond with ONLY a JSON object in this "
        "shape:\n" + _JSON_SHAPE
    )
    text = (
        "Is this image a menu board / price list? If yes, transcribe every item with its price and section. "
        "If it is not a menu (a dish photo, a shopfront, a logo), answer is_menu=false with an empty items list."
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": [
            {"type": "image_url", "image_url": {"url": image_url}},
            {"type": "text", "text": text},
        ]},
    ]


def parse_items(raw: Optional[str]) -> Dict[str, Any]:
    """Model output → {"is_menu": bool, "items": [{name, price, category}]}.
    Tolerant of fences and prose around the JSON; never raises."""
    out: Dict[str, Any] = {"is_menu": False, "items": []}
    if not raw:
        return out
    text = str(raw)
    m = re.search(r"\{[\s\S]*\}", text)
    if not m:
        return out
    try:
        data = json.loads(m.group(0))
    except Exception:
        # A trailing comma or a stray fence: try the lenient repair once.
        try:
            data = json.loads(re.sub(r",\s*([\]}])", r"\1", m.group(0)))
        except Exception:
            return out
    if not isinstance(data, dict):
        return out
    items: List[Dict[str, str]] = []
    seen = set()
    for entry in (data.get("items") or [])[:MAX_ITEMS * 2]:
        if not isinstance(entry, dict):
            continue
        name = re.sub(r"\s+", " ", str(entry.get("name") or "")).strip(" -–:")
        if len(name) < 2 or len(name) > 120:
            continue
        key = name.lower()
        if key in seen:
            continue
        seen.add(key)
        raw_price = str(entry.get("price") or "").strip()
        price = format_price(raw_price) if raw_price else None
        price_out = price.replace("RM", "") if price else ""
        category = re.sub(r"\s+", " ", str(entry.get("category") or "")).strip()[:60]
        items.append({"name": name[:120], "price": price_out, "category": category})
        if len(items) >= MAX_ITEMS:
            break
    out["is_menu"] = bool(data.get("is_menu")) or len(items) >= 3
    out["items"] = items if out["is_menu"] else []
    return out


async def read_menu_from_image(
    image_url: str,
    *,
    call_model: Callable[[List[Dict[str, Any]]], Awaitable[Optional[str]]],
) -> Dict[str, Any]:
    """Run the transcription. A model failure returns no items."""
    try:
        raw = await call_model(build_messages(image_url))
    except Exception as err:
        logger.warning(f"🧾 Menu OCR call failed: {err}")
        raw = None
    result = parse_items(raw)
    result["image_url"] = image_url
    priced = sum(1 for i in result["items"] if i["price"])
    logger.info(f"🧾 Menu OCR: is_menu={result['is_menu']} items={len(result['items'])} priced={priced} ({image_url[:80]})")
    return result
