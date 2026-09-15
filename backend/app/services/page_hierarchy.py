"""
Page hierarchy repairs (Round 2, §C9–§C12).

- **One real headline (§C9).** The H1 must be the largest text on the page:
  at least 2× the body size and never smaller than any other text. The
  Dobi page's biggest text was "Dari RM6" in a side card. ``static_type_repairs``
  fixes what can be seen in the markup (Tailwind size classes on non-H1
  text larger than the H1, an H2 set at body size); ``measured_type_repairs``
  uses the browser's computed sizes (from the critique render) to cap the
  offenders by CSS path and force the H1/H2 floors.
- **Section headings are headings (§C10).** H2 ≥ 1.6× body with a distinct
  weight — enforced by injected CSS, never by an eyebrow label.
- **Hero readability (§C11).** The hero text's background luminance is
  sampled on the screenshot inside the text's bounding box; below 4.5:1
  against the text colour a solid/gradient panel is put behind the text
  column. One hero image only: a background photo plus an inset photo of
  the same file loses the inset.
- **CTA de-duplication (§C12).** The nav CTA is the primary action
  (WhatsApp / telefon); the hero carries primary + secondary; a third
  repeat of the same CTA text elsewhere is removed.

Pure string/number work; the browser measurements come in as a dict.
"""

from __future__ import annotations

import io
import re
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

STYLE_ID = "binaapp-hierarchy"
H1_MIN_RATIO = 2.0
H2_MIN_RATIO = 1.6
HERO_MIN_CONTRAST = 4.5

_TW_SIZES: Dict[str, float] = {
    "text-xs": 0.75, "text-sm": 0.875, "text-base": 1.0, "text-lg": 1.125, "text-xl": 1.25, "text-2xl": 1.5,
    "text-3xl": 1.875, "text-4xl": 2.25, "text-5xl": 3.0, "text-6xl": 3.75, "text-7xl": 4.5, "text-8xl": 6.0, "text-9xl": 8.0,
}
_TW_SIZE_RE = re.compile(r"(?<![\w-])(?:(sm|md|lg|xl|2xl):)?(text-(?:xs|sm|base|lg|xl|[2-9]xl))(?![\w-])")
_H1_RE = re.compile(r"<h1\b([^>]*)>(.*?)</h1>", re.IGNORECASE | re.DOTALL)
_H2_RE = re.compile(r"<h2\b([^>]*)>", re.IGNORECASE)
_TAG_RE = re.compile(r"<[^>]+>")
_CLASS_RE = re.compile(r"\bclass=([\"'])(.*?)\1", re.IGNORECASE | re.DOTALL)
_HEAD_CLOSE_RE = re.compile(r"</head>", re.IGNORECASE)
_HERO_RE = re.compile(r"<(section|header|div)\b[^>]*\bid=[\"'](?:home|hero|utama)[\"'][^>]*>", re.IGNORECASE)
_BG_URL_RE = re.compile(r"background(?:-image)?\s*:[^;\"']*url\((['\"]?)([^'\")]+)\1\)", re.IGNORECASE)
_IMG_RE = re.compile(r"<img\b[^>]*\bsrc=[\"']([^\"']+)[\"'][^>]*>", re.IGNORECASE)
_CTA_RE = re.compile(r"<a\b[^>]*>(.*?)</a>", re.IGNORECASE | re.DOTALL)
_NAV_RE = re.compile(r"<nav\b[^>]*>.*?</nav>", re.IGNORECASE | re.DOTALL)


@dataclass
class HierarchyReport:
    class_rewrites: int = 0
    css_rules: List[str] = field(default_factory=list)
    hero_panel: bool = False
    hero_contrast: Optional[float] = None
    inset_removed: bool = False
    ctas_removed: int = 0
    notes: List[str] = field(default_factory=list)

    @property
    def changed(self) -> bool:
        return bool(self.class_rewrites or self.css_rules or self.hero_panel or self.inset_removed or self.ctas_removed)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "class_rewrites": self.class_rewrites, "css_rules": list(self.css_rules), "hero_panel": self.hero_panel,
            "hero_contrast": self.hero_contrast, "inset_removed": self.inset_removed, "ctas_removed": self.ctas_removed,
            "notes": list(self.notes),
        }


# ---------------------------------------------------------------------------
# §C9/§C10 static (markup) repairs
# ---------------------------------------------------------------------------

def _largest_size_in_classes(classes: str) -> Optional[float]:
    sizes = [_TW_SIZES[m.group(2)] for m in _TW_SIZE_RE.finditer(classes or "")]
    return max(sizes) if sizes else None


def _size_class_for(rem: float) -> str:
    best = min(_TW_SIZES.items(), key=lambda kv: abs(kv[1] - rem))
    return best[0]


