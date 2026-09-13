"""Publishing to a subdomain that already answers must never be silent.

WHY THIS EXISTS
---------------
Both publish paths treated "this subdomain belongs to you" as "this is your
site being republished", reused the row and overwrote it. Run 1: Kedai Runcit
Pak Din was published at 04:43:34; a second site, Gerai Burger Malam Adik, was
published to the same subdomain ninety minutes later and took the row —
same id, same created_at, new business, new HTML. The first site stopped
existing, and nothing anywhere said so. The row also kept the first shop's
address while serving the second one, which is what delivery zones, the map
widget and order confirmations read.

Owning a subdomain is not the same as this being the same site. This module
is the one place that difference is decided, so the two endpoints cannot drift
apart on it.

    conflict = subdomain_conflict(existing_row, incoming_name, subdomain)
    if conflict:  ->  409, and the merchant chooses

Pure functions over the row dict a publish already has in hand. No I/O.
"""

from __future__ import annotations

from typing import Dict, Optional


def occupant_name(existing_row: Optional[Dict]) -> str:
    """What the site currently on this subdomain calls itself, or ""."""
    if not existing_row:
        return ""
    return str(
        existing_row.get("business_name") or existing_row.get("name") or ""
    ).strip()


def is_live(existing_row: Optional[Dict]) -> bool:
    """True only for a row that is actually published.

    A draft of your own on the same subdomain is yours to overwrite; there is
    no live site to lose.
    """
    if not existing_row:
        return False
    if str(existing_row.get("status") or "").lower() == "published":
        return True
    return bool(existing_row.get("is_published"))


def is_same_site(existing_row: Optional[Dict], incoming_name: str) -> bool:
    """Is the publish in flight the same site as the one already here?

    The client mints a new website id for every publish, so the id cannot
    answer this — the business name can. An occupant we cannot name, or a
    publish that carries no name, is treated as the same site: those are
    drafts and legacy rows, and refusing them would block merchants from
    republishing their own pages to no purpose.
    """
    occupant = occupant_name(existing_row)
    incoming = str(incoming_name or "").strip()
    if not occupant or not incoming:
        return True
    return occupant.casefold() == incoming.casefold()


def replaces_other_site(existing_row: Optional[Dict], incoming_name: str) -> bool:
    """True when this publish is about to take over a DIFFERENT live site."""
    return is_live(existing_row) and not is_same_site(existing_row, incoming_name)


def subdomain_conflict(
    existing_row: Optional[Dict],
    incoming_name: str,
    subdomain: str,
    replace_existing: bool = False,
) -> Optional[Dict]:
    """The 409 body to return, or None when the publish may go ahead.

    ``replace_existing`` is the merchant's answer to exactly this question,
    and is the only thing that lets a live site be taken over.
    """
    if replace_existing:
        return None
    if not replaces_other_site(existing_row, incoming_name):
        return None
    occupant = occupant_name(existing_row)
    return {
        "success": False,
        "error": "subdomain_in_use",
        "message": (
            f"Subdomain '{subdomain}.binaapp.my' sudah digunakan oleh laman "
            f"'{occupant}'. Pilih subdomain lain, atau sahkan untuk "
            f"menggantikan laman itu."
        ),
        "subdomain": subdomain,
        "existing_business_name": occupant,
    }
