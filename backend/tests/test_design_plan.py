"""
Design plan — Pass 1 of two-pass generation (design_plan.py).

Covers:
- theme resolution: Cerah/Gelap toggle is a wall, the written brief beats it
- candidate directions honour theme, style pick and rolling history
- plan validation repairs palette contrast, fonts, hero treatment and
  rejects the cream+serif+gold default unless the direction justifies it
- custom directions only under Designer bebas
- brief quotes must come from the brief; the plan's why cites it
- feature toggles OFF remove sections; non-F&B plans never carry a menu
- the fallback plan is complete and passes the same checks
- multi-plan replies are distinct; completeness + listening questions
"""

import json

from app.services import design_directions as dd
from app.services.design_plan import (
    DesignPlan,
    PlanBrief,
    brief_completeness,
    brief_theme_request,
    build_plan_prompt,
    candidates_for,
    fallback_plan,
    listening_questions,
    parse_plan,
    parse_plans,
    plans_are_distinct,
    resolve_theme,
    sections_for,
    uses_cream_serif_gold,
)
from app.services.design_director import contrast_ratio, is_dark, is_light


def _brief(**kw) -> PlanBrief:
    base = dict(
        business_name="Nasi Kandar Crystal",
        description="Nasi kandar mamak buka 24 jam di Shah Alam. Ayam goreng berempah dan kari kepala ikan sejak 2009.",
        vertical="food",
        theme="bright",
        menu_item_count=5,
        has_hero_image=True,
        address="Shah Alam",
    )
    base.update(kw)
    return PlanBrief(**base)


def _raw(**overrides) -> str:
    data = {
        "direction": "warung_cerah",
        "why": "A mamak that never closes wants a loud, bright counter feel.",
        "brief_quotes": [],
        "palette": {"bg": "#FFFFFF", "surface": "#FFF4D6", "text": "#1F1A17", "muted": "#5C5148", "accent": "#E8541E", "accent_2": "#F5B400"},
        "type": {"display": "Archivo Black", "body": "Source Sans 3", "scale": "1.333 perfect fourth", "display_weight": 400},
        "hero_treatment": "menu-first",
        "signature_element": "a turmeric band with the top three dishes and prices",
        "layout_notes": "left aligned, no cards outside the menu",
        "motion": "price tiles slide in once",
        "avoid": ["italic headline word"],
    }
    data.update(overrides)
    return json.dumps(data)


# ---- theme ----------------------------------------------------------------

def test_theme_toggle_is_a_wall_and_bright_is_default():
    assert resolve_theme("light", None)[0] == "bright"
    assert resolve_theme("dark", None)[0] == "dark"
    assert resolve_theme(None, None, touched=False) == ("bright", "default", "")


def test_brief_beats_toggle_and_plan_says_so():
    theme, source, note = resolve_theme("light", "Saya nak tema gelap dan mewah")
    assert theme == "dark" and source == "brief" and "brief wins" in note
    theme, source, _ = resolve_theme("dark", "Jangan gelap, saya nak cerah dan ceria")
    assert theme == "bright" and source == "brief"
    assert brief_theme_request("warna biru sahaja") is None


# ---- candidates -----------------------------------------------------------

def test_candidates_honour_theme_style_and_history():
    dark_doodle = candidates_for(_brief(theme="dark", style="doodle"))
    assert dark_doodle and all(d.theme == "dark" and "doodle" in d.styles for d in dark_doodle)
    first = candidates_for(_brief())[0]
    rotated = candidates_for(_brief(), history=[first.key])
    assert rotated[0].key != first.key
    assert first.key not in [d.key for d in rotated]


def test_keyword_fit_ranks_first():
    assert candidates_for(_brief())[0].key == "warung_cerah"
    steak = _brief(description="Steakhouse dan wine lounge di Bangsar", theme="dark")
    assert candidates_for(steak)[0].key == "malam_bandar"


# ---- validation -----------------------------------------------------------

def test_valid_plan_parses_cleanly():
    brief = _brief()
    plan = parse_plan(_raw(), brief, candidates_for(brief))
    assert plan is not None
    assert plan.direction == "warung_cerah" and not plan.custom
    assert plan.adjustments == []
    assert plan.hero_treatment == "menu-first"
    assert "menu" in plan.sections and plan.sections[0] == "hero" and plan.sections[-1] == "footer"


