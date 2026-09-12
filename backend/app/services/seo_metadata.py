"""Deterministic SEO / social metadata for generated sites.

Malaysian SMEs share their site by pasting the link into WhatsApp. Without
Open Graph tags that paste renders as a bare URL — no title, no photo — which
is a hard conversion loss on the single channel that matters most here.
Generated pages carried none, and no JSON-LD either, so they were invisible
to local search.

Asking the model for these tags is unreliable (it is already carrying a long
rule list, and a dropped meta tag is silent). This module emits them
deterministically instead, from data the pipeline already has.

Pure function of (html, meta) -> html. Idempotent: re-running never
duplicates a tag, so it is safe on the template path, the AI path, and on
re-publish of an already-processed page.

NOTHING here is invented. Every field is derived from merchant-supplied data
or omitted — a JSON-LD block asserting a fake address or price range would be
the same defect this pipeline was just fixed for, in a machine-readable form
search engines actually trust.
"""

from __future__ import annotations

import html as _html
import json
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

# Business types that are restaurants in schema.org terms.
_FOOD_TYPES = frozenset({"food", "cafe", "bakery", "restaurant"})

_SCHEMA_TYPE_BY_BUSINESS = {
    "food": "Restaurant",
    "cafe": "CafeOrCoffeeShop",
    "bakery": "Bakery",
    "restaurant": "Restaurant",
    "salon": "BeautySalon",
    "clinic": "MedicalClinic",
    "gym": "ExerciseGym",
    "clothing": "ClothingStore",
    "services": "LocalBusiness",
    "general": "LocalBusiness",
}

#: schema.org day names, keyed by lowercase Malay/English tokens.
_DAY_TOKENS = {
    "isnin": "Monday", "monday": "Monday", "mon": "Monday",
    "selasa": "Tuesday", "tuesday": "Tuesday", "tue": "Tuesday",
    "rabu": "Wednesday", "wednesday": "Wednesday", "wed": "Wednesday",
    "khamis": "Thursday", "thursday": "Thursday", "thu": "Thursday",
    "jumaat": "Friday", "friday": "Friday", "fri": "Friday",
    "sabtu": "Saturday", "saturday": "Saturday", "sat": "Saturday",
    "ahad": "Sunday", "minggu": "Sunday", "sunday": "Sunday", "sun": "Sunday",
}
_DAY_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday",
              "Friday", "Saturday", "Sunday"]

_TIME_RE = re.compile(r"(\d{1,2})[:.](\d{2})\s*(am|pm|pagi|petang|malam|tgh)?", re.IGNORECASE)


@dataclass
class SeoMeta:
    """Everything the metadata block can be built from. All optional."""
    business_name: str = ""
    description: str = ""
    subdomain: str = ""
    site_url: str = ""
    hero_image: str = ""
    address: str = ""
    phone: str = ""
    language: str = "ms"
    business_type: str = "general"
    menu_items: List[Dict[str, str]] = field(default_factory=list)
    operating_hours: List[Any] = field(default_factory=list)


def _esc(value: str) -> str:
    """Escape for an HTML attribute value."""
    return _html.escape(str(value or ""), quote=True)


def _clean(text: str, limit: int) -> str:
    flat = re.sub(r"\s+", " ", str(text or "")).strip()
    if len(flat) <= limit:
        return flat
    # Cut on a word boundary so the description never ends mid-word.
    cut = flat[:limit].rsplit(" ", 1)[0].rstrip(",;:-")
    return cut


#: Google truncates around 155-160 characters; 155 leaves room for the
#: ellipsis without the snippet being cut a second time in the SERP.
META_DESCRIPTION_LIMIT = 155

#: How much of the budget a sentence break has to fill before it beats a
#: word break. Below this the sentence cut throws away too much of the
#: description to be worth the tidier ending.
_SENTENCE_MIN_RATIO = 0.6

_SENTENCE_END_RE = re.compile(r"[.!?](?:\s|$)")


def meta_description(text: str, limit: int = META_DESCRIPTION_LIMIT) -> str:
    """A description that ends somewhere a reader would stop.

    ``_clean`` cuts on a word boundary, which is why the reported page's
    description ended

        "...customer datang jauh dari Klang dan KL khas untuk"

    — a complete word and a severed sentence. This prefers the last SENTENCE
    boundary inside the budget, falls back to the last word boundary with a
    trailing ellipsis, and returns short text untouched.
    """
    flat = re.sub(r"\s+", " ", str(text or "")).strip()
    if not flat or len(flat) <= limit:
        return flat

    window = flat[:limit]
    ends = [m.end() for m in _SENTENCE_END_RE.finditer(window)]
    if ends and ends[-1] >= limit * _SENTENCE_MIN_RATIO:
        return window[:ends[-1]].strip()

    cut = window.rsplit(" ", 1)[0].rstrip(" ,;:-–—")
    if not cut:
        return window
    # A cut that already lands on a full stop needs no ellipsis after it.
    return cut if cut[-1] in ".!?" else f"{cut}…"


