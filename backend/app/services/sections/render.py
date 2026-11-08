"""Section renderers. Each returns an HTML fragment that uses only the
classes ``theme.render_css`` defines. No layout decisions are made by a
model anywhere in this file."""

from __future__ import annotations

import re
from typing import Dict, List
from urllib.parse import quote

from app.services.sections.copy import Copy
from app.services.sections.spec import SiteSpec
from app.services.sections.theme import esc

MENU_SLOT_ID = "binaapp-menu-slot"
MAPS_SLOT_ID = "binaapp-maps-slot"
CONTACT_SLOT_ID = "binaapp-contact-slot"

AI_LABEL = {"ms": "Gambar hiasan", "en": "Image for illustration"}

# ---------------------------------------------------------------------------
# Icons (inline SVG, currentColor)
# ---------------------------------------------------------------------------

ICONS: Dict[str, str] = {
    "whatsapp": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M17.5 14.4c-.3-.1-1.8-.9-2-1-.3-.1-.5-.1-.7.1-.2.3-.8 1-.9 1.2-.2.2-.3.2-.6.1-.3-.1-1.3-.5-2.4-1.5-.9-.8-1.5-1.8-1.7-2.1-.2-.3 0-.5.1-.6l.4-.5.3-.5c.1-.2 0-.4 0-.5l-.9-2.2c-.2-.6-.5-.5-.7-.5h-.6c-.2 0-.5.1-.8.4-.3.3-1 1-1 2.5s1.1 2.9 1.2 3.1c.1.2 2.1 3.2 5.1 4.5 2.5 1 3 .8 3.6.7.6-.1 1.8-.7 2-1.4.2-.7.2-1.3.2-1.4-.1-.2-.3-.3-.6-.4zM12 2a10 10 0 0 0-8.6 15.1L2 22l5-1.3A10 10 0 1 0 12 2zm0 18.2c-1.5 0-3-.4-4.3-1.2l-.3-.2-3 .8.8-2.9-.2-.3A8.2 8.2 0 1 1 12 20.2z"/></svg>',
    "phone": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6.6 10.8a15.1 15.1 0 0 0 6.6 6.6l2.2-2.2c.3-.3.7-.4 1-.2 1.1.4 2.3.6 3.6.6.6 0 1 .4 1 1V20c0 .6-.4 1-1 1A17 17 0 0 1 3 4c0-.6.4-1 1-1h3.5c.6 0 1 .4 1 1 0 1.3.2 2.5.6 3.6.1.3 0 .7-.2 1l-2.3 2.2z"/></svg>',
    "mail": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M20 4H4a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V6a2 2 0 0 0-2-2zm0 4-8 5-8-5V6l8 5 8-5v2z"/></svg>',
    "pin": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 2a7 7 0 0 0-7 7c0 5.3 7 13 7 13s7-7.7 7-13a7 7 0 0 0-7-7zm0 9.5A2.5 2.5 0 1 1 12 6.5a2.5 2.5 0 0 1 0 5z"/></svg>',
    "clock": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20zm0 18a8 8 0 1 1 0-16 8 8 0 0 1 0 16zm.5-13H11v6l5.2 3.2.8-1.3-4.5-2.7V7z"/></svg>',
    "flame": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M13.5 2s.6 3.3-1.3 5.6C10.4 9.8 8 11 8 14.5A5.5 5.5 0 0 0 13.5 20c3 0 5.5-2.2 5.5-5.5 0-3-2-4.3-2-4.3s.3 1.6-.9 2.5c.4-3.7-2.6-10.7-2.6-10.7zM7 15.5C7 18.5 9 22 13.5 22c-5 0-8.5-3-8.5-7.5 0-2 1-3.5 1-3.5s.1 2.5 1 4.5z"/></svg>',
    "gift": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M20 7h-2.2A3 3 0 0 0 15 2.5c-1.2 0-2.3.8-3 2-.7-1.2-1.8-2-3-2A3 3 0 0 0 6.2 7H4a2 2 0 0 0-2 2v2h20V9a2 2 0 0 0-2-2zM9 4.5c.6 0 1.4.8 1.9 2.5H9a1.3 1.3 0 0 1 0-2.5zm6 0a1.3 1.3 0 0 1 0 2.5h-1.9c.5-1.7 1.3-2.5 1.9-2.5zM3 13v7a2 2 0 0 0 2 2h6v-9H3zm10 9h6a2 2 0 0 0 2-2v-7h-8v9z"/></svg>',
    "tag": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M21.4 11.6 12.4 2.6A2 2 0 0 0 11 2H4a2 2 0 0 0-2 2v7c0 .5.2 1 .6 1.4l9 9a2 2 0 0 0 2.8 0l7-7a2 2 0 0 0 0-2.8zM6.5 8A1.5 1.5 0 1 1 6.5 5a1.5 1.5 0 0 1 0 3z"/></svg>',
    "menu": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 6h16v2H4zm0 5h16v2H4zm0 5h16v2H4z"/></svg>',
    "sparkle": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 2l1.8 5.7L19.5 9.5l-5.7 1.8L12 17l-1.8-5.7L4.5 9.5l5.7-1.8L12 2zm7 12l.9 2.6 2.6.9-2.6.9L19 21l-.9-2.6-2.6-.9 2.6-.9L19 14z"/></svg>',
    "instagram": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M7.5 2h9A5.5 5.5 0 0 1 22 7.5v9a5.5 5.5 0 0 1-5.5 5.5h-9A5.5 5.5 0 0 1 2 16.5v-9A5.5 5.5 0 0 1 7.5 2zm0 2A3.5 3.5 0 0 0 4 7.5v9A3.5 3.5 0 0 0 7.5 20h9a3.5 3.5 0 0 0 3.5-3.5v-9A3.5 3.5 0 0 0 16.5 4h-9zM12 7a5 5 0 1 1 0 10 5 5 0 0 1 0-10zm0 2a3 3 0 1 0 0 6 3 3 0 0 0 0-6zm5.3-2.8a1.2 1.2 0 1 1 0 2.4 1.2 1.2 0 0 1 0-2.4z"/></svg>',
    "facebook": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M13.5 22v-8h2.7l.4-3.2h-3.1V8.8c0-.9.3-1.6 1.6-1.6h1.7V4.4c-.3 0-1.3-.1-2.5-.1-2.5 0-4.1 1.5-4.1 4.2v2.3H7.4V14h2.8v8h3.3z"/></svg>',
    "tiktok": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M16.5 2c.3 2.3 1.6 3.7 3.9 3.9v3.3c-1.4 0-2.7-.4-3.9-1.2v6.6a5.9 5.9 0 1 1-5-5.8v3.4a2.5 2.5 0 1 0 1.7 2.4V2h3.3z"/></svg>',
}


