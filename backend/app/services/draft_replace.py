"""Publish a draft OVER one of the merchant's live sites ("Terbitkan ke
subdomain").

A generation leaves a ``pending_payment`` draft row (``draft-<id>``). The
create page can publish only the page it is holding in memory; a draft made
in another session (agp: generated, reviewed, approved) had no way to go
live. My Projects now offers "Terbitkan ke subdomain" on a draft card: pick
which of your live subdomains to replace, confirm, and the live page is
swapped.

``/api/publish`` alone would do the wrong thing with a draft's HTML: the
page embeds the DRAFT's id (data-website-id, widget script tags), which the
publish step treats as "promote this draft" — a second row on the subdomain,
a quota charge, and chat/delivery widgets pointing at the draft. So the
replace mode resolves the request server-side:

- both rows must belong to the caller; the draft must be a draft, the
  target a published site with a subdomain;
- the HTML comes from the draft row, with every occurrence of the draft id
  rewritten to the live site's id;
- description, business fields, address and the menu come from the draft
  row (the menu from its persisted ``menu_items``);
- the publish then runs as a republish of the live row (same id, same
  subdomain, no promotion, no quota charge).

Returns the body fields to merge, or an (HTTP status, error payload) pair.
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from loguru import logger

DRAFT_STATUSES = ("pending_payment", "draft", "generated")

_DRAFT_COLUMNS = (
    "id, user_id, status, subdomain, html_content, business_name, name, description, "
    "business_type, location_address, hero_image_prompt"
)
_TARGET_COLUMNS = "id, user_id, status, subdomain, business_name, name"


def _one(supabase, table: str, columns: str, row_id: str) -> Optional[Dict[str, Any]]:
    res = supabase.table(table).select(columns).eq("id", row_id).limit(1).execute()
    return (res.data or [None])[0]


def resolve_replace_request(
    supabase, user_id: str, draft_id: str, target_id: str,
) -> Tuple[Optional[Dict[str, Any]], Optional[Tuple[int, Dict[str, Any]]]]:
    """(body fields, None) on success; (None, (status, payload)) on refusal."""
    def _err(status: int, code: str, message: str):
        return None, (status, {"success": False, "error": code, "message": message})

    if not draft_id or not target_id:
        return _err(400, "replace_missing_ids", "draft_id dan replace_website_id diperlukan.")
    if draft_id == target_id:
        return _err(400, "replace_same_row", "Draf dan laman langsung adalah baris yang sama.")
    draft = _one(supabase, "websites", _DRAFT_COLUMNS, draft_id)
    target = _one(supabase, "websites", _TARGET_COLUMNS, target_id)
    if not draft or not target:
        return _err(404, "replace_not_found", "Draf atau laman langsung tidak dijumpai.")
    if draft.get("user_id") != user_id or target.get("user_id") != user_id:
        return _err(403, "replace_not_owner", "Draf dan laman langsung mesti milik akaun anda.")
    if str(draft.get("status") or "") not in DRAFT_STATUSES:
        return _err(409, "replace_not_a_draft", "Hanya draf boleh diterbitkan ke subdomain.")
    subdomain = str(target.get("subdomain") or "").strip().lower()
    if target.get("status") != "published" or not subdomain or subdomain.startswith("draft-"):
        return _err(409, "replace_target_not_live", "Subdomain yang dipilih belum diterbitkan.")
    html = str(draft.get("html_content") or "")
    if len(html) < 500:
        return _err(409, "replace_draft_empty", "Draf ini tiada kandungan untuk diterbitkan.")

    # The page embeds the draft's id (data-website-id, widget tags): point it
    # at the live site so the publish is a republish, not a draft promotion.
    html = html.replace(draft_id, target_id)

    menu_items = []
    try:
        from app.services.menu_persistence import load_menu_items
        menu_items = load_menu_items(supabase, draft_id) or []
    except Exception as err:  # the page still has its menu; only the rows are missing
        logger.warning(f"🔁 Draft {draft_id[:8]} menu rows not loaded: {err}")

    name = str(draft.get("business_name") or draft.get("name") or target.get("business_name") or "").strip()
    fields: Dict[str, Any] = {
        "html_content": html,
        "subdomain": subdomain,
        "website_id": target_id,
        "project_name": name or subdomain,
        "business_name": name,
        "description": draft.get("description") or None,
        "business_type": draft.get("business_type") or None,
        "hero_image_prompt": draft.get("hero_image_prompt") or None,
        "menu_items": menu_items,
        # The merchant picked this subdomain and confirmed the swap.
        "replace_existing": True,
    }
    if draft.get("location_address"):
        fields["address"] = draft["location_address"]
    logger.info(
        f"🔁 Draft {draft_id[:8]} will replace the live page on {subdomain} (row {target_id[:8]}); "
        f"{len(menu_items)} menu item(s) carried over"
    )
    return fields, None