def static_type_repairs(html: str, report: Optional[HierarchyReport] = None) -> Tuple[str, HierarchyReport]:
    """Tailwind-class level: no element other than the H1 may carry a size
    class larger than the H1's; every H2 carries at least text-3xl."""
    report = report or HierarchyReport()
    out = html or ""
    h1 = _H1_RE.search(out)
    if not h1:
        return out, report
    h1_size = _largest_size_in_classes(h1.group(1)) or 3.0
    if h1_size < 2.25:
        # The H1 itself is too small: lift it to text-5xl (3rem) in markup.
        attrs = h1.group(1)
        if _CLASS_RE.search(attrs):
            new_attrs = _CLASS_RE.sub(lambda m: f'class={m.group(1)}{_TW_SIZE_RE.sub("", m.group(2)).strip()} text-4xl md:text-5xl lg:text-6xl{m.group(1)}', attrs, count=1)
        else:
            new_attrs = attrs + ' class="text-4xl md:text-5xl lg:text-6xl"'
        out = out[: h1.start()] + f"<h1{new_attrs}>{h1.group(2)}</h1>" + out[h1.end():]
        report.class_rewrites += 1
        h1_size = 3.75
    cap = _size_class_for(max(1.875, h1_size - 0.75))

    # Non-H1 elements whose size class exceeds the H1's → capped.
    def _cap_element(m: "re.Match") -> str:
        tag = m.group(1).lower()
        attrs = m.group(2)
        if tag == "h1":
            return m.group(0)
        cm = _CLASS_RE.search(attrs)
        if not cm:
            return m.group(0)
        classes = cm.group(2)
        biggest = _largest_size_in_classes(classes)
        if biggest is None or biggest < h1_size:
            return m.group(0)

        def _sub(sm: "re.Match") -> str:
            prefix = f"{sm.group(1)}:" if sm.group(1) else ""
            return f"{prefix}{cap}" if _TW_SIZES[sm.group(2)] >= h1_size else sm.group(0)

        new_classes = _TW_SIZE_RE.sub(_sub, classes)
        report.class_rewrites += 1
        return m.group(0).replace(cm.group(0), f"class={cm.group(1)}{new_classes}{cm.group(1)}", 1)

    out = re.sub(r"<(h[2-6]|p|span|div|a|strong|em|li|button)\b([^>]*)>", _cap_element, out, flags=re.IGNORECASE)

    # H2 at body size → text-3xl.
    def _lift_h2(m: "re.Match") -> str:
        attrs = m.group(1)
        cm = _CLASS_RE.search(attrs)
        if cm:
            biggest = _largest_size_in_classes(cm.group(2))
            if biggest is not None and biggest >= 1.875:
                return m.group(0)
            new_classes = (_TW_SIZE_RE.sub("", cm.group(2)).strip() + " text-3xl md:text-4xl").strip()
            report.class_rewrites += 1
            return f"<h2{attrs.replace(cm.group(0), f'class={cm.group(1)}{new_classes}{cm.group(1)}', 1)}>"
        report.class_rewrites += 1
        return f'<h2{attrs} class="text-3xl md:text-4xl">'

    out = _H2_RE.sub(_lift_h2, out)
    return out, report


def hierarchy_css(body_px: float = 16.0) -> str:
    """The floor every plan-mode page gets: H1 ≥ 2× body, H2 ≥ 1.6× body,
    distinct weights; nothing else may exceed the H2 unless it is the H1."""
    h1 = max(2.0 * body_px, 32.0)
    h2 = max(1.6 * body_px, 25.6)
    return (
        f"h1{{font-size:max(var(--step-5,{h1 / 16:.3f}rem),{h1 / 16:.3f}rem)!important;line-height:1.05!important;font-weight:700}}"
        f"h2{{font-size:max(var(--step-3,{h2 / 16:.3f}rem),{h2 / 16:.3f}rem)!important;line-height:1.15!important;font-weight:700}}"
        f"h2 + p,h2 ~ p{{font-size:inherit}}"
    )


def _inject_css(html: str, css: str) -> str:
    if not css:
        return html
    if f'id="{STYLE_ID}"' in html:
        return re.sub(rf'(<style id="{STYLE_ID}">)(.*?)(</style>)', lambda m: f"{m.group(1)}{m.group(2)}{css}{m.group(3)}", html, count=1, flags=re.DOTALL)
    m = _HEAD_CLOSE_RE.search(html)
    block = f'<style id="{STYLE_ID}">{css}</style>\n'
    if not m:
        return block + html
    return html[: m.start()] + block + html[m.start():]


