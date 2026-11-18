"""mysyg.com surprise wishes API (no BinaApp login).

    GET  /api/v1/wishes/check-slug?slug=aisyah   is the link name free?
    POST /api/v1/wishes                          create (multipart) -> pay
    GET  /api/v1/wishes/{id}/status?t=TOKEN      sender's status (advances)
    GET  /api/v1/wishes/public/{slug}            recipient's data (advances)
    POST /api/v1/wishes/public/{slug}/open       recipient tapped the box
    POST /api/v1/wishes/public/{slug}/reply      recipient's reaction + note

The sender's secret token is returned once at creation and carried in the
status-page link; only its SHA-256 is stored. See services/wishes.py.
"""

from __future__ import annotations

import asyncio
import time
import uuid
from collections import defaultdict, deque
from typing import Deque, Dict, List, Optional

import cloudinary.uploader
from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from loguru import logger

from app.services import wishes as W

router = APIRouter()

ALLOWED_TYPES = {"image/jpeg", "image/jpg", "image/png", "image/webp", "image/heic", "image/heif"}

# A small per-IP limit on creation: each create uploads and moderates up to
# five photos, which costs money even if the wish is never paid for.
_CREATE_LIMIT = 8
_CREATE_WINDOW_SECONDS = 3600.0
_create_hits: Dict[str, Deque[float]] = defaultdict(deque)


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _rate_limited(ip: str) -> bool:
    now = time.monotonic()
    hits = _create_hits[ip]
    while hits and now - hits[0] > _CREATE_WINDOW_SECONDS:
        hits.popleft()
    if len(hits) >= _CREATE_LIMIT:
        return True
    hits.append(now)
    return False


# The recipient's two buttons are public, so each gets a small per-IP,
# per-wish budget: enough for a person changing their mind, not for a loop.
_OPEN_LIMIT = 30
_REPLY_LIMIT = 6
_PUBLIC_WINDOW_SECONDS = 3600.0
_public_hits: Dict[str, Deque[float]] = defaultdict(deque)


def _public_limited(kind: str, ip: str, slug: str, limit: int) -> bool:
    now = time.monotonic()
    if len(_public_hits) > 5000:  # bound memory under a spray of keys
        _public_hits.clear()
    hits = _public_hits[f"{kind}:{ip}:{slug}"]
    while hits and now - hits[0] > _PUBLIC_WINDOW_SECONDS:
        hits.popleft()
    if len(hits) >= limit:
        return True
    hits.append(now)
    return False


def _upload_photo_sync(data: bytes, public_id: str) -> Optional[str]:
    result = cloudinary.uploader.upload(
        data,
        resource_type="image",
        folder="mysyg/wishes",
        public_id=public_id,
        overwrite=True,
        format="jpg",
        # Phones send 4000px+ photos; the video model and the page need far
        # less. "limit" never upscales.
        transformation=[{"width": 1600, "height": 1600, "crop": "limit", "quality": "auto:good"}],
    )
    return (result or {}).get("secure_url")


@router.get("/wishes/check-slug")
async def check_slug(slug: str = ""):
    slug = (slug or "").strip().lower()
    problem = W.slug_problem(slug)
    if problem:
        return {"slug": slug, "available": False, "problem": problem}
    existing = await W.get_by_slug(slug)
    if existing and not (
        existing.get("status") == "awaiting_payment"
        and W._older_than(existing.get("created_at"), W.UNPAID_SLUG_HOLD)
    ):
        return {"slug": slug, "available": False, "problem": "Nama pautan ini sudah digunakan. Cuba nama lain."}
    return {"slug": slug, "available": True, "url": W.wish_url(slug)}


