"""When the merchant's arahan names colours, the palette uses only those.

agp.binaapp.my: the brief said "KUNING TERANG + MERAH CILI" (yellow / chilli
red, black outlines) and the plan shipped ``accent_2: #203808`` — a dark
green the model borrowed "from the photos". ``named_colours`` reads the
colours the brief names in a colour context (warna, tema, signboard,
brand, …), and ``constrain_palette`` replaces every palette colour that is
neither a neutral nor in the hue family of a named colour. Pure; no I/O.
"""

from __future__ import annotations

import colorsys
import re
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

#: Colour words (Malay + English) → a representative hex. Longest first so
#: "merah jambu" is not read as "merah".
_COLOUR_WORDS: Sequence[Tuple[str, str]] = (
    ("merah jambu", "#EC4899"), ("merah hati", "#7F1D1D"), ("merah cili", "#D7261E"), ("biru laut", "#1E3A8A"),
    ("kuning", "#FACC15"), ("yellow", "#FACC15"),
    ("merah", "#DC2626"), ("red", "#DC2626"), ("maroon", "#7F1D1D"),
    ("hitam", "#111111"), ("black", "#111111"),
    ("putih", "#FFFFFF"), ("white", "#FFFFFF"),
    ("hijau", "#16A34A"), ("green", "#16A34A"),
    ("biru", "#2563EB"), ("blue", "#2563EB"), ("navy", "#1E3A8A"),
    ("oren", "#F97316"), ("jingga", "#F97316"), ("orange", "#F97316"),
    ("ungu", "#7C3AED"), ("purple", "#7C3AED"),
    ("pink", "#EC4899"),
    ("coklat", "#92400E"), ("brown", "#92400E"),
    ("emas", "#D4A017"), ("gold", "#D4A017"),
    ("teal", "#0D9488"), ("turquoise", "#14B8A6"),
    ("kelabu", "#6B7280"), ("grey", "#6B7280"), ("gray", "#6B7280"),
    ("krim", "#FFF8E7"), ("cream", "#FFF8E7"),
)

#: The palette is LOCKED only when the brief explicitly lists brand
#: colours ("Warna jenama: kuning, merah, hitam", "Brand colours: red &
#: black"). A descriptive mention — "Cari kedai kuning terang dengan
#: signboard …", "logo kami merah" — describes the shop, not the palette:
#: locking on it turned the yellow/red/black brand into yellow-only and
#: would have removed the logo's red and black. Food words never count
#: either ("nasi putih", "sambal merah").
_CONTEXT_RE = re.compile(
    r"\b(?:warna\s+(?:jenama|tema|utama|rasmi|korporat|brand|kedai\s+kami\s+ialah)|tema\s+warna|skema\s+warna|"
    r"palet(?:te)?\s+warna|brand\s+colou?rs?|brand\s+palette|colou?r\s+(?:scheme|palette)|"
    r"(?:colou?rs?|warna)\s*[:：=])",
    re.IGNORECASE,
)

#: How far (degrees) a colour's hue may sit from a named colour's hue.
HUE_TOLERANCE = 22.0
#: How far a colour's lightness may sit from that named colour's: a shade,
#: not a different colour (dark brick-brown is not 'merah cili').
LIGHTNESS_TOLERANCE = 0.22


def _hex(value: Optional[str]) -> Optional[str]:
    v = str(value or "").strip()
    if re.fullmatch(r"#?[0-9a-fA-F]{6}", v):
        return "#" + v.lstrip("#").upper()
    if re.fullmatch(r"#?[0-9a-fA-F]{3}", v):
        v = v.lstrip("#")
        return "#" + "".join(c * 2 for c in v).upper()
    return None


def _hls(hex_value: str) -> Tuple[float, float, float]:
    h = hex_value.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    return colorsys.rgb_to_hls(r, g, b)


def is_neutral(hex_value: str) -> bool:
    """Whites, near-blacks, greys and barely-tinted off-whites."""
    hv = _hex(hex_value)
    if hv is None:
        return False
    hue, light, sat = _hls(hv)
    return light >= 0.94 or light <= 0.09 or sat <= 0.12 or (sat <= 0.25 and (light >= 0.88 or light <= 0.15))


def _hue_deg(hex_value: str) -> float:
    return _hls(hex_value)[0] * 360.0


def _hue_distance(a: float, b: float) -> float:
    d = abs(a - b) % 360.0
    return min(d, 360.0 - d)


