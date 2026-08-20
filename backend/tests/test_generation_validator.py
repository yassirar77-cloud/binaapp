"""Tests for the post-generation validator (the blocking pre-publish gate).

Fixtures are the three cases from the defect brief:

  1. Warung Kak Ropiah — the incident itself. A full F&B brief (priced items,
     catering packages, split Friday hours, JAKIM-registered premises) that
     shipped a site with four business-name-derived dishes and no prices.
  2. Multi-outlet kopitiam — per-outlet hours and a breakfast/lunch menu
     split, to prove the checks survive a more structured brief.
  3. Thin home-based input ("kuih tempahan, buat kat rumah, area putrajaya,
     whatsapp order") — must PASS with placeholders rather than being
     pressured into a fabricated address, price list or founding year.
"""

import pytest

from app.services.generation_validator import (
    GenerationBrief,
    SanitizerRemoval,
    brief_from_request,
    is_placeholder_phone,
    normalize_my_phone_digits,
    validate_generated_site,
)


def codes(issues):
    return {i.code for i in issues}


# ---------------------------------------------------------------------------
# Fixture 1 — Warung Kak Ropiah
# ---------------------------------------------------------------------------

KAK_ROPIAH_BRIEF = GenerationBrief(
    business_name="Warung Kak Ropiah",
    description="Warung nasi campur di Seksyen 13 Shah Alam. Resipi arwah ibu.",
    language="ms",
    whatsapp_number="0193456781",
    location_address="Seksyen 13, Shah Alam, Selangor",
    operating_hours="Isnin-Khamis 7:00 pagi - 4:00 petang; Jumaat tutup 12:00-14:30",
    menu_items=[
        {"name": "Nasi Campur Biasa", "price": "RM7.00"},
        {"name": "Ayam Masak Merah", "price": "RM5.50"},
        {"name": "Gulai Nangka", "price": "RM4.00"},
        {"name": "Pakej Katering A", "price": "RM18/pax", "category": "Katering"},
    ],
    model="glm-5.3",
)

GOOD_KAK_ROPIAH_HTML = """<!DOCTYPE html>
<html lang="ms"><head>
<title>Warung Kak Ropiah | Nasi Campur Shah Alam</title>
<meta name="description" content="Nasi campur masakan kampung di Seksyen 13 Shah Alam.">
<meta property="og:title" content="Warung Kak Ropiah">
<meta property="og:description" content="Nasi campur masakan kampung.">
<meta property="og:image" content="https://cdn.test/hero.jpg">
<meta property="og:url" content="https://kakropiah.binaapp.my">
<script type="application/ld+json">{"@context":"https://schema.org","@type":"Restaurant","name":"Warung Kak Ropiah"}</script>
</head><body>
<h1>Warung Kak Ropiah</h1>
<section id="menu">
  <h3>Nasi Campur Biasa</h3><p>RM7.00</p>
  <h3>Ayam Masak Merah</h3><p>RM5.50</p>
  <h3>Gulai Nangka</h3><p>RM4.00</p>
  <h3>Pakej Katering A</h3><p>RM18/pax</p>
</section>
<section id="hubungi">
  <p>Seksyen 13, Shah Alam, Selangor</p>
  <p>Isnin-Khamis 7:00 pagi - 4:00 petang. Jumaat tutup 12:00-14:30.</p>
  <a href="https://wa.me/60193456781">Pesan Sekarang</a>
</section>
</body></html>"""

#: What actually shipped: four business-name permutations, zero prices.
FABRICATED_KAK_ROPIAH_HTML = """<!DOCTYPE html>
<html lang="ms"><head><title>Warung Kak Ropiah</title></head><body>
<h1>Warung Kak Ropiah</h1>
<section id="menu">
  <h3>Kak Ropiah A0</h3><p>Hidangan istimewa kami.</p>
  <h3>Set Kak Ropiah A0</h3><p>Set lengkap untuk keluarga.</p>
  <h3>Kak Ropiah A0 Combo</h3><p>Gabungan terbaik.</p>
  <h3>Kak Ropiah A0 Istimewa</h3><p>Resipi rahsia.</p>
</section>
<a href="https://wa.me/60123456789">Pesan Sekarang</a>
</body></html>"""


