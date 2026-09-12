"""The pre-publish gate: assertions run on the FINAL HTML before it ships.

Five defects shipped to a live merchant site and none of them was caught by a
check. This module covers the four that a page can be judged on by itself,
with no merchant ground truth needed — so all four block at publish as well as
at generation:

  * literal backslash escapes rendered as visible text
  * an empty (or absent) <title> / meta description
  * an unresolved template placeholder or a developer-facing caption
  * the unfilled business-name marker

plus the one that needs the brief: a testimonial the merchant never supplied.
"""

import pytest

from app.services.generation_validator import (
    PUBLISH_ENFORCED_CODES,
    GenerationBrief,
    blocking_errors,
    business_name_placeholder,
    is_business_name_placeholder,
    validate_generated_site,
)

B = chr(92)
EM_DASH = B + "u2014"
PHONE_EMOJI = B + "U0001f4f1"


def codes(issues):
    return {i.code for i in issues}


def page(body: str, head: str = "", lang: str = "ms") -> str:
    """A page that passes every check except what the body introduces."""
    return (
        f'<html lang="{lang}"><head>'
        "<title>Warung Kak Ropiah</title>"
        '<meta name="description" content="Nasi campur Shah Alam.">'
        f"{head}</head><body>"
        "<h1>Warung Kak Ropiah</h1>"
        '<a href="https://wa.me/60193456781">Pesan</a>'
        f"{body}</body></html>"
    )


BRIEF = GenerationBrief(
    business_name="Warung Kak Ropiah",
    description="Warung nasi campur di Seksyen 13 Shah Alam.",
    whatsapp_number="0193456781",
)


class TestCleanPageStillPasses:
    def test_no_false_positives_on_a_good_page(self):
        html = page(
            "<p>Masakan rumah — resipi arwah ibu. Hubungi kami 📱</p>"
            '<section id="ulasan"><h2>Ulasan Pelanggan</h2>'
            "<p>Belum ada ulasan lagi.</p>"
            '<a href="#hubungi">Tambah ulasan anda</a></section>'
        )
        result = validate_generated_site(html, BRIEF)
        assert result.ok, result.error_messages()


class TestUnicodeEscapeLeak:
    @pytest.mark.parametrize("token", [EM_DASH, PHONE_EMOJI, B + "xe9"])
    def test_escape_in_body_text_is_an_error(self, token):
        result = validate_generated_site(page(f"<p>Kedai {token} Roti</p>"), BRIEF)
        assert "unicode_escape_leak" in codes(result.errors)

    def test_escape_in_the_title_is_an_error(self):
        html = (
            f'<html lang="ms"><head><title>Warung {EM_DASH} Nasi</title>'
            '<meta name="description" content="Nasi campur."></head>'
            '<body><h1>Warung</h1><a href="https://wa.me/60193456781">Pesan</a>'
            "</body></html>"
        )
        assert "unicode_escape_leak" in codes(validate_generated_site(html, BRIEF).errors)

    def test_escape_in_the_meta_description_is_an_error(self):
        html = (
            '<html lang="ms"><head><title>Warung</title>'
            f'<meta name="description" content="Masakan rumah {EM_DASH} sedap">'
            '</head><body><h1>Warung</h1>'
            '<a href="https://wa.me/60193456781">Pesan</a></body></html>'
        )
        assert "unicode_escape_leak" in codes(validate_generated_site(html, BRIEF).errors)

    def test_the_failure_message_carries_the_offending_snippet(self):
        result = validate_generated_site(page(f"<p>Kedai {EM_DASH} Roti</p>"), BRIEF)
        leak = next(e for e in result.errors if e.code == "unicode_escape_leak")
        assert EM_DASH in leak.detail
        assert "Kedai" in leak.detail

    def test_escapes_inside_script_are_not_a_leak(self):
        html = page(f"<script>var s = '{B}u003cbr{B}u003e';</script>")
        assert "unicode_escape_leak" not in codes(validate_generated_site(html, BRIEF).errors)

    def test_real_emoji_and_em_dash_are_fine(self):
        html = page("<p>Nasi Lemak — sedap 📱</p>")
        assert "unicode_escape_leak" not in codes(validate_generated_site(html, BRIEF).errors)

    def test_blocks_at_publish(self):
        result = validate_generated_site(page(f"<p>{EM_DASH}</p>"), GenerationBrief())
        assert "unicode_escape_leak" in codes(blocking_errors(result, PUBLISH_ENFORCED_CODES))


