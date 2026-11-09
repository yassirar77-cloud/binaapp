"""Serve mysyg.com wish pages straight from the backend.

The wildcard ``*.mysyg.com`` points at this Render service, so this
middleware answers every request on that domain before the BinaApp
subdomain middleware sees it:

    buat.mysyg.com /          -> creator page (make + pay for a wish)
    www.mysyg.com  /          -> creator page (once www has its own DNS)
    buat.mysyg.com /s/<id>    -> sender's status page (?t=<token>)
    <slug>.mysyg.com /        -> the recipient's gift page
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
from fastapi.responses import HTMLResponse, RedirectResponse
from loguru import logger

from app.services import wishes as W

_TEMPLATES = Path(__file__).resolve().parent.parent / "templates" / "wishes"
_CREATOR_SUBS = ("", "www", "buat")
_STATUS_PATH = re.compile(r"^/s/([0-9a-fA-F-]{36})/?$")


def _load(name: str) -> str:
    return (_TEMPLATES / name).read_text(encoding="utf-8")


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


def render_creator() -> str:
    config = {
        "domain": W.wish_domain(),
        "max_photos": W.MAX_PHOTOS,
        "occasions": {k: v["label"] for k, v in W.OCCASIONS.items()},
        "music": {k: v["label"] for k, v in W.MUSIC_STYLES.items()},
        "default_occasion": W.DEFAULT_OCCASION,
        "default_music": W.DEFAULT_MUSIC,
    }
    return (
        _page("create.html")
        .replace("__CONFIG_JSON__", script_json(config))
        .replace("__WISH_DOMAIN__", html.escape(W.wish_domain()))
        .replace("__PRICE__", f"{W.wish_price_rm():.2f}")
    )


def render_status() -> str:
    return _page("status.html").replace(
        "__CONFIG_JSON__", script_json({"support": W.support_contact()})
    )


def render_wish(row: Dict[str, Any]) -> str:
    view = W.public_view(row)
    title = f"Ada kejutan untuk {view['recipient_name']} 🎁"
    return (
        _page("wish.html")
        .replace("__OG_TITLE__", html.escape(title))
        .replace("__CREATOR_URL__", html.escape(f"https://{W.creator_host()}/"))
        .replace("__WISH_JSON__", script_json(view))
    )


def render_not_found() -> str:
    creator = html.escape(f"https://{W.creator_host()}/")
    return f"""<!doctype html><html lang="ms"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><meta name="robots" content="noindex">
<title>Kejutan tidak dijumpai — mysyg</title>
<style>body{{margin:0;min-height:100vh;display:grid;place-items:center;background:#2A1030;color:#FFF8F3;
font-family:system-ui,sans-serif;text-align:center;padding:24px}}a{{color:#E3B65C}}h1{{font-weight:600;font-size:24px}}</style>
</head><body><main><h1>Kejutan ini tidak dijumpai</h1>
<p>Semak semula pautan yang anda terima.</p><p><a href="{creator}">Buat kejutan anda sendiri</a></p></main></body></html>"""


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

        if sub in _CREATOR_SUBS:
            if path == "/":
                return _html(render_creator())
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
        asyncio.create_task(W.bump_views(row))
        return _html(render_wish(row))
    except Exception as exc:  # noqa: BLE001 — never break the connection
        logger.error(f"💌 wish middleware error: {exc}")
        return await call_next(request)
