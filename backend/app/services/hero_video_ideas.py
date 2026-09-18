"""Prompt ideas for the hero video card — curated, static, no AI call.

The merchant's own words are the best motion prompt the clip can get
(see ``build_hero_video_prompt``: what they type LEADS the prompt), and the
blank textarea is where most of them stop. A handful of short, concrete
scene ideas for their kind of business — steam off a wok, a shawl catching
the light, a barber's chair turning — gets them writing, and every idea
here obeys the rules the suffix enforces (no text, no faces to camera,
gentle continuous motion) so a tapped idea is a good prompt as-is.

    ideas_for("food")           → the food list
    ideas_for("kedai runcit")   → the retail list (normalised first)
    ideas_for("")               → the general list

Each idea is ``{"key", "ms", "en"}``; the dashboard shows ``ms`` and sends
whichever the merchant tapped as the ``prompt``.
"""

from __future__ import annotations

from typing import Dict, List

#: Ideas per BUSINESS_TYPE_VALUES key (``business_types.normalize_business_type``),
#: plus a general list for anything it cannot place.
_IDEAS: Dict[str, List[Dict[str, str]]] = {
    "food": [
        {"key": "food-wok", "ms": "Asap naik perlahan dari kuali panas, api biru di bawahnya",
         "en": "Steam rising slowly from a hot wok, blue flame beneath it"},
        {"key": "food-pour", "ms": "Kopi dituang perlahan ke dalam cawan, wap naik ke atas",
         "en": "Coffee poured slowly into a cup, steam rising"},
        {"key": "food-grill", "ms": "Sate dibakar di atas bara, percikan api kecil",
         "en": "Satay grilling over glowing embers, tiny sparks"},
        {"key": "food-table", "ms": "Kamera bergerak perlahan merentasi meja penuh hidangan",
         "en": "Camera drifting slowly across a table full of dishes"},
        {"key": "food-night", "ms": "Lampu warung berkelip lembut waktu senja, orang lalu-lalang kabur",
         "en": "Warm stall lights glowing at dusk, blurred passers-by"},
    ],
    "bakery": [
        {"key": "bakery-oven", "ms": "Roti keemasan dikeluarkan dari ketuhar, wap keluar perlahan",
         "en": "Golden bread pulled from the oven, steam drifting out"},
        {"key": "bakery-frost", "ms": "Krim dipaipkan perlahan di atas kek, cahaya lembut",
         "en": "Cream being piped slowly onto a cake, soft light"},
        {"key": "bakery-flour", "ms": "Tepung ditabur lembut, cahaya pagi menembusi tingkap",
         "en": "Flour dusting gently, morning light through a window"},
        {"key": "bakery-display", "ms": "Kamera bergerak perlahan melalui rak pastri berkilat",
         "en": "Camera gliding slowly past a shelf of glossy pastries"},
    ],
    "clothing": [
        {"key": "cloth-fabric", "ms": "Kain sutera berombak lembut ditiup angin, cahaya keemasan",
         "en": "Silk fabric rippling softly in a breeze, golden light"},
        {"key": "cloth-rail", "ms": "Kamera bergerak perlahan melalui rak baju berwarna-warni",
         "en": "Camera drifting slowly along a rail of colourful clothes"},
        {"key": "cloth-turn", "ms": "Gaun berputar perlahan di atas manekin, butiran debu bercahaya",
         "en": "A dress turning slowly on a mannequin, dust motes glowing"},
        {"key": "cloth-shawl", "ms": "Selendang dilipat perlahan, tekstur kain jelas kelihatan",
         "en": "A shawl folding slowly, fabric texture in close-up"},
    ],
    "salon": [
        {"key": "salon-chair", "ms": "Kerusi salun berpusing sangat perlahan, cermin memantulkan cahaya",
         "en": "A salon chair turning very slowly, mirror catching the light"},
        {"key": "salon-hair", "ms": "Rambut ditiup lembut oleh pengering, cahaya hangat",
         "en": "Hair lifted gently by a blow dryer, warm light"},
        {"key": "salon-spa", "ms": "Lilin berkelip dan kelopak bunga terapung di atas air",
         "en": "Candles flickering and petals floating on water"},
        {"key": "salon-tools", "ms": "Kamera bergerak perlahan merentasi alat salun yang tersusun kemas",
         "en": "Camera drifting slowly across neatly arranged salon tools"},
    ],
    "services": [
        {"key": "svc-workshop", "ms": "Percikan api kecil dari alat, cahaya bengkel yang hangat",
         "en": "Small sparks from a tool, warm workshop light"},
        {"key": "svc-hands", "ms": "Tangan bekerja perlahan dengan teliti, fokus cetek",
         "en": "Hands working slowly and carefully, shallow focus"},
        {"key": "svc-office", "ms": "Cahaya pagi bergerak perlahan merentasi meja kerja yang kemas",
         "en": "Morning light moving slowly across a tidy desk"},
        {"key": "svc-road", "ms": "Kenderaan bergerak perlahan di jalan waktu pagi, sedikit kabus",
         "en": "A vehicle moving slowly down a road at dawn, light mist"},
    ],
    "general": [
        {"key": "gen-light", "ms": "Cahaya pagi menembusi tingkap, butiran debu terapung perlahan",
         "en": "Morning light through a window, dust motes drifting slowly"},
        {"key": "gen-street", "ms": "Jalan bandar waktu senja, lampu berkelip, orang lalu-lalang kabur",
         "en": "A city street at dusk, lights glowing, blurred passers-by"},
        {"key": "gen-nature", "ms": "Daun bergoyang perlahan ditiup angin, cahaya matahari lembut",
         "en": "Leaves swaying slowly in a breeze, soft sunlight"},
        {"key": "gen-water", "ms": "Riak air yang tenang memantulkan cahaya keemasan",
         "en": "Calm water ripples reflecting golden light"},
        {"key": "gen-shop", "ms": "Kamera bergerak perlahan merentasi kedai yang kemas dan terang",
         "en": "Camera drifting slowly across a bright, tidy shop"},
    ],
}

#: How many ideas an answer carries, at most: enough to spark, few enough
#: to read on a phone.
MAX_IDEAS = 6


def ideas_for(business_type: str, limit: int = MAX_IDEAS) -> List[Dict[str, str]]:
    """The ideas for a business type (any spelling ``normalize_business_type``
    accepts), padded with general ones so every answer has a few."""
    from app.services.business_types import normalize_business_type

    kind = normalize_business_type(business_type) or "general"
    ideas = list(_IDEAS.get(kind) or [])
    if kind != "general":
        seen = {idea["key"] for idea in ideas}
        ideas += [idea for idea in _IDEAS["general"] if idea["key"] not in seen]
    return [dict(idea) for idea in ideas[: max(1, limit)]]


def idea_business_types() -> List[str]:
    return list(_IDEAS.keys())
