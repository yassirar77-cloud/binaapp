"""Serve mysyg.com wish pages straight from the backend.

The wildcard ``*.mysyg.com`` points at this Render service, so this
middleware answers every request on that domain before the BinaApp
subdomain middleware sees it:

    buat.mysyg.com /          -> creator page (make + pay for a wish)
    www.mysyg.com  /          -> creator page (once www has its own DNS)
    buat.mysyg.com /s/<id>    -> sender's status page (?t=<token>)
    <slug>.mysyg.com /        -> the recipient's gift page
                                 (?pratonton=<token>: the sender's preview)
    any host /og.png          -> the link-preview image
    any host /api/...         -> normal API routing (same-origin fetches)

Like the subdomain middleware, any unexpected error falls through to
call_next() rather than breaking the connection.
"""

from __future__ import annotations

import asyncio
import html
import json
import re
from pathlib import Path
from typing import Any, Dict

from fastapi import Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from loguru import logger

from app.services import wishes as W
from app.services import wish_writer as writer
from app.services.wish_direction import MAX_DIRECTION_CHARS

_TEMPLATES = Path(__file__).resolve().parent.parent / "templates" / "wishes"
_CREATOR_SUBS = ("", "www", "buat")
_STATUS_PATH = re.compile(r"^/s/([0-9a-fA-F-]{36})/?$")


def _load(name: str) -> str:
    """A template with the shared stylesheet inlined. One request per page:
    these open from a WhatsApp link on mobile data."""
    text = (_TEMPLATES / name).read_text(encoding="utf-8")
    if "/*__BASE_CSS__*/" in text:
        text = text.replace("/*__BASE_CSS__*/", (_TEMPLATES / "_base.css").read_text(encoding="utf-8"))
    return text


_OG_IMAGE: Dict[str, bytes] = {}


def og_image() -> bytes:
    if "png" not in _OG_IMAGE:
        _OG_IMAGE["png"] = (_TEMPLATES / "og.png").read_bytes()
    return _OG_IMAGE["png"]


_PAGES: Dict[str, str] = {}


def _page(name: str) -> str:
    if name not in _PAGES:
        _PAGES[name] = _load(name)
    return _PAGES[name]


def script_json(data: Any) -> str:
    """JSON safe to drop inside <script type="application/json">."""
    return (
        json.dumps(data, ensure_ascii=False)
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
        .replace(" ", "\\u2028")
        .replace(" ", "\\u2029")
    )


def _html(body: str, status: int = 200) -> HTMLResponse:
    return HTMLResponse(body, status_code=status, headers={"Cache-Control": "no-store"})


def wish_host_parts(host: str):
    """``sub`` for a host on the wish domain ("" for the apex), else None."""
    h = (host or "").strip().lower().split(":", 1)[0].rstrip(".")
    domain = W.wish_domain()
    if h == domain:
        return ""
    suffix = "." + domain
    if h.endswith(suffix):
        sub = h[: -len(suffix)]
        return sub if sub and "." not in sub else None
    return None


