"""
V2 Style DNA definitions.

Each Style DNA is a complete visual identity: colors, fonts, tokens, and
component-level Tailwind classes.  Used by recipe_builder to expand a
DesignBrief's ``style_dna`` field into full ``ThemeTokens``.

See docs/V2_ARCHITECTURE.md Section 12 Q5 for rationale & naming.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict


@dataclass(frozen=True)
class StyleDNADef:
    key: str
    marketing_name: str
    marketing_name_ms: str
    mode: str  # "light" or "dark"

    # Fonts
    heading_font: str
    body_font: str
    heading_weight: str
    body_weight: str
    font_cdn: str

    # Colors
    primary: str
    primary_hover: str
    secondary: str
    accent: str
    background: str
    surface: str
    text: str
    text_muted: str
    border: str
    gradient_from: str
    gradient_to: str

    # Component-level styles (Tailwind classes)
    button_primary: str
    button_secondary: str
    card: str
    nav: str

    # Design tokens
    border_radius_sm: str = "0.75rem"
    border_radius_md: str = "1rem"
    border_radius_lg: str = "1.5rem"
    shadow: str = "0 4px 6px -1px rgba(0,0,0,0.07), 0 2px 4px -2px rgba(0,0,0,0.05)"
    shadow_lg: str = "0 10px 15px -3px rgba(0,0,0,0.08), 0 4px 6px -4px rgba(0,0,0,0.04)"


# ---------------------------------------------------------------------------
# The 8 Style DNAs
# ---------------------------------------------------------------------------

STYLE_DNAS: Dict[str, StyleDNADef] = {}


def _register(d: StyleDNADef) -> StyleDNADef:
    STYLE_DNAS[d.key] = d
    return d


TEH_TARIK_WARM = _register(StyleDNADef(
    key="teh_tarik_warm",
    marketing_name="Teh Tarik Warm",
    marketing_name_ms="Teh Tarik Hangat",
    mode="light",
    heading_font="Lora",
    body_font="Nunito",
    heading_weight="700",
    body_weight="400",
    font_cdn="https://fonts.googleapis.com/css2?family=Lora:wght@400;600;700&family=Nunito:wght@400;500;600&display=swap",
    primary="#C2410C",
    primary_hover="#9A3412",
    secondary="#78350F",
    accent="#FED7AA",
    background="#FFFBF5",
    surface="#FFFFFF",
    text="#1C1917",
    text_muted="#78716C",
    border="rgba(194,65,12,0.1)",
    gradient_from="#C2410C",
    gradient_to="#78350F",
    button_primary="bg-[var(--color-primary)] hover:bg-[var(--color-primary-hover)] text-white font-semibold rounded-2xl px-7 py-3.5 transition-colors duration-200",
    button_secondary="border-2 border-[var(--color-primary)] text-[var(--color-primary)] hover:bg-[var(--color-primary)] hover:text-white font-semibold rounded-2xl px-7 py-3.5 transition-colors duration-200",
    card="bg-[var(--color-surface)] rounded-3xl shadow-md hover:shadow-lg transition-shadow duration-200",
    nav="bg-white/90 backdrop-blur-xl shadow-sm fixed top-0 w-full z-50",
))

PANDAN_FRESH = _register(StyleDNADef(
    key="pandan_fresh",
    marketing_name="Pandan Fresh",
    marketing_name_ms="Pandan Segar",
    mode="light",
    heading_font="Plus Jakarta Sans",
    body_font="Inter",
    heading_weight="700",
    body_weight="400",
    font_cdn="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700&family=Inter:wght@400;500;600&display=swap",
    primary="#16A34A",
    primary_hover="#15803D",
    secondary="#166534",
    accent="#DCFCE7",
    background="#FAFFFE",
    surface="#FFFFFF",
    text="#1A2E1A",
    text_muted="#6B8068",
    border="rgba(22,163,74,0.1)",
    gradient_from="#16A34A",
    gradient_to="#166534",
    button_primary="bg-[var(--color-primary)] hover:bg-[var(--color-primary-hover)] text-white font-semibold rounded-xl px-6 py-3 transition-colors duration-200",
    button_secondary="border-2 border-[var(--color-primary)] text-[var(--color-primary)] hover:bg-[var(--color-primary)] hover:text-white font-semibold rounded-xl px-6 py-3 transition-colors duration-200",
    card="bg-[var(--color-surface)] rounded-2xl shadow-lg shadow-black/5 border border-gray-100 hover:shadow-xl transition-shadow duration-200",
    nav="bg-white/90 backdrop-blur-xl shadow-sm fixed top-0 w-full z-50",
))

KOPI_HITAM = _register(StyleDNADef(
    key="kopi_hitam",
    marketing_name="Kopi Hitam",
    marketing_name_ms="Kopi Hitam",
    mode="dark",
    heading_font="Playfair Display",
    body_font="DM Sans",
    heading_weight="700",
    body_weight="400",
    font_cdn="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;700&family=DM+Sans:wght@400;500;700&display=swap",
    primary="#D4AF37",
    primary_hover="#B8972E",
    secondary="#8B7355",
    accent="#2A1F0E",
    background="#0A0A0A",
    surface="#1A1A1A",
    text="#F5F5F0",
    text_muted="#A0998C",
    border="rgba(255,255,255,0.1)",
    gradient_from="#D4AF37",
    gradient_to="#8B7355",
    button_primary="bg-[var(--color-primary)] hover:bg-[var(--color-primary-hover)] text-black font-semibold rounded-full px-8 py-3 transition-colors duration-200",
    button_secondary="border-2 border-[var(--color-primary)] text-[var(--color-primary)] hover:bg-[var(--color-primary)] hover:text-black font-semibold rounded-full px-8 py-3 transition-colors duration-200",
    card="bg-[var(--color-surface)]/80 backdrop-blur-xl border border-white/10 rounded-2xl hover:border-white/20 transition-all duration-200",
    nav="bg-[#0A0A0A]/90 backdrop-blur-xl border-b border-white/10 fixed top-0 w-full z-50",
    shadow="0 4px 6px -1px rgba(0,0,0,0.3), 0 2px 4px -2px rgba(0,0,0,0.2)",
    shadow_lg="0 10px 15px -3px rgba(0,0,0,0.4), 0 4px 6px -4px rgba(0,0,0,0.3)",
))

SAMBAL_BERANI = _register(StyleDNADef(
    key="sambal_berani",
    marketing_name="Sambal Berani",
    marketing_name_ms="Sambal Berani",
    mode="light",
    heading_font="Bebas Neue",
    body_font="Roboto",
    heading_weight="400",  # Bebas Neue only has 400
    body_weight="400",
    font_cdn="https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Roboto:wght@400;500;700&display=swap",
    primary="#EF4444",
    primary_hover="#DC2626",
    secondary="#F59E0B",
    accent="#FEF3C7",
    background="#FFFFFF",
    surface="#FFF7ED",
    text="#18181B",
    text_muted="#71717A",
    border="rgba(239,68,68,0.1)",
    gradient_from="#EF4444",
    gradient_to="#F59E0B",
    button_primary="bg-[var(--color-primary)] hover:bg-[var(--color-primary-hover)] text-white font-bold uppercase tracking-wider rounded-xl px-8 py-4 transition-colors duration-200",
    button_secondary="border-2 border-[var(--color-primary)] text-[var(--color-primary)] hover:bg-[var(--color-primary)] hover:text-white font-bold uppercase tracking-wider rounded-xl px-8 py-4 transition-colors duration-200",
    card="bg-[var(--color-surface)] rounded-2xl shadow-xl hover:shadow-2xl transition-shadow duration-200",
    nav="bg-white/90 backdrop-blur-xl shadow-md fixed top-0 w-full z-50",
))

SUTERA_PUTIH = _register(StyleDNADef(
    key="sutera_putih",
    marketing_name="Sutera Putih",
    marketing_name_ms="Sutera Putih",
    mode="light",
    heading_font="Cormorant Garamond",
    body_font="Inter",
    heading_weight="600",
    body_weight="400",
    font_cdn="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@400;600;700&family=Inter:wght@400;500&display=swap",
    primary="#18181B",
    primary_hover="#09090B",
    secondary="#3F3F46",
    accent="#F4F4F5",
    background="#FFFFFF",
    surface="#FAFAFA",
    text="#18181B",
    text_muted="#A1A1AA",
    border="rgba(0,0,0,0.06)",
    gradient_from="#18181B",
    gradient_to="#3F3F46",
    button_primary="bg-[var(--color-primary)] hover:bg-[var(--color-primary-hover)] text-white font-medium rounded-none px-8 py-3.5 transition-colors duration-200",
    button_secondary="border border-[var(--color-primary)] text-[var(--color-primary)] hover:bg-[var(--color-primary)] hover:text-white font-medium rounded-none px-8 py-3.5 transition-colors duration-200",
    card="bg-[var(--color-surface)] rounded-xl hover:bg-gray-50 transition-colors duration-200",
    nav="bg-white/95 backdrop-blur-xl fixed top-0 w-full z-50",
))

LAMPU_NEON = _register(StyleDNADef(
    key="lampu_neon",
    marketing_name="Lampu Neon",
    marketing_name_ms="Lampu Neon",
    mode="dark",
    heading_font="Space Grotesk",
    body_font="Inter",
    heading_weight="700",
    body_weight="400",
    font_cdn="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;600;700&family=Inter:wght@400;500&display=swap",
    primary="#8B5CF6",
    primary_hover="#7C3AED",
    secondary="#06B6D4",
    accent="#1E1B4B",
    background="#030712",
    surface="#111827",
    text="#F9FAFB",
    text_muted="#9CA3AF",
    border="rgba(139,92,246,0.2)",
    gradient_from="#8B5CF6",
    gradient_to="#06B6D4",
    button_primary="bg-gradient-to-r from-[var(--color-gradient-from)] to-[var(--color-gradient-to)] text-white font-semibold rounded-xl px-7 py-3.5 transition-all duration-200 hover:shadow-lg hover:shadow-purple-500/25",
    button_secondary="border border-[var(--color-primary)] text-[var(--color-primary)] hover:bg-[var(--color-primary)]/10 font-semibold rounded-xl px-7 py-3.5 transition-all duration-200",
    card="bg-[var(--color-surface)]/80 backdrop-blur-xl border border-[var(--color-primary)]/20 rounded-2xl hover:border-[var(--color-primary)]/40 transition-all duration-200",
    nav="bg-[#030712]/90 backdrop-blur-xl border-b border-purple-500/20 fixed top-0 w-full z-50",
    shadow="0 4px 6px -1px rgba(139,92,246,0.1), 0 2px 4px -2px rgba(139,92,246,0.06)",
    shadow_lg="0 10px 15px -3px rgba(139,92,246,0.15), 0 4px 6px -4px rgba(139,92,246,0.1)",
))

WARISAN_EMAS = _register(StyleDNADef(
    key="warisan_emas",
    marketing_name="Warisan Emas",
    marketing_name_ms="Warisan Emas",
    mode="light",
    heading_font="Playfair Display",
    body_font="Poppins",
    heading_weight="700",
    body_weight="400",
    font_cdn="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;700&family=Poppins:wght@400;500;600&display=swap",
    primary="#B45309",
    primary_hover="#92400E",
    secondary="#78350F",
    accent="#FDE68A",
    background="#FFFDF5",
    surface="#FFFFFF",
    text="#292524",
    text_muted="#78716C",
    border="rgba(180,83,9,0.1)",
    gradient_from="#B45309",
    gradient_to="#78350F",
    button_primary="bg-[var(--color-primary)] hover:bg-[var(--color-primary-hover)] text-white font-semibold rounded-xl px-7 py-3 transition-colors duration-200",
    button_secondary="border-2 border-[var(--color-primary)] text-[var(--color-primary)] hover:bg-[var(--color-primary)] hover:text-white font-semibold rounded-xl px-7 py-3 transition-colors duration-200",
    card="bg-[var(--color-surface)] rounded-2xl shadow-md border border-[var(--color-accent)]/30 hover:shadow-lg transition-shadow duration-200",
    nav="bg-white/90 backdrop-blur-xl shadow-sm fixed top-0 w-full z-50",
))

OMBAK_BIRU = _register(StyleDNADef(
    key="ombak_biru",
    marketing_name="Ombak Biru",
    marketing_name_ms="Ombak Biru",
    mode="light",
    heading_font="Source Serif 4",
    body_font="Open Sans",
    heading_weight="700",
    body_weight="400",
    font_cdn="https://fonts.googleapis.com/css2?family=Source+Serif+4:wght@400;600;700&family=Open+Sans:wght@400;500;600&display=swap",
    primary="#0891B2",
    primary_hover="#0E7490",
    secondary="#164E63",
    accent="#CFFAFE",
    background="#F8FDFF",
    surface="#FFFFFF",
    text="#0C1A22",
    text_muted="#5E8A9A",
    border="rgba(8,145,178,0.1)",
    gradient_from="#0891B2",
    gradient_to="#164E63",
    button_primary="bg-[var(--color-primary)] hover:bg-[var(--color-primary-hover)] text-white font-semibold rounded-xl px-7 py-3 transition-colors duration-200",
    button_secondary="border-2 border-[var(--color-primary)] text-[var(--color-primary)] hover:bg-[var(--color-primary)] hover:text-white font-semibold rounded-xl px-7 py-3 transition-colors duration-200",
    card="bg-[var(--color-surface)] rounded-2xl shadow-lg shadow-cyan-900/5 hover:shadow-xl transition-shadow duration-200",
    nav="bg-white/90 backdrop-blur-xl shadow-sm fixed top-0 w-full z-50",
))


def get_style_dna(key: str) -> StyleDNADef:
    """Look up a Style DNA by key. Raises KeyError if not found."""
    return STYLE_DNAS[key]
