"""mysyg.com surprise wishes — https://<slug>.mysyg.com.

A sender (no BinaApp account) uploads photos, writes a message, picks an
occasion and a music style, and pays per wish through ToyyibPay. After
payment, Wan 3.0 (DashScope, via ``zai_video_service``) animates the main
photo into a short portrait clip with a generated instrumental soundtrack.
The recipient opens the link, taps a gift box, and the video, message and
photos are revealed.

State machine (table ``wishes``, migration 062)::

    awaiting_payment -> paid -> generating -> storing -> ready
                                          \\-> video_failed

Nothing runs in the background. A wish moves forward when someone looks at
it: the sender's status page polls ``advance()``, the recipient's page calls
it once, and the ToyyibPay callback calls it after marking the bill paid.
Every transition is a conditional PATCH (``status=eq.<from>``) so two
pollers racing on one wish never submit or store a clip twice, and a Render
restart mid-render loses nothing — the task id is in the row.

Only fixed, server-written text ever reaches the video prompt. The sender's
message and names are shown on the page, never sent to the model.
"""

from __future__ import annotations

import asyncio
import hashlib
import os
import re
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from loguru import logger

from app.services.supabase_client import supabase_service

TABLE = "wishes"

# ---------------------------------------------------------------------------
# Configuration (env, read at call time so a Render env change needs no deploy)
# ---------------------------------------------------------------------------


def wish_domain() -> str:
    return (os.getenv("WISH_DOMAIN") or "mysyg.com").strip().lower().strip(".")


def creator_host() -> str:
    """Where the sender makes a wish. ``buat`` works with the wildcard DNS
    record alone; ``www`` works once its own CNAME points at Render."""
    return f"buat.{wish_domain()}"


def wish_price_rm() -> float:
    try:
        value = float(os.getenv("WISH_PRICE_RM", "9.90"))
    except ValueError:
        value = 9.90
    return round(value, 2) if value > 0 else 9.90


def wish_video_seconds() -> int:
    try:
        value = int(os.getenv("WISH_VIDEO_SECONDS", "10"))
    except ValueError:
        value = 10
    return min(max(value, 5), 15)


def wish_video_resolution() -> str:
    value = (os.getenv("WISH_VIDEO_RESOLUTION") or "720P").strip().upper()
    return value if value in ("480P", "720P", "1080P") else "720P"


def free_emails() -> List[str]:
    """Emails that skip payment (owner testing / demos)."""
    raw = os.getenv("WISH_FREE_EMAILS", "")
    return [e.strip().lower() for e in raw.split(",") if e.strip()]


MAX_PHOTOS = 5
MAX_PHOTO_BYTES = 8 * 1024 * 1024
MAX_MESSAGE_CHARS = 600
MAX_NAME_CHARS = 40
#: A clip that failed (or never came back) is tried this many times in total.
MAX_VIDEO_ATTEMPTS = 2
#: A render running longer than this is treated as lost and retried.
VIDEO_HARD_TIMEOUT = timedelta(minutes=20)
#: How often a poller may ask the provider / ToyyibPay about one wish.
POLL_INTERVAL = timedelta(seconds=8)
PAYMENT_CHECK_INTERVAL = timedelta(seconds=15)
#: An unpaid wish older than this no longer holds its link name.
UNPAID_SLUG_HOLD = timedelta(hours=2)

LIVE_STATUSES = ("paid", "generating", "storing", "ready", "video_failed")

RESERVED_SLUGS = frozenset({
    "www", "buat", "api", "app", "admin", "mail", "ftp", "staging", "dev",
    "binaapp", "mysyg", "help", "bantuan", "status", "support", "test",
    "billing", "bayar", "payment", "static", "assets", "cdn",
})

SLUG_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]{1,28}[a-z0-9])$")

# ---------------------------------------------------------------------------
# Occasions and music — the only text that reaches the video model
# ---------------------------------------------------------------------------