class TestRequiredMetadata:
    def test_missing_title_is_an_error(self):
        html = (
            '<html lang="ms"><head><meta name="description" content="Nasi.">'
            '</head><body><h1>Warung Kak Ropiah</h1>'
            '<a href="https://wa.me/60193456781">Pesan</a></body></html>'
        )
        assert "missing_title" in codes(validate_generated_site(html, BRIEF).errors)

    def test_empty_title_is_an_error(self):
        html = (
            '<html lang="ms"><head><title>   </title>'
            '<meta name="description" content="Nasi."></head>'
            '<body><h1>Warung Kak Ropiah</h1>'
            '<a href="https://wa.me/60193456781">Pesan</a></body></html>'
        )
        assert "missing_title" in codes(validate_generated_site(html, BRIEF).errors)

    def test_empty_meta_description_is_an_error(self):
        html = (
            '<html lang="ms"><head><title>Warung</title>'
            '<meta name="description" content=""></head>'
            '<body><h1>Warung Kak Ropiah</h1>'
            '<a href="https://wa.me/60193456781">Pesan</a></body></html>'
        )
        assert "missing_meta_description" in codes(validate_generated_site(html, BRIEF).errors)

    def test_both_block_at_publish(self):
        result = validate_generated_site(
            "<html lang='ms'><body><p>hi</p></body></html>", GenerationBrief()
        )
        blocked = codes(blocking_errors(result, PUBLISH_ENFORCED_CODES))
        assert {"missing_title", "missing_meta_description"} <= blocked


class TestUnresolvedPlaceholders:
    @pytest.mark.parametrize(
        "token",
        [
            "{{business_name}}",
            "{{ hero_title }}",
            "[BUSINESS_NAME]",
            "HERO_IMAGE_URL",
            "PHOTO_SLOT_3",
            "${businessName}",
            "Lorem ipsum dolor sit amet",
        ],
    )
    def test_template_token_is_an_error(self, token):
        result = validate_generated_site(page(f"<p>{token}</p>"), BRIEF)
        assert "unresolved_placeholder" in codes(result.errors)

    @pytest.mark.parametrize(
        "caption",
        [
            "Peta lokasi akan dipaparkan di sini",
            "Map will be displayed here",
            "Image goes here",
        ],
    )
    def test_dead_placeholder_caption_is_an_error(self, caption):
        result = validate_generated_site(page(f"<div>{caption}</div>"), BRIEF)
        assert "dead_placeholder_text" in codes(result.errors)

    @pytest.mark.parametrize(
        "copy",
        [
            "Menu baru akan datang tidak lama lagi",
            "New flavours coming soon",
        ],
    )
    def test_a_merchants_own_coming_soon_copy_is_not_blocked(self, copy):
        """These read as developer captions but merchants write them about
        real things. Blocking a publish over one would be a false positive."""
        result = validate_generated_site(page(f"<p>{copy}</p>"), BRIEF)
        assert "dead_placeholder_text" not in codes(result.errors)

    def test_a_real_map_embed_is_not_a_placeholder(self):
        html = page(
            '<iframe src="https://maps.google.com/maps?q=Seksyen+13+Shah+Alam&output=embed"'
            ' title="Peta lokasi"></iframe>'
        )
        result = validate_generated_site(html, BRIEF)
        assert "dead_placeholder_text" not in codes(result.errors)
        assert "unresolved_placeholder" not in codes(result.errors)

    def test_blocks_at_publish(self):
        result = validate_generated_site(page("<p>{{tagline}}</p>"), GenerationBrief())
        assert "unresolved_placeholder" in codes(
            blocking_errors(result, PUBLISH_ENFORCED_CODES)
        )


class TestBusinessNamePlaceholder:
    def test_helpers_agree(self):
        assert is_business_name_placeholder(business_name_placeholder("ms"))
        assert is_business_name_placeholder(business_name_placeholder("en"))
        assert is_business_name_placeholder("nama perniagaan anda")
        assert not is_business_name_placeholder("Warung Kak Ropiah")
        assert not is_business_name_placeholder("Kedai")
        assert not is_business_name_placeholder("")

    def test_unknown_language_falls_back_to_malay(self):
        assert business_name_placeholder("fr") == business_name_placeholder("ms")
        assert business_name_placeholder(None) == business_name_placeholder("ms")

    @pytest.mark.parametrize("lang", ["ms", "en"])
    def test_placeholder_on_the_page_is_an_error(self, lang):
        marker = business_name_placeholder(lang)
        html = (
            f'<html lang="{lang}"><head><title>{marker}</title>'
            f'<meta name="description" content="{marker} di Shah Alam."></head>'
            f"<body><h1>{marker}</h1>"
            '<a href="https://wa.me/60193456781">Pesan</a></body></html>'
        )
        result = validate_generated_site(html, GenerationBrief(business_name=marker))
        assert "business_name_placeholder" in codes(result.errors)

    def test_blocks_at_publish(self):
        marker = business_name_placeholder("ms")
        result = validate_generated_site(page(f"<footer>{marker}</footer>"), GenerationBrief())
        assert "business_name_placeholder" in codes(
            blocking_errors(result, PUBLISH_ENFORCED_CODES)
        )

    def test_a_real_name_is_not_flagged(self):
        result = validate_generated_site(page("<footer>Warung Kak Ropiah</footer>"), BRIEF)
        assert "business_name_placeholder" not in codes(result.errors)


