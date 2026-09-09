"""Cross-layer round-trip tests for merchant items and their prices.

WHY THIS FILE EXISTS
--------------------
A merchant entered six salon services with prices (RM380, RM450, RM320, RM65,
RM120, RM150) and switched "Senarai Harga" ON. Every one rendered on the
published page as "Atas permintaan" — price on request. That string appears
nowhere in this codebase: the language model invented it because it was given
service names and no prices.

The prices were never lost at render, and never lost in the browser. They were
sent in the POST body and read by nobody:

  * /api/generate/start read `uploaded_images`, a key the frontend never sends,
    so the item context it built was always empty;
  * no prompt template on the live path contained a price field at all;
  * `menu_items` — documented on WebsiteGenerationRequest as the SOURCE OF
    TRUTH whose names and prices "are rendered verbatim" and which the
    generator "may not rename, merge, round, or invent" — was never sent at
    generation and never read by the endpoint;
  * the only price-consuming code path in the product was the food-delivery
    ordering widget, gated on a feature this merchant had switched off.

A unit test asserting the price formatter works would have passed all year.
So these tests follow the six prices across every boundary they must survive,
ending at the actual prompt text handed to the model.
"""

from unittest.mock import patch, MagicMock, AsyncMock


SALON_DESC = (
    "Nadira Hair Studio ialah salon rambut & spa kepala untuk wanita di Shah Alam. "
    "Kami khusus dalam colouring dan hair treatment - balayage, korean perm dan "
    "keratin smoothing. Booking melalui WhatsApp sahaja."
)

# The merchant's actual six services, verbatim.
SIX_ITEMS = [
    {"name": "Balayage", "price": "RM380"},
    {"name": "Korean Perm", "price": "RM450"},
    {"name": "Keratin Smoothing", "price": "RM320"},
    {"name": "Gunting Rambut", "price": "RM65"},
    {"name": "Scalp Spa", "price": "RM120"},
    {"name": "Hair Treatment", "price": "RM150"},
]
ALL_PRICES = ["RM380", "RM450", "RM320", "RM65", "RM120", "RM150"]


def _quota_client():
    resp = MagicMock()
    resp.status_code = 200
    resp.headers = {"content-range": "0-0/0"}
    resp.json.return_value = [{
        "plan_id": "plan-pro",
        "subscription_plans": {"websites_limit": 10, "plan_name": "Pro"},
    }]
    client = MagicMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)
    client.get = AsyncMock(return_value=resp)
    return client


def _post(client, body):
    captured = {}

    def _fake_task(*args, **kwargs):
        captured.update(kwargs)

        async def _noop():
            return None

        return _noop()

    with (
        patch("app.main.supabase", None),
        patch("app.main.run_generation_task", _fake_task),
        patch("app.main.httpx.AsyncClient", return_value=_quota_client()),
        patch("app.main.sub_service.check_limit", new=AsyncMock(return_value={"allowed": True})),
    ):
        resp = client.post("/api/generate/start", json=body)
    return resp, captured


# ---------------------------------------------------------------------------
# Boundary 1: POST body -> the generation task
# ---------------------------------------------------------------------------