class TestFixtureKakRopiah:
    def test_good_output_passes(self):
        result = validate_generated_site(GOOD_KAK_ROPIAH_HTML, KAK_ROPIAH_BRIEF)
        assert result.ok, result.error_messages()

    def test_the_actual_incident_is_blocked(self):
        result = validate_generated_site(FABRICATED_KAK_ROPIAH_HTML, KAK_ROPIAH_BRIEF)
        assert not result.ok
        found = codes(result.errors)
        assert "fabricated_item_name" in found
        assert "section_label_in_item_name" in found
        assert "missing_price" in found
        assert "placeholder_whatsapp" in found

    def test_every_missing_price_is_reported_individually(self):
        result = validate_generated_site(FABRICATED_KAK_ROPIAH_HTML, KAK_ROPIAH_BRIEF)
        missing = [e for e in result.errors if e.code == "missing_price"]
        assert len(missing) == 4
        assert any("RM18/pax" in e.detail for e in missing)

    def test_model_is_recorded_for_fallback_tuning(self):
        result = validate_generated_site(FABRICATED_KAK_ROPIAH_HTML, KAK_ROPIAH_BRIEF)
        assert result.model == "glm-5.3"
        assert result.as_dict()["model"] == "glm-5.3"


# ---------------------------------------------------------------------------
# Fixture 2 — multi-outlet kopitiam
# ---------------------------------------------------------------------------

KOPITIAM_BRIEF = GenerationBrief(
    business_name="Kopitiam Ah Seng",
    description="Kopitiam dua cawangan, sarapan dan makan tengah hari.",
    language="ms",
    whatsapp_number="0126677889",
    location_address="Jalan Ipoh, Kuala Lumpur",
    operating_hours="Cawangan Jalan Ipoh 6:30-15:00; Cawangan Cheras 7:00-16:00",
    menu_items=[
        {"name": "Roti Bakar Kaya", "price": "RM3.50", "category": "Sarapan"},
        {"name": "Nasi Lemak Ayam", "price": "RM8.90", "category": "Tengah Hari"},
        {"name": "Kopi O", "price": "RM2.20", "category": "Minuman"},
    ],
    model="deepseek-v4-pro",
)

KOPITIAM_HTML = """<!DOCTYPE html>
<html lang="ms"><head>
<title>Kopitiam Ah Seng</title>
<meta name="description" content="Kopitiam dua cawangan di Kuala Lumpur.">
<meta property="og:title" content="Kopitiam Ah Seng">
<meta property="og:description" content="Sarapan dan makan tengah hari.">
<meta property="og:image" content="https://cdn.test/k.jpg">
<meta property="og:url" content="https://ahseng.binaapp.my">
<script type="application/ld+json">{"@type":"Restaurant","name":"Kopitiam Ah Seng"}</script>
</head><body>
<h1>Kopitiam Ah Seng</h1>
<h2>Sarapan</h2><h3>Roti Bakar Kaya</h3><p>RM3.50</p>
<h2>Tengah Hari</h2><h3>Nasi Lemak Ayam</h3><p>RM8.90</p>
<h2>Minuman</h2><h3>Kopi O</h3><p>RM2.20</p>
<p>Jalan Ipoh, Kuala Lumpur</p>
<p>Cawangan Jalan Ipoh 6:30-15:00, Cawangan Cheras 7:00-16:00</p>
<a href="https://wa.me/60126677889">Hubungi Kami</a>
</body></html>"""


