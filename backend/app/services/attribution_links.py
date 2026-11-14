"""
Tag the "Dibina dengan BinaApp" credit link on merchant sites.

Published pages carry a footer credit linking to https://binaapp.my. A bare
link tells us nothing: we cannot see that a signup came from a merchant's
site, let alone which one. This rewrites that link at serve time to

    https://binaapp.my/?utm_source=site-footer&utm_medium=referral&utm_campaign=<subdomain>

so the founder dashboard's Marketing tab can count visits and signups that
merchant sites send, per site.

Done at serve time (not generation time) so it covers every page already
published, without touching stored HTML. Only the bare home link is
rewritten: /polisi-privasi and other deep links are left alone, and a link
that is already tagged no longer matches, so this is idempotent.
"""
import re

_BARE_HOME_LINK_RE = re.compile(
    r"""href=(["'])https?://(?:www\.)?binaapp\.my/?\1""",
    re.IGNORECASE,
)
_SUBDOMAIN_SAFE_RE = re.compile(r"[^a-z0-9-]+")


def footer_credit_url(subdomain: str) -> str:
    campaign = _SUBDOMAIN_SAFE_RE.sub("", (subdomain or "").lower())[:63]
    url = "https://binaapp.my/?utm_source=site-footer&amp;utm_medium=referral"
    if campaign:
        url += f"&amp;utm_campaign={campaign}"
    return url


def tag_binaapp_links(html_content: str, subdomain: str) -> str:
    """Rewrite bare binaapp.my home links to the tagged footer-credit URL."""
    if not html_content or "binaapp.my" not in html_content:
        return html_content
    url = footer_credit_url(subdomain)
    return _BARE_HOME_LINK_RE.sub(lambda m: f"href={m.group(1)}{url}{m.group(1)}", html_content)
