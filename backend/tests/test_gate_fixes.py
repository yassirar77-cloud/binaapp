"""The visual gate after the first live builds (agp, mamak on Standard).

- mamak failed for "cut off at the bottom edge" on every menu card: the
  screenshot slices did not overlap. A cut-off now fails only when the
  browser measured one.
- agp's seven good card photos were dropped because the page-level review
  blamed the hero's burger on them. Each card's own photo is judged alone;
  the hero is judged against the business and swapped for the photo-free
  hero on a mismatch.
- the screenshot was taken before card images were drawn; an image still
  loading is slow, not broken.
- the burger itself came from the hero prompt; the image phase took 352 of
  362 seconds; the gate's regeneration redid all of it.
"""

from __future__ import annotations

import asyncio
import json
import time

from app.services import visual_gate as vg
from app.services.visual_gate import (
    GateReport, auto_fix, evaluate_checks, parse_card_photos, parse_hero, run_gate, use_photo_free_hero,
)


def _measured(**over):
    base = {"innerWidth": 390, "scrollWidth": 390, "heroCtas": [], "floating": [{"id": "whatsapp-button", "isWa": True, "obstructedBy": None}],
            "clipped": [], "lowContrast": [], "images": [], "ctas": [], "map": None}
    base.update(over)
    return base


def _render_with(mobile):
    async def _render(html, **kw):
        return mobile, _measured(innerWidth=1280, scrollWidth=1280), b"png", b"png", None
    return _render


def _vision(page=None, cards=None, hero=None, seen=None):
    """A vision model that answers each of the gate's three questions."""
    async def _call(messages):
        text = messages[0]["content"][0]["text"]
        if seen is not None:
            seen.append(messages)
        if "ONE card" in text or "ONE menu card" in text:
            return json.dumps(cards if cards is not None else {"mismatches": []})
        if "hero (top banner)" in text:
            return json.dumps(hero if hero is not None else {"matches": True, "shows": "the dishes", "reason": "fits"})
        return json.dumps(page if page is not None else {"issues": [], "overall": "pass"})
    return _call


CUTOFF = {"issues": [{"type": "cutoff", "where": "Milo Ais menu item", "detail": "card cut off at the bottom edge of the screen", "severity": "high"}],
          "overall": "fail"}


# ---------------------------------------------------------------------------
# Cut-offs need the measurements to agree
# ---------------------------------------------------------------------------

def test_vision_cutoff_without_measured_clipping_does_not_fail(monkeypatch):
    monkeypatch.setattr(vg, "render", _render_with(_measured()))
    r = asyncio.run(run_gate("<html/>", expect_map=False, expect_whatsapp=False, call_vision=_vision(page=CUTOFF)))
    assert r.passed, r.summary()
    issue = r.vision["issues"][0]
    assert issue["severity"] == "low" and "not confirmed" in issue["note"]


def test_vision_cutoff_with_measured_clipping_fails(monkeypatch):
    clipped = [{"text": "Milo Ais", "path": "h4.bmf-name", "scrollWidth": 300, "clientWidth": 120, "right": 300}]
    monkeypatch.setattr(vg, "render", _render_with(_measured(clipped=clipped)))
    r = asyncio.run(run_gate("<html/>", expect_map=False, expect_whatsapp=False, call_vision=_vision(page=CUTOFF)))
    assert {c.name for c in r.failed} == {"no_clipped_text", "vision_review"}


def test_cutoff_said_in_other_words_is_still_a_cutoff(monkeypatch):
    monkeypatch.setattr(vg, "render", _render_with(_measured()))
    page = {"issues": [{"type": "other", "where": "menu", "detail": "price is cut off", "severity": "high"},
                       {"type": "overlap", "where": "hero", "detail": "badge over the button", "severity": "high"}], "overall": "fail"}
    r = asyncio.run(run_gate("<html/>", expect_map=False, expect_whatsapp=False, call_vision=_vision(page=page)))
    assert [c.name for c in r.failed] == ["vision_review"] and r.failed[0].count == 1 and "overlap" in r.failed[0].detail


# ---------------------------------------------------------------------------
# Each card photo against its own name
# ---------------------------------------------------------------------------

CARDS = [{"name": "Set A – Ayam Gepuk", "png": b"\x89PNG-a"}, {"name": "Teh O Ais", "png": b"\x89PNG-b"},
         {"name": "Set B – Ayam Gepuk Tauhu Tempe", "png": b"\x89PNG-c"}]