def measured_type_repairs(html: str, measured: Dict[str, Any], report: Optional[HierarchyReport] = None) -> Tuple[str, HierarchyReport]:
    """From the browser's computed sizes: cap every non-H1 element that is
    as large as (or larger than) the H1 by CSS path, and force the H1/H2
    floors. ``measured`` is the dict the critique render produces."""
    report = report or HierarchyReport()
    if not measured:
        return html, report
    body_px = float(measured.get("bodyFontPx") or 16.0)
    h1_px = float(measured.get("h1FontPx") or 0.0)
    rules: List[str] = [hierarchy_css(body_px)]
    target_cap = max(h2_floor := H2_MIN_RATIO * body_px, min(h1_px * 0.75, h1_px - 4) if h1_px else h2_floor)
    for offender in measured.get("largerThanH1") or []:
        path = offender.get("path") if isinstance(offender, dict) else None
        if path:
            rules.append(f"{path}{{font-size:{target_cap / 16:.3f}rem!important;line-height:1.1!important}}")
            report.notes.append(f"capped {path} ({offender.get('px')}px) below the H1")
    for offender in measured.get("smallH2") or []:
        path = offender.get("path") if isinstance(offender, dict) else None
        if path:
            rules.append(f"{path}{{font-size:{H2_MIN_RATIO * body_px / 16:.3f}rem!important;font-weight:700!important}}")
            report.notes.append(f"lifted {path} ({offender.get('px')}px) to an H2 size")
    if h1_px and h1_px < H1_MIN_RATIO * body_px:
        report.notes.append(f"H1 at {h1_px}px lifted to ≥ {H1_MIN_RATIO * body_px}px")
    css = "".join(rules)
    report.css_rules.extend(rules)
    return _inject_css(html, css), report


# ---------------------------------------------------------------------------
# §C11 hero readability
# ---------------------------------------------------------------------------

def _luminance(rgb: Tuple[int, int, int]) -> float:
    def _c(v: int) -> float:
        s = v / 255.0
        return s / 12.92 if s <= 0.03928 else ((s + 0.055) / 1.055) ** 2.4
    r, g, b = rgb
    return 0.2126 * _c(r) + 0.7152 * _c(g) + 0.0722 * _c(b)


