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
    "aurora": {
        "id": "aurora",
        "name": "Northern Aurora",
        "name_ms": "Aurora Utara",
        "description": "Deep-space aurora theme with flowing light bands and twinkling stars.",
        "description_ms": "Tema aurora angkasa gelap dengan jalur cahaya mengalir dan bintang berkelip.",
        "preview_image": "/templates/neon_night.svg",
        "category": "dark",
        "best_for": ["restaurant", "cafe", "salon", "services", "general"],
        "color_mode": "dark",
        "fonts": {
            "heading": "Space Grotesk",
            "heading_weight": "700",
            "body": "Inter",
            "body_weight": "400",
            "cdn": "https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;600;700&family=Inter:wght@400;500;600&display=swap",
        },
        "colors": {
            "primary": "#34D399",
            "secondary": "#4A9EFF",
            "accent": "#A78BFA",
            "background": "#050520",
            "surface": "#0A0A2E",
            "text": "#F0F0FF",
            "text_muted": "#8888BB",
        },
        "layout": "clean_sections",
        "hero_style": "fullscreen_overlay",
        "card_style": "glassmorphism_neon",
        "animation_style": "aurora_flow",
        "design_instructions": """
DESIGN STYLE -- NORTHERN AURORA:
- CRITICAL: Use aurora color palette ONLY. Do NOT use gold, bronze, brown, or luxury styling.
- Background: #050520 (deep space blue-purple, NOT #0A0A0A)
- Surface/cards: #0A0A2E with subtle borders and blur
- Primary accent: #34D399 (aurora green)
- Secondary accents: #4A9EFF (blue), #A78BFA (purple), #F472B6 (pink)
- Typography feel: modern, cosmic, luminous (Space Grotesk + Inter)
- Buttons: gradient accents using aurora colors, not monochrome and not gold
- Add a dark cosmic atmosphere with soft glows and transparent layers

MANDATORY AURORA VISUAL ELEMENTS:
- Hero section must include flowing aurora light bands and twinkling stars
- Include a star overlay container with small animated dots
- Include 3 aurora bands with blur and opacity layering
- Add these classes and keyframes in a <style> block:

<style>
.aurora-hero {
  position: relative;
  overflow: hidden;
  background: #050520;
}
.star-field {
  position: absolute;
  inset: 0;
  pointer-events: none;
}
.star {
  position: absolute;
  width: 2px;
  height: 2px;
  border-radius: 9999px;
  background: rgba(240, 240, 255, 0.9);
  box-shadow: 0 0 6px rgba(240, 240, 255, 0.7);
  animation: twinkle 3s ease-in-out infinite;
}
.aurora-band {
  position: absolute;
  width: 200%;
  height: 60%;
  filter: blur(50px);
  opacity: 0.5;
  pointer-events: none;
}
.aurora-1 {
  top: 5%;
  left: -50%;
  background: linear-gradient(90deg, transparent, #34D399, #4A9EFF, transparent);
  animation: auroraFlow 8s ease-in-out infinite;
}
.aurora-2 {
  top: 20%;
  left: -45%;
  background: linear-gradient(90deg, transparent, #A78BFA, #F472B6, transparent);
  animation: auroraFlow 12s ease-in-out infinite reverse;
}
.aurora-3 {
  top: 35%;
  left: -55%;
  background: linear-gradient(90deg, transparent, #4A9EFF, #34D399, transparent);
  animation: auroraFlow 10s ease-in-out infinite;
}
@keyframes auroraFlow {
  0%, 100% { transform: translateX(-10%) skewY(-5deg) scaleY(1); }
  33% { transform: translateX(10%) skewY(3deg) scaleY(1.3); }
  66% { transform: translateX(-5%) skewY(-2deg) scaleY(0.8); }
}
@keyframes twinkle {
  0%, 100% { opacity: 0.2; transform: scale(0.8); }
  50% { opacity: 1; transform: scale(1.25); }
}
</style>
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
    "word_explosion": {
        "id": "word_explosion",
        "name": "Word Explosion",
        "name_ms": "Letupan Kata",
        "description": "Every word flies in from multiple angles and forms the website. A spectacular word tornado effect.",
        "description_ms": "Setiap perkataan terbang masuk dari pelbagai arah dan membentuk laman web. Kesan puting beliung kata yang hebat.",
        "preview_image": "/templates/word_explosion.svg",
        "category": "bold",
        "best_for": ["restaurant", "cafe", "food", "general"],
        "color_mode": "light",
        "fonts": {
            "heading": "Playfair Display",
            "heading_weight": "700",
            "body": "DM Sans",
            "body_weight": "400",
            "cdn": "https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;700&family=DM+Sans:wght@400;500;700&display=swap",
        },
        "colors": {
            "primary": "#E85D3A",
            "secondary": "#D4A853",
            "accent": "#FFF0E6",
            "background": "#FFF8F0",
            "surface": "#FFFFFF",
            "text": "#1A1A1A",
            "text_muted": "#7A7A7A",
        },
        "layout": "standard",
        "hero_style": "fullscreen_overlay",
        "card_style": "warm_rounded",
        "animation_style": "word_explosion",
        "design_instructions": """
DESIGN STYLE -- WORD EXPLOSION (LETUPAN KATA):
- Background: #FFF8F0 (warm cream)
- Cards: bg-white rounded-2xl shadow-md shadow-orange-900/5 border border-[#E85D3A]/10 p-8
- Warm orange accent: text-[#E85D3A] for headings and highlights
- Gold accent: text-[#D4A853] for secondary elements
- Buttons: bg-[#E85D3A] text-white font-semibold hover:bg-[#C44A2A] rounded-xl px-7 py-3
- Hero: Full-screen with warm gradient overlay
- Typography: Playfair Display (elegant serif) for headings, DM Sans (modern) for body
- Warm shadows: shadow-orange-900/10
- Section spacing: py-20 md:py-28

ANIMATION STYLE - WORD EXPLOSION:
- Wrap EVERY visible text word in <span class="fly-word">word</span>
- Each word must be a separate span, including punctuation attached to the word
- Apply to ALL sections: header, hero, menu items, descriptions, footer
- Include the .fly-word CSS keyframe animation and the JavaScript randomizer script at the bottom
- Words fly from 14 different random angles with rotation (up to 720deg), blur, and scale effects
- Stagger delay: each word starts 0.04s after the previous with random offset
- This creates a "word tornado" that assembles into the website

Include this CSS:
<style>
.fly-word {
  display: inline-block;
  opacity: 0;
  animation: flyIn var(--duration, 1.2s) var(--delay, 0s) cubic-bezier(0.23, 1, 0.32, 1) forwards;
}
@keyframes flyIn {
  0% { opacity: 0; transform: translate(var(--start-x), var(--start-y)) rotate(var(--start-rot)) scale(var(--start-scale)); filter: blur(8px); }
  60% { opacity: 1; filter: blur(0px); }
  80% { transform: translate(0, 0) rotate(0deg) scale(1.05); }
  100% { opacity: 1; transform: translate(0, 0) rotate(0deg) scale(1); filter: blur(0px); }
}
</style>

Include this JavaScript before </body>:
<script>
(function(){
  var words = document.querySelectorAll('.fly-word');
  var angles = [
    {x:'-120vw',y:'-80vh',rot:'-540deg',scale:0.1},
    {x:'120vw',y:'-60vh',rot:'480deg',scale:0.2},
    {x:'-100vw',y:'80vh',rot:'360deg',scale:0.1},
    {x:'100vw',y:'60vh',rot:'-400deg',scale:0.15},
    {x:'0px',y:'-100vh',rot:'720deg',scale:0.05},
    {x:'0px',y:'100vh',rot:'-600deg',scale:0.1},
    {x:'-130vw',y:'0px',rot:'500deg',scale:0.2},
    {x:'130vw',y:'0px',rot:'-450deg',scale:0.1},
    {x:'-80vw',y:'-120vh',rot:'300deg',scale:0.3},
    {x:'90vw',y:'110vh',rot:'-350deg',scale:0.05},
    {x:'-60vw',y:'130vh',rot:'800deg',scale:0.1},
    {x:'70vw',y:'-130vh',rot:'-700deg',scale:0.15}
  ];
  words.forEach(function(word, index){
    var angle = angles[Math.floor(Math.random()*angles.length)];
    var delay = index*0.04 + Math.random()*0.15;
    var duration = 0.8 + Math.random()*0.7;
    word.style.setProperty('--start-x', angle.x);
    word.style.setProperty('--start-y', angle.y);
    word.style.setProperty('--start-rot', angle.rot);
    word.style.setProperty('--start-scale', angle.scale);
    word.style.setProperty('--delay', delay+'s');
    word.style.setProperty('--duration', duration+'s');
  });
})();
</script>
""",
    },
    "ghost_restaurant": {
        "id": "ghost_restaurant",
        "name": "Ghost Restaurant",
        "name_ms": "Restoran Hantu",
        "description": "Website vanishes & reappears — a unique mystery restaurant with ghost cycle effect.",
        "description_ms": "Laman web hilang & muncul semula — restoran misteri yang unik dengan kesan kitaran hantu.",
        "preview_image": "/templates/ghost_restaurant.svg",
        "category": "dark",
        "best_for": ["restaurant", "food", "cafe", "general"],
        "color_mode": "dark",
        "fonts": {
            "heading": "Cormorant Garamond",
            "heading_weight": "600",
            "body": "Outfit",
            "body_weight": "400",
            "cdn": "https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@400;600;700&family=Outfit:wght@400;500;600&display=swap",
        },
        "colors": {
            "primary": "#00E5A0",
            "secondary": "#00B8D4",
            "accent": "#1A3D2E",
            "background": "#0D0D0D",
            "surface": "#1E1E1E",
            "text": "#EAEAEA",
            "text_muted": "#8A8A8A",
        },
        "layout": "centered",
        "hero_style": "fullscreen_overlay",
        "card_style": "glassmorphism_dark",
        "animation_style": "ghost_invisible",
        "design_instructions": """
DESIGN STYLE -- GHOST RESTAURANT (RESTORAN HANTU):
- Background: #0D0D0D (deep black)
- Cards: bg-[#1E1E1E]/80 backdrop-blur-xl border border-[#00E5A0]/15 rounded-2xl p-8
- Neon green accent: text-[#00E5A0] for highlights, headings, and CTAs
- Cyan secondary: text-[#00B8D4] for secondary elements
- Buttons: bg-[#00E5A0] text-[#0D0D0D] font-semibold hover:bg-[#00CC8E] rounded-xl px-7 py-3
- Hero: Dark mysterious overlay with subtle green glow
- Typography: Cormorant Garamond (elegant mystery serif) for headings, Outfit (clean modern) for body
- Glow effects: shadow-[#00E5A0]/20 on cards and buttons
- Mystery theme: use ghost/mystery naming (e.g. "Dapur Rahsia", "Rendang Misteri")
- Section spacing: py-24 md:py-36
- Gradient text on hero heading: bg-gradient-to-r from-[#00E5A0] to-[#00B8D4] bg-clip-text text-transparent

ANIMATION STYLE - GHOST RESTAURANT:
- Wrap ALL site content inside <div id="ghost-wrapper">
- Add fixed overlay elements OUTSIDE the wrapper: ghost message overlay, timer bar, countdown badge
- The ghost message shows a ghost emoji with "Gone Invisible..." text centered on screen
- Include the Ghost Cycle Engine JS: site vanishes after 3s, stays invisible 4s, reappears for 60s, repeats
- The vanish effect uses blur(20px) + brightness(2) + opacity(0) + scale(0.97)
- The appear effect uses a 2s animation from blur(30px) to clear
- Timer bar at top shows remaining visibility as a glowing gradient bar
- Countdown badge at bottom-right shows seconds remaining
- Theme the restaurant with mystery/ghost naming
- Use dark color scheme: #0D0D0D bg, #00E5A0 accent, #EAEAEA text

Include these elements OUTSIDE the ghost-wrapper:
<div id="ghost-overlay" style="display:none;position:fixed;inset:0;z-index:9999;background:rgba(13,13,13,0.95);flex-direction:column;align-items:center;justify-content:center;">
  <div style="font-size:80px;margin-bottom:20px;animation:ghostFloat 2s ease-in-out infinite;">&#128123;</div>
  <div style="font-size:24px;color:#00E5A0;font-family:'Cormorant Garamond',serif;">Gone Invisible...</div>
  <div style="font-size:14px;color:#8A8A8A;margin-top:10px;">Reappearing soon</div>
</div>
<div id="ghost-timer-bar" style="position:fixed;top:0;left:0;height:3px;width:100%;background:linear-gradient(90deg,#00E5A0,#00B8D4);z-index:10000;box-shadow:0 0 15px rgba(0,229,160,0.5);"></div>
<div id="countdown-display" style="position:fixed;bottom:20px;right:20px;background:rgba(0,0,0,0.8);backdrop-filter:blur(10px);border:1px solid rgba(0,229,160,0.2);border-radius:12px;padding:10px 18px;font-size:13px;color:#00E5A0;z-index:10001;font-family:'Outfit',sans-serif;"></div>

Include this CSS:
<style>
#ghost-wrapper {
  transition: opacity 1.5s cubic-bezier(0.4, 0, 0.2, 1), filter 1.5s cubic-bezier(0.4, 0, 0.2, 1), transform 1.5s cubic-bezier(0.4, 0, 0.2, 1);
}
#ghost-wrapper.vanishing { opacity: 0; filter: blur(20px) brightness(2); transform: scale(0.97); }
#ghost-wrapper.appearing { animation: ghostAppear 2s cubic-bezier(0.23, 1, 0.32, 1) forwards; }
@keyframes ghostAppear {
  0% { opacity: 0; filter: blur(30px) brightness(3); transform: scale(1.05); }
  30% { opacity: 0.3; filter: blur(15px) brightness(2); }
  60% { opacity: 0.7; filter: blur(5px) brightness(1.3); }
  100% { opacity: 1; filter: blur(0px) brightness(1); transform: scale(1); }
}
@keyframes ghostFloat { 0%,100% { transform: translateY(0); } 50% { transform: translateY(-15px); } }
</style>

Include this JavaScript before </body>:
<script>
(function(){
  var wrapper=document.getElementById('ghost-wrapper');
  var overlay=document.getElementById('ghost-overlay');
  var timerBar=document.getElementById('ghost-timer-bar');
  var countdownEl=document.getElementById('countdown-display');
  var VISIBLE_DURATION=60,INVISIBLE_DELAY=3,INVISIBLE_DURATION=4;
  function startGhostCycle(){
    var countdown=INVISIBLE_DELAY;
    countdownEl.textContent='Appearing in '+Math.ceil(countdown)+'s';
    var timer=setInterval(function(){
      countdown-=0.1;
      timerBar.style.width=(countdown/INVISIBLE_DELAY*100)+'%';
      countdownEl.textContent='Vanishing in '+Math.ceil(countdown)+'s';
      if(countdown<=0){clearInterval(timer);vanishSite();}
    },100);
  }
  function vanishSite(){
    wrapper.classList.add('vanishing');
    overlay.style.display='flex';
    setTimeout(function(){appearSite();},INVISIBLE_DURATION*1000);
  }
  function appearSite(){
    wrapper.classList.remove('vanishing');
    wrapper.classList.add('appearing');
    overlay.style.display='none';
    setTimeout(function(){
      wrapper.classList.remove('appearing');
      startVisibleCountdown();
    },2000);
  }
  function startVisibleCountdown(){
    var remaining=VISIBLE_DURATION;
    var timer=setInterval(function(){
      remaining-=0.1;
      timerBar.style.width=(remaining/VISIBLE_DURATION*100)+'%';
      countdownEl.textContent=remaining>10?'Visible for '+Math.ceil(remaining)+'s':'Vanishing in '+Math.ceil(remaining)+'s!';
      if(remaining<=0){clearInterval(timer);vanishSite();}
    },100);
  }
  startGhostCycle();
})();
</script>
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
    "word-explosion": {
        "id": "word-explosion",
        "style_key": "word-explosion",
        "name": "Word Explosion",
        "name_ms": "Letupan Kata",
        "categories": ["ceria", "premium"],
        "tag": "New",
        "is_premium": True,
        "is_new": True,
        "description": "Every word flies in from multiple angles and forms the website",
        "description_ms": "Setiap perkataan terbang masuk dari pelbagai arah dan membentuk laman web",
    },
    "ghost-restaurant": {
        "id": "ghost-restaurant",
        "style_key": "ghost-restaurant",
        "name": "Ghost Restaurant",
        "name_ms": "Restoran Hantu",
        "categories": ["gelap", "premium"],
        "tag": "New",
        "is_premium": True,
        "is_new": True,
        "description": "Website vanishes & reappears — a unique mystery restaurant",
        "description_ms": "Laman web hilang & muncul semula — restoran misteri yang unik",
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
    "aurora": "aurora",
    "spotlight": "elegance_dark",
    "parallax-layers": "fresh_clean",
    "word-explosion": "word_explosion",
    "ghost-restaurant": "ghost_restaurant",
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
