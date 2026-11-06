"""Menu fidelity — the merchant's items reach the page exactly as entered.

Ayam Gepuk Panglima entered 32 priced items and published a page with four
cards, two of them invented ("Ayam Goreng Coklat", "Ayam Goreng Keju"),
every price wrong and an empty "Seafood Krispy" section. Two things let that
happen, and this module closes both:

1. A large menu is never left to the model to transcribe. From
   ``DETERMINISTIC_MIN_ITEMS`` items up, the prompt asks for ONE empty slot
   (``<div id="binaapp-menu-slot"></div>``) inside the menu section and the
   items are rendered into it here, grouped by the merchant's own category
   labels, with names and prices copied from the data. A 16k-token output
   cap cannot truncate a list the model never writes.

2. Whatever the model did write is reconciled against the data afterwards
   (``reconcile_menu``): a card whose name is not a supplied item is removed,
   a card carrying the wrong price gets the supplied price, a supplied item
   missing from the page is injected into the menu section. Every correction
   is logged; more than ``SEVERE_CORRECTION_RATIO`` of the items needing one
   is logged as an error so the run is visible in the job diagnostics.

Pure string/BeautifulSoup transforms on the MENU SECTION ONLY — the rest of
the document is never re-serialised. No I/O.
"""

from __future__ import annotations

import html as _html
import os
import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple
from urllib.parse import quote

from bs4 import BeautifulSoup, Tag
from loguru import logger

from app.services.data_consistency import format_price

MENU_SLOT_ID = "binaapp-menu-slot"
MENU_BLOCK_CLASS = "binaapp-menu-block"

#: From this many supplied items up, the menu section is rendered here, not
#: by the model. Nine is the designer plan's own featured-tile cap: below it
#: the model lays out a handful of tiles well; above it, it drops, merges and
#: re-prices items (32 in → 4 out on ayamgepukpaglima).
DETERMINISTIC_MIN_ITEMS = int(os.getenv("MENU_DETERMINISTIC_MIN_ITEMS", "9"))

#: Share of supplied items that may need a correction before the run is
#: logged as an error (the page still ships — corrected).
SEVERE_CORRECTION_RATIO = 0.20

_PRICE_RE = re.compile(r"RM\s?\d[\d,]*(?:\.\d{1,2})?", re.IGNORECASE)
_SECTION_OPEN_RE = re.compile(r"<section\b[^>]*>", re.IGNORECASE)
_SECTION_ANY_RE = re.compile(r"<(/?)section\b[^>]*>", re.IGNORECASE)
_ID_RE = re.compile(r"\bid\s*=\s*[\"']([^\"']+)[\"']", re.IGNORECASE)
_MENU_ID_WORDS = ("menu", "produk", "product", "servis", "service", "perkhidmatan", "koleksi", "harga", "price", "offer")
_CTA_WORDS = {"pesan", "order", "tempah", "beli", "whatsapp", "add", "tambah", "pesan sekarang", "order now", "book"}
_UNCATEGORISED = {"ms": "Lain-lain", "en": "Others"}
_SIGNATURE_LABEL = {"ms": "SIGNATURE", "en": "SIGNATURE"}
_SIGNATURE_NAME_RE = re.compile(r"\bsignature\b", re.IGNORECASE)


def is_signature_name(name: str) -> bool:
    """An item whose own name says it is the signature dish."""
    return bool(_SIGNATURE_NAME_RE.search(str(name or "")))


# ---------------------------------------------------------------------------
# Items
# ---------------------------------------------------------------------------

@dataclass
class MenuItemSpec:
    name: str
    price: str = ""          # display form, "RM12.50" (or "" when none / prices off)
    category: str = ""
    description: str = ""
    image_url: str = ""
    signature: bool = False

    @property
    def key(self) -> str:
        return normalize_name(self.name)


