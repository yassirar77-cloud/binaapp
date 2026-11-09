"""binaapp.my + mysyg.com: a site lives on the domain its owner picked."""
import asyncio
from types import SimpleNamespace
from unittest.mock import patch

from app.services.site_domains import (
    normalize_site_domain,
    resolve_site_domain,
    site_domains,
    site_url,
    split_host,
)


def test_both_domains_allowed_main_first():
    assert site_domains()[:2] == ["binaapp.my", "mysyg.com"]


def test_normalize_and_resolve():
    assert normalize_site_domain("MYSYG.COM") == "mysyg.com"
    assert normalize_site_domain(".mysyg.com") == "mysyg.com"
    assert normalize_site_domain("evil.com") is None
    assert resolve_site_domain(None) == "binaapp.my"
    assert resolve_site_domain("evil.com") == "binaapp.my"


def test_site_url():
    assert site_url("kedai", "mysyg.com") == "https://kedai.mysyg.com"
    assert site_url("kedai", None) == "https://kedai.binaapp.my"


def test_split_host():
    assert split_host("kedai.mysyg.com") == ("kedai", "mysyg.com")
    assert split_host("Kedai.BinaApp.my:443") == ("kedai", "binaapp.my")
    assert split_host("mysyg.com") is None
    assert split_host("a.b.mysyg.com") is None
    assert split_host("kedai.mysyg.com.evil.io") is None


def _request(host, path="/"):
    return SimpleNamespace(
        headers={"host": host},
        url=SimpleNamespace(path=path, query=""),
    )


def _run_middleware(host, row, path="/"):
    from app.middleware import subdomain as mw

    mw._website_lookup_cache.clear()

    async def lookup(_sb, _sub):
        return [row]

    async def call_next(_req):
        return "NEXT"

    with patch.object(mw, "_get_supabase_client", return_value=object()), \
         patch.object(mw, "_lookup_website_row", side_effect=lookup):
        return asyncio.run(mw.subdomain_middleware(_request(host, path), call_next))


def test_wrong_domain_redirects_to_chosen_one():
    row = {"id": "w1", "user_id": "u1", "name": "Kedai", "site_domain": "mysyg.com"}
    resp = _run_middleware("kedai.binaapp.my", row, "/menu")
    assert resp.status_code == 302
    assert resp.headers["location"] == "https://kedai.mysyg.com/menu"


def test_row_without_domain_lives_on_binaapp():
    row = {"id": "w1", "user_id": "u1", "name": "Kedai"}
    resp = _run_middleware("kedai.mysyg.com", row)
    assert resp.status_code == 302
    assert resp.headers["location"] == "https://kedai.binaapp.my/"


def test_non_site_host_falls_through():
    from app.middleware import subdomain as mw

    async def call_next(_req):
        return "NEXT"

    assert asyncio.run(mw.subdomain_middleware(_request("api.binaapp.my"), call_next)) == "NEXT"
    assert asyncio.run(mw.subdomain_middleware(_request("binaapp-backend.onrender.com"), call_next)) == "NEXT"
