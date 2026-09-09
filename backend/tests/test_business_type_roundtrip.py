"""Cross-layer round-trip tests for business_type and hero_image_prompt.

WHY THIS FILE EXISTS
--------------------
The salon-with-a-drinks-hero bug was NOT a classifier bug. The create page
sent business_type="salon" correctly, and the classifier, given the chance,
would have answered "salon" too. The value was dropped in the plumbing
BETWEEN the endpoint and the generator: /api/generate/start never read the
key, and run_generation_task hardcoded business_type="business" into the AI
request. The result — business_type = '' on all 205 rows ever written — was
invisible to the entire test suite, because every existing test asserted on
one layer at a time.

A unit test of detect_business_type() would have passed all year while every
merchant's vertical was silently discarded. So these tests cross the layer
boundaries the value has to survive:

    POST body -> endpoint -> run_generation_task -> WebsiteGenerationRequest
    POST body -> /api/publish -> the websites upsert payload

The rule: if a value crosses a layer boundary, the test crosses it too.
"""

from unittest.mock import patch, MagicMock, AsyncMock

import pytest

SALON_DESC = (
    "Nadira Hair Studio ialah salon rambut & spa kepala untuk wanita di Shah Alam. "
    "Kami khusus dalam colouring dan hair treatment - balayage, korean perm dan "
    "keratin smoothing. Vibe salon tenang dan gelap; pelanggan suka duduk lama, "
    "minum kopi, dan tak rasa rushed. Booking melalui WhatsApp sahaja."
)
HERO_PROMPT = (
    "dark luxury hair salon interior, warm gold lighting, empty styling chair, cinematic"
)
VALID_HTML = (
    "<!DOCTYPE html><html><head><title>T</title></head><body><h1>Hi</h1></body></html>"
)


def _empty_select_mock():
    mock = MagicMock()
    for method in ("select", "insert", "update", "upsert", "delete",
                   "eq", "neq", "limit", "single", "order"):
        getattr(mock, method).return_value = mock
    response = MagicMock()
    response.data = []
    mock.execute.return_value = response
    return mock


# ---------------------------------------------------------------------------
# Boundary 1: POST /api/generate/start  ->  run_generation_task
# ---------------------------------------------------------------------------

class TestEndpointHandsTheVerticalToTheTask:

    def _post(self, client, body):
        captured = {}

        def _fake_task(*args, **kwargs):
            # Deliberately a SYNC function returning a coroutine: the
            # endpoint does asyncio.create_task(run_generation_task(...)),
            # so the arguments are bound when the call is made but an async
            # body would not run before the response is returned. Capturing
            # at call time is what makes the assertion deterministic.
            captured.update(kwargs)
            captured["_positional"] = args

            async def _noop():
                return None

            return _noop()

        # The endpoint counts the user's existing websites over HTTP before
        # it starts a job. Answer it with "0 websites" so the quota gate
        # passes without leaving the process.
        quota_resp = MagicMock()
        quota_resp.status_code = 200
        quota_resp.headers = {"content-range": "0-0/0"}
        # The same client answers the subscription lookup that follows the
        # count, so give it an active plan with room to spare.
        quota_resp.json.return_value = [{
            "plan_id": "plan-pro",
            "subscription_plans": {"websites_limit": 10, "plan_name": "Pro"},
        }]
        fake_http = MagicMock()
        fake_http.__aenter__ = AsyncMock(return_value=fake_http)
        fake_http.__aexit__ = AsyncMock(return_value=False)
        fake_http.get = AsyncMock(return_value=quota_resp)

        with (
            patch("app.main.supabase", None),        # skip the job-row insert
            patch("app.main.run_generation_task", _fake_task),
            patch("app.main.httpx.AsyncClient", return_value=fake_http),
            patch("app.main.sub_service.check_limit",
                  new=AsyncMock(return_value={"allowed": True})),
        ):
            resp = client.post("/api/generate/start", json=body)
        return resp, captured

    def test_explicit_business_type_and_hero_prompt_reach_the_task(self, client):
        resp, captured = self._post(client, {
            "description": SALON_DESC,
            "business_type": "salon",
            "hero_image_prompt": HERO_PROMPT,
            "user_id": "u-1",
        })
        assert resp.status_code == 200, resp.text
        # The exact assertion the original bug needed: the merchant's pick
        # survives the endpoint instead of being dropped on the floor.
        assert captured.get("business_type") == "salon"
        assert captured.get("hero_image_prompt") == HERO_PROMPT

    def test_picker_auto_means_no_explicit_pick(self, client):
        resp, captured = self._post(client, {
            "description": SALON_DESC,
            "business_type": "auto",
            "user_id": "u-1",
        })
        assert resp.status_code == 200, resp.text
        assert captured.get("business_type") is None
        assert captured.get("hero_image_prompt") is None

    def test_unknown_picker_value_degrades_to_no_pick(self, client):
        resp, captured = self._post(client, {
            "description": SALON_DESC,
            "business_type": "not-a-real-vertical",
            "user_id": "u-1",
        })
        assert resp.status_code == 200, resp.text
        assert captured.get("business_type") is None


