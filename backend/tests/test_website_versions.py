"""Tests for version history (services/website_versions.py and
api/v1/endpoints/website_versions.py).

What matters:

  1. A snapshot can never break a save: it never raises, and it never stores
     a page that would be dangerous to restore (empty / unbalanced).
  2. History stays useful: identical pages and bursts of same-kind edits do
     not fill it, and only the newest MAX_VERSIONS rows are kept.
  3. A restore is owner-only, credit-free, publishes only balanced HTML, and
     stores the page it replaces first — so a restore is itself undoable.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.endpoints import website_versions as endpoint
from app.services import website_versions as versions


def _page(body: str) -> str:
    return f"<!DOCTYPE html><html><head><title>Kedai Ali</title></head><body>{body}</body></html>"


LIVE_HTML = _page("<h1>Sekarang</h1>")
OLD_HTML = _page("<h1>Dahulu</h1>")
TRUNCATED_HTML = "<!DOCTYPE html><html><head></head><body><div><img src=\"https://res.cl"


class FakeTable:
    """An in-memory website_versions table behind the four storage calls."""

    def __init__(self):
        self.rows = []
        self._n = 0
        self.clock = datetime(2026, 1, 1, tzinfo=timezone.utc)

    def add(self, website_id="ws-1", html=OLD_HTML, source="manual_save", age_seconds=None, **extra):
        self._n += 1
        created = (
            datetime.now(timezone.utc) - timedelta(seconds=age_seconds)
            if age_seconds is not None
            else self.clock + timedelta(minutes=self._n)
        )
        row = {
            "id": f"v-{self._n}",
            "website_id": website_id,
            "html": html,
            "content_hash": versions.content_hash(html),
            "source": source,
            "label": None,
            "size_bytes": len(html.encode()),
            "created_by": None,
            "created_at": created.isoformat(),
        }
        row.update(extra)
        self.rows.append(row)
        return row

    async def select(self, params):
        rows = list(self.rows)
        for key in ("website_id", "id"):
            if key in params:
                want = params[key].split("eq.", 1)[1]
                rows = [r for r in rows if r[key] == want]
        if params.get("order") == "created_at.desc":
            rows.sort(key=lambda r: r["created_at"], reverse=True)
        offset = int(params.get("offset", 0))
        limit = int(params.get("limit", 1000))
        rows = rows[offset:offset + limit]
        columns = params.get("select", "*")
        if columns != "*":
            keep = columns.split(",")
            rows = [{k: r[k] for k in keep if k in r} for r in rows]
        return rows

    async def insert(self, row):
        return self.add(
            row["website_id"], row["html"], row["source"], age_seconds=0,
            label=row.get("label"), created_by=row.get("created_by"),
        )

    async def delete(self, ids):
        self.rows = [r for r in self.rows if r["id"] not in ids]

    async def update(self, version_id, website_id, data):
        for r in self.rows:
            if r["id"] == version_id and r["website_id"] == website_id:
                r.update(data)
                return {k: v for k, v in r.items() if k != "html"}
        return None


@pytest.fixture
def table(monkeypatch):
    fake = FakeTable()
    monkeypatch.setattr(versions, "_select", fake.select)
    monkeypatch.setattr(versions, "_insert", fake.insert)
    monkeypatch.setattr(versions, "_delete", fake.delete)
    monkeypatch.setattr(versions, "_update", fake.update)
    return fake


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class TestSnapshot:
    async def test_stores_the_page_and_returns_metadata_without_html(self, table):
        stored = await versions.snapshot("ws-1", LIVE_HTML, "regenerate", "user-1")
        assert stored and "html" not in stored
        assert stored["source"] == "regenerate"
        assert table.rows[0]["html"] == LIVE_HTML
        assert table.rows[0]["created_by"] == "user-1"

    async def test_identical_to_the_newest_version_is_skipped(self, table):
        assert await versions.snapshot("ws-1", LIVE_HTML, "regenerate")
        assert await versions.snapshot("ws-1", LIVE_HTML, "restore") is None
        assert len(table.rows) == 1

    @pytest.mark.parametrize("html", ["", "   ", None, TRUNCATED_HTML])
    async def test_empty_or_unbalanced_html_is_never_stored(self, table, html):
        assert await versions.snapshot("ws-1", html, "manual_save") is None
        assert table.rows == []

    async def test_a_burst_of_same_kind_edits_keeps_only_the_first(self, table):
        assert await versions.snapshot("ws-1", _page("a"), "theme")
        assert await versions.snapshot("ws-1", _page("b"), "theme") is None
        # A different kind of change is its own decision and is kept.
        assert await versions.snapshot("ws-1", _page("c"), "regenerate")
        assert [r["html"] for r in table.rows] == [_page("a"), _page("c")]

    async def test_same_kind_edit_after_the_burst_window_is_kept(self, table):
        table.add(html=_page("a"), source="manual_save",
                  age_seconds=versions.BURST_WINDOW_SECONDS + 60)
        assert await versions.snapshot("ws-1", _page("b"), "manual_save")
        assert len(table.rows) == 2

    async def test_regenerates_are_never_collapsed(self, table):
        assert await versions.snapshot("ws-1", _page("a"), "regenerate")
        assert await versions.snapshot("ws-1", _page("b"), "regenerate")
        assert len(table.rows) == 2

    async def test_prunes_to_the_newest_max_versions(self, table):
        for i in range(versions.MAX_VERSIONS + 5):
            table.add(html=_page(f"old {i}"), source="regenerate")
        oldest_ids = {r["id"] for r in table.rows[:6]}
        assert await versions.snapshot("ws-1", LIVE_HTML, "regenerate")
        assert len(table.rows) == versions.MAX_VERSIONS
        assert not oldest_ids & {r["id"] for r in table.rows}
        assert table.rows[-1]["html"] == LIVE_HTML

    async def test_prune_never_touches_another_website(self, table):
        for i in range(versions.MAX_VERSIONS + 3):
            table.add(website_id="ws-2", html=_page(f"other {i}"), source="regenerate")
        await versions.snapshot("ws-1", LIVE_HTML, "regenerate")
        assert sum(r["website_id"] == "ws-2" for r in table.rows) == versions.MAX_VERSIONS + 3

    async def test_a_storage_failure_never_raises_into_the_save(self, monkeypatch):
        async def boom(*_a, **_k):
            raise RuntimeError("supabase is down")

        monkeypatch.setattr(versions, "_select", boom)
        monkeypatch.setattr(versions, "_insert", boom)
        assert await versions.snapshot("ws-1", LIVE_HTML, "manual_save") is None

    async def test_a_prune_failure_still_keeps_the_snapshot(self, table, monkeypatch):
        async def boom(_ids):
            raise RuntimeError("delete failed")

        for i in range(versions.MAX_VERSIONS + 1):
            table.add(html=_page(f"old {i}"), source="regenerate")
        monkeypatch.setattr(versions, "_delete", boom)
        assert await versions.snapshot("ws-1", LIVE_HTML, "regenerate")

    async def test_unknown_source_falls_back_and_label_is_clamped(self, table):
        stored = await versions.snapshot("ws-1", LIVE_HTML, "nonsense", label="x" * 200)
        assert stored["source"] == "manual_save"
        assert len(table.rows[0]["label"]) == versions.LABEL_MAX


class TestReads:
    async def test_list_is_newest_first_and_carries_no_html(self, table):
        table.add(html=_page("1"))
        table.add(html=_page("2"))
        rows = await versions.list_versions("ws-1")
        assert [r["id"] for r in rows] == ["v-2", "v-1"]
        assert all("html" not in r for r in rows)

    async def test_a_version_is_only_readable_through_its_own_website(self, table):
        row = table.add(website_id="ws-2")
        assert await versions.get_version("ws-1", row["id"]) is None
        assert (await versions.get_version("ws-2", row["id"]))["html"] == OLD_HTML


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

def _row(**overrides):
    row = {
        "id": "ws-1",
        "user_id": "test-user-id-12345",
        "name": "Kedai Ali",
        "subdomain": "kedaiali",
        "status": "published",
        "html_content": LIVE_HTML,
    }
    row.update(overrides)
    return row


@pytest.fixture
def client():
    # The router is mounted under /websites by api/v1/router.py; mounting it
    # here keeps these tests about this router alone.
    app = FastAPI()
    app.include_router(endpoint.router, prefix="/api/v1/websites")
    return TestClient(app)


@pytest.fixture
def patches(table):
    with (
        patch.object(endpoint.supabase_service, "get_website",
                     new=AsyncMock(return_value=_row())) as get_website,
        patch.object(endpoint.supabase_service, "update_website",
                     new=AsyncMock(return_value=True)) as update_website,
        patch.object(endpoint.storage_service, "publish_website",
                     new=AsyncMock(return_value="https://kedaiali.binaapp.my")) as publish_website,
        patch.object(endpoint, "_fetch_serving_snapshot",
                     new=AsyncMock(return_value=None)) as fetch_snapshot,
    ):
        yield {
            "get_website": get_website,
            "update_website": update_website,
            "publish_website": publish_website,
            "fetch_snapshot": fetch_snapshot,
            "table": table,
        }


BASE = "/api/v1/websites/ws-1/versions"


class TestGates:
    @pytest.mark.parametrize("method,path", [
        ("get", BASE),
        ("get", f"{BASE}/v-1"),
        ("patch", f"{BASE}/v-1"),
        ("post", f"{BASE}/v-1/restore"),
    ])
    def test_every_route_requires_auth(self, client, patches, method, path):
        kwargs = {"json": {"label": "x"}} if method == "patch" else {}
        assert getattr(client, method)(path, **kwargs).status_code in (401, 403)

    @pytest.mark.parametrize("method,path", [
        ("get", BASE),
        ("get", f"{BASE}/v-1"),
        ("patch", f"{BASE}/v-1"),
        ("post", f"{BASE}/v-1/restore"),
    ])
    def test_someone_elses_site_is_403(self, client, auth_headers, patches, method, path):
        patches["table"].add()
        patches["get_website"].return_value = _row(user_id="someone-else")
        kwargs = {"json": {"label": "x"}} if method == "patch" else {}
        resp = getattr(client, method)(path, headers=auth_headers, **kwargs)
        assert resp.status_code == 403
        assert not patches["publish_website"].called
        assert not patches["update_website"].called

    def test_missing_site_is_404(self, client, auth_headers, patches):
        patches["get_website"].return_value = None
        assert client.get(BASE, headers=auth_headers).status_code == 404

    def test_missing_version_is_404(self, client, auth_headers, patches):
        assert client.get(f"{BASE}/nope", headers=auth_headers).status_code == 404
        assert client.post(f"{BASE}/nope/restore", headers=auth_headers).status_code == 404

    def test_a_version_of_another_site_is_404(self, client, auth_headers, patches):
        other = patches["table"].add(website_id="ws-2")
        resp = client.post(f"{BASE}/{other['id']}/restore", headers=auth_headers)
        assert resp.status_code == 404
        assert not patches["publish_website"].called


class TestListAndPreview:
    def test_list_returns_metadata_only(self, client, auth_headers, patches):
        patches["table"].add(source="regenerate")
        body = client.get(BASE, headers=auth_headers).json()
        assert body["success"] is True
        assert body["max_versions"] == versions.MAX_VERSIONS
        (version,) = body["versions"]
        assert version["source"] == "regenerate"
        assert "html" not in version and "content_hash" not in version

    def test_preview_returns_the_html(self, client, auth_headers, patches):
        row = patches["table"].add()
        body = client.get(f"{BASE}/{row['id']}", headers=auth_headers).json()
        assert body["html_content"] == OLD_HTML
        assert "html" not in body["version"]

    def test_label_is_saved_and_cleared(self, client, auth_headers, patches):
        row = patches["table"].add()
        resp = client.patch(f"{BASE}/{row['id']}", headers=auth_headers, json={"label": " Sebelum Raya "})
        assert resp.json()["version"]["label"] == "Sebelum Raya"
        resp = client.patch(f"{BASE}/{row['id']}", headers=auth_headers, json={"label": ""})
        assert resp.json()["version"]["label"] is None

    def test_storage_failure_is_a_503_not_a_500(self, client, auth_headers, patches, monkeypatch):
        async def boom(_params):
            raise RuntimeError("down")

        monkeypatch.setattr(versions, "_select", boom)
        assert client.get(BASE, headers=auth_headers).status_code == 503


class TestRestore:
    def test_restores_publishes_and_saves_the_current_page_first(self, client, auth_headers, patches):
        table = patches["table"]
        row = table.add(html=OLD_HTML, source="regenerate")

        resp = client.post(f"{BASE}/{row['id']}/restore", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["changed"] is True
        assert body["live_site_updated"] is True
        assert body["html_content"] == OLD_HTML

        assert patches["publish_website"].call_args.kwargs["html_content"] == OLD_HTML
        assert patches["update_website"].call_args.args[1]["html_content"] == OLD_HTML

        # The page that was live is now a version — the restore is undoable.
        undo = [r for r in table.rows if r["source"] == "restore"]
        assert len(undo) == 1 and undo[0]["html"] == LIVE_HTML
        assert body["undo_version_id"] == undo[0]["id"]

    def test_the_live_snapshot_is_what_gets_saved_when_it_differs_from_the_db(
        self, client, auth_headers, patches
    ):
        served = _page("<h1>Yang pelawat nampak</h1>")
        patches["fetch_snapshot"].return_value = served
        row = patches["table"].add(html=OLD_HTML, source="regenerate")

        client.post(f"{BASE}/{row['id']}/restore", headers=auth_headers)
        saved = {r["html"] for r in patches["table"].rows if r["source"] == "restore"}
        assert served in saved

    def test_a_draft_is_restored_without_touching_storage(self, client, auth_headers, patches):
        patches["get_website"].return_value = _row(status="draft")
        row = patches["table"].add(html=OLD_HTML, source="regenerate")
        body = client.post(f"{BASE}/{row['id']}/restore", headers=auth_headers).json()
        assert body["changed"] is True and body["live_site_updated"] is False
        assert not patches["publish_website"].called
        assert not patches["fetch_snapshot"].called
        assert patches["update_website"].called

    def test_an_unbalanced_version_is_refused_and_nothing_is_written(
        self, client, auth_headers, patches
    ):
        row = patches["table"].add(html=TRUNCATED_HTML)
        resp = client.post(f"{BASE}/{row['id']}/restore", headers=auth_headers)
        assert resp.status_code == 422
        assert resp.json()["detail"]["error"] == "version_html_unbalanced"
        assert not patches["publish_website"].called
        assert not patches["update_website"].called

    def test_restoring_the_page_already_live_changes_nothing(self, client, auth_headers, patches):
        row = patches["table"].add(html=LIVE_HTML)
        body = client.post(f"{BASE}/{row['id']}/restore", headers=auth_headers).json()
        assert body["changed"] is False
        assert not patches["publish_website"].called
        assert not patches["update_website"].called
        assert len(patches["table"].rows) == 1

    def test_refused_while_a_generation_is_running(self, client, auth_headers, patches):
        patches["get_website"].return_value = _row(status="generating")
        row = patches["table"].add()
        resp = client.post(f"{BASE}/{row['id']}/restore", headers=auth_headers)
        assert resp.status_code == 409
        assert not patches["update_website"].called

    def test_storage_failure_is_reported_honestly(self, client, auth_headers, patches):
        patches["publish_website"].side_effect = RuntimeError("storage down")
        row = patches["table"].add(html=OLD_HTML)
        body = client.post(f"{BASE}/{row['id']}/restore", headers=auth_headers).json()
        assert body["live_site_updated"] is False
        assert body["warning"] == "storage_refresh_failed"
        assert "belum dikemas kini" in body["message"]

    def test_a_rejected_db_write_is_an_error(self, client, auth_headers, patches):
        patches["update_website"].return_value = False
        row = patches["table"].add(html=OLD_HTML)
        assert client.post(f"{BASE}/{row['id']}/restore", headers=auth_headers).status_code == 500

    def test_restore_never_touches_quota(self, client, auth_headers, patches):
        row = patches["table"].add(html=OLD_HTML)
        with patch(
            "app.services.subscription_service.subscription_service.check_limit",
            new=AsyncMock(side_effect=AssertionError("quota touched")),
        ):
            assert client.post(f"{BASE}/{row['id']}/restore", headers=auth_headers).status_code == 200


# ---------------------------------------------------------------------------
# Hooks: the overwrite paths snapshot the page they are about to replace.
# ---------------------------------------------------------------------------

class TestHooks:
    def test_editor_save_snapshots_the_previous_page(self, auth_headers, table):
        from app.main import app

        new_html = _page("<h1>Baru</h1>")
        with (
            patch("app.api.v1.endpoints.websites.supabase_service.get_website",
                  new=AsyncMock(return_value=_row(status="draft"))),
            patch("app.api.v1.endpoints.websites.supabase_service.update_website",
                  new=AsyncMock(return_value=True)),
        ):
            resp = TestClient(app).put(
                "/api/v1/websites/ws-1", headers=auth_headers, json={"html_content": new_html}
            )
        assert resp.status_code == 200
        assert [(r["source"], r["html"]) for r in table.rows] == [("manual_save", LIVE_HTML)]

    def test_editor_save_succeeds_when_history_is_down(self, auth_headers, monkeypatch):
        from app.main import app

        async def boom(*_a, **_k):
            raise RuntimeError("down")

        monkeypatch.setattr(versions, "_select", boom)
        with (
            patch("app.api.v1.endpoints.websites.supabase_service.get_website",
                  new=AsyncMock(return_value=_row(status="draft"))),
            patch("app.api.v1.endpoints.websites.supabase_service.update_website",
                  new=AsyncMock(return_value=True)),
        ):
            resp = TestClient(app).put(
                "/api/v1/websites/ws-1", headers=auth_headers, json={"html_content": _page("x")}
            )
        assert resp.status_code == 200

    def test_theme_change_snapshots_the_old_colours(self, auth_headers, table):
        from app.main import app

        themed = (
            "<!DOCTYPE html><html><head><style>:root{--primary-color:#EA580C;"
            "--bg-color:#FFFBF5;--text-color:#1C1917;}</style></head>"
            '<body><div style="background:#EA580C">Pesan</div></body></html>'
        )
        with (
            patch("app.api.v1.endpoints.design_studio.supabase_service.get_website",
                  new=AsyncMock(return_value=_row(status="draft", html_content=themed))),
            patch("app.api.v1.endpoints.design_studio.supabase_service.update_website",
                  new=AsyncMock(return_value=True)),
        ):
            resp = TestClient(app).patch(
                "/api/v1/websites/ws-1/theme", headers=auth_headers, json={"palette": "blue"}
            )
        assert resp.status_code == 200 and resp.json()["changed"] is True
        assert [(r["source"], r["html"]) for r in table.rows] == [("theme", themed)]