def normalize_name(text: str) -> str:
    """Comparison key: case-, punctuation- and whitespace-insensitive, with
    any price fragment removed. "Set A – Ayam Gepuk" == "set a - ayam gepuk"."""
    t = _html.unescape(str(text or ""))
    t = _PRICE_RE.sub(" ", t)
    t = t.lower().replace("&", " and ")
    t = re.sub(r"[^\w\s]", " ", t, flags=re.UNICODE)
    return re.sub(r"\s+", " ", t).strip()


def normalize_items(raw: Optional[Iterable[Any]]) -> List[MenuItemSpec]:
    """Merchant rows (MenuItemInput models, dicts, DB rows or bare strings) →
    specs. Rows without a name are dropped; nothing here ever raises."""
    out: List[MenuItemSpec] = []
    seen = set()
    for entry in (raw or []):
        try:
            if isinstance(entry, MenuItemSpec):
                if entry.key and entry.key not in seen:
                    seen.add(entry.key)
                    out.append(entry)
                continue
            if hasattr(entry, "model_dump"):
                d = entry.model_dump()
            elif hasattr(entry, "dict"):
                d = entry.dict()
            elif isinstance(entry, dict):
                d = entry
            elif isinstance(entry, str):
                d = {"name": entry}
            else:
                continue
            name = re.sub(r"\s+", " ", str(d.get("name") or "")).strip()
            if not name:
                continue
            raw_price = d.get("price")
            price = ""
            if raw_price not in (None, ""):
                price = format_price(raw_price) or str(raw_price).strip()
            category = str(d.get("category") or d.get("category_name") or "").strip()
            spec = MenuItemSpec(
                name=name,
                price=price,
                category=category[:60],
                description=str(d.get("description") or "").strip()[:400],
                image_url=str(d.get("image_url") or d.get("url") or "").strip(),
                signature=bool(
                    d.get("signature") or d.get("is_signature") or d.get("is_popular") or d.get("featured")
                    or is_signature_name(name)
                ),
            )
            if spec.key in seen:
                continue
            seen.add(spec.key)
            out.append(spec)
        except Exception:
            continue
    return out


def use_deterministic_menu(items: Sequence[MenuItemSpec]) -> bool:
    return len(items) >= DETERMINISTIC_MIN_ITEMS


# ---------------------------------------------------------------------------
# Item photography
# ---------------------------------------------------------------------------

#: Categories whose items stay text-only in the menu block: drinks, kids'
#: menu, add-ons. A photo of "Air Mineral 500ml" or "Sambal Extra" spends
#: the image budget on the items a customer looks at least.
_DRINK_CAT_RE = re.compile(r"minuman|drinks?\b|beverage|\bair\b", re.IGNORECASE)
_KIDS_CAT_RE = re.compile(r"\bkids?\b|kid'?s|kanak", re.IGNORECASE)
_ADDON_CAT_RE = re.compile(r"tambahan|add[\s-]?ons?\b|\bextras?\b|sampingan|\bsides?\b", re.IGNORECASE)


def is_drink_category(category: str) -> bool:
    return bool(_DRINK_CAT_RE.search(str(category or "")))


def is_kids_category(category: str) -> bool:
    return bool(_KIDS_CAT_RE.search(str(category or "")))


def is_addon_category(category: str) -> bool:
    return bool(_ADDON_CAT_RE.search(str(category or "")))


def text_only_category(category: str) -> bool:
    """Drinks, kids' menu and add-ons render without a photo."""
    return is_drink_category(category) or is_kids_category(category) or is_addon_category(category)


def _price_value(price: str) -> Optional[float]:
    try:
        return float(_price_key(price)) if price else None
    except ValueError:
        return None