def contrast(rgb_a: Tuple[int, int, int], rgb_b: Tuple[int, int, int]) -> float:
    la, lb = _luminance(rgb_a), _luminance(rgb_b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def parse_css_color(value: str) -> Optional[Tuple[int, int, int]]:
    v = (value or "").strip().lower()
    m = re.match(r"rgba?\((\d+)\s*,\s*(\d+)\s*,\s*(\d+)", v)
    if m:
        return int(m.group(1)), int(m.group(2)), int(m.group(3))
    m = re.match(r"#([0-9a-f]{6})$", v)
    if m:
        h = m.group(1)
        return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    m = re.match(r"#([0-9a-f]{3})$", v)
    if m:
        h = m.group(1)
        return int(h[0] * 2, 16), int(h[1] * 2, 16), int(h[2] * 2, 16)
    return None


def sample_region_luminance(png: bytes, box: Dict[str, float]) -> Optional[Tuple[int, int, int]]:
    """Mean colour of the screenshot inside ``box`` ({x, y, width, height})."""
    try:
        from PIL import Image
    except Exception:
        return None
    try:
        with Image.open(io.BytesIO(png)) as img:
            rgb = img.convert("RGB")
            x0 = max(0, int(box.get("x", 0)))
            y0 = max(0, int(box.get("y", 0)))
            x1 = min(rgb.width, int(box.get("x", 0) + box.get("width", 0)))
            y1 = min(rgb.height, int(box.get("y", 0) + box.get("height", 0)))
            if x1 <= x0 or y1 <= y0:
                return None
            region = rgb.crop((x0, y0, x1, y1))
            region.thumbnail((48, 48))
            pixels = list(region.getdata())
            n = len(pixels)
            return tuple(int(sum(p[i] for p in pixels) / n) for i in range(3))  # type: ignore[return-value]
    except Exception:
        return None


HERO_PANEL_CSS = (
    "{background:rgba(0,0,0,.58)!important;color:#fff!important;padding:clamp(1rem,3vw,2rem)!important;"
    "border-radius:1rem;backdrop-filter:blur(2px);display:inline-block;max-width:min(100%,42rem)}"
    " {path} *{color:#fff!important}"
)


def hero_readability_repair(html: str, png: Optional[bytes], measured: Dict[str, Any], report: Optional[HierarchyReport] = None) -> Tuple[str, HierarchyReport]:
    """Measure the hero text's background on the screenshot; below 4.5:1,
    put a solid panel behind the text column (by CSS path)."""
    report = report or HierarchyReport()
    hero = (measured or {}).get("heroText") or {}
    box, path, colour = hero.get("box"), hero.get("path"), hero.get("color")
    if not (png and box and path):
        return html, report
    text_rgb = parse_css_color(colour or "") or (255, 255, 255)
    bg_rgb = sample_region_luminance(png, box)
    if bg_rgb is None:
        return html, report
    ratio = round(contrast(text_rgb, bg_rgb), 2)
    report.hero_contrast = ratio
    if ratio >= HERO_MIN_CONTRAST:
        return html, report
    css = path + HERO_PANEL_CSS.replace("{path}", path)
    report.hero_panel = True
    report.css_rules.append(css)
    report.notes.append(f"hero text contrast {ratio}:1 on the image — panel added behind {path}")
    return _inject_css(html, css), report


def remove_duplicate_hero_image(html: str, report: Optional[HierarchyReport] = None) -> Tuple[str, HierarchyReport]:
    """One hero image: a background photo plus an inset <img> of the same
    file inside the hero loses the inset."""
    report = report or HierarchyReport()
    m = _HERO_RE.search(html or "")
    if not m:
        return html, report
    # Hero block = from the open tag to the next top-level section.
    end = re.search(r"</(section|header)>", html[m.end():], re.IGNORECASE)
    stop = m.end() + (end.end() if end else 0)
    block = html[m.start():stop]
    bg = _BG_URL_RE.search(block)
    if not bg:
        return html, report
    bg_url = bg.group(2).split("?")[0].rsplit("/", 1)[-1]
    new_block = block
    for im in list(_IMG_RE.finditer(block)):
        src = im.group(1).split("?")[0].rsplit("/", 1)[-1]
        if src == bg_url:
            new_block = new_block.replace(im.group(0), "", 1)
            report.inset_removed = True
            report.notes.append("inset hero photo duplicating the background removed")
            break
    if new_block == block:
        return html, report
    return html[: m.start()] + new_block + html[stop:], report


# ---------------------------------------------------------------------------
# §C12 CTA de-duplication
# ---------------------------------------------------------------------------

def _cta_text(inner: str) -> str:
    return re.sub(r"\s+", " ", _TAG_RE.sub(" ", inner)).strip().lower()


def dedupe_ctas(html: str, report: Optional[HierarchyReport] = None) -> Tuple[str, HierarchyReport]:
    """Nav = primary action, hero = primary + secondary, no third repeat:
    an anchor whose text already appears in the nav and the hero is removed
    from the rest of the page."""
    report = report or HierarchyReport()
    if not html:
        return html, report
    nav = _NAV_RE.search(html)
    hero = _HERO_RE.search(html)
    nav_span = (nav.start(), nav.end()) if nav else (0, 0)
    hero_end = None
    if hero:
        end = re.search(r"</(section|header)>", html[hero.end():], re.IGNORECASE)
        hero_end = hero.end() + (end.end() if end else 0)
    hero_span = (hero.start(), hero_end) if hero and hero_end else (0, 0)
    nav_texts = {_cta_text(m.group(1)) for m in _CTA_RE.finditer(html[nav_span[0]:nav_span[1]])} if nav else set()
    hero_texts = {_cta_text(m.group(1)) for m in _CTA_RE.finditer(html[hero_span[0]:hero_span[1]])} if hero else set()
    repeated = {t for t in nav_texts & hero_texts if t and len(t) > 2}
    if not repeated:
        return html, report
    out = html
    # Remove later occurrences (outside nav + hero) from the end backwards.
    for m in reversed(list(_CTA_RE.finditer(html))):
        if nav_span[0] <= m.start() < nav_span[1] or hero_span[0] <= m.start() < hero_span[1]:
            continue
        # Footer navigation is allowed to repeat links.
        if re.search(r"<footer\b", html[: m.start()], re.IGNORECASE) and not re.search(r"</footer>", html[: m.start()], re.IGNORECASE):
            continue
        if _cta_text(m.group(1)) in repeated:
            out = out[: m.start()] + out[m.end():]
            report.ctas_removed += 1
    if report.ctas_removed:
        report.notes.append(f"removed {report.ctas_removed} third-repeat CTA(s): {sorted(repeated)}")
    return out, report


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def apply_hierarchy_repairs(
    html: str,
    *,
    measured: Optional[Dict[str, Any]] = None,
    hero_png: Optional[bytes] = None,
    body_px: float = 16.0,
) -> Tuple[str, HierarchyReport]:
    """All of §C9–§C12 in one pass: static repairs always; measured repairs
    and the hero panel when a render is available."""
    report = HierarchyReport()
    out, report = static_type_repairs(html, report)
    out, report = remove_duplicate_hero_image(out, report)
    out, report = dedupe_ctas(out, report)
    if measured:
        out, report = measured_type_repairs(out, measured, report)
        out, report = hero_readability_repair(out, hero_png, measured, report)
    else:
        css = hierarchy_css(body_px)
        report.css_rules.append(css)
        out = _inject_css(out, css)
    return out, report