def _to_24h(raw: str) -> Optional[str]:
    """'2:30 petang' -> '14:30'. None when unparseable (never guessed)."""
    m = _TIME_RE.search(raw or "")
    if not m:
        return None
    hour, minute, marker = int(m.group(1)), int(m.group(2)), (m.group(3) or "").lower()
    if hour > 23 or minute > 59:
        return None
    if marker in ("pm", "petang", "malam") and hour < 12:
        hour += 12
    elif marker in ("am", "pagi") and hour == 12:
        hour = 0
    elif marker == "tgh" and hour < 12:
        hour += 12
    return f"{hour:02d}:{minute:02d}"


def _days_from_label(label: str) -> List[str]:
    """'Isnin - Khamis' -> [Monday..Thursday]. Unknown labels -> []."""
    text = (label or "").lower()
    found = [(text.index(tok), day) for tok, day in _DAY_TOKENS.items() if tok in text]
    if not found:
        return []
    found.sort()
    days = []
    for _, day in found:
        if day not in days:
            days.append(day)
    # A range ("Isnin - Khamis") is exactly two endpoints with a dash between.
    if len(days) == 2 and re.search(r"[-–—]|hingga|sampai|to\b", text):
        start, end = _DAY_ORDER.index(days[0]), _DAY_ORDER.index(days[1])
        if start <= end:
            return _DAY_ORDER[start:end + 1]
    return days


def _opening_hours_spec(operating_hours: List[Any]) -> List[Dict[str, Any]]:
    """schema.org openingHoursSpecification from structured hours.

    Emits one entry per (day-range, time-range) pair, so a Friday split
    produces TWO entries — the whole point of the P1-2 hours work. Anything
    unparseable is skipped rather than guessed.
    """
    spec: List[Dict[str, Any]] = []
    for entry in (operating_hours or []):
        if not isinstance(entry, dict):
            continue
        days = _days_from_label(entry.get("days") or entry.get("day") or "")
        if not days:
            continue
        raw_hours = entry.get("hours", entry.get("time", ""))
        ranges: List[str] = []
        if isinstance(raw_hours, str):
            ranges = [raw_hours]
        elif isinstance(raw_hours, (list, tuple)):
            for item in raw_hours:
                if isinstance(item, str):
                    ranges.append(item)
                elif isinstance(item, dict):
                    ranges.append(f"{item.get('open', '')} - {item.get('close', '')}")
        for rng in ranges:
            parts = re.split(r"\s*[-–—]\s*|\s+hingga\s+|\s+to\s+", rng.strip())
            if len(parts) != 2:
                continue
            opens, closes = _to_24h(parts[0]), _to_24h(parts[1])
            if not opens or not closes:
                continue
            spec.append({
                "@type": "OpeningHoursSpecification",
                "dayOfWeek": days,
                "opens": opens,
                "closes": closes,
            })
    return spec


#: "buka 24 jam", "24/7", "open 24 hours" — an explicit always-open claim.
#: The reported restaurant said so in its own brief and the JSON-LD node
#: carried no openingHours at all, which is the single richest local-SEO
#: field a 24-hour restaurant has.
_ALWAYS_OPEN_RE = re.compile(
    r"\b24\s*(?:jam|hours?|hrs?)\b|\b24\s*/\s*7\b|\bopen\s+24\b|\bbuka\s+24\b",
    re.IGNORECASE,
)

#: Every day, midnight to one minute before it. schema.org has no "always
#: open" flag; Mo-Su 00:00-23:59 is the encoding Google documents.
ALWAYS_OPEN_SPEC = {
    "@type": "OpeningHoursSpecification",
    "dayOfWeek": list(_DAY_ORDER),
    "opens": "00:00",
    "closes": "23:59",
}


def is_always_open(text: str) -> bool:
    """True when the merchant's own words say the business never closes."""
    return bool(_ALWAYS_OPEN_RE.search(str(text or "")))


