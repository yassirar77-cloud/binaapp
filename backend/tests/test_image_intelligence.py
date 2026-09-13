"""
Imagery intelligence (image_intelligence.py): hero quality gate, dominant
colour extraction, Cloudinary section crops, and the dish-specific hero cue.
"""

import io

import pytest

from app.services import image_intelligence as ii

PIL = pytest.importorskip("PIL")
from PIL import Image  # noqa: E402


def _png(w, h, colour=(200, 40, 30)):
    buf = io.BytesIO()
    Image.new("RGB", (w, h), colour).save(buf, format="PNG")
    return buf.getvalue()


def test_hero_quality_gate():
    good = ii.hero_quality_from_bytes(_png(1600, 900))
    assert good.known and good.full_bleed_ok
    small = ii.hero_quality_from_bytes(_png(800, 600))
    assert small.known and not small.full_bleed_ok and "800px" in small.reason
    portrait = ii.hero_quality_from_bytes(_png(1200, 1600))
    assert portrait.portrait and not portrait.full_bleed_ok
    unknown = ii.hero_quality_from_bytes(None)
    assert not unknown.known and unknown.full_bleed_ok  # never block on a fetch failure
    assert not ii.hero_quality_from_bytes(b"not an image").known


def test_dominant_colours_skip_plate_white_and_shadow_black():
    img = Image.new("RGB", (60, 60), (255, 255, 255))
    for x in range(30):
        for y in range(60):
            img.putpixel((x, y), (210, 60, 30))  # sambal red
    for x in range(30, 45):
        for y in range(60):
            img.putpixel((x, y), (20, 20, 20))
    for x in range(45, 55):
        for y in range(60):
            img.putpixel((x, y), (40, 120, 60))  # pandan green
    buf = io.BytesIO(); img.save(buf, format="PNG")
    colours = ii.dominant_colours_from_bytes(buf.getvalue(), n=2)
    assert len(colours) == 2
    assert colours[0].startswith("#D") or colours[0].startswith("#C")  # red first
    assert all(c not in ("#FFFFFF", "#141414") for c in colours)
    assert ii.dominant_colours_from_bytes(None) == []


def test_cloudinary_crops_only_cloudinary_and_once():
    url = "https://res.cloudinary.com/demo/image/upload/v1712/binaapp/hero.jpg"
    hero = ii.cloudinary_transform(url, "hero")
    assert hero == "https://res.cloudinary.com/demo/image/upload/c_fill,ar_16:9,g_auto,w_1600,q_auto,f_auto/v1712/binaapp/hero.jpg"
    assert ii.cloudinary_transform(hero, "hero") == hero  # idempotent
    menu = ii.cloudinary_transform(url, "menu")
    assert "ar_4:3" in menu and "w_900" in menu
    assert "ar_3:2" in ii.cloudinary_transform(url, "gallery")
    other = "https://xyz.supabase.co/storage/v1/object/public/a.jpg"
    assert ii.cloudinary_transform(other, "hero") == other
    assert ii.cloudinary_transform(url, "unknown-role") == url


def test_apply_section_crops_and_uploaded_list():
    urls = {"hero": "https://res.cloudinary.com/demo/image/upload/h.jpg", "gallery1": "https://res.cloudinary.com/demo/image/upload/g1.jpg", "gallery1_name": "Ayam"}
    out = ii.apply_section_crops(urls)
    assert "ar_16:9" in out["hero"] and "ar_4:3" in out["gallery1"] and out["gallery1_name"] == "Ayam"
    uploaded = [{"url": urls["hero"], "name": "Hero Image"}, {"url": urls["gallery1"], "name": "Ayam", "price": "RM8"}, "https://res.cloudinary.com/demo/image/upload/x.jpg"]
    cropped = ii.crop_uploaded_images(uploaded)
    assert "ar_16:9" in cropped[0]["url"] and "ar_4:3" in cropped[1]["url"] and cropped[1]["price"] == "RM8"
    assert "ar_4:3" in cropped[2]


def test_direction_hero_cue_is_dish_specific_and_merchant_led():
    cue = ii.direction_hero_cue(image_cue="close-up plated Malaysian dishes on a steel counter", vertical="food", theme="bright",
                                item_names=["Ayam Goreng Berempah", "Kari Kepala Ikan"])
    assert cue.startswith("featuring Ayam Goreng Berempah, Kari Kepala Ikan")
    assert "daylight" in cue and "no people" in cue
    led = ii.direction_hero_cue(image_cue="x", vertical="food", theme="dark", item_names=[], merchant_prompt="Sate di atas arang, asap")
    assert led.startswith("Sate di atas arang, asap") and "evening light" in led
    generic = ii.direction_hero_cue(image_cue="happy person eating a burger", vertical="food", theme="bright")
    assert "person eating" not in generic and "the dish close-up" in generic
    salon = ii.direction_hero_cue(image_cue="bright salon interior", vertical="salon", theme="bright", item_names=["Gunting rambut"])
    assert "showing Gunting rambut" in salon and "no people" not in salon