class TestFixtureKopitiam:
    def test_multi_outlet_output_passes(self):
        result = validate_generated_site(KOPITIAM_HTML, KOPITIAM_BRIEF)
        assert result.ok, result.error_messages()

    def test_dropping_one_outlets_hours_is_caught(self):
        html = KOPITIAM_HTML.replace(
            "<p>Cawangan Jalan Ipoh 6:30-15:00, Cawangan Cheras 7:00-16:00</p>", ""
        )
        result = validate_generated_site(html, KOPITIAM_BRIEF)
        assert "missing_operating_hours" in codes(result.errors)

    def test_dropping_a_menu_split_is_caught_by_price_integrity(self):
        html = KOPITIAM_HTML.replace("<h3>Kopi O</h3><p>RM2.20</p>", "")
        result = validate_generated_site(html, KOPITIAM_BRIEF)
        assert "missing_price" in codes(result.errors)


# ---------------------------------------------------------------------------
# Fixture 3 — thin home-based input
# ---------------------------------------------------------------------------

THIN_BRIEF = GenerationBrief(
    business_name="Kuih Mak Ngah",
    description="kuih tempahan, buat kat rumah, area putrajaya, whatsapp order",
    language="ms",
    whatsapp_number="0139988776",
    location_address=None,
    operating_hours=None,
    menu_items=[],
    model="glm-5.3",
)

THIN_PLACEHOLDER_HTML = """<!DOCTYPE html>
<html lang="ms"><head>
<title>Kuih Mak Ngah</title>
<meta name="description" content="Kuih tempahan di area Putrajaya.">
<meta property="og:title" content="Kuih Mak Ngah">
<meta property="og:description" content="Kuih tempahan.">
<meta property="og:image" content="https://cdn.test/kuih.jpg">
<meta property="og:url" content="https://maknagah.binaapp.my">
<script type="application/ld+json">{"@type":"Bakery","name":"Kuih Mak Ngah"}</script>
</head><body>
<h1>Kuih Mak Ngah</h1>
<section id="menu">
  <h2>Menu Akan Datang</h2>
  <p>Menu penuh akan dikemas kini tidak lama lagi. Hubungi kami untuk pertanyaan.</p>
</section>
<a href="https://wa.me/60139988776">Pesan Sekarang</a>
</body></html>"""


class TestFixtureThinInput:
    def test_placeholder_output_passes(self):
        """The whole point: an honest empty menu must be publishable."""
        result = validate_generated_site(THIN_PLACEHOLDER_HTML, THIN_BRIEF)
        assert result.ok, result.error_messages()

    def test_no_address_supplied_is_not_an_error(self):
        result = validate_generated_site(THIN_PLACEHOLDER_HTML, THIN_BRIEF)
        assert "missing_location" not in codes(result.errors)

    def test_fabricated_address_is_not_demanded(self):
        """The validator must never push the generator toward inventing."""
        result = validate_generated_site(THIN_PLACEHOLDER_HTML, THIN_BRIEF)
        assert "missing_operating_hours" not in codes(result.errors)

    def test_fabricated_items_still_blocked_on_a_thin_brief(self):
        html = THIN_PLACEHOLDER_HTML.replace(
            "<h2>Menu Akan Datang</h2>",
            "<h2>Menu</h2><h3>Set Kuih Mak Ngah</h3><h3>Kuih Mak Ngah Combo</h3>",
        )
        result = validate_generated_site(html, THIN_BRIEF)
        assert "fabricated_item_name" in codes(result.errors)


# ---------------------------------------------------------------------------
# Individual checks
# ---------------------------------------------------------------------------

