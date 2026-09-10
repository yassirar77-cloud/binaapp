"""
Regression tests for description + generation_count persistence on the
publish flow.

Background: migration 039 added websites.description and
websites.generation_count to power the editor's regenerate flow. PR #665
wired them through the v1 endpoint, but the production /create flow
hits POST /api/publish (defined in app.main) and a sibling endpoint in
app.api.simple.publish — neither of which was updated, so newly-created
websites landed with description=NULL / generation_count=0 and the
editor's regenerate UI couldn't reuse the prompt.

These tests pin the fix: when the frontend sends a description, the
upsert payload must include it, and a brand-new website must record
generation_count=1.
"""

import contextlib
from unittest.mock import patch, MagicMock, AsyncMock

import pytest


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------

VALID_BALANCED_HTML = (
    "<!DOCTYPE html><html><head><title>Test</title></head>"
    "<body><h1>Hello</h1></body></html>"
)


def _empty_select_mock():
    """Build a chainable Supabase table mock whose .execute() returns no
    rows — simulates a brand-new website ID with no existing record."""
    mock = MagicMock()
    for method in (
        "select", "insert", "update", "upsert", "delete",
        "eq", "neq", "limit", "single", "order",
    ):
        getattr(mock, method).return_value = mock
    response = MagicMock()
    response.data = []
    mock.execute.return_value = response
    return mock


# ----------------------------------------------------------------------
# main.py POST /api/publish
# ----------------------------------------------------------------------