def image_priority(items: Sequence[MenuItemSpec]) -> List[MenuItemSpec]:
    """Items that may carry a photo, most deserving first.

    Drinks, kids' items and add-ons are excluded (unless the whole menu is
    such items — a drinks-only kiosk still gets photos). Among the rest:
    signature items, then items in the first category, then "Set" items,
    then items priced above the median; menu order breaks ties."""
    items = list(items)
    eligible = [it for it in items if not text_only_category(it.category)] or items
    if not eligible:
        return []
    first_cat = next((it.category for it in eligible if it.category), "")
    values = sorted(v for v in (_price_value(it.price) for it in items) if v is not None)
    median = values[len(values) // 2] if values else None

    def _score(it: MenuItemSpec) -> int:
        score = 0
        if it.signature:
            score += 8
        if first_cat and it.category == first_cat:
            score += 4
        if re.match(r"\s*set\b", it.name, re.IGNORECASE):
            score += 2
        v = _price_value(it.price)
        if median is not None and v is not None and v > median:
            score += 1
        return score

    order = {id(it): i for i, it in enumerate(eligible)}
    return sorted(eligible, key=lambda it: (-_score(it), order[id(it)]))


def attach_item_images(
    items: Sequence[MenuItemSpec],
    images: Iterable[Tuple[str, str]],
    *,
    budget: Optional[int] = None,
) -> Tuple[List[MenuItemSpec], int]:
    """Give items the photos generated or uploaded for them.

    ``images`` is (item name, url) pairs — the auto-fill's gallery slots and
    named uploads. A photo goes to the supplied item its name matches, only
    when that item is eligible (``image_priority``) and has no photo of its
    own; at most ``budget`` photos are attached. Returns new specs (inputs
    are not mutated) and how many photos were attached."""
    from dataclasses import replace as _replace
    out = list(items)
    eligible = {it.key for it in image_priority(out)}
    index = {it.key: i for i, it in enumerate(out)}
    attached = 0
    for name, url in images:
        if budget is not None and attached >= budget:
            break
        url = str(url or "").strip()
        if not name or not url.startswith(("http://", "https://", "/")):
            continue
        it = match_item(name, out)
        if it is None or it.key not in eligible or it.image_url:
            continue
        out[index[it.key]] = _replace(it, image_url=url)
        attached += 1
    return out, attached


# ---------------------------------------------------------------------------
# Deterministic render
# ---------------------------------------------------------------------------

_BLOCK_CSS = """
<style id="binaapp-menu-block-css">
.binaapp-menu-block{--bmf-primary:var(--primary-color,#B91C1C);--bmf-accent:var(--accent-color,var(--primary-color,#B91C1C));--bmf-surface:var(--surface-color,#FFFFFF);--bmf-text:var(--text-color,#1C1917);--bmf-muted:var(--text-muted,rgba(28,25,23,.72));}
.binaapp-menu-block .bmf-cat{margin:2.5rem 0 1rem;text-align:center}
.binaapp-menu-block .bmf-cat:first-child{margin-top:0}
.binaapp-menu-block .bmf-cat h3{font-family:var(--font-heading,inherit);font-size:clamp(1.35rem,2.6vw,1.9rem);line-height:1.2;margin:0;color:var(--bmf-text)}
.binaapp-menu-block .bmf-cat .bmf-rule{width:3rem;height:3px;margin:.65rem auto 0;background:var(--bmf-accent);border-radius:999px}
.binaapp-menu-block .bmf-grid{display:flex;flex-wrap:wrap;justify-content:center;gap:1rem;list-style:none;margin:0;padding:0}
.binaapp-menu-block .bmf-card{position:relative;display:flex;flex-direction:column;width:100%;max-width:24rem;min-height:100%;background:var(--bmf-surface);color:var(--bmf-text);border:1px solid rgba(0,0,0,.08);border-radius:1rem;overflow:hidden;box-shadow:0 6px 24px rgba(0,0,0,.06)}
@media (min-width:640px){.binaapp-menu-block .bmf-card{width:calc(50% - .5rem)}}
@media (min-width:1024px){.binaapp-menu-block .bmf-card{width:calc(33.333% - .7rem)}}
.binaapp-menu-block .bmf-card img{width:100%;aspect-ratio:4/3;object-fit:cover;display:block;background:rgba(0,0,0,.05)}
.binaapp-menu-block .bmf-body{display:flex;flex-direction:column;gap:.35rem;padding:1rem 1.1rem 1.1rem;flex:1}
.binaapp-menu-block .bmf-card.bmf-text-only .bmf-body{padding-top:1.35rem;border-top:4px solid var(--bmf-accent)}
.binaapp-menu-block .bmf-name{font-family:var(--font-heading,inherit);font-size:1.1rem;font-weight:700;line-height:1.25;margin:0;color:var(--bmf-text)}
.binaapp-menu-block .bmf-desc{font-size:.92rem;line-height:1.5;margin:0;color:var(--bmf-muted)}
.binaapp-menu-block .bmf-foot{display:flex;align-items:center;justify-content:space-between;gap:.75rem;margin-top:auto;padding-top:.6rem}
.binaapp-menu-block .bmf-price{font-family:var(--font-heading,inherit);font-size:1.2rem;font-weight:800;color:var(--bmf-primary);white-space:nowrap}
.binaapp-menu-block .bmf-order{display:inline-flex;align-items:center;gap:.4rem;padding:.5rem .9rem;border-radius:999px;background:var(--bmf-primary);color:#fff;font-size:.85rem;font-weight:700;text-decoration:none;white-space:nowrap}
.binaapp-menu-block .bmf-order:hover{filter:brightness(1.08)}
.binaapp-menu-block .bmf-badge{position:absolute;top:.75rem;left:.75rem;padding:.25rem .6rem;border-radius:999px;background:var(--bmf-accent);color:#fff;font-size:.7rem;font-weight:800;letter-spacing:.06em;text-transform:uppercase}
.binaapp-menu-block .bmf-card.bmf-text-only .bmf-badge{position:static;align-self:flex-start;margin-bottom:.35rem}
.binaapp-menu-block .bmf-card.bmf-signature{border:2px solid var(--bmf-accent);box-shadow:0 0 0 4px color-mix(in srgb,var(--bmf-accent) 18%,transparent),0 10px 30px rgba(0,0,0,.10);background:color-mix(in srgb,var(--bmf-accent) 7%,var(--bmf-surface))}
.binaapp-menu-block .bmf-card.bmf-signature .bmf-badge{z-index:1;box-shadow:0 2px 8px rgba(0,0,0,.18)}
</style>
"""


def _esc(text: str) -> str:
    return _html.escape(str(text or ""), quote=True)


def _lang(language: Optional[str]) -> str:
    return "en" if str(language or "ms").lower().startswith("en") else "ms"


def order_link(wa_digits: str, prefill: str, item_name: str) -> str:
    text = f"{prefill} {item_name}".strip()
    return f"https://wa.me/{wa_digits}?text={quote(text, safe='')}"


def group_by_category(items: Sequence[MenuItemSpec]) -> List[Tuple[str, List[MenuItemSpec]]]:
    """Categories in first-seen order; uncategorised items last."""
    groups: Dict[str, List[MenuItemSpec]] = {}
    order: List[str] = []
    for it in items:
        key = it.category.strip()
        if key not in groups:
            groups[key] = []
            order.append(key)
        groups[key].append(it)
    named = [(k, groups[k]) for k in order if k]
    if "" in groups:
        named.append(("", groups[""]))
    return named


def render_menu_block(
    items: Sequence[MenuItemSpec],
    *,
    language: str = "ms",
    wa_digits: str = "",
    show_prices: bool = True,
    order_prefill: str = "",
    order_label: Optional[str] = None,
    with_css: bool = True,
) -> str:
    """The merchant's items as grouped cards. Names and prices are copied
    from the data; nothing is invented, so there is nothing to validate."""
    if not items:
        return ""
    lang = _lang(language)
    order_label = order_label or ("Order" if lang == "en" else "Pesan")
    parts: List[str] = [_BLOCK_CSS if with_css else "", f'<div class="{MENU_BLOCK_CLASS}" data-binaapp-menu-items="{len(items)}">']
    groups = group_by_category(items)
    show_headings = any(k for k, _ in groups)
    for cat, members in groups:
        label = cat or (_UNCATEGORISED[lang] if show_headings else "")
        if label:
            parts.append(f'<div class="bmf-cat"><h3>{_esc(label)}</h3><div class="bmf-rule" aria-hidden="true"></div></div>')
        parts.append('<ul class="bmf-grid">')
        for it in members:
            text_only = not it.image_url
            card_cls = "bmf-card bmf-text-only" if text_only else "bmf-card"
            if it.signature:
                card_cls += " bmf-signature"
            card = [f'<li class="{card_cls}">']
            if it.image_url:
                card.append(f'<img src="{_esc(it.image_url)}" alt="{_esc(it.name)}" loading="lazy" decoding="async">')
            card.append('<div class="bmf-body">')
            if it.signature:
                card.append(f'<span class="bmf-badge">{_SIGNATURE_LABEL[lang]}</span>')
            card.append(f'<h4 class="bmf-name">{_esc(it.name)}</h4>')
            if it.description:
                card.append(f'<p class="bmf-desc">{_esc(it.description)}</p>')
            foot = []
            if show_prices and it.price:
                foot.append(f'<span class="bmf-price">{_esc(it.price)}</span>')
            if wa_digits:
                foot.append(
                    f'<a class="bmf-order" href="{_esc(order_link(wa_digits, order_prefill, it.name))}" '
                    f'target="_blank" rel="noopener" aria-label="{_esc(order_label + " " + it.name)}">{_esc(order_label)}</a>'
                )
            if foot:
                card.append('<div class="bmf-foot">' + "".join(foot) + "</div>")
            card.append("</div></li>")
            parts.append("".join(card))
        parts.append("</ul>")
    parts.append("</div>")
    return "\n".join(p for p in parts if p)


_SLOT_RE = re.compile(
    rf"<div\b[^>]*\bid\s*=\s*[\"']{MENU_SLOT_ID}[\"'][^>]*>(.*?)</div>",
    re.IGNORECASE | re.DOTALL,
)


def fill_menu_slot(html: str, block: str) -> Tuple[str, bool]:
    """Render ``block`` into the model-emitted slot. (html, filled)."""
    if not html or not block:
        return html, False
    m = _SLOT_RE.search(html)
    if not m:
        return html, False
    opening = html[m.start():m.start() + html[m.start():].index(">") + 1]
    return html[: m.start()] + opening + "\n" + block + "\n</div>" + html[m.end():], True


# ---------------------------------------------------------------------------
# Finding the menu section
# ---------------------------------------------------------------------------

def _section_span(html: str, open_match: "re.Match") -> Tuple[int, int]:
    """[start, end) of the <section> opened at ``open_match``, nesting-aware."""
    depth = 0
    for m in _SECTION_ANY_RE.finditer(html, open_match.start()):
        if m.group(1):
            depth -= 1
            if depth == 0:
                return open_match.start(), m.end()
        else:
            depth += 1
    return open_match.start(), len(html)


def find_menu_section(html: str, items: Sequence[MenuItemSpec] = ()) -> Optional[Tuple[int, int]]:
    """The menu section's span: by id first, else the section holding the
    most supplied item names, else the section with the most prices."""
    if not html:
        return None
    best: Optional[Tuple[int, int]] = None
    best_score = -1
    keys = [it.key for it in items]
    for m in _SECTION_OPEN_RE.finditer(html):
        tag = m.group(0)
        sid = (_ID_RE.search(tag) or [None, ""])[1] if _ID_RE.search(tag) else ""
        start, end = _section_span(html, m)
        body = html[start:end]
        if MENU_SLOT_ID in body:
            return start, end
        score = 0
        if sid and any(w in sid.lower() for w in _MENU_ID_WORDS):
            score += 50
        text = normalize_name(re.sub(r"<[^>]+>", " ", body))
        score += sum(3 for k in keys if k and k in text)
        score += min(len(_PRICE_RE.findall(body)), 20)
        if score > best_score and score > 0:
            best, best_score = (start, end), score
    return best


# ---------------------------------------------------------------------------
# Reconciliation (the validator)
# ---------------------------------------------------------------------------

@dataclass
class MenuFidelityReport:
    total: int = 0
    matched: int = 0
    removed: List[str] = field(default_factory=list)
    price_fixed: List[str] = field(default_factory=list)
    renamed: List[str] = field(default_factory=list)
    injected: List[str] = field(default_factory=list)
    duplicates: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)
    section_found: bool = False

    @property
    def corrections(self) -> int:
        return len(self.removed) + len(self.price_fixed) + len(self.renamed) + len(self.injected) + len(self.duplicates)

    @property
    def changed(self) -> bool:
        return self.corrections > 0

    @property
    def ratio(self) -> float:
        return self.corrections / self.total if self.total else 0.0

    @property
    def severe(self) -> bool:
        return self.total > 0 and self.ratio > SEVERE_CORRECTION_RATIO

    def as_dict(self) -> Dict[str, Any]:
        return {
            "total": self.total, "matched": self.matched, "removed": list(self.removed),
            "price_fixed": list(self.price_fixed), "renamed": list(self.renamed), "injected": list(self.injected),
            "duplicates": list(self.duplicates), "corrections": self.corrections,
            "severe": self.severe, "section_found": self.section_found, "notes": list(self.notes),
        }


