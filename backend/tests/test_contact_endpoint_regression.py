"""
Regression tests for PATCH /api/v1/websites/{id}/contact (credit-free WhatsApp
number edit).

Background — the mimba incident: the contact endpoint used to take the DB
`html_content` blob, run a wa.me regex over it, and republish it straight to the
storage snapshot the subdomain middleware serves. Two things went wrong:

  A) The DB blob had silently diverged from the live snapshot and was TRUNCATED
     (cut off mid-<img>, no </body>/</html>, missing the footer, the floating
     WhatsApp button, the chat-widget.js loader and the delivery markers).
     Republishing it overwrote the good live snapshot → every injected widget
     (WhatsApp float, "Pesan Delivery", BinaChat) vanished from the live site.

  B) Because the rewrite ran on the stale/broken DB blob (not the content
     visitors actually see), the number on the live site did not change even
     though the endpoint returned success.

The fix:
  1. rewrite against the LIVE serving snapshot when available;
  2. NEVER publish structurally-unbalanced HTML (mirrors the PUT /publish gate);
  3. tell the caller honestly whether the live site was actually updated.

These tests pin all three.
"""

from unittest.mock import patch, AsyncMock

import pytest


# A structurally-complete page: balanced tags, ends with </html>, and carries
# the widget markers the middleware relies on (delivery button, chat loader,
# floating WhatsApp button) plus wa.me links pointing at the OLD number.
FULL_HTML = (
    "<!DOCTYPE html><html><head><title>Mimba</title></head>"
    "<body>"
    '<a href="https://wa.me/60195551234?text=Hi">Chat</a>'
    '<button id="binaapp-delivery-btn">order</button>'
    '<script src="https://x/static/widgets/chat-widget.js" data-website-id="w1"></script>'
    '<a id="whatsapp-button" href="https://wa.me/60195551234">wa</a>'
    "<footer>foot</footer>"
    "</body></html>"
)

# The mimba failure mode: truncated mid-tag, no closing wrappers, widgets gone.
TRUNCATED_HTML = (
    "<!DOCTYPE html><html><head><title>Mimba</title></head>"
    "<body>"
    '<a href="https://wa.me/60195551234">Chat</a>'
    '<img src="https://res.cloudinary.com/x/image/upload'
)


def _row(**overrides):
    row = {
        "id": "ws-mimba",
        "user_id": "test-user-id-12345",
        "subdomain": "mimba",
        "status": "published",
        "whatsapp_number": "0195551234",  # normalises to 60195551234
        "html_content": FULL_HTML,
    }
    row.update(overrides)
    return row


@pytest.fixture
def patches():
    with (
        patch(
            "app.api.v1.endpoints.websites.supabase_service.get_website",
            new=AsyncMock(),
        ) as get_website,
        patch(
            "app.api.v1.endpoints.websites.supabase_service.update_website",
            new=AsyncMock(return_value=True),
        ) as update_website,
        patch(
            "app.api.v1.endpoints.websites.storage_service.publish_website",
            new=AsyncMock(return_value="https://mimba.binaapp.my"),
        ) as publish_website,
        patch(
            "app.api.v1.endpoints.websites._fetch_serving_snapshot",
            new=AsyncMock(return_value=None),
        ) as fetch_snapshot,
    ):
        yield {
            "get_website": get_website,
            "update_website": update_website,
            "publish_website": publish_website,
            "fetch_snapshot": fetch_snapshot,
        }


def _published_html(patches):
    """The html_content argument passed to storage_service.publish_website."""
    assert patches["publish_website"].called
    return patches["publish_website"].call_args.kwargs["html_content"]


def _update_payload(patches):
    """The data dict passed to supabase_service.update_website."""
    args, kwargs = patches["update_website"].call_args
    return args[1] if len(args) > 1 else kwargs.get("data", args[-1])


