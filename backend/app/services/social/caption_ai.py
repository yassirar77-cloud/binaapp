"""AI caption drafts for social posts, on the existing provider chain.

Order: DeepSeek → Z.ai GLM (when configured) → a deterministic template, so
the button always produces something editable. The result is trimmed to the
platform limit in UTF-16 units, which is how TikTok counts.
"""

from __future__ import annotations

from typing import Optional

from loguru import logger

from app.services.social.tiktok_client import VIDEO_TITLE_MAX_UTF16, utf16_length

SYSTEM_PROMPT = (
    "You write short, punchy TikTok captions for BinaApp (binaapp.my), a Malaysian "
    "AI website builder for small F&B businesses: describe your kedai in plain "
    "Bahasa Malaysia or English and get a live website with WhatsApp ordering, "
    "menus, QR codes and delivery. Output ONLY the caption text — no quotes, no "
    "preamble, no explanations. Keep it natural for Malaysian creators; "
    "'Manglish' is fine when the brief mixes languages. Include 3–6 relevant "
    "hashtags at the end (e.g. #BinaApp #SMEMalaysia #KedaiMakan). No claims "
    "about prices, awards or numbers that are not in the brief."
)

_LANG_HINT = {
    "ms": "Write in Bahasa Malaysia.",
    "en": "Write in English.",
    "mixed": "Write in casual Malaysian mixed BM/English.",
}


def _fallback_caption(brief: str, language: str) -> str:
    brief = " ".join(brief.split())[:160].rstrip(".")
    if language == "en":
        body = f"{brief}. Build your F&B website in minutes with BinaApp 🚀" if brief else "Build your F&B website in minutes with BinaApp 🚀"
    else:
        body = f"{brief}. Bina laman web kedai anda dalam beberapa minit dengan BinaApp 🚀" if brief else "Bina laman web kedai anda dalam beberapa minit dengan BinaApp 🚀"
    return f"{body}\n\n#BinaApp #SMEMalaysia #KedaiMakan #LamanWeb"


def trim_utf16(text: str, max_units: int) -> str:
    """Trim to ``max_units`` UTF-16 code units without splitting a surrogate pair."""
    if utf16_length(text) <= max_units:
        return text
    encoded = text.encode("utf-16-le")[: max_units * 2]
    out = encoded.decode("utf-16-le", errors="ignore")
    return out.rstrip()


async def draft_caption(
    brief: str,
    *,
    language: str = "mixed",
    media_type: str = "video",
    max_units: int = VIDEO_TITLE_MAX_UTF16,
    ai_service: Optional[object] = None,
) -> dict:
    """Return ``{"caption": str, "provider": str}``. Never raises."""
    language = language if language in _LANG_HINT else "mixed"
    brief = (brief or "").strip()
    prompt = (
        f"{_LANG_HINT[language]}\nMedia: {'photo carousel' if media_type == 'photo' else 'short video'}.\n"
        f"Hard limit: {min(max_units, 600)} characters including hashtags; aim for under 300.\n"
        f"Brief from the BinaApp team: {brief or 'a quick look at BinaApp building a kedai makan website'}"
    )

    if ai_service is None:
        try:
            from app.services.ai_service import ai_service as _svc  # heavy import, lazy

            ai_service = _svc
        except Exception as exc:  # noqa: BLE001 - offline / test environments
            logger.warning("caption_ai: AI service unavailable: {}", exc)
            ai_service = None

    text: Optional[str] = None
    provider = "template"
    if ai_service is not None:
        for name, call in (
            ("deepseek", getattr(ai_service, "_call_deepseek", None)),
            ("glm", getattr(ai_service, "_call_glm", None)),
        ):
            if call is None:
                continue
            if name == "glm" and not getattr(ai_service, "zai_api_key", None):
                continue
            try:
                raw = await call(prompt, temperature=0.8, system_prompt=SYSTEM_PROMPT, max_tokens=400)
            except Exception as exc:  # noqa: BLE001 - provider hiccup, try the next
                logger.warning("caption_ai: {} failed: {}", name, exc)
                raw = None
            if raw and raw.strip():
                text = raw.strip().strip('"').strip()
                provider = name
                break

    if not text:
        text = _fallback_caption(brief, language)
    return {"caption": trim_utf16(text, max_units), "provider": provider}