def render_creator(promo_left: int = 0) -> str:
    config = {
        # Launch offer: free base-package wishes still to give away.
        "promo": {"left": max(0, int(promo_left)), "total": W.promo_limit(), "package": W.PACKAGE_BASE},
        "domain": W.wish_domain(),
        "max_photos": W.MAX_PHOTOS,
        "occasions": {
            k: {
                "label": W.OCCASIONS[k]["label"], "title": W.OCCASIONS[k]["title"],
                "emoji": W.OCCASIONS[k]["emoji"], "ideas": W.OCCASIONS[k]["ideas"],
            }
            for k in W.OFFERED_OCCASIONS
        },
        "music": {k: v["label"] for k, v in W.MUSIC_STYLES.items()},
        "default_occasion": W.DEFAULT_OCCASION,
        "default_music": W.DEFAULT_MUSIC,
        "max_unlock_days": W.MAX_UNLOCK_AHEAD.days,
        "video_seconds": W.wish_video_seconds(),
        "packages": W.packages_public(),
        "default_package": W.PACKAGE_BASE,
        "scene_ideas": W.SCENE_IDEAS,
        "max_direction": MAX_DIRECTION_CHARS,
        "since_kinds": {k: W.SINCE_KINDS[k]["label"] for k in W.OFFERED_SINCE},
        "question_ideas": W.QUESTION_IDEAS,
        "max_question": W.MAX_QUESTION_CHARS,
        "max_hint": W.MAX_HINT_CHARS,
        "max_answer": W.MAX_ANSWER_CHARS,
        "writer": {
            "relations": {k: v["label"] for k, v in writer.RELATIONS.items()},
            "tones": {k: v["label"] for k, v in writer.TONES.items()},
            "default_relation": writer.DEFAULT_RELATION,
            "default_tone": writer.DEFAULT_TONE,
            "max_notes": writer.MAX_NOTES_CHARS,
        },
    }
    return (
        _page("create.html")
        .replace("__CONFIG_JSON__", script_json(config))
        .replace("__WISH_DOMAIN__", html.escape(W.wish_domain()))
        .replace("__PRICE__", f"{W.wish_price_rm():.2f}")
        .replace("__OG_IMAGE__", html.escape(f"https://{W.creator_host()}/og.png"))
    )


def render_status() -> str:
    return _page("status.html").replace(
        "__CONFIG_JSON__", script_json({"support": W.support_contact()})
    )


def render_wish(row: Dict[str, Any], preview: bool = False) -> str:
    view = W.public_view(row, preview=preview)
    title = f"Ada kejutan untuk {view['recipient_name']} 🎁"
    return (
        _page("wish.html")
        .replace("__OG_TITLE__", html.escape(title))
        .replace("__OG_IMAGE__", html.escape(f"{W.wish_url(row['slug'])}/og.png"))
        .replace("__THEME__", html.escape(view["theme"]))
        .replace("__CREATOR_URL__", html.escape(f"https://{W.creator_host()}/"))
        .replace("__WISH_JSON__", script_json(view))
    )


def render_not_found() -> str:
    return _page("notfound.html").replace(
        "__CREATOR_URL__", html.escape(f"https://{W.creator_host()}/")
    )


async def wish_middleware(request: Request, call_next):
    try:
        sub = wish_host_parts(request.headers.get("host", ""))
        if sub is None:
            return await call_next(request)
        path = request.url.path or "/"
        if path.startswith("/api/") or path in ("/health", "/robots.txt"):
            if path == "/robots.txt":
                return HTMLResponse("User-agent: *\nDisallow: /s/\n", media_type="text/plain")
            return await call_next(request)
        if request.method not in ("GET", "HEAD"):
            return await call_next(request)
        if path == "/og.png":
            return Response(
                og_image(), media_type="image/png",
                headers={"Cache-Control": "public, max-age=86400"},
            )

        if sub in _CREATOR_SUBS:
            if path == "/":
                return _html(render_creator(await W.promo_left_cached()))
            if _STATUS_PATH.match(path):
                return _html(render_status())
            return RedirectResponse("/", status_code=302)

        if path != "/":
            return RedirectResponse("/", status_code=302)
        if W.slug_problem(sub):
            return _html(render_not_found(), 404)
        row = await W.get_by_slug(sub)
        if not row or row.get("status") not in W.LIVE_STATUSES:
            return _html(render_not_found(), 404)
        # Nudge a pending clip forward without making the visitor wait.
        if row.get("status") != "ready":
            asyncio.create_task(W._safe_advance(row))
        # The sender's own look (token in the link) is not a view.
        query = getattr(request, "query_params", None) or {}
        preview = W.token_matches(row, query.get("pratonton"))
        if not preview:
            asyncio.create_task(W.bump_views(row))
        return _html(render_wish(row, preview=preview))
    except Exception as exc:  # noqa: BLE001 — never break the connection
        logger.error(f"💌 wish middleware error: {exc}")
        return await call_next(request)