class TestTruncatedBlobNeverClobbersLiveSite:
    """Bug A — a truncated/unbalanced base must never reach storage."""

    def test_truncated_db_and_no_snapshot_skips_republish(
        self, client, auth_headers, patches
    ):
        # DB blob is truncated AND the live snapshot can't be fetched → there is
        # no safe base. The endpoint must NOT publish anything.
        patches["get_website"].return_value = _row(html_content=TRUNCATED_HTML)
        patches["fetch_snapshot"].return_value = None

        resp = client.patch(
            "/api/v1/websites/ws-mimba/contact",
            headers=auth_headers,
            json={"whatsapp_number": "0123456789"},
        )

        assert resp.status_code == 200
        body = resp.json()
        # Storage snapshot left untouched — widgets preserved.
        patches["publish_website"].assert_not_called()
        # DB html_content NOT overwritten with the truncated blob.
        assert "html_content" not in _update_payload(patches)
        # Honest response.
        assert body["live_site_updated"] is False
        assert body["warning"] == "no_balanced_html_base"

    def test_truncated_db_but_good_snapshot_rewrites_snapshot(
        self, client, auth_headers, patches
    ):
        # DB blob truncated, but the live snapshot is intact → rewrite the
        # snapshot (fixes bug B) and keep the widgets (fixes bug A).
        patches["get_website"].return_value = _row(html_content=TRUNCATED_HTML)
        patches["fetch_snapshot"].return_value = FULL_HTML

        resp = client.patch(
            "/api/v1/websites/ws-mimba/contact",
            headers=auth_headers,
            json={"whatsapp_number": "0123456789"},
        )

        assert resp.status_code == 200
        body = resp.json()
        published = _published_html(patches)
        # Number actually changed on what we publish.
        assert "wa.me/60123456789" in published
        assert "wa.me/60195551234" not in published
        # Widgets/structure survived (they came from the good snapshot).
        assert "chat-widget.js" in published
        assert 'id="whatsapp-button"' in published
        assert "binaapp-delivery-btn" in published
        assert published.rstrip().endswith("</html>")
        # DB blob repaired/synced to the good content.
        assert _update_payload(patches)["html_content"] == published
        assert body["live_site_updated"] is True
        assert "warning" not in body


class TestNumberActuallyChanges:
    """Bug B — the live snapshot's wa.me links must reflect the new number."""

    def test_good_db_no_snapshot_falls_back_and_publishes(
        self, client, auth_headers, patches
    ):
        # Balanced DB blob, snapshot unavailable → fall back to the DB blob
        # (it's balanced, so safe) and publish the rewrite.
        patches["get_website"].return_value = _row(html_content=FULL_HTML)
        patches["fetch_snapshot"].return_value = None

        resp = client.patch(
            "/api/v1/websites/ws-mimba/contact",
            headers=auth_headers,
            json={"whatsapp_number": "0123456789"},
        )

        assert resp.status_code == 200
        published = _published_html(patches)
        assert "wa.me/60123456789" in published
        assert "wa.me/60195551234" not in published
        # ?text= prefill suffix preserved by the regex.
        assert "wa.me/60123456789?text=Hi" in published
        assert resp.json()["live_site_updated"] is True

    def test_draft_site_updates_db_without_publishing(
        self, client, auth_headers, patches
    ):
        # A draft has no live snapshot to refresh; the DB blob is still rewritten
        # and no storage publish happens.
        patches["get_website"].return_value = _row(
            status="draft", html_content=FULL_HTML
        )

        resp = client.patch(
            "/api/v1/websites/ws-mimba/contact",
            headers=auth_headers,
            json={"whatsapp_number": "0123456789"},
        )

        assert resp.status_code == 200
        patches["publish_website"].assert_not_called()
        assert "wa.me/60123456789" in _update_payload(patches)["html_content"]


class TestAccessControl:
    """The guard rails around the credit-free path must still hold."""

    def test_404_when_missing(self, client, auth_headers, patches):
        patches["get_website"].return_value = None
        resp = client.patch(
            "/api/v1/websites/ws-mimba/contact",
            headers=auth_headers,
            json={"whatsapp_number": "0123456789"},
        )
        assert resp.status_code == 404

    def test_403_when_not_owner(self, client, auth_headers, patches):
        patches["get_website"].return_value = _row(user_id="someone-else")
        resp = client.patch(
            "/api/v1/websites/ws-mimba/contact",
            headers=auth_headers,
            json={"whatsapp_number": "0123456789"},
        )
        assert resp.status_code == 403
        patches["publish_website"].assert_not_called()

    def test_400_when_number_missing(self, client, auth_headers, patches):
        patches["get_website"].return_value = _row()
        resp = client.patch(
            "/api/v1/websites/ws-mimba/contact",
            headers=auth_headers,
            json={"whatsapp_number": "   "},
        )
        assert resp.status_code == 400
