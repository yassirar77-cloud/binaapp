"""One unknown column must not throw away the whole write.

2026-09-13, website ae906a32: the generation finished, and step 4 wrote a
derived ``integrations`` list to a column no migration ever created. PostgREST
answered

    400 {"code":"PGRST204","message":"Could not find the 'integrations'
         column of 'websites' in the schema cache"}

A PATCH is all-or-nothing, so the generated HTML, the meta tags, the sections
and the generation count went with it — and the endpoint logged "✅ Step 4/4:
Database updated successfully" and "🎉 Website generation completed
successfully" straight afterwards, because it never looked at the result.

Two fixes, both tested here: an unknown column is dropped and the write
retried, and a write that genuinely fails says so.
"""

import pytest

from app.services.supabase_client import (
    CRITICAL_WEBSITE_COLUMNS,
    SupabaseService,
    unknown_column,
)

PGRST204 = (
    '{"code":"PGRST204","details":null,"hint":null,"message":"Could not find '
    "the 'integrations' column of 'websites' in the schema cache\"}"
)


class FakeResponse:
    def __init__(self, status_code, payload=None, text=None):
        self.status_code = status_code
        self._payload = payload
        self.text = text if text is not None else ("[]" if payload is None else "ok")

    def json(self):
        return self._payload


class FakeClient:
    """Answers each PATCH from a scripted list, recording what was sent."""

    def __init__(self, responses):
        self._responses = list(responses)
        self.sent = []

    async def patch(self, url, headers=None, params=None, json=None):
        self.sent.append(dict(json or {}))
        return self._responses.pop(0)


def _service(responses):
    service = SupabaseService.__new__(SupabaseService)
    service.url = "https://example.supabase.co"
    service.headers = {}
    client = FakeClient(responses)

    class _Ctx:
        async def __aenter__(self):
            return client

        async def __aexit__(self, *exc):
            return False

    service._client = lambda: _Ctx()
    return service, client


class TestReadingPostgrestsAnswer:
    def test_the_missing_column_is_named(self):
        assert unknown_column(400, PGRST204) == "integrations"

    def test_another_400_is_not_a_missing_column(self):
        assert unknown_column(400, '{"code":"23505","message":"duplicate key"}') is None

    def test_a_success_is_never_read_as_one(self):
        assert unknown_column(200, PGRST204) is None

    def test_the_columns_that_must_never_be_dropped(self):
        assert {"html_content", "status", "user_id", "id", "subdomain"} <= CRITICAL_WEBSITE_COLUMNS


class TestTheWriteSurvivesSchemaDrift:
    @pytest.mark.asyncio
    async def test_the_unknown_column_is_dropped_and_the_rest_lands(self):
        service, client = _service([
            FakeResponse(400, text=PGRST204),
            FakeResponse(200, payload=[{"id": "ae906a32"}]),
        ])
        ok = await service.update_website(
            "ae906a32",
            {"html_content": "<html>…</html>", "integrations": ["WhatsApp"], "generation_count": 4},
        )
        assert ok is True
        assert len(client.sent) == 2
        assert "integrations" in client.sent[0]
        assert "integrations" not in client.sent[1]
        # The point of the retry: the page and the counter are still written.
        assert client.sent[1]["html_content"] == "<html>…</html>"
        assert client.sent[1]["generation_count"] == 4

    @pytest.mark.asyncio
    async def test_the_callers_payload_is_not_mutated(self):
        service, _client = _service([
            FakeResponse(400, text=PGRST204),
            FakeResponse(200, payload=[{"id": "x"}]),
        ])
        payload = {"html_content": "<html></html>", "integrations": []}
        await service.update_website("x", payload)
        assert "integrations" in payload

    @pytest.mark.asyncio
    async def test_a_column_that_matters_is_never_dropped(self):
        missing_html = PGRST204.replace("integrations", "html_content")
        service, client = _service([FakeResponse(400, text=missing_html)])
        ok = await service.update_website("x", {"html_content": "<html></html>"})
        assert ok is False
        assert len(client.sent) == 1

    @pytest.mark.asyncio
    async def test_an_ordinary_failure_is_still_a_failure(self):
        service, client = _service([FakeResponse(500, text="upstream exploded")])
        assert await service.update_website("x", {"html_content": "h"}) is False
        assert len(client.sent) == 1

    @pytest.mark.asyncio
    async def test_zero_rows_is_still_a_failure(self):
        service, _client = _service([FakeResponse(200, payload=[])])
        assert await service.update_website("x", {"html_content": "h"}) is False

    @pytest.mark.asyncio
    async def test_a_clean_write_makes_exactly_one_request(self):
        service, client = _service([FakeResponse(200, payload=[{"id": "x"}])])
        assert await service.update_website("x", {"html_content": "h"}) is True
        assert len(client.sent) == 1

    @pytest.mark.asyncio
    async def test_several_unknown_columns_are_dropped_one_by_one(self):
        first = PGRST204
        second = PGRST204.replace("integrations", "sections")
        service, client = _service([
            FakeResponse(400, text=first),
            FakeResponse(400, text=second),
            FakeResponse(200, payload=[{"id": "x"}]),
        ])
        ok = await service.update_website(
            "x", {"html_content": "h", "integrations": [], "sections": []}
        )
        assert ok is True
        assert client.sent[-1] == {"html_content": "h"}

    @pytest.mark.asyncio
    async def test_nothing_left_to_write_is_a_failure_not_a_success(self):
        service, _client = _service([FakeResponse(400, text=PGRST204)])
        assert await service.update_website("x", {"integrations": []}) is False