def _match_score(card_key: str, item_key: str, n_items_sharing: int = 1) -> float:
    """How surely a card named ``card_key`` is the supplied ``item_key``.
    0 means no. Exact wins; a card that carries the whole item name plus a
    qualifier ("Set A – Ayam Gepuk (pedas)") is the item; a card that is a
    FRAGMENT of the item name ("Set Panglima" for two different Panglima
    sets, "Ayam Goreng" for "Pedal Ayam Goreng (3 pcs)") is not — that is
    exactly the shape of an invented dish."""
    if not card_key or not item_key:
        return 0.0
    if card_key == item_key:
        return 1.0
    tc, ti = set(card_key.split()), set(item_key.split())
    if len(ti) >= 2 and ti <= tc:
        return 0.95
    ratio = SequenceMatcher(None, card_key, item_key).ratio()
    if ratio >= 0.88:
        return ratio
    if len(tc) >= 2 and tc <= ti and n_items_sharing == 1 and len(tc) / len(ti) >= 0.6:
        return 0.8
    return 0.0


def match_item(name: str, items: Sequence[MenuItemSpec]) -> Optional[MenuItemSpec]:
    key = normalize_name(name)
    if not key:
        return None
    for it in items:
        if it.key == key:
            return it
    tc = set(key.split())
    sharing = sum(1 for it in items if tc <= set(it.key.split())) if len(tc) >= 2 else 0
    best, best_score = None, 0.0
    for it in items:
        score = _match_score(key, it.key, sharing)
        if score > best_score:
            best, best_score = it, score
    return best