def test_palette_contrast_is_repaired_not_trusted():
    brief = _brief()
    plan = parse_plan(
        _raw(palette={"bg": "#FFFFFF", "surface": "#FFFFFF", "text": "#BBBBBB", "muted": "#DDDDDD", "accent": "#FFE9A0", "accent_2": "#F5B400"}),
        brief, candidates_for(brief),
    )
    assert contrast_ratio(plan.palette["text"], plan.palette["bg"]) >= 4.5
    assert contrast_ratio(plan.palette["muted"], plan.palette["bg"]) >= 3.0
    assert contrast_ratio(plan.palette["accent"], plan.palette["bg"]) >= 3.0
    assert any("palette.text" in a for a in plan.adjustments)
    assert any("palette.accent" in a for a in plan.adjustments)


def test_theme_flip_in_palette_is_overruled():
    brief = _brief(theme="bright")
    plan = parse_plan(
        _raw(palette={"bg": "#111111", "surface": "#222222", "text": "#FFFFFF", "muted": "#CCCCCC", "accent": "#E8541E", "accent_2": "#F5B400"}),
        brief, candidates_for(brief),
    )
    assert is_light(plan.palette["bg"])
    assert any("did not match the bright theme" in a for a in plan.adjustments)
    dark = _brief(theme="dark", description="Steakhouse dan wine lounge")
    plan = parse_plan(_raw(direction="malam_bandar"), dark, candidates_for(dark))
    assert is_dark(plan.palette["bg"])


def test_fonts_outside_allowlist_and_similar_sans_are_repaired():
    brief = _brief()
    plan = parse_plan(_raw(type={"display": "Comic Sans MS", "body": "Arial", "scale": "1.3", "display_weight": 650}), brief, candidates_for(brief))
    assert plan.type["display"] in dd.DISPLAY_FONTS and plan.type["body"] in dd.ALLOWED_FONTS
    assert plan.type["scale"] == "1.333 perfect fourth"
    assert dd.is_valid_pairing(plan.type["display"], plan.type["body"])
    plan = parse_plan(_raw(type={"display": "Bricolage Grotesque", "body": "DM Sans", "scale": "1.25 major third", "display_weight": 700}), brief, candidates_for(brief))
    assert plan.type["body"] != "DM Sans"
    assert any("two similar sans" in a for a in plan.adjustments)


def test_single_family_plan_is_allowed_for_readable_sans():
    brief = _brief(vertical="services", description="Bengkel aircond dan paip", style=None)
    plan = parse_plan(_raw(direction="bengkel_yakin", type={"display": "Rubik", "body": "Rubik", "scale": "1.25 major third", "display_weight": 800}), brief, candidates_for(brief))
    assert plan.type["display"] == plan.type["body"] == "Rubik"


def test_cream_serif_gold_rejected_unless_direction_justifies():
    assert uses_cream_serif_gold({"bg": "#F4F1EA", "accent": "#C9A24D", "accent_2": "#333333"}, "Playfair Display")
    assert not uses_cream_serif_gold({"bg": "#FFFFFF", "accent": "#C9A24D", "accent_2": "#333333"}, "Playfair Display")
    brief = _brief()
    plan = parse_plan(
        _raw(direction="kopi_moden",
             palette={"bg": "#F4F1EA", "surface": "#FFFFFF", "text": "#2B2119", "muted": "#6A5A4E", "accent": "#B8862B", "accent_2": "#9A3B2E"},
             type={"display": "Fraunces", "body": "Manrope", "scale": "1.25 major third", "display_weight": 500}),
        brief, candidates_for(brief),
    )
    assert not uses_cream_serif_gold(plan.palette, plan.type["display"])
    assert any("cream + serif + gold" in a for a in plan.adjustments)
    # Dapur Keluarga is the direction that justifies cream.
    family = _brief(description="Restoran keluarga masakan kampung dan katering kenduri")
    plan = parse_plan(
        _raw(direction="dapur_keluarga",
             palette={"bg": "#F7F1E6", "surface": "#FFFFFF", "text": "#2B2119", "muted": "#6A5A4E", "accent": "#9A3B2E", "accent_2": "#B8862B"},
             type={"display": "Fraunces", "body": "Source Sans 3", "scale": "1.25 major third", "display_weight": 600}),
        family, candidates_for(family),
    )
    assert plan.direction == "dapur_keluarga"
    assert not any("cream + serif + gold" in a for a in plan.adjustments)


