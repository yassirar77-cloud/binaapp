"""
Template Gallery Service
Provides design template definitions for the Template Gallery feature.
Each template contains design tokens (colors, fonts, layout instructions)
that are injected into the DeepSeek prompt when generating a website.

Templates are NOT HTML files - they are design instructions that guide
the AI to produce websites with specific visual styles.
"""

from typing import Optional, List, Dict


TEMPLATES: Dict[str, dict] = {
    "elegance_dark": {
        "id": "elegance_dark",
        "name": "Elegance",
        "name_ms": "Elegansi",
        "description": "Dark luxury with gold accents. Perfect for fine dining, premium services.",
        "description_ms": "Gelap mewah dengan aksen emas. Sesuai untuk restoran mewah, perkhidmatan premium.",
        "preview_image": "/templates/elegance_dark.svg",
        "category": "premium",
        "best_for": ["restaurant", "salon", "services"],
        "color_mode": "dark",
        "fonts": {
            "heading": "Playfair Display",
            "heading_weight": "700",
            "body": "DM Sans",
            "body_weight": "400",
            "cdn": "https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;700&family=DM+Sans:wght@400;500;700&display=swap",
        },
        "colors": {
            "primary": "#D4AF37",
            "secondary": "#8B7355",
            "accent": "#2A1F0E",
            "background": "#0A0A0A",
            "surface": "#1A1A1A",
            "text": "#F5F5F0",
            "text_muted": "#A0998C",
        },
        "layout": "editorial",
        "hero_style": "fullscreen_overlay",
        "card_style": "glassmorphism_dark",
        "animation_style": "fade_elegant",
        "design_instructions": """
DESIGN STYLE -- ELEGANCE DARK:
- Background: #0A0A0A (rich black, NOT pure #000)
- Cards: bg-[#1A1A1A]/80 backdrop-blur-xl border border-white/10 rounded-2xl
- Gold accents on headings, buttons, dividers: text-[#D4AF37]
- Buttons: bg-[#D4AF37] text-black font-semibold hover:bg-[#B8960C] rounded-full px-8 py-3
- Hero: Full-screen image with gradient overlay from-black/80 via-black/40 to-transparent
- Section dividers: thin gold line (border-t border-[#D4AF37]/20)
- Generous spacing: py-24 md:py-36 between sections
- Typography: Playfair Display for headings (elegant serif), DM Sans for body
- Images: rounded-2xl border border-white/10 shadow-2xl
- Hover effects: hover:border-[#D4AF37]/30 transition-all duration-500
- Subtle gold glow on hover: hover:shadow-[#D4AF37]/10
""",
    },
    "fresh_clean": {
        "id": "fresh_clean",
        "name": "Fresh & Clean",
        "name_ms": "Segar & Bersih",
        "description": "Bright, airy, and modern. Great for cafes, bakeries, health businesses.",
        "description_ms": "Cerah, lapang dan moden. Sesuai untuk kafe, bakeri, perniagaan kesihatan.",
        "preview_image": "/templates/fresh_clean.svg",
        "category": "modern",
        "best_for": ["cafe", "bakery", "clinic", "general"],
        "color_mode": "light",
        "fonts": {
            "heading": "Plus Jakarta Sans",
            "heading_weight": "700",
            "body": "Inter",
            "body_weight": "400",
            "cdn": "https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700&family=Inter:wght@400;500;600&display=swap",
        },
        "colors": {
            "primary": "#16A34A",
            "secondary": "#166534",
            "accent": "#DCFCE7",
            "background": "#FAFFFE",
            "surface": "#FFFFFF",
            "text": "#1A2E1A",
            "text_muted": "#6B8068",
        },
        "layout": "clean_sections",
        "hero_style": "split_image_right",
        "card_style": "soft_shadow",
        "animation_style": "fade_gentle",
        "design_instructions": """
DESIGN STYLE -- FRESH & CLEAN:
- Background: #FAFFFE (very subtle green-white tint)
- Cards: bg-white rounded-2xl shadow-lg shadow-black/5 border border-gray-100 p-8
- Green accents: text-[#16A34A] for highlights, badges, CTAs
- Buttons: bg-[#16A34A] text-white font-semibold hover:bg-[#15803D] rounded-xl px-6 py-3
- Hero: Split layout -- text left, image right with rounded-3xl shadow-2xl
- Lots of whitespace: py-20 md:py-32 between sections
- Typography: Plus Jakarta Sans (modern, friendly), Inter for body
- Cards with subtle hover lift: hover:-translate-y-1 hover:shadow-xl transition-all duration-300
- Soft background elements: bg-[#16A34A]/5 rounded-full blur-3xl behind sections
- Clean dividers: no visible lines, just generous spacing
- Badge style: bg-[#DCFCE7] text-[#16A34A] px-4 py-1.5 rounded-full text-sm font-medium
""",
    },
    "warm_cozy": {
        "id": "warm_cozy",
        "name": "Warm & Cozy",
        "name_ms": "Hangat & Selesa",
        "description": "Earthy tones, warm feeling. Ideal for restaurants, bakeries, home businesses.",
        "description_ms": "Warna bumi, rasa hangat. Sesuai untuk restoran, bakeri, perniagaan rumah.",
        "preview_image": "/templates/warm_cozy.svg",
        "category": "warm",
        "best_for": ["restaurant", "bakery", "food", "cafe"],
        "color_mode": "light",
        "fonts": {
            "heading": "Lora",
            "heading_weight": "700",
            "body": "Nunito",
            "body_weight": "400",
            "cdn": "https://fonts.googleapis.com/css2?family=Lora:wght@400;600;700&family=Nunito:wght@400;500;600&display=swap",
        },
        "colors": {
            "primary": "#EA580C",
            "secondary": "#92400E",
            "accent": "#FED7AA",
            "background": "#FFFBF5",
            "surface": "#FFFFFF",
            "text": "#1C1917",
            "text_muted": "#78716C",
        },
        "layout": "editorial",
        "hero_style": "fullscreen_overlay",
        "card_style": "warm_rounded",
        "animation_style": "fade_warm",
        "design_instructions": """
DESIGN STYLE -- WARM & COZY:
- Background: #FFFBF5 (warm cream, NOT cold white)
- Cards: bg-white rounded-3xl shadow-md shadow-orange-900/5 border border-orange-100/50 p-8
- Warm orange accents: text-[#EA580C] for highlights
- Buttons: bg-[#EA580C] text-white font-semibold hover:bg-[#C2410C] rounded-2xl px-7 py-3.5
- Hero: Full-screen food image with warm gradient overlay from-[#1C1917]/70 via-[#1C1917]/30 to-transparent
- Typography: Lora (warm serif) for headings, Nunito (friendly rounded) for body
- Rounded everything: rounded-2xl, rounded-3xl
- Warm shadows: shadow-orange-900/10
- Background accents: bg-[#FED7AA]/30 rounded-full blur-3xl behind sections
- Decorative elements: subtle dotted patterns, warm-toned
- Section spacing: py-20 md:py-28
- Food images with warm border: rounded-2xl border-2 border-[#FED7AA]/30
""",
    },
    "bold_vibrant": {
        "id": "bold_vibrant",
        "name": "Bold & Vibrant",
        "name_ms": "Berani & Bertenaga",
        "description": "High energy, bright colors, big text. Perfect for gyms, street food, youth brands.",
        "description_ms": "Bertenaga tinggi, warna cerah, teks besar. Sesuai untuk gym, makanan jalanan, jenama muda.",
        "preview_image": "/templates/bold_vibrant.svg",
        "category": "bold",
        "best_for": ["gym", "food", "clothing", "general"],
        "color_mode": "light",
        "fonts": {
            "heading": "Bebas Neue",
            "heading_weight": "400",
            "body": "Roboto",
            "body_weight": "400",
            "cdn": "https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Roboto:wght@400;500;700&display=swap",
        },
        "colors": {
            "primary": "#EF4444",
            "secondary": "#F59E0B",
            "accent": "#FEF3C7",
            "background": "#FFFFFF",
            "surface": "#FFF7ED",
            "text": "#18181B",
            "text_muted": "#71717A",
        },
        "layout": "storefront",
        "hero_style": "bold_split",
        "card_style": "chunky",
        "animation_style": "fade_energetic",
        "design_instructions": """
DESIGN STYLE -- BOLD & VIBRANT:
- Background: #FFFFFF with colored section blocks
- Cards: bg-[#FFF7ED] rounded-2xl border-2 border-[#EF4444]/20 p-6
- Bold red + yellow accents: text-[#EF4444], bg-[#F59E0B]
- Buttons: bg-[#EF4444] text-white font-bold uppercase tracking-wider hover:bg-[#DC2626] rounded-xl px-8 py-4 text-lg
- Hero: Split layout with HUGE text (text-7xl md:text-9xl) + image
- Typography: Bebas Neue (bold display) for headings, Roboto for body
- Oversized headings: text-5xl md:text-7xl for section titles
- Thick borders: border-2 or border-3
- Energetic hover: hover:scale-105 hover:rotate-1 transition-all duration-300
- Colored section backgrounds alternating: bg-white then bg-[#FEF3C7] then bg-white
- Sticker/badge style: rotate-3 or -rotate-2 on badges for playful feel
""",
    },
    "minimal_luxe": {
        "id": "minimal_luxe",
        "name": "Minimal Luxe",
        "name_ms": "Minimalis Mewah",
        "description": "Less is more. Subtle elegance with maximum whitespace. For premium brands.",
        "description_ms": "Kurang itu lebih. Keanggunan halus dengan ruang putih maksimum. Untuk jenama premium.",
        "preview_image": "/templates/minimal_luxe.svg",
        "category": "minimal",
        "best_for": ["salon", "clothing", "services", "clinic"],
        "color_mode": "light",
        "fonts": {
            "heading": "Cormorant Garamond",
            "heading_weight": "600",
            "body": "Inter",
            "body_weight": "400",
            "cdn": "https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@400;600;700&family=Inter:wght@400;500&display=swap",
        },
        "colors": {
            "primary": "#18181B",
            "secondary": "#3F3F46",
            "accent": "#F4F4F5",
            "background": "#FFFFFF",
            "surface": "#FAFAFA",
            "text": "#18181B",
            "text_muted": "#A1A1AA",
        },
        "layout": "professional",
        "hero_style": "minimal_centered",
        "card_style": "borderless",
        "animation_style": "fade_subtle",
        "design_instructions": """
DESIGN STYLE -- MINIMAL LUXE:
- Background: #FFFFFF (pure white)
- Cards: bg-[#FAFAFA] rounded-xl p-10 (NO shadows, NO borders -- just subtle background)
- Black accent only: text-[#18181B]
- Buttons: bg-[#18181B] text-white font-medium hover:bg-[#3F3F46] rounded-none px-8 py-3.5 (square edges = luxury)
- Hero: Centered text with massive spacing, image below or subtle background
- Typography: Cormorant Garamond (elegant thin serif), Inter (clean sans)
- MAXIMUM whitespace: py-32 md:py-44 between sections
- Thin hairline dividers: border-t border-gray-200
- No decorative elements -- pure content focus
- Image style: rounded-none (sharp edges), subtle grayscale filter on hover
- Letter spacing on headings: tracking-wide or tracking-widest
- Uppercase subheadings: uppercase text-sm tracking-[0.2em] text-[#A1A1AA]
""",
    },
    "neon_night": {
        "id": "neon_night",
        "name": "Neon Night",
        "name_ms": "Neon Malam",
        "description": "Cyberpunk-inspired dark theme with neon glows. For bars, nightlife, gaming, tech.",
        "description_ms": "Tema gelap inspirasi cyberpunk dengan cahaya neon. Untuk bar, hiburan malam, gaming, teknologi.",
        "preview_image": "/templates/neon_night.svg",
        "category": "dark",
        "best_for": ["food", "general", "services"],
        "color_mode": "dark",
        "fonts": {
            "heading": "Space Grotesk",
            "heading_weight": "700",
            "body": "Inter",
            "body_weight": "400",
            "cdn": "https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;600;700&family=Inter:wght@400;500&display=swap",
        },
        "colors": {
            "primary": "#8B5CF6",
            "secondary": "#06B6D4",
            "accent": "#1E1B4B",
            "background": "#030712",
            "surface": "#111827",
            "text": "#F9FAFB",
            "text_muted": "#9CA3AF",
        },
        "layout": "clean_sections",
        "hero_style": "fullscreen_overlay",
        "card_style": "glassmorphism_neon",
        "animation_style": "fade_cyber",
        "design_instructions": """
DESIGN STYLE -- NEON NIGHT:
- Background: #030712 (near-black blue)
- Cards: bg-[#111827]/80 backdrop-blur-xl border border-[#8B5CF6]/20 rounded-2xl p-8
- Neon purple + cyan accents: text-[#8B5CF6], text-[#06B6D4]
- Buttons: bg-gradient-to-r from-[#8B5CF6] to-[#06B6D4] text-white font-semibold rounded-xl px-7 py-3 hover:shadow-lg hover:shadow-[#8B5CF6]/25
- Hero: Dark overlay with subtle gradient glow effects
- Typography: Space Grotesk (techy), Inter for body
- Neon glow effects: shadow-[#8B5CF6]/20, shadow-[#06B6D4]/20 on hover
- Gradient text on headings: bg-gradient-to-r from-[#8B5CF6] to-[#06B6D4] bg-clip-text text-transparent
- Background glow blobs: absolute bg-[#8B5CF6]/10 rounded-full blur-3xl
- Border glow on hover: hover:border-[#8B5CF6]/40
- Grid pattern background: bg-[linear-gradient(rgba(139,92,246,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(139,92,246,0.03)_1px,transparent_1px)] bg-[size:50px_50px]
""",
    },
    "malay_heritage": {
        "id": "malay_heritage",
        "name": "Warisan Melayu",
        "name_ms": "Warisan Melayu",
        "description": "Malaysian heritage-inspired. Rich cultural colors with modern layout. For traditional businesses.",
        "description_ms": "Inspirasi warisan Malaysia. Warna budaya yang kaya dengan susun atur moden. Untuk perniagaan tradisional.",
        "preview_image": "/templates/malay_heritage.svg",
        "category": "cultural",
        "best_for": ["restaurant", "food", "services", "general"],
        "color_mode": "light",
        "fonts": {
            "heading": "Playfair Display",
            "heading_weight": "700",
            "body": "Poppins",
            "body_weight": "400",
            "cdn": "https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;700&family=Poppins:wght@400;500;600&display=swap",
        },
        "colors": {
            "primary": "#B45309",
            "secondary": "#78350F",
            "accent": "#FDE68A",
            "background": "#FFFDF5",
            "surface": "#FFFFFF",
            "text": "#292524",
            "text_muted": "#78716C",
        },
        "layout": "editorial",
        "hero_style": "fullscreen_overlay",
        "card_style": "heritage_warm",
        "animation_style": "fade_warm",
        "design_instructions": """
DESIGN STYLE -- WARISAN MELAYU (MALAY HERITAGE):
- Background: #FFFDF5 (warm ivory)
- Cards: bg-white rounded-2xl shadow-md border border-[#FDE68A]/30 p-8
- Rich amber/gold accents: text-[#B45309], bg-[#FDE68A]
- Buttons: bg-[#B45309] text-white font-semibold hover:bg-[#92400E] rounded-xl px-7 py-3
- Hero: Full-screen with rich warm overlay from-[#78350F]/70 to-transparent
- Typography: Playfair Display (classic elegance), Poppins (modern readable)
- Decorative accents: subtle Islamic geometric pattern hints using CSS
- Gold divider lines: border-t-2 border-[#FDE68A]/50
- Badge style: bg-[#FDE68A] text-[#78350F] font-semibold px-4 py-1.5 rounded-full
- Warm image treatment: rounded-2xl border-2 border-[#FDE68A]/20
- Section backgrounds alternating: bg-[#FFFDF5] then bg-[#FDE68A]/10
- Cultural touches: use Halal badge prominently, warm welcoming language
""",
    },
    "ocean_breeze": {
        "id": "ocean_breeze",
        "name": "Ocean Breeze",
        "name_ms": "Angin Lautan",
        "description": "Cool blues and teals. Relaxing and trustworthy. For seafood, spa, wellness, tech.",
        "description_ms": "Biru dan teal sejuk. Menenangkan dan dipercayai. Untuk makanan laut, spa, kesejahteraan, teknologi.",
        "preview_image": "/templates/ocean_breeze.svg",
        "category": "cool",
        "best_for": ["restaurant", "clinic", "salon", "services"],
        "color_mode": "light",
        "fonts": {
            "heading": "Source Serif 4",
            "heading_weight": "700",
            "body": "Open Sans",
            "body_weight": "400",
            "cdn": "https://fonts.googleapis.com/css2?family=Source+Serif+4:wght@400;600;700&family=Open+Sans:wght@400;500;600&display=swap",
        },
        "colors": {
            "primary": "#0891B2",
            "secondary": "#164E63",
            "accent": "#CFFAFE",
            "background": "#F8FDFF",
            "surface": "#FFFFFF",
            "text": "#0C1A22",
            "text_muted": "#5E8A9A",
        },
        "layout": "professional",
        "hero_style": "split_image_right",
        "card_style": "soft_shadow",
        "animation_style": "fade_gentle",
        "design_instructions": """
DESIGN STYLE -- OCEAN BREEZE:
- Background: #F8FDFF (very subtle cool blue-white)
- Cards: bg-white rounded-2xl shadow-lg shadow-cyan-900/5 border border-cyan-100/50 p-8
- Cool teal/cyan accents: text-[#0891B2]
- Buttons: bg-[#0891B2] text-white font-semibold hover:bg-[#0E7490] rounded-xl px-7 py-3
- Hero: Split layout with calming image + clean text
- Typography: Source Serif 4 (authoritative serif), Open Sans (clean)
- Cool-toned shadows: shadow-cyan-900/5
- Background blobs: bg-[#0891B2]/5 rounded-full blur-3xl
- Wavy section dividers using SVG or CSS clip-path
- Badge: bg-[#CFFAFE] text-[#0891B2] px-4 py-1.5 rounded-full
- Professional spacing: py-20 md:py-32
""",
    },
}