OCCASIONS: Dict[str, Dict[str, str]] = {
    "birthday": {
        "label": "Hari Jadi",
        "title": "Selamat Hari Jadi",
        "emoji": "🎂",
        "scene": "colorful confetti and a few soft balloons drift gently through the air, warm festive golden light",
    },
    "anniversary": {
        "label": "Ulang Tahun Perkahwinan",
        "title": "Selamat Ulang Tahun Perkahwinan",
        "emoji": "💍",
        "scene": "soft rose petals float down slowly, warm romantic candlelight glow, gentle sparkles",
    },
    "love": {
        "label": "Saja Nak Cakap Sayang",
        "title": "Untuk Sayangku",
        "emoji": "💖",
        "scene": "soft glowing heart-shaped bokeh lights float around, warm dreamy pink and golden light",
    },
    "raya": {
        "label": "Hari Raya",
        "title": "Selamat Hari Raya",
        "emoji": "🌙",
        "scene": "warm glowing pelita oil lamps and soft festive lights twinkle in the background, gentle evening glow",
    },
    "sorry": {
        "label": "Minta Maaf",
        "title": "Maafkan Saya",
        "emoji": "🌷",
        "scene": "soft morning sunlight, a few flower petals drift gently, calm and tender atmosphere",
    },
    "thanks": {
        "label": "Terima Kasih",
        "title": "Terima Kasih, Sayang",
        "emoji": "🌻",
        "scene": "warm golden sunlight, soft floating sparkles, peaceful and grateful atmosphere",
    },
    "congrats": {
        "label": "Tahniah",
        "title": "Tahniah!",
        "emoji": "🎉",
        "scene": "golden confetti falls gently, bright celebratory light, joyful sparkles",
    },
}

MUSIC_STYLES: Dict[str, Dict[str, str]] = {
    "romantic_piano": {
        "label": "Piano romantik",
        "prompt": "soft romantic instrumental piano music",
    },
    "cheerful": {
        "label": "Ceria & gembira",
        "prompt": "light cheerful upbeat instrumental music with ukulele and soft bells",
    },
    "acoustic": {
        "label": "Gitar akustik",
        "prompt": "warm gentle acoustic guitar instrumental music",
    },
    "orchestral": {
        "label": "Orkestra lembut",
        "prompt": "emotional soft orchestral strings instrumental music",
    },
    "none": {"label": "Tanpa muzik", "prompt": ""},
}

DEFAULT_OCCASION = "birthday"
DEFAULT_MUSIC = "romantic_piano"


def occasion_info(key: Optional[str]) -> Dict[str, str]:
    return OCCASIONS.get(key or "", OCCASIONS[DEFAULT_OCCASION])


def build_video_prompt(occasion: str, music_style: str) -> str:
    """Fixed, server-side prompt for image-to-video. The photo is the first
    frame; the prompt only asks for gentle, faithful motion around it."""
    occ = occasion_info(occasion)
    parts = [
        "The people in this photo gently come to life with natural, subtle movement: "
        "soft warm smiles, natural blinking, slight head movement, hair moving softly in a light breeze.",
        f"Around them, {occ['scene']}.",
        "The camera slowly and smoothly pushes in.",
        "Keep every face, body and outfit exactly as in the original photo, realistic and natural, "
        "no distortion, no extra people.",
        "No text, no captions, no logos, no watermarks.",
    ]
    music = MUSIC_STYLES.get(music_style or "", MUSIC_STYLES[DEFAULT_MUSIC])
    if music["prompt"]:
        parts.append(f"Soundtrack: {music['prompt']}, no singing, no voices, no speech.")
    return " ".join(parts)


def keep_audio_url(url: Optional[str]) -> Optional[str]:
    """Drop Cloudinary's ``ac_none`` (strip audio) from a delivery URL.

    ``zai_video_service.store`` returns the hero-video delivery URL, which
    removes the soundtrack because hero clips play muted behind a page. A
    wish clip's soundtrack is the point, so its URL must keep the audio.
    The stored asset itself always has the audio; only the URL differs.
    """
    if not url:
        return url
    return re.sub(r"(?<=[/,])ac_none(?:,|(?=/))", "", url).replace(",/", "/")


def wants_audio(music_style: str) -> bool:
    return bool(MUSIC_STYLES.get(music_style or "", MUSIC_STYLES[DEFAULT_MUSIC])["prompt"])


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------


