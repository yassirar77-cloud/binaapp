"""
Tests for the widget catalogue + theme-token extractor + slot-aware
injection helpers. These are pure-function helpers (no I/O, no DB) so the
tests run in isolation without any mocks.
"""

import pytest

from app.services.widget_catalogue import (
    SLOT_PREFIX,
    WIDGETS,
    build_prompt_context_block,
    get_widget,
    widgets_for_request,
)


class TestWidgetCatalogue:
    """The catalogue is the single source of truth — sanity-check it."""

    def test_every_widget_has_a_slot_id_with_canonical_prefix(self):
        for widget_id, widget in WIDGETS.items():
            assert widget.slot_id.startswith(SLOT_PREFIX), (
                f"{widget_id} slot_id={widget.slot_id} missing canonical prefix"
            )
            assert widget.slot_id.endswith("-slot"), (
                f"{widget_id} slot_id={widget.slot_id} missing '-slot' suffix"
            )

    def test_required_widgets_exist(self):
        # These are the widgets the spec calls out by name. Renaming or
        # removing one is a coordination point with the prompt builder
        # and the injection layer — the test forces a conscious decision.
        for required in ("whatsapp", "chat", "delivery", "pesanan", "maps", "contact"):
            assert required in WIDGETS, f"Missing widget '{required}' in catalogue"

    def test_get_widget_returns_none_for_unknown(self):
        assert get_widget("does-not-exist") is None

    def test_each_widget_has_primary_colour(self):
        # The prompt context block references default colours; missing
        # entries would silently drop information from the prompt.
        for widget in WIDGETS.values():
            assert "primary" in widget.default_colors, (
                f"{widget.id} missing default primary colour"
            )

    def test_widget_specs_are_frozen(self):
        # Frozen so callers can't accidentally mutate the global catalogue
        # mid-request (e.g. via .default_colors['primary'] = ...).
        whatsapp = WIDGETS["whatsapp"]
        with pytest.raises(Exception):  # FrozenInstanceError or similar
            whatsapp.default_position = "anywhere"  # type: ignore[misc]


class TestWidgetsForRequest:
    """Right list, right order — the prompt block leans on this order."""

    def test_no_features_means_no_widgets(self):
        widgets = widgets_for_request(
            include_whatsapp=False,
            include_maps=False,
            include_ecommerce=False,
            include_contact=False,
            include_chat=False,
        )
        assert widgets == []

    def test_ecommerce_pulls_in_delivery_and_pesanan(self):
        widgets = widgets_for_request(
            include_whatsapp=False,
            include_maps=False,
            include_ecommerce=True,
            include_contact=False,
            include_chat=False,
        )
        ids = [w.id for w in widgets]
        assert "delivery" in ids
        assert "pesanan" in ids

    def test_delivery_listed_before_whatsapp(self):
        # Delivery is the most layout-disruptive; it must be at the top
        # of the prompt block so the AI sees it first.
        widgets = widgets_for_request(
            include_whatsapp=True,
            include_maps=False,
            include_ecommerce=True,
            include_contact=False,
            include_chat=True,
        )
        ids = [w.id for w in widgets]
        assert ids.index("delivery") < ids.index("whatsapp")
        assert ids.index("delivery") < ids.index("chat")


class TestPromptContextBlock:
    def test_empty_list_returns_empty_string(self):
        # Don't pollute the prompt when nothing will be injected.
        assert build_prompt_context_block([]) == ""

    def test_block_mentions_every_widget_by_slot_id(self):
        widgets = widgets_for_request(
            include_whatsapp=True,
            include_maps=True,
            include_ecommerce=True,
        )
        block = build_prompt_context_block(widgets)
        for w in widgets:
            assert w.slot_id in block, (
                f"Prompt block missing slot_id for {w.id}"
            )

    def test_block_includes_primary_colour_hint_when_provided(self):
        block = build_prompt_context_block(
            [WIDGETS["whatsapp"]],
            primary_color="#abc123",
        )
        assert "#abc123" in block
        assert "PRIMARY COLOUR" in block

    def test_block_omits_primary_colour_hint_when_none(self):
        block = build_prompt_context_block([WIDGETS["whatsapp"]])
        assert "PRIMARY COLOUR" not in block

    def test_block_forbids_duplicate_floating_buttons(self):
        # The whole point is to stop the AI bolting its own WhatsApp/chat
        # button on top of the injected one. Make sure that rule is in
        # the prompt verbatim.
        block = build_prompt_context_block([WIDGETS["whatsapp"], WIDGETS["chat"]])
        assert "Do NOT add your own floating" in block


