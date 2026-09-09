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