def slugify(text: str) -> str:
    """A link-name suggestion from a name: 'Nur Aisyah!' -> 'nur-aisyah'."""
    s = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return s[:30].strip("-")


def slug_problem(slug: str) -> Optional[str]:
    """Why ``slug`` can't be a link name, in Malay, or None if it can."""
    if not slug:
        return "Sila isi nama pautan."
    if slug in RESERVED_SLUGS:
        return "Nama pautan ini dikhaskan. Cuba nama lain."
    if not SLUG_RE.match(slug):
        return "Guna 3–30 huruf kecil, nombor atau tanda sempang (-), tanpa sempang di hujung."
    if "--" in slug:
        return "Jangan guna dua sempang berturut-turut."
    return None


EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def clean_phone(phone: str) -> Optional[str]:
    digits = re.sub(r"\D", "", phone or "")
    if digits.startswith("60"):
        digits = "0" + digits[2:]
    return digits if 9 <= len(digits) <= 12 and digits.startswith("0") else None


def clean_text(value: str, limit: int) -> str:
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", value or "").strip()
    return text[:limit]


def new_token() -> str:
    return secrets.token_urlsafe(24)


def hash_token(token: str) -> str:
    return hashlib.sha256((token or "").encode("utf-8")).hexdigest()


def token_matches(row: Dict[str, Any], token: Optional[str]) -> bool:
    expected = row.get("edit_token_hash") or ""
    return bool(token) and bool(expected) and secrets.compare_digest(hash_token(token), expected)


def wish_url(slug: str) -> str:
    return f"https://{slug}.{wish_domain()}"


def status_url(wish_id: str, token: str) -> str:
    return f"https://{creator_host()}/s/{wish_id}?t={token}"


# ---------------------------------------------------------------------------
# Time helpers
# ---------------------------------------------------------------------------


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _parse_ts(value: Any) -> Optional[datetime]:
    if not value:
        return None
    try:
        text = str(value)
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        parsed = datetime.fromisoformat(text)
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _older_than(value: Any, delta: timedelta, now: Optional[datetime] = None) -> bool:
    ts = _parse_ts(value)
    return ts is None or (now or _utcnow()) - ts >= delta


# ---------------------------------------------------------------------------
# Database (service role, PostgREST)
# ---------------------------------------------------------------------------


def _url() -> str:
    return f"{supabase_service.url}/rest/v1/{TABLE}"


async def get_by_id(wish_id: str) -> Optional[Dict[str, Any]]:
    try:
        async with supabase_service._client() as client:
            resp = await client.get(
                _url(), headers=supabase_service.headers,
                params={"id": f"eq.{wish_id}", "limit": "1"},
            )
        if resp.status_code == 200 and resp.json():
            return resp.json()[0]
    except Exception as exc:  # noqa: BLE001
        logger.error(f"💌 wish lookup {wish_id} failed: {exc}")
    return None


async def get_by_slug(slug: str) -> Optional[Dict[str, Any]]:
    try:
        async with supabase_service._client() as client:
            resp = await client.get(
                _url(), headers=supabase_service.headers,
                params={"slug": f"eq.{slug}", "limit": "1"},
            )
        if resp.status_code == 200 and resp.json():
            return resp.json()[0]
    except Exception as exc:  # noqa: BLE001
        logger.error(f"💌 wish lookup by slug {slug} failed: {exc}")
    return None


async def get_by_bill(bill_code: str) -> Optional[Dict[str, Any]]:
    try:
        async with supabase_service._client() as client:
            resp = await client.get(
                _url(), headers=supabase_service.headers,
                params={"bill_code": f"eq.{bill_code}", "limit": "1"},
            )
        if resp.status_code == 200 and resp.json():
            return resp.json()[0]
    except Exception as exc:  # noqa: BLE001
        logger.error(f"💌 wish lookup by bill {bill_code} failed: {exc}")
    return None