def test_direction_outside_theme_or_history_is_rotated():
    brief = _brief(theme="bright")
    plan = parse_plan(_raw(direction="malam_bandar"), brief, candidates_for(brief))
    assert dd.DIRECTION_BY_KEY[plan.direction].theme == "bright"
    history = ["warung_cerah"]
    plan = parse_plan(_raw(direction="warung_cerah"), brief, candidates_for(brief, history), history)
    assert plan.direction != "warung_cerah"
    assert any("rotated" in a for a in plan.adjustments)


def test_custom_direction_only_under_designer_bebas():
    bebas = _brief(freedom="designer")
    plan = parse_plan(_raw(direction="Sunrise Counter"), bebas, candidates_for(bebas))
    assert plan.custom and plan.direction == "custom:sunrise-counter" and plan.direction_name == "Sunrise Counter"
    guided = _brief(freedom="guided")
    plan = parse_plan(_raw(direction="Sunrise Counter"), guided, candidates_for(guided))
    assert not plan.custom and plan.direction in dd.DIRECTION_BY_KEY
    assert any("Ikut sistem" in a for a in plan.adjustments)


def test_hero_treatment_rules():
    no_photo = _brief(has_hero_image=False)
    plan = parse_plan(_raw(hero_treatment="photo-full-bleed"), no_photo, candidates_for(no_photo))
    assert plan.hero_treatment in ("menu-first", "typographic")
    portrait = _brief(has_hero_image=True, hero_full_bleed_ok=False)
    plan = parse_plan(_raw(hero_treatment="photo-full-bleed"), portrait, candidates_for(portrait))
    assert plan.hero_treatment == "photo-split"
    video = _brief(hero_video=True)
    plan = parse_plan(_raw(hero_treatment="typographic", motion="confetti everywhere"), video, candidates_for(video))
    assert plan.hero_treatment == "photo-full-bleed"
    assert "video" in plan.motion


def test_brief_quotes_must_come_from_the_brief():
    brief = _brief(design_brief="Guna warna pink. Saya nak rasa seperti kafe Korea.")
    plan = parse_plan(_raw(why="Honours 'Guna warna pink' with a pink accent.", brief_quotes=["Guna warna pink.", "invented sentence"]), brief, candidates_for(brief))
    assert plan.brief_quotes == ["Guna warna pink."]
    assert any("not in the brief" in a for a in plan.adjustments)
    plan = parse_plan(_raw(why="A bright counter.", brief_quotes=[]), brief, candidates_for(brief))
    assert plan.brief_quotes  # the whole brief is carried when nothing matched
    assert "brief" in plan.to_prompt_block("ms").lower()


def test_merchant_override_dark_doodle_pink_cites_brief():
    theme, source, note = resolve_theme("dark", "guna warna pink")
    brief = _brief(
        business_name="Kek Comel", description="Kedai kek dan brownies di Bangi", vertical="bakery",
        theme=theme, theme_source=source, theme_note=note, style="doodle", design_brief="guna warna pink", freedom="designer",
    )
    cands = candidates_for(brief)
    assert all(d.theme == "dark" and "doodle" in d.styles for d in cands)
    raw = _raw(
        direction=cands[0].key,
        why='Honours "guna warna pink": the chalk accents and prices are pink on the dark board.',
        brief_quotes=["guna warna pink"],
        palette={"bg": "#1E2A26", "surface": "#27352F", "text": "#FBF7EE", "muted": "#C7C1B3", "accent": "#FF6FA5", "accent_2": "#FFD447"},
        type={"display": "Baloo 2", "body": "Source Sans 3", "scale": "1.25 major third", "display_weight": 700},
        hero_treatment="pattern",
    )
    plan = parse_plan(raw, brief, cands)
    assert is_dark(plan.palette["bg"])
    assert plan.palette["accent"] == "#FF6FA5"
    assert plan.type["display"] in ("Baloo 2", "Fredoka")
    assert plan.brief_quotes == ["guna warna pink"]
    assert "pink" in plan.why


