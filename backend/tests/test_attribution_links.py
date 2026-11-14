"""Footer credit links on merchant sites are tagged at serve time."""
from app.services.attribution_links import footer_credit_url, tag_binaapp_links

TAGGED = "https://binaapp.my/?utm_source=site-footer&amp;utm_medium=referral&amp;utm_campaign=ali"


def test_bare_home_link_is_tagged_with_the_subdomain():
    html = '<p>Dibina dengan <a href="https://binaapp.my" target="_blank">BinaApp</a></p>'
    assert f'href="{TAGGED}"' in tag_binaapp_links(html, "ali")


def test_variants_trailing_slash_www_and_single_quotes():
    for href in ('"https://binaapp.my/"', '"https://www.binaapp.my"', "'https://binaapp.my'"):
        out = tag_binaapp_links(f"<a href={href}>BinaApp</a>", "ali")
        assert TAGGED in out


def test_deep_links_and_other_sites_are_untouched():
    html = (
        '<a href="https://binaapp.my/polisi-privasi">Polisi</a>'
        '<a href="https://ali.binaapp.my">Kedai</a>'
        '<a href="https://notbinaapp.my">x</a>'
        '<img src="https://binaapp.my/logo.png">'
    )
    assert tag_binaapp_links(html, "ali") == html


def test_idempotent():
    html = '<a href="https://binaapp.my">BinaApp</a>'
    once = tag_binaapp_links(html, "ali")
    assert tag_binaapp_links(once, "ali") == once


def test_subdomain_cannot_inject_markup():
    url = footer_credit_url('ali"><script>')
    assert '"' not in url and "<" not in url
    assert url.endswith("utm_campaign=aliscript")


def test_no_subdomain_still_tags_the_source():
    out = tag_binaapp_links('<a href="https://binaapp.my">B</a>', "")
    assert "utm_source=site-footer" in out and "utm_campaign" not in out


def test_empty_and_unrelated_html_pass_through():
    assert tag_binaapp_links("", "ali") == ""
    assert tag_binaapp_links("<p>hello</p>", "ali") == "<p>hello</p>"
