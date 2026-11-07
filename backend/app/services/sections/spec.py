"""``SiteSpec``: everything a composed page renders, taken from the
merchant's own data. Nothing in here is written by a model."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Sequence

from app.services.menu_fidelity import MenuItemSpec, normalize_items

FOOD_VERTICALS = ("food", "bakery")
_LEVEL_WORD_RE = re.compile(r"\blevel\s*(\d)\s*[:\-–—]?\s*([A-Za-z][A-Za-z ]{0,20})?", re.IGNORECASE)


@dataclass
class OptionChip:
    label: str          # "Level 1 · Spicy"
    icon: str = "flame"


@dataclass
class Banner:
    kind: str           # refill | charge | note
    title: str
    text: str


@dataclass
class SiteSpec:
    business_name: str
    vertical: str = "general"
    language: str = "ms"
    description: str = ""
    wa_digits: str = ""
    phone_display: str = ""
    email: str = ""
    address: str = ""
    hours: str = ""
    is_24h: bool = False
    logo_url: str = ""
    hero_url: str = ""
    hero_illustrative: bool = False
    about_url: str = ""
    about_illustrative: bool = False
    items: List[MenuItemSpec] = field(default_factory=list)
    show_prices: bool = True
    option_chips: List[OptionChip] = field(default_factory=list)
    banners: List[Banner] = field(default_factory=list)
    coming_soon: List[str] = field(default_factory=list)
    socials: Dict[str, str] = field(default_factory=dict)
    payment_methods: List[str] = field(default_factory=list)
    delivery_available: bool = False
    include_maps: bool = True
    include_whatsapp: bool = True
    include_contact_form: bool = True
    design_style: Optional[str] = None
    color_mode: str = "light"

    @property
    def is_food(self) -> bool:
        return self.vertical in FOOD_VERTICALS

    @property
    def lang(self) -> str:
        return "en" if str(self.language or "ms").lower().startswith("en") else "ms"

    @property
    def has_menu(self) -> bool:
        return bool(self.items)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "business_name": self.business_name, "vertical": self.vertical, "language": self.language,
            "wa_digits": self.wa_digits, "address": self.address, "hours": self.hours, "is_24h": self.is_24h,
            "logo": bool(self.logo_url), "hero": bool(self.hero_url), "about_photo": bool(self.about_url),
            "items": len(self.items), "chips": [c.label for c in self.option_chips],
            "banners": [b.kind for b in self.banners], "coming_soon": list(self.coming_soon),
            "socials": sorted(self.socials), "payment": list(self.payment_methods),
        }


# ---------------------------------------------------------------------------
# Facts from the brief
# ---------------------------------------------------------------------------

def option_chips_from_facts(facts: Iterable[Any], lang: str = "ms") -> List[OptionChip]:
    """Spice levels (or any "Level n" scale) as chips, one per level."""
    chips: List[OptionChip] = []
    for fact in facts:
        if getattr(fact, "kind", "") != "level":
            continue
        text = str(getattr(fact, "text", "") or "")
        names: Dict[str, str] = {}
        for m in _LEVEL_WORD_RE.finditer(text):
            word = (m.group(2) or "").strip()
            # keep a one- or two-word descriptor ("Spicy", "Extra Hot")
            word = " ".join(word.split()[:2]) if word else ""
            if word.lower() in ("dan", "and", "or", "atau", "level"):
                word = ""
            names.setdefault(m.group(1), word)
        for lvl in sorted(set(getattr(fact, "levels", []) or names.keys())):
            word = names.get(lvl, "")
            chips.append(OptionChip(label=f"Level {lvl}" + (f" · {word}" if word else "")))
        if chips:
            break
    return chips


def banners_from_facts(facts: Iterable[Any], lang: str = "ms") -> List[Banner]:
    out: List[Banner] = []
    for fact in facts:
        kind = getattr(fact, "kind", "")
        text = str(getattr(fact, "text", "") or "").strip()
        if not text:
            continue
        if kind == "refill":
            out.append(Banner("refill", "Free refill" if lang == "en" else "Refill percuma", text))
        elif kind == "charge":
            kws = [k.lower() for k in (getattr(fact, "keywords", []) or [])]
            if any("away" in k or "bungkus" in k for k in kws):
                title = "Take-away" if lang == "en" else "Bungkus"
            elif any("deliver" in k or "hantar" in k for k in kws):
                title = "Delivery" if lang == "en" else "Penghantaran"
            else:
                title = "Charges" if lang == "en" else "Caj tambahan"
            out.append(Banner("charge", title, text))
    return out


def coming_soon_from_facts(facts: Iterable[Any]) -> List[str]:
    for fact in facts:
        if getattr(fact, "kind", "") == "coming_soon":
            return [str(i) for i in (getattr(fact, "items", []) or []) if str(i).strip()]
    return []


# ---------------------------------------------------------------------------
# Building the spec from a request
# ---------------------------------------------------------------------------

def _display_phone(digits: str) -> str:
    try:
        from app.services.contact_links import display_phone
        return display_phone(digits) if digits else ""
    except Exception:
        return digits


def _vertical_for(request: Any) -> str:
    from app.services.business_types import detect_business_type, normalize_business_type
    explicit = normalize_business_type(getattr(request, "business_type", None))
    if explicit and explicit != "auto":
        return explicit
    return detect_business_type(str(getattr(request, "description", "") or ""))


def _first_free_photo(image_urls: Dict[str, Any], items: Sequence[MenuItemSpec], posters: Sequence[str]) -> str:
    """A gallery photo not paired to a menu item and not a poster — the
    about section's picture, if any."""
    used = {it.image_url for it in items if it.image_url}
    for i in range(1, 5):
        url = image_urls.get(f"gallery{i}")
        if isinstance(url, str) and url and url not in used and url not in posters and not image_urls.get(f"gallery{i}_name"):
            return url
    return ""