def test_card_photos_are_judged_one_by_one(monkeypatch):
    monkeypatch.setattr(vg, "render", _render_with(_measured(_crops={"cards": CARDS, "hero": None})))
    seen = []
    # The page-level answer still blames every card (as on the live agp
    # run); with card crops present it is not used.
    page = {"issues": [], "photo_mismatches": [{"item": c["name"], "reason": "same burger photo"} for c in CARDS], "overall": "pass"}
    r = asyncio.run(run_gate("<html/>", expect_map=False, expect_whatsapp=False, call_vision=_vision(
        page=page, cards={"mismatches": [{"card": 2, "reason": "fried chicken, not a drink"}]}, seen=seen)))
    assert r.passed and r.photo_mismatches == ["Teh O Ais"]
    card_msg = next(m for m in seen if "ONE card" in m[0]["content"][0]["text"])[0]["content"]
    # name, then that card's own photo, for every card
    assert [c.get("text") for c in card_msg[1::2]] == ["Card 1: Set A – Ayam Gepuk", "Card 2: Teh O Ais", "Card 3: Set B – Ayam Gepuk Tauhu Tempe"]
    assert all(c["type"] == "image_url" for c in card_msg[2::2])
    fixed, fixes = auto_fix('<li class="bmf-card"><img src="x"><h4 class="bmf-name">Teh O Ais</h4></li>'
                            '<li class="bmf-card"><img src="y"><h4 class="bmf-name">Set A – Ayam Gepuk</h4></li>', r)
    assert fixes == ["dropped_mismatched_photos(1)"] and 'src="y"' in fixed and 'src="x"' not in fixed


def test_card_check_without_verdict_keeps_every_photo(monkeypatch):
    monkeypatch.setattr(vg, "render", _render_with(_measured(_crops={"cards": CARDS})))

    async def _call(messages):
        return "not json" if "ONE card" in messages[0]["content"][0]["text"] else json.dumps({"issues": [], "overall": "pass"})
    r = asyncio.run(run_gate("<html/>", expect_map=False, expect_whatsapp=False, call_vision=_call))
    assert r.passed and r.photo_mismatches == [] and not any(c.name == "photo_matches_name" for c in r.checks)


def test_parse_card_photos():
    assert parse_card_photos('{"mismatches": []}', CARDS) == []
    got = parse_card_photos('```json\n{"mismatches":[{"card":"#3","reason":"a burger"},{"card":9},{"card":"x"},{"card":3}]}\n```', CARDS)
    assert got == [{"item": "Set B – Ayam Gepuk Tauhu Tempe", "reason": "a burger"}]
    assert parse_card_photos("nope", CARDS) is None


# ---------------------------------------------------------------------------
# The hero against the business
# ---------------------------------------------------------------------------

AGP = {"name": "Ayam Gepuk Panglima", "type": "food", "description": "Ayam gepuk dengan sambal pedas", "items": ["Set A – Ayam Gepuk"]}


def test_hero_mismatch_is_soft_and_fixed_by_the_photo_free_hero(monkeypatch):
    monkeypatch.setattr(vg, "render", _render_with(_measured(_crops={"cards": [], "hero": b"\x89PNG-hero", "hero_kind": "img"})))
    seen = []
    r = asyncio.run(run_gate("<html/>", expect_map=False, expect_whatsapp=False, business=AGP, call_vision=_vision(
        hero={"matches": False, "shows": "a burger and fries", "reason": "the shop sells ayam gepuk"}, seen=seen)))
    assert r.passed
    hero = next(c for c in r.checks if c.name == "hero_matches_business")
    assert not hero.ok and not hero.hard and "burger" in hero.detail
    hero_msg = next(m for m in seen if "hero (top banner)" in m[0]["content"][0]["text"])[0]["content"]
    assert "Ayam Gepuk Panglima" in hero_msg[0]["text"] and "Set A – Ayam Gepuk" in hero_msg[0]["text"]
    page = ('<html><head></head><body><section class="bs-hero" id="home"><div class="bs-hero-media"><img src="burger.jpg">'
            '<span class="bs-ai-label">Gambar hiasan</span></div><div class="bs-hero-scrim"></div><div class="bs-wrap"><h1>AGP</h1></div></section></body></html>')
    fixed, fixes = auto_fix(page, r)
    assert fixes == ["photo_free_hero"]
    assert 'class="bs-hero bs-hero-solid"' in fixed and "burger.jpg" not in fixed and "bs-hero-scrim" not in fixed and "<h1>AGP</h1>" in fixed