def _price_value(raw: str) -> Optional[str]:
    """'RM12.50' -> '12.50'. None when there is no number to publish."""
    match = re.search(r"(\d+(?:[.,]\d{1,2})?)", str(raw or ""))
    if not match:
        return None
    return match.group(1).replace(",", ".")


def _menu_node(menu_items: List[Dict[str, str]]) -> Optional[Dict[str, Any]]:
    """A schema.org Menu built from the merchant's OWN items.

    Grouped into MenuSections when they supplied categories, flat otherwise.
    Prices become Offers only when they parse to a number — a MenuItem with
    an invented price is the same defect as an invented dish.
    """
    items = [i for i in (menu_items or []) if (i or {}).get("name")]
    if not items:
        return None

    def _item(entry: Dict[str, str]) -> Dict[str, Any]:
        node: Dict[str, Any] = {"@type": "MenuItem", "name": str(entry["name"]).strip()}
        if entry.get("description"):
            node["description"] = _clean(str(entry["description"]), 200)
        price = _price_value(entry.get("price", ""))
        if price:
            node["offers"] = {
                "@type": "Offer", "price": price, "priceCurrency": "MYR",
            }
        return node

    sections: Dict[str, List[Dict[str, Any]]] = {}
    for entry in items:
        sections.setdefault(str(entry.get("category") or "").strip(), []).append(_item(entry))

    if len(sections) == 1 and "" in sections:
        return {"@type": "Menu", "hasMenuItem": sections[""]}
    return {
        "@type": "Menu",
        "hasMenuSection": [
            {
                "@type": "MenuSection",
                **({"name": name} if name else {}),
                "hasMenuItem": entries,
            }
            for name, entries in sections.items()
        ],
    }


def _price_range(menu_items: List[Dict[str, str]]) -> str:
    """'RM4 - RM42' from supplied prices. '' when none are numeric."""
    values: List[float] = []
    for item in (menu_items or []):
        price = str((item or {}).get("price") or "")
        for match in re.finditer(r"(\d+(?:[.,]\d{1,2})?)", price):
            try:
                values.append(float(match.group(1).replace(",", ".")))
            except ValueError:
                continue
    if not values:
        return ""
    low, high = min(values), max(values)

    def _fmt(v: float) -> str:
        return f"RM{int(v)}" if float(v).is_integer() else f"RM{v:.2f}"

    return _fmt(low) if low == high else f"{_fmt(low)} - {_fmt(high)}"


def build_json_ld(meta: SeoMeta) -> Optional[Dict[str, Any]]:
    """schema.org node for the business, or None without enough real data."""
    if not meta.business_name:
        return None

    schema_type = _SCHEMA_TYPE_BY_BUSINESS.get(
        (meta.business_type or "general").lower(), "LocalBusiness"
    )
    node: Dict[str, Any] = {
        "@context": "https://schema.org",
        "@type": schema_type,
        "name": meta.business_name,
    }
    if meta.description:
        node["description"] = _clean(meta.description, 300)
    if meta.site_url:
        node["url"] = meta.site_url
    if meta.hero_image:
        node["image"] = meta.hero_image
    if meta.phone:
        node["telephone"] = meta.phone
    if meta.address:
        node["address"] = {
            "@type": "PostalAddress",
            "streetAddress": meta.address,
            "addressCountry": "MY",
        }
    if (meta.business_type or "").lower() in _FOOD_TYPES:
        node["servesCuisine"] = "Malaysian"
    price = _price_range(meta.menu_items)
    if price:
        node["priceRange"] = price
    hours = _opening_hours_spec(meta.operating_hours)
    if not hours and is_always_open(meta.description):
        hours = [dict(ALWAYS_OPEN_SPEC)]
    if hours:
        node["openingHoursSpecification"] = hours

    # A restaurant's menu is the richest local result it can earn, and the
    # items are the merchant's own — nothing is invented by publishing them.
    if (meta.business_type or "").lower() in _FOOD_TYPES:
        menu = _menu_node(meta.menu_items)
        if menu:
            node["hasMenu"] = menu

    return node


