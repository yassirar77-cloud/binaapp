"""
READ-ONLY containment audit for the PATCH /{id}/contact truncation regression.

WHAT IT ANSWERS
  "Which published sites currently have a TRUNCATED / structurally-unbalanced
   stored html_content or storage snapshot?" — i.e. the sites the credit-free
   WhatsApp-number edit could have damaged (or that are broken for any reason).

HOW
  1. Reads every published website row from the DB (id, subdomain, updated_at,
     whatsapp_number, html_content, status) — no writes.
  2. Runs the SAME structural gate the fix uses (utils.html_balance) over the DB
     blob AND the live storage snapshot the middleware actually serves.
  3. Flags any row where the DB blob OR the storage snapshot is unbalanced.
  4. Highlights rows updated at/after the PATCH /contact deploy so you can see
     which breakage falls inside the exposure window.

CAVEAT — attribution:
  The contact endpoint writes NO audit row, so "storage snapshot is unbalanced"
  is a SUPERSET of "damaged by /contact": generation-time truncation (jiwa/huil/
  juio precedent) produces the same symptom. To attribute a specific site to a
  /contact run, cross-reference this list against app logs:
      grep "WhatsApp number updated credit-free for website" <logs>
      # or the access log: PATCH /api/v1/websites/*/contact
  The DEPLOY_CUTOFF filter below narrows the window; logs give certainty.

  It is READ-ONLY: it never republishes, never edits a row, never touches
  storage. Safe to run against prod.

Run from backend/ with SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY set:
    python -m scripts.audit_contact_truncation
"""

import asyncio
import sys

import httpx

from app.core.config import settings
from app.core.supabase import get_supabase_client
from app.utils.html_balance import is_html_balanced

# PATCH /contact shipped in PR #712 (commit cd24df6) at this instant.
# Anything updated before this could not have been touched by the endpoint.
DEPLOY_CUTOFF = "2026-07-06T10:35:06+00:00"  # 18:35:06 +08:00


async def _storage_snapshot(subdomain: str) -> tuple[str | None, int]:
    """Fetch the live serving snapshot (cache-busted). Returns (text, status)."""
    url = (
        f"{settings.SUPABASE_URL}/storage/v1/object/public/"
        f"{settings.STORAGE_BUCKET_NAME}/{subdomain}/index.html?cb=audit"
    )
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url)
        return (resp.text if resp.status_code == 200 else None, resp.status_code)
    except Exception as e:  # noqa: BLE001
        print(f"   ! snapshot fetch failed for {subdomain}: {e}")
        return (None, -1)


async def main() -> int:
    supabase = get_supabase_client()

    # Page through all published sites. Adjust page size if the table is large.
    rows: list[dict] = []
    page, size = 0, 1000
    while True:
        res = (
            supabase.table("websites")
            .select("id, subdomain, status, whatsapp_number, updated_at, html_content")
            .eq("status", "published")
            .range(page * size, page * size + size - 1)
            .execute()
        )
        batch = res.data or []
        rows.extend(batch)
        if len(batch) < size:
            break
        page += 1

    print(f"Scanned {len(rows)} published sites. Deploy cutoff = {DEPLOY_CUTOFF}\n")

    damaged: list[dict] = []
    for r in rows:
        sub = r.get("subdomain")
        if not sub:
            continue
        db_html = r.get("html_content") or ""
        db_ok = is_html_balanced(db_html)[0] if db_html else True

        snap, code = await _storage_snapshot(sub)
        snap_ok = is_html_balanced(snap)[0] if snap else None  # None = missing

        # A site is "damaged" if either persisted copy is structurally broken.
        broken = (db_html and not db_ok) or (snap is not None and not snap_ok)
        if not broken:
            continue

        in_window = (r.get("updated_at") or "") >= DEPLOY_CUTOFF
        damaged.append({**r, "db_ok": db_ok, "snap_ok": snap_ok, "code": code,
                        "in_window": in_window})

    if not damaged:
        print("✅ No published site has an unbalanced DB blob or storage snapshot.")
        return 0

    damaged.sort(key=lambda d: (not d["in_window"], d["subdomain"]))
    print(f"⚠️  {len(damaged)} site(s) with broken stored HTML "
          f"({sum(d['in_window'] for d in damaged)} updated since deploy):\n")
    print(f"{'subdomain':22} {'db':>4} {'storage':>8} {'in_window':>10}  updated_at")
    for d in damaged:
        db = "OK" if d["db_ok"] else "BAD"
        st = ("OK" if d["snap_ok"] else ("MISSING" if d["snap_ok"] is None else "BAD"))
        print(f"{d['subdomain']:22} {db:>4} {st:>8} {str(d['in_window']):>10}  "
              f"{d.get('updated_at')}")

    print("\nSubdomains (in exposure window first):")
    print("  " + ", ".join(d["subdomain"] for d in damaged if d["in_window"]))
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
