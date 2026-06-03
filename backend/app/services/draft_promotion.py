"""
Draft promotion — flip a pre-payment website draft to a live published site.

Background
----------
The generator persists finished HTML as a status='pending_payment' websites
row with a placeholder ``draft-<uuid>`` subdomain, tied to the user, so the
work is never lost before payment (see run_generation_task in main.py). The
public site, however, is served by the subdomain middleware from Supabase
Storage under a REAL subdomain, and the free-tier gate refuses to serve until
the owner's plan permits it.

Publishing normally happens via ``/api/publish`` — but the post-payment return
flow never calls it (confirmed in prod: no ``mode=promote-draft`` log after
payment). So a paid user's draft stayed ``pending_payment`` with a ``draft-``
subdomain and the public URL served the upgrade paywall.

This module promotes the draft straight from the ToyyibPay payment callback,
server-side: auto-generate a real subdomain from the business name, inject the
widgets, upload the HTML to storage so the middleware can serve it, and flip
the DB row to ``published``. It reuses the existing publish building blocks
(``fix_website_id_in_html`` / widget injectors / ``storage_service``) rather
than duplicating them.
"""

import re
from datetime import datetime
from typing import Optional

import httpx
from loguru import logger

from app.core.config import settings
from app.services.storage_service import storage_service
from app.services.subscription_service import subscription_service


_SVC_HEADERS = {
    "apikey": settings.SUPABASE_SERVICE_ROLE_KEY,
    "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
    "Content-Type": "application/json",
}
_BASE = settings.SUPABASE_URL

# Subdomain rules mirrored from publish.validate_subdomain: 3..30 chars,
# lowercase alnum + hyphen, no leading/trailing hyphen.
_MAX_SUBDOMAIN = 30


def _slugify(name: str) -> str:
    """Turn a business name into a subdomain-safe slug."""
    slug = (name or "").lower().strip()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = re.sub(r"-{2,}", "-", slug).strip("-")
    slug = slug[:_MAX_SUBDOMAIN].strip("-")
    if len(slug) < 3:
        slug = (f"site-{slug}".strip("-"))[:_MAX_SUBDOMAIN]
    return slug or "site"


async def _subdomain_taken(subdomain: str, exclude_id: str, client: httpx.AsyncClient) -> bool:
    """True if another website row already owns this subdomain."""
    resp = await client.get(
        f"{_BASE}/rest/v1/websites",
        headers=_SVC_HEADERS,
        params={"subdomain": f"eq.{subdomain}", "select": "id", "limit": "1"},
    )
    if resp.status_code != 200:
        # Fail safe: treat lookup failure as "taken" so we fall through to a
        # suffixed candidate rather than risk a unique-constraint collision.
        return True
    rows = resp.json()
    return bool(rows) and rows[0].get("id") != exclude_id


async def _unique_subdomain(base: str, exclude_id: str, client: httpx.AsyncClient) -> str:
    """Find a free subdomain starting from ``base`` (base, base-2, base-3 …)."""
    candidate = base
    i = 2
    while await _subdomain_taken(candidate, exclude_id, client):
        suffix = f"-{i}"
        candidate = f"{base[:_MAX_SUBDOMAIN - len(suffix)]}{suffix}"
        i += 1
        if i > 50:
            # Last resort: graft on part of the row id (guaranteed unique).
            candidate = f"{base[:_MAX_SUBDOMAIN - 7]}-{exclude_id[:6]}"
            break
    return candidate


async def promote_latest_draft_for_user(user_id: str) -> Optional[dict]:
    """Promote the user's most-recent pending_payment draft to published.

    Returns ``{"id", "subdomain", "public_url"}`` on success, else ``None``
    (no draft to promote, or a failure — failures are logged, never raised, so
    they cannot abort the payment flow).
    """
    if not user_id:
        return None

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            # Newest pending_payment draft for this user.
            resp = await client.get(
                f"{_BASE}/rest/v1/websites",
                headers=_SVC_HEADERS,
                params={
                    "user_id": f"eq.{user_id}",
                    "status": "eq.pending_payment",
                    "select": "id,business_name,name,subdomain,html_content,description",
                    "order": "created_at.desc",
                    "limit": "1",
                },
            )
            if resp.status_code != 200 or not resp.json():
                logger.info(
                    f"🪪 No pending_payment draft to promote for user {user_id}"
                )
                return None

            draft = resp.json()[0]
            draft_id = draft["id"]
            html = draft.get("html_content") or ""
            biz = draft.get("business_name") or draft.get("name") or "site"

            if not html:
                logger.warning(
                    f"🪪 Draft {draft_id} for user {user_id} has empty html_content — "
                    f"skipping promotion"
                )
                return None

            subdomain = await _unique_subdomain(_slugify(biz), draft_id, client)

            # Reuse the publish building blocks (no main.py import → no cycle).
            from app.api.simple.publish import (
                fix_website_id_in_html,
                inject_delivery_widget_if_needed,
                inject_chat_widget_if_needed,
            )

            html = fix_website_id_in_html(html, draft_id)
            html = inject_delivery_widget_if_needed(
                html,
                draft_id,
                biz,
                description=draft.get("description") or biz,
                language="ms",
            )
            html = inject_chat_widget_if_needed(
                html, draft_id, api_url="https://binaapp-backend.onrender.com"
            )

            # Upload to storage so the subdomain middleware can serve the site.
            public_url = await storage_service.upload_website(
                user_id=user_id, subdomain=subdomain, html_content=html
            )

            # Flip the DB row → published.
            logger.info(
                f"🪪 Promoting pre-payment draft {draft_id} → published for "
                f"user {user_id} (subdomain={subdomain})"
            )
            patch = await client.patch(
                f"{_BASE}/rest/v1/websites",
                headers={**_SVC_HEADERS, "Prefer": "return=minimal"},
                params={"id": f"eq.{draft_id}"},
                json={
                    "status": "published",
                    "subdomain": subdomain,
                    "public_url": public_url,
                    "html_content": html,
                    "published_at": datetime.utcnow().isoformat(),
                    "updated_at": datetime.utcnow().isoformat(),
                },
            )
            if patch.status_code not in (200, 204):
                logger.error(
                    f"❌ [WEBSITES INSERT] FAILED promote draft {draft_id} "
                    f"user_id={user_id}: {patch.status_code} {patch.text[:200]}"
                )
                return None

            logger.info(
                f"✅ [WEBSITES INSERT] id={draft_id} user_id={user_id} "
                f"status=published mode=promote-draft subdomain={subdomain} "
                f"html_chars={len(html)}"
            )

        # Now that it's live, count it against quota. Best-effort: usage
        # self-heals from actual published-row counts regardless.
        try:
            await subscription_service.increment_usage(user_id, "create_website")
            logger.info(f"📊 Incremented websites_count for user {user_id}")
        except Exception as inc_err:
            logger.warning(
                f"⚠️ usage increment after promote failed for {user_id}: {inc_err}"
            )

        return {"id": draft_id, "subdomain": subdomain, "public_url": public_url}

    except Exception as e:
        logger.error(
            f"❌ promote_latest_draft_for_user failed for {user_id}: {e}",
            exc_info=True,
        )
        return None
