"""Server-rendered social images for a published site — no browser, no AI call.

WHY THIS EXISTS
---------------
Malaysian SMEs market one way above all others: they paste their link into
WhatsApp. A bare `kedaiali.binaapp.my` link with no preview image looks like
spam next to a competitor whose link unfurls into a branded card. Big brands
solve this with a designer; nobody solves it for a warung.

This module renders two images straight from data the merchant already has —
their business name, their real published URL, and the palette their page is
actually wearing (``theme_patcher.detect_palette``):

* **Share card** (1200x630) — the Open Graph / WhatsApp link-preview image.
  Served publicly at ``https://<sub>.binaapp.my/share-card.png`` and injected
  as ``og:image`` at serve time, so every link share unfurls branded, with
  zero merchant effort.
* **Story card** (1080x1920) — a WhatsApp Status / Instagram Story poster
  with the site's QR embedded, sized for a phone screen. Merchants post it;
  followers screenshot and scan.

Everything is drawn offline with Pillow. Like the QR toolkit, degradation is
explicit: if Pillow is unavailable the renderers return ``b""`` and callers
must treat that as "no image" — a missing preview image must never take a
merchant's page (or the serve path) down with it.
"""

from __future__ import annotations

import io
import logging
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)

try:  # pragma: no cover - exercised by the ImportError branch in tests
    from PIL import Image, ImageDraw, ImageFont

    PIL_AVAILABLE = True
except ImportError:  # pragma: no cover
    Image = ImageDraw = ImageFont = None
    PIL_AVAILABLE = False
    logger.warning("⚠️ Pillow not installed — share/story cards unavailable")

try:  # pragma: no cover
    import segno

    SEGNO_AVAILABLE = True
except ImportError:  # pragma: no cover
    segno = None
    SEGNO_AVAILABLE = False

#: Font files tried in order. DejaVu and Liberation ship with almost every
#: Linux base image (including the Render/Railway ones this backend deploys
#: to); the Pillow bundled default is the last resort and still scalable on
#: Pillow >= 10.1.
_BOLD_FONT_CANDIDATES = (
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/liberation/LiberationSans-Bold.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
)
_REGULAR_FONT_CANDIDATES = (
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    "/usr/share/fonts/liberation/LiberationSans-Regular.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
)

#: Open Graph dimensions WhatsApp/Facebook/Telegram all accept.
SHARE_CARD_SIZE = (1200, 630)
#: 9:16 — WhatsApp Status, Instagram Story, TikTok.
STORY_CARD_SIZE = (1080, 1920)


# ---------------------------------------------------------------------------
# Colour helpers
# ---------------------------------------------------------------------------