class TestPlaceholderContacts:
    @pytest.mark.parametrize("number", ["60123456789", "0123456789", "60111111111"])
    def test_known_dummies_blocked(self, number):
        html = f'<html lang="ms"><body><a href="https://wa.me/{number}">Pesan</a></body></html>'
        result = validate_generated_site(html, GenerationBrief(business_name=""))
        assert "placeholder_whatsapp" in codes(result.errors)

    def test_real_number_passes(self):
        html = '<html lang="ms"><body><a href="https://wa.me/60193456781">Pesan</a></body></html>'
        result = validate_generated_site(html, GenerationBrief(business_name=""))
        assert "placeholder_whatsapp" not in codes(result.errors)

    def test_placeholder_tel_link_blocked(self):
        html = '<html lang="ms"><body><a href="tel:+60123456789">Call</a></body></html>'
        result = validate_generated_site(html, GenerationBrief(business_name=""))
        assert "placeholder_phone" in codes(result.errors)

    def test_empty_wa_link_blocked(self):
        html = '<html lang="ms"><body><a href="https://wa.me/">Pesan</a></body></html>'
        result = validate_generated_site(html, GenerationBrief(business_name=""))
        assert "empty_whatsapp_link" in codes(result.errors)

    @pytest.mark.parametrize("raw,expected", [
        ("0193456781", "60193456781"),
        ("+60 19-345 6781", "60193456781"),
        ("60123456789", ""),
        ("60111111111", ""),
        ("123", ""),
        (None, ""),
    ])
    def test_normalizer(self, raw, expected):
        assert normalize_my_phone_digits(raw) == expected

    def test_is_placeholder_phone(self):
        assert is_placeholder_phone("60123456789")
        assert not is_placeholder_phone("60193456781")
        assert not is_placeholder_phone("")


class TestDerivedItemNames:
    def test_supplied_item_named_set_a_is_allowed(self):
        """Merchant data always wins, however odd it looks."""
        brief = GenerationBrief(
            business_name="Katering Ali",
            menu_items=[{"name": "Set A", "price": "RM20"}],
        )
        html = '<html lang="ms"><body><h1>Katering Ali</h1><h3>Set A</h3><p>RM20</p>' \
               '<a href="tel:60193456781">Call</a></body></html>'
        result = validate_generated_site(html, brief)
        assert "fabricated_item_name" not in codes(result.errors)

    def test_shop_type_word_alone_is_not_business_name_overlap(self):
        """'Warung' in an item name must not trip the check by itself."""
        brief = GenerationBrief(business_name="Warung Sedap")
        html = '<html lang="ms"><body><h3>Set Warung Special</h3></body></html>'
        result = validate_generated_site(html, brief)
        assert "fabricated_item_name" not in codes(result.errors)

    def test_business_name_without_suffix_is_not_flagged(self):
        """The <h1> is the business name — that is correct, not fabrication."""
        brief = GenerationBrief(business_name="Warung Kak Ropiah")
        html = '<html lang="ms"><body><h1>Warung Kak Ropiah</h1></body></html>'
        result = validate_generated_site(html, brief)
        assert "fabricated_item_name" not in codes(result.errors)


class TestSanitizerTrace:
    def test_bare_deletion_is_an_error(self):
        brief = GenerationBrief(
            business_name="Warung X",
            sanitizer_removals=[SanitizerRemoval(claim="Halal", substitution="")],
        )
        result = validate_generated_site("<html><body><h1>Warung X</h1></body></html>", brief)
        assert "sanitizer_bare_deletion" in codes(result.errors)

    def test_substituted_removal_passes(self):
        brief = GenerationBrief(
            business_name="Warung X",
            sanitizer_removals=[
                SanitizerRemoval(claim="Halal", substitution="Tiada Babi & Arak")
            ],
        )
        result = validate_generated_site("<html><body><h1>Warung X</h1></body></html>", brief)
        assert "sanitizer_bare_deletion" not in codes(result.errors)


