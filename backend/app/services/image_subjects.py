"""
Category-locked image subjects (Round 2, §A1).

A laundry site came back with a chef plating food and two people shaking
hands, because the non-food prompt templates described a *kind* of picture
("skilled professional at work with a client") instead of the *subject*.
Every generated image now starts with a subject clause from this table —
chosen by the vertical and the merchant's own words — and non-F&B prompts
are scrubbed of F&B wording before they leave. The negative prompt is the
same everywhere: no text, no letters, no logo, no watermark, no people's
faces (labels are HTML; faces are a privacy and credibility risk).

Pure module; ``ai_service`` applies it.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

#: The universal negative prompt (§A1). Providers with a negative_prompt
#: field receive NEGATIVE_TERMS; providers without one get NEGATIVE_PROMPT
#: appended as positive-phrased exclusions.
NEGATIVE_PROMPT = (
    "no text, no letters, no words, no lettering, no captions, no signage, no labels, "
    "no watermark, no logo anywhere in the image, no people's faces"
)
NEGATIVE_TERMS = "text, letters, words, logo, watermark, signage, label, people's faces, faces, portrait"

_FNB_WORDS = (
    "dish", "dishes", "plated", "plating", "chef", "chefs", "restaurant", "cuisine", "appetizing", "appetising",
    "food photography", "food", "meal", "meals", "delicious", "tasty", "menu", "cooking", "kitchen", "kuih",
    "nasi", "gravy", "buffet", "cafe", "café", "coffee", "beverage", "drink",
)
_FNB_WORD_RE = re.compile(r"\b(?:" + "|".join(re.escape(w) for w in sorted(_FNB_WORDS, key=len, reverse=True)) + r")\b", re.IGNORECASE)


@dataclass(frozen=True)
class ImageSubject:
    key: str
    vision_label: str  # what the vision check asks the image to match
    hero_clause: str  # prepended to every hero prompt
    item_clause: str  # template with {item}
    verticals: Tuple[str, ...]
    keywords: Tuple[str, ...] = ()


SUBJECTS: Tuple[ImageSubject, ...] = (
    ImageSubject(
        key="laundry",
        vision_label="a self-service laundromat / laundry shop (washing machines, dryers, folded clothes)",
        hero_clause="self-service laundromat interior, rows of front-load washing machines and dryers, clean bright, product photography",
        item_clause="{item} in a self-service laundromat, front-load washing machine or dryer, folded clean laundry, clean bright, product photography",
        verticals=("services", "general"),
        keywords=("dobi", "laundry", "laundromat", "layan diri", "cuci baju", "mesin basuh", "pengering", "dry clean", "dry-clean", "dobi layan"),
    ),
    ImageSubject(
        key="salon",
        vision_label="a hair or beauty salon (salon chair, mirror, styling tools)",
        hero_clause="salon chair, large mirror, styling tools on the counter, clean modern salon interior, soft daylight",
        item_clause="{item}, salon workstation with the tools for it, chair and mirror, clean modern salon interior",
        verticals=("salon",),
        keywords=("salon", "rambut", "hair", "spa", "kecantikan", "beauty", "facial", "makeup", "bridal", "kuku", "nail", "manicure"),
    ),
    ImageSubject(
        key="barber",
        vision_label="a barbershop (barber chair, clippers, mirror)",
        hero_clause="barbershop interior, leather barber chair, clippers and combs on the counter, mirror, clean and bright",
        item_clause="{item}, barber tools laid out on the counter, barber chair and mirror, clean barbershop interior",
        verticals=("salon", "services"),
        keywords=("barber", "barbershop", "gunting rambut lelaki", "grooming", "fade"),
    ),
    ImageSubject(
        key="workshop",
        vision_label="a repair or service workshop (tools, equipment, workbench, air-conditioner or plumbing parts)",
        hero_clause="service workshop bench with tools and equipment laid out, clean and organised, bright daylight, product photography",
        item_clause="{item}, the tools and parts for it laid out on a clean workbench, product photography",
        verticals=("services", "general"),
        keywords=("bengkel", "workshop", "aircond", "air cond", "air-cond", "paip", "plumbing", "elektrik", "electrical", "repair", "baiki", "servis kereta", "tayar", "mekanik", "renovation", "kontraktor", "pembinaan", "wiring", "cctv"),
    ),
    ImageSubject(
        key="cleaning",
        vision_label="a cleaning service (cleaning equipment, spotless interior)",
        hero_clause="spotless home interior with professional cleaning equipment neatly arranged, bright daylight",
        item_clause="{item}, cleaning equipment and supplies arranged neatly in a spotless interior, bright daylight",
        verticals=("services", "general"),
        keywords=("pembersihan", "cleaning", "cuci rumah", "housekeeping", "sanitasi", "pest control", "kawalan serangga"),
    ),
    ImageSubject(
        key="tuition",
        vision_label="a tuition or learning centre (desks, books, whiteboard)",
        hero_clause="bright tuition classroom with desks, books and a clean whiteboard, no people, daylight",
        item_clause="{item}, textbooks and stationery on a tidy desk in a bright classroom, no people",
        verticals=("services", "general"),
        keywords=("tuisyen", "tuition", "kelas", "pusat tuisyen", "mengaji", "tadika", "kindergarten", "akademi", "bimbingan"),
    ),
    ImageSubject(
        key="photography",
        vision_label="a photography or creative studio (camera, lights, backdrop)",
        hero_clause="the photographer's work: cinematic silhouette composition at golden hour, elegant venue backdrop, faces not visible, professional photography",
        item_clause="{item}, artistic professional photography, cinematic silhouette and candid detail shots, faces not visible, golden hour lighting",
        verticals=("services", "general"),
        keywords=("fotografi", "photography", "photographer", "jurugambar", "videografi", "videography", "studio", "photo booth"),
    ),
    ImageSubject(
        key="fitness",
        vision_label="a gym or fitness studio (equipment, mats, weights)",
        hero_clause="bright fitness studio with dumbbells, mats and equipment neatly arranged, no people",
        item_clause="{item}, fitness equipment for it arranged in a bright studio, no people",
        verticals=("services", "general"),
        keywords=("gym", "fitness", "senaman", "yoga", "pilates", "muay thai", "personal trainer"),
    ),
    ImageSubject(
        key="clinic",
        vision_label="a clinic or wellness centre (treatment room, equipment)",
        hero_clause="clean bright clinic treatment room with equipment neatly arranged, no people",
        item_clause="{item}, clinic equipment and supplies in a clean bright treatment room, no people",
        verticals=("services", "general"),
        keywords=("klinik", "clinic", "dental", "gigi", "fisioterapi", "physio", "urut", "massage", "rawatan"),
    ),
    ImageSubject(
        key="pets",
        vision_label="a pet grooming or pet shop (grooming table, pet supplies)",
        hero_clause="pet grooming salon with a grooming table, brushes and supplies, clean and bright",
        item_clause="{item}, pet grooming tools and supplies on a clean table, bright interior",
        verticals=("services", "general"),
        keywords=("pet", "haiwan", "kucing", "anjing", "grooming haiwan", "petshop", "pet shop"),
    ),
    ImageSubject(
        key="carwash",
        vision_label="a car wash or auto detailing bay (car, foam, water, detailing tools)",
        hero_clause="car wash bay with a freshly washed car, foam and water spray, detailing tools, bright daylight",
        item_clause="{item}, car detailing tools and products beside a clean car in a wash bay",
        verticals=("services", "general"),
        keywords=("car wash", "cuci kereta", "detailing", "polish kereta", "coating"),
    ),
    ImageSubject(
        key="printing",
        vision_label="a printing or signage shop (printer, paper, banner rolls)",
        hero_clause="print shop with a large-format printer, paper rolls and finished prints stacked neatly, bright interior",
        item_clause="{item}, printed samples and materials on a clean table in a print shop",
        verticals=("services", "general"),
        keywords=("printing", "cetak", "percetakan", "banner", "bunting", "sticker", "signage"),
    ),
    ImageSubject(
        key="florist",
        vision_label="a florist (flowers, bouquets, vases)",
        hero_clause="florist shop with fresh flower bouquets in vases and buckets, soft daylight",
        item_clause="{item}, fresh flower arrangement on a clean table, soft daylight",
        verticals=("general", "services"),
        keywords=("florist", "bunga", "flower", "bouquet", "jambangan"),
    ),
    ImageSubject(
        key="clothing",
        vision_label="clothing or fashion (garment flat-lay or on a mannequin)",
        hero_clause="flat-lay of folded garments on a plain surface or a garment on a mannequin, clean studio lighting",
        item_clause="flat-lay or mannequin shot of {item}, plain background, clean studio lighting, product photography",
        verticals=("clothing",),
        keywords=("baju", "kurung", "kebaya", "hijab", "tudung", "fesyen", "fashion", "pakaian", "apparel", "clothing", "garment", "streetwear", "butik", "boutique", "t-shirt", "jersey"),
    ),
    ImageSubject(
        key="retail",
        vision_label="retail products on display (product photography)",
        hero_clause="the shop's products arranged on a plain surface, clean studio lighting, product photography",
        item_clause="product photography of {item} on a plain surface, clean studio lighting",
        verticals=("general", "clothing"),
        keywords=("kedai", "runcit", "produk", "product", "gadget", "telefon", "hardware", "aksesori", "accessories", "borong", "online shop"),
    ),
    ImageSubject(
        key="services_generic",
        vision_label="a service business workspace (tools and equipment of the trade, no people)",
        hero_clause="the tools and equipment of the service laid out in a clean, bright workspace, no people, product photography",
        item_clause="{item}, the tools and equipment for it laid out in a clean bright workspace, no people",
        verticals=("services",),
    ),
)

_BY_KEY: Dict[str, ImageSubject] = {s.key: s for s in SUBJECTS}
_VERTICAL_DEFAULT = {
    "services": "services_generic",
    "salon": "salon",
    "clothing": "clothing",
    "general": "retail",
}


def is_fnb_vertical(vertical: Optional[str]) -> bool:
    return (vertical or "").lower() in ("food", "bakery")


def subject_for(vertical: Optional[str], *texts: Optional[str]) -> Optional[ImageSubject]:
    """The image subject for a non-F&B business, from the merchant's own
    words first and the vertical's default second. None for F&B (the
    curated dish prompts own that path)."""
    v = (vertical or "general").lower()
    if is_fnb_vertical(v):
        return None
    haystack = " ".join(t for t in texts if t).lower()
    best: Optional[Tuple[int, ImageSubject]] = None
    for subject in SUBJECTS:
        if not subject.keywords:
            continue
        score = sum(2 if " " in kw else 1 for kw in subject.keywords if kw in haystack)
        if score:
            # The merchant's words decide; the vertical only breaks ties.
            score += 1 if v in subject.verticals else 0
            if best is None or score > best[0]:
                best = (score, subject)
    if best:
        return best[1]
    return _BY_KEY.get(_VERTICAL_DEFAULT.get(v, "retail"))


def scrub_fnb_wording(prompt: str) -> str:
    """Remove F&B words from a non-F&B prompt (the words, not the sentence)."""
    cleaned = _FNB_WORD_RE.sub("", prompt or "")
    cleaned = re.sub(r"\s*,\s*,+", ",", cleaned)
    cleaned = re.sub(r"\s{2,}", " ", cleaned)
    cleaned = re.sub(r"^[\s,]+|[\s,]+$", "", cleaned)
    return cleaned


def has_fnb_wording(prompt: str) -> bool:
    return bool(_FNB_WORD_RE.search(prompt or ""))


def with_negative(prompt: str) -> str:
    """Append the universal negative prompt as positive-phrased exclusions
    (idempotent) — for providers with no negative_prompt field."""
    text = (prompt or "").rstrip().rstrip(",")
    if "no people's faces" in text.lower():
        return text
    return f"{text}, {NEGATIVE_PROMPT}"


def lock_prompt(
    kind: str,
    subject: ImageSubject,
    *,
    item: Optional[str] = None,
    context: Optional[str] = None,
    extra: Optional[str] = None,
) -> str:
    """Build a category-locked prompt: subject clause first, then the item
    and the business context (and any extra composition clause), F&B
    wording scrubbed, negative appended."""
    if kind == "hero":
        body = subject.hero_clause
    else:
        body = subject.item_clause.format(item=(item or "the service").strip())
    if context:
        body = f"{body}, for the business: {scrub_fnb_wording(context)}"
    if extra:
        body = f"{body}, {extra.strip().rstrip(',')}"
    return with_negative(scrub_fnb_wording(body))


def stricter_prompt(prompt: str) -> str:
    """Second attempt after a failed vision check: an empty scene, nothing
    written anywhere, nobody in frame."""
    base = (prompt or "").rstrip()
    if base.lower().endswith(NEGATIVE_PROMPT.lower()):
        base = base[: -len(NEGATIVE_PROMPT)].rstrip().rstrip(",")
    return (
        f"{base}, empty scene with no people at all, no hands, no faces, absolutely no text or lettering "
        f"or numbers or signs anywhere in the image, plain surfaces, {NEGATIVE_PROMPT}"
    )