def _hex_to_rgb(value: str, fallback: Tuple[int, int, int]) -> Tuple[int, int, int]:
    candidate = (value or "").strip().lstrip("#")
    if len(candidate) == 3:
        candidate = "".join(ch * 2 for ch in candidate)
    if len(candidate) != 6:
        return fallback
    try:
        return tuple(int(candidate[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]
    except ValueError:
        return fallback


def _luminance(rgb: Tuple[int, int, int]) -> float:
    def channel(c: int) -> float:
        c_srgb = c / 255.0
        return c_srgb / 12.92 if c_srgb <= 0.03928 else ((c_srgb + 0.055) / 1.055) ** 2.4

    r, g, b = rgb
    return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)


def _contrast(a: Tuple[int, int, int], b: Tuple[int, int, int]) -> float:
    la, lb = _luminance(a), _luminance(b)
    lighter, darker = max(la, lb), min(la, lb)
    return (lighter + 0.05) / (darker + 0.05)


def _on_color(bg: Tuple[int, int, int]) -> Tuple[int, int, int]:
    """Black or white text, whichever stays readable on ``bg``."""
    white, near_black = (255, 255, 255), (17, 24, 39)
    return white if _contrast(white, bg) >= 4.5 else near_black


def _mix(
    a: Tuple[int, int, int], b: Tuple[int, int, int], t: float
) -> Tuple[int, int, int]:
    return tuple(round(ca + (cb - ca) * t) for ca, cb in zip(a, b))  # type: ignore[return-value]


def _resolve_colors(palette: Optional[dict]) -> dict:
    """The palette roles the renderers need, with BinaApp-orange fallbacks.

    ``detect_palette`` is best-effort and may return a partial dict — every
    role must have a usable default so a page with no detectable palette
    still gets a clean (if generic) card.
    """
    palette = palette or {}
    primary = _hex_to_rgb(palette.get("primary", ""), (234, 88, 12))
    background = _hex_to_rgb(palette.get("background", ""), (248, 250, 252))
    text = _hex_to_rgb(palette.get("text", ""), (17, 24, 39))
    # A background that can't carry its own text colour readably (common when
    # detect_palette pairs a dark-mode text with a light background or vice
    # versa) falls back to deriving the text from the background.
    if _contrast(text, background) < 3.0:
        text = _on_color(background)
    muted = _mix(text, background, 0.35)
    return {
        "primary": primary,
        "on_primary": _on_color(primary),
        "background": background,
        "text": text,
        "muted": muted,
    }


# ---------------------------------------------------------------------------
# Font + text helpers
# ---------------------------------------------------------------------------

def _load_font(size: int, bold: bool = True):
    candidates = _BOLD_FONT_CANDIDATES if bold else _REGULAR_FONT_CANDIDATES
    for path in candidates:
        try:
            return ImageFont.truetype(path, size=size)
        except Exception:
            continue
    try:
        # Pillow >= 10.1: scalable embedded font.
        return ImageFont.load_default(size=size)
    except TypeError:  # pragma: no cover - ancient Pillow
        return ImageFont.load_default()


def _wrap_to_width(draw, text: str, font, max_width: int) -> List[str]:
    """Greedy word wrap measured with the actual font."""
    words = (text or "").split()
    lines: List[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if draw.textlength(candidate, font=font) <= max_width or not current:
            current = candidate
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def _fit_text(
    draw,
    text: str,
    max_width: int,
    max_lines: int,
    start_size: int,
    min_size: int,
    bold: bool = True,
):
    """Largest font size at which ``text`` wraps into ``max_lines`` lines.

    Ellipsises the last line as a final resort so a very long business name
    can never overflow the canvas.
    """
    size = start_size
    while size > min_size:
        font = _load_font(size, bold=bold)
        lines = _wrap_to_width(draw, text, font, max_width)
        if len(lines) <= max_lines and all(
            draw.textlength(line, font=font) <= max_width for line in lines
        ):
            return font, lines
        size = size - max(2, size // 12)

    font = _load_font(min_size, bold=bold)
    lines = _wrap_to_width(draw, text, font, max_width)[:max_lines]
    if lines:
        last = lines[-1]
        while last and draw.textlength(last + "…", font=font) > max_width:
            last = last[:-1].rstrip()
        lines[-1] = (last + "…") if last != lines[-1] else last
    return font, lines


def _line_height(font) -> int:
    ascent, descent = font.getmetrics()
    return ascent + descent


def _display_url(url: str) -> str:
    return (url or "").replace("https://", "").replace("http://", "").rstrip("/")


# ---------------------------------------------------------------------------
# Decorations
# ---------------------------------------------------------------------------

def _decorate(base, primary: Tuple[int, int, int]) -> None:
    """Two soft primary-tinted discs so the card reads branded, not blank.

    Drawn onto an RGBA overlay and alpha-composited, keeping the text layer
    fully opaque.
    """
    width, height = base.size
    overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    r1 = int(height * 0.75)
    draw.ellipse(
        [width - r1 // 2, -r1 // 2, width + r1 // 2, r1 // 2],
        fill=primary + (26,),
    )
    r2 = int(height * 0.55)
    draw.ellipse(
        [-r2 // 2, height - r2 // 2, r2 // 2, height + r2 // 2],
        fill=primary + (20,),
    )
    base.alpha_composite(overlay)


def _qr_png_image(url: str, dark: Tuple[int, int, int], target_px: int):
    """The site QR as a PIL image roughly ``target_px`` wide, or None."""
    if not url or not SEGNO_AVAILABLE:
        return None
    try:
        code = segno.make(url, error="m")
        # segno renders at integer scale; pick the scale that lands nearest
        # the target, then resize with NEAREST to keep modules crisp.
        modules = code.symbol_size(scale=1, border=2)[0]
        scale = max(2, target_px // modules)
        buf = io.BytesIO()
        dark_hex = "#{:02X}{:02X}{:02X}".format(*dark)
        code.save(buf, kind="png", scale=scale, border=2, dark=dark_hex, light="#FFFFFF")
        buf.seek(0)
        img = Image.open(buf).convert("RGB")
        if img.width != target_px:
            img = img.resize((target_px, target_px), Image.NEAREST)
        return img
    except Exception as exc:  # pragma: no cover - encoder should not fail
        logger.error(f"Story QR render failed: {exc}")
        return None


# ---------------------------------------------------------------------------
# Renderers
# ---------------------------------------------------------------------------

def render_share_card(
    business_name: str,
    url: str,
    palette: Optional[dict] = None,
    tagline: Optional[str] = None,
) -> bytes:
    """The 1200x630 Open Graph image for a link preview, as PNG bytes.

    Everything on it is the merchant's own data: name, real URL, the palette
    the page is wearing. Returns ``b""`` when Pillow is unavailable or the
    draw fails — callers treat that as "no image".
    """
    if not PIL_AVAILABLE:
        return b""
    try:
        colors = _resolve_colors(palette)
        width, height = SHARE_CARD_SIZE
        card = Image.new("RGBA", SHARE_CARD_SIZE, colors["background"] + (255,))
        _decorate(card, colors["primary"])
        draw = ImageDraw.Draw(card)

        margin = 84
        content_width = width - margin * 2

        # Kicker: the bare domain, small caps, primary — reads as the brand tag.
        kicker_font = _load_font(30, bold=True)
        draw.text(
            (margin, margin),
            _display_url(url).upper(),
            font=kicker_font,
            fill=colors["primary"],
        )

        # Business name, fitted.
        name_font, name_lines = _fit_text(
            draw,
            business_name or _display_url(url),
            max_width=content_width,
            max_lines=2,
            start_size=104,
            min_size=48,
        )
        y = margin + 76
        for line in name_lines:
            draw.text((margin, y), line, font=name_font, fill=colors["text"])
            y += int(_line_height(name_font) * 1.04)

        # URL pill measured first: the tagline must never run into it.
        pill_font = _load_font(34, bold=True)
        pill_text = _display_url(url)
        pill_pad_x, pill_pad_y = 36, 20
        pill_w = int(draw.textlength(pill_text, font=pill_font)) + pill_pad_x * 2
        pill_h = _line_height(pill_font) + pill_pad_y * 2
        pill_y = height - margin - pill_h

        # Tagline (the page's own meta description) — muted, only as many
        # lines as actually fit between the name and the pill.
        if tagline:
            tag_font, tag_lines = _fit_text(
                draw,
                tagline,
                max_width=content_width,
                max_lines=2,
                start_size=38,
                min_size=26,
                bold=False,
            )
            y += 18
            tag_line_h = int(_line_height(tag_font) * 1.15)
            for i, line in enumerate(tag_lines):
                if y + tag_line_h > pill_y - 24:
                    break
                if i == len(tag_lines) - 1 or y + tag_line_h * 2 <= pill_y - 24:
                    draw.text((margin, y), line, font=tag_font, fill=colors["muted"])
                else:
                    # Last line we can fit but more remain — ellipsise it.
                    clipped = line
                    while clipped and draw.textlength(clipped + "…", font=tag_font) > content_width:
                        clipped = clipped[:-1].rstrip()
                    draw.text((margin, y), clipped + "…", font=tag_font, fill=colors["muted"])
                    y += tag_line_h
                    break
                y += tag_line_h
        draw.rounded_rectangle(
            [margin, pill_y, margin + pill_w, pill_y + pill_h],
            radius=pill_h // 2,
            fill=colors["primary"],
        )
        draw.text(
            (margin + pill_pad_x, pill_y + pill_pad_y),
            pill_text,
            font=pill_font,
            fill=colors["on_primary"],
        )

        buf = io.BytesIO()
        card.convert("RGB").save(buf, format="PNG", optimize=True)
        return buf.getvalue()
    except Exception as exc:
        logger.error(f"Share card render failed for '{business_name}': {exc}")
        return b""


def render_story_card(
    business_name: str,
    url: str,
    palette: Optional[dict] = None,
    tagline: Optional[str] = None,
    language: str = "ms",
) -> bytes:
    """A 1080x1920 WhatsApp-Status / Instagram-Story poster, as PNG bytes.

    Carries the site QR in a white frame so a follower can screenshot the
    status and scan it later — the offline equivalent of a swipe-up link.
    """
    if not PIL_AVAILABLE:
        return b""
    try:
        colors = _resolve_colors(palette)
        width, height = STORY_CARD_SIZE
        is_ms = (language or "ms").lower().startswith("ms")

        card = Image.new("RGBA", STORY_CARD_SIZE, colors["background"] + (255,))
        _decorate(card, colors["primary"])
        draw = ImageDraw.Draw(card)

        margin = 96
        content_width = width - margin * 2

        # Kicker pill, centred.
        kicker = "IMBAS & LAWAT" if is_ms else "SCAN & VISIT"
        kicker_font = _load_font(36, bold=True)
        k_w = int(draw.textlength(kicker, font=kicker_font)) + 72
        k_h = _line_height(kicker_font) + 36
        k_x = (width - k_w) // 2
        k_y = 170
        draw.rounded_rectangle(
            [k_x, k_y, k_x + k_w, k_y + k_h], radius=k_h // 2, fill=colors["primary"]
        )
        draw.text(
            (k_x + 36, k_y + 18), kicker, font=kicker_font, fill=colors["on_primary"]
        )

        # Business name, centred and fitted.
        name_font, name_lines = _fit_text(
            draw,
            business_name or _display_url(url),
            max_width=content_width,
            max_lines=3,
            start_size=110,
            min_size=54,
        )
        y = k_y + k_h + 84
        for line in name_lines:
            line_w = draw.textlength(line, font=name_font)
            draw.text(
                ((width - line_w) // 2, y), line, font=name_font, fill=colors["text"]
            )
            y += int(_line_height(name_font) * 1.05)

        if tagline:
            tag_font, tag_lines = _fit_text(
                draw,
                tagline,
                max_width=content_width,
                max_lines=2,
                start_size=42,
                min_size=30,
                bold=False,
            )
            y += 20
            for line in tag_lines:
                line_w = draw.textlength(line, font=tag_font)
                draw.text(
                    ((width - line_w) // 2, y), line, font=tag_font, fill=colors["muted"]
                )
                y += int(_line_height(tag_font) * 1.2)

        # QR in a white rounded frame — always on white for scan contrast.
        qr_target = 560
        frame_pad = 44
        frame_size = qr_target + frame_pad * 2
        frame_x = (width - frame_size) // 2
        frame_y = max(y + 70, (height - frame_size) // 2 - 40)
        draw.rounded_rectangle(
            [frame_x, frame_y, frame_x + frame_size, frame_y + frame_size],
            radius=48,
            fill=(255, 255, 255),
            outline=colors["primary"],
            width=6,
        )
        qr_img = _qr_png_image(url, colors["text"], qr_target)
        if qr_img is not None:
            card.paste(qr_img, (frame_x + frame_pad, frame_y + frame_pad))

        # URL under the frame, primary and bold.
        url_font = _load_font(44, bold=True)
        url_text = _display_url(url)
        while url_text and draw.textlength(url_text, font=url_font) > content_width:
            url_font = _load_font(max(28, url_font.size - 4), bold=True)
            if url_font.size <= 28:
                break
        url_w = draw.textlength(url_text, font=url_font)
        url_y = frame_y + frame_size + 56
        draw.text(
            ((width - url_w) // 2, url_y), url_text, font=url_font, fill=colors["primary"]
        )

        # One-line instruction at the bottom.
        # No emoji here: the fonts we can rely on server-side (DejaVu /
        # Liberation) draw emoji as tofu boxes.
        hint = (
            "Tangkap skrin & imbas kod QR ini"
            if is_ms
            else "Screenshot & scan this QR code"
        )
        hint_font = _load_font(34, bold=False)
        hint_w = draw.textlength(hint, font=hint_font)
        draw.text(
            ((width - hint_w) // 2, height - 150),
            hint,
            font=hint_font,
            fill=colors["muted"],
        )

        buf = io.BytesIO()
        card.convert("RGB").save(buf, format="PNG", optimize=True)
        return buf.getvalue()
    except Exception as exc:
        logger.error(f"Story card render failed for '{business_name}': {exc}")
        return b""
