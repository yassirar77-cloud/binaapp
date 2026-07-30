"""P1 correctness fixes from the generation-defect audit.

  P1-1  Sanitizer stripped an unverified halal claim and left nothing, AND
        the prompt suppressed the word even when the merchant DID state it
        (JAKIM-registered premises). Substitution is covered in
        test_claim_sanitizer; this file covers the prompt-side carve-out.
  P1-2  Friday split hours ("closed 12:00-14:30 for Jumaat prayers")
        collapsed into "Pagi hingga petang, Isnin tutup".
  P1-3  Factual drift: 'late mother' became 'nenek', gulai nangka was
        described as "asam manis", a "15+ Tahun" badge was invented, and a
        3-up stat row was padded with "2 Signature Lauk".
  P1-4  "majas rumah" shipped in the catering section.
"""

import pytest

from app.services.ai_service import AIService
from app.services.generation_linter import lint_malay_typos, lint_html
from app.services.generation_validator import (
    GenerationBrief,
    validate_generated_site,
)


@pytest.fixture
def service():
    return AIService.__new__(AIService)


def _prompt(service, **kw):
    params = dict(
        name="Warung Kak Ropiah",
        desc="Warung nasi campur di Seksyen 13 Shah Alam.",
        style="modern",
        language="ms",
        whatsapp_number="0193456781",
        image_choice="ai",
        images={"hero": "https://cdn.test/h.jpg"},
    )
    params.update(kw)
    return service._build_strict_prompt(**params)


# ---------------------------------------------------------------------------
# P1-1 — merchant-stated trust signals must be INCLUDED, not suppressed
# ---------------------------------------------------------------------------

class TestHalalCarveOut:
    def test_merchant_stated_halal_is_affirmatively_required(self, service):
        p = _prompt(service, desc=(
            "Warung nasi campur. Premis berdaftar JAKIM, sijil halal dipaparkan."
        ))
        assert "MERCHANT-STATED TRUST SIGNALS" in p
        assert "You MUST surface this on the page" in p
        assert "halal" in p.lower()

    def test_no_carve_out_when_nothing_was_stated(self, service):
        p = _prompt(service, desc="Warung nasi campur masakan kampung harian.")
        assert "MERCHANT-STATED TRUST SIGNALS" not in p

    def test_carve_out_forbids_upgrading_the_claim(self, service):
        """Stating 'premis berdaftar JAKIM' must not become 'JAKIM Certified'."""
        p = _prompt(service, desc="Warung nasi campur. Premis berdaftar JAKIM.")
        assert "Do NOT upgrade or embellish it" in p

    def test_general_no_invention_rule_still_present(self, service):
        """The carve-out must not weaken the ban for unstated claims."""
        p = _prompt(service, desc="Warung nasi campur. Premis berdaftar JAKIM.")
        assert "do NOT add any certification, authority, or logo the merchant did not state" in p


# ---------------------------------------------------------------------------
# P1-2 — split operating hours
# ---------------------------------------------------------------------------

class TestSplitOperatingHours:
    FRIDAY_SPLIT = [
        {"days": "Isnin - Khamis", "hours": "7:00 pagi - 4:00 petang"},
        {"days": "Jumaat",
         "hours": ["7:00 pagi - 12:00 tgh", "2:30 petang - 4:00 petang"],
         "note": "Rehat solat Jumaat"},
        {"days": "Ahad", "hours": "Tutup"},
    ]

    def test_both_friday_blocks_render(self, service):
        html = service._render_operating_hours_html(self.FRIDAY_SPLIT, "default")
        assert "7:00 pagi - 12:00 tgh" in html
        assert "2:30 petang - 4:00 petang" in html

    def test_split_ranges_are_on_separate_lines(self, service):
        html = service._render_operating_hours_html(self.FRIDAY_SPLIT, "default")
        assert "12:00 tgh<br>2:30 petang" in html

    def test_note_is_rendered(self, service):
        html = service._render_operating_hours_html(self.FRIDAY_SPLIT, "default")
        assert "Rehat solat Jumaat" in html

    def test_plain_string_hours_still_work(self, service):
        html = service._render_operating_hours_html(
            [{"days": "Setiap hari", "hours": "9:00 - 18:00"}], "default"
        )
        assert "9:00 - 18:00" in html
        assert "<br>" not in html

    @pytest.mark.parametrize("value,expected", [
        ("7:00 - 16:00", "7:00 - 16:00"),
        (["7:00 - 12:00", "14:30 - 16:00"], "7:00 - 12:00<br>14:30 - 16:00"),
        ([{"open": "8:00", "close": "13:00"}], "8:00 - 13:00"),
        ({"open": "8:00", "close": "13:00"}, "8:00 - 13:00"),
        ([], ""),
        (None, ""),
    ])
    def test_format_hour_ranges_contract(self, service, value, expected):
        assert service._format_hour_ranges(value) == expected

    def test_copy_prompt_forbids_collapsing_a_split_day(self, service):
        prompt = service._build_content_only_prompt(
            business_name="Warung Kak Ropiah",
            description="warung nasi campur",
            language="ms",
            phone="60193456781",
            address="Shah Alam",
            menu_items=[],
            operating_hours=self.FRIDAY_SPLIT,
        )
        # The rule wraps across lines in the prompt — compare on normalised
        # whitespace so re-wrapping the source doesn't break the test.
        flat = " ".join(prompt.split())
        assert "SPLIT HOURS" in flat
        assert "NEVER collapse a split day into a single range" in flat
        assert "never silently drop the closure" in flat
        # Both blocks reach the copywriter.
        assert "7:00 pagi - 12:00 tgh" in prompt
        assert "2:30 petang - 4:00 petang" in prompt
        assert "Rehat solat Jumaat" in prompt