def _text(el: Tag) -> str:
    return re.sub(r"\s+", " ", el.get_text(" ", strip=True)).strip()


def _is_cta(text: str) -> bool:
    t = normalize_name(text)
    return not t or t in _CTA_WORDS or len(t) <= 2


def _name_of(card: Tag) -> Tuple[Optional[Tag], str]:
    """The element and text that name the item in ``card``."""
    for h in card.find_all(["h2", "h3", "h4", "h5", "h6"]):
        t = _text(h)
        if t and not _PRICE_RE.fullmatch(t) and not _is_cta(t):
            return h, t
    for el in card.find_all(["strong", "b", "span", "p", "div", "dt", "a"]):
        if el.find(["h2", "h3", "h4", "h5", "h6", "p", "div", "ul", "li"]):
            continue
        t = _text(el)
        if not t or _PRICE_RE.search(t) and len(_PRICE_RE.sub("", t).strip()) < 3:
            continue
        if _is_cta(t) or len(t) > 80 or el.name == "a":
            continue
        return el, t
    return None, ""


def _card_for(node: Tag, root: Tag) -> Optional[Tag]:
    """Smallest ancestor of ``node`` that names an item and holds at most
    one price — the card. None when the walk reaches the section root."""
    el = node if isinstance(node, Tag) else node.parent
    while el is not None and el is not root:
        if el.name in ("li", "article", "div", "tr", "dl", "a", "section"):
            name_el, name = _name_of(el)
            prices = [s for s in el.find_all(string=_PRICE_RE)]
            if name and len(prices) <= 1 and (name_el is not node or True):
                # A wrapper that names a CATEGORY and holds one card would
                # also qualify; prefer the inner element when it names too.
                return el
        el = el.parent
    return None


