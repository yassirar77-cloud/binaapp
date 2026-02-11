/**
 * Template Gallery Data (frontend)
 *
 * Contains the design instructions for each template.
 * Used by the /api/generate route to inject template tokens into the AI prompt.
 */

interface TemplateDesign {
  name: string
  fonts: {
    heading: string
    body: string
    cdn: string
  }
  colors: {
    primary: string
    secondary: string
    accent: string
    background: string
    surface: string
    text: string
    text_muted: string
  }
  design_instructions: string
}

const TEMPLATE_DESIGNS: Record<string, TemplateDesign> = {
  elegance_dark: {
    name: 'Elegance',
    fonts: {
      heading: 'Playfair Display',
      body: 'DM Sans',
      cdn: 'https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;700&family=DM+Sans:wght@400;500;700&display=swap',
    },
    colors: {
      primary: '#D4AF37', secondary: '#8B7355', accent: '#2A1F0E',
      background: '#0A0A0A', surface: '#1A1A1A', text: '#F5F5F0', text_muted: '#A0998C',
    },
    design_instructions: `DESIGN STYLE -- ELEGANCE DARK:
- Background: #0A0A0A (rich black)
- Cards: bg-[#1A1A1A]/80 backdrop-blur-xl border border-white/10 rounded-2xl
- Gold accents: text-[#D4AF37]
- Buttons: bg-[#D4AF37] text-black font-semibold rounded-full px-8 py-3
- Hero: Full-screen image with gradient overlay from-black/80
- Typography: Playfair Display headings, DM Sans body`,
  },
  fresh_clean: {
    name: 'Fresh & Clean',
    fonts: {
      heading: 'Plus Jakarta Sans',
      body: 'Inter',
      cdn: 'https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700&family=Inter:wght@400;500;600&display=swap',
    },
    colors: {
      primary: '#16A34A', secondary: '#166534', accent: '#DCFCE7',
      background: '#FAFFFE', surface: '#FFFFFF', text: '#1A2E1A', text_muted: '#6B8068',
    },
    design_instructions: `DESIGN STYLE -- FRESH & CLEAN:
- Background: #FAFFFE
- Cards: bg-white rounded-2xl shadow-lg shadow-black/5 border border-gray-100
- Green accents: text-[#16A34A]
- Buttons: bg-[#16A34A] text-white rounded-xl px-6 py-3
- Typography: Plus Jakarta Sans headings, Inter body`,
  },
  warm_cozy: {
    name: 'Warm & Cozy',
    fonts: {
      heading: 'Lora',
      body: 'Nunito',
      cdn: 'https://fonts.googleapis.com/css2?family=Lora:wght@400;600;700&family=Nunito:wght@400;500;600&display=swap',
    },
    colors: {
      primary: '#EA580C', secondary: '#92400E', accent: '#FED7AA',
      background: '#FFFBF5', surface: '#FFFFFF', text: '#1C1917', text_muted: '#78716C',
    },
    design_instructions: `DESIGN STYLE -- WARM & COZY:
- Background: #FFFBF5 (warm cream)
- Cards: bg-white rounded-3xl shadow-md
- Orange accents: text-[#EA580C]
- Buttons: bg-[#EA580C] text-white rounded-2xl px-7 py-3.5
- Typography: Lora headings, Nunito body`,
  },
  bold_vibrant: {
    name: 'Bold & Vibrant',
    fonts: {
      heading: 'Bebas Neue',
      body: 'Roboto',
      cdn: 'https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Roboto:wght@400;500;700&display=swap',
    },
    colors: {
      primary: '#EF4444', secondary: '#F59E0B', accent: '#FEF3C7',
      background: '#FFFFFF', surface: '#FFF7ED', text: '#18181B', text_muted: '#71717A',
    },
    design_instructions: `DESIGN STYLE -- BOLD & VIBRANT:
- Background: #FFFFFF with colored section blocks
- Bold red + yellow: text-[#EF4444], bg-[#F59E0B]
- Buttons: bg-[#EF4444] text-white font-bold uppercase rounded-xl px-8 py-4
- HUGE text: text-7xl md:text-9xl for hero
- Typography: Bebas Neue headings, Roboto body`,
  },
  minimal_luxe: {
    name: 'Minimal Luxe',
    fonts: {
      heading: 'Cormorant Garamond',
      body: 'Inter',
      cdn: 'https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@400;600;700&family=Inter:wght@400;500&display=swap',
    },
    colors: {
      primary: '#18181B', secondary: '#3F3F46', accent: '#F4F4F5',
      background: '#FFFFFF', surface: '#FAFAFA', text: '#18181B', text_muted: '#A1A1AA',
    },
    design_instructions: `DESIGN STYLE -- MINIMAL LUXE:
- Background: #FFFFFF pure white
- Cards: bg-[#FAFAFA] rounded-xl (NO shadows, NO borders)
- Black accent: text-[#18181B]
- Buttons: bg-[#18181B] text-white rounded-none px-8 py-3.5
- MAXIMUM whitespace, thin hairline dividers
- Typography: Cormorant Garamond headings, Inter body`,
  },
  neon_night: {
    name: 'Neon Night',
    fonts: {
      heading: 'Space Grotesk',
      body: 'Inter',
      cdn: 'https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;600;700&family=Inter:wght@400;500&display=swap',
    },
    colors: {
      primary: '#8B5CF6', secondary: '#06B6D4', accent: '#1E1B4B',
      background: '#030712', surface: '#111827', text: '#F9FAFB', text_muted: '#9CA3AF',
    },
    design_instructions: `DESIGN STYLE -- NEON NIGHT:
- Background: #030712 (near-black blue)
- Cards: bg-[#111827]/80 backdrop-blur-xl border border-[#8B5CF6]/20
- Neon purple + cyan: text-[#8B5CF6], text-[#06B6D4]
- Buttons: bg-gradient-to-r from-[#8B5CF6] to-[#06B6D4]
- Gradient text on headings
- Typography: Space Grotesk headings, Inter body`,
  },
  malay_heritage: {
    name: 'Warisan Melayu',
    fonts: {
      heading: 'Playfair Display',
      body: 'Poppins',
      cdn: 'https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;700&family=Poppins:wght@400;500;600&display=swap',
    },
    colors: {
      primary: '#B45309', secondary: '#78350F', accent: '#FDE68A',
      background: '#FFFDF5', surface: '#FFFFFF', text: '#292524', text_muted: '#78716C',
    },
    design_instructions: `DESIGN STYLE -- WARISAN MELAYU:
- Background: #FFFDF5 (warm ivory)
- Cards: bg-white rounded-2xl shadow-md border border-[#FDE68A]/30
- Amber/gold accents: text-[#B45309], bg-[#FDE68A]
- Buttons: bg-[#B45309] text-white rounded-xl px-7 py-3
- Typography: Playfair Display headings, Poppins body`,
  },
  ocean_breeze: {
    name: 'Ocean Breeze',
    fonts: {
      heading: 'Source Serif 4',
      body: 'Open Sans',
      cdn: 'https://fonts.googleapis.com/css2?family=Source+Serif+4:wght@400;600;700&family=Open+Sans:wght@400;500;600&display=swap',
    },
    colors: {
      primary: '#0891B2', secondary: '#164E63', accent: '#CFFAFE',
      background: '#F8FDFF', surface: '#FFFFFF', text: '#0C1A22', text_muted: '#5E8A9A',
    },
    design_instructions: `DESIGN STYLE -- OCEAN BREEZE:
- Background: #F8FDFF (cool blue-white)
- Cards: bg-white rounded-2xl shadow-lg shadow-cyan-900/5
- Teal/cyan accents: text-[#0891B2]
- Buttons: bg-[#0891B2] text-white rounded-xl px-7 py-3
- Typography: Source Serif 4 headings, Open Sans body`,
  },
  word_explosion: {
    name: 'Word Explosion',
    fonts: {
      heading: 'Playfair Display',
      body: 'DM Sans',
      cdn: 'https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;700&family=DM+Sans:wght@400;500;700&display=swap',
    },
    colors: {
      primary: '#E85D3A', secondary: '#D4A853', accent: '#FFF0E6',
      background: '#FFF8F0', surface: '#FFFFFF', text: '#1A1A1A', text_muted: '#7A7A7A',
    },
    design_instructions: `DESIGN STYLE -- WORD EXPLOSION:
- Background: #FFF8F0 (warm cream)
- Cards: bg-white rounded-2xl shadow-md border border-[#E85D3A]/10
- Orange accent: text-[#E85D3A], gold: text-[#D4A853]
- Buttons: bg-[#E85D3A] text-white rounded-xl px-7 py-3
- Typography: Playfair Display headings, DM Sans body
- Wrap EVERY visible text word in <span class="fly-word">word</span>
- Include flyIn CSS keyframe and JS randomizer for word tornado effect`,
  },
  ghost_restaurant: {
    name: 'Ghost Restaurant',
    fonts: {
      heading: 'Cormorant Garamond',
      body: 'Outfit',
      cdn: 'https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@400;600;700&family=Outfit:wght@400;500;600&display=swap',
    },
    colors: {
      primary: '#00E5A0', secondary: '#00B8D4', accent: '#1A3D2E',
      background: '#0D0D0D', surface: '#1E1E1E', text: '#EAEAEA', text_muted: '#8A8A8A',
    },
    design_instructions: `DESIGN STYLE -- GHOST RESTAURANT:
- Background: #0D0D0D (deep black)
- Cards: bg-[#1E1E1E]/80 backdrop-blur-xl border border-[#00E5A0]/15
- Neon green accent: text-[#00E5A0], cyan: text-[#00B8D4]
- Buttons: bg-[#00E5A0] text-[#0D0D0D] rounded-xl px-7 py-3
- Typography: Cormorant Garamond headings, Outfit body
- Wrap ALL content in <div id="ghost-wrapper">
- Include ghost cycle engine: vanish after 3s, invisible 4s, reappear for 60s
- Mystery/ghost themed restaurant naming`,
  },
}