def icon(name: str) -> str:
    return ICONS.get(name, "")


# ---------------------------------------------------------------------------
# Links
# ---------------------------------------------------------------------------

def wa_link(digits: str, prefill: str) -> str:
    return f"https://wa.me/{digits}?text={quote(prefill)}" if digits else "#contact"


def tel_link(digits: str) -> str:
    return f"tel:+{digits}" if digits else "#contact"


def town_of(address: str) -> str:
    """"41200 Klang, Selangor" -> "Klang": the town after the postcode, else
    the second-last comma part, else nothing."""
    text = str(address or "").strip()
    if not text:
        return ""
    m = re.search(r"\b\d{5}\s*,?\s*([A-Za-z][A-Za-z .'-]{1,30}?)\s*(?:,|$)", text)
    if m:
        return m.group(1).strip()
    parts = [p.strip() for p in text.split(",") if p.strip()]
    if len(parts) >= 2:
        return re.sub(r"^\d{5}\s*", "", parts[-2])
    return ""


def strings(spec: SiteSpec) -> Dict[str, str]:
    from app.services.site_strings import strings_for
    return strings_for(spec.lang)


def catalogue_words(spec: SiteSpec) -> Dict[str, str]:
    """Nav label, heading and CTA for the items section, per vertical."""
    s = strings(spec)
    if spec.is_food:
        return {"nav": s["nav_menu"], "heading": s["heading_menu"], "cta": s["cta_view_menu"]}
    if spec.vertical == "clothing":
        return {"nav": s["nav_collection"], "heading": s["heading_collection"], "cta": s["cta_view_collection"]}
    if spec.vertical in ("salon", "services"):
        return {"nav": s["nav_services"], "heading": s["heading_services_prices"], "cta": s["cta_view_services"]}
    return {"nav": s["nav_products"], "heading": s["heading_products"], "cta": s["cta_view_products"]}


