"""Served-page freshness: a republished site must be what the next visitor
sees, and a browser must revalidate instead of holding a five-minute copy.

Background: a merchant published a site from the create page, the hero
video landed ~90s later and was applied to storage — but their phone kept
showing the pre-video page: the middleware held a 60s in-process copy and
the response carried Cache-Control: max-age=300.
"""

from unittest.mock import AsyncMock, patch

from starlette.requests import Request

from app.middleware import subdomain as mw
from app.services import storage_service as ss


def _request(headers=None):
    raw = [(k.lower().encode(), v.encode()) for k, v in (headers or {}).items()]
    return Request({"type": "http", "method": "GET", "headers": raw, "path": "/"})


class TestInvalidateSiteCache:
    def test_drops_both_caches_for_the_subdomain(self):
        mw._cache_set(mw._storage_html_cache, "kedai", "<html>old</html>")
        mw._cache_set(mw._website_lookup_cache, "kedai", {"id": "ws-1"})
        mw._cache_set(mw._storage_html_cache, "other", "<html>keep</html>")

        mw.invalidate_site_cache("kedai")

        assert mw._cache_get(mw._storage_html_cache, "kedai") is None
        assert mw._cache_get(mw._website_lookup_cache, "kedai") is None
        assert mw._cache_get(mw._storage_html_cache, "other") == "<html>keep</html>"

    def test_unknown_or_blank_subdomain_is_a_noop(self):
        mw.invalidate_site_cache("never-cached")
        mw.invalidate_site_cache("")


class TestPageResponseFreshness:
    def test_merchant_page_is_no_cache_with_an_etag(self):
        resp = mw._page_response("<html>v1</html>", _request(), "ws-1")
        assert resp.status_code == 200
        assert resp.headers["cache-control"] == "no-cache"
        assert resp.headers["etag"].startswith('"') and resp.headers["etag"].endswith('"')
        assert resp.headers["content-type"].startswith("text/html")

    def test_etag_changes_with_the_page(self):
        a = mw._page_response("<html>v1</html>", _request(), "ws-1").headers["etag"]
        b = mw._page_response("<html>v2</html>", _request(), "ws-1").headers["etag"]
        assert a != b

    def test_matching_if_none_match_gets_a_304(self):
        etag = mw._page_response("<html>v1</html>", _request(), "ws-1").headers["etag"]
        resp = mw._page_response("<html>v1</html>", _request({"If-None-Match": etag}), "ws-1")
        assert resp.status_code == 304
        assert resp.headers["etag"] == etag
        assert resp.body == b""

    def test_stale_if_none_match_gets_the_new_page(self):
        old = mw._page_response("<html>v1</html>", _request(), "ws-1").headers["etag"]
        resp = mw._page_response("<html>v2</html>", _request({"If-None-Match": old}), "ws-1")
        assert resp.status_code == 200
        assert b"v2" in resp.body

    def test_weak_and_list_forms_of_if_none_match_still_match(self):
        etag = mw._page_response("<html>v1</html>", _request(), "ws-1").headers["etag"]
        resp = mw._page_response(
            "<html>v1</html>", _request({"If-None-Match": f'"other", {etag}'}), "ws-1"
        )
        assert resp.status_code == 304

    def test_weak_etag_echoed_by_a_gzipping_proxy_still_matches(self):
        # Cloudflare/Render compress the body and rewrite "abc" → W/"abc";
        # browsers send the weak form back in If-None-Match.
        etag = mw._page_response("<html>v1</html>", _request(), "ws-1").headers["etag"]
        resp = mw._page_response(
            "<html>v1</html>", _request({"If-None-Match": "W/" + etag}), "ws-1"
        )
        assert resp.status_code == 304

    def test_legacy_page_without_a_row_keeps_the_long_max_age(self):
        resp = mw._page_response("<html>legacy</html>", _request(), None)
        assert resp.headers["cache-control"] == "public, max-age=3600"
        assert "etag" in resp.headers


class TestPublishInvalidates:
    async def test_upload_website_drops_the_served_copy(self):
        mw._cache_set(mw._storage_html_cache, "kedai", "<html>old</html>")
        with (
            patch.object(ss.storage_service.supabase, "upload_file", new=AsyncMock(return_value="https://x/1")),
            patch.object(ss.storage_service.supabase, "delete_file", new=AsyncMock(return_value=True)),
        ):
            url = await ss.storage_service.upload_website("user-1", "kedai", "<html>new</html>")
        assert url.startswith("https://kedai.")
        assert mw._cache_get(mw._storage_html_cache, "kedai") is None

    async def test_invalidation_failure_never_breaks_a_publish(self):
        with (
            patch.object(ss.storage_service.supabase, "upload_file", new=AsyncMock(return_value="https://x/1")),
            patch.object(ss.storage_service.supabase, "delete_file", new=AsyncMock(return_value=True)),
            patch.object(mw, "invalidate_site_cache", side_effect=RuntimeError("boom")),
        ):
            url = await ss.storage_service.upload_website("user-1", "kedai", "<html>new</html>")
        assert url.startswith("https://kedai.")


