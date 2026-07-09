"""
Tests for the theme-aware delivery widget injection.

Covers:
- Theme token extraction (primary/secondary from CSS vars and Tailwind config)
- resolve_widget_theme: extracted palette vs neutral dark fallback
- Category tabs derived from the merchant's actual menu items — never the
  static business-type template categories (Baju/Tudung/Aksesori etc.)
- inject_ordering_system: theme CSS variables applied to widget fragments,
  merchant page content left byte-identical
- Chat entry-point dedupe: inline chat button and chat-widget.js never
  co-exist on one page
"""

import pytest

from app.services.ai_service import extract_theme_tokens
from app.services.templates import (
    TemplateService,
    resolve_widget_theme,
    WIDGET_FALLBACK_PRIMARY,
    WIDGET_FALLBACK_PRIMARY_DARK,
    WIDGET_FALLBACK_SECONDARY,
)
from app.services.business_types import generate_category_buttons_from_menu


WEBSITE_ID = "11111111-1111-1111-1111-111111111111"

TAILWIND_SITE = (
    '<!DOCTYPE html><html><head><script>tailwind.config={theme:{extend:{colors:'
    '{primary:"#0ea5e9",secondary:"#f59e0b"}}}}</script></head>'
    '<body><h1 style="color:#f97316">Kedai Kek Mawar</h1></body></html>'
)
CSSVAR_SITE = (
    '<!DOCTYPE html><html><head><style>:root{--primary-color:#7c3aed;'
    '--secondary-color:#22d3ee;}</style></head><body><p>hi</p></body></html>'
)
PLAIN_SITE = "<html><head></head><body><p>hi</p></body></html>"

MENU = [
    {"name": "Kek Coklat", "price": 45, "category": "Kek"},
    {"name": "Croissant", "price": 6, "category": "Pastri"},
    {"name": "Brownies", "price": 12, "category": "Kek"},
]


@pytest.fixture
def svc():
    return TemplateService()


# ── theme extraction ─────────────────────────────────────────────────────────

class TestThemeExtraction:

    def test_tailwind_config_colors(self):
        tokens = extract_theme_tokens(TAILWIND_SITE)
        assert tokens["primary"] == "#0ea5e9"
        assert tokens["secondary"] == "#f59e0b"

    def test_css_variables(self):
        tokens = extract_theme_tokens(CSSVAR_SITE)
        assert tokens["primary"] == "#7c3aed"
        assert tokens["secondary"] == "#22d3ee"

    def test_nothing_extractable(self):
        assert extract_theme_tokens(PLAIN_SITE) == {}
        assert extract_theme_tokens("") == {}


class TestResolveWidgetTheme:

    def test_extracted_palette_used(self):
        theme = resolve_widget_theme({"primary": "#0ea5e9", "secondary": "#f59e0b"})
        assert theme["primary"] == "#0ea5e9"
        assert theme["secondary"] == "#f59e0b"
        # derived tints computed from primary
        assert theme["primary_soft"].startswith("#0ea5e9")
        assert theme["primary_ring"].startswith("#0ea5e9")

    def test_neutral_dark_fallback(self):
        for tokens in ({}, None, {"primary": "not-a-color"}):
            theme = resolve_widget_theme(tokens)
            assert theme["primary"] == WIDGET_FALLBACK_PRIMARY
            assert theme["primary_dark"] == WIDGET_FALLBACK_PRIMARY_DARK
            assert theme["secondary"] == WIDGET_FALLBACK_SECONDARY

    def test_secondary_derived_when_missing(self):
        theme = resolve_widget_theme({"primary": "#0ea5e9"})
        assert theme["secondary"] != WIDGET_FALLBACK_SECONDARY
        assert theme["secondary"].startswith("#")


# ── menu-derived categories ──────────────────────────────────────────────────