def primary_cta(spec: SiteSpec, *, on_dark: bool = False, in_nav: bool = False) -> str:
    """The WhatsApp CTA: icon + label, always."""
    from app.services.whatsapp_prefill import default_prefill
    s = strings(spec)
    label = s["cta_order_whatsapp"] if spec.is_food else s["cta_chat_whatsapp"]
    href = wa_link(spec.wa_digits, default_prefill(spec.lang, "food" if spec.is_food else "general"))
    cls = "bs-btn bs-btn-wa"
    text = f'<span class="bs-btn-text">{esc(label)}</span>' if in_nav else esc(label)
    return f'<a class="{cls}" href="{esc(href)}" target="_blank" rel="noopener" aria-label="{esc(label)}">{icon("whatsapp")}{text}</a>'


def secondary_cta(spec: SiteSpec, *, on_dark: bool = False) -> str:
    words = catalogue_words(spec)
    cls = "bs-btn bs-btn-ghost" + (" bs-on-dark" if on_dark else "")
    if spec.has_menu:
        return f'<a class="{cls}" href="#menu">{icon("menu")}{esc(words["cta"])}</a>'
    s = strings(spec)
    if spec.wa_digits:
        return f'<a class="{cls}" href="{esc(tel_link(spec.wa_digits))}">{icon("phone")}{esc(s["cta_call"])}</a>'
    return f'<a class="{cls}" href="#about">{icon("sparkle")}{esc(s["nav_about"])}</a>'


# ---------------------------------------------------------------------------
# Sections
# ---------------------------------------------------------------------------

def render_nav(spec: SiteSpec) -> str:
    s = strings(spec)
    words = catalogue_words(spec)
    brand_inner = (
        f'<img src="{esc(spec.logo_url)}" alt="{esc(spec.business_name)}" width="120" height="40">'
        if spec.logo_url else ""
    ) + f"<span>{esc(spec.business_name)}</span>"
    links: List[str] = []
    if spec.has_menu:
        links.append(f'<li><a href="#menu">{esc(words["nav"])}</a></li>')
    links.append(f'<li><a href="#about">{esc(s["nav_about"])}</a></li>')
    if spec.address:
        links.append(f'<li><a href="#location">{esc(s["nav_location"])}</a></li>')
    links.append(f'<li><a href="#contact">{esc(s["nav_contact"])}</a></li>')
    cta = primary_cta(spec, in_nav=True) if spec.wa_digits else ""
    return (
        '<header class="bs-nav" id="top"><div class="bs-wrap">'
        f'<a class="bs-brand" href="#top">{brand_inner}</a>'
        f'<nav aria-label="Menu utama"><ul class="bs-nav-links">{"".join(links)}</ul></nav>'
        f"{cta}</div></header>"
    )


