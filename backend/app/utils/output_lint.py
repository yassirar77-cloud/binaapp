"""Design/compliance lint for generated website HTML (M0 quality harness).

Pure functions, no I/O, no LLM. Used by:
  - backend/tests/test_output_lint.py (CI gate over docs/previews and fixtures)
  - backend/scripts/generate_golden_set.py (per-output lint report in meta.json)
  - app.services.recipe_pipeline (brief-level + output-level compliance gate)

Checks:
  - Forbidden wording (Trade Descriptions Act 2011): "Halal Certified",
    "Sijil Halal", "JAKIM" must never appear — "Pengusaha Muslim" only.
  - Structural output contract: doctype, <html lang>, </body> present
    (widget injectors splice before </body>), balanced tags
    (publish rejects unbalanced HTML with 422).
  - Language purity: BM pages must not carry the default English nav
    labels and vice versa (conservative, nav-label based).
  - Token contrast: WCAG relative-luminance ratio between the page's
    --color-text and --color-background custom properties (hex only).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from app.utils.html_balance import is_html_balanced

# ---------------------------------------------------------------------------
# Forbidden wording (case-insensitive). "Pengusaha Muslim" is the only
# permitted phrasing; these must never reach a published page.
# ---------------------------------------------------------------------------
FORBIDDEN_PHRASES: Tuple[str, ...] = (
    "halal certified",
    "sijil halal",
    "jakim",
    "certified halal",
    "100% halal",
)

# Nav labels used to detect the wrong language leaking into the chrome of a
# page. Deliberately conservative: body copy can legitimately mix languages
# (dish names, "WhatsApp", brand words) so we only flag nav-level defaults.
_EN_NAV_LABELS = ("Home", "About Us", "Contact Us", "Opening Hours", "Our Menu")
_MS_NAV_LABELS = ("Laman Utama", "Tentang Kami", "Hubungi Kami", "Waktu Operasi")

_LANG_ATTR_RE = re.compile(r"<html[^>]*\blang\s*=\s*[\"']([a-zA-Z-]+)[\"']", re.IGNORECASE)
_ROOT_VAR_RE = re.compile(r"--([a-z0-9-]+)\s*:\s*(#[0-9a-fA-F]{3,8})\b")
_CLOSING_BODY_RE = re.compile(r"</\s*body\s*>", re.IGNORECASE)
_DOCTYPE_RE = re.compile(r"<!DOCTYPE\s+html", re.IGNORECASE)


@dataclass
class LintReport:
    issues: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.issues

    def as_dict(self) -> dict:
        return {"ok": self.ok, "issues": self.issues, "warnings": self.warnings}


def find_forbidden_wording(text: str) -> List[str]:
    """Return the forbidden phrases present in *text* (case-insensitive)."""
    lowered = text.lower()
    return [p for p in FORBIDDEN_PHRASES if p in lowered]


def find_language_leakage(html: str, language: str) -> List[str]:
    """Flag default nav labels from the wrong language.

    Only inspects anchor/button text so legitimate mixed-language body copy
    (dish names, testimonials) never trips it.
    """
    labels = _MS_NAV_LABELS if language == "en" else _EN_NAV_LABELS
    if language not in ("ms", "en"):
        return []
    hits = []
    # Anchor/button inner text only.
    inner_texts = re.findall(r"<(?:a|button)\b[^>]*>(.*?)</(?:a|button)>", html, re.DOTALL | re.IGNORECASE)
    joined = " ".join(re.sub(r"<[^>]+>", " ", t) for t in inner_texts)
    for label in labels:
        if re.search(rf"\b{re.escape(label)}\b", joined):
            hits.append(label)
    return hits


def _relative_luminance(hex_color: str) -> Optional[float]:
    """WCAG relative luminance of a #rgb/#rrggbb hex color. None if unparsable."""
    h = hex_color.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    if len(h) not in (6, 8):
        return None
    try:
        r, g, b = (int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4))
    except ValueError:
        return None

    def chan(c: float) -> float:
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    return 0.2126 * chan(r) + 0.7152 * chan(g) + 0.0722 * chan(b)


def contrast_ratio(hex_a: str, hex_b: str) -> Optional[float]:
    """WCAG contrast ratio between two hex colors (>= 1.0), None if unparsable."""
    la, lb = _relative_luminance(hex_a), _relative_luminance(hex_b)
    if la is None or lb is None:
        return None
    lighter, darker = max(la, lb), min(la, lb)
    return (lighter + 0.05) / (darker + 0.05)


def extract_root_hex_vars(html: str) -> dict:
    """Extract `--name: #hex` custom properties from the document."""
    return {name: value for name, value in _ROOT_VAR_RE.findall(html)}


def lint_html(
    html: str,
    language: Optional[str] = None,
    require_website_id: bool = False,
    min_text_contrast: float = 4.5,
) -> LintReport:
    """Run every check against a generated HTML document."""
    report = LintReport()

    if not html or not html.strip():
        report.issues.append("empty HTML")
        return report

    for phrase in find_forbidden_wording(html):
        report.issues.append(f"forbidden wording present: {phrase!r} (use 'Pengusaha Muslim')")

    if not _DOCTYPE_RE.search(html):
        report.issues.append("missing <!DOCTYPE html>")

    if not _CLOSING_BODY_RE.search(html):
        report.issues.append("missing </body> (widget injection point)")

    balanced, unclosed = is_html_balanced(html)
    if not balanced:
        report.issues.append(f"unbalanced HTML (publish would 422): unclosed {unclosed}")

    lang_match = _LANG_ATTR_RE.search(html)
    if not lang_match:
        report.warnings.append("missing lang attribute on <html>")
    elif language and lang_match.group(1).lower().split("-")[0] != language:
        report.issues.append(
            f"lang attribute {lang_match.group(1)!r} does not match requested language {language!r}"
        )

    if language:
        for label in find_language_leakage(html, language):
            report.issues.append(f"wrong-language nav label for {language} page: {label!r}")

    if require_website_id and "data-website-id" not in html:
        report.issues.append("missing data-website-id marker (draft promotion / widget targeting)")

    root_vars = extract_root_hex_vars(html)
    text_c, bg_c = root_vars.get("color-text"), root_vars.get("color-background")
    if text_c and bg_c:
        ratio = contrast_ratio(text_c, bg_c)
        if ratio is not None and ratio < min_text_contrast:
            report.issues.append(
                f"text/background contrast {ratio:.2f} below WCAG {min_text_contrast}:1 "
                f"({text_c} on {bg_c})"
            )

    return report