class TestThemeTokenExtraction:
    """Pulls primary/accent/surface colours out of generated HTML."""

    def setup_method(self):
        # Local import keeps `app` import failures isolated from
        # catalogue tests above.
        from app.services.ai_service import extract_theme_tokens

        self.extract = extract_theme_tokens

    def test_returns_empty_for_empty_input(self):
        assert self.extract("") == {}
        assert self.extract(None) == {}  # type: ignore[arg-type]

    def test_extracts_css_variable_primary(self):
        html = "<style>:root { --primary-color: #ff5733; }</style>"
        assert self.extract(html).get("primary") == "#ff5733"

    def test_extracts_tailwind_primary(self):
        html = 'tailwind.config = { theme: { extend: { colors: { primary: "#abcdef" } } } }'
        assert self.extract(html).get("primary") == "#abcdef"

    def test_extracts_all_three_tokens(self):
        html = """
        <style>
        :root {
          --primary-color: #111111;
          --accent-color: #222222;
          --bg-color: #333333;
        }
        </style>
        """
        result = self.extract(html)
        assert result == {
            "primary": "#111111",
            "accent": "#222222",
            "surface": "#333333",
        }

    def test_first_match_wins(self):
        # When both --primary-color and `primary: "..."` are present,
        # the CSS-variable form (defined by our own prompt preamble)
        # should win since it's the authoritative source.
        html = (
            '<style>:root { --primary-color: #111; }</style>'
            'colors: { primary: "#222" }'
        )
        assert self.extract(html).get("primary") == "#111"


class TestSlotInjection:
    """Slot-aware injection: AI emits a placeholder div, we fill it."""

    def setup_method(self):
        from app.services.templates import _find_widget_slot, _inject_into_slot

        self.find = _find_widget_slot
        self.inject = _inject_into_slot

    def test_find_slot_returns_none_when_absent(self):
        assert self.find("<html></html>", WIDGETS["pesanan"]) is None

    def test_find_slot_matches_canonical_id(self):
        html = '<div id="binaapp-pesanan-slot"></div>'
        assert self.find(html, WIDGETS["pesanan"]) == "binaapp-pesanan-slot"

    def test_find_slot_matches_alias(self):
        # The catalogue lists "binaapp-pesanan" as an alias for the
        # delivery slot, since the AI sometimes emits a near-miss id.
        html = '<div id="binaapp-pesanan"></div>'
        assert self.find(html, WIDGETS["delivery"]) == "binaapp-pesanan"

    def test_inject_replaces_inner_contents_only(self):
        html = '<body><div id="binaapp-maps-slot">old</div></body>'
        result = self.inject(html, "binaapp-maps-slot", "<iframe></iframe>")
        assert "<iframe></iframe>" in result
        assert "old" not in result
        # Outer wrapper preserved
        assert 'id="binaapp-maps-slot"' in result

    def test_inject_is_a_no_op_when_slot_missing(self):
        html = "<body><p>no slot here</p></body>"
        result = self.inject(html, "binaapp-maps-slot", "<iframe></iframe>")
        assert result == html

    def test_inject_handles_single_quote_id(self):
        html = "<div id='binaapp-contact-slot'>x</div>"
        result = self.inject(html, "binaapp-contact-slot", "<form></form>")
        assert "<form></form>" in result