def _collect_cards(root: Tag) -> List[Tag]:
    cards: List[Tag] = []
    seen = set()

    def _add(c: Optional[Tag]):
        if c is not None and id(c) not in seen:
            seen.add(id(c))
            cards.append(c)

    for s in root.find_all(string=_PRICE_RE):
        if s.parent is None or s.parent.name in ("script", "style"):
            continue
        _add(_card_for(s.parent, root))
    for a in root.find_all("a", href=re.compile(r"wa\.me|whatsapp", re.IGNORECASE)):
        _add(_card_for(a, root))
    # Drop a card that contains another card (a wrapper matched through a
    # price that really belongs to the inner card).
    inner = set()
    for c in cards:
        for d in cards:
            if c is not d and d in c.descendants:
                inner.add(id(c))
    return [c for c in cards if id(c) not in inner]


def reconcile_menu(
    html: str,
    raw_items: Optional[Iterable[Any]],
    *,
    language: str = "ms",
    wa_digits: str = "",
    show_prices: bool = True,
    order_prefill: str = "",
) -> Tuple[str, MenuFidelityReport]:
    """Make the page's menu agree with the merchant's items. Returns the
    corrected HTML and a report of every correction."""
    items = normalize_items(raw_items)
    report = MenuFidelityReport(total=len(items))
    if not html or not items:
        return html, report
    span = find_menu_section(html, items)
    if span is None:
        report.notes.append("no menu section found — injecting a full menu block before the footer")
        block = render_menu_block(items, language=language, wa_digits=wa_digits, show_prices=show_prices, order_prefill=order_prefill)
        html2 = _insert_before_footer(html, f'<section id="menu" class="py-16 md:py-24"><div class="max-w-6xl mx-auto px-4">{block}</div></section>')
        report.injected = [it.name for it in items]
        return html2, report
    report.section_found = True
    start, end = span
    fragment = html[start:end]
    soup = BeautifulSoup(fragment, "html.parser")
    root = soup.find("section") or soup

    authoritative = root.find(id=MENU_SLOT_ID)
    found: Dict[str, Tag] = {}
    for card in _collect_cards(root):
        in_slot = authoritative is not None and (card is authoritative or card in authoritative.descendants)
        name_el, name = _name_of(card)
        if not name:
            continue
        item = match_item(name, items)
        if item is None:
            # Not a supplied item. Remove it only when it is priced or
            # orderable — an informational tile ("Level 1 Spicy") stays.
            report.removed.append(name)
            card.decompose()
            continue
        if item.key in found and not in_slot:
            report.duplicates.append(name)
            card.decompose()
            continue
        if item.key in found and in_slot:
            # The slot wins: drop the earlier (model-written) copy.
            prev = found[item.key]
            if prev is not card and prev is not authoritative and prev not in (authoritative.descendants if authoritative else ()):
                report.duplicates.append(name)
                prev.decompose()
        found[item.key] = card
        if not in_slot:
            if name_el is not None and normalize_name(name) != item.key:
                _replace_text(name_el, item.name)
                report.renamed.append(f"{name} -> {item.name}")
            if show_prices:
                _fix_price(card, item, report)
    report.matched = len(found)

    missing = [it for it in items if it.key not in found]
    if missing:
        block = render_menu_block(
            missing, language=language, wa_digits=wa_digits, show_prices=show_prices,
            order_prefill=order_prefill, with_css=("binaapp-menu-block-css" not in html),
        )
        wrapper = BeautifulSoup(block, "html.parser")
        target = authoritative if authoritative is not None else root
        target.append(wrapper)
        report.injected = [it.name for it in missing]

    if not report.changed:
        return html, report
    # Only the section's CHILDREN are re-serialised; its own opening tag is
    # kept byte-for-byte (BeautifulSoup would reorder its attributes).
    open_tag = _SECTION_OPEN_RE.match(fragment)
    if root is not soup and open_tag is not None:
        inner = "".join(str(c) for c in root.contents)
        new_fragment = open_tag.group(0) + inner + "</section>"
    else:
        new_fragment = str(soup)
    out = html[:start] + new_fragment + html[end:]
    return out, report


