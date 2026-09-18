"""
Tests for the blank-page guard: HTML truncated before any body content.

Regression context — a production generation burned 374s and shipped a blank
website. The log told the whole story:

    DeepSeek ✅ Generated 90119 chars (finish_reason=length, completion_tokens=24000)
    DeepSeek output usage: 24000/24000 tokens (100% of cap)
    Pass 2 regeneration unusable (empty/non-HTML/truncated) — keeping the previous attempt
    Plan gate result: {"served_attempt": 1, "critique": {"average": 6.5, ...}}
    HTML TRUNCATED at 90550 chars (no </html>)
    Unclosed tags (3): ['html', 'head', 'style']
    🔧 Auto-emitted 2 missing closer(s): </style></head>

The model spent its entire 24K output budget elaborating the <head> stylesheet
and the response was cut off mid-CSS-rule, having never opened <body>. The
truncation repair then auto-closed it into a *structurally valid* document —
`</style></head></body></html>` — with an empty body. Every downstream check
passed (balance scan, validation, publish gate) and the merchant got a blank
white page.

Three things had to be wrong at once, and all three are covered here:
  1. _extract_html manufactured a renderable-looking page out of a head-only
     fragment instead of refusing it.
  2. _regenerate_pass2 discarded a truncated revision to "keep the previous
     attempt" without checking that the previous attempt was a page at all.
  3. The plan gate ranked on critique score only, so a blank document that
     scored 6.5 (the critique reads the markup, and the CSS mentions .hero /
     .menu) outranked nothing and was served.

No network calls — _extract_html and the gate helpers are pure.
"""

import pytest
from unittest.mock import patch

import app.services.ai_service as ai_service_module
from app.services.ai_service import AIService
from app.utils.html_balance import has_renderable_body


# ── the production artefact ──────────────────────────────────────────────────

# Shape of the real failure: <head> opens, <style> opens, CSS runs on, EOF.
PROD_TRUNCATED = (
    "<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n"
    "<meta charset=\"utf-8\">\n<title>Warung Nasi</title>\n"
    "<style>\n"
    + ".hero-meta .meta-item { opacity: 0.5; margin-left: 8px; }\n" * 200
    + "@media (max-width: 639px) {\n"
    "    .hero-meta .meta-item:not(:last-child)::after {\n"
    "        content: \"\";"
)

GOOD_HTML = (
    "<!DOCTYPE html>\n<html lang=\"en\">\n<head><style>.hero{color:red}</style></head>\n"
    "<body>\n<section class=\"hero\"><h1>Warung Nasi</h1><p>Open daily</p></section>\n"
    "</body>\n</html>"
)


# ── has_renderable_body ──────────────────────────────────────────────────────

def test_head_only_truncation_has_no_renderable_body():
    """The exact production artefact: CSS only, never reached <body>."""
    assert has_renderable_body(PROD_TRUNCATED) is False


def test_autoclosed_head_only_document_still_has_no_body():
    """After the truncation repair the document *parses* — and renders nothing.

    This is the shape that reached production: valid tags, empty page.
    """
    autoclosed = PROD_TRUNCATED + "\n</style></head>\n</body>\n</html>"
    assert has_renderable_body(autoclosed) is False


def test_real_page_has_renderable_body():
    assert has_renderable_body(GOOD_HTML) is True


def test_body_containing_only_css_is_not_renderable():
    """A <style> block is not content — a body holding only CSS is blank."""
    html = "<html><body>\n  <style>.a{color:red}</style>\n</body></html>"
    assert has_renderable_body(html) is False


def test_body_containing_only_script_is_not_renderable():
    html = "<html><body><script>var a = '<div>not markup</div>';</script></body></html>"
    assert has_renderable_body(html) is False


def test_body_with_only_an_image_is_renderable():
    """Elements that paint on their own count even with no text."""
    assert has_renderable_body('<html><body><img src="hero.jpg"></body></html>') is True


def test_body_with_only_a_comment_is_not_renderable():
    assert has_renderable_body("<html><body><!-- TODO --></body></html>") is False


@pytest.mark.parametrize("html", ["", None])
def test_empty_input_is_not_renderable(html):
    assert has_renderable_body(html) is False


# ── _extract_html refuses to return a blank page ─────────────────────────────

@pytest.fixture
def svc():
    return AIService()