# ---------------------------------------------------------------------------
# Boundary 2: run_generation_task  ->  WebsiteGenerationRequest
# ---------------------------------------------------------------------------

class TestTaskBuildsTheRequestWithTheRealVertical:
    """This is the boundary the bug actually lived on: the request was
    built with a hardcoded business_type="business" — not even a real
    vertical — so every downstream consumer ignored it and guessed."""

    async def _run(self, **task_kwargs):
        import app.main as main

        captured = {}

        async def _fake_generate(request, **kwargs):
            captured["request"] = request
            raise RuntimeError("stop-after-capture")

        with (
            patch("app.main.supabase", None),
            patch.object(main.ai_service, "generate_website", _fake_generate),
        ):
            await main.run_generation_task(
                "job-1", SALON_DESC, "e@x.com", "u-1", **task_kwargs
            )
        return captured.get("request")

    @pytest.mark.asyncio
    async def test_explicit_salon_lands_on_the_request(self):
        request = await self._run(business_type="salon", hero_image_prompt=HERO_PROMPT)
        assert request is not None, "generate_website was never reached"
        # The regression: this used to be the literal string "business".
        assert request.business_type == "salon"
        assert request.business_type != "business"
        assert request.hero_image_prompt == HERO_PROMPT

    @pytest.mark.asyncio
    async def test_no_explicit_pick_leaves_the_field_empty_for_the_classifier(self):
        request = await self._run()
        assert request is not None
        assert not request.business_type
        assert request.hero_image_prompt is None

    @pytest.mark.asyncio
    async def test_the_request_vertical_drives_the_image_category(self):
        """End of the chain: the value that survived must be the value the
        image prompts are actually chosen by."""
        from app.services.ai_service import AIService

        service = AIService.__new__(AIService)
        request = await self._run(business_type="salon")
        category = service._autofill_prompt_category(
            request.description, request.business_type
        )
        assert category == "services"

    @pytest.mark.asyncio
    async def test_classifier_fallback_is_logged_as_classified_not_explicit(self):
        """The negative case: with no explicit pick the scorer decides, the
        resolved value is still used, and the log says where it came from —
        so whoever reads the log can tell a real pick from a guess. This is
        the diagnostic that was missing when the bug was reported: the logs
        could not distinguish the two."""
        from loguru import logger as _logger
        from app.services.ai_service import AIService

        service = AIService.__new__(AIService)
        request = await self._run()

        lines = []
        sink_id = _logger.add(lines.append, level="INFO", format="{message}")
        try:
            category = service._autofill_prompt_category(
                request.description, request.business_type
            )
        finally:
            _logger.remove(sink_id)

        assert category == "services"          # scorer still gets it right
        text = "".join(lines)
        assert "business_type=salon" in text
        assert "source=classified-from-description" in text
        assert "source=explicit]" not in text

    @pytest.mark.asyncio
    async def test_explicit_pick_is_logged_as_explicit(self):
        from loguru import logger as _logger
        from app.services.ai_service import AIService

        service = AIService.__new__(AIService)
        request = await self._run(business_type="salon")

        lines = []
        sink_id = _logger.add(lines.append, level="INFO", format="{message}")
        try:
            service._autofill_prompt_category(
                request.description, request.business_type
            )
        finally:
            _logger.remove(sink_id)
        assert "source=explicit]" in "".join(lines)


# ---------------------------------------------------------------------------
# Boundary 3: POST /api/publish  ->  the websites row
# ---------------------------------------------------------------------------