class TestWarnings:
    def test_metadata_warnings_do_not_block(self):
        html = '<html lang="ms"><body><h1>Kedai A</h1>' \
               '<a href="https://wa.me/60193456781">Pesan</a></body></html>'
        result = validate_generated_site(html, GenerationBrief(business_name="Kedai A"))
        assert result.ok
        found = codes(result.warnings)
        assert "missing_title" in found
        assert "missing_og_tag" in found
        assert "missing_json_ld" in found

    def test_long_meta_description_warns(self):
        html = (
            '<html lang="ms"><head><title>A</title>'
            f'<meta name="description" content="{"x" * 200}">'
            '</head><body><h1>Kedai A</h1>'
            '<a href="https://wa.me/60193456781">Pesan</a></body></html>'
        )
        result = validate_generated_site(html, GenerationBrief(business_name="Kedai A"))
        assert "long_meta_description" in codes(result.warnings)

    def test_invalid_json_ld_warns(self):
        html = (
            '<html lang="ms"><head><title>A</title>'
            '<script type="application/ld+json">{not valid json}</script>'
            '</head><body><h1>Kedai A</h1>'
            '<a href="https://wa.me/60193456781">Pesan</a></body></html>'
        )
        result = validate_generated_site(html, GenerationBrief(business_name="Kedai A"))
        assert "invalid_json_ld" in codes(result.warnings)

    def test_english_cta_on_malay_page_warns(self):
        html = '<html lang="ms"><body><h1>Kedai A</h1>' \
               '<a href="https://wa.me/60193456781">Order Now</a></body></html>'
        result = validate_generated_site(html, GenerationBrief(business_name="Kedai A"))
        assert "mixed_language_cta" in codes(result.warnings)

    def test_empty_image_and_slot_warn(self):
        html = (
            '<html lang="ms"><body><h1>Kedai A</h1><img alt="x">'
            '<div id="binaapp-contact-slot"></div>'
            '<a href="https://wa.me/60193456781">Pesan</a></body></html>'
        )
        result = validate_generated_site(html, GenerationBrief(business_name="Kedai A"))
        found = codes(result.warnings)
        assert "empty_image" in found
        assert "empty_injection_slot" in found


class TestRequiredFields:
    def test_missing_business_name_errors(self):
        html = '<html lang="ms"><body><h1>Something Else</h1>' \
               '<a href="https://wa.me/60193456781">Pesan</a></body></html>'
        result = validate_generated_site(html, GenerationBrief(business_name="Warung Kak Ropiah"))
        assert "missing_business_name" in codes(result.errors)

    def test_no_contact_method_errors(self):
        html = '<html lang="ms"><body><h1>Kedai A</h1><p>Selamat datang</p></body></html>'
        result = validate_generated_site(html, GenerationBrief(business_name="Kedai A"))
        assert "no_contact_method" in codes(result.errors)

    def test_contact_form_counts_as_contact(self):
        html = '<html lang="ms"><body><h1>Kedai A</h1><form><input name="x"></form></body></html>'
        result = validate_generated_site(html, GenerationBrief(business_name="Kedai A"))
        assert "no_contact_method" not in codes(result.errors)


class TestPurityAndRobustness:
    def test_empty_html_errors(self):
        result = validate_generated_site("", GenerationBrief(business_name="X"))
        assert not result.ok
        assert "empty_html" in codes(result.errors)

    def test_does_not_mutate_the_brief(self):
        brief = GenerationBrief(
            business_name="Warung Kak Ropiah",
            menu_items=[{"name": "Nasi Campur Biasa", "price": "RM7.00"}],
        )
        before = (brief.business_name, list(brief.menu_items), brief.language)
        validate_generated_site(FABRICATED_KAK_ROPIAH_HTML, brief)
        assert (brief.business_name, list(brief.menu_items), brief.language) == before

    def test_deterministic(self):
        a = validate_generated_site(FABRICATED_KAK_ROPIAH_HTML, KAK_ROPIAH_BRIEF).as_dict()
        b = validate_generated_site(FABRICATED_KAK_ROPIAH_HTML, KAK_ROPIAH_BRIEF).as_dict()
        assert a == b

    def test_malformed_html_never_raises(self):
        for html in ("<html", "<<>>", "<div><p>unclosed", "&&&&", "<img src=>"):
            validate_generated_site(html, KAK_ROPIAH_BRIEF)

    def test_price_split_across_tags_still_counts(self):
        brief = GenerationBrief(
            business_name="Kedai A",
            menu_items=[{"name": "Nasi", "price": "RM7.00"}],
        )
        html = ('<html lang="ms"><body><h1>Kedai A</h1><h3>Nasi</h3>'
                '<span>RM</span><span>7.00</span>'
                '<a href="https://wa.me/60193456781">Pesan</a></body></html>')
        result = validate_generated_site(html, brief)
        assert "missing_price" not in codes(result.errors)


