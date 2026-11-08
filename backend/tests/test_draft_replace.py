"""'Terbitkan ke subdomain': publish one of my drafts over one of my live
sites — swap the live page, never create a second row, never promote the
draft, never charge the quota."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.draft_replace import resolve_replace_request

USER = "u-1"
DRAFT_ID = "a1df9b79-abc4-4ea2-a0e5-40d81bdff709"
LIVE_ID = "3103bded-f220-419e-bc1d-7df5fab12c80"
DRAFT_HTML = (
    "<!DOCTYPE html><html><head><title>AGP</title></head><body><h1>Ayam Gepuk Panglima</h1>"
    + "<p>menu</p>" * 80
    + f'<div data-website-id="{DRAFT_ID}"></div><script src="/static/widgets/chat-widget.js" data-website-id="{DRAFT_ID}"></script>'
    + "</body></html>"
)


class _Table:
    def __init__(self, rows):
        self.rows, self._id = rows, None

    def select(self, *a, **k):
        return self

    def eq(self, col, val):
        self._id = val
        return self

    def limit(self, n):
        return self

    def execute(self):
        row = self.rows.get(self._id)
        return MagicMock(data=[row] if row else [])


class _Supa:
    def __init__(self, rows):
        self.rows = rows

    def table(self, name):
        return _Table(self.rows)


def _rows(**over):
    draft = {"id": DRAFT_ID, "user_id": USER, "status": "pending_payment", "subdomain": f"draft-{DRAFT_ID}",
             "html_content": DRAFT_HTML, "business_name": "Ayam Gepuk Panglima", "name": None,
             "description": "Ayam gepuk di Klang", "business_type": "food",
             "location_address": "No. 44-1, Jalan Bayu Impian 4A/KS9, Kota Bayu Emas, 41200 Klang, Selangor",
             "hero_image_prompt": "ayam gepuk"}
    live = {"id": LIVE_ID, "user_id": USER, "status": "published", "subdomain": "agp", "business_name": "Ayam Gepuk Panglima", "name": "agp"}
    draft.update(over.get("draft", {}))
    live.update(over.get("live", {}))
    return {DRAFT_ID: draft, LIVE_ID: live}


MENU = [{"name": "Set A – Ayam Gepuk", "price": "12.50", "category": "Set Ayam"}]


class TestResolve:
    def test_builds_a_republish_of_the_live_row(self):
        with patch("app.services.menu_persistence.load_menu_items", return_value=MENU):
            fields, err = resolve_replace_request(_Supa(_rows()), USER, DRAFT_ID, LIVE_ID)
        assert err is None
        assert fields["website_id"] == LIVE_ID and fields["subdomain"] == "agp" and fields["replace_existing"] is True
        assert DRAFT_ID not in fields["html_content"] and fields["html_content"].count(LIVE_ID) == 2
        assert fields["menu_items"] == MENU and fields["address"].startswith("No. 44-1")
        assert fields["business_name"] == "Ayam Gepuk Panglima" and fields["description"] == "Ayam gepuk di Klang"

    @pytest.mark.parametrize("over,status,code", [
        ({"draft": {"user_id": "someone-else"}}, 403, "replace_not_owner"),
        ({"live": {"user_id": "someone-else"}}, 403, "replace_not_owner"),
        ({"draft": {"status": "published"}}, 409, "replace_not_a_draft"),
        ({"live": {"status": "pending_payment"}}, 409, "replace_target_not_live"),
        ({"live": {"subdomain": "draft-x"}}, 409, "replace_target_not_live"),
        ({"draft": {"html_content": "<p>x</p>"}}, 409, "replace_draft_empty"),
    ])
    def test_refusals(self, over, status, code):
        fields, err = resolve_replace_request(_Supa(_rows(**over)), USER, DRAFT_ID, LIVE_ID)
        assert fields is None and err[0] == status and err[1]["error"] == code

    def test_missing_rows_and_same_row(self):
        assert resolve_replace_request(_Supa({}), USER, DRAFT_ID, LIVE_ID)[1][0] == 404
        assert resolve_replace_request(_Supa(_rows()), USER, LIVE_ID, LIVE_ID)[1][0] == 400


def _publish_mocks(test_user_id):
    existing = MagicMock(data=[{"id": LIVE_ID, "user_id": test_user_id, "status": "published", "subdomain": "agp"}])
    table = MagicMock()
    for m in ("select", "insert", "update", "upsert", "delete", "eq", "neq", "limit", "single", "order"):
        getattr(table, m).return_value = table
    table.execute.return_value = existing
    supa = MagicMock()
    supa.table.return_value = table
    storage = MagicMock(status_code=201, text="")
    client = MagicMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)
    client.post = AsyncMock(return_value=storage)
    return supa, client


def test_endpoint_republishes_the_live_row_without_quota(client, auth_headers, test_user_id):
    supa, http = _publish_mocks(test_user_id)
    html = DRAFT_HTML.replace(DRAFT_ID, LIVE_ID)
    fields = {"html_content": html, "subdomain": "agp", "website_id": LIVE_ID, "project_name": "Ayam Gepuk Panglima",
              "business_name": "Ayam Gepuk Panglima", "description": "Ayam gepuk di Klang", "business_type": "food",
              "hero_image_prompt": None, "menu_items": [], "replace_existing": True}
    check_limit = AsyncMock(return_value={"allowed": True})
    with (
        patch("app.main.supabase", supa),
        patch("app.services.draft_replace.resolve_replace_request", return_value=(fields, None)) as resolve,
        patch("app.main.sub_service.check_limit", new=check_limit),
        patch("app.main.sub_service.increment_usage", new=AsyncMock(return_value=True)),
        patch("app.services.plan_features.can_publish_subdomain", new=AsyncMock(return_value=True)),
        patch("app.main.supabase_service.is_email_verified", new=AsyncMock(return_value=True)),
        patch("app.main.httpx.AsyncClient", return_value=http),
    ):
        resp = client.post("/api/publish", headers=auth_headers, json={
            "draft_id": DRAFT_ID, "replace_website_id": LIVE_ID,
            "html_content": "<html>client html is ignored</html>", "subdomain": "evil",
        })
    assert resp.status_code == 200, resp.text
    resolve.assert_called_once()
    assert resolve.call_args.args[2:] == (DRAFT_ID, LIVE_ID)
    check_limit.assert_not_called()  # a republish of an existing site, not a new one
    upserts = [c.args[0] for c in supa.table.return_value.upsert.call_args_list if c.args and isinstance(c.args[0], dict)]
    row = next(u for u in upserts if u.get("subdomain"))
    assert row["id"] == LIVE_ID and row["subdomain"] == "agp" and row["status"] == "published"
    uploaded = http.post.call_args_list[0]
    assert "/websites/agp/index.html" in str(uploaded)


def test_endpoint_returns_the_refusal(client, auth_headers):
    with (
        patch("app.main.supabase", MagicMock()),
        patch("app.services.draft_replace.resolve_replace_request",
              return_value=(None, (403, {"success": False, "error": "replace_not_owner"}))),
    ):
        resp = client.post("/api/publish", headers=auth_headers, json={"draft_id": DRAFT_ID, "replace_website_id": LIVE_ID})
    assert resp.status_code == 403 and resp.json()["error"] == "replace_not_owner"


class TestListedDrafts:
    def _list(self, client, auth_headers, rows):
        with patch("app.api.v1.endpoints.websites.supabase_service.get_user_websites", new=AsyncMock(return_value=rows)):
            resp = client.get("/api/v1/websites/", headers=auth_headers)
        assert resp.status_code == 200, resp.text
        return resp.json()

    def _row(self, i, status, sub=None):
        return {"id": f"w{i}", "status": status, "subdomain": sub or f"draft-w{i}", "business_name": "AGP",
                "created_at": f"2026-11-0{i}T10:00:00+00:00"}

    def test_user_without_a_live_site_sees_no_generated_drafts(self, client, auth_headers):
        assert self._list(client, auth_headers, [self._row(1, "pending_payment")]) == []

    def test_user_with_a_live_site_sees_their_newest_drafts_flagged(self, client, auth_headers):
        rows = [self._row(1, "published", "agp")] + [self._row(i, "pending_payment") for i in range(2, 9)]
        out = self._list(client, auth_headers, rows)
        drafts = [w for w in out if w["replaceable_draft"]]
        assert {w["id"] for w in drafts} == {"w8", "w7", "w6", "w5", "w4"}  # the newest five
        assert all(w["status"] == "draft" and w["subdomain"] is None and w["full_url"] is None for w in drafts)
        live = next(w for w in out if w["id"] == "w1")
        assert live["replaceable_draft"] is False and live["subdomain"] == "agp"

    def test_publishable_drafts_come_first_then_newest_site(self, client, auth_headers):
        # agp's account: ~150 sites came back in PostgREST's arbitrary order
        # and the draft to publish sat mid-list on mobile.
        rows = [self._row(1, "published", "agp"), self._row(3, "pending_payment"),
                self._row(2, "published", "kuih"), self._row(4, "pending_payment")]
        rows[0]["updated_at"] = "2026-11-07T16:41:00+00:00"  # just edited
        out = self._list(client, auth_headers, rows)
        assert [w["id"] for w in out] == ["w4", "w3", "w1", "w2"]

    def test_list_does_not_select_page_html(self, client, auth_headers):
        get = AsyncMock(return_value=[self._row(1, "published", "agp")])
        with patch("app.api.v1.endpoints.websites.supabase_service.get_user_websites", new=get):
            client.get("/api/v1/websites/", headers=auth_headers)
        columns = get.call_args.kwargs.get("columns") or ""
        assert "html_content" not in columns and "status" in columns and "subdomain" in columns


class TestHeroVideoCarriedOver:
    """agp: publishing the draft dropped the hero video the merchant had put
    on the live page (the clip lives in the page HTML; a draft has none)."""

    HERO_PAGE = (
        "<!DOCTYPE html><html><head><title>AGP</title></head><body>"
        '<section id="hero" class="relative min-h-[70vh] overflow-hidden"><h1>Ayam Gepuk Panglima</h1>'
        "<p>Makin Pedas, Rasa Makin Padu.</p></section>"
        + "<p>menu</p>" * 80
        + f'<div data-website-id="{DRAFT_ID}"></div></body></html>'
    )
    CLIP = "https://res.cloudinary.com/dpisgucmw/video/upload/v1/binaapp/hero_videos/agp.mp4"

    def _live_with_clip(self):
        from app.services.hero_video_patcher import apply_hero_video, build_settings
        return apply_hero_video(self.HERO_PAGE, build_settings(video_url=self.CLIP, overlay="dark", text_mode="light")).html

    def test_live_clip_and_look_go_onto_the_draft(self):
        from app.services.hero_video_patcher import detect_hero_video
        rows = _rows(draft={"html_content": self.HERO_PAGE}, live={"html_content": self._live_with_clip()})
        with patch("app.services.menu_persistence.load_menu_items", return_value=[]):
            fields, err = resolve_replace_request(_Supa(rows), USER, DRAFT_ID, LIVE_ID)
        assert err is None
        video = detect_hero_video(fields["html_content"])
        assert video and video["video_url"].endswith("agp.mp4")
        assert video["overlay"] == "dark" and video["text_mode"] == "light"
        assert "Makin Pedas, Rasa Makin Padu." in fields["html_content"]

    def test_no_clip_on_the_live_page_leaves_the_draft_alone(self):
        rows = _rows(draft={"html_content": self.HERO_PAGE}, live={"html_content": self.HERO_PAGE})
        with patch("app.services.menu_persistence.load_menu_items", return_value=[]):
            fields, _ = resolve_replace_request(_Supa(rows), USER, DRAFT_ID, LIVE_ID)
        assert "binaapp:hero-video" not in fields["html_content"]

    def test_a_broken_live_page_never_blocks_the_publish(self):
        from app.services.draft_replace import carry_hero_video
        with patch("app.services.hero_video_patcher.detect_hero_video", side_effect=RuntimeError("boom")):
            assert carry_hero_video("<html>", self.HERO_PAGE) == self.HERO_PAGE
