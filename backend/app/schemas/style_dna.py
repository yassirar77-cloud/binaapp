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
# The 13 Style DNAs
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


PASAR_MALAM_NEON = _register(StyleDNADef(
    key="pasar_malam_neon",
    marketing_name="Pasar Malam Neon",
    marketing_name_ms="Pasar Malam Neon",
    mode="dark",
    heading_font="Bebas Neue",
    body_font="Inter",
    heading_weight="400",  # Bebas Neue only has 400
    body_weight="400",
    font_cdn="https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Inter:wght@400;500;700&display=swap",
    primary="#FF3CAC",
    primary_hover="#E0349A",
    secondary="#00F5D4",
    accent="#1A0033",
    background="#0D0015",
    surface="#1A0A2E",
    text="#FFFFFF",
    text_muted="#C4B5D0",
    border="rgba(255,60,172,0.25)",
    gradient_from="#FF3CAC",
    gradient_to="#00F5D4",
    button_primary="bg-gradient-to-r from-[var(--color-gradient-from)] to-[var(--color-gradient-to)] text-white font-bold uppercase tracking-widest rounded-none px-8 py-4 transition-all duration-200 hover:shadow-lg hover:shadow-pink-500/30",
    button_secondary="border-2 border-[var(--color-primary)] text-[var(--color-primary)] hover:bg-[var(--color-primary)] hover:text-white font-bold uppercase tracking-widest rounded-none px-8 py-4 transition-all duration-200",
    card="bg-[var(--color-surface)]/90 backdrop-blur-md border border-pink-500/20 rounded-none hover:border-pink-500/50 transition-all duration-200",
    nav="bg-[#0D0015]/95 backdrop-blur-xl border-b border-pink-500/30 fixed top-0 w-full z-50",
    shadow="0 4px 12px -2px rgba(255,60,172,0.15), 0 2px 6px -2px rgba(0,245,212,0.1)",
    shadow_lg="0 12px 24px -4px rgba(255,60,172,0.2), 0 6px 12px -4px rgba(0,245,212,0.15)",
))

KAMPUNG_SERENE = _register(StyleDNADef(
    key="kampung_serene",
    marketing_name="Kampung Serene",
    marketing_name_ms="Kampung Tenang",
    mode="light",
    heading_font="Cormorant Garamond",
    body_font="Noto Serif",
    heading_weight="500",
    body_weight="400",
    font_cdn="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,400;0,500;0,600;1,600&family=Noto+Serif:wght@400;600&display=swap",
    primary="#2D5016",
    primary_hover="#1E3A0F",
    secondary="#6B4E2A",
    accent="#E8F0DB",
    background="#FDFDF8",
    surface="#FFFFFF",
    text="#2C2C1E",
    text_muted="#7A7A5A",
    border="rgba(45,80,22,0.1)",
    gradient_from="#2D5016",
    gradient_to="#6B4E2A",
    button_primary="bg-[var(--color-primary)] hover:bg-[var(--color-primary-hover)] text-white font-medium rounded-full px-8 py-3.5 transition-colors duration-300",
    button_secondary="border border-[var(--color-primary)] text-[var(--color-primary)] hover:bg-[var(--color-primary)] hover:text-white font-medium rounded-full px-8 py-3.5 transition-colors duration-300",
    card="bg-[var(--color-surface)] rounded-3xl border border-green-900/5 hover:shadow-md transition-shadow duration-300",
    nav="bg-[#FDFDF8]/95 backdrop-blur-sm fixed top-0 w-full z-50",
    border_radius_sm="1rem",
    border_radius_md="1.5rem",
    border_radius_lg="2rem",
    shadow="0 2px 8px -2px rgba(45,80,22,0.06), 0 1px 3px -1px rgba(0,0,0,0.04)",
    shadow_lg="0 8px 20px -4px rgba(45,80,22,0.08), 0 4px 8px -4px rgba(0,0,0,0.04)",
))

KOPITIAM_NOSTALGIA = _register(StyleDNADef(
    key="kopitiam_nostalgia",
    marketing_name="Kopitiam Nostalgia",
    marketing_name_ms="Kopitiam Nostalgia",
    mode="light",
    heading_font="Playfair Display",
    body_font="Source Serif Pro",
    heading_weight="700",
    body_weight="400",
    font_cdn="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;700&family=Source+Serif+Pro:wght@400;600&display=swap",
    primary="#6B3A1F",
    primary_hover="#4A2710",
    secondary="#8B6914",
    accent="#F5E6C8",
    background="#FDF8F0",
    surface="#FFFDF7",
    text="#3B2F2F",
    text_muted="#8C7A6B",
    border="rgba(107,58,31,0.12)",
    gradient_from="#6B3A1F",
    gradient_to="#8B6914",
    button_primary="bg-[var(--color-primary)] hover:bg-[var(--color-primary-hover)] text-white font-semibold rounded-lg px-7 py-3 border-b-4 border-[var(--color-primary-hover)] transition-colors duration-200",
    button_secondary="border-2 border-[var(--color-primary)] text-[var(--color-primary)] hover:bg-[var(--color-primary)] hover:text-white font-semibold rounded-lg px-7 py-3 transition-colors duration-200",
    card="bg-[var(--color-surface)] rounded-xl border border-[var(--color-accent)] shadow-sm hover:shadow-md transition-shadow duration-200",
    nav="bg-[#FDF8F0]/95 backdrop-blur-sm border-b border-[var(--color-accent)] fixed top-0 w-full z-50",
    border_radius_sm="0.5rem",
    border_radius_md="0.75rem",
    border_radius_lg="1rem",
    shadow="0 2px 6px -1px rgba(107,58,31,0.08), 0 1px 3px -1px rgba(0,0,0,0.04)",
    shadow_lg="0 8px 16px -4px rgba(107,58,31,0.12), 0 3px 6px -2px rgba(0,0,0,0.06)",
))