def build_meta_tags(meta: SeoMeta) -> str:
    """The OG/Twitter/description block. Only tags backed by real data."""
    title = meta.business_name
    desc = meta_description(meta.description)

    tags: List[str] = []
    if desc:
        tags.append(f'<meta name="description" content="{_esc(desc)}">')
    if title:
        tags.append(f'<meta property="og:title" content="{_esc(title)}">')
        tags.append(f'<meta property="og:site_name" content="{_esc(title)}">')
    if desc:
        tags.append(f'<meta property="og:description" content="{_esc(desc)}">')
    if meta.hero_image:
        tags.append(f'<meta property="og:image" content="{_esc(meta.hero_image)}">')
    if meta.site_url:
        tags.append(f'<meta property="og:url" content="{_esc(meta.site_url)}">')
    tags.append('<meta property="og:type" content="website">')
    tags.append(
        f'<meta property="og:locale" content='
        f'"{"ms_MY" if str(meta.language or "ms").startswith("ms") else "en_MY"}">'
    )
    # summary_large_image only when there IS an image to show.
    tags.append(
        f'<meta name="twitter:card" content='
        f'"{"summary_large_image" if meta.hero_image else "summary"}">'
    )
    if title:
        tags.append(f'<meta name="twitter:title" content="{_esc(title)}">')
    if desc:
        tags.append(f'<meta name="twitter:description" content="{_esc(desc)}">')
    if meta.hero_image:
        tags.append(f'<meta name="twitter:image" content="{_esc(meta.hero_image)}">')
    return "\n".join(tags)