def test_hero_check_needs_a_hero_photo_and_the_business(monkeypatch):
    seen = []
    monkeypatch.setattr(vg, "render", _render_with(_measured(_crops={"cards": [], "hero": None})))
    asyncio.run(run_gate("<html/>", expect_map=False, expect_whatsapp=False, business=AGP, call_vision=_vision(seen=seen)))
    monkeypatch.setattr(vg, "render", _render_with(_measured(_crops={"cards": [], "hero": b"png"})))
    asyncio.run(run_gate("<html/>", expect_map=False, expect_whatsapp=False, call_vision=_vision(seen=seen)))
    assert len(seen) == 2 and all("hero (top banner)" not in m[0]["content"][0]["text"] for m in seen)


def test_parse_hero():
    assert parse_hero('{"matches": false, "shows": "burger", "reason": "x"}')["matches"] is False
    assert parse_hero('{"matches": "no"}')["matches"] is False and parse_hero('{"matches": "yes"}')["matches"] is True
    assert parse_hero('{"shows": "burger"}') is None and parse_hero(None) is None


def test_photo_free_hero_on_a_freeform_page():
    page = ('<html><head><style>#home{color:#fff}</style></head><body><section id="home" style="background-image:url(b.jpg);padding:2rem">'
            '<img src="burger.jpg" width="1600" class="hero-img"><h1>Kedai</h1><img src="logo.png" width="40"></section></body></html>')
    out, n = use_photo_free_hero(page)
    assert n == 1 and "burger.jpg" not in out and "logo.png" in out and "url(b.jpg)" not in out and "padding:2rem" in out
    assert 'data-bvg-solid="1"' in out and 'id="binaapp-visual-gate-hero"' in out
    assert use_photo_free_hero("<html><body><p>no hero</p></body></html>") == ("<html><body><p>no hero</p></body></html>", 0)


# ---------------------------------------------------------------------------
# Slow images are not broken images
# ---------------------------------------------------------------------------

def test_image_still_loading_is_not_dropped():
    images = [{"src": "https://res.cloudinary.com/x/slow.jpg", "ok": False, "pending": True},
              {"src": "https://example.invalid/broken.jpg", "ok": False, "pending": False},
              {"src": "https://res.cloudinary.com/x/fine.jpg", "ok": True, "pending": False}]
    checks = {c.name: c for c in evaluate_checks(_measured(images=images), _measured(innerWidth=1280, scrollWidth=1280), expect_map=False, expect_whatsapp=True)}
    assert checks["images_load"].count == 1 and "broken" in checks["images_load"].detail
    assert not checks["images_drawn"].ok and not checks["images_drawn"].hard and "slow" in checks["images_drawn"].detail
    rep = GateReport(checks=list(checks.values()), rendered=True)
    page = '<img src="https://res.cloudinary.com/x/slow.jpg"><img src="https://example.invalid/broken.jpg">'
    fixed, fixes = auto_fix(page, rep)
    assert "slow.jpg" in fixed and "broken.jpg" not in fixed and fixes[0] == "dropped_broken_images(1)"


# ---------------------------------------------------------------------------
# The hero prompt (agp: "a stacked burger and fries on kraft paper")
# ---------------------------------------------------------------------------

BURGER_CUE = "a stacked burger and fries on kraft paper, hard daylight, bold shadows"
STREET_KEYWORDS = ("burger", "street food", "fries")


def test_hero_prompt_is_the_merchants_dishes_not_the_directions_example():
    from app.services.image_intelligence import direction_hero_cue
    cue = direction_hero_cue(image_cue=BURGER_CUE, vertical="food", theme="bright", cue_keywords=STREET_KEYWORDS,
                             item_names=["Set A – Ayam Gepuk", "Set B – Ayam Gepuk Tauhu Tempe", "Set C – Ayam Gepuk Kubis Goreng"],
                             business_text="Ayam Gepuk Panglima ayam gepuk sambal")
    assert "burger" not in cue and "fries" not in cue and "kraft" not in cue
    assert cue.startswith("a generous spread of smashed crispy fried chicken with fried tofu, tempeh and stir-fried cabbage")
    assert "Set A" not in cue and "hard daylight, bold shadows" in cue  # the direction's light stays