# ---- sections / features ------------------------------------------------

def test_non_fnb_plans_never_carry_a_menu():
    for vertical, text in (("salon", "Salon rambut dan spa"), ("services", "Bengkel aircond"), ("clothing", "Butik baju kurung")):
        brief = _brief(vertical=vertical, description=text)
        plan = fallback_plan(brief)
        assert "menu" not in plan.sections, vertical
        assert dd.DIRECTION_BY_KEY[plan.direction].theme == "bright"
    assert "servis_harga" in fallback_plan(_brief(vertical="salon", description="Salon rambut")).sections
    assert "kawasan_liputan" in fallback_plan(_brief(vertical="services", description="Bengkel")).sections


def test_features_off_remove_sections():
    gallery = sections_for(_brief(gallery_count=3))
    assert "gallery" in gallery
    assert "gallery" not in sections_for(_brief(gallery_count=2))
    no_contact = sections_for(_brief(whatsapp=False, contact_form=False))
    assert "contact" not in no_contact and "location" in no_contact
    services = sections_for(_brief(vertical="services", testimonials=0))
    assert "testimoni" not in services
    assert "testimoni" in sections_for(_brief(vertical="services", testimonials=2))


def test_prompt_states_every_merchant_constraint():
    brief = _brief(theme="dark", style="elegant", whatsapp=False, maps=False, contact_form=False, hero_video=True,
                   design_brief="Mewah dan gelap", image_colours=["#8B2F2F"])
    prompt = build_plan_prompt(brief, candidates_for(brief), history=["malam_bandar"])
    assert "DARK page" in prompt and "MEWAH" in prompt
    assert "NO WhatsApp buttons" in prompt and "Google Maps OFF" in prompt and "no contact form" in prompt
    assert "photo-full-bleed" in prompt and "#8B2F2F" in prompt and "malam_bandar" in prompt
    assert "Mewah dan gelap" in prompt


# ---- fallback / multi / listening -----------------------------------------

def test_fallback_plan_is_complete_and_readable():
    for vertical, text, theme in (("food", "Nasi kandar", "bright"), ("bakery", "Kek", "dark"), ("salon", "Spa", "bright"), ("services", "Bengkel", "dark"), ("clothing", "Butik", "bright"), ("general", "Kedai runcit", "bright")):
        plan = fallback_plan(_brief(vertical=vertical, description=text, theme=theme))
        assert plan.source == "fallback"
        assert contrast_ratio(plan.palette["text"], plan.palette["bg"]) >= 4.5
        assert contrast_ratio(plan.palette["accent"], plan.palette["bg"]) >= 3.0
        assert plan.hero_treatment in dd.HERO_TREATMENTS
        assert plan.signature_element and plan.motion and plan.avoid
        d = plan.as_dict()
        assert d["version"] == 1 and d["direction"] == plan.direction


def test_multi_plan_reply_is_distinct():
    brief = _brief()
    cands = candidates_for(brief)
    raw = json.dumps([json.loads(_raw(direction="warung_cerah")), json.loads(_raw(direction="warung_cerah")), json.loads(_raw(direction="warung_cerah"))])
    plans = parse_plans(raw, brief, cands, n_plans=3)
    assert len(plans) == 3 and plans_are_distinct(plans)


def test_concept_adapter_keeps_pipeline_tokens():
    plan = fallback_plan(_brief())
    concept = plan.to_concept("ms")
    for key in ("primary", "secondary", "accent", "accent_strong", "background", "surface", "text", "text_muted"):
        assert key in concept.palette
    assert concept.fonts["heading"] == plan.type["display"]
    assert "fonts.googleapis.com" in concept.fonts["cdn_link"]
    assert concept.sections[0].id == "hero" and concept.sections[-1].id == "footer"


def test_completeness_and_listening_questions():
    thin = PlanBrief(business_name="Kedai", description="Kedai makan", vertical="food")
    assert brief_completeness(thin) < 40
    questions = listening_questions(thin)
    assert questions and any("hidangan" in q for q in questions)
    full = _brief(hours="10am-10pm", design_brief="Cerah")
    assert brief_completeness(full) >= 40
