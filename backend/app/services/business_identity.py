"""Business-name resolution — one place that decides what a site is called.

WHY THIS EXISTS
---------------
The simple generation path built its AI request with

    business_name = description.split()[0]

so the merchant's actual name (already sent by the client as `business_name`)
was thrown away and the model was handed the first word of the free-text
brief. When that word carried no identity the model invented one, and a real
generation shipped with the literal Malay word for "shop" in every identity
surface at once:

    <h1>Kedai</h1>, <title>Kedai — …</title>, og:title "Kedai",
    JSON-LD "name":"Kedai", footer "© 2026 Kedai"

A generic noun in structured data is worse than a missing one: Google reads
JSON-LD, and a merchant who shares that link looks like they never finished
setting the site up.

THE RULE
--------
A site is never named by a fallback. Either

  (a) the merchant typed a name, or
  (b) a name can be read out of their own brief with confidence, or
  (c) generation is blocked with "Nama kedai wajib".

There is no (d). `resolve_business_name()` implements (a)/(b);
`is_generic_business_name()` is the gate that makes (c) fire, and the
post-generation validator uses the same predicate on the rendered page so a
model that invents "Kedai Kami" on its own is caught too.

Pure functions, no I/O — safe to call from the endpoint, the generator and
the validator alike.
"""

from __future__ import annotations

import re
from typing import List, Optional

#: Shop-type / legal-entity nouns that carry no identity on their own.
#: "Kedai" is a business, "Kedai Pak Mat" is a name.
GENERIC_NAME_WORDS = frozenset({
    # Malay shop types
    "kedai", "restoran", "restaurant", "warung", "gerai", "kafe", "cafe",
    "bakeri", "bakery", "katering", "catering", "butik", "boutique",
    "salon", "klinik", "clinic", "studio", "pusat", "syarikat", "perniagaan",
    "bisnes", "business", "shop", "store", "outlet", "stall", "enterprise",
    "trading", "resources", "services", "servis", "company", "brand",
    # Possessives / filler the model appends to make a fallback look intentional
    "kami", "saya", "anda", "kita", "my", "our", "your", "the", "and", "dan",
    "sdn", "bhd", "plt", "enterprise", "ent",
    # Bare placeholders seen in production output
    "untitled", "example", "sample", "demo", "test", "placeholder", "name",
    "nama", "website", "laman", "web",
})

#: Type nouns that legitimately START a real name ("Restoran Nasi Kandar
#: Crystal"). Used to anchor extraction, never to accept a name on their own.
_TYPE_PREFIXES = (
    "kedai", "restoran", "restaurant", "warung", "gerai", "kafe", "cafe",
    "bakeri", "bakery", "katering", "salon", "klinik", "butik", "studio",
    "pusat",
)

#: Places are not identities. A candidate whose every distinguishing word is
#: a Malaysian place name is the merchant's location, not their shop.
_PLACE_WORDS = frozenset({
    "malaysia", "kuala", "lumpur", "kl", "selangor", "shah", "alam", "klang",
    "subang", "jaya", "petaling", "ampang", "cheras", "puchong", "serdang",
    "bangi", "kajang", "rawang", "gombak", "sepang", "nilai", "seremban",
    "penang", "pulau", "pinang", "georgetown", "johor", "bahru", "ipoh",
    "perak", "kedah", "alor", "setar", "kelantan", "kota", "bharu",
    "terengganu", "kuala", "pahang", "kuantan", "melaka", "malacca",
    "negeri", "sembilan", "sabah", "sarawak", "kuching", "kinabalu",
    "putrajaya", "cyberjaya", "perlis", "kangar", "labuan", "utara",
    "selatan", "timur", "barat", "tengah",
})

#: "nama kedai saya ialah X" / "business name: X" — the merchant telling us
#: outright. The separator is REQUIRED: without it the capture swallows the
#: possessive and yields "saya ialah Warung Kak Ropiah".
_NAME_MARKER_RES = (
    re.compile(
        r"""(?:nama|name)\s+
            (?:kedai|restoran|warung|gerai|kafe|cafe|bisnes|perniagaan
              |syarikat|business|shop|store)?\s*
            (?:saya|kami|kita|aku|my|our)?\s*
            (?::|ialah|adalah|\bis\b|=)\s*
            (?P<name>[^.,;\n!?]{2,60})
        """,
        re.IGNORECASE | re.VERBOSE,
    ),
    re.compile(r"bernama\s+(?P<name>[^.,;\n!?]{2,60})", re.IGNORECASE),
)

#: A quoted name: "Nasi Kandar Daging Crystal" / 'Warung Kak Ropiah'.
_QUOTED_RE = re.compile(r"""["“'‘]([^"”'’\n]{3,60})["”'’]""")

#: A shop-type noun followed by CAPITALISED words: "Restoran Nasi Kandar".
#: The type word is matched case-insensitively (merchants type "kedai"), the
#: tail is NOT — an all-lowercase tail is prose, not a name, and matching it
#: case-insensitively turned "jual nasi lemak sedap di shah alam" into a
#: business called "nasi lemak sedap di shah".
_ANCHORED_NAME_RE = re.compile(
    r"\b((?i:" + "|".join(_TYPE_PREFIXES) + r")(?:\s+[A-Z][\w'’\-]*){1,4})\b"
)