def test_hero_prompt_keeps_the_example_only_when_it_is_this_business():
    from app.services.image_intelligence import direction_hero_cue
    burger_shop = direction_hero_cue(image_cue=BURGER_CUE, vertical="food", theme="bright", cue_keywords=STREET_KEYWORDS,
                                     business_text="Burger Bakar Abang Long, burger daging")
    assert burger_shop.startswith("a stacked burger and fries")
    other = direction_hero_cue(image_cue=BURGER_CUE, vertical="food", theme="bright", cue_keywords=STREET_KEYWORDS,
                               business_text="Ayam Gepuk Panglima")
    assert "burger" not in other and other.startswith("a generous spread of the shop's freshly cooked dishes")
    salon = direction_hero_cue(image_cue="a bright salon interior with an empty styling chair, soft daylight", vertical="salon",
                               theme="bright", item_names=["Gunting & Blow"], cue_keywords=("salon",), business_text="Salon Ayu")
    assert "showing Gunting & Blow" in salon and "salon interior" not in salon and "appetising" not in salon
    barber = direction_hero_cue(image_cue="a barber chair under a single warm light in a dark shop, warm evening light",
                                vertical="salon", theme="dark", item_names=["Gunting & Blow", "Warna Penuh"],
                                cue_keywords=("barber", "gunting"), business_text="Salon Seri Ayu, salon wanita, Gunting & Blow")
    assert "barber" not in barber and "warm evening light" in barber
    phone = direction_hero_cue(image_cue="a clean studio with a camera on a tripod, soft daylight", vertical="general", theme="bright",
                               item_names=["Screen Replacement"], cue_keywords=("photography", "studio"), business_text="Kedai Telefon Hafiz repair")
    assert "camera" not in phone


# ---------------------------------------------------------------------------
# Image phase: Z.ai queue past the target goes to Stability at once
# ---------------------------------------------------------------------------

def test_image_waits_for_zai_only_while_it_fits_the_target(monkeypatch):
    from app.services.ai_service import AIService
    monkeypatch.setenv("IMAGE_PHASE_TARGET_SECONDS", "100")
    monkeypatch.setenv("ZAI_IMAGE_EXPECTED_SECONDS", "40")
    s = AIService()
    s.stability_api_key = "sk-test"
    phase = s._new_zai_image_phase()
    assert not s._zai_turn_too_late(phase)          # 1st: ends ~40s
    phase["queued"] = 1
    assert not s._zai_turn_too_late(phase)          # 2nd: ~80s
    phase["queued"] = 2
    assert s._zai_turn_too_late(phase) and phase["rerouted"] == 1   # 3rd: ~120s > 100s
    phase["queued"], phase["avg"] = 0, 30.0
    phase["started"] = time.monotonic() - 90       # 90s already gone
    assert s._zai_turn_too_late(phase)
    s.stability_api_key = ""                        # nowhere else to go: wait for Z.ai
    assert not s._zai_turn_too_late(phase)
    monkeypatch.setenv("IMAGE_PHASE_TARGET_SECONDS", "0")
    s.stability_api_key = "sk-test"
    assert not s._zai_turn_too_late(phase)          # 0 = old behaviour


def test_eight_images_finish_near_the_target(monkeypatch):
    """Eight images, Z.ai 'taking' 4s each (40s scaled down 10x), Stability
    0.2s: two go to Z.ai, six to Stability in parallel."""
    from app.services import ai_service as svc
    monkeypatch.setenv("IMAGE_PROVIDER", "zai")
    monkeypatch.setenv("IMAGE_PHASE_TARGET_SECONDS", "10")
    monkeypatch.setenv("ZAI_IMAGE_EXPECTED_SECONDS", "4")
    monkeypatch.setenv("ZAI_IMAGE_REQUEST_DELAY_SECONDS", "0")
    s = svc.AIService()
    s.stability_api_key = "sk-test"
    s.zai_api_key = "zai-test"
    used = []

    async def _zai(prompt):
        await asyncio.sleep(4)
        used.append("zai")
        return "https://res.cloudinary.com/x/image/upload/zai.jpg"

    async def _stab(prompt, food=True, doodle=False):
        await asyncio.sleep(0.2)
        used.append("stability")
        return "https://res.cloudinary.com/x/image/upload/stab.jpg"
    monkeypatch.setattr(s, "_generate_image_zai", _zai)
    monkeypatch.setattr(s, "_generate_stability_image", _stab)

    async def _run():
        phase = s._new_zai_image_phase()
        t0 = time.monotonic()
        urls = await asyncio.gather(*[s._generate_image(f"dish {i}", food=False, zai_phase=phase) for i in range(8)])
        return time.monotonic() - t0, urls
    took, urls = asyncio.run(_run())
    assert all(urls) and used.count("zai") == 2 and used.count("stability") == 6
    assert took < 9.5  # was 8 x 4s = 32s


