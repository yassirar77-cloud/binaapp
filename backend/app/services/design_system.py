"""
Design System Module
Provides comprehensive design guidelines, font pairings, color palettes,
layout templates, hero variants, and animation configs for premium website generation.

Variety model: every business type has SEVERAL font pairings, colour palettes,
and hero/layout options. A deterministic seed derived from the business name
picks one combination, so two different businesses of the same type no longer
receive an identical-looking website, while regenerating the SAME business
stays visually stable. Explicit user requests (a colour theme or style words
found in the description) override the seeded picks — the user always wins.
"""

import hashlib
import logging
import re

logger = logging.getLogger(__name__)


def _variant_seed(business_name: str) -> int:
    """Deterministic seed from the business name — stable across runs."""
    normalized = (business_name or "").strip().lower()
    if not normalized:
        return 0
    return int(hashlib.md5(normalized.encode("utf-8")).hexdigest()[:8], 16)


def _pick(options: list, seed: int, divisor: int, variant: int = 0):
    """Seeded pick from `options`, walked forward by `variant` steps.

    `variant` is the "shuffle design" offset. variant=0 reproduces the
    pre-shuffle pick exactly, so every existing site keeps its look; each
    increment advances ONE step through this pool. Because it is an offset
    and not randomness, shuffling three times and reloading still shows
    shuffle #3 — re-rolls are reproducible and shareable.
    """
    if not options:
        return None
    index = (seed // divisor + int(variant or 0)) % len(options)
    return options[index]


# ============================================================================
# FONT PAIRINGS BY BUSINESS TYPE
# ============================================================================

FONT_PAIRINGS = {
    "food": {
        "heading": "Playfair Display",
        "heading_weights": "400;700",
        "heading_fallback": "Georgia, serif",
        "heading_category": "serif",
        "body": "DM Sans",
        "body_weights": "400;500;700",
        "body_fallback": "system-ui, sans-serif",
        "body_category": "sans-serif",
        "vibe": "Elegant, appetizing",
    },
    "cafe": {
        "heading": "Cormorant Garamond",
        "heading_weights": "400;600;700",
        "heading_fallback": "Georgia, serif",
        "heading_category": "serif",
        "body": "Karla",
        "body_weights": "400;500;600",
        "body_fallback": "Helvetica Neue, sans-serif",
        "body_category": "sans-serif",
        "vibe": "Refined, cozy",
    },
    "salon": {
        "heading": "Italiana",
        "heading_weights": "400",
        "heading_fallback": "Georgia, serif",
        "heading_category": "serif",
        "body": "Poppins",
        "body_weights": "300;400;500;600",
        "body_fallback": "system-ui, sans-serif",
        "body_category": "sans-serif",
        "vibe": "Luxurious, feminine",
    },
    "clothing": {
        "heading": "Tenor Sans",
        "heading_weights": "400",
        "heading_fallback": "Helvetica Neue, sans-serif",
        "heading_category": "sans-serif",
        "body": "Work Sans",
        "body_weights": "300;400;500;600",
        "body_fallback": "system-ui, sans-serif",
        "body_category": "sans-serif",
        "vibe": "Editorial, chic",
    },
    "bakery": {
        "heading": "Lora",
        "heading_weights": "400;600;700",
        "heading_fallback": "Georgia, serif",
        "heading_category": "serif",
        "body": "Nunito",
        "body_weights": "400;600;700",
        "body_fallback": "system-ui, sans-serif",
        "body_category": "sans-serif",
        "vibe": "Warm, inviting",
    },
    "services": {
        "heading": "Plus Jakarta Sans",
        "heading_weights": "500;600;700;800",
        "heading_fallback": "system-ui, sans-serif",
        "heading_category": "sans-serif",
        "body": "Manrope",
        "body_weights": "400;500;600;700",
        "body_fallback": "Helvetica Neue, sans-serif",
        "body_category": "sans-serif",
        "vibe": "Professional, trustworthy",
    },
    "gym": {
        "heading": "Bebas Neue",
        "heading_weights": "400",
        "heading_fallback": "Impact, sans-serif",
        "heading_category": "sans-serif",
        "body": "Barlow",
        "body_weights": "400;500;700",
        "body_fallback": "Helvetica Neue, sans-serif",
        "body_category": "sans-serif",
        "vibe": "Bold, energetic",
    },
    "clinic": {
        "heading": "Source Serif 4",
        "heading_weights": "400;600;700",
        "heading_fallback": "Georgia, serif",
        "heading_category": "serif",
        "body": "Open Sans",
        "body_weights": "400;500;600",
        "body_fallback": "system-ui, sans-serif",
        "body_category": "sans-serif",
        "vibe": "Clean, authoritative",
    },
    "general": {
        "heading": "Plus Jakarta Sans",
        "heading_weights": "500;600;700;800",
        "heading_fallback": "system-ui, sans-serif",
        "heading_category": "sans-serif",
        "body": "Mulish",
        "body_weights": "400;500;600;700",
        "body_fallback": "Helvetica Neue, sans-serif",
        "body_category": "sans-serif",
        "vibe": "Professional, versatile",
    },
}


# Additional font pairings per business type. Index 0 is always the classic
# pairing above (kept first for backward compatibility); the seeded pick
# rotates across the whole list so same-type businesses stop looking cloned.
ALT_FONT_PAIRINGS = {
    "food": [
        {
            "heading": "Fraunces",
            "heading_weights": "400;600;700",
            "heading_fallback": "Georgia, serif",
            "heading_category": "serif",
            "body": "Outfit",
            "body_weights": "400;500;600",
            "body_fallback": "system-ui, sans-serif",
            "body_category": "sans-serif",
            "vibe": "Contemporary editorial, warm",
        },
        {
            "heading": "Marcellus",
            "heading_weights": "400",
            "heading_fallback": "Georgia, serif",
            "heading_category": "serif",
            "body": "Figtree",
            "body_weights": "400;500;600",
            "body_fallback": "system-ui, sans-serif",
            "body_category": "sans-serif",
            "vibe": "Understated fine-dining",
        },
    ],
    "cafe": [
        {
            "heading": "Libre Baskerville",
            "heading_weights": "400;700",
            "heading_fallback": "Georgia, serif",
            "heading_category": "serif",
            "body": "Jost",
            "body_weights": "400;500;600",
            "body_fallback": "Helvetica Neue, sans-serif",
            "body_category": "sans-serif",
            "vibe": "Literary, artisan",
        },
        {
            "heading": "Fraunces",
            "heading_weights": "400;600;700",
            "heading_fallback": "Georgia, serif",
            "heading_category": "serif",
            "body": "Nunito Sans",
            "body_weights": "400;600;700",
            "body_fallback": "system-ui, sans-serif",
            "body_category": "sans-serif",
            "vibe": "Playful specialty-coffee",
        },
    ],
    "salon": [
        {
            "heading": "Marcellus",
            "heading_weights": "400",
            "heading_fallback": "Georgia, serif",
            "heading_category": "serif",
            "body": "Mulish",
            "body_weights": "400;500;600",
            "body_fallback": "system-ui, sans-serif",
            "body_category": "sans-serif",
            "vibe": "Quiet luxury",
        },
        {
            "heading": "Prata",
            "heading_weights": "400",
            "heading_fallback": "Georgia, serif",
            "heading_category": "serif",
            "body": "Jost",
            "body_weights": "300;400;500",
            "body_fallback": "Helvetica Neue, sans-serif",
            "body_category": "sans-serif",
            "vibe": "High-fashion editorial",
        },
    ],
    "clothing": [
        {
            "heading": "Archivo",
            "heading_weights": "500;600;700",
            "heading_fallback": "Helvetica Neue, sans-serif",
            "heading_category": "sans-serif",
            "body": "Figtree",
            "body_weights": "400;500;600",
            "body_fallback": "system-ui, sans-serif",
            "body_category": "sans-serif",
            "vibe": "Modern streetwear",
        },
        {
            "heading": "Prata",
            "heading_weights": "400",
            "heading_fallback": "Georgia, serif",
            "heading_category": "serif",
            "body": "Work Sans",
            "body_weights": "300;400;500",
            "body_fallback": "system-ui, sans-serif",
            "body_category": "sans-serif",
            "vibe": "Boutique elegance",
        },
    ],
    "bakery": [
        {
            "heading": "Fraunces",
            "heading_weights": "400;600;700",
            "heading_fallback": "Georgia, serif",
            "heading_category": "serif",
            "body": "Quicksand",
            "body_weights": "400;500;600",
            "body_fallback": "system-ui, sans-serif",
            "body_category": "sans-serif",
            "vibe": "Sweet, artisanal",
        },
        {
            "heading": "DM Serif Display",
            "heading_weights": "400",
            "heading_fallback": "Georgia, serif",
            "heading_category": "serif",
            "body": "Nunito Sans",
            "body_weights": "400;600;700",
            "body_fallback": "system-ui, sans-serif",
            "body_category": "sans-serif",
            "vibe": "Classic patisserie",
        },
    ],
    "services": [
        {
            "heading": "Sora",
            "heading_weights": "400;600;700",
            "heading_fallback": "system-ui, sans-serif",
            "heading_category": "sans-serif",
            "body": "Figtree",
            "body_weights": "400;500;600",
            "body_fallback": "Helvetica Neue, sans-serif",
            "body_category": "sans-serif",
            "vibe": "Tech-forward, precise",
        },
        {
            "heading": "Space Grotesk",
            "heading_weights": "500;600;700",
            "heading_fallback": "system-ui, sans-serif",
            "heading_category": "sans-serif",
            "body": "Work Sans",
            "body_weights": "400;500;600",
            "body_fallback": "Helvetica Neue, sans-serif",
            "body_category": "sans-serif",
            "vibe": "Contemporary studio",
        },
    ],
    "gym": [
        {
            "heading": "Anton",
            "heading_weights": "400",
            "heading_fallback": "Impact, sans-serif",
            "heading_category": "sans-serif",
            "body": "Manrope",
            "body_weights": "400;500;700",
            "body_fallback": "Helvetica Neue, sans-serif",
            "body_category": "sans-serif",
            "vibe": "Heavyweight impact",
        },
        {
            "heading": "Archivo Black",
            "heading_weights": "400",
            "heading_fallback": "Impact, sans-serif",
            "heading_category": "sans-serif",
            "body": "Barlow",
            "body_weights": "400;500;700",
            "body_fallback": "Helvetica Neue, sans-serif",
            "body_category": "sans-serif",
            "vibe": "Athletic, unstoppable",
        },
    ],
    "clinic": [
        {
            "heading": "Bitter",
            "heading_weights": "400;600;700",
            "heading_fallback": "Georgia, serif",
            "heading_category": "serif",
            "body": "Karla",
            "body_weights": "400;500;600",
            "body_fallback": "system-ui, sans-serif",
            "body_category": "sans-serif",
            "vibe": "Established, caring",
        },
        {
            "heading": "Newsreader",
            "heading_weights": "400;600;700",
            "heading_fallback": "Georgia, serif",
            "heading_category": "serif",
            "body": "Mulish",
            "body_weights": "400;500;600",
            "body_fallback": "system-ui, sans-serif",
            "body_category": "sans-serif",
            "vibe": "Calm authority",
        },
    ],
    "general": [
        {
            "heading": "Sora",
            "heading_weights": "400;600;700",
            "heading_fallback": "system-ui, sans-serif",
            "heading_category": "sans-serif",
            "body": "Manrope",
            "body_weights": "400;500;600;700",
            "body_fallback": "Helvetica Neue, sans-serif",
            "body_category": "sans-serif",
            "vibe": "Crisp, current",
        },
        {
            "heading": "Bricolage Grotesque",
            "heading_weights": "500;600;700",
            "heading_fallback": "system-ui, sans-serif",
            "heading_category": "sans-serif",
            "body": "Figtree",
            "body_weights": "400;500;600",
            "body_fallback": "Helvetica Neue, sans-serif",
            "body_category": "sans-serif",
            "vibe": "Distinctive, characterful",
        },
    ],
}


# ============================================================================
# COLOR PALETTES BY BUSINESS TYPE (LIGHT + DARK)
# ============================================================================

COLOR_PALETTES = {
    "food": {
        "light": {
            "primary": "#EA580C",
            "secondary": "#92400E",
            "accent": "#FED7AA",
            "background": "#FFFBF5",
            "surface": "#FFFFFF",
            "text": "#1C1917",
            "text_muted": "#78716C",
            "border": "#E7E5E4",
        },
        "dark": {
            "primary": "#FB923C",
            "secondary": "#FDBA74",
            "accent": "#431407",
            "background": "#0C0A09",
            "surface": "#1C1917",
            "text": "#F5F5F4",
            "text_muted": "#A8A29E",
            "border": "#292524",
        },
    },
    "cafe": {
        "light": {
            "primary": "#92400E",
            "secondary": "#78350F",
            "accent": "#FEF3C7",
            "background": "#FFFDF7",
            "surface": "#FFFFFF",
            "text": "#1C1917",
            "text_muted": "#78716C",
            "border": "#E7E5E4",
        },
        "dark": {
            "primary": "#D97706",
            "secondary": "#FBBF24",
            "accent": "#451A03",
            "background": "#0C0A09",
            "surface": "#1C1917",
            "text": "#FEFCE8",
            "text_muted": "#A8A29E",
            "border": "#292524",
        },
    },
    "salon": {
        "light": {
            "primary": "#A24E63",
            "secondary": "#6E4A4F",
            "accent": "#F6E2DD",
            "background": "#FFFBFA",
            "surface": "#FFFFFF",
            "text": "#2A1E20",
            "text_muted": "#7C6A6C",
            "border": "#EEE3E1",
        },
        "dark": {
            "primary": "#D98A9B",
            "secondary": "#C9A89E",
            "accent": "#3A2429",
            "background": "#14100F",
            "surface": "#1F1917",
            "text": "#F7ECEE",
            "text_muted": "#B3A4A4",
            "border": "#2F2724",
        },
    },
    "clothing": {
        "light": {
            "primary": "#EC4899",
            "secondary": "#9D174D",
            "accent": "#FCE7F3",
            "background": "#FFFBFD",
            "surface": "#FFFFFF",
            "text": "#1A1A2E",
            "text_muted": "#6B7280",
            "border": "#F3E8F0",
        },
        "dark": {
            "primary": "#F472B6",
            "secondary": "#FBCFE8",
            "accent": "#500724",
            "background": "#0F0A10",
            "surface": "#1A1A2E",
            "text": "#FDF2F8",
            "text_muted": "#A1A1AA",
            "border": "#2E2A30",
        },
    },
    "bakery": {
        "light": {
            "primary": "#D97706",
            "secondary": "#92400E",
            "accent": "#FEF3C7",
            "background": "#FFFDF5",
            "surface": "#FFFFFF",
            "text": "#1C1917",
            "text_muted": "#78716C",
            "border": "#E7E5E4",
        },
        "dark": {
            "primary": "#FBBF24",
            "secondary": "#FDE68A",
            "accent": "#451A03",
            "background": "#0C0A09",
            "surface": "#1C1917",
            "text": "#FEFCE8",
            "text_muted": "#A8A29E",
            "border": "#292524",
        },
    },
    "services": {
        "light": {
            "primary": "#2563EB",
            "secondary": "#1E40AF",
            "accent": "#DBEAFE",
            "background": "#F8FAFF",
            "surface": "#FFFFFF",
            "text": "#0F172A",
            "text_muted": "#64748B",
            "border": "#E2E8F0",
        },
        "dark": {
            "primary": "#60A5FA",
            "secondary": "#93C5FD",
            "accent": "#1E3A5F",
            "background": "#0B1120",
            "surface": "#0F172A",
            "text": "#F1F5F9",
            "text_muted": "#94A3B8",
            "border": "#1E293B",
        },
    },
    "gym": {
        "light": {
            "primary": "#DC2626",
            "secondary": "#991B1B",
            "accent": "#FEE2E2",
            "background": "#FFFBFB",
            "surface": "#FFFFFF",
            "text": "#0F172A",
            "text_muted": "#64748B",
            "border": "#E2E8F0",
        },
        "dark": {
            "primary": "#EF4444",
            "secondary": "#FCA5A5",
            "accent": "#450A0A",
            "background": "#0A0A0A",
            "surface": "#171717",
            "text": "#F5F5F5",
            "text_muted": "#A3A3A3",
            "border": "#262626",
        },
    },
    "clinic": {
        "light": {
            "primary": "#0D9488",
            "secondary": "#115E59",
            "accent": "#CCFBF1",
            "background": "#F8FFFE",
            "surface": "#FFFFFF",
            "text": "#0F172A",
            "text_muted": "#64748B",
            "border": "#E2E8F0",
        },
        "dark": {
            "primary": "#2DD4BF",
            "secondary": "#99F6E4",
            "accent": "#134E4A",
            "background": "#0A1210",
            "surface": "#0F1F1C",
            "text": "#F0FDFA",
            "text_muted": "#94A3B8",
            "border": "#1E3330",
        },
    },
    "general": {
        "light": {
            "primary": "#10B981",
            "secondary": "#065F46",
            "accent": "#D1FAE5",
            "background": "#F8FFF9",
            "surface": "#FFFFFF",
            "text": "#0F172A",
            "text_muted": "#64748B",
            "border": "#E2E8F0",
        },
        "dark": {
            "primary": "#34D399",
            "secondary": "#6EE7B7",
            "accent": "#064E3B",
            "background": "#0A120E",
            "surface": "#0F1F18",
            "text": "#F0FDF4",
            "text_muted": "#94A3B8",
            "border": "#1E3329",
        },
    },
}


# Additional colour palettes per business type. Index 0 is always the classic
# palette above; the seeded pick rotates across the whole list.
ALT_COLOR_PALETTES = {
    "food": [
        {  # Fresh herb bistro
            "light": {
                "primary": "#15803D", "secondary": "#14532D", "accent": "#DCFCE7",
                "background": "#F7FDF8", "surface": "#FFFFFF", "text": "#122117",
                "text_muted": "#6B8068", "border": "#E3EFE4",
            },
            "dark": {
                "primary": "#4ADE80", "secondary": "#86EFAC", "accent": "#14532D",
                "background": "#09110C", "surface": "#14241A", "text": "#ECFDF3",
                "text_muted": "#9DB8A5", "border": "#1F3A2A",
            },
        },
        {  # Sambal crimson
            "light": {
                "primary": "#B91C1C", "secondary": "#7F1D1D", "accent": "#FEE2E2",
                "background": "#FFF9F6", "surface": "#FFFFFF", "text": "#1C1917",
                "text_muted": "#78716C", "border": "#F1E5E1",
            },
            "dark": {
                "primary": "#F87171", "secondary": "#FCA5A5", "accent": "#450A0A",
                "background": "#0F0A0A", "surface": "#1D1414", "text": "#FEF2F2",
                "text_muted": "#B3A0A0", "border": "#2E2222",
            },
        },
    ],
    "cafe": [
        {  # Matcha
            "light": {
                "primary": "#4D7C0F", "secondary": "#3F6212", "accent": "#ECFCCB",
                "background": "#FDFFF6", "surface": "#FFFFFF", "text": "#1C2A10",
                "text_muted": "#7A8465", "border": "#E7EDD8",
            },
            "dark": {
                "primary": "#A3E635", "secondary": "#BEF264", "accent": "#365314",
                "background": "#0C1006", "surface": "#171F0E", "text": "#F7FEE7",
                "text_muted": "#A8B58F", "border": "#2A331B",
            },
        },
        {  # Mocha noir minimal
            "light": {
                "primary": "#44403C", "secondary": "#292524", "accent": "#E7E5E4",
                "background": "#FAFAF9", "surface": "#FFFFFF", "text": "#1C1917",
                "text_muted": "#78716C", "border": "#E7E5E4",
            },
            "dark": {
                "primary": "#D6D3D1", "secondary": "#A8A29E", "accent": "#292524",
                "background": "#0C0A09", "surface": "#1C1917", "text": "#FAFAF9",
                "text_muted": "#A8A29E", "border": "#292524",
            },
        },
    ],
    "salon": [
        {  # Champagne gold
            "light": {
                "primary": "#A16207", "secondary": "#713F12", "accent": "#FEF9C3",
                "background": "#FFFDF7", "surface": "#FFFFFF", "text": "#1C1917",
                "text_muted": "#78716C", "border": "#F0EADB",
            },
            "dark": {
                "primary": "#EAB308", "secondary": "#FDE047", "accent": "#422006",
                "background": "#0E0C07", "surface": "#1C1917", "text": "#FEFCE8",
                "text_muted": "#A8A29E", "border": "#2C2824",
            },
        },
        {  # Noir editorial
            "light": {
                "primary": "#18181B", "secondary": "#3F3F46", "accent": "#F4F4F5",
                "background": "#FFFFFF", "surface": "#FAFAFA", "text": "#18181B",
                "text_muted": "#71717A", "border": "#E4E4E7",
            },
            "dark": {
                "primary": "#E4E4E7", "secondary": "#A1A1AA", "accent": "#27272A",
                "background": "#09090B", "surface": "#18181B", "text": "#FAFAFA",
                "text_muted": "#A1A1AA", "border": "#27272A",
            },
        },
    ],
    "clothing": [
        {  # Denim navy
            "light": {
                "primary": "#1E3A8A", "secondary": "#172554", "accent": "#DBEAFE",
                "background": "#F8FAFF", "surface": "#FFFFFF", "text": "#0F172A",
                "text_muted": "#64748B", "border": "#E2E8F0",
            },
            "dark": {
                "primary": "#93C5FD", "secondary": "#BFDBFE", "accent": "#1E3A8A",
                "background": "#0A0F1E", "surface": "#111A2E", "text": "#EFF6FF",
                "text_muted": "#94A3B8", "border": "#1E293B",
            },
        },
        {  # Earth editorial
            "light": {
                "primary": "#7C2D12", "secondary": "#431407", "accent": "#FFEDD5",
                "background": "#FFFBF7", "surface": "#FFFFFF", "text": "#1C1917",
                "text_muted": "#78716C", "border": "#F2E8E0",
            },
            "dark": {
                "primary": "#FDBA74", "secondary": "#FED7AA", "accent": "#431407",
                "background": "#100B08", "surface": "#1D140E", "text": "#FFF7ED",
                "text_muted": "#B3A296", "border": "#2E211A",
            },
        },
    ],
    "bakery": [
        {  # Strawberry cream
            "light": {
                "primary": "#BE185D", "secondary": "#831843", "accent": "#FCE7F3",
                "background": "#FFFBFC", "surface": "#FFFFFF", "text": "#24151B",
                "text_muted": "#7E6A72", "border": "#F4E3EA",
            },
            "dark": {
                "primary": "#F9A8D4", "secondary": "#FBCFE8", "accent": "#500724",
                "background": "#120A0E", "surface": "#21141A", "text": "#FDF2F8",
                "text_muted": "#B39CA8", "border": "#33222A",
            },
        },
        {  # Pistachio
            "light": {
                "primary": "#65A30D", "secondary": "#3F6212", "accent": "#ECFCCB",
                "background": "#FCFFF4", "surface": "#FFFFFF", "text": "#1A2409",
                "text_muted": "#7A8465", "border": "#E5EDD5",
            },
            "dark": {
                "primary": "#BEF264", "secondary": "#D9F99D", "accent": "#365314",
                "background": "#0B0F05", "surface": "#161F0C", "text": "#F7FEE7",
                "text_muted": "#A6B48D", "border": "#29331A",
            },
        },
    ],
    "services": [
        {  # Emerald trust
            "light": {
                "primary": "#047857", "secondary": "#064E3B", "accent": "#D1FAE5",
                "background": "#F7FDFB", "surface": "#FFFFFF", "text": "#0F172A",
                "text_muted": "#64748B", "border": "#E2E8F0",
            },
            "dark": {
                "primary": "#34D399", "secondary": "#6EE7B7", "accent": "#064E3B",
                "background": "#06110E", "surface": "#0E1F1A", "text": "#ECFDF5",
                "text_muted": "#94A3B8", "border": "#1B332C",
            },
        },
        {  # Navy + amber
            "light": {
                "primary": "#1E3A8A", "secondary": "#172554", "accent": "#FEF3C7",
                "background": "#F8FAFF", "surface": "#FFFFFF", "text": "#0F172A",
                "text_muted": "#64748B", "border": "#E2E8F0",
            },
            "dark": {
                "primary": "#93C5FD", "secondary": "#FDE68A", "accent": "#1E3A8A",
                "background": "#0A0F1E", "surface": "#111A2E", "text": "#EFF6FF",
                "text_muted": "#94A3B8", "border": "#1E293B",
            },
        },
    ],
    "gym": [
        {  # Electric lime
            "light": {
                "primary": "#65A30D", "secondary": "#1A1A1A", "accent": "#ECFCCB",
                "background": "#FFFFFF", "surface": "#FAFAF9", "text": "#171717",
                "text_muted": "#737373", "border": "#E5E5E5",
            },
            "dark": {
                "primary": "#A3E635", "secondary": "#D9F99D", "accent": "#1A2E05",
                "background": "#0A0A0A", "surface": "#171717", "text": "#FAFAFA",
                "text_muted": "#A3A3A3", "border": "#262626",
            },
        },
        {  # Blue steel
            "light": {
                "primary": "#0369A1", "secondary": "#0C4A6E", "accent": "#E0F2FE",
                "background": "#F8FCFF", "surface": "#FFFFFF", "text": "#0F172A",
                "text_muted": "#64748B", "border": "#E2E8F0",
            },
            "dark": {
                "primary": "#38BDF8", "secondary": "#7DD3FC", "accent": "#0C4A6E",
                "background": "#071019", "surface": "#0E1B2A", "text": "#F0F9FF",
                "text_muted": "#94A3B8", "border": "#1C2B3A",
            },
        },
    ],
    "clinic": [
        {  # Calm blue
            "light": {
                "primary": "#0369A1", "secondary": "#075985", "accent": "#E0F2FE",
                "background": "#F8FCFF", "surface": "#FFFFFF", "text": "#0F172A",
                "text_muted": "#64748B", "border": "#E2E8F0",
            },
            "dark": {
                "primary": "#7DD3FC", "secondary": "#BAE6FD", "accent": "#0C4A6E",
                "background": "#071019", "surface": "#0E1B2A", "text": "#F0F9FF",
                "text_muted": "#94A3B8", "border": "#1C2B3A",
            },
        },
        {  # Warm sage wellness
            "light": {
                "primary": "#4D7C0F", "secondary": "#3F6212", "accent": "#ECFCCB",
                "background": "#FDFFF8", "surface": "#FFFFFF", "text": "#1C2A10",
                "text_muted": "#7A8465", "border": "#E7EDD8",
            },
            "dark": {
                "primary": "#BEF264", "secondary": "#D9F99D", "accent": "#365314",
                "background": "#0B0F05", "surface": "#161F0C", "text": "#F7FEE7",
                "text_muted": "#A6B48D", "border": "#29331A",
            },
        },
    ],
    "general": [
        {  # Deep cyan
            "light": {
                "primary": "#0E7490", "secondary": "#155E75", "accent": "#CFFAFE",
                "background": "#F7FDFF", "surface": "#FFFFFF", "text": "#0F172A",
                "text_muted": "#64748B", "border": "#E2E8F0",
            },
            "dark": {
                "primary": "#22D3EE", "secondary": "#67E8F9", "accent": "#155E75",
                "background": "#051318", "surface": "#0C232B", "text": "#ECFEFF",
                "text_muted": "#94A3B8", "border": "#164E63",
            },
        },
        {  # Graphite + coral
            "light": {
                "primary": "#E11D48", "secondary": "#9F1239", "accent": "#FFE4E6",
                "background": "#FFF9FA", "surface": "#FFFFFF", "text": "#1C1917",
                "text_muted": "#78716C", "border": "#F4E4E7",
            },
            "dark": {
                "primary": "#FB7185", "secondary": "#FDA4AF", "accent": "#4C0519",
                "background": "#130A0D", "surface": "#211318", "text": "#FFF1F2",
                "text_muted": "#B39BA3", "border": "#351E26",
            },
        },
    ],
}


# Full palettes for EXPLICIT user colour requests ("warna biru", "gold theme").
# When the user asks for a colour, this palette replaces the seeded pick
# entirely — user freedom beats the per-type default.
NAMED_COLOR_PALETTES = {
    "blue": {
        "light": {
            "primary": "#2563EB", "secondary": "#1E40AF", "accent": "#DBEAFE",
            "background": "#F8FAFF", "surface": "#FFFFFF", "text": "#0F172A",
            "text_muted": "#64748B", "border": "#E2E8F0",
        },
        "dark": {
            "primary": "#60A5FA", "secondary": "#93C5FD", "accent": "#1E3A5F",
            "background": "#0B1120", "surface": "#0F172A", "text": "#F1F5F9",
            "text_muted": "#94A3B8", "border": "#1E293B",
        },
    },
    "navy": {
        "light": {
            "primary": "#1E3A8A", "secondary": "#172554", "accent": "#DBEAFE",
            "background": "#F8FAFF", "surface": "#FFFFFF", "text": "#0F172A",
            "text_muted": "#64748B", "border": "#E2E8F0",
        },
        "dark": {
            "primary": "#93C5FD", "secondary": "#BFDBFE", "accent": "#1E3A8A",
            "background": "#0A0F1E", "surface": "#111A2E", "text": "#EFF6FF",
            "text_muted": "#94A3B8", "border": "#1E293B",
        },
    },
    "green": {
        "light": {
            "primary": "#16A34A", "secondary": "#166534", "accent": "#DCFCE7",
            "background": "#F9FDF9", "surface": "#FFFFFF", "text": "#122117",
            "text_muted": "#6B8068", "border": "#E3EFE4",
        },
        "dark": {
            "primary": "#4ADE80", "secondary": "#86EFAC", "accent": "#14532D",
            "background": "#09110C", "surface": "#14241A", "text": "#ECFDF3",
            "text_muted": "#9DB8A5", "border": "#1F3A2A",
        },
    },
    "red": {
        "light": {
            "primary": "#DC2626", "secondary": "#991B1B", "accent": "#FEE2E2",
            "background": "#FFFAFA", "surface": "#FFFFFF", "text": "#1C1917",
            "text_muted": "#78716C", "border": "#F3E2E2",
        },
        "dark": {
            "primary": "#F87171", "secondary": "#FCA5A5", "accent": "#450A0A",
            "background": "#0F0A0A", "surface": "#1D1414", "text": "#FEF2F2",
            "text_muted": "#B3A0A0", "border": "#2E2222",
        },
    },
    "maroon": {
        "light": {
            "primary": "#9F1239", "secondary": "#881337", "accent": "#FFE4E6",
            "background": "#FFFAFB", "surface": "#FFFFFF", "text": "#241419",
            "text_muted": "#7E6A6F", "border": "#F4E2E6",
        },
        "dark": {
            "primary": "#FB7185", "secondary": "#FDA4AF", "accent": "#4C0519",
            "background": "#130A0D", "surface": "#211318", "text": "#FFF1F2",
            "text_muted": "#B39BA3", "border": "#351E26",
        },
    },
    "purple": {
        "light": {
            "primary": "#7C3AED", "secondary": "#5B21B6", "accent": "#EDE9FE",
            "background": "#FCFAFF", "surface": "#FFFFFF", "text": "#1E1B2E",
            "text_muted": "#6D6A80", "border": "#EAE5F5",
        },
        "dark": {
            "primary": "#A78BFA", "secondary": "#C4B5FD", "accent": "#2E1065",
            "background": "#0C0817", "surface": "#161129", "text": "#F5F3FF",
            "text_muted": "#A5A0B8", "border": "#2A2440",
        },
    },
    "pink": {
        "light": {
            "primary": "#DB2777", "secondary": "#9D174D", "accent": "#FCE7F3",
            "background": "#FFFBFD", "surface": "#FFFFFF", "text": "#24151C",
            "text_muted": "#7E6A74", "border": "#F6E2EC",
        },
        "dark": {
            "primary": "#F472B6", "secondary": "#F9A8D4", "accent": "#500724",
            "background": "#120A0E", "surface": "#21141A", "text": "#FDF2F8",
            "text_muted": "#B39CA8", "border": "#33222A",
        },
    },
    "gold": {
        "light": {
            "primary": "#A16207", "secondary": "#713F12", "accent": "#FEF9C3",
            "background": "#FFFDF5", "surface": "#FFFFFF", "text": "#1C1917",
            "text_muted": "#78716C", "border": "#F0E9D2",
        },
        "dark": {
            "primary": "#EAB308", "secondary": "#FDE047", "accent": "#422006",
            "background": "#0E0C07", "surface": "#1C1917", "text": "#FEFCE8",
            "text_muted": "#A8A29E", "border": "#2C2824",
        },
    },
    "orange": {
        "light": {
            "primary": "#EA580C", "secondary": "#9A3412", "accent": "#FED7AA",
            "background": "#FFFBF5", "surface": "#FFFFFF", "text": "#1C1917",
            "text_muted": "#78716C", "border": "#F3E6DA",
        },
        "dark": {
            "primary": "#FB923C", "secondary": "#FDBA74", "accent": "#431407",
            "background": "#0C0A09", "surface": "#1C1917", "text": "#F5F5F4",
            "text_muted": "#A8A29E", "border": "#292524",
        },
    },
    "teal": {
        "light": {
            "primary": "#0D9488", "secondary": "#115E59", "accent": "#CCFBF1",
            "background": "#F7FFFD", "surface": "#FFFFFF", "text": "#102420",
            "text_muted": "#5F7A74", "border": "#DDEEE9",
        },
        "dark": {
            "primary": "#2DD4BF", "secondary": "#99F6E4", "accent": "#134E4A",
            "background": "#0A1210", "surface": "#0F1F1C", "text": "#F0FDFA",
            "text_muted": "#94A3B8", "border": "#1E3330",
        },
    },
    "brown": {
        "light": {
            "primary": "#92400E", "secondary": "#78350F", "accent": "#FEF3C7",
            "background": "#FFFDF7", "surface": "#FFFFFF", "text": "#1C1917",
            "text_muted": "#78716C", "border": "#EDE5D8",
        },
        "dark": {
            "primary": "#D9A45B", "secondary": "#E8C08A", "accent": "#3E2A12",
            "background": "#0E0A06", "surface": "#1B140C", "text": "#FBF3E7",
            "text_muted": "#B3A48E", "border": "#2E2416",
        },
    },
    "black": {
        "light": {
            "primary": "#18181B", "secondary": "#3F3F46", "accent": "#F4F4F5",
            "background": "#FFFFFF", "surface": "#FAFAFA", "text": "#18181B",
            "text_muted": "#71717A", "border": "#E4E4E7",
        },
        "dark": {
            "primary": "#E4E4E7", "secondary": "#A1A1AA", "accent": "#27272A",
            "background": "#09090B", "surface": "#18181B", "text": "#FAFAFA",
            "text_muted": "#A1A1AA", "border": "#27272A",
        },
    },
}


# Malay + English colour words → NAMED_COLOR_PALETTES key.
# Multi-word phrases must be checked before single words.
_COLOR_WORDS = [
    ("merah jambu", "pink"),
    ("biru laut", "teal"),
    ("biru gelap", "navy"),
    ("navy blue", "navy"),
    ("dark blue", "navy"),
    ("hijau daun", "green"),
    ("rose gold", "pink"),
    ("biru", "blue"),
    ("navy", "navy"),
    ("blue", "blue"),
    ("hijau", "green"),
    ("green", "green"),
    ("merah", "red"),
    ("red", "red"),
    ("maroon", "maroon"),
    ("ungu", "purple"),
    ("purple", "purple"),
    ("violet", "purple"),
    ("pink", "pink"),
    ("emas", "gold"),
    ("gold", "gold"),
    ("kuning", "gold"),
    ("yellow", "gold"),
    ("oren", "orange"),
    ("jingga", "orange"),
    ("orange", "orange"),
    ("teal", "teal"),
    ("turquoise", "teal"),
    ("cyan", "teal"),
    ("coklat", "brown"),
    ("brown", "brown"),
    ("hitam", "black"),
    ("black", "black"),
    ("putih", "black"),
    ("white", "black"),
]

# Style adjectives (Malay + English) → style hint key.
_STYLE_WORDS = [
    (("mewah", "luxury", "luxurious", "premium", "elegant", "elegan",
      "exclusive", "eksklusif", "classy", "berkelas"), "elegant"),
    (("minimalis", "minimalist", "minimal", "simple", "ringkas", "bersih",
      "clean"), "minimal"),
    (("ceria", "playful", "fun", "colourful", "colorful", "vibrant",
      "berwarna-warni", "cute", "comel"), "playful"),
    (("bold", "berani", "garang", "impactful", "striking"), "bold"),
    (("klasik", "classic", "traditional", "tradisional", "vintage", "retro",
      "warisan", "heritage"), "classic"),
]

# Words that signal the colour term is about DESIGN, not a product
# ("kek pandan hijau" must NOT force a green theme).
_DESIGN_CONTEXT = r"(?:warna|tema|theme|colou?r|color\s+scheme|design|reka\s*bentuk|latar|background|button|butang)"


def extract_design_preferences(description: str) -> dict:
    """Extract EXPLICIT design requests from the business description.

    Returns {"color": <named palette key or None>,
             "style_hint": <style key or None>}

    Colour detection is deliberately conservative: a colour word only counts
    when it appears next to a design word ("warna biru", "blue theme",
    "tema emas"), so product mentions like "kek pandan hijau" never
    hijack the palette.
    """
    prefs = {"color": None, "style_hint": None}
    if not description:
        return prefs

    text = description.lower()

    for word, palette_key in _COLOR_WORDS:
        escaped = re.escape(word)
        # design-word BEFORE colour ("warna biru", "tema warna biru laut")
        before = rf"{_DESIGN_CONTEXT}[\s\w]{{0,20}}?\b{escaped}\b"
        # colour BEFORE design-word ("biru theme", "gold design")
        after = rf"\b{escaped}\b\s*(?:{_DESIGN_CONTEXT})"
        if re.search(before, text) or re.search(after, text):
            prefs["color"] = palette_key
            logger.info(f"🎨 User requested colour theme: {palette_key} (matched '{word}')")
            break

    for words, hint in _STYLE_WORDS:
        for w in words:
            if re.search(rf"\b{re.escape(w)}\b", text):
                prefs["style_hint"] = hint
                break
        if prefs["style_hint"]:
            break

    return prefs


# ============================================================================
# LAYOUT TEMPLATES BY BUSINESS TYPE
# ============================================================================

LAYOUT_TEMPLATES = {
    "food": """LAYOUT STRUCTURE (Editorial style - MUST FOLLOW):
1. HERO: Full-screen image with gradient overlay, business name centered at bottom, optional factual kicker badge above name ONLY if the business data provides one (NEVER invent "Est." years, "Halal"/certifications, or ownership claims), two CTA buttons
2. ABOUT: Split section - image on left (rounded-2xl), story text on right with decorative accent
3. FEATURED: Full-width spotlight of a signature dish/item with large image and description
4. MENU/GALLERY: 3-column grid of menu items with hover card lift effect, staggered animations
5. TESTIMONIALS: Customer reviews section with quote marks and star ratings
6. CONTACT: Contact info with WhatsApp CTA, operating hours
7. FOOTER: Business name, quick links, social icons""",

    "cafe": """LAYOUT STRUCTURE (Editorial style - MUST FOLLOW):
1. HERO: Full-screen image with gradient overlay from bottom, elegant centered text with serif heading
2. ABOUT: Split section - text left describing the cafe vibe, atmospheric image right
3. MENU: Featured drinks/items in an asymmetric grid layout with prices
4. GALLERY: 3-column masonry-style image grid showing ambiance
5. TESTIMONIALS: Customer quotes with minimal styling
6. CONTACT: Location, hours, WiFi availability, social links
7. FOOTER: Minimal footer with essential info""",

    "salon": """LAYOUT STRUCTURE (Showcase style - MUST FOLLOW):
1. HERO: Split hero - large image on right side, text + CTA on left side with elegant typography
2. SERVICES: Service cards grid with icon overlays and pricing, glassmorphism effect
3. GALLERY: Portfolio/Before-After style gallery in masonry layout
4. PRICING: Pricing cards with glassmorphism backdrop-blur effect
5. TEAM: Staff/stylist profiles with circular images
6. BOOKING CTA: Full-width banner with gradient background and booking button
7. CONTACT: Contact details and operating hours
8. FOOTER: Elegant footer with business info""",

    "clothing": """LAYOUT STRUCTURE (Storefront style - MUST FOLLOW):
1. HERO: Minimal hero with very large heading text, product image on right with decorative blob behind it
2. CATEGORIES: Large category cards with overlapping elements and subtle shadows
3. PRODUCTS: Asymmetric product grid with hover zoom effect on images
4. BRAND STORY: Full-width section with large background, brand narrative text overlay
5. REVIEWS: Customer testimonials with product photos
6. ORDER CTA: WhatsApp order banner with call-to-action
7. FOOTER: Footer with quick links and social media""",

    "bakery": """LAYOUT STRUCTURE (Storefront style - MUST FOLLOW):
1. HERO: Warm, inviting hero with full image, cursive heading overlay, CTA for ordering
2. FEATURED: Signature item spotlight with large image and story
3. PRODUCTS: Grid of baked goods with warm-toned cards, prices, and order buttons
4. ABOUT: Story section about the bakery's passion, with parallax-feel image
5. CUSTOM ORDERS: Section for custom cake/order info with WhatsApp CTA
6. REVIEWS: Customer testimonials
7. CONTACT: Location, hours, order info
8. FOOTER: Warm footer with essential info""",

    "services": """LAYOUT STRUCTURE (Professional style - MUST FOLLOW):
1. HERO: Clean hero with headline + subtext + two CTAs (primary and outline)
2. STATS BAR: Horizontal bar with key numbers (years experience, customers served, projects completed)
3. SERVICES: Alternating left-right sections for each service with icon and description
4. PROCESS: Step-by-step "How It Works" section (3-4 steps with numbered circles)
5. TESTIMONIALS: Client testimonials with company/name
6. FAQ: Accordion-style frequently asked questions
7. CONTACT: Contact form layout + WhatsApp CTA + location
8. FOOTER: Professional footer with links""",

    "gym": """LAYOUT STRUCTURE (Professional Bold style - MUST FOLLOW):
1. HERO: High-impact hero with bold uppercase heading, energetic gradient overlay
2. STATS: Key numbers bar (members, classes, trainers)
3. PROGRAMS: Service/class cards in grid with bold typography
4. SCHEDULE: Weekly schedule or class timetable section
5. TRAINERS: Team section with trainer profiles
6. MEMBERSHIP: Pricing/membership tier cards
7. CTA BANNER: Join now banner with strong call-to-action
8. CONTACT: Location and contact info
9. FOOTER: Footer with links""",

    "clinic": """LAYOUT STRUCTURE (Professional Clean style - MUST FOLLOW):
1. HERO: Clean, trustworthy hero with professional image, headline, and appointment CTA
2. SERVICES: Medical/health service cards with clean icons
3. ABOUT: Doctor/team credentials and clinic story
4. PROCESS: How to book / patient journey steps
5. TESTIMONIALS: Patient reviews
6. FAQ: Common questions accordion
7. CONTACT: Appointment booking CTA, location, hours
8. FOOTER: Professional footer""",

    "general": """LAYOUT STRUCTURE (Professional style - MUST FOLLOW):
1. HERO: Clean hero with headline + subtext + CTA button
2. ABOUT: Brief business introduction with image
3. PRODUCTS/SERVICES: Grid of offerings with cards
4. FEATURES: Key selling points or unique value propositions
5. TESTIMONIALS: Customer reviews
6. CONTACT: Contact info with WhatsApp CTA
7. FOOTER: Footer with links and info""",
}


# ============================================================================
# HERO SECTION VARIANTS BY BUSINESS TYPE
# ============================================================================

HERO_VARIANTS = {
    "food": """HERO SECTION DESIGN (Full-bleed with bottom text):
<section id="home" class="relative h-[70vh] min-h-[400px]" data-aos="fade-in">
  <img src="HERO_IMAGE_URL" class="absolute inset-0 w-full h-full object-cover" alt="HERO_ALT_TEXT">
  <div class="absolute inset-0 bg-gradient-to-t from-black/70 via-black/30 to-transparent"></div>
  <div class="relative z-10 flex items-end h-full pb-16 md:pb-20 px-6 md:px-16">
    <div class="max-w-2xl">
      <span class="inline-flex px-4 py-1.5 rounded-full bg-primary/20 backdrop-blur-sm text-white text-sm font-medium mb-4">TAGLINE_KICKER</span>
      <h1 class="text-4xl md:text-6xl lg:text-7xl font-heading font-bold text-white leading-tight tracking-tight">BUSINESS_NAME</h1>
      <p class="text-lg md:text-xl text-white/80 mt-4 font-body">TAGLINE</p>
      <div class="flex flex-wrap gap-4 mt-8">
        <a href="#menu" class="inline-flex items-center px-8 py-3.5 bg-primary text-white rounded-full font-body font-semibold tracking-wide hover:-translate-y-1 hover:shadow-2xl transition-all duration-300">VIEW_MENU_CTA</a>
        <a href="WHATSAPP_LINK" class="inline-flex items-center px-8 py-3.5 border-2 border-white/40 text-white rounded-full font-body font-semibold tracking-wide hover:bg-white/10 transition-all duration-300">WHATSAPP_CTA</a>
      </div>
    </div>
  </div>
</section>""",

    "cafe": """HERO SECTION DESIGN (Full-bleed atmospheric):
<section id="home" class="relative h-[70vh] min-h-[400px]" data-aos="fade-in">
  <img src="HERO_IMAGE_URL" class="absolute inset-0 w-full h-full object-cover" alt="HERO_ALT_TEXT">
  <div class="absolute inset-0 bg-gradient-to-t from-black/60 via-black/20 to-transparent"></div>
  <div class="relative z-10 flex items-center justify-center h-full text-center px-6">
    <div class="max-w-3xl">
      <h1 class="text-5xl md:text-7xl font-heading font-bold text-white leading-tight tracking-tight">BUSINESS_NAME</h1>
      <p class="text-lg md:text-xl text-white/80 mt-4 font-body">TAGLINE</p>
      <a href="#menu" class="inline-flex items-center mt-8 px-8 py-3.5 bg-primary text-white rounded-full font-body font-semibold tracking-wide hover:-translate-y-1 hover:shadow-2xl transition-all duration-300">VIEW_MENU_CTA</a>
    </div>
  </div>
</section>""",

    "salon": """HERO SECTION DESIGN (Split hero - text left, image right):
<section id="home" class="grid md:grid-cols-2 min-h-screen">
  <div class="flex items-center px-8 md:px-16 py-20 order-2 md:order-1" data-aos="fade-right">
    <div>
      <span class="inline-flex px-4 py-1.5 rounded-full bg-primary/10 text-primary text-sm font-body font-medium mb-6">TAGLINE_KICKER</span>
      <h1 class="text-4xl md:text-5xl lg:text-7xl font-heading leading-tight tracking-tight" style="color: var(--text-color)">BUSINESS_NAME</h1>
      <p class="text-lg mt-4 font-body" style="color: var(--text-muted-color)">TAGLINE</p>
      <a href="#services" class="inline-flex items-center mt-8 px-8 py-3.5 bg-primary text-white rounded-full font-body font-semibold tracking-wide hover:-translate-y-1 hover:shadow-2xl transition-all duration-300">VIEW_SERVICES_CTA</a>
    </div>
  </div>
  <div class="relative order-1 md:order-2 min-h-[400px]" data-aos="fade-left">
    <img src="HERO_IMAGE_URL" class="absolute inset-0 w-full h-full object-cover" alt="HERO_ALT_TEXT">
  </div>
</section>""",

    "clothing": """HERO SECTION DESIGN (Minimal with large text + image):
<section id="home" class="relative overflow-hidden py-24 md:py-32 px-6 md:px-8" style="background-color: var(--bg-color)">
  <div class="max-w-7xl mx-auto grid md:grid-cols-2 gap-12 items-center">
    <div data-aos="fade-right">
      <h1 class="text-5xl md:text-6xl lg:text-8xl font-heading leading-none tracking-tight" style="color: var(--text-color)">BUSINESS_NAME</h1>
      <p class="text-xl mt-6 font-body" style="color: var(--text-muted-color)">TAGLINE</p>
      <a href="#products" class="inline-flex items-center mt-8 px-8 py-3.5 bg-primary text-white rounded-full font-body font-semibold tracking-wide hover:-translate-y-1 hover:shadow-2xl transition-all duration-300">SHOP_CTA</a>
    </div>
    <div class="relative" data-aos="fade-left">
      <img src="HERO_IMAGE_URL" class="rounded-3xl shadow-2xl w-full" alt="HERO_ALT_TEXT">
      <div class="absolute -bottom-6 -left-6 w-32 h-32 bg-primary/20 rounded-full blur-2xl"></div>
    </div>
  </div>
</section>""",

    "bakery": """HERO SECTION DESIGN (Warm full-bleed):
<section id="home" class="relative h-[70vh] min-h-[400px]" data-aos="fade-in">
  <img src="HERO_IMAGE_URL" class="absolute inset-0 w-full h-full object-cover" alt="HERO_ALT_TEXT">
  <div class="absolute inset-0 bg-gradient-to-t from-black/60 via-black/20 to-transparent"></div>
  <div class="relative z-10 flex items-end h-full pb-16 md:pb-20 px-6 md:px-16">
    <div class="max-w-2xl">
      <h1 class="text-4xl md:text-6xl lg:text-7xl font-heading font-bold text-white leading-tight">BUSINESS_NAME</h1>
      <p class="text-lg md:text-xl text-white/80 mt-4 font-body">TAGLINE</p>
      <a href="#products" class="inline-flex items-center mt-8 px-8 py-3.5 bg-primary text-white rounded-full font-body font-semibold tracking-wide hover:-translate-y-1 hover:shadow-2xl transition-all duration-300">ORDER_CTA</a>
    </div>
  </div>
</section>""",

    "services": """HERO SECTION DESIGN (Clean professional with 2 CTAs):
<section id="home" class="relative py-24 md:py-32 px-6 md:px-8" style="background-color: var(--bg-color)">
  <div class="max-w-7xl mx-auto grid md:grid-cols-2 gap-12 items-center">
    <div data-aos="fade-right">
      <span class="inline-flex px-4 py-1.5 rounded-full bg-primary/10 text-primary text-sm font-body font-medium mb-6">TAGLINE_KICKER</span>
      <h1 class="text-4xl md:text-5xl lg:text-6xl font-heading font-bold leading-tight tracking-tight" style="color: var(--text-color)">BUSINESS_NAME</h1>
      <p class="text-lg md:text-xl mt-4 font-body" style="color: var(--text-muted-color)">TAGLINE</p>
      <div class="flex flex-wrap gap-4 mt-8">
        <a href="#services" class="inline-flex items-center px-8 py-3.5 bg-primary text-white rounded-full font-body font-semibold tracking-wide hover:-translate-y-1 hover:shadow-2xl transition-all duration-300">VIEW_SERVICES_CTA</a>
        <a href="WHATSAPP_LINK" class="inline-flex items-center px-8 py-3.5 border-2 border-primary/30 text-primary rounded-full font-body font-semibold tracking-wide hover:bg-primary/5 transition-all duration-300">WHATSAPP_CTA</a>
      </div>
    </div>
    <div class="relative" data-aos="fade-left">
      <img src="HERO_IMAGE_URL" class="rounded-3xl shadow-2xl w-full" alt="HERO_ALT_TEXT">
    </div>
  </div>
</section>""",

    "gym": """HERO SECTION DESIGN (High-impact bold):
<section id="home" class="relative h-[70vh] min-h-[400px]" data-aos="fade-in">
  <img src="HERO_IMAGE_URL" class="absolute inset-0 w-full h-full object-cover" alt="HERO_ALT_TEXT">
  <div class="absolute inset-0 bg-gradient-to-r from-black/80 via-black/50 to-transparent"></div>
  <div class="relative z-10 flex items-center h-full px-6 md:px-16">
    <div class="max-w-2xl">
      <h1 class="text-5xl md:text-7xl lg:text-8xl font-heading font-bold text-white uppercase tracking-wider">BUSINESS_NAME</h1>
      <p class="text-lg md:text-xl text-white/80 mt-4 font-body">TAGLINE</p>
      <a href="#programs" class="inline-flex items-center mt-8 px-10 py-4 bg-primary text-white rounded-full font-body font-bold text-lg tracking-wide uppercase hover:-translate-y-1 hover:shadow-2xl transition-all duration-300">JOIN_CTA</a>
    </div>
  </div>
</section>""",

    "clinic": """HERO SECTION DESIGN (Clean trustworthy):
<section id="home" class="relative py-24 md:py-32 px-6 md:px-8" style="background-color: var(--bg-color)">
  <div class="max-w-7xl mx-auto grid md:grid-cols-2 gap-12 items-center">
    <div data-aos="fade-right">
      <span class="inline-flex px-4 py-1.5 rounded-full bg-primary/10 text-primary text-sm font-body font-medium mb-6">TAGLINE_KICKER</span>
      <h1 class="text-4xl md:text-5xl lg:text-6xl font-heading font-bold leading-tight tracking-tight" style="color: var(--text-color)">BUSINESS_NAME</h1>
      <p class="text-lg md:text-xl mt-4 font-body" style="color: var(--text-muted-color)">TAGLINE</p>
      <a href="#services" class="inline-flex items-center mt-8 px-8 py-3.5 bg-primary text-white rounded-full font-body font-semibold tracking-wide hover:-translate-y-1 hover:shadow-2xl transition-all duration-300">BOOK_CTA</a>
    </div>
    <div class="relative" data-aos="fade-left">
      <img src="HERO_IMAGE_URL" class="rounded-3xl shadow-2xl w-full" alt="HERO_ALT_TEXT">
    </div>
  </div>
</section>""",

    "general": """HERO SECTION DESIGN (Clean with image):
<section id="home" class="relative py-24 md:py-32 px-6 md:px-8" style="background-color: var(--bg-color)">
  <div class="max-w-7xl mx-auto grid md:grid-cols-2 gap-12 items-center">
    <div data-aos="fade-right">
      <h1 class="text-4xl md:text-5xl lg:text-6xl font-heading font-bold leading-tight tracking-tight" style="color: var(--text-color)">BUSINESS_NAME</h1>
      <p class="text-lg md:text-xl mt-4 font-body" style="color: var(--text-muted-color)">TAGLINE</p>
      <a href="#products" class="inline-flex items-center mt-8 px-8 py-3.5 bg-primary text-white rounded-full font-body font-semibold tracking-wide hover:-translate-y-1 hover:shadow-2xl transition-all duration-300">VIEW_PRODUCTS_CTA</a>
    </div>
    <div class="relative" data-aos="fade-left">
      <img src="HERO_IMAGE_URL" class="rounded-3xl shadow-2xl w-full" alt="HERO_ALT_TEXT">
    </div>
  </div>
</section>""",
}

# No-images hero variants
HERO_VARIANTS_NO_IMAGES = {
    "food": """HERO SECTION DESIGN (Gradient, NO images):
<section id="home" class="relative h-[70vh] min-h-[500px] overflow-hidden" data-aos="fade-in">
  <div class="absolute inset-0 bg-gradient-to-br from-primary via-secondary to-primary/80"></div>
  <div class="absolute inset-0 bg-[radial-gradient(circle_at_30%_50%,rgba(255,255,255,0.1)_0%,transparent_60%)]"></div>
  <div class="relative z-10 flex items-center justify-center h-full text-center px-6">
    <div class="max-w-3xl">
      <span class="inline-flex px-4 py-1.5 rounded-full bg-white/20 backdrop-blur-sm text-white text-sm font-medium mb-6">TAGLINE_KICKER</span>
      <h1 class="text-4xl md:text-6xl lg:text-7xl font-heading font-bold text-white leading-tight tracking-tight">BUSINESS_NAME</h1>
      <p class="text-lg md:text-xl text-white/80 mt-4 font-body">TAGLINE</p>
      <a href="#menu" class="inline-flex items-center mt-8 px-8 py-3.5 bg-white text-primary rounded-full font-body font-semibold tracking-wide hover:-translate-y-1 hover:shadow-2xl transition-all duration-300">VIEW_MENU_CTA</a>
    </div>
  </div>
</section>""",

    "default": """HERO SECTION DESIGN (Gradient, NO images):
<section id="home" class="relative h-[70vh] min-h-[500px] overflow-hidden" data-aos="fade-in">
  <div class="absolute inset-0 bg-gradient-to-br from-primary via-secondary to-primary/80"></div>
  <div class="absolute inset-0 bg-[radial-gradient(circle_at_30%_50%,rgba(255,255,255,0.1)_0%,transparent_60%)]"></div>
  <div class="relative z-10 flex items-center justify-center h-full text-center px-6">
    <div class="max-w-3xl">
      <h1 class="text-4xl md:text-6xl lg:text-7xl font-heading font-bold text-white leading-tight tracking-tight">BUSINESS_NAME</h1>
      <p class="text-lg md:text-xl text-white/80 mt-4 font-body">TAGLINE</p>
      <a href="#services" class="inline-flex items-center mt-8 px-8 py-3.5 bg-white text-primary rounded-full font-body font-semibold tracking-wide hover:-translate-y-1 hover:shadow-2xl transition-all duration-300">CTA_TEXT</a>
    </div>
  </div>
</section>""",
}


# Alternate hero designs per business type. Index 0 is always the classic
# HERO_VARIANTS entry; the seeded pick rotates across the whole list so two
# restaurants stop opening with the identical hero.
ALT_HERO_VARIANTS = {
    "food": [
        """HERO SECTION DESIGN (Split hero — text left, tall image right with floating card):
<section id="home" class="grid md:grid-cols-2 min-h-[85vh]" style="background-color: var(--bg-color)">
  <div class="flex items-center px-6 md:px-16 py-20 order-2 md:order-1" data-aos="fade-right">
    <div>
      <span class="inline-flex px-4 py-1.5 rounded-full bg-primary/10 text-primary text-sm font-body font-medium mb-6">TAGLINE_KICKER</span>
      <h1 class="font-heading font-bold leading-[1.05] tracking-tight" style="font-size: clamp(2.5rem, 6vw, 4.5rem); color: var(--text-color)">BUSINESS_NAME</h1>
      <p class="text-lg md:text-xl mt-5 font-body" style="color: var(--text-muted-color)">TAGLINE</p>
      <div class="flex flex-wrap gap-4 mt-8">
        <a href="#menu" class="inline-flex items-center px-8 py-3.5 bg-primary text-white rounded-full font-body font-semibold tracking-wide hover:-translate-y-1 hover:shadow-2xl transition-all duration-300">VIEW_MENU_CTA</a>
        <a href="WHATSAPP_LINK" class="inline-flex items-center px-8 py-3.5 border-2 border-primary/30 text-primary rounded-full font-body font-semibold tracking-wide hover:bg-primary/5 transition-all duration-300">WHATSAPP_CTA</a>
      </div>
    </div>
  </div>
  <div class="relative order-1 md:order-2 min-h-[320px] md:min-h-0" data-aos="fade-left">
    <img src="HERO_IMAGE_URL" class="absolute inset-0 w-full h-full object-cover" alt="HERO_ALT_TEXT">
    <div class="hidden md:block absolute bottom-8 -left-10 bg-white/95 backdrop-blur rounded-2xl shadow-2xl px-6 py-4 max-w-[240px]">
      <p class="text-sm font-body font-semibold" style="color: #1C1917">SIGNATURE_DISH_NAME</p>
      <p class="text-xs font-body mt-1" style="color: #78716C">SIGNATURE_DISH_NOTE</p>
    </div>
  </div>
</section>""",
        """HERO SECTION DESIGN (Full-bleed cinematic, centered, scroll cue):
<section id="home" class="relative h-[88vh] min-h-[480px]" data-aos="fade-in">
  <img src="HERO_IMAGE_URL" class="absolute inset-0 w-full h-full object-cover" alt="HERO_ALT_TEXT">
  <div class="absolute inset-0 bg-gradient-to-b from-black/40 via-black/25 to-black/70"></div>
  <div class="relative z-10 flex flex-col items-center justify-center h-full text-center px-6">
    <p class="text-white/80 font-body text-sm uppercase tracking-[0.35em] mb-5">TAGLINE_KICKER</p>
    <h1 class="font-heading font-bold text-white leading-[1.02] tracking-tight" style="font-size: clamp(2.75rem, 8vw, 5.5rem)">BUSINESS_NAME</h1>
    <p class="text-lg md:text-xl text-white/85 mt-5 max-w-2xl font-body">TAGLINE</p>
    <div class="flex flex-wrap justify-center gap-4 mt-9">
      <a href="#menu" class="inline-flex items-center px-8 py-3.5 bg-primary text-white rounded-full font-body font-semibold tracking-wide hover:-translate-y-1 hover:shadow-2xl transition-all duration-300">VIEW_MENU_CTA</a>
      <a href="WHATSAPP_LINK" class="inline-flex items-center px-8 py-3.5 bg-white/10 backdrop-blur border border-white/30 text-white rounded-full font-body font-semibold tracking-wide hover:bg-white/20 transition-all duration-300">WHATSAPP_CTA</a>
    </div>
    <a href="#about" class="absolute bottom-8 text-white/70 hover:text-white transition-colors" aria-label="Scroll"><i class="fa-solid fa-chevron-down fa-bounce"></i></a>
  </div>
</section>""",
    ],
    "services": [
        """HERO SECTION DESIGN (Centered with stat chips):
<section id="home" class="relative py-24 md:py-36 px-6 md:px-8 overflow-hidden" style="background-color: var(--bg-color)">
  <div class="absolute -top-24 -right-24 w-96 h-96 bg-primary/5 rounded-full blur-3xl"></div>
  <div class="absolute -bottom-24 -left-24 w-96 h-96 bg-primary/5 rounded-full blur-3xl"></div>
  <div class="relative max-w-4xl mx-auto text-center" data-aos="fade-up">
    <span class="inline-flex px-4 py-1.5 rounded-full bg-primary/10 text-primary text-sm font-body font-medium mb-6">TAGLINE_KICKER</span>
    <h1 class="font-heading font-bold leading-[1.08] tracking-tight" style="font-size: clamp(2.5rem, 6vw, 4.25rem); color: var(--text-color)">BUSINESS_NAME</h1>
    <p class="text-lg md:text-xl mt-5 max-w-2xl mx-auto font-body" style="color: var(--text-muted-color)">TAGLINE</p>
    <div class="flex flex-wrap justify-center gap-4 mt-9">
      <a href="#services" class="inline-flex items-center px-8 py-3.5 bg-primary text-white rounded-full font-body font-semibold tracking-wide hover:-translate-y-1 hover:shadow-2xl transition-all duration-300">VIEW_SERVICES_CTA</a>
      <a href="WHATSAPP_LINK" class="inline-flex items-center px-8 py-3.5 border-2 border-primary/30 text-primary rounded-full font-body font-semibold tracking-wide hover:bg-primary/5 transition-all duration-300">WHATSAPP_CTA</a>
    </div>
  </div>
</section>""",
    ],
    "salon": [
        """HERO SECTION DESIGN (Full-bleed with offset editorial text):
<section id="home" class="relative h-[85vh] min-h-[460px]" data-aos="fade-in">
  <img src="HERO_IMAGE_URL" class="absolute inset-0 w-full h-full object-cover" alt="HERO_ALT_TEXT">
  <div class="absolute inset-0 bg-gradient-to-r from-black/65 via-black/30 to-transparent"></div>
  <div class="relative z-10 flex items-center h-full px-6 md:px-20">
    <div class="max-w-xl">
      <p class="text-white/75 font-body text-sm uppercase tracking-[0.3em] mb-5">TAGLINE_KICKER</p>
      <h1 class="font-heading text-white leading-[1.05] tracking-tight" style="font-size: clamp(2.5rem, 7vw, 5rem)">BUSINESS_NAME</h1>
      <p class="text-lg text-white/85 mt-5 font-body">TAGLINE</p>
      <a href="#services" class="inline-flex items-center mt-8 px-8 py-3.5 bg-white text-black rounded-full font-body font-semibold tracking-wide hover:-translate-y-1 hover:shadow-2xl transition-all duration-300">VIEW_SERVICES_CTA</a>
    </div>
  </div>
</section>""",
    ],
    "clothing": [
        """HERO SECTION DESIGN (Editorial center, oversized type over image band):
<section id="home" class="relative pt-24 pb-0 px-0 overflow-hidden" style="background-color: var(--bg-color)">
  <div class="max-w-5xl mx-auto text-center px-6" data-aos="fade-up">
    <p class="font-body text-sm uppercase tracking-[0.35em] mb-4" style="color: var(--text-muted-color)">TAGLINE_KICKER</p>
    <h1 class="font-heading leading-[0.95] tracking-tight" style="font-size: clamp(3rem, 10vw, 7rem); color: var(--text-color)">BUSINESS_NAME</h1>
    <p class="text-lg md:text-xl mt-5 font-body max-w-xl mx-auto" style="color: var(--text-muted-color)">TAGLINE</p>
    <a href="#products" class="inline-flex items-center mt-8 px-9 py-4 bg-primary text-white rounded-full font-body font-semibold tracking-wide hover:-translate-y-1 hover:shadow-2xl transition-all duration-300">SHOP_CTA</a>
  </div>
  <div class="mt-14 relative h-[45vh] min-h-[320px]" data-aos="fade-up" data-aos-delay="150">
    <img src="HERO_IMAGE_URL" class="absolute inset-0 w-full h-full object-cover" alt="HERO_ALT_TEXT">
  </div>
</section>""",
    ],
    "general": [
        """HERO SECTION DESIGN (Centered minimal with image band below):
<section id="home" class="relative pt-24 md:pt-32 pb-0 overflow-hidden" style="background-color: var(--bg-color)">
  <div class="max-w-4xl mx-auto text-center px-6" data-aos="fade-up">
    <span class="inline-flex px-4 py-1.5 rounded-full bg-primary/10 text-primary text-sm font-body font-medium mb-6">TAGLINE_KICKER</span>
    <h1 class="font-heading font-bold leading-[1.05] tracking-tight" style="font-size: clamp(2.5rem, 6.5vw, 4.5rem); color: var(--text-color)">BUSINESS_NAME</h1>
    <p class="text-lg md:text-xl mt-5 font-body max-w-2xl mx-auto" style="color: var(--text-muted-color)">TAGLINE</p>
    <a href="#products" class="inline-flex items-center mt-8 px-8 py-3.5 bg-primary text-white rounded-full font-body font-semibold tracking-wide hover:-translate-y-1 hover:shadow-2xl transition-all duration-300">VIEW_PRODUCTS_CTA</a>
  </div>
  <div class="mt-14 max-w-6xl mx-auto px-6" data-aos="fade-up" data-aos-delay="150">
    <img src="HERO_IMAGE_URL" class="rounded-t-3xl shadow-2xl w-full max-h-[55vh] object-cover" alt="HERO_ALT_TEXT">
  </div>
</section>""",
    ],
}


# ============================================================================
# DESIGN PERSONALITIES — a seeded "art direction voice" layered on top of the
# structural blueprint, so pages differ in feel, not just in colours.
# ============================================================================

DESIGN_PERSONALITIES = {
    "editorial": {
        "name": "Editorial Magazine",
        "prompt": """DESIGN PERSONALITY — EDITORIAL MAGAZINE:
- Asymmetric layouts: offset headings, images that break the grid slightly, two-column text blocks
- Numbered section kickers: small uppercase labels like "01 — TENTANG KAMI" above each section heading
- Oversized display headings with tight leading; italic serif accents on one or two key words
- Thin horizontal rules (border-t) as section dividers; generous whitespace
- Captions under images in small muted text""",
    },
    "soft_organic": {
        "name": "Soft Organic",
        "prompt": """DESIGN PERSONALITY — SOFT ORGANIC:
- Generous rounded corners everywhere (rounded-3xl); pill-shaped badges and buttons
- Soft blurred colour blobs behind sections (bg-primary/5 blur-3xl) and one section with a subtle tinted background
- Friendly, warm microcopy; icons inside soft tinted circles (bg-primary/10 rounded-full p-4)
- Cards with soft diffused shadows (shadow-lg shadow-primary/5), never hard edges
- Overlapping elements: an image slightly overlapping its section boundary""",
    },
    "refined_luxe": {
        "name": "Refined Luxe",
        "prompt": """DESIGN PERSONALITY — REFINED LUXE:
- Hairline borders (border, 1px, low-opacity) instead of heavy shadows; muted, restrained colour usage
- Letterspaced uppercase kickers: text-xs uppercase tracking-[0.3em] above headings
- Large serif display headings; generous negative space (py-28+ sections)
- Buttons: slim, wide padding, subtle hover (no bounce); images framed with thin borders
- One metallic-feeling accent detail per section maximum — restraint is the luxury""",
    },
    "bold_contrast": {
        "name": "Bold Contrast",
        "prompt": """DESIGN PERSONALITY — BOLD CONTRAST:
- Oversized headings (clamp up to 6rem) with heavy weight; short punchy copy
- Strong colour blocking: at least one full-width band section in the primary colour with white text
- Thick underline or highlight accents on key words (decoration-4 underline-offset-8 or a background highlight span)
- Big stat numbers (text-5xl+); solid buttons with strong hover states
- High-contrast section alternation: light section → tinted section → colour-block section""",
    },
    "modern_minimal": {
        "name": "Modern Minimal",
        "prompt": """DESIGN PERSONALITY — MODERN MINIMAL:
- Strict grid alignment; consistent max-w container; no decorative shapes or blobs
- Neutral surfaces with ONE accent colour used only on CTAs and small details
- Small uppercase labels, restrained heading sizes, plenty of whitespace
- Cards separated by borders (border border-gray-200) rather than shadows
- Underlined text links instead of secondary buttons where appropriate""",
    },
    "warm_crafted": {
        "name": "Warm Crafted",
        "prompt": """DESIGN PERSONALITY — WARM CRAFTED:
- Warm tinted backgrounds alternating with white sections; cream instead of stark white
- Rounded-2xl cards with soft warm shadows (shadow-orange-900/5 style, matched to palette)
- Hand-crafted feel: slightly imperfect layouts, an offset polaroid-style framed image with padding and shadow
- Icons and small illustrative touches in tinted circles; dotted or wavy divider accents
- Conversational, warm copy tone""",
    },
}

# Which personalities suit each design type (seeded pick from this list).
PERSONALITY_POOL = {
    "food": ["editorial", "warm_crafted", "bold_contrast", "soft_organic"],
    "cafe": ["editorial", "warm_crafted", "refined_luxe", "modern_minimal"],
    "salon": ["refined_luxe", "editorial", "modern_minimal", "soft_organic"],
    "clothing": ["editorial", "modern_minimal", "bold_contrast", "refined_luxe"],
    "bakery": ["warm_crafted", "soft_organic", "editorial", "refined_luxe"],
    "services": ["modern_minimal", "bold_contrast", "editorial", "refined_luxe"],
    "gym": ["bold_contrast", "modern_minimal", "editorial"],
    "clinic": ["modern_minimal", "soft_organic", "refined_luxe"],
    "general": ["modern_minimal", "editorial", "soft_organic", "bold_contrast", "warm_crafted"],
}

# Style hints extracted from the user's description force a personality.
_STYLE_HINT_TO_PERSONALITY = {
    "elegant": "refined_luxe",
    "minimal": "modern_minimal",
    "playful": "soft_organic",
    "bold": "bold_contrast",
    "classic": "warm_crafted",
}


class DesignSystem:
    """Complete design system for premium website generation"""

    @staticmethod
    def _font_options(business_type: str) -> list:
        base = FONT_PAIRINGS.get(business_type, FONT_PAIRINGS["general"])
        alts = ALT_FONT_PAIRINGS.get(business_type, ALT_FONT_PAIRINGS["general"])
        return [base] + list(alts)

    @staticmethod
    def _palette_options(business_type: str) -> list:
        base = COLOR_PALETTES.get(business_type, COLOR_PALETTES["general"])
        alts = ALT_COLOR_PALETTES.get(business_type, ALT_COLOR_PALETTES["general"])
        return [base] + list(alts)

    @staticmethod
    def _hero_options(business_type: str) -> list:
        base = HERO_VARIANTS.get(business_type, HERO_VARIANTS["general"])
        alts = ALT_HERO_VARIANTS.get(business_type, [])
        return [base] + list(alts)

    @staticmethod
    def _build_font_cdn(pairing: dict) -> dict:
        heading_encoded = pairing["heading"].replace(" ", "+")
        body_encoded = pairing["body"].replace(" ", "+")
        cdn_link = (
            f'<link rel="preconnect" href="https://fonts.googleapis.com">\n'
            f'<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
            f'<link href="https://fonts.googleapis.com/css2?family={heading_encoded}:wght@{pairing["heading_weights"]}'
            f'&family={body_encoded}:wght@{pairing["body_weights"]}&display=swap" rel="stylesheet">'
        )
        return {
            **pairing,
            "cdn_link": cdn_link,
        }

    def get_font_pairing(
        self, business_type: str, business_name: str = "", variant: int = 0
    ) -> dict:
        """Get font pairing for a business type.

        With a business_name, the pairing is a deterministic seeded pick from
        this type's pool (variety across businesses, stability per business).
        Without one, the classic pairing is returned (backward compatible).
        `variant` walks the pick forward for the "shuffle design" re-roll.
        """
        options = self._font_options(business_type)
        if business_name:
            pairing = _pick(options, _variant_seed(business_name), 1, variant)
        elif variant:
            pairing = options[int(variant) % len(options)]
        else:
            pairing = options[0]
        return self._build_font_cdn(pairing)

    def get_color_palette(
        self,
        business_type: str,
        color_mode: str = "light",
        business_name: str = "",
        color_override: str = None,
        variant: int = 0,
    ) -> dict:
        """Get color palette for a business type and color mode.

        color_override (a NAMED_COLOR_PALETTES key from an explicit user
        request) always wins. Otherwise, business_name gives a seeded pick
        from the type's pool; no name = classic palette (backward compatible).
        `variant` walks the pick forward for the "shuffle design" re-roll.
        """
        if color_override and color_override in NAMED_COLOR_PALETTES:
            named = NAMED_COLOR_PALETTES[color_override]
            return named.get(color_mode, named["light"])
        options = self._palette_options(business_type)
        if business_name:
            # Divide by 7 so the palette pick doesn't always pair with the
            # same font pick (seed % len would sync when pools match in size).
            palettes = _pick(options, _variant_seed(business_name), 7, variant)
        elif variant:
            palettes = options[int(variant) % len(options)]
        else:
            palettes = options[0]
        return palettes.get(color_mode, palettes["light"])

    def get_layout_template(self, business_type: str) -> str:
        """Get layout template for a business type"""
        return LAYOUT_TEMPLATES.get(business_type, LAYOUT_TEMPLATES["general"])

    def get_hero_variant(
        self,
        business_type: str,
        has_images: bool = True,
        business_name: str = "",
        variant: int = 0,
    ) -> str:
        """Get hero section variant for a business type.

        With a business_name, a deterministic seeded pick from this type's
        hero pool; without one, the classic hero (backward compatible).
        `variant` walks the pick forward for the "shuffle design" re-roll.
        """
        if not has_images:
            return HERO_VARIANTS_NO_IMAGES.get(business_type, HERO_VARIANTS_NO_IMAGES["default"])
        options = self._hero_options(business_type)
        if business_name:
            return _pick(options, _variant_seed(business_name), 3, variant)
        if variant:
            return options[int(variant) % len(options)]
        return options[0]

    def get_personality(
        self,
        business_type: str,
        business_name: str = "",
        style_hint: str = None,
        variant: int = 0,
    ) -> dict:
        """Pick a design personality for this site.

        An explicit style hint from the user's description forces the matching
        personality; otherwise a seeded pick from the type's pool, walked
        forward by `variant` for the "shuffle design" re-roll.
        """
        if style_hint and style_hint in _STYLE_HINT_TO_PERSONALITY:
            key = _STYLE_HINT_TO_PERSONALITY[style_hint]
        else:
            pool = PERSONALITY_POOL.get(business_type, PERSONALITY_POOL["general"])
            if business_name:
                key = _pick(pool, _variant_seed(business_name), 11, variant)
            elif variant:
                key = pool[int(variant) % len(pool)]
            else:
                key = pool[0]
        return {"key": key, **DESIGN_PERSONALITIES[key]}

    def build(
        self,
        business_type: str,
        color_mode: str = "light",
        business_name: str = "",
        description: str = "",
        has_images: bool = True,
        brand_colors: dict = None,
        variant: int = 0,
        palette_override: str = None,
        style_override: str = None,
    ) -> dict:
        """One-call design bundle with internally CONSISTENT picks.

        Extracts explicit user preferences from the description (colour theme,
        style adjectives), applies them as overrides, and returns fonts,
        palette, hero, layout, personality, and a matching Tailwind config.

        brand_colors: optional dict of explicit hex overrides from the request
        ({"primary": "#RRGGBB", "secondary": ..., "accent": ...}) — the
        strongest override of all (the merchant's actual brand).

        variant: "shuffle design" offset. 0 keeps the business's natural
        (pre-shuffle) look; each increment re-rolls fonts, palette, hero and
        personality one step forward, reproducibly.

        palette_override / style_override: explicit picks from the design
        picker UI. They beat the description sniffing (a merchant who taps
        "Navy" in the UI means it more than one who typed the word).
        """
        prefs = extract_design_preferences(description)
        if palette_override and palette_override in NAMED_COLOR_PALETTES:
            prefs = {**prefs, "color": palette_override}
        if style_override and style_override in _STYLE_HINT_TO_PERSONALITY:
            prefs = {**prefs, "style_hint": style_override}

        fonts = self.get_font_pairing(
            business_type, business_name=business_name, variant=variant
        )
        palette = self.get_color_palette(
            business_type,
            color_mode,
            business_name=business_name,
            color_override=prefs["color"],
            variant=variant,
        )

        # Merchant brand colours (validated hex only) beat every other pick.
        brand_applied = False
        if brand_colors:
            clean = {
                k: str(v).strip().upper()
                for k, v in brand_colors.items()
                if k in ("primary", "secondary", "accent")
                and isinstance(v, str)
                and re.fullmatch(r"#[0-9A-Fa-f]{6}", str(v).strip())
            }
            if clean:
                palette = {**palette, **clean}
                brand_applied = True
                logger.info(f"🎨 Merchant brand colours applied: {sorted(clean)}")
        hero = self.get_hero_variant(
            business_type,
            has_images=has_images,
            business_name=business_name,
            variant=variant,
        )
        layout = self.get_layout_template(business_type)
        personality = self.get_personality(
            business_type,
            business_name=business_name,
            style_hint=prefs["style_hint"],
            variant=variant,
        )

        tailwind_config = f"""<script>
tailwind.config = {{
  theme: {{
    extend: {{
      colors: {{
        'primary': '{palette["primary"]}',
        'secondary': '{palette["secondary"]}',
        'accent': '{palette["accent"]}',
        'surface': '{palette["surface"]}',
      }},
      fontFamily: {{
        'sans': ['{fonts["body"]}', '{fonts["body_fallback"]}'],
        'heading': ['{fonts["heading"]}', '{fonts["heading_fallback"]}'],
        'body': ['{fonts["body"]}', '{fonts["body_fallback"]}'],
      }}
    }}
  }}
}}
</script>"""

        user_request_lines = []
        if brand_applied:
            user_request_lines.append(
                "- The merchant supplied their own BRAND COLOURS — the palette above already "
                "contains them. Keep every colour decision consistent with the brand; this "
                "OVERRIDES any conflicting colour guidance elsewhere in this prompt."
            )
        if prefs["color"] and not brand_applied:
            user_request_lines.append(
                f"- The user explicitly asked for a {prefs['color'].upper()} colour theme. "
                f"The palette above already reflects it — keep EVERY colour decision consistent "
                f"with this theme, and it OVERRIDES any conflicting colour guidance elsewhere "
                f"in this prompt."
            )
        if prefs["style_hint"]:
            user_request_lines.append(
                f"- The user asked for a {prefs['style_hint'].upper()} look — the design "
                f"personality below was chosen to honour that. Commit to it fully."
            )
        user_request_block = (
            "USER DESIGN REQUEST (HIGHEST PRIORITY):\n" + "\n".join(user_request_lines)
            if user_request_lines else ""
        )

        return {
            "preferences": prefs,
            "fonts": fonts,
            "palette": palette,
            "hero_variant": hero,
            "layout": layout,
            "personality": personality,
            "tailwind_config": tailwind_config,
            "user_request_block": user_request_block,
            # Echoed back so the caller can persist "which re-roll is this"
            # and show the merchant a stable "Design #3" label.
            "variant": int(variant or 0),
        }

    def get_animation_config(self) -> str:
        """Get AOS animation CDN and init config"""
        return """SCROLL ANIMATIONS (MUST include AOS library):
Add these in <head>:
<link href="https://unpkg.com/aos@2.3.4/dist/aos.css" rel="stylesheet">

Add before </body>:
<script src="https://unpkg.com/aos@2.3.4/dist/aos.js"></script>
<script>AOS.init({ duration: 800, once: true, offset: 100 });</script>

ANIMATION RULES (add data-aos attributes):
- Hero section: data-aos="fade-in" or no animation
- About/story sections: data-aos="fade-up"
- Gallery/menu cards: data-aos="fade-up" with staggered data-aos-delay="100", "200", "300"
- Contact section: data-aos="fade-up"
- Stats/numbers: data-aos="zoom-in"
- Left-side content: data-aos="fade-right"
- Right-side content: data-aos="fade-left"
- DO NOT add data-aos to the <header> navigation bar"""

    def get_tailwind_config(self, business_type: str, color_mode: str = "light") -> str:
        """Get complete Tailwind config script with fonts and colors"""
        fonts = self.get_font_pairing(business_type)
        colors = self.get_color_palette(business_type, color_mode)

        return f"""<script>
tailwind.config = {{
  theme: {{
    extend: {{
      colors: {{
        'primary': '{colors["primary"]}',
        'secondary': '{colors["secondary"]}',
        'accent': '{colors["accent"]}',
        'surface': '{colors["surface"]}',
      }},
      fontFamily: {{
        'sans': ['{fonts["body"]}', '{fonts["body_fallback"]}'],
        'heading': ['{fonts["heading"]}', '{fonts["heading_fallback"]}'],
        'body': ['{fonts["body"]}', '{fonts["body_fallback"]}'],
      }}
    }}
  }}
}}
</script>"""

    def get_typography_rules(self) -> str:
        """Get typography hierarchy rules"""
        return """TYPOGRAPHY RULES (MUST FOLLOW):
- Hero heading: text-4xl md:text-5xl lg:text-7xl font-heading font-bold leading-tight tracking-tight
- Section headings: text-3xl md:text-4xl lg:text-5xl font-heading font-bold
- Subheadings: text-xl md:text-2xl font-body font-medium
- Body text: text-base md:text-lg font-body leading-relaxed
- Small/caption: text-sm font-body
- Button text: text-sm md:text-base font-body font-semibold tracking-wide
- Navigation links: text-sm font-body font-medium

SPACING RULES (MUST FOLLOW):
- Between sections: py-20 md:py-28 lg:py-32
- Section inner padding: px-6 md:px-8 lg:px-16
- Between heading and content: mb-10 md:mb-14
- Card padding: p-6 md:p-8
- Max content width: max-w-7xl mx-auto"""

    def get_design_patterns(self, color_mode: str = "light") -> str:
        """Get advanced CSS design patterns"""
        if color_mode == "dark":
            return """DESIGN PATTERNS TO USE (DARK MODE):
- Card style: bg-surface/80 backdrop-blur-xl border border-white/10 shadow-xl rounded-2xl
- Hover card lift: hover:-translate-y-2 hover:shadow-2xl transition-all duration-500
- Image containers: overflow-hidden rounded-2xl border border-white/10
- Image hover zoom: img hover:scale-110 transition-transform duration-700
- Badge/tag: inline-flex px-3 py-1 rounded-full bg-primary/20 text-primary text-sm font-medium
- Decorative blobs: absolute -z-10 bg-primary/10 rounded-full blur-3xl (behind sections)
- Divider: border-t border-white/10
- Smooth scroll: add to <html>: scroll-behavior: smooth
- Background: Use var(--bg-color) as the main page background
- Surface cards: Use var(--surface-color) for card backgrounds"""
        else:
            return """DESIGN PATTERNS TO USE (LIGHT MODE):
- Card style: bg-white shadow-xl hover:shadow-2xl rounded-2xl border border-gray-100
- Hover card lift: hover:-translate-y-2 hover:shadow-2xl transition-all duration-500
- Image containers: overflow-hidden rounded-2xl
- Image hover zoom: img hover:scale-110 transition-transform duration-700
- Badge/tag: inline-flex px-3 py-1 rounded-full bg-primary/10 text-primary text-sm font-medium
- Decorative blobs: absolute -z-10 bg-primary/5 rounded-full blur-3xl (behind sections)
- Subtle background texture: bg-[radial-gradient(#e5e7eb_1px,transparent_1px)] bg-[size:20px_20px] (optional, for one section)
- Divider: border-t border-gray-200/50
- Smooth scroll: add to <html>: scroll-behavior: smooth
- Background: Use var(--bg-color) as the main page background
- Surface cards: Use var(--surface-color) for card backgrounds"""

    def get_dark_mode_rules(self) -> str:
        """Get dark mode specific design rules"""
        return """DARK MODE DESIGN RULES:
- Page background: Use the background color from the palette (NOT pure black #000)
- Card/surface background: Use the surface color with /80 opacity + backdrop-blur
- Text: Use the text color for headings, text_muted for body text
- Accent areas: Use accent color for highlight backgrounds
- Borders: Use border color from palette or border-white/10
- Shadows: shadow-2xl shadow-black/20
- Images: Add rounded-2xl and subtle border border-white/10
- Navigation bar: Use surface color with backdrop-blur-xl, NOT pure white
- Buttons: Primary color buttons stay bright, outline buttons use border-white/30"""

    def get_quality_checklist(self) -> str:
        """Get quality checklist"""
        return """
## QUALITY CHECKLIST
Before completing generation, verify:
- All sections present and complete
- Mobile responsive (test at 375px, 768px, 1024px)
- No broken HTML tags
- CSS properly scoped and organized
- JavaScript functions working
- WhatsApp integration functional (if requested)
- Smooth scrolling between sections
- Professional visual hierarchy
- Consistent color palette throughout
- Google Fonts loading correctly
- AOS animations applied to sections
"""

    def get_business_template_prompt(self, business_type: str) -> str:
        """Get business-specific template guidelines"""
        templates = {
            "restaurant": "Restaurant/food business with menu, gallery, and ordering focus",
            "cafe": "Cafe with emphasis on ambiance, drinks menu, and cozy atmosphere",
            "salon": "Beauty salon with services, pricing, booking, and portfolio focus",
            "clothing": "Fashion/clothing with product showcase, categories, and shopping focus",
            "bakery": "Bakery with product display, custom orders, and warm branding",
            "services": "Professional services with process steps, FAQ, and trust elements",
            "gym": "Fitness/gym with programs, trainers, membership, and energetic design",
            "clinic": "Healthcare clinic with services, credentials, and trust-building design",
            "general": "General business with products/services showcase",
        }
        return templates.get(business_type, templates["general"])


# Create singleton instance
design_system = DesignSystem()


# ============================================================================
# PUBLIC DESIGN CATALOGUE
#
# The picker UI (and the credit-free theme repaint endpoint) needs to know
# what looks exist. Everything below is a read-only projection of the tables
# above — no new source of truth, so a palette added there shows up in the
# picker automatically.
# ============================================================================

#: Display order for the palette picker. Warm/most-requested first — this is
#: what the merchant scrolls through, so it is a curation, not a data change.
PALETTE_DISPLAY_ORDER = [
    "blue", "navy", "teal", "green", "gold", "orange",
    "red", "maroon", "brown", "purple", "pink", "black",
]

#: Malay-first labels: the dashboard is in Bahasa Melayu.
PALETTE_LABELS = {
    "blue": ("Biru", "Blue"),
    "navy": ("Biru Laut", "Navy"),
    "teal": ("Hijau Toska", "Teal"),
    "green": ("Hijau", "Green"),
    "gold": ("Emas", "Gold"),
    "orange": ("Oren", "Orange"),
    "red": ("Merah", "Red"),
    "maroon": ("Merah Marun", "Maroon"),
    "brown": ("Coklat", "Brown"),
    "purple": ("Ungu", "Purple"),
    "pink": ("Merah Jambu", "Pink"),
    "black": ("Hitam Putih", "Monochrome"),
}

STYLE_LABELS = {
    "elegant": ("Mewah", "Elegant"),
    "minimal": ("Minimalis", "Minimal"),
    "playful": ("Ceria", "Playful"),
    "bold": ("Berani", "Bold"),
    "classic": ("Klasik", "Classic"),
}


def font_pairing_key(pairing: dict) -> str:
    """Stable slug for a font pairing — 'playfair-display__dm-sans'."""
    def slug(name: str) -> str:
        return re.sub(r"[^a-z0-9]+", "-", (name or "").lower()).strip("-")

    return f"{slug(pairing.get('heading'))}__{slug(pairing.get('body'))}"


def list_named_palettes(color_mode: str = "light") -> list:
    """Every named palette, ready for a swatch grid.

    Returns [{key, label_ms, label_en, colors: {...}}] in display order.
    Unknown color_mode falls back to 'light'.
    """
    mode = color_mode if color_mode in ("light", "dark") else "light"
    ordered = [k for k in PALETTE_DISPLAY_ORDER if k in NAMED_COLOR_PALETTES]
    ordered += [k for k in NAMED_COLOR_PALETTES if k not in ordered]
    out = []
    for key in ordered:
        entry = NAMED_COLOR_PALETTES[key]
        label_ms, label_en = PALETTE_LABELS.get(key, (key.title(), key.title()))
        out.append({
            "key": key,
            "label_ms": label_ms,
            "label_en": label_en,
            "colors": dict(entry.get(mode, entry["light"])),
        })
    return out


def get_named_palette(key: str, color_mode: str = "light") -> dict:
    """One named palette by key, or {} when the key is unknown."""
    entry = NAMED_COLOR_PALETTES.get(key)
    if not entry:
        return {}
    mode = color_mode if color_mode in ("light", "dark") else "light"
    return dict(entry.get(mode, entry["light"]))


def next_palette_key(current: str = None, step: int = 1) -> str:
    """The next palette in display order — the "shuffle colour" button.

    Deterministic on purpose: the merchant taps shuffle, sees the next
    swatch, and can tap back to where they were.
    """
    ordered = [k for k in PALETTE_DISPLAY_ORDER if k in NAMED_COLOR_PALETTES]
    if not ordered:
        return ""
    if current not in ordered:
        return ordered[int(step or 1) % len(ordered)]
    return ordered[(ordered.index(current) + int(step or 1)) % len(ordered)]


def match_palette_key(primary_hex: str) -> str:
    """Which named palette owns this primary colour? '' when none does.

    Used to seed the shuffle from a live page: read the site's current
    primary, find the palette it came from, advance one step.
    """
    if not primary_hex:
        return ""
    target = str(primary_hex).strip().upper()
    for key, entry in NAMED_COLOR_PALETTES.items():
        for mode in ("light", "dark"):
            if str(entry.get(mode, {}).get("primary", "")).upper() == target:
                return key
    return ""


def list_font_pairings(business_type: str = None) -> list:
    """Every font pairing available, de-duplicated across business types.

    Without a business_type, the whole catalogue (so a cafe can borrow the
    gym's condensed display face if that is the look the owner wants).
    """
    if business_type:
        types = [business_type]
    else:
        types = sorted(set(list(FONT_PAIRINGS.keys()) + list(ALT_FONT_PAIRINGS.keys())))

    seen = set()
    out = []
    for btype in types:
        options = design_system._font_options(btype)
        for pairing in options:
            key = font_pairing_key(pairing)
            if key in seen:
                continue
            seen.add(key)
            out.append({
                "key": key,
                "heading": pairing["heading"],
                "body": pairing["body"],
                "heading_weights": pairing.get("heading_weights", "400;600;700"),
                "body_weights": pairing.get("body_weights", "400;500;600;700"),
                "heading_fallback": pairing.get("heading_fallback", "Georgia, serif"),
                "body_fallback": pairing.get("body_fallback", "system-ui, sans-serif"),
                "vibe": pairing.get("vibe", ""),
                "business_type": btype,
            })
    return out


def get_font_pairing_by_key(key: str) -> dict:
    """One font pairing by its slug, or {} when the slug is unknown."""
    if not key:
        return {}
    for pairing in list_font_pairings():
        if pairing["key"] == key:
            return pairing
    return {}


def list_styles() -> list:
    """The style personalities a merchant can force from the picker."""
    out = []
    for key in _STYLE_HINT_TO_PERSONALITY:
        label_ms, label_en = STYLE_LABELS.get(key, (key.title(), key.title()))
        personality = DESIGN_PERSONALITIES.get(_STYLE_HINT_TO_PERSONALITY[key], {})
        out.append({
            "key": key,
            "label_ms": label_ms,
            "label_en": label_en,
            "personality": _STYLE_HINT_TO_PERSONALITY[key],
            "description": personality.get("name", ""),
        })
    return out