/**
 * Mapping from animated template IDs (shown in gallery) to design template IDs.
 * The gallery displays animated hero styles (e.g. 'aurora', 'gradient-wave'),
 * but the AI prompt injection uses design templates (e.g. 'elegance_dark', 'neon_night').
 */
const ANIMATED_TO_DESIGN_MAP: Record<string, string> = {
  'particle-globe': 'neon_night',
  'gradient-wave': 'neon_night',
  'floating-food': 'warm_cozy',
  'neon-grid': 'neon_night',
  'morphing-blob': 'elegance_dark',
  'matrix-code': 'neon_night',
  'aurora': 'elegance_dark',
  'spotlight': 'elegance_dark',
  'parallax-layers': 'fresh_clean',
  'word-explosion': 'word_explosion',
  'ghost-restaurant': 'ghost_restaurant',
}

export function getTemplatePromptInjection(templateId: string): string {
  // First try direct lookup (design template ID), then resolve via animated template mapping
  const designKey = TEMPLATE_DESIGNS[templateId] ? templateId : ANIMATED_TO_DESIGN_MAP[templateId]
  const template = designKey ? TEMPLATE_DESIGNS[designKey] : undefined
  if (!template) return ''

  return `
=== TEMPLATE DESIGN SYSTEM (MUST FOLLOW EXACTLY) ===

TEMPLATE: ${template.name}

GOOGLE FONTS (include this EXACT link in <head>):
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="${template.fonts.cdn}" rel="stylesheet">

TAILWIND CONFIG (include this EXACT script after Tailwind CDN):
<script>
tailwind.config = {
  theme: {
    extend: {
      colors: {
        'primary': '${template.colors.primary}',
        'secondary': '${template.colors.secondary}',
        'accent': '${template.colors.accent}',
        'surface': '${template.colors.surface}',
        'background': '${template.colors.background}',
      },
      fontFamily: {
        'heading': ['${template.fonts.heading}', 'serif'],
        'body': ['${template.fonts.body}', 'sans-serif'],
      }
    }
  }
}
</script>

USE THESE FONTS:
- All headings: font-heading font-bold
- All body text: font-body
- Page background: bg-[${template.colors.background}]
- Main text color: text-[${template.colors.text}]
- Muted text: text-[${template.colors.text_muted}]

AOS ANIMATIONS (include in <head> and before </body>):
<link href="https://unpkg.com/aos@2.3.4/dist/aos.css" rel="stylesheet">
<script src="https://unpkg.com/aos@2.3.4/dist/aos.js"></script>
<script>AOS.init({ duration: 800, once: true, offset: 100 });</script>

Add data-aos="fade-up" to each section.

${template.design_instructions}

=== END TEMPLATE DESIGN SYSTEM ===
`
}