@router.post("/wishes")
async def create_wish(
    request: Request,
    slug: str = Form(...),
    occasion: str = Form(W.DEFAULT_OCCASION),
    sender_name: str = Form(...),
    recipient_name: str = Form(...),
    message: str = Form(...),
    music_style: str = Form(W.DEFAULT_MUSIC),
    payer_email: str = Form(...),
    payer_phone: str = Form(...),
    consent: str = Form(""),
    unlock_at: str = Form(""),
    package: str = Form(""),
    video_direction: str = Form(""),
    photos: List[UploadFile] = File(...),
):
    if _rate_limited(_client_ip(request)):
        raise HTTPException(429, "Terlalu banyak cubaan. Sila cuba lagi sejam lagi.")

    slug = (slug or "").strip().lower()
    problem = W.slug_problem(slug)
    if problem:
        raise HTTPException(400, problem)
    if occasion not in W.OCCASIONS:
        occasion = W.DEFAULT_OCCASION
    if music_style not in W.MUSIC_STYLES:
        music_style = W.DEFAULT_MUSIC
    sender = W.clean_text(sender_name, W.MAX_NAME_CHARS)
    recipient = W.clean_text(recipient_name, W.MAX_NAME_CHARS)
    text = W.clean_text(message, W.MAX_MESSAGE_CHARS)
    email = (payer_email or "").strip().lower()
    phone = W.clean_phone(payer_phone)
    if not sender or not recipient:
        raise HTTPException(400, "Sila isi nama anda dan nama penerima.")
    if len(text) < 5:
        raise HTTPException(400, "Sila tulis ucapan anda (sekurang-kurangnya 5 huruf).")
    if not W.EMAIL_RE.match(email):
        raise HTTPException(400, "Alamat emel tidak sah.")
    if not phone:
        raise HTTPException(400, "Nombor telefon tidak sah. Contoh: 0123456789")
    if consent.lower() not in ("1", "true", "yes", "on"):
        raise HTTPException(400, "Sila sahkan anda mempunyai kebenaran menggunakan gambar ini.")
    try:
        unlock = W.parse_unlock_at(unlock_at)
    except ValueError as exc:
        raise HTTPException(400, str(exc))

    package = W.package_key((package or "").strip().lower())

    files = [f for f in (photos or []) if f and f.filename][: W.MAX_PHOTOS]
    if not files:
        raise HTTPException(400, "Sila muat naik sekurang-kurangnya satu gambar.")

    # The sender's own direction for the clip is screened here, before any
    # upload and long before payment: nobody pays for a scene we will not make.
    from app.services.wish_direction import REFUSAL, prepare_direction

    direction = await prepare_direction(video_direction)
    if not direction["ok"]:
        raise HTTPException(400, REFUSAL)

    # Slug still free? (An abandoned unpaid wish frees its name after 2 h.)
    await W.delete_stale_unpaid(slug)
    if await W.get_by_slug(slug):
        raise HTTPException(409, "Nama pautan ini sudah digunakan. Cuba nama lain.")

    # Read, moderate and upload every photo before anything is stored.
    from app.services.image_moderation_service import moderate_uploaded_image

    batch = uuid.uuid4().hex[:10]
    blobs: List[bytes] = []
    for index, upload in enumerate(files):
        if (upload.content_type or "").lower() not in ALLOWED_TYPES:
            raise HTTPException(400, f"Gambar {index + 1}: guna JPG, PNG, WEBP atau HEIC.")
        data = await upload.read()
        if not data:
            raise HTTPException(400, f"Gambar {index + 1} kosong.")
        if len(data) > W.MAX_PHOTO_BYTES:
            raise HTTPException(400, f"Gambar {index + 1} terlalu besar (maksimum 8 MB).")
        blobs.append(data)

    verdicts = await asyncio.gather(
        *(moderate_uploaded_image(data, files[i].filename or "") for i, data in enumerate(blobs))
    )
    for index, verdict in enumerate(verdicts):
        if not verdict.get("allowed", True):
            raise HTTPException(400, f"Gambar {index + 1} tidak dibenarkan: {verdict.get('message', '')}")

    async def _upload(index: int, data: bytes) -> Optional[str]:
        try:
            return await asyncio.to_thread(_upload_photo_sync, data, f"{slug}-{batch}-{index + 1}")
        except Exception as exc:  # noqa: BLE001
            logger.error(f"💌 photo {index + 1} upload failed for {slug}: {exc}")
            return None

    photo_urls = list(await asyncio.gather(*(_upload(i, d) for i, d in enumerate(blobs))))
    if not all(photo_urls):
        raise HTTPException(502, "Gagal memuat naik gambar. Sila cuba lagi.")

    token = W.new_token()
    free = email in W.free_emails()
    new_row = {
        "slug": slug,
        "status": "paid" if free else "awaiting_payment",
        "occasion": occasion,
        "sender_name": sender,
        "recipient_name": recipient,
        "message": text,
        "music_style": music_style,
        "photo_urls": photo_urls,
        "payer_email": email,
        "payer_phone": phone,
        "edit_token_hash": W.hash_token(token),
        "amount_rm": 0 if free else W.package_price_rm(package),
        "package": package,
        "video_seconds": W.package_seconds(package),
    }
    if direction["scene"]:
        new_row["video_direction"] = direction["direction"]
        new_row["video_scene"] = direction["scene"]
    if unlock:
        # Only sent when chosen, so a database without migration 069 still
        # takes every ordinary wish.
        new_row["unlock_at"] = unlock.isoformat()
    try:
        row = await W.insert(new_row)
    except W.WishSchemaError:
        raise HTTPException(
            503,
            "Pilihan video ini belum tersedia buat masa ini. Cuba pakej Ringkas tanpa arahan video, "
            "atau cuba sebentar lagi.",
        )
    if not row:
        raise HTTPException(409, "Nama pautan ini baru sahaja diambil. Cuba nama lain.")

    status_link = W.status_url(row["id"], token)
    if free:
        logger.info(f"💌 wish {slug} created FREE for {email}")
        asyncio.create_task(W._safe_advance(row))
        return {"id": row["id"], "token": token, "status_url": status_link, "payment_url": None}

    bill = await W.create_bill(row, token)
    if not bill.get("success"):
        logger.error(f"💌 wish {slug} bill failed: {bill.get('error')}")
        await W.transition(row["id"], "awaiting_payment", {"status": "cancelled"})
        raise HTTPException(502, "Gagal membuka pembayaran. Sila cuba sebentar lagi.")
    await W.transition(row["id"], "awaiting_payment", {"bill_code": bill["bill_code"]})
    logger.info(f"💌 wish {slug} created, bill {bill['bill_code']}")
    return {
        "id": row["id"],
        "token": token,
        "status_url": status_link,
        "payment_url": bill["payment_url"],
    }