# ---------------------------------------------------------------------------
# P1-3 — factual drift
# ---------------------------------------------------------------------------

class TestFactualDrift:
    def test_prompt_bans_invented_stat_numbers(self, service):
        p = _prompt(service)
        assert "STAT / BADGE NUMBERS MUST BE REAL" in p
        assert "15+ Tahun" in p          # the exact invented badge, as an example
        assert "2 Signature Lauk" in p   # the exact padding metric, as an example

    def test_prompt_requires_fewer_cells_over_padding(self, service):
        p = _prompt(service)
        assert "RENDER FEWER CELLS" in p

    def test_prompt_pins_relationships_and_flavour(self, service):
        p = _prompt(service)
        assert "RELATIONSHIPS AND PROVENANCE MUST BE EXACT" in p
        assert "nenek" in p          # the exact drift that shipped
        assert "asam manis" in p     # the exact wrong flavour claim

    def test_glm_system_prompt_carries_the_same_rules(self, service):
        rules = AIService._GLM_PROMPT_RULES_HEAD
        assert "NEVER pad a fixed-slot layout with an invented metric" in rules
        assert "late" in rules and "mother" in rules

    @pytest.mark.parametrize("snippet", [
        "15+ Tahun", "1000+ Pelanggan", "4.9 bintang", "250 ulasan",
    ])
    def test_validator_flags_invented_metrics(self, snippet):
        brief = GenerationBrief(
            business_name="Warung Kak Ropiah",
            description="Warung nasi campur di Seksyen 13 Shah Alam.",
        )
        html = (f'<html lang="ms"><body><h1>Warung Kak Ropiah</h1><span>{snippet}</span>'
                f'<a href="https://wa.me/60193456781">P</a></body></html>')
        result = validate_generated_site(html, brief)
        assert any(w.code == "invented_metric" for w in result.warnings), snippet

    def test_validator_allows_figures_present_in_the_brief(self):
        brief = GenerationBrief(
            business_name="Warung X",
            description="Beroperasi 15 tahun di Shah Alam",
        )
        html = ('<html lang="ms"><body><h1>Warung X</h1><span>15+ Tahun</span>'
                '<a href="https://wa.me/60193456781">P</a></body></html>')
        result = validate_generated_site(html, brief)
        assert not any(w.code == "invented_metric" for w in result.warnings)

    def test_invented_metrics_warn_but_do_not_block(self):
        """A number can legitimately reach the page via supplied data, and the
        publish-time brief is weak — flag for review, never block."""
        brief = GenerationBrief(business_name="Warung X")
        html = ('<html lang="ms"><body><h1>Warung X</h1><span>1000+ Pelanggan</span>'
                '<a href="https://wa.me/60193456781">P</a></body></html>')
        result = validate_generated_site(html, brief)
        assert any(w.code == "invented_metric" for w in result.warnings)
        assert not any(e.code == "invented_metric" for e in result.errors)


# ---------------------------------------------------------------------------
# P1-4 — Malay typo pass
# ---------------------------------------------------------------------------

class TestMalayTypoLinter:
    def test_majas_becomes_majlis(self):
        out, fixes = lint_malay_typos("<p>Sesuai untuk majas rumah.</p>")
        assert "majlis rumah" in out
        assert fixes == [("majas", "majlis")]

    def test_capitalisation_preserved(self):
        assert "Majlis Rumah" in lint_malay_typos("<h3>Majas Rumah</h3>")[0]
        assert "MAJLIS" in lint_malay_typos("<p>MAJAS RUMAH</p>")[0]

    def test_script_and_style_bodies_untouched(self):
        html = '<script>var majas = "majas";</script><p>majas</p>'
        out, _ = lint_malay_typos(html)
        assert 'var majas = "majas";' in out      # JS identifier intact
        assert "<p>majlis</p>" in out

    def test_attributes_and_urls_untouched(self):
        html = '<a href="/majas-rumah" class="majas-card">majas</a>'
        out, _ = lint_malay_typos(html)
        assert 'href="/majas-rumah"' in out
        assert 'class="majas-card"' in out
        assert ">majlis<" in out

    def test_correct_spelling_is_left_alone(self):
        html = "<p>majlis perkahwinan dan majlis korporat</p>"
        out, fixes = lint_malay_typos(html)
        assert out == html
        assert fixes == []

    def test_wired_into_lint_html(self):
        out, report = lint_html("<p>tempahan untuk majas rumah</p>")
        assert "majlis rumah" in out
        assert report.typo_fixes == [("majas", "majlis")]
        assert report.changed

    def test_empty_input_is_safe(self):
        assert lint_malay_typos("") == ("", [])
