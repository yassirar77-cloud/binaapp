"""
Cuisine-Specific Image Pools — curated Unsplash CDN URLs for Malaysian food.

Each image uses the correct Unsplash CDN format:
  https://images.unsplash.com/photo-{CDN_ID}?w=800&h=600&fit=crop&q=80

Usage:
    from app.data.malaysian_food_images import get_cuisine_images, pick_images
    images = get_cuisine_images("malay_fusion")
    hero, gallery, menu = pick_images("malay_fusion", hero=1, gallery=4, menu=3)
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Dict, List, Optional


def _url(cdn_id: str, w: int = 800, h: int = 600) -> str:
    return f"https://images.unsplash.com/{cdn_id}?w={w}&h={h}&fit=crop&q=80"


def _hero_url(cdn_id: str) -> str:
    return f"https://images.unsplash.com/{cdn_id}?w=1200&h=800&fit=crop&q=80"


@dataclass(frozen=True)
class FoodImage:
    cdn_id: str        # e.g. "photo-1688084546323-fcd3f9d8389b"
    dish: str
    category: str      # "hero", "menu_item", "ambience", "detail", "drink", "dessert"
    photographer: str

    @property
    def url(self) -> str:
        return _url(self.cdn_id)

    def hero_url(self) -> str:
        return _hero_url(self.cdn_id)


# ---------------------------------------------------------------------------
# Image pools by dish — CDN IDs resolved from Unsplash API
# ---------------------------------------------------------------------------

NASI_LEMAK: List[FoodImage] = [
    FoodImage("photo-1677921755291-c39158477b8e", "Nasi lemak with sambal and fried chicken", "menu_item", "Aldrin Rachman Pradana"),
    FoodImage("photo-1666239308347-4292ea2ff777", "Nasi lemak plate with sides", "menu_item", "Mufid Majnun"),
    FoodImage("photo-1666239308345-c4c12ef3e177", "Nasi lemak traditional presentation", "menu_item", "Mufid Majnun"),
    FoodImage("photo-1647093953000-9065ed6f85ef", "Nasi lemak with vegetables and rice", "menu_item", "Iosi Pratama"),
    FoodImage("photo-1624957389019-0c814505746d", "Nasi lemak with fried chicken on ceramic plate", "hero", "Takashi Miyazaki"),
    FoodImage("photo-1666239308046-ead0314ee0fe", "Nasi lemak traditional", "menu_item", "Mufid Majnun"),
    FoodImage("photo-1541832676-9b763b0239ab", "Nasi lemak on black plate", "hero", "Louis Hansel"),
    FoodImage("photo-1770966485209-e20d97337f1a", "Nasi lemak on banana leaf with spoon", "hero", "You Le"),
    FoodImage("photo-1740969136580-05d6f2d1838c", "Nasi lemak with several side dishes", "hero", "You Le"),
    FoodImage("photo-1777113310112-d4f115599921", "Nasi lemak platter with egg and peanuts", "menu_item", "note thanun"),
    FoodImage("photo-1600015835779-c6b36ddeac1f", "Rice with meat on white ceramic plate", "menu_item", "Faisal"),
    FoodImage("photo-1561741858-cefa7ca99edf", "Plate of rice and cooked food", "menu_item", "Baiq Daling"),
    FoodImage("photo-1707270686195-7415251cc9c0", "White plate with rice and vegetables", "menu_item", "Inna Safa"),
]

RENDANG: List[FoodImage] = [
    FoodImage("photo-1688084546323-fcd3f9d8389b", "Rendang in bowl close-up", "hero", "Christian Dala"),
    FoodImage("photo-1688084442478-3b499d17126f", "Beef rendang close-up", "detail", "Christian Dala"),
    FoodImage("photo-1766567461692-32c352d198d4", "Spicy chicken rendang with chili", "menu_item", "dika Mahendra"),
    FoodImage("photo-1612870422157-7dac0887af89", "Rendang on white ceramic plate", "menu_item", "Junior REIS"),
    FoodImage("photo-1606143704849-eb181ba1543a", "Rendang in bowl", "menu_item", "qaz farid"),
    FoodImage("photo-1550367363-ea12860cc124", "Rendang ribs", "detail", "Faisal"),
    FoodImage("photo-1740993382497-65dba6c7a689", "Beef stew in brown bowl", "menu_item", "Zulfahmi Al Ridhawi"),
    FoodImage("photo-1692757299006-8e047baddfa1", "Rendang with carrots on wooden plate", "menu_item", "Mizan Adlan"),
    FoodImage("photo-1642509600566-96fe95a744b3", "Rendang with rice on white plate", "menu_item", "Itadaki"),
]

ROTI_CANAI: List[FoodImage] = [
    FoodImage("photo-1768967032487-b6ef958a017e", "Crispy roti canai with dipping sauce", "menu_item", "You Le"),
]

LAKSA: List[FoodImage] = [
    FoodImage("photo-1775986501486-380ea9539e07", "Creamy laksa with fried toppings and drink", "hero", "Kent Chin"),
    FoodImage("photo-1767324672767-f05db5118584", "Hearty laksa stew with meat and vegetables", "menu_item", "You Le"),
    FoodImage("photo-1768703321878-564507eae1f6", "Bowls of laksa noodle soup", "menu_item", "You Le"),
    FoodImage("photo-1708607546261-e8a945cc15e6", "Laksa with noodles and shrimp in white bowl", "menu_item", "James Lo"),
    FoodImage("photo-1633271332313-04df64c0105b", "Laksa noodles with meat and vegetables", "menu_item", "Amanda Lim"),
    FoodImage("photo-1768703321913-db220381bb84", "Fish ball laksa with vegetables", "menu_item", "You Le"),
    FoodImage("photo-1740362381404-6e5c375b8afc", "Spoonful of laksa noodle soup", "detail", "Khanh Nguyen"),
]

SATAY: List[FoodImage] = [
    FoodImage("photo-1772855386828-a18ff9a12584", "Chicken satay skewers with peanut sauce", "hero", "likesilkto"),
    FoodImage("photo-1744175331258-f4758acce6ca", "Meat skewers grilling over hot coals", "ambience", "wd toro"),
    FoodImage("photo-1696385793103-71f51f6fd3b7", "Satay plate with peanut sauce", "menu_item", "K Azwan"),
    FoodImage("photo-1696385793104-745d4dd65c5a", "Satay with vegetable garnish", "menu_item", "K Azwan"),
    FoodImage("photo-1678867158236-70fa512d687f", "Satay platter on banana leaf", "hero", "Tam Mai"),
    FoodImage("photo-1768162125959-8a35d4ede7dc", "Chicken skewers with green onions", "menu_item", "Perry Merrity II"),
    FoodImage("photo-1636301175218-6994458a4b0a", "Satay cooking on grill", "ambience", "Fitria Yusrifa"),
]

NASI_KANDAR: List[FoodImage] = [
    FoodImage("photo-1751704316221-7e7e6887d0ed", "Hawker serving plates of rice", "ambience", "Kelvin Zyteng"),
    FoodImage("photo-1751704316210-5b38619aaf8f", "Chef preparing nasi kandar in busy kitchen", "ambience", "Kelvin Zyteng"),
    FoodImage("photo-1751704316216-624074fb1176", "Cook serving nasi kandar", "ambience", "Kelvin Zyteng"),
    FoodImage("photo-1600015835779-c6b36ddeac1f", "Rice with meat on white plate", "menu_item", "Faisal"),
]

TEH_TARIK: List[FoodImage] = [
    # Limited teh tarik images on Unsplash
]

KUIH: List[FoodImage] = [
    FoodImage("photo-1738225734433-9fb17ed770a4", "Kuih plate close-up", "dessert", "fabio guntur"),
    FoodImage("photo-1764349844260-1c53c2318872", "Star-shaped fried pastries on green plate", "dessert", "Kalindu Waranga"),
    FoodImage("photo-1560739086-eb6fde4babfa", "Kuih on black tray", "dessert", "wang kenan"),
    FoodImage("photo-1625021657499-deba0f2099d8", "Kuih cookies on black plate", "dessert", "pariwat pannium"),
    FoodImage("photo-1617694455303-59af55af7e58", "Kuih sliced on pan", "dessert", "Esperanza Doronila"),
    FoodImage("photo-1617694455712-77ce4c1ce7b3", "Assorted kuih on steel tray", "dessert", "Esperanza Doronila"),
]

CHAR_KWAY_TEOW: List[FoodImage] = [
    FoodImage("photo-1606143704995-52426a8a32c6", "Char kway teow", "menu_item", "qaz farid"),
    FoodImage("photo-1632660373393-c83bf5413d16", "Stir fried Penang noodles", "menu_item", "Advocator SY"),
    FoodImage("photo-1752924349474-d717ed874d98", "Fried noodles topped with egg", "menu_item", "Gilbertus Angelo"),
    FoodImage("photo-1612939675110-fe3a0129a024", "Fried noodles on white plate", "menu_item", "Fahmi Anwar"),
]

MEE_GORENG: List[FoodImage] = [
    FoodImage("photo-1645696329525-8ec3bee460a9", "Mee goreng Jawa", "menu_item", "R Eris"),
    FoodImage("photo-1680675494363-75bbf9838a09", "Mi goreng with vegetables and egg", "menu_item", "R Eris"),
    FoodImage("photo-1705088295609-3ce7befbe8ee", "Mee goreng with meat and vegetables", "menu_item", "Gourmet Lenz"),
    FoodImage("photo-1705562705207-4322c4ab4844", "Mee goreng with vegetables", "menu_item", "Yosafat Herdian"),
]

MODERN_FUSION: List[FoodImage] = [
    FoodImage("photo-1693376194231-677002aab5b2", "Asian fusion plated dish with chopsticks", "menu_item", "Curves Photography"),
    FoodImage("photo-1585144570839-e429bb95ffb4", "Fine dining Asian fusion on black ceramic", "hero", "Louis Hansel"),
    FoodImage("photo-1580876205972-0dc89bc0e336", "Modern cooked dish on white plate", "menu_item", "CHUTTERSNAP"),
    FoodImage("photo-1653666351563-6e636c00b38e", "Rendang-style meat plated with veggies", "menu_item", "sandi firmansyah"),
    FoodImage("photo-1585627990987-58ef59c709e6", "Gourmet braised chicken wings fine dining", "detail", "nmw brands"),
    FoodImage("photo-1767429013002-69b35cb45395", "Fish with creamy sauce and bok choy", "menu_item", "You Le"),
    FoodImage("photo-1621317607972-b2afed231542", "Rendang plated fine dining with lemon", "hero", "Fernandes Photographer"),
    FoodImage("photo-1569580990518-5c62fd4bdcf7", "Fusion burger on teal ceramic plate", "menu_item", "Pesce Huang"),
]

RESTAURANT_INTERIOR: List[FoodImage] = [
    FoodImage("photo-1773927005455-8efc55a8d512", "Bright cafe interior with plants and tables", "ambience", "Janelle Ang"),
    FoodImage("photo-1771830916721-c8da5d52e50f", "Cozy cafe with wooden tables", "ambience", "Elist Nguyen"),
    FoodImage("photo-1774978236593-2cac523ef549", "Cozy booth seating with lamp", "ambience", "Adhitya Sibikumar"),
    FoodImage("photo-1664428376383-799654030b72", "People sitting at restaurant table", "ambience", "Rendy Novantino"),
    FoodImage("photo-1766492281651-e893cd930191", "Cozy restaurant with wooden tables", "ambience", "aLgivari Rizchy"),
    FoodImage("photo-1771830916812-28b912eac957", "Dimly lit cafe interior", "ambience", "Elist Nguyen"),
    FoodImage("photo-1765872292853-427bc0cd8442", "Cafe with large windows and greenery", "ambience", "maxine guo"),
]


# ---------------------------------------------------------------------------
# Cuisine → Image Pool mapping
# ---------------------------------------------------------------------------

CUISINE_POOLS: Dict[str, List[List[FoodImage]]] = {
    "mamak": [ROTI_CANAI, NASI_KANDAR, MEE_GORENG, SATAY],
    "malay_fusion": [NASI_LEMAK, RENDANG, LAKSA, SATAY, KUIH, CHAR_KWAY_TEOW, MODERN_FUSION],
    "malay_traditional": [NASI_LEMAK, RENDANG, SATAY, KUIH, NASI_KANDAR],
    "fine_dining_malay": [RENDANG, LAKSA, NASI_LEMAK, SATAY, KUIH, MODERN_FUSION],
    "kopitiam_chinese": [CHAR_KWAY_TEOW, MEE_GORENG, LAKSA],
    "fast_food_halal": [SATAY, MEE_GORENG, NASI_LEMAK, ROTI_CANAI],
    "warung_kampung": [NASI_LEMAK, RENDANG, NASI_KANDAR, SATAY, MEE_GORENG],
    "cafe_modern": [LAKSA, NASI_LEMAK, KUIH, RENDANG, MODERN_FUSION],
    "western_halal": [RENDANG, SATAY, LAKSA],
    "thai_halal": [LAKSA, SATAY, MEE_GORENG],
    "indian_halal": [ROTI_CANAI, NASI_KANDAR],
    "nyonya": [LAKSA, KUIH, CHAR_KWAY_TEOW, NASI_LEMAK],
}


def get_cuisine_images(cuisine_type: str) -> List[FoodImage]:
    """Get all images for a cuisine type, flattened from pools."""
    pools = CUISINE_POOLS.get(cuisine_type, [])
    all_images: List[FoodImage] = []
    for pool in pools:
        all_images.extend(pool)
    return all_images


def pick_images(
    cuisine_type: str,
    hero: int = 1,
    gallery: int = 4,
    menu: int = 3,
    seed: Optional[int] = None,
) -> Dict[str, List[FoodImage]]:
    """Pick non-repeating images for each slot from the cuisine pool."""
    all_images = get_cuisine_images(cuisine_type)
    if not all_images:
        return {"hero": [], "gallery": [], "menu": []}

    rng = random.Random(seed)
    used_ids: set = set()

    def _pick(pool: List[FoodImage], count: int, preferred_cat: Optional[str] = None) -> List[FoodImage]:
        available = [img for img in pool if img.cdn_id not in used_ids]
        if preferred_cat:
            preferred = [img for img in available if img.category == preferred_cat]
            rest = [img for img in available if img.category != preferred_cat]
            ordered = preferred + rest
        else:
            ordered = list(available)
        rng.shuffle(ordered)
        picked = ordered[:count]
        for img in picked:
            used_ids.add(img.cdn_id)
        return picked

    hero_picks = _pick(all_images, hero, "hero")
    gallery_picks = _pick(all_images, gallery, "ambience")
    menu_picks = _pick(all_images, menu, "menu_item")

    return {
        "hero": hero_picks,
        "gallery": gallery_picks,
        "menu": menu_picks,
    }


def build_image_map(
    cuisine_type: str,
    gallery_count: int = 4,
    menu_count: int = 3,
    seed: Optional[int] = None,
) -> Dict[str, str]:
    """Build a complete image_map dict ready for DesignBrief."""
    picks = pick_images(cuisine_type, hero=1, gallery=gallery_count, menu=menu_count, seed=seed)

    image_map: Dict[str, str] = {}

    if picks["hero"]:
        image_map["hero"] = picks["hero"][0].hero_url()

    for i, img in enumerate(picks["gallery"], 1):
        image_map[f"gallery_{i}"] = img.url

    for i, img in enumerate(picks["menu"], 1):
        image_map[f"menu_{i}"] = img.url

    # Add an interior shot
    rng = random.Random(seed)
    interior = list(RESTAURANT_INTERIOR)
    rng.shuffle(interior)
    if interior:
        image_map["interior"] = interior[0].url

    return image_map