@router.get("/wishes/{wish_id}/status")
async def wish_status(wish_id: str, t: str = ""):
    try:
        uuid.UUID(wish_id)
    except ValueError:
        raise HTTPException(404, "Kejutan tidak dijumpai.")
    row = await W.get_by_id(wish_id)
    if not row or not W.token_matches(row, t):
        raise HTTPException(404, "Kejutan tidak dijumpai.")
    row = await W.advance(row)
    return W.owner_view(row)


async def _live_wish(slug: str) -> dict:
    row = await W.get_by_slug((slug or "").lower())
    if not row or row.get("status") not in W.LIVE_STATUSES:
        raise HTTPException(404, "Kejutan tidak dijumpai.")
    return row


@router.get("/wishes/public/{slug}")
async def wish_public(slug: str, t: str = ""):
    row = await _live_wish(slug)
    row = await W.advance(row)
    # ?t=<sender token> is the sender previewing a sealed gift.
    return W.public_view(row, preview=W.token_matches(row, t))


@router.post("/wishes/public/{slug}/open")
async def wish_opened(slug: str, request: Request):
    """The recipient tapped the gift box. Sealed gifts cannot be opened."""
    row = await _live_wish(slug)
    if W.is_locked(row):
        raise HTTPException(423, "Kejutan ini belum boleh dibuka.")
    if _public_limited("open", _client_ip(request), row["slug"], _OPEN_LIMIT):
        return {"ok": True}
    if await W.record_open(row):
        asyncio.create_task(W.notify_opened(row))
    return {"ok": True}


@router.post("/wishes/public/{slug}/reply")
async def wish_reply(slug: str, request: Request):
    """The recipient's reaction and short note back to the sender."""
    row = await _live_wish(slug)
    if W.is_locked(row):
        raise HTTPException(423, "Kejutan ini belum boleh dibuka.")
    try:
        body = await request.json()
    except Exception:  # noqa: BLE001
        body = None
    if not isinstance(body, dict):
        raise HTTPException(400, "Balasan tidak sah.")
    reaction = body.get("reaction")
    reaction = reaction if reaction in W.REACTIONS else None
    text = W.clean_text(str(body.get("text") or ""), W.MAX_REPLY_CHARS)
    if not reaction and not text:
        raise HTTPException(400, "Pilih satu reaksi atau tulis balasan.")
    if _public_limited("reply", _client_ip(request), row["slug"], _REPLY_LIMIT):
        raise HTTPException(429, "Terlalu banyak balasan. Cuba lagi nanti.")
    saved = await W.save_reply(row, reaction, text)
    if not saved:
        raise HTTPException(503, "Balasan tidak dapat dihantar sekarang. Cuba lagi sebentar.")
    # One email per wish: a changed reply updates the status page silently,
    # so this public button can never be used to flood the sender's inbox.
    if not row.get("replied_at"):
        asyncio.create_task(W.notify_reply(saved))
    return {"ok": True}
