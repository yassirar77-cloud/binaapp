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