def _replace_text(el: Tag, new_text: str) -> None:
    strings = [s for s in el.find_all(string=True) if str(s).strip()]
    if not strings:
        el.string = new_text
        return
    strings[0].replace_with(new_text)
    for s in strings[1:]:
        s.replace_with("")


def _fix_price(card: Tag, item: MenuItemSpec, report: MenuFidelityReport) -> None:
    nodes = [s for s in card.find_all(string=_PRICE_RE) if s.parent is not None and s.parent.name not in ("script", "style")]
    if not item.price:
        return
    want = item.price
    if not nodes:
        return
    node = nodes[0]
    shown = _PRICE_RE.search(str(node)).group(0)
    if _price_key(shown) == _price_key(want):
        return
    node.replace_with(_PRICE_RE.sub(want, str(node), count=1))
    report.price_fixed.append(f"{item.name}: {shown} -> {want}")


def _price_key(text: str) -> str:
    digits = re.sub(r"[^\d.]", "", str(text or "").replace(",", ""))
    try:
        return f"{float(digits):.2f}"
    except ValueError:
        return digits


def _insert_before_footer(html: str, block: str) -> str:
    m = re.search(r"<footer\b", html, re.IGNORECASE)
    if m:
        return html[: m.start()] + block + "\n" + html[m.start():]
    m = re.search(r"</body>", html, re.IGNORECASE)
    if m:
        return html[: m.start()] + block + "\n" + html[m.start():]
    return html + block


