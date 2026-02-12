"""
Design System Module
Provides comprehensive design guidelines, font pairings, color palettes,
layout templates, hero variants, and animation configs for premium website generation.
"""

import logging

logger = logging.getLogger(__name__)


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
        "body": "Inter",
        "body_weights": "400;500;600",
        "body_fallback": "system-ui, sans-serif",
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
        "body": "Inter",
        "body_weights": "400;500;600",
        "body_fallback": "system-ui, sans-serif",
        "body_category": "sans-serif",
        "vibe": "Professional, trustworthy",
    },
    "gym": {
        "heading": "Bebas Neue",
        "heading_weights": "400",
        "heading_fallback": "Impact, sans-serif",
        "heading_category": "sans-serif",
        "body": "Roboto",
        "body_weights": "400;500;700",
        "body_fallback": "system-ui, sans-serif",
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
        "body": "Inter",
        "body_weights": "400;500;600",
        "body_fallback": "system-ui, sans-serif",
        "body_category": "sans-serif",
        "vibe": "Professional, versatile",
    },
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
            "primary": "#A855F7",
            "secondary": "#581C87",
            "accent": "#F3E8FF",
            "background": "#FDFBFF",
            "surface": "#FFFFFF",
            "text": "#1E1B2E",
            "text_muted": "#6B6880",
            "border": "#E9E5F0",
        },
        "dark": {
            "primary": "#C084FC",
            "secondary": "#E9D5FF",
            "accent": "#3B0764",
            "background": "#0E0B1A",
            "surface": "#1E1B2E",
            "text": "#F5F3FF",
            "text_muted": "#A5A0B8",
            "border": "#2E2A3E",
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


# ============================================================================
# LAYOUT TEMPLATES BY BUSINESS TYPE
# ============================================================================

LAYOUT_TEMPLATES = {
    "food": """LAYOUT STRUCTURE (Editorial style - MUST FOLLOW):
1. HERO: Full-screen image with gradient overlay, business name centered at bottom, badge "Est. 2024 · Halal" above name, two CTA buttons
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
  <img src="HERO_IMAGE_URL" class="absolute inset-0 w-full h-full object-cover" alt="Hero">
  <div class="absolute inset-0 bg-gradient-to-t from-black/70 via-black/30 to-transparent"></div>
  <div class="relative z-10 flex items-end h-full pb-16 md:pb-20 px-6 md:px-16">
    <div class="max-w-2xl">
      <span class="inline-flex px-4 py-1.5 rounded-full bg-primary/20 backdrop-blur-sm text-white text-sm font-medium mb-4">Est. 2024 · Halal Certified</span>
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
  <img src="HERO_IMAGE_URL" class="absolute inset-0 w-full h-full object-cover" alt="Hero">
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
      <span class="inline-flex px-4 py-1.5 rounded-full bg-primary/10 text-primary text-sm font-body font-medium mb-6">Premium Beauty Experience</span>
      <h1 class="text-4xl md:text-5xl lg:text-7xl font-heading leading-tight tracking-tight" style="color: var(--text-color)">BUSINESS_NAME</h1>
      <p class="text-lg mt-4 font-body" style="color: var(--text-muted-color)">TAGLINE</p>
      <a href="#services" class="inline-flex items-center mt-8 px-8 py-3.5 bg-primary text-white rounded-full font-body font-semibold tracking-wide hover:-translate-y-1 hover:shadow-2xl transition-all duration-300">VIEW_SERVICES_CTA</a>
    </div>
  </div>
  <div class="relative order-1 md:order-2 min-h-[400px]" data-aos="fade-left">
    <img src="HERO_IMAGE_URL" class="absolute inset-0 w-full h-full object-cover" alt="Hero">
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
      <img src="HERO_IMAGE_URL" class="rounded-3xl shadow-2xl w-full" alt="Hero">
      <div class="absolute -bottom-6 -left-6 w-32 h-32 bg-primary/20 rounded-full blur-2xl"></div>
    </div>
  </div>
</section>""",

    "bakery": """HERO SECTION DESIGN (Warm full-bleed):
<section id="home" class="relative h-[70vh] min-h-[400px]" data-aos="fade-in">
  <img src="HERO_IMAGE_URL" class="absolute inset-0 w-full h-full object-cover" alt="Hero">
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
      <span class="inline-flex px-4 py-1.5 rounded-full bg-primary/10 text-primary text-sm font-body font-medium mb-6">Trusted & Professional</span>
      <h1 class="text-4xl md:text-5xl lg:text-6xl font-heading font-bold leading-tight tracking-tight" style="color: var(--text-color)">BUSINESS_NAME</h1>
      <p class="text-lg md:text-xl mt-4 font-body" style="color: var(--text-muted-color)">TAGLINE</p>
      <div class="flex flex-wrap gap-4 mt-8">
        <a href="#services" class="inline-flex items-center px-8 py-3.5 bg-primary text-white rounded-full font-body font-semibold tracking-wide hover:-translate-y-1 hover:shadow-2xl transition-all duration-300">VIEW_SERVICES_CTA</a>
        <a href="WHATSAPP_LINK" class="inline-flex items-center px-8 py-3.5 border-2 border-primary/30 text-primary rounded-full font-body font-semibold tracking-wide hover:bg-primary/5 transition-all duration-300">WHATSAPP_CTA</a>
      </div>
    </div>
    <div class="relative" data-aos="fade-left">
      <img src="HERO_IMAGE_URL" class="rounded-3xl shadow-2xl w-full" alt="Hero">
    </div>
  </div>
</section>""",

    "gym": """HERO SECTION DESIGN (High-impact bold):
<section id="home" class="relative h-[70vh] min-h-[400px]" data-aos="fade-in">
  <img src="HERO_IMAGE_URL" class="absolute inset-0 w-full h-full object-cover" alt="Hero">
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
      <span class="inline-flex px-4 py-1.5 rounded-full bg-primary/10 text-primary text-sm font-body font-medium mb-6">Healthcare You Can Trust</span>
      <h1 class="text-4xl md:text-5xl lg:text-6xl font-heading font-bold leading-tight tracking-tight" style="color: var(--text-color)">BUSINESS_NAME</h1>
      <p class="text-lg md:text-xl mt-4 font-body" style="color: var(--text-muted-color)">TAGLINE</p>
      <a href="#services" class="inline-flex items-center mt-8 px-8 py-3.5 bg-primary text-white rounded-full font-body font-semibold tracking-wide hover:-translate-y-1 hover:shadow-2xl transition-all duration-300">BOOK_CTA</a>
    </div>
    <div class="relative" data-aos="fade-left">
      <img src="HERO_IMAGE_URL" class="rounded-3xl shadow-2xl w-full" alt="Hero">
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
      <img src="HERO_IMAGE_URL" class="rounded-3xl shadow-2xl w-full" alt="Hero">
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
      <span class="inline-flex px-4 py-1.5 rounded-full bg-white/20 backdrop-blur-sm text-white text-sm font-medium mb-6">Est. 2024</span>
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


class DesignSystem:
    """Complete design system for premium website generation"""

    def get_font_pairing(self, business_type: str) -> dict:
        """Get font pairing for a business type"""
        pairing = FONT_PAIRINGS.get(business_type, FONT_PAIRINGS["general"])
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

    def get_color_palette(self, business_type: str, color_mode: str = "light") -> dict:
        """Get color palette for a business type and color mode"""
        palettes = COLOR_PALETTES.get(business_type, COLOR_PALETTES["general"])
        return palettes.get(color_mode, palettes["light"])

    def get_layout_template(self, business_type: str) -> str:
        """Get layout template for a business type"""
        return LAYOUT_TEMPLATES.get(business_type, LAYOUT_TEMPLATES["general"])

    def get_hero_variant(self, business_type: str, has_images: bool = True) -> str:
        """Get hero section variant for a business type"""
        if not has_images:
            return HERO_VARIANTS_NO_IMAGES.get(business_type, HERO_VARIANTS_NO_IMAGES["default"])
        return HERO_VARIANTS.get(business_type, HERO_VARIANTS["general"])

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