class TestApiPublishPersistsDescription:
    """The endpoint at app.main:/api/publish is the one the production
    /create flow actually calls. The upsert into websites must carry
    description (when provided) and generation_count=1 for new rows."""

    def _captured_upsert_payload(self, supabase_mock):
        """Pull the dict that was passed to .table('websites').upsert()."""
        # The endpoint calls supabase.table('websites').upsert(payload, ...)
        # We use the chainable mock so every .table() / .upsert() call
        # is recorded — find the upsert call with a dict payload.
        for call in supabase_mock.table.return_value.upsert.call_args_list:
            args, _kwargs = call
            if args and isinstance(args[0], dict):
                return args[0]
        return None

    def test_new_website_upsert_includes_description_and_generation_count(
        self, client, auth_headers
    ):
        supabase_mock = MagicMock()
        # .table('websites') returns a chainable that responds with
        # empty data to existence + subdomain-ownership checks (so the
        # endpoint treats this as a brand-new website).
        supabase_mock.table.return_value = _empty_select_mock()

        # Fake httpx client whose POST to Supabase Storage "succeeds".
        storage_response = MagicMock()
        storage_response.status_code = 201
        storage_response.text = ""
        fake_async_client = MagicMock()
        fake_async_client.__aenter__ = AsyncMock(return_value=fake_async_client)
        fake_async_client.__aexit__ = AsyncMock(return_value=False)
        fake_async_client.post = AsyncMock(return_value=storage_response)

        with (
            patch("app.main.supabase", supabase_mock),
            patch(
                "app.main.sub_service.check_limit",
                new=AsyncMock(return_value={"allowed": True}),
            ),
            patch(
                "app.main.sub_service.increment_usage",
                new=AsyncMock(return_value=True),
            ),
            patch(
                "app.services.plan_features.can_publish_subdomain",
                new=AsyncMock(return_value=True),
            ),
            # Email-verification gate on /api/publish: treat the user as
            # verified so this persistence test reaches the upsert.
            patch(
                "app.main.supabase_service.is_email_verified",
                new=AsyncMock(return_value=True),
            ),
            patch(
                "app.main.httpx.AsyncClient",
                return_value=fake_async_client,
            ),
        ):
            resp = client.post(
                "/api/publish",
                headers=auth_headers,
                json={
                    "html_content": VALID_BALANCED_HTML,
                    "subdomain": "newshop",
                    "project_name": "New Shop",
                    "website_id": "ws-new-1",
                    "description": "A modern bakery in Shah Alam with delivery",
                },
            )

        assert resp.status_code == 200, resp.text
        payload = self._captured_upsert_payload(supabase_mock)
        assert payload is not None, "websites upsert was never called"

        # Regression assertions — these are the columns migration 039
        # added that the editor's regenerate UI reads back.
        assert payload.get("description") == (
            "A modern bakery in Shah Alam with delivery"
        )
        assert payload.get("generation_count") == 1

        # Sanity: the rest of the row still looks right.
        assert payload["id"] == "ws-new-1"
        assert payload["subdomain"] == "newshop"
        assert payload["status"] == "published"

    def test_republish_does_not_null_description_or_reset_counter(
        self, client, auth_headers, test_user_id
    ):
        """When the frontend omits description on a republish, the upsert
        must NOT carry description (which would null-out the stored prompt)
        and must NOT reset generation_count (which would lose history)."""

        # Simulate an existing website owned by the same user.
        existing_row = MagicMock()
        existing_row.data = [{"id": "ws-existing-1", "user_id": test_user_id}]
        table_mock = MagicMock()
        for method in (
            "select", "insert", "update", "upsert", "delete",
            "eq", "neq", "limit", "single", "order",
        ):
            getattr(table_mock, method).return_value = table_mock
        table_mock.execute.return_value = existing_row

        supabase_mock = MagicMock()
        supabase_mock.table.return_value = table_mock

        storage_response = MagicMock()
        storage_response.status_code = 201
        storage_response.text = ""
        fake_async_client = MagicMock()
        fake_async_client.__aenter__ = AsyncMock(return_value=fake_async_client)
        fake_async_client.__aexit__ = AsyncMock(return_value=False)
        fake_async_client.post = AsyncMock(return_value=storage_response)

        with (
            patch("app.main.supabase", supabase_mock),
            patch(
                "app.main.sub_service.check_limit",
                new=AsyncMock(return_value={"allowed": True}),
            ),
            patch(
                "app.main.sub_service.increment_usage",
                new=AsyncMock(return_value=True),
            ),
            patch(
                "app.services.plan_features.can_publish_subdomain",
                new=AsyncMock(return_value=True),
            ),
            # Email-verification gate on /api/publish: treat the user as
            # verified so this persistence test reaches the upsert.
            patch(
                "app.main.supabase_service.is_email_verified",
                new=AsyncMock(return_value=True),
            ),
            patch(
                "app.main.httpx.AsyncClient",
                return_value=fake_async_client,
            ),
        ):
            resp = client.post(
                "/api/publish",
                headers=auth_headers,
                json={
                    "html_content": VALID_BALANCED_HTML,
                    "subdomain": "existingshop",
                    "project_name": "Existing Shop",
                    "website_id": "ws-existing-1",
                    # Note: no "description" key — republish from the dashboard
                    # doesn't necessarily re-send the prompt.
                },
            )

        assert resp.status_code == 200, resp.text
        payload = self._captured_upsert_payload(supabase_mock)
        assert payload is not None
        # Key must be absent — including it as None would null out the
        # previously-stored prompt on a partial-data republish.
        assert "description" not in payload
        # generation_count is owned by the regenerate endpoint on the
        # update path; publish must not silently reset it.
        assert "generation_count" not in payload



    def _republish_env(self, existing_id, test_user_id, missing_id=None):
        """Supabase + storage mocks for a subdomain the user already owns.

        ``missing_id`` is an id whose lookup must MISS. The endpoint first
        looks the client's website_id up by id and only falls through to the
        subdomain check when that finds nothing — which is exactly the
        /create flow, where the client sends a fresh uuid every time. A mock
        that answers every query with the existing row "finds" the client
        uuid and never reaches the rebind this test exists to pin.
        """
        existing_row = MagicMock()
        existing_row.data = [{"id": existing_id, "user_id": test_user_id}]
        empty = MagicMock()
        empty.data = []
        table_mock = MagicMock()
        for method in (
            "select", "insert", "update", "upsert", "delete",
            "eq", "neq", "limit", "single", "order",
        ):
            getattr(table_mock, method).return_value = table_mock

        def _execute():
            last_eq = table_mock.eq.call_args
            if missing_id and last_eq and tuple(last_eq.args) == ("id", missing_id):
                return empty
            return existing_row

        table_mock.execute.side_effect = _execute
        supabase_mock = MagicMock()
        supabase_mock.table.return_value = table_mock

        storage_response = MagicMock()
        storage_response.status_code = 201
        storage_response.text = ""
        fake_async_client = MagicMock()
        fake_async_client.__aenter__ = AsyncMock(return_value=fake_async_client)
        fake_async_client.__aexit__ = AsyncMock(return_value=False)
        fake_async_client.post = AsyncMock(return_value=storage_response)
        return supabase_mock, fake_async_client

    @contextlib.contextmanager
    def _republish_patches(self, supabase_mock, fake_async_client):
        """Same patch set as the republish test above, as one context."""
        with (
            patch("app.main.supabase", supabase_mock),
            patch("app.main.sub_service.check_limit",
                  new=AsyncMock(return_value={"allowed": True})),
            patch("app.main.sub_service.increment_usage",
                  new=AsyncMock(return_value=True)),
            patch("app.services.plan_features.can_publish_subdomain",
                  new=AsyncMock(return_value=True)),
            patch("app.main.supabase_service.is_email_verified",
                  new=AsyncMock(return_value=True)),
            patch("app.main.httpx.AsyncClient", return_value=fake_async_client),
        ):
            yield

    def test_republish_to_owned_subdomain_returns_the_existing_row_id(
        self, client, auth_headers, test_user_id
    ):
        """Regression for the hero video that never started.

        The /create page generates its own uuid and sends it as website_id.
        When the subdomain is one the merchant already owns, the endpoint
        UPDATES that row and keeps its id — so the client's uuid never
        exists. The response's website_id is the only way the client can
        learn the real id; it must be the existing row's, and the upsert
        must target that row (not insert the client's id as a new one).
        """
        supabase_mock, fake_client = self._republish_env(
            "ws-existing-1", test_user_id, missing_id="client-generated-uuid"
        )
        with self._republish_patches(supabase_mock, fake_client):
            resp = client.post(
                "/api/publish",
                headers=auth_headers,
                json={
                    "html_content": VALID_BALANCED_HTML,
                    "subdomain": "existingshop",
                    "project_name": "Existing Shop",
                    # A DIFFERENT id from the row that owns the subdomain —
                    # exactly what the /create page sends on a republish.
                    "website_id": "client-generated-uuid",
                },
            )

        assert resp.status_code == 200, resp.text
        assert resp.json()["website_id"] == "ws-existing-1"
        payload = self._captured_upsert_payload(supabase_mock)
        assert payload["id"] == "ws-existing-1"

    def test_publish_stamps_published_at(
        self, client, auth_headers, test_user_id
    ):
        """published_at was never written on this path, so every site made
        via /create had it NULL and the dashboard could not order by it.
        Both a fresh publish and a republish are a publish — stamp it."""
        supabase_mock, fake_client = self._republish_env("ws-existing-1", test_user_id)
        with self._republish_patches(supabase_mock, fake_client):
            resp = client.post(
                "/api/publish",
                headers=auth_headers,
                json={
                    "html_content": VALID_BALANCED_HTML,
                    "subdomain": "existingshop",
                    "project_name": "Existing Shop",
                    "website_id": "ws-existing-1",
                },
            )

        assert resp.status_code == 200, resp.text
        payload = self._captured_upsert_payload(supabase_mock)
        assert payload.get("published_at"), "published_at must be stamped on publish"
        assert payload["published_at"] == payload["updated_at"]