def named_colours(*texts: Optional[str]) -> List[str]:
    """Hexes for the colours the brief EXPLICITLY lists as its brand
    colours, in first-mentioned order, de-duplicated. Empty = no lock."""
    found: List[Tuple[Tuple[int, int], str]] = []
    n_sent = 0
    for text in texts:
        if not text:
            continue
        for sent in re.split(r"(?<=[.!?\n])\s*", str(text)):
            n_sent += 1
            if not _CONTEXT_RE.search(sent):
                continue
            low = sent.lower()
            taken: List[Tuple[int, int]] = []
            for word, hx in _COLOUR_WORDS:
                for m in re.finditer(rf"\b{re.escape(word)}\b", low):
                    if any(s <= m.start() < e for s, e in taken):
                        continue
                    taken.append((m.start(), m.end()))
                    found.append(((n_sent, m.start()), hx))
    out: List[str] = []
    for _, hx in sorted(found):
        if hx not in out:
            out.append(hx)
    return out


def brief_colour_set(texts: Iterable[Optional[str]], brand_colors: Optional[Dict[str, str]] = None) -> List[str]:
    """Colours the brief names, plus any explicit brand colours — empty
    when the brief names none (no constraint then)."""
    named = named_colours(*list(texts or ()))
    if not named:
        return []
    for value in (brand_colors or {}).values() if isinstance(brand_colors, dict) else ():
        hv = _hex(value)
        if hv and hv not in named:
            named.append(hv)
    return named


def allowed(hex_value: str, named: Sequence[str]) -> bool:
    """Neutral, or a shade of a chromatic named colour: within
    HUE_TOLERANCE of its hue AND LIGHTNESS_TOLERANCE of its lightness. Hue
    alone let a dark brick-brown (#5D2310, 0.27 darker than chilli red)
    pass as 'red' — every price and Pesan button on agp came out brown."""
    hv = _hex(hex_value)
    if hv is None:
        return False
    if is_neutral(hv):
        return True
    hue, light = _hue_deg(hv), _hls(hv)[1]
    return any(
        not is_neutral(n)
        and _hue_distance(hue, _hue_deg(n)) <= HUE_TOLERANCE
        and abs(light - _hls(n)[1]) <= LIGHTNESS_TOLERANCE
        for n in named
    )


def _luminance(hex_value: str) -> float:
    def ch(c: float) -> float:
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    h = hex_value.lstrip("#")
    r, g, b = (ch(int(h[i:i + 2], 16) / 255) for i in (0, 2, 4))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _contrast(a: str, b: str) -> float:
    la, lb = sorted((_luminance(a), _luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


_NEUTRALS = {
    "light": {"bg": "#FFFFFF", "surface": "#FAFAFA", "text": "#111111", "muted": "#525252"},
    "dark": {"bg": "#0A0A0A", "surface": "#171717", "text": "#F5F5F5", "muted": "#A3A3A3"},
}


def constrain_palette(
    palette: Dict[str, str],
    named: Sequence[str],
    *,
    accent_keys: Iterable[str],
    neutral_keys: Dict[str, str],
    background_key: str,
    dark: bool = False,
) -> Tuple[Dict[str, str], List[str]]:
    """Every colour outside the merchant's named colours (plus neutrals)
    is replaced. Accent keys take the named chromatic colours, the most
    readable on the background first; neutral keys (``{key: role}`` with
    role in bg/surface/text/muted) fall back to plain neutrals. Returns the
    new palette and the adjustments made."""
    out = dict(palette)
    notes: List[str] = []
    named = [h for h in (_hex(n) for n in named) if h]
    chromatic = [n for n in named if not is_neutral(n)]
    if not chromatic:
        return out, notes
    mode = "dark" if dark else "light"
    for key, role in neutral_keys.items():
        value = _hex(out.get(key))
        if value and not allowed(value, named):
            out[key] = _NEUTRALS[mode].get(role, _NEUTRALS[mode]["surface"])
            notes.append(f"palette.{key}: {value} is not a merchant colour — neutral {out[key]}")
    bg = _hex(out.get(background_key)) or _NEUTRALS[mode]["bg"]
    in_use = {(_hex(out.get(k)) or "") for k in accent_keys}
    for key in accent_keys:
        value = _hex(out.get(key))
        if value and allowed(value, named):
            continue
        ranked = sorted(chromatic, key=lambda c: -_contrast(c, bg))
        pick = next((c for c in ranked if c not in in_use), ranked[0])
        in_use.add(pick)
        out[key] = pick
        notes.append(f"palette.{key}: {value or '(none)'} is not a merchant colour — {pick} from the brief")
    return out, notes
