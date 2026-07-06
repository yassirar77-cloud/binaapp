"""
One-shot storage re-sync for a single published site.

WHY: The subdomain serve path (app/middleware/subdomain.py) serves the HTML
SNAPSHOT stored in Supabase Storage at `{subdomain}/index.html` — it never
reads websites.html_content live. This site's html_content was updated via
direct SQL (bypassing publish), so the DB is correct but the storage snapshot
is stale (still shows the old WhatsApp placeholder).

WHAT THIS DOES: Reads the current websites.html_content VERBATIM from the DB
and re-uploads it through the SAME storage call PUT /websites/{id}/publish uses
(storage_service.publish_website → upload_website, x-upsert:true). It does NOT
regenerate or modify the HTML. The x-upsert overwrite is what invalidates the
Supabase Smart CDN copy (max-age=3600), so the stale edge object is replaced.

After upload it fetches the live serving object with a cache-busting query
param and asserts the new number is present and the old placeholder is gone.

SCOPE: serve/publish/storage path only. Touches nothing billing-related.

Run from backend/ in an environment with SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY:
    python -m scripts.resync_ultramedic_storage
"""

import asyncio
import sys

import httpx

from app.core.config import settings
from app.core.supabase import get_supabase_client
from app.services.storage_service import storage_service

WEBSITE_ID = "4ce98a8d-d772-4f66-82e5-1e1a7e14075d"
EXPECTED_SUBDOMAIN = "ultramedic"
NEW_NUMBER = "126973105"       # must be present after re-sync
OLD_PLACEHOLDER = "123456789"  # must be absent after re-sync


async def main() -> int:
    # 1. Read the current row straight from the DB (verbatim html_content).
    supabase = get_supabase_client()
    result = (
        supabase.table("websites")
        .select("id, subdomain, user_id, whatsapp_number, html_content, status")
        .eq("id", WEBSITE_ID)
        .limit(1)
        .execute()
    )
    if not result.data:
        print(f"❌ No website row for id {WEBSITE_ID}")
        return 1

    row = result.data[0]
    subdomain = row.get("subdomain")
    user_id = row.get("user_id")
    html_content = row.get("html_content") or ""

    print(f"Row: subdomain={subdomain} user_id={user_id} "
          f"status={row.get('status')} whatsapp_number={row.get('whatsapp_number')} "
          f"html_len={len(html_content)}")

    # Guard rails — refuse to touch the wrong site or push an obviously-wrong DB.
    if subdomain != EXPECTED_SUBDOMAIN:
        print(f"❌ subdomain mismatch: expected {EXPECTED_SUBDOMAIN}, got {subdomain}")
        return 1
    if not html_content:
        print("❌ DB html_content is empty — refusing to overwrite storage")
        return 1
    if NEW_NUMBER not in html_content:
        print(f"❌ DB html_content does NOT contain {NEW_NUMBER} — DB not actually "
              f"updated; aborting so we don't republish stale content")
        return 1
    if OLD_PLACEHOLDER in html_content:
        print(f"⚠️  DB html_content still contains {OLD_PLACEHOLDER} — the direct-SQL "
              f"update may be incomplete. Aborting; fix the DB first.")
        return 1

    # 2. Re-upload verbatim via the exact same call PUT /publish uses.
    #    x-upsert overwrite invalidates the Supabase Smart CDN copy.
    public_url = await storage_service.publish_website(
        subdomain=subdomain,
        html_content=html_content,
        website_id=WEBSITE_ID,
        user_id=user_id,
    )
    print(f"✅ Re-uploaded storage snapshot for {subdomain} → {public_url}")

    # 3. Verify the LIVE serving object. Cache-bust query param bypasses the CDN
    #    so we read the freshly-written object, not a stale edge copy.
    serving_url = (
        f"{settings.SUPABASE_URL}/storage/v1/object/public/"
        f"{settings.STORAGE_BUCKET_NAME}/{subdomain}/index.html?cb=resync"
    )
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(serving_url)

    if resp.status_code != 200:
        print(f"❌ Serving object fetch returned {resp.status_code}")
        return 1

    served = resp.text
    has_new = NEW_NUMBER in served
    has_old = OLD_PLACEHOLDER in served
    print(f"Live storage object: has {NEW_NUMBER}={has_new}  has {OLD_PLACEHOLDER}={has_old}  "
          f"(len={len(served)})")

    if has_new and not has_old:
        print("✅ GREEN — storage snapshot now serves the new WhatsApp number.")
        print("   Note: the app 60s in-process cache and 300s response cache "
              "may still show old for a few minutes; they self-heal.")
        return 0

    print("❌ NOT GREEN — storage object still mismatched. Investigate before retrying.")
    return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