#: A run of capitalised words, optionally carrying & / bin / binti / a number.
_TITLE_RUN_RE = re.compile(
    r"\b(?:[A-Z][\w'’\-]*|&)(?:\s+(?:[A-Z][\w'’\-]*|&|bin|binti|dan|of|\d{1,4})){0,5}\b"
)

_MAX_NAME_WORDS = 6


def _words(value: str) -> List[str]:
    return [w for w in re.findall(r"[\w'’\-&]+", str(value or "")) if w]


def _tidy(candidate: str) -> str:
    """Trim a raw candidate to something usable as a display name."""
    text = re.sub(r"\s+", " ", str(candidate or "")).strip(" \t\-–—,;:.\"'“”‘’")
    if not text:
        return ""
    words = text.split(" ")
    if len(words) > _MAX_NAME_WORDS:
        words = words[:_MAX_NAME_WORDS]
    # Merchants type "kedai Pak Mat"; the shopfront says "Kedai Pak Mat".
    if words and words[0].islower() and words[0].lower() in _TYPE_PREFIXES:
        words[0] = words[0].capitalize()
    return " ".join(words).strip(" \t\-–—,;:.")


def is_generic_business_name(name: Optional[str]) -> bool:
    """True when `name` carries no business identity of its own.

    Empty, a bare shop-type noun ("Kedai", "Restoran"), a shop type plus a
    possessive ("Kedai Kami", "My Business"), or a pure placeholder
    ("Untitled", "Business"). Anything with at least one distinguishing word
    is a real name, however plain — "Kedai Pak Mat" is somebody's shop.
    """
    tokens = [w.lower() for w in _words(name)]
    if not tokens:
        return True
    # A name made only of type nouns / possessives / placeholders is generic.
    if all(t in GENERIC_NAME_WORDS for t in tokens):
        return True
    distinctive = [t for t in tokens if t not in GENERIC_NAME_WORDS]
    if not distinctive:
        return True
    # A short or numeric distinguisher is still a distinguisher: "Kedai A"
    # and "Kedai 2" are real shopfronts. Only a name with NOTHING of its own
    # is generic — being stricter here blocks real merchants, which is the
    # worse failure of the two.
    # "Shah Alam", "Kuala Lumpur" — where they are, not who they are.
    if all(t in _PLACE_WORDS for t in distinctive):
        return True
    return False


def _candidates_from_description(description: str) -> List[str]:
    """Ordered name candidates read out of the merchant's own brief."""
    text = re.sub(r"\s+", " ", str(description or "")).strip()
    if not text:
        return []

    out: List[str] = []

    # 1. An explicit "nama kedai ialah …" marker is the merchant telling us.
    for pattern in _NAME_MARKER_RES:
        for match in pattern.finditer(text):
            out.append(_tidy(match.group("name")))

    # 2. A quoted phrase is almost always the name.
    for match in _QUOTED_RE.finditer(text):
        out.append(_tidy(match.group(1)))

    # 3. A type noun followed by capitalised words: "Restoran Nasi Kandar
    #    Crystal". Anchored on the type word so we keep it in the name.
    for match in _ANCHORED_NAME_RE.finditer(text):
        out.append(_tidy(match.group(1)))

    # 4. A capitalised run in the opening clause — merchants usually lead with
    #    the name ("Nasi Kandar Daging Crystal, buka 24 jam …").
    head = text.split(".")[0][:160]
    for match in _TITLE_RUN_RE.finditer(head):
        out.append(_tidy(match.group(0)))

    seen = set()
    unique: List[str] = []
    for candidate in out:
        key = candidate.lower()
        if candidate and key not in seen:
            seen.add(key)
            unique.append(candidate)
    return unique


def derive_business_name(description: str) -> str:
    """Best real name readable from the brief, or '' when there is none.

    Never invents. Returns '' rather than a plausible-looking guess, because
    the caller's correct response to '' is to ask the merchant — not to ship
    a word we made up.
    """
    for candidate in _candidates_from_description(description):
        if not is_generic_business_name(candidate):
            return candidate
    return ""


def resolve_business_name(
    business_name: Optional[str], description: str = ""
) -> str:
    """The name to generate under: merchant's own, else read from the brief.

    '' means "no usable name" — callers MUST block generation and ask,
    never substitute a placeholder.
    """
    typed = _tidy(business_name or "")
    if typed and not is_generic_business_name(typed):
        return typed
    derived = derive_business_name(description)
    if derived:
        return derived
    # A generic-but-typed name is still the merchant's own words; prefer it
    # over nothing only when they actually typed something with a letter in
    # it AND it is not a bare type noun. (is_generic_business_name already
    # rejected that, so reaching here means we have nothing.)
    return ""


#: Message shown when generation is blocked for want of a name.
MISSING_NAME_MESSAGE = {
    "ms": "Nama kedai wajib. Sila isi nama perniagaan anda sebelum menjana laman.",
    "en": "Business name is required. Please enter your business name before generating.",
}


def missing_name_message(language: str = "ms") -> str:
    lang = "en" if str(language or "ms").lower().startswith("en") else "ms"
    return MISSING_NAME_MESSAGE[lang]