def build_spec(
    request: Any,
    *,
    image_urls: Optional[Dict[str, Any]] = None,
    items: Optional[Sequence[MenuItemSpec]] = None,
    ai_image_urls: Iterable[str] = (),
    poster_urls: Iterable[str] = (),
    wa_digits: Optional[str] = None,
    language: Optional[str] = None,
    color_mode: str = "light",
) -> SiteSpec:
    from app.services.brief_facts import extract_key_facts

    image_urls = image_urls or {}
    ai_urls = set(ai_image_urls or ())
    posters = list(poster_urls or ())
    lang_value = language or (request.language.value if hasattr(getattr(request, "language", None), "value") else str(getattr(request, "language", "ms") or "ms"))
    lang = "en" if str(lang_value).lower().startswith("en") else "ms"
    if wa_digits is None:
        from app.services.generation_validator import normalize_my_phone_digits
        wa_digits = normalize_my_phone_digits(getattr(request, "whatsapp_number", None) or "") or ""
    if items is None:
        items = normalize_items(getattr(request, "menu_items", None) or [])
    items = list(items)
    facts = extract_key_facts(getattr(request, "description", None), getattr(request, "design_brief", None))
    hero = image_urls.get("hero") if isinstance(image_urls.get("hero"), str) else ""
    if hero in posters:
        hero = ""
    about = _first_free_photo(image_urls, items, posters)
    socials = {}
    if bool(getattr(request, "include_social", False)):
        for k, v in (getattr(request, "social_media", None) or {}).items():
            if isinstance(v, str) and v.strip():
                socials[str(k).lower()] = v.strip()
    hours = str(getattr(request, "opening_hours", None) or "").strip()
    is_24h = bool(getattr(request, "is_24h", False))
    if not is_24h and hours:
        try:
            from app.services.data_consistency import hours_are_24h
            is_24h = hours_are_24h(hours)
        except Exception:
            pass
    return SiteSpec(
        business_name=str(getattr(request, "business_name", "") or "").strip(),
        vertical=_vertical_for(request),
        language=lang,
        description=str(getattr(request, "description", "") or ""),
        wa_digits=wa_digits or "",
        phone_display=_display_phone(wa_digits or ""),
        email=str(getattr(request, "contact_email", None) or "").strip(),
        address=str(getattr(request, "location_address", None) or "").strip(),
        hours=hours,
        is_24h=is_24h,
        logo_url=str(getattr(request, "logo", None) or "").strip(),
        hero_url=hero or "",
        hero_illustrative=bool(hero and hero in ai_urls),
        about_url=about,
        about_illustrative=bool(about and about in ai_urls),
        items=items,
        show_prices=bool(getattr(request, "show_prices", True)),
        option_chips=option_chips_from_facts(facts, lang),
        banners=banners_from_facts(facts, lang),
        coming_soon=coming_soon_from_facts(facts),
        socials=socials,
        payment_methods=[str(p) for p in (getattr(request, "payment_methods", None) or [])],
        delivery_available=bool(getattr(request, "include_ecommerce", False)),
        include_maps=bool(getattr(request, "include_maps", True)),
        include_whatsapp=bool(getattr(request, "include_whatsapp", True)) and bool(wa_digits),
        include_contact_form=bool(getattr(request, "include_contact_form", True)),
        design_style=getattr(request, "design_style", None),
        color_mode=str(color_mode or "light"),
    )