class TestBriefFromRequest:
    def test_builds_from_a_real_request(self):
        from app.models.schemas import WebsiteGenerationRequest

        request = WebsiteGenerationRequest(
            description="warung nasi campur shah alam",
            business_name="Warung Kak Ropiah",
            subdomain="kakropiah",
            whatsapp_number="0193456781",
            menu_items=[{"name": "Nasi Campur Biasa", "price": "RM7.00"}],
        )
        brief = brief_from_request(request, model="glm-5.3")
        assert brief.business_name == "Warung Kak Ropiah"
        assert brief.menu_items == [
            {"name": "Nasi Campur Biasa", "price": "RM7.00", "category": ""}
        ]
        assert brief.language == "ms"
        assert brief.model == "glm-5.3"

    def test_legacy_string_trace_counts_as_bare_deletion(self):
        brief = brief_from_request(
            type("R", (), {"business_name": "X", "description": "y"})(),
            sanitizer_removals=["Halal"],
        )
        assert brief.sanitizer_removals[0].substitution == ""

    def test_never_raises_on_junk(self):
        brief = brief_from_request(object(), sanitizer_removals=[None, 123])
        assert isinstance(brief.business_name, str)


class TestPublishGateScoping:
    """The publish path only has a weak brief (project name + description),
    so it may only enforce checks that need no merchant ground truth.
    Enforcing the rest there would block legitimate hand-edited pages."""

    def test_weak_brief_errors_are_not_blocking_at_publish(self):
        from app.services.generation_validator import (
            PUBLISH_ENFORCED_CODES,
            blocking_errors,
        )

        html = "<html lang=\"ms\"><body><p>Selamat datang</p></body></html>"
        result = validate_generated_site(html, GenerationBrief(business_name="Bakery 01"))
        # Brief-dependent checks still fire...
        assert "missing_business_name" in codes(result.errors)
        assert "no_contact_method" in codes(result.errors)
        # ...but none of them block a publish.
        assert blocking_errors(result, PUBLISH_ENFORCED_CODES) == []

    def test_fake_number_blocks_at_publish(self):
        from app.services.generation_validator import (
            PUBLISH_ENFORCED_CODES,
            blocking_errors,
        )

        html = ('<html lang="ms"><body><h1>Bakery 01</h1>'
                '<a href="https://wa.me/60123456789">Pesan</a></body></html>')
        result = validate_generated_site(html, GenerationBrief(business_name="Bakery 01"))
        blocked = blocking_errors(result, PUBLISH_ENFORCED_CODES)
        assert [e.code for e in blocked] == ["placeholder_whatsapp"]

    def test_fabricated_items_block_at_publish(self):
        from app.services.generation_validator import (
            PUBLISH_ENFORCED_CODES,
            blocking_errors,
        )

        html = ('<html lang="ms"><body><h1>Warung Kak Ropiah</h1>'
                '<h3>Set Kak Ropiah A0</h3>'
                '<a href="https://wa.me/60193456781">Pesan</a></body></html>')
        result = validate_generated_site(
            html, GenerationBrief(business_name="Warung Kak Ropiah")
        )
        assert blocking_errors(result, PUBLISH_ENFORCED_CODES)

    def test_generation_path_enforces_everything(self):
        from app.services.generation_validator import blocking_errors

        html = "<html lang=\"ms\"><body><p>Selamat datang</p></body></html>"
        result = validate_generated_site(html, GenerationBrief(business_name="Bakery 01"))
        # No filter -> every error blocks (full brief available at generation).
        assert len(blocking_errors(result)) == len(result.errors) > 0