class TestPublishPersistsTheVertical:

    def _captured_upsert(self, supabase_mock):
        for call in supabase_mock.table.return_value.upsert.call_args_list:
            args, _ = call
            if args and isinstance(args[0], dict):
                return args[0]
        return None

    def _publish(self, client, auth_headers, body_extra):
        supabase_mock = MagicMock()
        supabase_mock.table.return_value = _empty_select_mock()

        storage_response = MagicMock()
        storage_response.status_code = 201
        storage_response.text = ""
        fake_async_client = MagicMock()
        fake_async_client.__aenter__ = AsyncMock(return_value=fake_async_client)
        fake_async_client.__aexit__ = AsyncMock(return_value=False)
        fake_async_client.post = AsyncMock(return_value=storage_response)

        with (
            patch("app.main.supabase", supabase_mock),
            patch("app.main.sub_service.check_limit",
                  new=AsyncMock(return_value={"allowed": True})),
            patch("app.main.sub_service.increment_usage", new=AsyncMock(return_value=True)),
            patch("app.services.plan_features.can_publish_subdomain",
                  new=AsyncMock(return_value=True)),
            patch("app.main.supabase_service.is_email_verified",
                  new=AsyncMock(return_value=True)),
            patch("app.main.httpx.AsyncClient", return_value=fake_async_client),
        ):
            resp = client.post("/api/publish", headers=auth_headers, json={
                "html_content": VALID_HTML,
                "subdomain": "nadirasalon",
                "project_name": "Nadira",
                "website_id": "ws-salon-1",
                "description": SALON_DESC,
                **body_extra,
            })
        return resp, self._captured_upsert(supabase_mock)

    def test_row_records_the_vertical_and_the_hero_prompt(self, client, auth_headers):
        resp, payload = self._publish(client, auth_headers, {
            "business_type": "salon",
            "hero_image_prompt": HERO_PROMPT,
        })
        assert resp.status_code == 200, resp.text
        assert payload is not None, "websites upsert was never called"
        # websites.business_type was '' on all 205 historical rows because
        # nothing ever wrote it. This is the assertion that pins it.
        assert payload.get("business_type") == "salon"
        assert payload.get("hero_image_prompt") == HERO_PROMPT

    def test_picker_value_is_canonicalised_before_it_hits_the_row(self, client, auth_headers):
        resp, payload = self._publish(client, auth_headers, {"business_type": "Lain-Lain"})
        assert resp.status_code == 200, resp.text
        assert payload.get("business_type") == "general"

    def test_missing_column_does_not_cost_the_merchant_their_website(
        self, client, auth_headers
    ):
        """Production is the only environment, so code and migration 055 can
        land in either order. If the columns aren't there yet the row must
        still be saved without them — a missing optional column must never
        turn a wrong-hero bug into an outage."""
        supabase_mock = MagicMock()
        table_mock = _empty_select_mock()
        supabase_mock.table.return_value = table_mock

        calls = []

        def _upsert(payload, **kwargs):
            calls.append(dict(payload))
            if "hero_image_prompt" in payload:
                raise Exception(
                    "column \"hero_image_prompt\" of relation \"websites\" does not exist"
                )
            return table_mock

        table_mock.upsert.side_effect = _upsert

        storage_response = MagicMock()
        storage_response.status_code = 201
        storage_response.text = ""
        fake_async_client = MagicMock()
        fake_async_client.__aenter__ = AsyncMock(return_value=fake_async_client)
        fake_async_client.__aexit__ = AsyncMock(return_value=False)
        fake_async_client.post = AsyncMock(return_value=storage_response)

        with (
            patch("app.main.supabase", supabase_mock),
            patch("app.main.sub_service.check_limit",
                  new=AsyncMock(return_value={"allowed": True})),
            patch("app.main.sub_service.increment_usage", new=AsyncMock(return_value=True)),
            patch("app.services.plan_features.can_publish_subdomain",
                  new=AsyncMock(return_value=True)),
            patch("app.main.supabase_service.is_email_verified",
                  new=AsyncMock(return_value=True)),
            patch("app.main.httpx.AsyncClient", return_value=fake_async_client),
        ):
            resp = client.post("/api/publish", headers=auth_headers, json={
                "html_content": VALID_HTML,
                "subdomain": "nadirasalon",
                "project_name": "Nadira",
                "website_id": "ws-salon-2",
                "description": SALON_DESC,
                "business_type": "salon",
                "hero_image_prompt": HERO_PROMPT,
            })

        assert resp.status_code == 200, resp.text
        assert len(calls) == 2, "expected a retry without the optional columns"
        assert "hero_image_prompt" in calls[0]
        assert "hero_image_prompt" not in calls[1]
        # The website itself still lands — that is the point.
        assert calls[1]["id"] == "ws-salon-2"
        assert calls[1]["status"] == "published"

    def test_a_real_db_error_is_not_swallowed(self, client, auth_headers):
        """The fallback must only catch the missing-column case. Any other
        failure still fails loudly rather than silently dropping data."""
        supabase_mock = MagicMock()
        table_mock = _empty_select_mock()
        supabase_mock.table.return_value = table_mock
        table_mock.upsert.side_effect = Exception("connection refused")

        storage_response = MagicMock()
        storage_response.status_code = 201
        storage_response.text = ""
        fake_async_client = MagicMock()
        fake_async_client.__aenter__ = AsyncMock(return_value=fake_async_client)
        fake_async_client.__aexit__ = AsyncMock(return_value=False)
        fake_async_client.post = AsyncMock(return_value=storage_response)

        with (
            patch("app.main.supabase", supabase_mock),
            patch("app.main.sub_service.check_limit",
                  new=AsyncMock(return_value={"allowed": True})),
            patch("app.main.sub_service.increment_usage", new=AsyncMock(return_value=True)),
            patch("app.services.plan_features.can_publish_subdomain",
                  new=AsyncMock(return_value=True)),
            patch("app.main.supabase_service.is_email_verified",
                  new=AsyncMock(return_value=True)),
            patch("app.main.httpx.AsyncClient", return_value=fake_async_client),
        ):
            resp = client.post("/api/publish", headers=auth_headers, json={
                "html_content": VALID_HTML,
                "subdomain": "nadirasalon",
                "project_name": "Nadira",
                "website_id": "ws-salon-3",
                "description": SALON_DESC,
                "business_type": "salon",
            })
        assert resp.status_code == 500, resp.text

    def test_republish_without_the_fields_does_not_wipe_them(self, client, auth_headers):
        """Same contract as description: omitting a field on a republish
        must leave the stored value alone, not null it."""
        resp, payload = self._publish(client, auth_headers, {})
        assert resp.status_code == 200, resp.text
        assert "business_type" not in payload
        assert "hero_image_prompt" not in payload
