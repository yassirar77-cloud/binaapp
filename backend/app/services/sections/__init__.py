"""Deterministic page sections.

Code renders every structural section of a merchant site (nav, hero,
options strip, info banners, menu slot, coming soon, about, location,
contact, footer) from the merchant's own data. The AI's only inputs are
the THEME (palette, fonts, style variant — through the design plan) and
the COPY (headline, sub-headline, about text). The AI never writes layout
CSS for these sections, so there is nothing to patch after the fact.

Entry point: ``compose.compose_page``.
"""

from app.services.sections.compose import compose_page  # noqa: F401
from app.services.sections.copy import Copy, build_copy_prompt, fallback_copy, parse_copy  # noqa: F401
from app.services.sections.spec import SiteSpec, build_spec  # noqa: F401
from app.services.sections.theme import Theme, theme_from_plan  # noqa: F401

PAGE_MODE_DETERMINISTIC = "deterministic"
PAGE_MODE_FREEFORM = "freeform"