class TestSixPricedItemsReachTheTask:

    def test_all_six_names_and_prices_survive_the_endpoint(self, client):
        resp, captured = _post(client, {
            "description": SALON_DESC,
            "business_type": "salon",
            "menu_items": SIX_ITEMS,
            "features": {"priceList": True, "whatsapp": True},
            "user_id": "u-1",
        })
        assert resp.status_code == 200, resp.text
        got = captured.get("menu_items")
        assert got is not None, "menu_items never reached the task"
        assert len(got) == 6, f"expected 6 items, got {len(got)}"
        assert [i["name"] for i in got] == [i["name"] for i in SIX_ITEMS]
        assert [i["price"] for i in got] == ALL_PRICES

    def test_prices_are_not_reformatted_or_rounded(self, client):
        """Prices are strings on purpose: RM18/pax and RM5 - RM8 are real
        Malaysian pricing forms a float cannot represent."""
        odd = [
            {"name": "Set Kenduri", "price": "RM18/pax"},
            {"name": "Potong Kanak-kanak", "price": "RM25 - RM35"},
            {"name": "Konsultasi", "price": "Percuma"},
        ]
        resp, captured = _post(client, {
            "description": SALON_DESC, "menu_items": odd,
            "features": {"priceList": True}, "user_id": "u-1",
        })
        assert resp.status_code == 200, resp.text
        assert [i["price"] for i in captured["menu_items"]] == [
            "RM18/pax", "RM25 - RM35", "Percuma",
        ]

    def test_price_list_toggle_is_read(self, client):
        for flag in (True, False):
            resp, captured = _post(client, {
                "description": SALON_DESC, "menu_items": SIX_ITEMS,
                "features": {"priceList": flag}, "user_id": "u-1",
            })
            assert resp.status_code == 200, resp.text
            assert captured.get("show_prices") is flag

    def test_price_list_defaults_to_on_when_absent(self, client):
        resp, captured = _post(client, {
            "description": SALON_DESC, "menu_items": SIX_ITEMS, "user_id": "u-1",
        })
        assert captured.get("show_prices") is True

    def test_items_without_a_photo_still_count_as_items(self, client):
        """The reported case: six services typed in, no photos uploaded."""
        resp, captured = _post(client, {
            "description": SALON_DESC,
            "menu_items": [{**i, "url": ""} for i in SIX_ITEMS],
            "user_id": "u-1",
        })
        assert len(captured["menu_items"]) == 6

    def test_legacy_client_gallery_rows_are_still_honoured(self, client):
        """Frontend and backend deploy independently. A client that has not
        shipped menu_items yet still sends the same {name, price} rows as
        gallery_metadata — the prices must not vanish in that window."""
        resp, captured = _post(client, {
            "description": SALON_DESC,
            "gallery_metadata": [{"url": "", **i} for i in SIX_ITEMS],
            "user_id": "u-1",
        })
        assert resp.status_code == 200, resp.text
        assert [i["price"] for i in captured["menu_items"]] == ALL_PRICES

    def test_ui_noise_is_rejected_not_rendered_as_an_item(self, client):
        """Names like "WhatsApp" and "Hubungi Kami" are page furniture that
        earlier extraction turned into menu items."""
        resp, captured = _post(client, {
            "description": SALON_DESC,
            "menu_items": [
                {"name": "Balayage", "price": "RM380"},
                {"name": "WhatsApp", "price": ""},
                {"name": "Hubungi Kami", "price": ""},
                {"name": "", "price": "RM99"},
            ],
            "user_id": "u-1",
        })
        assert [i["name"] for i in captured["menu_items"]] == ["Balayage"]

    def test_typed_items_do_not_hijack_the_image_choice(self, client):
        """Item rows carry no photo. They must not be counted as uploads —
        doing so flipped image_choice to 'upload' with nothing to upload,
        which normalised to 'none' and left the site with no images."""
        resp, captured = _post(client, {
            "description": SALON_DESC,
            "image_choice": "ai",
            "images": [{"url": "", "name": "Balayage", "price": "RM380"}],
            "user_id": "u-1",
        })
        assert resp.status_code == 200, resp.text
        assert captured.get("image_choice") == "ai"


# ---------------------------------------------------------------------------
# Boundary 2: the request -> the actual prompt text
# ---------------------------------------------------------------------------

class TestPricesReachThePromptVerbatim:
    """The end of the chain. Everything above is worthless if the six prices
    do not appear in the text the model is handed."""

    def _prompt(self, items, show_prices=True):
        from app.services.ai_service import AIService

        service = AIService.__new__(AIService)
        return service._build_strict_prompt(
            name="Nadira Hair Studio",
            desc=SALON_DESC,
            style="elegant",
            language="ms",
            menu_items=items,
            show_prices=show_prices,
        )

    def test_every_price_appears_in_the_prompt(self):
        prompt = self._prompt(SIX_ITEMS)
        for price in ALL_PRICES:
            assert f'"{price}"' in prompt, f"{price} missing from the prompt"
        for item in SIX_ITEMS:
            assert f'"{item["name"]}"' in prompt

    def test_the_source_of_truth_contract_is_stated(self):
        prompt = self._prompt(SIX_ITEMS)
        assert "SOURCE OF TRUTH" in prompt
        assert "Never round, reformat, convert, or invent a price" in prompt
        assert "Do NOT add any item that is not in this list" in prompt

    def test_prices_off_suppresses_them_without_inventing_a_substitute(self):
        prompt = self._prompt(SIX_ITEMS, show_prices=False)
        # Names still render; prices do not.
        assert '"Balayage"' in prompt
        for price in ALL_PRICES:
            assert f'"{price}"' not in prompt
        assert "DO NOT render a price for any item" in prompt
        # And specifically must not swap in the invented string.
        assert "atas permintaan" in prompt.lower(), (
            "the prompt should name 'atas permintaan' as a FORBIDDEN substitute"
        )

    def test_no_items_asks_for_an_honest_placeholder_not_invented_ones(self):
        prompt = self._prompt([])
        assert "DO NOT invent prices" in prompt
        assert "RENDER A PLACEHOLDER" in prompt