def get_template(template_id: str) -> Optional[dict]:
    """Get a template by ID. Returns None if not found."""
    return TEMPLATES.get(template_id, None)


def get_all_templates() -> list:
    """Get all templates for the gallery display."""
    return [
        {
            "id": t["id"],
            "name": t["name"],
            "name_ms": t["name_ms"],
            "description": t["description"],
            "description_ms": t["description_ms"],
            "preview_image": t["preview_image"],
            "category": t["category"],
            "best_for": t["best_for"],
            "color_mode": t["color_mode"],
            "colors": t["colors"],
        }
        for t in TEMPLATES.values()
    ]


def get_templates_for_business(business_type: str) -> list:
    """Get recommended templates for a specific business type."""
    recommended = []
    others = []
    for t in TEMPLATES.values():
        summary = {
            "id": t["id"],
            "name": t["name"],
            "name_ms": t["name_ms"],
            "description": t["description"],
            "description_ms": t["description_ms"],
            "preview_image": t["preview_image"],
            "category": t["category"],
            "color_mode": t["color_mode"],
            "colors": t["colors"],
        }
        if business_type in t["best_for"]:
            summary["recommended"] = True
            recommended.append(summary)
        else:
            summary["recommended"] = False
            others.append(summary)
    return recommended + others


ANIMATED_TEMPLATES: Dict[str, dict] = {
    "particle-globe": {
        "id": "particle-globe",
        "style_key": "particle-globe",
        "name": "Particle Globe",
        "name_ms": "Glob Zarah",
        "categories": ["premium", "gelap"],
        "tag": "Premium",
        "is_premium": True,
        "description": "3D rotating particle sphere with blue color scheme",
        "description_ms": "Sfera zarah 3D berputar dengan skema warna biru",
    },
    "gradient-wave": {
        "id": "gradient-wave",
        "style_key": "gradient-wave",
        "name": "Gradient Wave",
        "name_ms": "Gelombang Gradien",
        "categories": ["gelap", "ceria"],
        "tag": "Vibrant",
        "is_premium": False,
        "description": "Purple/blue/pink gradient waves sliding horizontally",
        "description_ms": "Gelombang gradien ungu/biru/merah jambu meluncur mendatar",
    },
    "floating-food": {
        "id": "floating-food",
        "style_key": "floating-food",
        "name": "Floating Food",
        "name_ms": "Makanan Terapung",
        "categories": ["gelap", "ceria"],
        "tag": "Vibrant",
        "is_premium": False,
        "description": "Floating food emoji items in glass-morphism cards",
        "description_ms": "Item emoji makanan terapung dalam kad kaca",
    },
    "neon-grid": {
        "id": "neon-grid",
        "style_key": "neon-grid",
        "name": "Neon Grid",
        "name_ms": "Grid Neon",
        "categories": ["gelap", "premium"],
        "tag": "Dark",
        "is_premium": True,
        "description": "Perspective CSS grid with pulsing neon glow orbs",
        "description_ms": "Grid CSS perspektif dengan bebola cahaya neon berdenyut",
    },
    "morphing-blob": {
        "id": "morphing-blob",
        "style_key": "morphing-blob",
        "name": "Morphing Blob",
        "name_ms": "Blob Berubah",
        "categories": ["gelap", "minimal"],
        "tag": "Minimal",
        "is_premium": False,
        "description": "Organic blob shape continuously morphing with gradient fill",
        "description_ms": "Bentuk organik berubah secara berterusan dengan isian gradien",
    },
    "matrix-code": {
        "id": "matrix-code",
        "style_key": "matrix-code",
        "name": "Matrix Code",
        "name_ms": "Kod Matrix",
        "categories": ["gelap"],
        "tag": "Dark",
        "is_premium": False,
        "description": "Falling code rain with katakana and hex characters",
        "description_ms": "Hujan kod jatuh dengan aksara katakana dan hex",
    },
    "aurora": {
        "id": "aurora",
        "style_key": "aurora",
        "name": "Aurora Borealis",
        "name_ms": "Aurora",
        "categories": ["premium", "gelap", "ceria"],
        "tag": "Premium",
        "is_premium": True,
        "description": "Aurora bands with twinkling stars on deep navy background",
        "description_ms": "Jalur aurora dengan bintang berkelip di latar belakang biru gelap",
    },
    "spotlight": {
        "id": "spotlight",
        "style_key": "spotlight",
        "name": "Spotlight",
        "name_ms": "Sorotan",
        "categories": ["gelap", "minimal"],
        "tag": "Minimal",
        "is_premium": False,
        "description": "Moving orange spotlight with pulsing icon circles",
        "description_ms": "Sorotan oren bergerak dengan bulatan ikon berdenyut",
    },
    "parallax-layers": {
        "id": "parallax-layers",
        "style_key": "parallax-layers",
        "name": "Parallax Layers",
        "name_ms": "Lapisan Paralaks",
        "categories": ["premium", "ceria"],
        "tag": "Premium",
        "is_premium": True,
        "description": "Floating circles with independent parallax animations",
        "description_ms": "Bulatan terapung dengan animasi paralaks bebas",
    },
}