TESTIMONIAL_SECTION = (
    '<section id="testimoni"><h2>Kata Pelanggan</h2>'
    '<div class="testimonial-card">'
    '<i class="fa-solid fa-star"></i>'
    "<p>&ldquo;Nasi campur paling sedap di Shah Alam, sentiasa panas!&rdquo;</p>"
    "<span>Encik Rahman</span></div></section>"
)


class TestFabricatedTestimonials:
    def test_invented_reviews_are_an_error_when_none_were_supplied(self):
        result = validate_generated_site(page(TESTIMONIAL_SECTION), BRIEF)
        assert "fabricated_testimonial" in codes(result.errors)

    def test_supplied_reviews_are_allowed(self):
        brief = GenerationBrief(
            business_name="Warung Kak Ropiah",
            reviews=[{"name": "Encik Rahman", "text": "Nasi campur paling sedap."}],
        )
        result = validate_generated_site(page(TESTIMONIAL_SECTION), brief)
        assert "fabricated_testimonial" not in codes(result.errors)

    def test_an_empty_state_is_not_a_fabricated_review(self):
        html = page(
            '<section id="ulasan"><h2>Ulasan Pelanggan</h2>'
            "<p>Belum ada ulasan lagi. Ulasan sebenar daripada pelanggan anda "
            "akan muncul di sini.</p>"
            '<a href="#hubungi">Tambah ulasan anda</a></section>'
        )
        result = validate_generated_site(html, BRIEF)
        assert "fabricated_testimonial" not in codes(result.errors)

    def test_not_enforced_at_publish(self):
        """At publish the brief is unknown — a merchant who has since pasted
        in their real reviews must not be blocked by them."""
        result = validate_generated_site(page(TESTIMONIAL_SECTION), GenerationBrief())
        assert "fabricated_testimonial" not in codes(
            blocking_errors(result, PUBLISH_ENFORCED_CODES)
        )


class TestGateFailsLoudly:
    def test_every_new_error_carries_a_detail_snippet(self):
        marker = business_name_placeholder("ms")
        html = page(
            f"<p>Kedai {EM_DASH} Roti</p>"
            "<p>{{tagline}}</p>"
            "<div>Peta lokasi akan dipaparkan di sini</div>"
            f"<footer>{marker}</footer>"
            + TESTIMONIAL_SECTION
        )
        result = validate_generated_site(html, BRIEF)
        found = codes(result.errors)
        assert {
            "unicode_escape_leak",
            "unresolved_placeholder",
            "dead_placeholder_text",
            "business_name_placeholder",
            "fabricated_testimonial",
        } <= found
        for err in result.errors:
            assert err.detail, f"{err.code} reported nothing to look at"


class TestFabricatedTestimonialsFalsePositives:
    """The quote detector reads rendered text, not markup — a long class list
    or URL sitting inside a quoted attribute is not somebody's review."""

    def test_long_attribute_values_are_not_quotes(self):
        html = page(
            '<section id="ulasan" class="py-20 md:py-28 bg-surface rounded-2xl shadow-lg">'
            '<h2>Ulasan Pelanggan</h2>'
            '<a href="https://wa.me/60193456781?text=Salam%20saya%20nak%20tanya">'
            "Tambah ulasan anda</a>"
            "<p>Belum ada ulasan lagi.</p></section>"
        )
        result = validate_generated_site(html, BRIEF)
        assert "fabricated_testimonial" not in codes(result.errors)

    def test_a_short_label_in_quotes_is_not_a_review(self):
        html = page('<section id="ulasan"><h2>Ulasan</h2><p>"Sedap"</p></section>')
        result = validate_generated_site(html, BRIEF)
        assert "fabricated_testimonial" not in codes(result.errors)