def log_report(report: MenuFidelityReport, *, business: str = "", model: str = "") -> None:
    """One line per correction; an ERROR line when the run was severe."""
    if not report.total:
        return
    tag = f"[{business}]" if business else ""
    for n in report.removed:
        logger.warning(f"🍽️ MENU FIDELITY {tag} removed invented item: {n!r}")
    for n in report.duplicates:
        logger.warning(f"🍽️ MENU FIDELITY {tag} removed duplicate card: {n!r}")
    for n in report.price_fixed:
        logger.warning(f"🍽️ MENU FIDELITY {tag} corrected price: {n}")
    for n in report.renamed:
        logger.warning(f"🍽️ MENU FIDELITY {tag} restored exact name: {n}")
    for n in report.injected:
        logger.warning(f"🍽️ MENU FIDELITY {tag} injected missing item: {n!r}")
    for n in report.notes:
        logger.warning(f"🍽️ MENU FIDELITY {tag} {n}")
    summary = (
        f"🍽️ MENU FIDELITY {tag} {report.matched}/{report.total} supplied items matched, "
        f"{report.corrections} correction(s) ({report.ratio:.0%}) [model={model or 'unknown'}]"
    )
    if report.severe:
        logger.error(f"🔴 {summary} — more than {SEVERE_CORRECTION_RATIO:.0%} of the menu needed correcting")
    elif report.changed:
        logger.warning(summary)
    else:
        logger.info(summary)