def render_hero(spec: SiteSpec, copy: Copy) -> str:
    has_photo = bool(spec.hero_url)
    cls = "bs-hero" + ("" if has_photo else " bs-hero-solid")
    media = ""
    if has_photo:
        label = f'<span class="bs-ai-label">{esc(AI_LABEL[spec.lang])}</span>' if spec.hero_illustrative else ""
        media = (
            f'<div class="bs-hero-media"><img src="{esc(spec.hero_url)}" alt="{esc(spec.business_name)}" '
            f'width="1600" height="900" fetchpriority="high">{label}</div><div class="bs-hero-scrim"></div>'
        )
    kicker = f'<span class="bs-kicker">{esc(copy.kicker)}</span>' if copy.kicker else ""
    ctas = []
    if spec.wa_digits:
        ctas.append(primary_cta(spec, on_dark=has_photo))
    ctas.append(secondary_cta(spec, on_dark=has_photo))
    notes: List[str] = []
    if spec.is_24h:
        notes.append(("Open 24 hours" if spec.lang == "en" else "Buka 24 jam"))
    elif spec.hours:
        notes.append(esc(spec.hours))
    town = town_of(spec.address)
    if town:
        notes.append(esc(town))
    note_html = f'<div class="bs-hero-note">{"".join(f"<span>{n}</span>" for n in notes)}</div>' if notes else ""
    return (
        f'<section class="{cls}" id="home">{media}<div class="bs-wrap">{kicker}'
        f'<h1 class="bs-h1">{esc(copy.headline)}</h1>'
        f'<p class="bs-sub">{esc(copy.subheadline)}</p>'
        f'<div class="bs-cta-row">{"".join(ctas)}</div>{note_html}</div></section>'
    )


def render_options_strip(spec: SiteSpec) -> str:
    if not spec.option_chips:
        return ""
    title = "Spice level" if spec.lang == "en" else "Tahap pedas"
    chips = "".join(f'<span class="bs-chip">{icon(c.icon)}{esc(c.label)}</span>' for c in spec.option_chips)
    return f'<div class="bs-strip" id="options" aria-label="{esc(title)}"><div class="bs-wrap"><span class="bs-strip-title">{esc(title)}</span>{chips}</div></div>'


def render_banners(spec: SiteSpec) -> str:
    if not spec.banners:
        return ""
    cards = []
    for b in spec.banners:
        ic = "gift" if b.kind == "refill" else "tag"
        cards.append(f'<div class="bs-banner">{icon(ic)}<div><strong>{esc(b.title)}</strong><p>{esc(b.text)}</p></div></div>')
    return f'<section class="bs-banners" id="info"><div class="bs-wrap">{"".join(cards)}</div></section>'


def render_menu_section(spec: SiteSpec, copy: Copy) -> str:
    """The heading and an EMPTY slot; ``menu_fidelity`` renders the cards."""
    if not spec.has_menu:
        return ""
    words = catalogue_words(spec)
    lead = f'<p class="bs-lead">{esc(copy.menu_lead)}</p>' if copy.menu_lead else ""
    return (
        f'<section class="bs-section" id="menu"><div class="bs-wrap"><h2 class="bs-h2">{esc(words["heading"])}</h2>'
        f'<div class="bs-rule" aria-hidden="true"></div>{lead}<div id="{MENU_SLOT_ID}"></div></div></section>'
    )


def render_coming_soon(spec: SiteSpec) -> str:
    if not spec.coming_soon:
        return ""
    title = "Coming soon" if spec.lang == "en" else "Akan datang"
    items = "".join(f"<li>{esc(i)}</li>" for i in spec.coming_soon[:12])
    return (
        f'<section class="bs-section bs-alt" id="coming-soon"><div class="bs-wrap"><h2 class="bs-h2">{esc(title)}</h2>'
        f'<div class="bs-rule" aria-hidden="true"></div><ul class="bs-soon-list">{items}</ul></div></section>'
    )