def inject_seo_metadata(html: str, meta: SeoMeta) -> str:
    """Add title/description/OG/JSON-LD to the page head.

    Idempotent — a tag already present is never duplicated, and an existing
    non-empty <title> is left alone (the model may have written a better one).
    Returns the html unchanged when there is no head to inject into.
    """
    if not html or not html.strip():
        return html

    lowered = html.lower()
    additions: List[str] = []

    # <title> only when missing or empty.
    title_match = re.search(r"<title\b[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
    if meta.business_name and (not title_match or not title_match.group(1).strip()):
        page_title = meta.business_name
        tagline = _clean(meta.description, 60)
        if tagline:
            page_title = f"{meta.business_name} | {tagline}"
        if title_match:
            html = html[:title_match.start()] + html[title_match.end():]
            lowered = html.lower()
        additions.append(f"<title>{_esc(page_title)}</title>")

    for tag in build_meta_tags(meta).split("\n"):
        if not tag.strip():
            continue
        key = re.search(r'(?:property|name)="([^"]+)"', tag)
        if key and f'"{key.group(1)}"' in html:
            continue  # already present — never duplicate
        additions.append(tag)

    if "application/ld+json" not in lowered:
        node = build_json_ld(meta)
        if node:
            additions.append(
                '<script type="application/ld+json">'
                + json.dumps(node, ensure_ascii=False, separators=(",", ":"))
                + "</script>"
            )

    if not additions:
        return html

    block = "\n" + "\n".join(additions) + "\n"
    # Prefer </head>; fall back to after <head>, then before <body>, then top.
    for pattern, position in (
        (re.compile(r"</head\s*>", re.IGNORECASE), "before"),
        (re.compile(r"<head\b[^>]*>", re.IGNORECASE), "after"),
        (re.compile(r"<body\b[^>]*>", re.IGNORECASE), "before"),
    ):
        match = pattern.search(html)
        if match:
            idx = match.start() if position == "before" else match.end()
            return html[:idx] + block + html[idx:]
    return block + html


# ---------------------------------------------------------------------------
# Publish-time finalisation
# ---------------------------------------------------------------------------
#
# Everything above runs at GENERATION time, when the site has no address yet:
# ai_service passes subdomain="preview", so the page is built carrying
#
#     <meta property="og:url" content="https://preview.binaapp.my">
#     "url":"https://preview.binaapp.my"      (JSON-LD)
#
# and no <link rel="canonical"> at all. Published to oopoo.binaapp.my, that
# page tells WhatsApp, Facebook and Google that it lives somewhere else — so
# a merchant sharing their own link unfurls a generic preview page.
#
# The real host is only known at publish. These functions rewrite it there,
# idempotently, so a republish neither duplicates nor re-breaks anything.

_PREVIEW_URL_RE = re.compile(r"https?://preview\.binaapp\.my[^\"'\s<]*", re.IGNORECASE)
_CANONICAL_RE = re.compile(
    r"""<link\b[^>]*rel\s*=\s*["']canonical["'][^>]*>""", re.IGNORECASE
)
_OG_URL_RE = re.compile(
    r"""(<meta\b[^>]*property\s*=\s*["']og:url["'][^>]*content\s*=\s*["'])([^"']*)(["'])""",
    re.IGNORECASE,
)
_LD_JSON_RE = re.compile(
    r"""(<script\b[^>]*type\s*=\s*["']application/ld\+json["'][^>]*>)(.*?)(</script>)""",
    re.IGNORECASE | re.DOTALL,
)
_THEME_COLOR_RE = re.compile(
    r"""<meta\b[^>]*name\s*=\s*["']theme-color["'][^>]*>""", re.IGNORECASE
)
_ICON_RE = re.compile(
    r"""<link\b[^>]*rel\s*=\s*["'][^"']*\bicon\b[^"']*["'][^>]*>""", re.IGNORECASE
)
_PRIMARY_COLOR_RE = re.compile(
    r"--(?:primary-color|color-primary|brand-color|primary)\s*:\s*"
    r"(#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6}))\b"
)


def favicon_data_uri(business_name: str, color: str = "#111827") -> str:
    """A letter-mark favicon as an inline SVG data URI.

    Generated pages shipped with no favicon at all, so every tab and every
    bookmark showed the browser's blank-document glyph. An SVG data URI needs
    no hosting, no extra request, and survives being copied between hosts.
    """
    letter = next((c for c in str(business_name or "") if c.isalnum()), "•").upper()
    svg = (
        "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'>"
        f"<rect width='64' height='64' rx='14' fill='{color}'/>"
        "<text x='32' y='44' font-family='system-ui,sans-serif' font-size='36' "
        f"font-weight='700' fill='#ffffff' text-anchor='middle'>{_html.escape(letter)}</text>"
        "</svg>"
    )
    from urllib.parse import quote

    return "data:image/svg+xml;charset=utf-8," + quote(svg, safe="")


def page_primary_color(html: str) -> str:
    """The page's brand colour, for <meta name="theme-color">."""
    match = _PRIMARY_COLOR_RE.search(html or "")
    return match.group(1) if match else "#111827"


def finalize_published_seo(
    html: str,
    site_url: str,
    business_name: str = "",
    geo: Optional[Dict[str, float]] = None,
) -> str:
    """Point a generated page's metadata at where it actually lives.

    * every ``preview.binaapp.my`` URL becomes ``site_url``
    * ``og:url`` is set (added when absent)
    * a ``<link rel="canonical">`` is added
    * the JSON-LD node's ``url`` is corrected and ``geo`` added when the
      publish step geocoded the address
    * a favicon and ``theme-color`` are added when the page has none

    Idempotent — safe on every republish.
    """
    if not html or not html.strip():
        return html
    site_url = (site_url or "").rstrip("/")
    if not site_url:
        return html

    out = _PREVIEW_URL_RE.sub(site_url, html)

    if _OG_URL_RE.search(out):
        out = _OG_URL_RE.sub(lambda m: f"{m.group(1)}{site_url}{m.group(3)}", out, count=1)
        head_additions = []
    else:
        head_additions = [f'<meta property="og:url" content="{_esc(site_url)}">']

    if not _CANONICAL_RE.search(out):
        head_additions.append(f'<link rel="canonical" href="{_esc(site_url)}">')
    if not _ICON_RE.search(out):
        icon = favicon_data_uri(business_name, page_primary_color(out))
        head_additions.append(f'<link rel="icon" href="{icon}">')
    if not _THEME_COLOR_RE.search(out):
        head_additions.append(
            f'<meta name="theme-color" content="{_esc(page_primary_color(out))}">'
        )

    def _fix_ld(match: "re.Match") -> str:
        try:
            node = json.loads(match.group(2).strip())
        except Exception:
            return match.group(0)
        nodes = node if isinstance(node, list) else [node]
        for entry in nodes:
            if not isinstance(entry, dict):
                continue
            if entry.get("@context"):
                entry["url"] = site_url
            if geo and geo.get("lat") is not None and geo.get("lng") is not None:
                entry["geo"] = {
                    "@type": "GeoCoordinates",
                    "latitude": round(float(geo["lat"]), 6),
                    "longitude": round(float(geo["lng"]), 6),
                }
        return (
            match.group(1)
            + json.dumps(node, ensure_ascii=False, separators=(",", ":"))
            + match.group(3)
        )

    out = _LD_JSON_RE.sub(_fix_ld, out)

    if head_additions:
        block = "\n" + "\n".join(head_additions) + "\n"
        if re.search(r"</head\s*>", out, re.IGNORECASE):
            out = re.sub(r"</head\s*>", block + "</head>", out, count=1, flags=re.IGNORECASE)
        elif re.search(r"<body\b[^>]*>", out, re.IGNORECASE):
            out = re.sub(r"(<body\b[^>]*>)", lambda m: m.group(1) + block, out, count=1, flags=re.IGNORECASE)
        else:
            out = block + out
    return out