# ----------------------------------------------------------------------
# app.api.simple.publish (do_insert path)
# ----------------------------------------------------------------------


class TestSimplePublishPersistsDescription:
    """The sibling endpoint at app.api.simple.publish is currently
    unmounted but kept in lockstep with main.py — when somebody wires it
    up later we want the same persistence guarantees."""

    @pytest.mark.asyncio
    async def test_do_insert_writes_description_and_generation_count(self):
        """Call the publish handler directly (the router isn't included
        in the live app) with the heavy deps mocked. The captured
        payload to create_website must include the two new columns."""

        from app.api.simple import publish as simple_publish

        captured = {}

        async def fake_create_website(data):
            captured.update(data)
            return {"id": data["id"]}

        # Mock the chained supabase_service calls used by the publish handler.
        with (
            patch.object(
                simple_publish.supabase_service,
                "create_website",
                new=AsyncMock(side_effect=fake_create_website),
            ),
            patch.object(
                simple_publish.supabase_service,
                "check_subdomain_available",
                new=AsyncMock(return_value=True),
            ),
            # Email-verification gate: treat the publishing user as verified
            # so this persistence-focused test reaches create_website.
            patch.object(
                simple_publish.supabase_service,
                "is_email_verified",
                new=AsyncMock(return_value=True),
            ),
            patch.object(
                simple_publish.storage_service,
                "upload_website",
                new=AsyncMock(return_value="https://example.com/site"),
            ),
            patch.object(
                simple_publish.storage_service,
                "check_subdomain_exists",
                new=AsyncMock(return_value=False),
            ),
        ):
            request = simple_publish.PublishRequest(
                html_content=VALID_BALANCED_HTML,
                subdomain="bakery01",
                project_name="Bakery 01",
                user_id="11111111-1111-4111-8111-111111111111",
                description="A modern bakery in Shah Alam with delivery",
            )

            # http_request and current_user are only used for auth-flavoured
            # branches we don't exercise; a MagicMock is enough.
            fake_http_request = MagicMock()
            fake_http_request.query_params = {}

            response = await simple_publish.publish_website(
                request=request,
                http_request=fake_http_request,
                current_user=None,
            )

        assert response.success is True
        # Regression: migration-039 columns must be on the insert payload.
        assert captured.get("description") == (
            "A modern bakery in Shah Alam with delivery"
        )
        assert captured.get("generation_count") == 1

    @pytest.mark.asyncio
    async def test_do_insert_omits_description_when_not_provided(self):
        """If the caller doesn't supply a description (legacy flow,
        anonymous user), the insert payload must omit the column rather
        than write SQL NULL — keeps backward compat with old callers."""

        from app.api.simple import publish as simple_publish

        captured = {}

        async def fake_create_website(data):
            captured.update(data)
            return {"id": data["id"]}

        with (
            patch.object(
                simple_publish.supabase_service,
                "create_website",
                new=AsyncMock(side_effect=fake_create_website),
            ),
            patch.object(
                simple_publish.supabase_service,
                "check_subdomain_available",
                new=AsyncMock(return_value=True),
            ),
            # Email-verification gate: treat the publishing user as verified
            # so this persistence-focused test reaches create_website.
            patch.object(
                simple_publish.supabase_service,
                "is_email_verified",
                new=AsyncMock(return_value=True),
            ),
            patch.object(
                simple_publish.storage_service,
                "upload_website",
                new=AsyncMock(return_value="https://example.com/site"),
            ),
            patch.object(
                simple_publish.storage_service,
                "check_subdomain_exists",
                new=AsyncMock(return_value=False),
            ),
        ):
            request = simple_publish.PublishRequest(
                html_content=VALID_BALANCED_HTML,
                subdomain="bakery02",
                project_name="Bakery 02",
                user_id="22222222-2222-4222-8222-222222222222",
                # no description
            )
            fake_http_request = MagicMock()
            fake_http_request.query_params = {}

            await simple_publish.publish_website(
                request=request,
                http_request=fake_http_request,
                current_user=None,
            )

        assert "description" not in captured
        # generation_count is unconditional on new inserts — it's the
        # row's lifetime regen counter, defaulting to 1 for the initial
        # generation regardless of whether we know the prompt.
        assert captured.get("generation_count") == 1