# ---------------------------------------------------------------------------
# The gate's regeneration reuses the first build's images
# ---------------------------------------------------------------------------

def test_regeneration_reuses_images(monkeypatch):
    from app.models.schemas import WebsiteGenerationRequest
    from app.services import ai_service as svc
    monkeypatch.setenv("BINAAPP_PAGE_MODE", "deterministic")
    monkeypatch.setenv("IMAGE_CHECK_ENABLED", "false")
    monkeypatch.setenv("DESIGN_PLAN_STORE_ENABLED", "false")
    s = svc.AIService()
    s.deepseek_api_key = s.zai_api_key = s.qwen_api_key = ""

    async def _no_images(*a, **k):
        raise AssertionError("images generated again")
    monkeypatch.setattr(s, "_autofill_missing_images", _no_images)
    req = WebsiteGenerationRequest(
        description="Kedai kopi di Klang. Kopi tarik dan roti bakar.", business_name="Kopi Pak Su", business_type="food", subdomain="kopipaksu",
        whatsapp_number="0126973105", menu_items=[{"name": "Kopi Tarik", "price": "3.00"}, {"name": "Roti Bakar", "price": "2.50"}],
    )
    hero = "https://res.cloudinary.com/demo/image/upload/v1/binaapp/hero-kopi.jpg"
    bundle = {"image_urls": {"hero": hero}, "ai_image_urls": [hero], "poster_uploads": [], "ai_images_generated": 1}
    progress = []

    async def _progress(p, m):
        progress.append(p)
    resp = asyncio.run(s.generate_website(req, image_choice="ai", reuse_images=bundle, progress_callback=_progress))
    assert "hero-kopi.jpg" in resp.html_content and resp.ai_images_count == 0
    assert resp.image_bundle["image_urls"]["hero"] == hero
    assert 45 in progress


# ---------------------------------------------------------------------------
# Before enforce: the named dish with sides, the kicker, the QR label
# ---------------------------------------------------------------------------

def test_card_with_its_named_dish_and_side_dishes_is_kept():
    """agp's Set Udang Krispy: "shrimp are present, but tofu and tempeh are
    major components" — the named dish is there, so the photo stays. Set
    Sotong Krispy with no squid in it is still dropped."""
    cards = [{"name": "Set Sotong Krispy", "png": b"a"}, {"name": "Set Udang Krispy", "png": b"b"}]
    raw = json.dumps({"mismatches": [
        {"card": 1, "named_dish": "crispy squid", "named_dish_visible": False, "reason": "only tofu and tempeh"},
        {"card": 2, "named_dish": "crispy prawns", "named_dish_visible": True, "reason": "prawns present but tofu and tempeh dominate"},
    ]})
    assert parse_card_photos(raw, cards) == [{"item": "Set Sotong Krispy", "reason": "only tofu and tempeh"}]
    assert parse_card_photos(json.dumps({"mismatches": [{"card": 2, "named_dish_visible": "yes"}]}), cards) == []
    rubric = vg.CARD_PHOTO_RUBRIC
    assert "dish is clearly visible the photo MATCHES" in rubric and "a set meal comes with sides" in rubric


def test_hero_kicker_is_never_cut_with_an_ellipsis():
    from app.services.sections.copy import LIMITS, fit_label
    assert fit_label("Ayam Gepuk · Kota Bayu Emas, Klang", LIMITS["kicker"]) == "Ayam Gepuk · Kota Bayu Emas"
    assert fit_label("Kedai Kek · Seksyen 7, Shah Alam, Selangor Darul Ehsan", 32) == "Kedai Kek · Seksyen 7, Shah Alam"  # 32: fits
    assert fit_label("Restoran Mamak 24 Jam di SS2", 32) == "Restoran Mamak 24 Jam di SS2"
    for text in ("Ayam Gepuk Panglima Kota Bayu Emas Klang Selangor", "Kek · Klang…", "A" * 50):
        out = fit_label(text, 32)
        assert "…" not in out and len(out) <= 32