class _FakeResponse:
    def __init__(self, status_code: int, text: str = ""):
        self.status_code = status_code
        self.text = text


class _FakeClient:
    """Stands in for httpx.AsyncClient and records every URL requested."""

    urls: list = []
    responses: dict = {}

    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def get(self, url, **kwargs):
        _FakeClient.urls.append(url)
        for prefix, resp in _FakeClient.responses.items():
            if url.startswith(prefix):
                return resp
        return _FakeResponse(404)


class TestStorageCdnVersioning:
    """The storage object is served with `cache-control: public, max-age=3600`
    and the Smart CDN takes up to a minute to notice an upsert. Dropping the
    in-process copy alone was not enough: the next visitor's fetch still came
    back from the CDN with the pre-publish page (mibo: video injected and
    uploaded at 12:43:14, the 12:44:00 visit served the page without it)."""

    def setup_method(self):
        mw._storage_versions.clear()
        mw._storage_html_cache.clear()
        _FakeClient.urls = []
        _FakeClient.responses = {}

    def test_never_published_in_this_process_uses_the_plain_cdn_url(self):
        with patch.object(mw.settings, "SUPABASE_URL", "https://sb.test"):
            url = mw.storage_object_url("kedai", "kedai/index.html")
        assert url == "https://sb.test/storage/v1/object/public/websites/kedai/index.html"

    def test_a_republish_gives_the_object_a_new_cdn_key(self):
        with patch.object(mw.settings, "SUPABASE_URL", "https://sb.test"):
            mw.invalidate_site_cache("kedai")
            first = mw.storage_object_url("kedai", "kedai/index.html")
            mw.invalidate_site_cache("kedai")
            second = mw.storage_object_url("kedai", "kedai/index.html")
            other = mw.storage_object_url("other", "other/index.html")
        assert first.startswith("https://sb.test/storage/v1/object/public/websites/kedai/index.html?v=")
        assert second != first
        assert "?" not in other, "only the republished site is versioned"

    async def test_fetch_after_a_publish_bypasses_the_cdn_copy(self):
        _FakeClient.responses = {"https://sb.test/storage/v1/object/public/websites/kedai/index.html?v=": _FakeResponse(200, "<html>new</html>")}
        with (
            patch.object(mw.settings, "SUPABASE_URL", "https://sb.test"),
            patch.object(mw.httpx, "AsyncClient", _FakeClient),
        ):
            mw.invalidate_site_cache("kedai")
            html = await mw._fetch_html_from_storage("kedai")
        assert html == "<html>new</html>"
        assert len(_FakeClient.urls) == 1
        assert "?v=" in _FakeClient.urls[0]
        # and the fresh copy is what the in-process cache now holds
        assert mw._cache_get(mw._storage_html_cache, "kedai") == "<html>new</html>"

    async def test_legacy_path_is_versioned_too(self):
        _FakeClient.responses = {"https://sb.test/storage/v1/object/public/websites/demo-user/kedai/index.html?v=": _FakeResponse(200, "<html>legacy</html>")}
        with (
            patch.object(mw.settings, "SUPABASE_URL", "https://sb.test"),
            patch.object(mw.httpx, "AsyncClient", _FakeClient),
        ):
            mw.invalidate_site_cache("kedai")
            html = await mw._fetch_html_from_storage("kedai")
        assert html == "<html>legacy</html>"
        assert all("?v=" in u for u in _FakeClient.urls)

    def test_version_table_is_bounded(self):
        for i in range(mw._SUBDOMAIN_CACHE_MAX_ENTRIES + 5):
            mw.invalidate_site_cache(f"site-{i}")
        assert len(mw._storage_versions) == mw._SUBDOMAIN_CACHE_MAX_ENTRIES
        assert "site-0" not in mw._storage_versions
        assert f"site-{mw._SUBDOMAIN_CACHE_MAX_ENTRIES + 4}" in mw._storage_versions


class TestSnapshotReadsAreNeverCdnStale:
    """Edit paths (hero video, theme, contact) read the live snapshot with a
    constant `?cb=hero-video` style key — which the CDN then cached for an
    hour, so the second edit within the hour rewrote a stale page."""

    def setup_method(self):
        _FakeClient.urls = []
        _FakeClient.responses = {}

    async def test_each_read_uses_a_fresh_cache_key(self):
        from app.services import serving_snapshot as snap

        _FakeClient.responses = {"https://sb.test/storage/v1/object/public/websites/kedai/index.html?cb=hero-video-": _FakeResponse(200, "<html>live</html>")}
        with (
            patch.object(snap.settings, "SUPABASE_URL", "https://sb.test"),
            patch.object(snap.httpx, "AsyncClient", _FakeClient),
        ):
            a = await snap.fetch_published_snapshot("kedai", cache_bust="hero-video")
            b = await snap.fetch_published_snapshot("kedai", cache_bust="hero-video")
        assert a == b == "<html>live</html>"
        assert len(_FakeClient.urls) == 2
        assert _FakeClient.urls[0] != _FakeClient.urls[1]
        assert all("?cb=hero-video-" in u for u in _FakeClient.urls)
