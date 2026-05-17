"""Admin endpoint to repair structurally-broken stored HTML.

Background: a previous version of the website generator emitted HTML with
two defects that survived into stored `websites.html_content`:
  1. Duplicate Tailwind CDN <script> and Font Awesome <link> tags (one
     from the AI-generated homepage <head>, another re-injected by the
     delivery-system pass — fixed forward in templates.py:1013).
  2. Unclosed mid-body tags (e.g. testimonials <section> opened but never
     closed) that the splice in inject_ordering_system inherited, causing
     mobile horizontal overflow on jiwa/huil/juio — fixed forward in
     ai_service._extract_html (Items 2-3).

This endpoint repairs the already-published static HTML those defects
left behind. Generator fixes only help future generations; this is the
backfill.

DESIGN GUARANTEES (see scope confirmation before implementation):
  - WILL ONLY: remove duplicate library includes (keep the first of each),
    and insert missing closing tags computed from a forward tag-balance
    scan. Nothing else.
  - WILL NOT: regenerate, call AI, re-run inject_ordering_system, touch
    visible text, images, prices, styles, layout, or any field other
    than html_content + updated_at.
  - Integrity check after repair: result must be balanced AND the
    tag-stripped visible text must be byte-identical to the pre-repair
    text. If either fails, skip the write for that site.
  - Backup-before-overwrite: pre-repair HTML is saved to
    {subdomain}/index.pre-repair-{timestamp}.html for one-call rollback.
  - Idempotent: a second run produces no further change.
  - Admin-only: requires role='admin' in public.users. Bulk operations
    are not authorized via plain authentication.

Endpoint: POST /api/v1/admin/repair-websites
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, status
from loguru import logger

from app.core.config import settings
from app.core.security import get_current_user
from app.services.subscription_service import subscription_service
from app.services.supabase_client import supabase_service
from app.utils.html_balance import (
    find_unclosed_tags,
    is_html_balanced,
    strip_trailing_wrapper_closers,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# Pure repair logic — kept free of FastAPI / I/O so it's unit-testable and
# the endpoint can call it inside its dry-run loop without side effects.
# ---------------------------------------------------------------------------

# Matches a <script ...> tag whose src is the Tailwind CDN, plus an optional
# </script> close that immediately follows (with optional whitespace between).
# Case-insensitive. Single OR double quotes accepted.
_TAILWIND_SCRIPT_RE = re.compile(
    r"<script\b[^>]*?\bsrc\s*=\s*['\"][^'\"]*cdn\.tailwindcss\.com[^'\"]*['\"][^>]*>"
    r"(\s*</script>)?",
    re.IGNORECASE,
)

# Matches a <link ...> tag whose href is the Font Awesome 6.4.0 CSS on
# cdnjs. The version is pinned because templates.py injects exactly 6.4.0
# (line 1018) — older AI generations also pin 6.4.0; we don't want to
# accidentally remove an unrelated FA version a user might have added.
_FONTAWESOME_LINK_RE = re.compile(
    r"<link\b[^>]*?\bhref\s*=\s*['\"][^'\"]*cdnjs\.cloudflare\.com/ajax/libs/"
    r"font-awesome/6\.4\.0/css/all\.min\.css[^'\"]*['\"][^>]*?/?>",
    re.IGNORECASE,
)

_STRIP_TAGS_RE = re.compile(r"<[^>]+>")
_WHITESPACE_RUN_RE = re.compile(r"\s+")


def _remove_duplicates(html: str, pattern: re.Pattern) -> Tuple[str, int]:
    """Keep the first regex match, remove all subsequent ones.

    Returns (new_html, number_of_tags_removed).
    """
    matches = list(pattern.finditer(html))
    if len(matches) <= 1:
        return html, 0
    # Walk back-to-front so earlier indices stay valid after deletion.
    new_html = html
    removed = 0
    for m in reversed(matches[1:]):
        new_html = new_html[: m.start()] + new_html[m.end():]
        removed += 1
    return new_html, removed


def _splice_missing_closers(html: str) -> Tuple[str, List[str]]:
    """Insert missing closing tags. Mirrors ai_service._extract_html's
    Item 3 logic exactly so the in-flight pipeline and the backfill agree.

    Returns (new_html, list_of_closing_tags_inserted_innermost_first).
    """
    if not html:
        return html, []
    ends_with_html = html.rstrip().endswith("</html>")
    if ends_with_html:
        # Case 2: silent mid-body imbalance.
        body_raw = find_unclosed_tags(strip_trailing_wrapper_closers(html))
        unclosed_body = [t for t in body_raw if t not in ("html", "body")]
        if not unclosed_body:
            return html, []
        inner_closers = "".join(f"</{t}>" for t in reversed(unclosed_body))
        body_match = re.search(r"</\s*body\s*>", html, flags=re.IGNORECASE)
        html_match = re.search(r"</\s*html\s*>", html, flags=re.IGNORECASE)
        if body_match:
            at = body_match.start()
            return html[:at] + inner_closers + "\n" + html[at:], list(reversed(unclosed_body))
        if html_match:
            at = html_match.start()
            return html[:at] + inner_closers + "\n" + html[at:], list(reversed(unclosed_body))
        return html, []
    # Case 1: classic truncation — append innermost-first then wrapper.
    unclosed = find_unclosed_tags(html)
    inner_closers = "".join(
        f"</{t}>" for t in reversed(unclosed) if t not in ("html", "body")
    )
    if "</body>" not in html:
        return html + "\n" + inner_closers + "\n</body>\n</html>", [
            f"</{t}>" for t in reversed(unclosed) if t not in ("html", "body")
        ] + ["</body>", "</html>"]
    return html + "\n" + inner_closers + "\n</html>", [
        f"</{t}>" for t in reversed(unclosed) if t not in ("html", "body")
    ] + ["</html>"]


def _visible_text(html: str) -> str:
    """Strip all tags and normalize whitespace runs. Used as the integrity
    check after repair: the visible text of the page must NOT change.
    Insertion of </section>/</div> closers and removal of script/link tags
    is invisible by definition, so this should be byte-identical."""
    no_tags = _STRIP_TAGS_RE.sub("", html or "")
    return _WHITESPACE_RUN_RE.sub(" ", no_tags).strip()


def repair_html(html: str) -> Tuple[str, Dict[str, Any]]:
    """Pure repair pass. Returns (repaired_html, report).

    Report fields:
      duplicate_tailwind_removed: int
      duplicate_fontawesome_removed: int
      tags_inserted: List[str]  (innermost-first, the closers spliced in)
      balanced_before: bool
      balanced_after: bool
      text_content_preserved: bool
      html_changed: bool
      safe_to_write: bool  (true iff balanced_after AND text_content_preserved)
    """
    report: Dict[str, Any] = {
        "duplicate_tailwind_removed": 0,
        "duplicate_fontawesome_removed": 0,
        "tags_inserted": [],
        "balanced_before": True,
        "balanced_after": True,
        "text_content_preserved": True,
        "html_changed": False,
        "safe_to_write": True,
    }
    if not html:
        return html, report

    report["balanced_before"] = is_html_balanced(html)[0]
    before_text = _visible_text(html)

    work = html
    work, n_tw = _remove_duplicates(work, _TAILWIND_SCRIPT_RE)
    report["duplicate_tailwind_removed"] = n_tw
    work, n_fa = _remove_duplicates(work, _FONTAWESOME_LINK_RE)
    report["duplicate_fontawesome_removed"] = n_fa

    work, inserted = _splice_missing_closers(work)
    report["tags_inserted"] = inserted

    balanced_after, _ = is_html_balanced(work)
    report["balanced_after"] = balanced_after

    after_text = _visible_text(work)
    text_ok = (after_text == before_text)
    report["text_content_preserved"] = text_ok

    report["html_changed"] = (work != html)
    report["safe_to_write"] = balanced_after and text_ok

    return work, report


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

@router.post("/admin/repair-websites")
async def repair_websites(
    subdomain: Optional[str] = Query(
        None,
        description="Repair the single website with this subdomain.",
    ),
    website_id: Optional[str] = Query(
        None,
        description="Repair the single website with this id (UUID).",
    ),
    all_sites: bool = Query(
        False,
        alias="all",
        description=(
            "Repair every status=published website. Defaults to dry_run=true "
            "unless dry_run is explicitly set to false (bulk must opt in to "
            "writing). Aliased as `all` in the URL — `all_sites` internally "
            "to avoid shadowing the Python builtin."
        ),
    ),
    dry_run: Optional[bool] = Query(
        None,
        description=(
            "Tri-state. Omit (None) to use the default for the chosen mode: "
            "single-site mode defaults to FALSE (writes), all=true mode "
            "defaults to TRUE (dry-run). Set explicitly to override."
        ),
    ),
    current_user: dict = Depends(get_current_user),
):
    """Repair stored HTML for one or more published websites.

    Exactly one of `subdomain`, `website_id`, or `all=true` is required.
    Auth: requires role='admin' in public.users.
    """
    user_id = current_user.get("sub") or current_user.get("id")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")

    is_admin = await subscription_service._is_admin(user_id)
    if not is_admin:
        # No fallback to "own sites only" — this endpoint touches the
        # storage bucket and customer HTML, and the safer behavior is to
        # refuse entirely if the caller isn't admin. Customers who want
        # to re-fix their own site can use the normal Publish flow once
        # their HTML is regenerated.
        logger.warning(f"🛑 repair-websites called by non-admin user_id={user_id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required for this operation.",
        )

    # Normalize string params: strip whitespace, lowercase subdomain, empty → None.
    if subdomain is not None:
        subdomain = subdomain.strip().lower() or None
    if website_id is not None:
        website_id = website_id.strip() or None

    selectors = [bool(subdomain), bool(website_id), all_sites]
    if sum(selectors) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Specify exactly one of: subdomain, website_id, all=true.",
        )
    if sum(selectors) > 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Specify only one of: subdomain, website_id, all=true.",
        )

    # Bulk dry-run-by-default: ?all=true writes only when dry_run is
    # *explicitly* false. Single-site defaults to write (dry_run=false)
    # so the trial-on-jiwa workflow doesn't need an extra param.
    if all_sites:
        dry_run_effective = True if dry_run is None else dry_run
    else:
        dry_run_effective = False if dry_run is None else dry_run
    # Below this point the original variable name is preserved.
    dry_run = dry_run_effective
    all_flag = all_sites

    # Fetch target rows via the same REST pattern the existing admin
    # republish uses (see api/simple/publish.py:767). supabase_service.url
    # + supabase_service.headers carry the service-role auth.
    sites: List[Dict[str, Any]] = []
    rest_url = f"{supabase_service.url}/rest/v1/websites"
    select_cols = "id,user_id,subdomain,status,html_content"
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            if subdomain:
                params = {
                    "subdomain": f"eq.{subdomain}",
                    "select": select_cols,
                    "limit": "1",
                }
            elif website_id:
                params = {
                    "id": f"eq.{website_id}",
                    "select": select_cols,
                    "limit": "1",
                }
            else:
                params = {
                    "status": "eq.published",
                    "select": select_cols,
                }
            resp = await client.get(rest_url, headers=supabase_service.headers, params=params)
            if resp.status_code != 200:
                logger.error(f"❌ repair-websites: site lookup failed: {resp.status_code} {resp.text[:200]}")
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail="Failed to fetch target websites from Supabase.",
                )
            sites = resp.json() or []
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("❌ repair-websites: site lookup threw")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to fetch target websites: {e}",
        )

    logger.info(
        f"🔧 repair-websites: admin={user_id} mode="
        f"{'all' if all_flag else ('subdomain=' + subdomain if subdomain else 'website_id=' + website_id)} "
        f"dry_run={dry_run} candidates={len(sites)}"
    )

    summary = {
        "dry_run": dry_run,
        "total": len(sites),
        "repaired": 0,
        "skipped_unchanged": 0,
        "skipped_not_published": 0,
        "skipped_unsafe": 0,
        "errors": 0,
        "per_site": [],
    }

    bucket = settings.STORAGE_BUCKET_NAME
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    for site in sites:
        sub = site.get("subdomain") or "?"
        wid = site.get("id") or "?"
        site_user_id = site.get("user_id")
        site_status = site.get("status")
        html = site.get("html_content") or ""

        site_report: Dict[str, Any] = {
            "subdomain": sub,
            "website_id": wid,
            "status": site_status,
            "dry_run": dry_run,
            "error": None,
            "uploaded_to_storage": False,
            "db_updated": False,
            "backup_path": None,
        }

        if site_status != "published":
            site_report["error"] = "not_published"
            summary["skipped_not_published"] += 1
            summary["per_site"].append(site_report)
            continue

        if not html:
            site_report["error"] = "empty_html_content"
            summary["errors"] += 1
            summary["per_site"].append(site_report)
            continue

        try:
            new_html, report = repair_html(html)
        except Exception as e:
            logger.exception(f"❌ repair-websites: repair_html threw for {sub}")
            site_report["error"] = f"repair_html_exception: {e}"
            summary["errors"] += 1
            summary["per_site"].append(site_report)
            continue

        site_report.update(report)

        if not report["html_changed"]:
            summary["skipped_unchanged"] += 1
            summary["per_site"].append(site_report)
            continue

        if not report["safe_to_write"]:
            # Either still unbalanced after repair, or visible text changed.
            # Both indicate the repair would do harm — refuse the write.
            logger.error(
                f"🛑 repair-websites: UNSAFE result for {sub} — "
                f"balanced_after={report['balanced_after']} "
                f"text_content_preserved={report['text_content_preserved']}. "
                f"Skipping write."
            )
            site_report["error"] = "unsafe_repair_result"
            summary["skipped_unsafe"] += 1
            summary["per_site"].append(site_report)
            continue

        if dry_run:
            # Report would-change but do not write or back up.
            summary["repaired"] += 1
            summary["per_site"].append(site_report)
            continue

        # WRITE PATH — backup first, then write.
        try:
            backup_path = f"{sub}/index.pre-repair-{ts}.html"
            await supabase_service.upload_file(
                bucket=bucket,
                path=backup_path,
                file_data=html.encode("utf-8"),
                content_type="text/html; charset=utf-8",
            )
            site_report["backup_path"] = backup_path
            logger.info(f"   💾 backup written: {backup_path}")
        except Exception as e:
            # Refuse to overwrite if backup failed — we lose the undo button.
            logger.exception(f"❌ repair-websites: backup failed for {sub}, skipping write")
            site_report["error"] = f"backup_failed: {e}"
            summary["errors"] += 1
            summary["per_site"].append(site_report)
            continue

        # Storage write (subdomain path; the user-id-keyed mirror path used
        # by the API preview is not republished here on purpose — we don't
        # have the user_id reliably for storage_service.upload_website's
        # second path, and the subdomain path is what the live site serves).
        try:
            primary_path = f"{sub}/index.html"
            await supabase_service.upload_file(
                bucket=bucket,
                path=primary_path,
                file_data=new_html.encode("utf-8"),
                content_type="text/html; charset=utf-8",
            )
            site_report["uploaded_to_storage"] = True
            # Mirror to {user_id}/{subdomain}/index.html when we have it,
            # so the /api/preview path stays in sync with subdomain.
            if site_user_id:
                mirror_path = f"{site_user_id}/{sub}/index.html"
                try:
                    await supabase_service.upload_file(
                        bucket=bucket,
                        path=mirror_path,
                        file_data=new_html.encode("utf-8"),
                        content_type="text/html; charset=utf-8",
                    )
                except Exception as e:
                    # Non-fatal: subdomain path already updated. Log only.
                    logger.warning(f"⚠️ repair-websites: mirror upload failed for {sub}: {e}")
        except Exception as e:
            logger.exception(f"❌ repair-websites: storage write failed for {sub}")
            site_report["error"] = f"storage_write_failed: {e}"
            summary["errors"] += 1
            summary["per_site"].append(site_report)
            continue

        # DB update — html_content + updated_at only. Nothing else.
        try:
            ok = await supabase_service.update_website(
                wid,
                {
                    "html_content": new_html,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                },
            )
            site_report["db_updated"] = bool(ok)
            if not ok:
                site_report["error"] = "db_update_returned_false"
                summary["errors"] += 1
                summary["per_site"].append(site_report)
                continue
        except Exception as e:
            logger.exception(f"❌ repair-websites: DB update failed for {sub}")
            site_report["error"] = f"db_update_failed: {e}"
            summary["errors"] += 1
            summary["per_site"].append(site_report)
            continue

        summary["repaired"] += 1
        logger.info(
            f"   ✅ repaired {sub}: "
            f"tw={report['duplicate_tailwind_removed']} "
            f"fa={report['duplicate_fontawesome_removed']} "
            f"tags_inserted={report['tags_inserted']}"
        )
        summary["per_site"].append(site_report)

    logger.info(
        f"📊 repair-websites summary: total={summary['total']} "
        f"repaired={summary['repaired']} unchanged={summary['skipped_unchanged']} "
        f"unsafe={summary['skipped_unsafe']} not_published={summary['skipped_not_published']} "
        f"errors={summary['errors']} dry_run={dry_run}"
    )
    return summary
