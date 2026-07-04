"""Golden prompt set for side-by-side pipeline comparison (M0).

Six Malaysian F&B scenarios, each phrased twice:
  - BM  (Bahasa Malaysia, language="ms")
  - Manglish (colloquial Malaysian English, language="en") — stresses
    intent extraction on informal register.

These are FIXED. Do not edit existing prompts (that would invalidate
historical comparisons); append new ones with new ids instead.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass(frozen=True)
class GoldenPrompt:
    id: str
    scenario: str
    language: str  # "ms" | "en"
    business_name: str
    description: str
    color_mode: str = "light"
    features: Dict[str, bool] = field(default_factory=lambda: {"whatsapp": True})
    whatsapp_number: Optional[str] = "+60123456789"


GOLDEN_PROMPTS: List[GoldenPrompt] = [
    # 1 — retro neon mamak for students
    GoldenPrompt(
        id="mamak_neon_bm",
        scenario="retro_neon_mamak",
        language="ms",
        business_name="Mamak Bintang 24 Jam",
        color_mode="dark",
        description=(
            "Saya nak website untuk Mamak Bintang, mamak 24 jam di Bangi. "
            "Famous dengan roti canai garing dan teh tarik. Suasana meriah, "
            "ramai student lepak malam-malam. Nak gaya retro neon sikit, "
            "macam pasar malam dengan lampu neon."
        ),
    ),
    GoldenPrompt(
        id="mamak_neon_manglish",
        scenario="retro_neon_mamak",
        language="en",
        business_name="Mamak Bintang 24 Jam",
        color_mode="dark",
        description=(
            "Boss, I want website for my mamak stall in Bangi lah. Open 24 hours, "
            "students all lepak here until 3am one. Our roti canai damn garing, "
            "teh tarik also power. Want that retro neon vibe, like pasar malam "
            "lights, don't want boring corporate look."
        ),
    ),
    # 2 — bright family mamak
    GoldenPrompt(
        id="mamak_family_bm",
        scenario="bright_family_mamak",
        language="ms",
        business_name="Restoran Nasi Kandar Keluarga",
        description=(
            "Website untuk restoran nasi kandar keluarga di Seremban. Terang, "
            "mesra keluarga, sesuai bawa anak-anak. Menu nasi kandar, ayam "
            "goreng berempah, roti canai. Kami pengusaha Muslim, buka setiap "
            "hari 7 pagi hingga 10 malam."
        ),
    ),
    GoldenPrompt(
        id="mamak_family_manglish",
        scenario="bright_family_mamak",
        language="en",
        business_name="Restoran Nasi Kandar Keluarga",
        description=(
            "Need a website for my family nasi kandar restaurant in Seremban. "
            "Very family friendly one, bring the whole kampung also can. Bright "
            "and cheerful feel please, not those dark moody cafe style. We are "
            "Muslim-owned, open every day 7am to 10pm."
        ),
    ),
    # 3 — kopitiam nostalgia
    GoldenPrompt(
        id="kopitiam_bm",
        scenario="kopitiam_nostalgia",
        language="ms",
        business_name="Kopitiam Warisan Ipoh",
        description=(
            "Kopitiam lama di Ipoh sejak 1962. Kopi putih Ipoh, roti bakar kaya, "
            "telur separuh masak. Nak rasa nostalgia zaman dulu — jubin lama, "
            "kerusi kayu, suasana klasik. Website mesti ada cerita sejarah "
            "keluarga kami tiga generasi."
        ),
    ),
    GoldenPrompt(
        id="kopitiam_manglish",
        scenario="kopitiam_nostalgia",
        language="en",
        business_name="Kopitiam Warisan Ipoh",
        description=(
            "Our kopitiam in Ipoh old town, running since 1962 three generations "
            "already. White coffee, kaya toast, half boiled eggs — the classics "
            "lah. Want that old school nostalgia feeling, vintage tiles, marble "
            "table tops. Must tell our family story also."
        ),
    ),
    # 4 — fine dining
    GoldenPrompt(
        id="finedining_bm",
        scenario="fine_dining",
        language="ms",
        business_name="Hidang by Chef Rahim",
        color_mode="dark",
        description=(
            "Restoran fine dining masakan Melayu moden di Kuala Lumpur. "
            "Pengalaman menu degustasi 7 hidangan, plating halus, bahan "
            "tempatan premium. Suasana mewah dan eksklusif, tempahan sahaja. "
            "Website perlu nampak premium dan elegan, warna gelap dengan "
            "sentuhan emas."
        ),
    ),
    GoldenPrompt(
        id="finedining_manglish",
        scenario="fine_dining",
        language="en",
        business_name="Hidang by Chef Rahim",
        color_mode="dark",
        description=(
            "High end modern Malay fine dining in KL. 7-course degustation, "
            "premium local ingredients, very atas plating. Reservation only. "
            "Website must look expensive — dark, elegant, gold accents, the "
            "kind of site where people expect to pay RM400 per head."
        ),
    ),
    # 5 — catering (large-scale Malay wedding/event catering)
    GoldenPrompt(
        id="catering_bm",
        scenario="event_catering",
        language="ms",
        business_name="Aneka Rasa Katering",
        description=(
            "Syarikat katering untuk majlis perkahwinan dan korporat di Shah Alam. "
            "Pakej kenduri lengkap dengan pelamin, kanopi dan buffet — nasi "
            "minyak, ayam masak merah, daging salai masak lemak. Dah 15 tahun "
            "berkhidmat, beribu majlis. Nak website nampak grand dan meriah "
            "macam butik pengantin besar, penuh warna tradisional."
        ),
    ),
    GoldenPrompt(
        id="catering_manglish",
        scenario="event_catering",
        language="en",
        business_name="Aneka Rasa Katering",
        description=(
            "We do wedding and corporate catering in Shah Alam — full kenduri "
            "package, pelamin, canopy, buffet line all in. 15 years in the "
            "business, thousands of events done. Want the website to feel grand "
            "and festive like those big bridal boutique showrooms, rich "
            "traditional colours, not plain and boring."
        ),
    ),
    # 6 — minimalist cafe
    GoldenPrompt(
        id="cafe_minimal_bm",
        scenario="cafe_minimalist",
        language="ms",
        business_name="Ruang Kopi",
        description=(
            "Kafe specialty coffee minimalis di Bangsar. Kopi single origin, "
            "pastri artisan, susu oat. Konsep bersih dan tenang — putih, kayu "
            "cerah, banyak ruang kosong. Pelanggan kami suka bekerja dari kafe. "
            "Website mesti simple, bersih, banyak white space."
        ),
    ),
    GoldenPrompt(
        id="cafe_minimal_manglish",
        scenario="cafe_minimalist",
        language="en",
        business_name="Ruang Kopi",
        description=(
            "Minimalist specialty coffee cafe in Bangsar. Single origin beans, "
            "artisan pastries, oat milk everything. Clean calm concept — white "
            "walls, light wood, lots of empty space. Customers come here to "
            "work on laptops. Website must be super clean and simple, plenty "
            "of white space, no clutter."
        ),
    ),
]

PROMPTS_BY_ID: Dict[str, GoldenPrompt] = {p.id: p for p in GOLDEN_PROMPTS}