def test_extract_html_refuses_head_only_truncation(svc):
    """The core fix: no blank page is manufactured out of a truncated head."""
    assert svc._extract_html(PROD_TRUNCATED) is None
    assert svc._last_extract_info["was_truncated"] is True
    assert svc._last_extract_info["bodyless"] is True


def test_extract_html_still_repairs_truncation_that_has_content(svc):
    """Regression guard: ordinary mid-body truncation must still be salvaged.

    The blank-page fix must not turn every truncation into a hard failure —
    a page cut off part-way through its last section is still a page.
    """
    truncated_mid_body = (
        "<!DOCTYPE html>\n<html><head><style>.a{color:red}</style></head>\n"
        "<body>\n<section class=\"hero\"><h1>Warung Nasi</h1></section>\n"
        "<section class=\"menu\"><div class=\"card\"><h3>Nasi Lemak</h3>"
    )
    out = svc._extract_html(truncated_mid_body)
    assert out is not None
    assert out.rstrip().endswith("</html>")
    assert svc._last_extract_info["was_truncated"] is True
    assert svc._last_extract_info["bodyless"] is False
    assert "Nasi Lemak" in out


def test_extract_html_passes_through_a_complete_page(svc):
    out = svc._extract_html(GOOD_HTML)
    assert out is not None
    assert "Warung Nasi" in out
    assert svc._last_extract_info["was_truncated"] is False
    assert svc._last_extract_info["bodyless"] is False


def test_extract_html_flags_untruncated_blank_page_without_failing(svc):
    """A complete-but-empty document is flagged, not refused.

    We have no evidence of a cause for this one, so it stays loud rather than
    fatal — only the truncated case has a proven blank-page failure mode.
    """
    blank = "<!DOCTYPE html>\n<html><head><style>.a{}</style></head><body></body></html>"
    out = svc._extract_html(blank)
    assert out is not None
    assert svc._last_extract_info["was_truncated"] is False
    assert svc._last_extract_info["bodyless"] is True


# ── _regenerate_pass2 no longer "keeps" a blank previous attempt ─────────────

@pytest.mark.asyncio
async def test_pass2_takes_truncated_revision_over_blank_previous(svc):
    """The log line that shipped the blank site:

        "Pass 2 regeneration unusable (empty/non-HTML/truncated) —
         keeping the previous attempt"

    …where the previous attempt had no body. A truncated revision that renders
    content is strictly better than a blank page.
    """
    revision = GOOD_HTML[:-20]  # truncated, but has real body content
    svc.deepseek_api_key = "test-key"

    async def _call(*a, **kw):
        svc._last_api_call = {"provider": "deepseek", "truncated": True}
        return revision

    with patch.object(svc, "_call_deepseek", new=_call):
        out = await svc._regenerate_pass2(
            "prompt", ["fix the hero"],
            previous_html=PROD_TRUNCATED,
            has_images=False, designer_mode=False, provider="deepseek",
        )
    assert out == revision


@pytest.mark.asyncio
async def test_pass2_still_discards_truncated_revision_when_previous_is_a_page(svc):
    """Unchanged behaviour when the previous attempt actually renders."""
    svc.deepseek_api_key = "test-key"

    async def _call(*a, **kw):
        svc._last_api_call = {"provider": "deepseek", "truncated": True}
        return "<html><body><h1>Half a p"

    with patch.object(svc, "_call_deepseek", new=_call):
        out = await svc._regenerate_pass2(
            "prompt", ["fix the hero"],
            previous_html=GOOD_HTML,
            has_images=False, designer_mode=False, provider="deepseek",
        )
    assert out is None


# ── the plan gate never serves a blank attempt ───────────────────────────────

@pytest.mark.asyncio
async def test_plan_gate_prefers_a_rendering_attempt_over_a_higher_scored_blank(svc):
    """A blank attempt that critiques at 6.5 must lose to a page that critiques
    lower — the ranking bug that chose the blank document in production."""
    attempt_htmls = iter([GOOD_HTML])

    async def _fake_regen(*a, **kw):
        return next(attempt_htmls, None)

    # Lint clean, no critique model → gate falls back to lint + the body check.
    with patch.object(ai_service_module, "design_critique_enabled", return_value=False), \
         patch.object(svc, "_regenerate_pass2", new=_fake_regen):
        served = await svc._run_plan_gate(
            PROD_TRUNCATED, plan=None, prompt="p",
            has_images=False, designer_mode=False, language="en", provider="deepseek",
        )

    # The blank first attempt must not be what comes back.
    assert has_renderable_body(served) is True
    assert "Warung Nasi" in served