STREETFOOD_BOLD = _register(StyleDNADef(
    key="streetfood_bold",
    marketing_name="Streetfood Bold",
    marketing_name_ms="Jalanan Tegas",
    mode="light",
    heading_font="Anton",
    body_font="DM Sans",
    heading_weight="400",  # Anton only has 400
    body_weight="400",
    font_cdn="https://fonts.googleapis.com/css2?family=Anton&family=DM+Sans:wght@400;500;700&display=swap",
    primary="#FF6B00",
    primary_hover="#E05500",
    secondary="#1A1A1A",
    accent="#FFF0E0",
    background="#FFFFFF",
    surface="#FFF8F0",
    text="#1A1A1A",
    text_muted="#6B6B6B",
    border="rgba(255,107,0,0.12)",
    gradient_from="#FF6B00",
    gradient_to="#FF2D55",
    button_primary="bg-[var(--color-primary)] hover:bg-[var(--color-primary-hover)] text-white font-bold uppercase tracking-wider rounded-xl px-8 py-4 transition-transform duration-150 hover:scale-105",
    button_secondary="bg-[var(--color-secondary)] text-white hover:bg-black font-bold uppercase tracking-wider rounded-xl px-8 py-4 transition-transform duration-150 hover:scale-105",
    card="bg-[var(--color-surface)] rounded-2xl shadow-xl border-l-4 border-[var(--color-primary)] hover:shadow-2xl transition-all duration-200",
    nav="bg-white shadow-lg fixed top-0 w-full z-50",
    border_radius_sm="0.75rem",
    border_radius_md="1rem",
    border_radius_lg="1.5rem",
    shadow="0 4px 12px -2px rgba(255,107,0,0.1), 0 2px 6px -2px rgba(0,0,0,0.08)",
    shadow_lg="0 12px 28px -6px rgba(255,107,0,0.15), 0 6px 12px -4px rgba(0,0,0,0.08)",
))

FINE_DINING_OBSIDIAN = _register(StyleDNADef(
    key="fine_dining_obsidian",
    marketing_name="Fine Dining Obsidian",
    marketing_name_ms="Santapan Mewah Obsidian",
    mode="dark",
    heading_font="Fraunces",
    body_font="Inter",
    heading_weight="700",
    body_weight="400",
    font_cdn="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,700&family=Inter:wght@400;500&display=swap",
    primary="#C9A96E",
    primary_hover="#B8963E",
    secondary="#4A3728",
    accent="#1C1410",
    background="#0C0A08",
    surface="#1A1614",
    text="#F5F0E8",
    text_muted="#A09080",
    border="rgba(201,169,110,0.15)",
    gradient_from="#C9A96E",
    gradient_to="#4A3728",
    button_primary="bg-[var(--color-primary)] hover:bg-[var(--color-primary-hover)] text-black font-medium tracking-wide rounded-none px-10 py-4 transition-colors duration-300",
    button_secondary="border border-[var(--color-primary)] text-[var(--color-primary)] hover:bg-[var(--color-primary)] hover:text-black font-medium tracking-wide rounded-none px-10 py-4 transition-colors duration-300",
    card="bg-[var(--color-surface)] border border-[var(--color-primary)]/10 rounded-none hover:border-[var(--color-primary)]/30 transition-all duration-300",
    nav="bg-[#0C0A08]/95 backdrop-blur-xl border-b border-[var(--color-primary)]/10 fixed top-0 w-full z-50",
    border_radius_sm="0",
    border_radius_md="0",
    border_radius_lg="0.25rem",
    shadow="0 4px 8px -2px rgba(0,0,0,0.4), 0 2px 4px -2px rgba(201,169,110,0.05)",
    shadow_lg="0 12px 24px -6px rgba(0,0,0,0.5), 0 6px 12px -4px rgba(201,169,110,0.08)",
))


def get_style_dna(key: str) -> StyleDNADef:
    """Look up a Style DNA by key. Raises KeyError if not found."""
    return STYLE_DNAS[key]