class TestMenuDerivedCategories:

    def test_categories_from_items(self):
        html = generate_category_buttons_from_menu(
            [{"category": "kek"}, {"category": "pastri"}, {"category": "kek"}],
            "bakery",
        )
        assert "filterDeliveryCategory('kek')" in html
        assert "filterDeliveryCategory('pastri')" in html
        # template categories never leak in
        assert "baju" not in html.lower()
        assert "tudung" not in html.lower()

    def test_single_category_collapses_to_all(self):
        html = generate_category_buttons_from_menu(
            [{"category": "kek"}, {"category": "kek"}], "bakery"
        )
        assert "filterDeliveryCategory('all')" in html
        assert "filterDeliveryCategory('kek')" not in html

    def test_no_items_only_all(self):
        html = generate_category_buttons_from_menu([], "clothing")
        assert "filterDeliveryCategory('all')" in html
        assert "Baju" not in html and "Tudung" not in html and "Aksesori" not in html

    def test_known_category_ids_get_config_labels(self):
        html = generate_category_buttons_from_menu(
            [{"category": "nasi"}, {"category": "minuman"}], "food"
        )
        # food config supplies the display labels for these ids
        assert "filterDeliveryCategory('nasi')" in html
        assert "filterDeliveryCategory('minuman')" in html


# ── ordering system injection ────────────────────────────────────────────────

class TestOrderingSystemInjection:

    def _inject(self, svc, site, menu=MENU, business_type="bakery"):
        return svc.inject_ordering_system(
            site, menu, [],
            {"name": "Kedai Kek Mawar", "phone": "0123456789"},
            business_type=business_type,
            website_id=WEBSITE_ID,
        )

    def test_menu_categories_and_no_template_categories(self, svc):
        out = self._inject(svc, TAILWIND_SITE)
        assert "filterDeliveryCategory('kek')" in out
        assert "filterDeliveryCategory('pastri')" in out
        assert "baju" not in out.lower() and "tudung" not in out.lower()

    def test_theme_vars_from_site_palette(self, svc):
        out = self._inject(svc, TAILWIND_SITE)
        assert "--binaapp-primary: #0ea5e9" in out
        assert "--binaapp-secondary: #f59e0b" in out

    def test_neutral_dark_fallback_theme(self, svc):
        out = self._inject(svc, PLAIN_SITE)
        assert f"--binaapp-primary: {WIDGET_FALLBACK_PRIMARY}" in out

    def test_widget_fragments_carry_no_template_orange(self, svc):
        out = self._inject(svc, TAILWIND_SITE)
        # merchant content is preserved byte-identical...
        assert '<h1 style="color:#f97316">Kedai Kek Mawar</h1>' in out
        # ...and is the ONLY place template orange remains
        rest = out.replace('<h1 style="color:#f97316">Kedai Kek Mawar</h1>', "")
        for literal in ("#ea580c", "#f97316", "rgba(234,88,12"):
            assert literal not in rest, f"unthemed literal remains: {literal}"

    def test_item_category_prefers_merchant_value(self, svc):
        # 'Nasi Lemak' would keyword-detect as 'nasi'; the merchant's own
        # category value must win
        out = self._inject(
            svc, PLAIN_SITE,
            menu=[{"name": "Nasi Lemak", "price": 8, "category": "Signature"},
                  {"name": "Teh Tarik", "price": 3, "category": "Minuman"}],
            business_type="food",
        )
        assert '"category": "signature"' in out


# ── chat entry-point dedupe ──────────────────────────────────────────────────

class TestChatDedupe:

    def test_inline_chat_blocks_chat_widget_injection(self, svc):
        out = svc.inject_ordering_system(
            PLAIN_SITE, MENU, [], {"name": "K", "phone": "0123456789"},
            business_type="bakery", website_id=WEBSITE_ID,
        )
        assert "binaapp-inline-chat-btn" in out
        out2 = svc.inject_chat_widget(out, WEBSITE_ID)
        assert "widgets/chat-widget.js" not in out2

    def test_chat_widget_script_blocks_inline_chat_button(self, svc):
        site = (
            "<html><head></head><body><p>hi</p>"
            f'<script src="https://x/static/widgets/chat-widget.js" data-website-id="{WEBSITE_ID}"></script>'
            "</body></html>"
        )
        out = svc.inject_ordering_system(
            site, MENU, [], {"name": "K", "phone": "0123456789"},
            business_type="bakery", website_id=WEBSITE_ID,
        )
        assert "binaapp-inline-chat-btn" not in out

    def test_chat_widget_injected_when_no_entry_point(self, svc):
        out = svc.inject_chat_widget(PLAIN_SITE, WEBSITE_ID)
        assert "widgets/chat-widget.js" in out
        # and never twice
        out2 = svc.inject_chat_widget(out, WEBSITE_ID)
        assert out2.count("widgets/chat-widget.js") == 1