def test_model_kicker_goes_through_the_fitter():
    from app.services.sections.copy import parse_copy
    from app.services.sections import build_spec
    from app.models.schemas import WebsiteGenerationRequest
    req = WebsiteGenerationRequest(description="Ayam gepuk di Kota Bayu Emas, Klang.", business_name="Ayam Gepuk Panglima",
                                   business_type="food", subdomain="agp", whatsapp_number="0126973105",
                                   menu_items=[{"name": "Set A", "price": "12.50"}])
    spec = build_spec(req)
    copy = parse_copy(json.dumps({"kicker": "AYAM GEPUK · KOTA BAYU EMAS, KLANG", "headline": "Ayam Gepuk Panglima",
                                  "subheadline": "Sambal segar setiap hari.", "about_title": "Tentang", "tagline": "Pedas",
                                  "contact_lead": "Hubungi kami", "about_paragraphs": ["Kami di Klang."]}), spec)
    assert copy.kicker == "AYAM GEPUK · KOTA BAYU EMAS"


def test_card_check_knows_services_and_hidden_fillings():
    """Live golden run: salon cards dropped for "salon interior, no colouring
    visible", kedai telefon's "Screen Replacement" for "not the named service
    as a dish", mamak's Roti Telur for "no visible egg"."""
    rubric = vg.CARD_PHOTO_RUBRIC
    assert "For a SERVICE" in rubric and "Screen Replacement" in rubric and "never has to show a customer" in rubric
    assert "roti telur" in rubric and "does not have to be visible" in rubric
    msgs = vg.build_card_photo_messages([{"name": "Warna Penuh", "png": b"\x89PNG"}],
                                        {"name": "Salon Seri Ayu", "type": "salon", "description": "Salon wanita di Shah Alam"})
    head = msgs[0]["content"][0]["text"]
    assert "Salon Seri Ayu (type: salon)" in head and "Salon wanita" in head
    assert vg.build_card_photo_messages([{"name": "x", "png": b"\x89PNG"}])[0]["content"][0]["text"] == rubric


def test_card_check_gets_the_business(monkeypatch):
    monkeypatch.setattr(vg, "render", _render_with(_measured(_crops={"cards": [{"name": "Warna Penuh", "png": b"p"}]})))
    seen = []
    asyncio.run(run_gate("<html/>", expect_map=False, expect_whatsapp=False, call_vision=_vision(seen=seen),
                         business={"name": "Salon Seri Ayu", "type": "salon", "description": "Salon"}))
    card_msg = next(m for m in seen if "ONE card" in m[0]["content"][0]["text"])
    assert "Salon Seri Ayu" in card_msg[0]["content"][0]["text"]


def test_lookalike_variants_of_one_food_match():
    """mamak (clean rerun): Roti Bom dropped because "authentic Roti Bom is a
    deep-fried ball", Roti Planta flagged because the photo cannot show
    margarine. A roti photo on a roti card matches."""
    rubric = vg.CARD_PHOTO_RUBRIC
    assert "every roti (canai, planta, bom, telur, tisu, kosong)" in rubric and "cannot show margarine" in rubric


def test_dropped_card_photo_keeps_its_src():
    cards = [{"name": "Roti Bom", "src": "https://res.cloudinary.com/x/roti-bom.jpg", "png": b"p"}]
    got = parse_card_photos('{"mismatches":[{"card":1,"named_dish_visible":false,"reason":"a pizza"}]}', cards)
    assert got == [{"item": "Roti Bom", "reason": "a pizza", "src": "https://res.cloudinary.com/x/roti-bom.jpg"}]


def test_service_business_cards_are_judged_on_belonging_to_the_business():
    """Clean rerun: salon's four service cards dropped for "empty salon
    interior, no colouring visible" even with the service rule in the dish
    rubric. A non-food business gets the trade rubric."""
    salon = {"name": "Salon Seri Ayu", "type": "salon", "description": "Salon wanita"}
    text = vg.build_card_photo_messages([{"name": "Warna Penuh", "png": b"p"}], salon)[0]["content"][0]["text"]
    assert text.startswith(vg.TRADE_PHOTO_RUBRIC) and "empty salon interior matches 'Warna Penuh'" in text
    phone = {"name": "Mobile Hub", "type": "general", "description": "phone repair"}
    assert vg.build_card_photo_messages([{"name": "Screen Replacement", "png": b"p"}], phone)[0]["content"][0]["text"].startswith(vg.TRADE_PHOTO_RUBRIC)
    for food in ({"type": "food"}, {"type": "bakery"}, {"type": ""}, None):
        assert vg.build_card_photo_messages([{"name": "Set A", "png": b"p"}], food)[0]["content"][0]["text"].startswith(vg.CARD_PHOTO_RUBRIC)