async def insert(row: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Insert a wish. Returns the stored row, or None (slug taken / error)."""
    headers = {**supabase_service.headers, "Prefer": "return=representation"}
    try:
        async with supabase_service._client() as client:
            resp = await client.post(_url(), headers=headers, json=row)
        if resp.status_code in (200, 201) and resp.json():
            return resp.json()[0]
        logger.warning(f"💌 wish insert failed: {resp.status_code} {resp.text[:300]}")
    except Exception as exc:  # noqa: BLE001
        logger.error(f"💌 wish insert error: {exc}")
    return None


async def delete_stale_unpaid(slug: str) -> None:
    """Free a link name held by an abandoned, unpaid wish."""
    cutoff = (_utcnow() - UNPAID_SLUG_HOLD).isoformat()
    try:
        async with supabase_service._client() as client:
            await client.delete(
                _url(), headers=supabase_service.headers,
                params={"slug": f"eq.{slug}", "status": "eq.awaiting_payment",
                        "created_at": f"lt.{cutoff}"},
            )
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"💌 stale wish cleanup for {slug} failed: {exc}")


async def transition(
    wish_id: str, from_status: Any, data: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """PATCH the wish only while it is in ``from_status`` (one status or a
    tuple). Returns the updated row if this caller won, else None."""
    statuses = from_status if isinstance(from_status, (tuple, list)) else (from_status,)
    flt = f"eq.{statuses[0]}" if len(statuses) == 1 else f"in.({','.join(statuses)})"
    headers = {**supabase_service.headers, "Prefer": "return=representation"}
    payload = {**data, "updated_at": _utcnow().isoformat()}
    try:
        async with supabase_service._client() as client:
            resp = await client.patch(
                _url(), headers=headers,
                params={"id": f"eq.{wish_id}", "status": flt},
                json=payload,
            )
        if resp.status_code == 200 and resp.json():
            return resp.json()[0]
        if resp.status_code != 200:
            logger.error(f"💌 wish {wish_id} transition failed: {resp.status_code} {resp.text[:300]}")
    except Exception as exc:  # noqa: BLE001
        logger.error(f"💌 wish {wish_id} transition error: {exc}")
    return None


async def bump_views(row: Dict[str, Any]) -> None:
    try:
        async with supabase_service._client() as client:
            await client.patch(
                _url(), headers={**supabase_service.headers, "Prefer": "return=minimal"},
                params={"id": f"eq.{row['id']}"},
                json={"view_count": int(row.get("view_count") or 0) + 1},
            )
    except Exception:  # noqa: BLE001 — a view counter is never worth an error
        pass


# ---------------------------------------------------------------------------
# Payment
# ---------------------------------------------------------------------------


async def create_bill(row: Dict[str, Any], token: str) -> Dict[str, Any]:
    from app.services.toyyibpay_service import toyyibpay_service

    occ = occasion_info(row.get("occasion"))
    return await asyncio.to_thread(
        toyyibpay_service.create_bill,
        bill_name="Kejutan mysyg.com",
        bill_description=f"{occ['label']} untuk {row['recipient_name']} ({row['slug']}.{wish_domain()})",
        bill_amount=float(row["amount_rm"]),
        bill_email=row["payer_email"],
        bill_phone=row["payer_phone"],
        bill_name_customer=row["sender_name"],
        bill_external_reference_no=f"WISH_{row['slug']}"[:30],
        return_url=status_url(row["id"], token),
    )


async def mark_paid(row: Dict[str, Any], tp_transaction_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """awaiting_payment -> paid. Idempotent: a second caller gets None."""
    updated = await transition(row["id"], "awaiting_payment", {
        "status": "paid",
        "paid_at": _utcnow().isoformat(),
        "toyyibpay_transaction_id": tp_transaction_id,
    })
    if updated:
        logger.info(f"💌 wish {row['slug']} paid (bill={row.get('bill_code')})")
    return updated


async def handle_paid_bill(bill_code: str, tp_transaction_id: Optional[str] = None) -> bool:
    """ToyyibPay callback hook. True if ``bill_code`` belongs to a wish."""
    row = await get_by_bill(bill_code)
    if not row:
        return False
    updated = await mark_paid(row, tp_transaction_id)
    if updated:
        # Start the clip without holding ToyyibPay's callback open; if this
        # task dies with the process, the next status poll starts it.
        asyncio.create_task(_safe_advance(updated))
    return True


async def _check_bill_paid(row: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Callback lost? Ask ToyyibPay directly (rate-limited per wish)."""
    from app.services.toyyibpay_service import toyyibpay_service

    if not row.get("bill_code"):
        return None
    if not _older_than(row.get("last_polled_at"), PAYMENT_CHECK_INTERVAL):
        return None
    await transition(row["id"], "awaiting_payment", {"last_polled_at": _utcnow().isoformat()})
    result = await asyncio.to_thread(toyyibpay_service.get_bill_transactions, row["bill_code"])
    transactions = (result.get("transactions") or []) if result.get("success") else []
    for txn in transactions:
        if isinstance(txn, dict) and str(txn.get("billpaymentStatus")) == "1":
            return await mark_paid(row, txn.get("billpaymentInvoiceNo"))
    return None


# ---------------------------------------------------------------------------
# Video
# ---------------------------------------------------------------------------


async def start_video(row: Dict[str, Any]) -> Dict[str, Any]:
    """paid -> generating (claim), then submit the clip. On a submit error
    the wish goes back to ``paid`` for a retry, or to ``video_failed``."""
    from app.services.zai_video_service import PROVIDER_DASHSCOPE, zai_video_service

    attempts = int(row.get("video_attempts") or 0) + 1
    prompt = build_video_prompt(row.get("occasion"), row.get("music_style"))
    claimed = await transition(row["id"], "paid", {
        "status": "generating",
        "video_attempts": attempts,
        "video_prompt": prompt,
        "video_task_id": None,
        "video_error": None,
        "video_started_at": _utcnow().isoformat(),
        "last_polled_at": _utcnow().isoformat(),
    })
    if not claimed:
        return await get_by_id(row["id"]) or row

    photos = claimed.get("photo_urls") or []
    try:
        task_id = await zai_video_service.submit(
            prompt,
            duration=wish_video_seconds(),
            image_url=photos[0] if photos else None,
            provider=PROVIDER_DASHSCOPE,
            aspect="9:16",
            resolution=wish_video_resolution(),
            audio=wants_audio(claimed.get("music_style")),
        )
    except Exception as exc:  # noqa: BLE001
        logger.error(f"💌 wish {claimed['slug']} video submit failed (attempt {attempts}): {exc}")
        return await _video_attempt_failed(claimed, str(exc))

    logger.info(f"💌 wish {claimed['slug']} video task {task_id} submitted (attempt {attempts})")
    return await transition(claimed["id"], "generating", {
        "video_task_id": task_id,
        "video_provider": PROVIDER_DASHSCOPE,
        "last_polled_at": _utcnow().isoformat(),
    }) or claimed


async def _video_attempt_failed(row: Dict[str, Any], error: str) -> Dict[str, Any]:
    attempts = int(row.get("video_attempts") or 0)
    if attempts < MAX_VIDEO_ATTEMPTS:
        retry = await transition(row["id"], ("generating", "storing"), {
            "status": "paid", "video_error": error[:500], "video_task_id": None,
        })
        return retry or row
    failed = await transition(row["id"], ("generating", "storing"), {
        "status": "video_failed", "video_error": error[:500],
    })
    logger.error(f"💌 wish {row['slug']} video FAILED after {attempts} attempts: {error}")
    return failed or row


async def poll_video(row: Dict[str, Any]) -> Dict[str, Any]:
    """One provider poll for a generating wish (rate-limited per wish)."""
    from app.services.zai_video_service import zai_video_service

    task_id = row.get("video_task_id")
    if not task_id:
        # Claimed but the submit never recorded a task (process died in
        # between). Give it the hard timeout, then retry.
        if _older_than(row.get("updated_at"), timedelta(minutes=3)):
            return await _video_attempt_failed(row, "submit lost")
        return row
    if _older_than(row.get("video_started_at"), VIDEO_HARD_TIMEOUT):
        return await _video_attempt_failed(row, "render timed out")
    if not _older_than(row.get("last_polled_at"), POLL_INTERVAL):
        return row

    stamped = await transition(row["id"], "generating", {"last_polled_at": _utcnow().isoformat()})
    if not stamped:
        return await get_by_id(row["id"]) or row
    try:
        result = await zai_video_service.fetch_result(task_id, provider=row.get("video_provider"))
    except Exception as exc:  # noqa: BLE001 — transient poll error: try next time
        logger.warning(f"💌 wish {row['slug']} poll error: {exc}")
        return stamped

    if result.get("status") == "processing":
        return stamped
    if result.get("status") != "success":
        return await _video_attempt_failed(
            stamped, f"{result.get('raw_status')}: {result.get('message') or result.get('code') or ''}"
        )

    storing = await transition(row["id"], "generating", {"status": "storing"})
    if not storing:
        return await get_by_id(row["id"]) or row
    try:
        stored = await zai_video_service.store(result["video_url"], website_id=f"wish-{row['slug']}")
    except Exception as exc:  # noqa: BLE001
        logger.error(f"💌 wish {row['slug']} store failed: {exc}")
        return await _video_attempt_failed(storing, f"store: {exc}")
    ready = await transition(row["id"], "storing", {
        "status": "ready",
        "video_url": keep_audio_url(stored.get("video_url")),
        "poster_url": stored.get("poster_url"),
        "video_error": None,
    })
    logger.info(f"💌 wish {row['slug']} READY: {wish_url(row['slug'])}")
    return ready or storing


async def advance(row: Dict[str, Any]) -> Dict[str, Any]:
    """Move a wish one step forward if it can. Never raises."""
    try:
        status = row.get("status")
        if status == "awaiting_payment":
            paid = await _check_bill_paid(row)
            if not paid:
                return row
            row, status = paid, "paid"
        if status == "paid":
            return await start_video(row)
        if status == "generating":
            return await poll_video(row)
        if status == "storing" and _older_than(row.get("updated_at"), timedelta(minutes=5)):
            # A store that died with its process: generate again.
            return await _video_attempt_failed(row, "store lost")
    except Exception as exc:  # noqa: BLE001
        logger.error(f"💌 advance({row.get('slug')}) error: {exc}")
    return row


async def _safe_advance(row: Dict[str, Any]) -> None:
    await advance(row)


# ---------------------------------------------------------------------------
# Public shapes
# ---------------------------------------------------------------------------


def public_view(row: Dict[str, Any]) -> Dict[str, Any]:
    """What the recipient's page may show. No payer details, no tokens."""
    occ = occasion_info(row.get("occasion"))
    return {
        "slug": row.get("slug"),
        "occasion": row.get("occasion"),
        "title": occ["title"],
        "emoji": occ["emoji"],
        "sender_name": row.get("sender_name"),
        "recipient_name": row.get("recipient_name"),
        "message": row.get("message"),
        "photo_urls": row.get("photo_urls") or [],
        "video_url": row.get("video_url") if row.get("status") == "ready" else None,
        "poster_url": row.get("poster_url") if row.get("status") == "ready" else None,
        "has_music": wants_audio(row.get("music_style")),
        "video_pending": row.get("status") in ("paid", "generating", "storing"),
    }


def support_contact() -> str:
    """Shown to a sender whose video failed (WISH_SUPPORT_CONTACT, e.g. an
    email or WhatsApp number). Empty hides the sentence."""
    return (os.getenv("WISH_SUPPORT_CONTACT") or "").strip()


def payment_page_url(bill_code: Optional[str]) -> Optional[str]:
    if not bill_code:
        return None
    from app.services.toyyibpay_service import toyyibpay_service

    return f"{toyyibpay_service.base_url}/{bill_code}"


def owner_view(row: Dict[str, Any]) -> Dict[str, Any]:
    """What the sender's status page shows."""
    return {
        "payment_url": payment_page_url(row.get("bill_code")) if row.get("status") == "awaiting_payment" else None,
        "id": row.get("id"),
        "slug": row.get("slug"),
        "status": row.get("status"),
        "url": wish_url(row["slug"]),
        "recipient_name": row.get("recipient_name"),
        "amount_rm": float(row.get("amount_rm") or 0),
        "video_url": row.get("video_url"),
        "poster_url": row.get("poster_url"),
        "attempts": int(row.get("video_attempts") or 0),
    }
