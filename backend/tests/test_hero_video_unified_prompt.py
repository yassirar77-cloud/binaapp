"""One hero visual, two renderings: the video scene is the hero image prompt."""
from app.services.zai_video_service import _PROMPT_SUFFIX, build_hero_video_prompt

HERO = "dark luxury hair salon interior, warm gold lighting, empty styling chair, cinematic"


def test_hero_image_prompt_becomes_the_scene_with_the_preset_as_motion():
    p = build_hero_video_prompt(business_name="Nadira", business_type="salon",
                                description="salon rambut", style="cinematic", hero_image_prompt=HERO)
    assert p.startswith(HERO + ". ")
    assert "slow cinematic camera drift" in p
    assert "Atmospheric scene for" not in p
    assert p.endswith(_PROMPT_SUFFIX)


def test_merchant_motion_prompt_is_appended_to_the_hero_scene():
    p = build_hero_video_prompt(hero_image_prompt=HERO, custom_prompt="steam rising slowly from a cup")
    assert p.startswith(HERO + ". steam rising slowly from a cup")
    assert "camera drift" not in p


def test_without_a_hero_prompt_behaviour_is_unchanged():
    custom = build_hero_video_prompt(custom_prompt="kopi dituang perlahan")
    assert custom.startswith("kopi dituang perlahan")
    auto = build_hero_video_prompt(business_name="Kedai Ali", business_type="food", description="Nasi lemak")
    assert auto.startswith("Atmospheric scene for a food business called Kedai Ali: Nasi lemak")


def test_stays_within_the_provider_limit():
    p = build_hero_video_prompt(hero_image_prompt="x " * 400, custom_prompt="y " * 200)
    assert len(p) <= 512 and p.endswith(_PROMPT_SUFFIX)


# ── prompt hygiene ───────────────────────────────────────────────────────────
# Regression: the live prompt for website mirana went out as
#   "Golden dress rotate behind beautifully Background video for a website
#    hero: no text, ..."
# The merchant's instruction ran straight into the boilerplate as one clause,
# and the "cinematic" style they had selected never reached the model at all.

def _head(prompt: str) -> str:
    """The prompt with the fixed suffix removed."""
    assert prompt.endswith(_PROMPT_SUFFIX)
    return prompt[: len(prompt) - len(_PROMPT_SUFFIX)].rstrip()


def test_custom_prompt_is_closed_before_the_boilerplate():
    """No run-on: the suffix must start its own sentence."""
    p = build_hero_video_prompt(custom_prompt="Golden dress rotate behind beautifully")
    assert "beautifully Background video" not in p
    assert _head(p).endswith(".")


def test_hero_scene_motion_is_closed_before_the_boilerplate():
    p = build_hero_video_prompt(hero_image_prompt=HERO, custom_prompt="steam rising")
    assert "steam rising Background" not in p
    assert _head(p).endswith(".")


def test_selected_style_still_applies_when_a_custom_prompt_is_given():
    """The style buttons were dead controls for anyone who typed a prompt."""
    p = build_hero_video_prompt(custom_prompt="Golden dress rotate", style="cinematic")
    assert p.startswith("Golden dress rotate.")  # merchant's words lead
    assert "slow cinematic camera drift" in p
    q = build_hero_video_prompt(custom_prompt="Golden dress rotate", style="elegant")
    assert "luxurious minimal composition" in q
    assert "slow cinematic camera drift" not in q


def test_existing_punctuation_is_not_doubled():
    for text in ("ends with period.", "excited!", "really?"):
        p = build_hero_video_prompt(custom_prompt=text)
        assert ".." not in p and "!." not in p and "?." not in p


def test_terminator_never_pushes_the_prompt_over_the_limit():
    from app.services.zai_video_service import ZAI_PROMPT_MAX_CHARS
    for n in range(0, 700, 13):
        p = build_hero_video_prompt(custom_prompt="y " * n, hero_image_prompt="x " * n)
        assert len(p) <= ZAI_PROMPT_MAX_CHARS, (n, len(p))
        assert p.endswith(_PROMPT_SUFFIX)
