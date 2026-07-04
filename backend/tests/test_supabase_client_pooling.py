"""
Regression tests for SupabaseService.delete_website_cascade and the shared
pooled httpx.AsyncClient.

The cascade delete is the riskiest consumer of SupabaseService's HTTP layer:
it issues ~15 REST calls whose ORDER matters (children before parents, and
rider_id must be nullified on delivery_orders before riders are deleted).
These tests pin that behaviour down so the HTTP-client internals can change
(per-call clients -> one pooled client) without silently breaking deletion.

All HTTP traffic is captured with httpx.MockTransport — no network involved.
"""

import httpx
import pytest

from app.services.supabase_client import SupabaseService

WEBSITE_ID = "11111111-2222-3333-4444-555555555555"
RIDER_IDS = ["rider-1", "rider-2"]
CONVERSATION_IDS = ["conv-1"]
ORDER_IDS = ["order-1", "order-2"]


class RecordingHandler:
    """MockTransport handler that records every request and answers like
    Supabase REST would for the cascade-delete flow."""

    def __init__(self):
        self.requests: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        path = request.url.path

        if request.method == "GET":
            if path == "/rest/v1/riders":
                return httpx.Response(200, json=[{"id": r} for r in RIDER_IDS])
            if path == "/rest/v1/chat_conversations":
                return httpx.Response(200, json=[{"id": c} for c in CONVERSATION_IDS])
            if path == "/rest/v1/delivery_orders":
                return httpx.Response(200, json=[{"id": o} for o in ORDER_IDS])
            return httpx.Response(200, json=[])

        # DELETE / PATCH — Supabase answers 204 No Content
        return httpx.Response(204)

    # -- helpers -----------------------------------------------------------

    def calls(self, method: str, path: str) -> list[httpx.Request]:
        return [r for r in self.requests if r.method == method and r.url.path == path]

    def first_index(self, method: str, path: str) -> int:
        for i, r in enumerate(self.requests):
            if r.method == method and r.url.path == path:
                return i
        raise AssertionError(f"No {method} {path} in recorded requests")


@pytest.fixture
def service_and_handler(monkeypatch):
    """A SupabaseService whose HTTP layer is a recording MockTransport.

    Patches the httpx.AsyncClient constructor as seen by the module so the
    mock applies regardless of whether the service opens a client per call
    or reuses one pooled client.
    """
    handler = RecordingHandler()
    real_async_client = httpx.AsyncClient

    def patched_async_client(*args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(handler)
        return real_async_client(*args, **kwargs)

    monkeypatch.setattr(
        "app.services.supabase_client.httpx.AsyncClient", patched_async_client
    )
    return SupabaseService(), handler


@pytest.mark.asyncio
async def test_cascade_delete_succeeds_and_reports_tables(service_and_handler):
    service, handler = service_and_handler

    result = await service.delete_website_cascade(WEBSITE_ID)

    assert result["success"] is True
    deleted = " ".join(result["deleted_tables"])
    for table in [
        "chat_messages",
        "chat_conversations",
        "rider_locations",
        "order_items",
        "delivery_orders",
        "menu_items",
        "menu_categories",
        "delivery_zones",
        "delivery_settings",
        "riders",
        "generation_jobs",
    ]:
        assert table in deleted, f"{table} missing from deleted_tables"


@pytest.mark.asyncio
async def test_cascade_delete_order_children_before_parents(service_and_handler):
    service, handler = service_and_handler

    result = await service.delete_website_cascade(WEBSITE_ID)
    assert result["success"] is True

    # chat_messages (child) before chat_conversations (parent)
    assert handler.first_index("DELETE", "/rest/v1/chat_messages") < handler.first_index(
        "DELETE", "/rest/v1/chat_conversations"
    )
    # order_items (child) before delivery_orders (parent)
    assert handler.first_index("DELETE", "/rest/v1/order_items") < handler.first_index(
        "DELETE", "/rest/v1/delivery_orders"
    )
    # rider_locations (child) before riders (parent)
    assert handler.first_index("DELETE", "/rest/v1/rider_locations") < handler.first_index(
        "DELETE", "/rest/v1/riders"
    )
    # rider_id must be nullified on delivery_orders BEFORE the orders are
    # deleted and before riders are deleted (FK integrity)
    nullify_patch = handler.first_index("PATCH", "/rest/v1/delivery_orders")
    assert nullify_patch < handler.first_index("DELETE", "/rest/v1/delivery_orders")
    assert nullify_patch < handler.first_index("DELETE", "/rest/v1/riders")
    # the website row itself is deleted last
    website_delete = handler.first_index("DELETE", "/rest/v1/websites")
    assert website_delete == len(handler.requests) - 1


@pytest.mark.asyncio
async def test_cascade_delete_uses_child_ids_in_filters(service_and_handler):
    service, handler = service_and_handler

    await service.delete_website_cascade(WEBSITE_ID)

    # chat_messages deleted by the conversation ids fetched earlier
    (msg_delete,) = handler.calls("DELETE", "/rest/v1/chat_messages")
    assert "conversation_id" in str(msg_delete.url.params)
    for cid in CONVERSATION_IDS:
        assert cid in str(msg_delete.url)

    # rider_locations deleted by rider ids
    (loc_delete,) = handler.calls("DELETE", "/rest/v1/rider_locations")
    for rid in RIDER_IDS:
        assert rid in str(loc_delete.url)

    # order_items deleted by order ids
    (items_delete,) = handler.calls("DELETE", "/rest/v1/order_items")
    for oid in ORDER_IDS:
        assert oid in str(items_delete.url)

    # final website delete filters on the website id
    (site_delete,) = handler.calls("DELETE", "/rest/v1/websites")
    assert WEBSITE_ID in str(site_delete.url)


@pytest.mark.asyncio
async def test_pooled_client_is_reused_across_calls(service_and_handler):
    """All REST calls must go through ONE shared AsyncClient (connection
    pooling), and it must stay open between calls."""
    service, handler = service_and_handler

    await service.get_website(WEBSITE_ID)
    first = service._pooled_client
    assert first is not None and not first.is_closed

    await service.get_website_by_subdomain("demo")
    assert service._pooled_client is first, "client was recreated between calls"
    assert not first.is_closed


@pytest.mark.asyncio
async def test_aclose_closes_and_next_call_recreates(service_and_handler):
    service, handler = service_and_handler

    await service.get_website(WEBSITE_ID)
    old = service._pooled_client
    await service.aclose()
    assert old.is_closed

    # Next call transparently gets a fresh client
    await service.get_website(WEBSITE_ID)
    assert service._pooled_client is not old
    assert not service._pooled_client.is_closed


@pytest.mark.asyncio
async def test_cascade_delete_fails_when_website_delete_fails(monkeypatch):
    """A non-2xx on the final website DELETE must surface success=False."""
    handler = RecordingHandler()
    original_call = RecordingHandler.__call__

    def failing_call(self, request):
        if request.method == "DELETE" and request.url.path == "/rest/v1/websites":
            self.requests.append(request)
            return httpx.Response(409, text="foreign key constraint")
        return original_call(self, request)

    handler.__class__ = type("FailingHandler", (RecordingHandler,), {"__call__": failing_call})

    real_async_client = httpx.AsyncClient

    def patched_async_client(*args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(handler)
        return real_async_client(*args, **kwargs)

    monkeypatch.setattr(
        "app.services.supabase_client.httpx.AsyncClient", patched_async_client
    )

    service = SupabaseService()
    result = await service.delete_website_cascade(WEBSITE_ID)

    assert result["success"] is False
    # partial progress is still reported so callers can log it
    assert "deleted_tables" in result