def get_animated_templates() -> list:
    """Get all animated template styles."""
    return list(ANIMATED_TEMPLATES.values())


def get_animated_template(style_key: str) -> Optional[dict]:
    """Get a specific animated template by style key."""
    return ANIMATED_TEMPLATES.get(style_key)


# Mapping from animated template IDs (shown in gallery) to design template IDs.
# The gallery displays animated hero styles (e.g. 'aurora', 'gradient-wave'),
# but the AI prompt injection uses design templates (e.g. 'elegance_dark', 'neon_night').
ANIMATED_TO_DESIGN_MAP: Dict[str, str] = {
    "particle-globe": "neon_night",
    "gradient-wave": "neon_night",
    "floating-food": "warm_cozy",
    "neon-grid": "neon_night",
    "morphing-blob": "elegance_dark",
    "matrix-code": "neon_night",
    "aurora": "elegance_dark",
    "spotlight": "elegance_dark",
    "parallax-layers": "fresh_clean",
}


def get_template_prompt_injection(template_id: str) -> str:
    """
    Get the design instructions to inject into the DeepSeek prompt.
    Returns empty string if no template selected (backward compatible).

    Accepts both design template IDs (e.g. 'elegance_dark') and animated
    template IDs (e.g. 'aurora') by resolving through ANIMATED_TO_DESIGN_MAP.
    """
    # First try direct lookup (design template ID), then resolve via animated template mapping
    design_key = template_id if template_id in TEMPLATES else ANIMATED_TO_DESIGN_MAP.get(template_id)
    template = TEMPLATES.get(design_key) if design_key else None
    if not template:
        return ""

    return f"""
=== TEMPLATE DESIGN SYSTEM (MUST FOLLOW EXACTLY) ===

TEMPLATE: {template['name']}

GOOGLE FONTS (include this EXACT link in <head>):
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="{template['fonts']['cdn']}" rel="stylesheet">

TAILWIND CONFIG (include this EXACT script after Tailwind CDN):
<script>
tailwind.config = {{
  theme: {{
    extend: {{
      colors: {{
        'primary': '{template['colors']['primary']}',
        'secondary': '{template['colors']['secondary']}',
        'accent': '{template['colors']['accent']}',
        'surface': '{template['colors']['surface']}',
        'background': '{template['colors']['background']}',
      }},
      fontFamily: {{
        'heading': ['{template['fonts']['heading']}', 'serif'],
        'body': ['{template['fonts']['body']}', 'sans-serif'],
      }}
    }}
  }}
}}
</script>

USE THESE FONTS:
- All headings: font-heading font-bold
- All body text: font-body
- Page background: bg-[{template['colors']['background']}]
- Main text color: text-[{template['colors']['text']}]
- Muted text: text-[{template['colors']['text_muted']}]

AOS ANIMATIONS (include these in <head> and before </body>):
<link href="https://unpkg.com/aos@2.3.4/dist/aos.css" rel="stylesheet">
<script src="https://unpkg.com/aos@2.3.4/dist/aos.js"></script>
<script>AOS.init({{ duration: 800, once: true, offset: 100 }});</script>

Add data-aos="fade-up" to each section.
Add data-aos-delay="100", "200", "300" to stagger cards.

{template['design_instructions']}

=== END TEMPLATE DESIGN SYSTEM ===
"""