def render_about(spec: SiteSpec, copy: Copy) -> str:
    paras = "".join(f"<p>{esc(p)}</p>" for p in copy.about_paragraphs)
    photo = ""
    if spec.about_url:
        label = f'<span class="bs-ai-label">{esc(AI_LABEL[spec.lang])}</span>' if spec.about_illustrative else ""
        photo = f'<div class="bs-about-photo"><img src="{esc(spec.about_url)}" alt="{esc(spec.business_name)}" loading="lazy" width="800" height="600">{label}</div>'
    facts: List[str] = []
    if spec.has_menu:
        n = len(spec.items)
        facts.append(f'<div class="bs-fact"><strong>{n}</strong><span>{"items on the menu" if spec.lang == "en" else "pilihan dalam menu"}</span></div>' if spec.is_food
                     else f'<div class="bs-fact"><strong>{n}</strong><span>{"products & services" if spec.lang == "en" else "produk & servis"}</span></div>')
    if spec.is_24h:
        facts.append(f'<div class="bs-fact"><strong>24h</strong><span>{"open every day" if spec.lang == "en" else "buka setiap hari"}</span></div>')
    if spec.delivery_available:
        facts.append(f'<div class="bs-fact"><strong>{"Delivery" if spec.lang == "en" else "Hantar"}</strong><span>{"we deliver" if spec.lang == "en" else "penghantaran tersedia"}</span></div>')
    facts_html = f'<div class="bs-about-facts">{"".join(facts)}</div>' if facts else ""
    wrap_cls = "bs-wrap" + (" bs-has-photo" if photo else "")
    return (
        f'<section class="bs-section bs-about" id="about"><div class="{wrap_cls}">'
        f'<div class="bs-about-text"><h2 class="bs-h2">{esc(copy.about_title)}</h2><div class="bs-rule" aria-hidden="true"></div>{paras}{facts_html}</div>'
        f"{photo}</div></section>"
    )


def _info_rows(spec: SiteSpec) -> str:
    s = strings(spec)
    rows: List[str] = []
    if spec.address:
        rows.append(f'<div class="bs-info-row">{icon("pin")}<div><strong>{esc(s["label_address"])}</strong><span>{esc(spec.address)}</span></div></div>')
    if spec.is_24h or spec.hours:
        hours = ("Open 24 hours, every day" if spec.lang == "en" else "Buka 24 jam, setiap hari") if spec.is_24h else spec.hours
        rows.append(f'<div class="bs-info-row">{icon("clock")}<div><strong>{esc(s["heading_hours"])}</strong><span>{esc(hours)}</span></div></div>')
    if spec.wa_digits:
        rows.append(f'<div class="bs-info-row">{icon("phone")}<div><strong>{esc(s["cta_call"])}</strong><a href="{esc(tel_link(spec.wa_digits))}">{esc(spec.phone_display)}</a></div></div>')
    if spec.email:
        rows.append(f'<div class="bs-info-row">{icon("mail")}<div><strong>E-mel</strong><a href="mailto:{esc(spec.email)}">{esc(spec.email)}</a></div></div>')
    return "".join(rows)


def render_location(spec: SiteSpec) -> str:
    """Address card + the maps slot. The slot is filled by
    ``TemplateService.inject_google_maps`` (iframe + Maps/Waze buttons);
    the ``bs-map`` box never clips it."""
    if not spec.address:
        return ""
    s = strings(spec)
    map_html = f'<div class="bs-map"><div id="{MAPS_SLOT_ID}"></div></div>' if spec.include_maps else ""
    return (
        f'<section class="bs-section bs-alt bs-location" id="location"><div class="bs-wrap"><h2 class="bs-h2">{esc(s["heading_location"])}</h2>'
        f'<div class="bs-rule" aria-hidden="true"></div><div class="bs-grid"><div class="bs-info-card">{_info_rows(spec)}</div>{map_html}</div></div></section>'
    )


