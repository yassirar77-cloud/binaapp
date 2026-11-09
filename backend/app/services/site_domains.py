"""Which apex domains a published site can live under.

A site is always ``<subdomain>.<site_domain>``. ``site_domain`` is one of
``settings.MAIN_DOMAIN`` (binaapp.my) or ``settings.ALT_SITE_DOMAINS``
(mysyg.com), stored per website in ``websites.site_domain`` (migration 061).

The subdomain is globally unique across ALL domains — ``kedai`` can only
belong to one site — so the subdomain middleware can answer a request on any
of the domains, then redirect to the one the merchant chose.
"""

from typing import List, Optional

from app.core.config import settings


def site_domains() -> List[str]:
    """MAIN_DOMAIN first, then the extra domains, lowercased and de-duplicated."""
    out: List[str] = []
    raw = [settings.MAIN_DOMAIN] + (settings.ALT_SITE_DOMAINS or "").split(",")
    for d in raw:
        d = (d or "").strip().lower().strip(".")
        if d and d not in out:
            out.append(d)
    return out


def default_site_domain() -> str:
    return site_domains()[0]


def normalize_site_domain(value: Optional[str]) -> Optional[str]:
    """The allowed domain ``value`` names, or None if it names none.

    Accepts "mysyg.com", ".mysyg.com", "MYSYG.COM".
    """
    v = (value or "").strip().lower().strip(".")
    return v if v in site_domains() else None


def resolve_site_domain(value: Optional[str]) -> str:
    """Like normalize_site_domain but falls back to the default domain."""
    return normalize_site_domain(value) or default_site_domain()


def site_url(subdomain: str, site_domain: Optional[str] = None) -> str:
    """``https://<subdomain>.<site_domain>`` (default domain if unset/unknown)."""
    return f"https://{subdomain}.{resolve_site_domain(site_domain)}"


def split_host(host: str):
    """``(subdomain, domain)`` for a host on one of our site domains, else None.

    Strips any port. Only a single label in front of the domain counts as a
    subdomain; the apex itself and deeper hosts return None.
    """
    h = (host or "").strip().lower().split(":", 1)[0].rstrip(".")
    for d in site_domains():
        suffix = "." + d
        if h.endswith(suffix):
            sub = h[: -len(suffix)]
            if sub and "." not in sub:
                return sub, d
    return None