def render_contact(spec: SiteSpec, copy: Copy) -> str:
    s = strings(spec)
    ctas: List[str] = []
    if spec.wa_digits:
        ctas.append(primary_cta(spec))
        ctas.append(f'<a class="bs-btn bs-btn-ghost" href="{esc(tel_link(spec.wa_digits))}">{icon("phone")}{esc(s["cta_call"])} {esc(spec.phone_display)}</a>')
    if spec.email:
        ctas.append(f'<a class="bs-btn bs-btn-ghost" href="mailto:{esc(spec.email)}">{icon("mail")}E-mel</a>')
    socials = "".join(
        f'<a class="bs-btn bs-btn-ghost" href="{esc(url)}" target="_blank" rel="noopener">{icon(name)}{esc(name.title())}</a>'
        for name, url in spec.socials.items() if name in ("instagram", "facebook", "tiktok")
    )
    info = "" if spec.address else f'<div class="bs-info-card" style="max-width:36rem;margin:1.5rem auto 0">{_info_rows(spec)}</div>'
    form_slot = f'<div id="{CONTACT_SLOT_ID}" style="max-width:36rem;margin:2rem auto 0"></div>' if spec.include_contact_form else ""
    return (
        f'<section class="bs-section bs-contact" id="contact"><div class="bs-wrap"><h2 class="bs-h2">{esc(s["heading_contact"])}</h2>'
        f'<div class="bs-rule" aria-hidden="true"></div><p class="bs-lead">{esc(copy.contact_lead)}</p>'
        f'<div class="bs-cta-row">{"".join(ctas)}{socials}</div>{info}{form_slot}</div></section>'
    )


def render_footer(spec: SiteSpec, copy: Copy) -> str:
    s = strings(spec)
    words = catalogue_words(spec)
    brand = (f'<img src="{esc(spec.logo_url)}" alt="" width="120" height="40">' if spec.logo_url else "") + f"<span>{esc(spec.business_name)}</span>"
    links: List[str] = []
    if spec.has_menu:
        links.append(f'<li><a href="#menu">{esc(words["nav"])}</a></li>')
    links.append(f'<li><a href="#about">{esc(s["nav_about"])}</a></li>')
    if spec.address:
        links.append(f'<li><a href="#location">{esc(s["nav_location"])}</a></li>')
    links.append(f'<li><a href="#contact">{esc(s["nav_contact"])}</a></li>')
    contact: List[str] = []
    if spec.wa_digits:
        contact.append(f'<li><a href="{esc(wa_link(spec.wa_digits, ""))}" target="_blank" rel="noopener">WhatsApp {esc(spec.phone_display)}</a></li>')
        contact.append(f'<li><a href="{esc(tel_link(spec.wa_digits))}">{esc(s["cta_call"])}: {esc(spec.phone_display)}</a></li>')
    if spec.email:
        contact.append(f'<li><a href="mailto:{esc(spec.email)}">{esc(spec.email)}</a></li>')
    if spec.address:
        contact.append(f"<li>{esc(spec.address)}</li>")
    pay = ""
    if spec.payment_methods:
        badges = "".join(f"<span>{esc(s['payment_cod'] if p == 'cod' else s['payment_qr'])}</span>" for p in spec.payment_methods if p in ("cod", "qr"))
        if badges:
            pay = f'<div class="bs-footer-pay">{badges}</div>'
    import datetime as _dt
    year = _dt.date.today().year
    return (
        '<footer class="bs-footer" id="footer"><div class="bs-wrap">'
        f'<div><a class="bs-brand" href="#top">{brand}</a><p>{esc(copy.tagline)}</p>{pay}</div>'
        f'<div><h4>{esc(s["nav_menu"] if spec.is_food else "Pautan")}</h4><ul>{"".join(links)}</ul></div>'
        f'<div><h4>{esc(s["heading_contact"])}</h4><ul>{"".join(contact)}</ul></div>'
        f'</div><div class="bs-footer-bottom">© {year} {esc(spec.business_name)}. {esc(s["footer_rights"])}.</div></footer>'
    )
