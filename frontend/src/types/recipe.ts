/**
 * V2 Component-Recipe TypeScript types.
 *
 * Mirrors the Pydantic schemas in backend/app/schemas/recipe.py.
 * Used by the frontend assembler preview and the section components.
 */

// ---------------------------------------------------------------------------
// Enums
// ---------------------------------------------------------------------------

export const SECTION_TYPES = [
  'hero', 'about', 'menu', 'gallery', 'testimonial', 'contact', 'footer',
] as const
export type SectionType = (typeof SECTION_TYPES)[number]

export const STYLE_DNA_KEYS = [
  'teh_tarik_warm', 'pandan_fresh', 'kopi_hitam', 'sambal_berani',
  'sutera_putih', 'lampu_neon', 'warisan_emas', 'ombak_biru',
  'pasar_malam_neon', 'kampung_serene', 'kopitiam_nostalgia',
  'streetfood_bold', 'fine_dining_obsidian',
] as const
export type StyleDNAKey = (typeof STYLE_DNA_KEYS)[number]

export const VALID_VARIANTS: Record<SectionType, readonly string[]> = {
  hero: ['centered', 'split', 'video', 'minimal', 'slider'],
  about: ['story', 'stats', 'timeline', 'cards', 'minimal'],
  menu: ['grid', 'cards', 'list', 'categorized', 'featured'],
  gallery: ['masonry', 'grid', 'carousel', 'lightbox', 'full-width'],
  testimonial: ['cards', 'slider', 'quote', 'grid', 'minimal'],
  contact: ['simple', 'form', 'map', 'split', 'cards'],
  footer: ['simple', 'columns', 'cta', 'minimal', 'brand'],
} as const

// ---------------------------------------------------------------------------
// Design Brief (Stage 1 — AI output)
// ---------------------------------------------------------------------------

export interface SocialMedia {
  instagram?: string | null
  facebook?: string | null
  tiktok?: string | null
}

export interface BusinessInfo {
  name: string
  type: string
  tagline: string
  about: string[]
  address?: string | null
  whatsapp?: string | null
  email?: string | null
  social_media?: SocialMedia | null
  operating_hours?: string | null
}

export interface SectionSpec {
  type: SectionType
  variant: string
  content: Record<string, unknown>
}

export interface FeatureFlags {
  whatsapp: boolean
  google_map: boolean
  delivery_system: boolean
  gallery: boolean
  price_list: boolean
  operating_hours: boolean
  testimonials: boolean
  social_media: boolean
}

export interface DesignBrief {
  $schema: 'design_brief_v1'
  version: string
  language: 'ms' | 'en'
  business: BusinessInfo
  style_dna: StyleDNAKey
  color_mode: 'light' | 'dark'
  sections: SectionSpec[]
  image_map: Record<string, string>
  features: FeatureFlags
}

// ---------------------------------------------------------------------------
// Page Recipe (Stage 2 — assembler input)
// ---------------------------------------------------------------------------

export interface PageMeta {
  title: string
  description: string
  language: 'ms' | 'en'
  favicon?: string | null
  og_image?: string | null
}

export interface FontTokens {
  heading: string
  heading_weight: string
  body: string
  body_weight: string
  cdn_url: string
}

export interface ColorTokens {
  primary: string
  primary_hover: string
  secondary: string
  accent: string
  background: string
  surface: string
  text: string
  text_muted: string
  border: string
  gradient_from: string
  gradient_to: string
}

export interface DesignTokens {
  border_radius_sm: string
  border_radius_md: string
  border_radius_lg: string
  shadow: string
  shadow_lg: string
  spacing_section: string
  max_width: string
}

export interface ComponentStyles {
  button_primary: string
  button_secondary: string
  card: string
  nav: string
  section_padding: string
}

export interface ThemeTokens {
  style_dna: StyleDNAKey
  fonts: FontTokens
  colors: ColorTokens
  tokens: DesignTokens
  component_styles: ComponentStyles
}

export interface NavLink {
  label: string
  href: string
}

export interface NavCTA {
  label: string
  href: string
}

export interface NavConfig {
  logo_text: string
  links: NavLink[]
  cta?: NavCTA | null
}

export interface AnimationConfig {
  type: string
  delay: number
}

export interface RenderedSection {
  id: string
  component: string
  props: Record<string, unknown>
  animation: AnimationConfig
}

export interface TailwindConfig {
  theme: Record<string, unknown>
}

export interface PageRecipe {
  $schema: 'page_recipe_v1'
  version: string
  meta: PageMeta
  theme: ThemeTokens
  nav: NavConfig
  sections: RenderedSection[]
  head_assets: string[]
  tailwind_config?: TailwindConfig | null
  body_scripts: string[]
  init_scripts: string[]
}

// ---------------------------------------------------------------------------
// Component props — each section component receives these via PageRecipe
// ---------------------------------------------------------------------------

export interface HeroSplitProps {
  headline: string
  subheadline: string
  cta_text: string
  cta_link: string
  cta_secondary_text?: string
  cta_secondary_link?: string
  image_url?: string | null
  image_alt?: string
  image_position?: 'left' | 'right'
}

export interface AboutStoryProps {
  heading: string
  paragraphs: string[]
  image_url?: string | null
  image_alt?: string
  image_position?: 'left' | 'right'
}

export interface MenuItem {
  name: string
  description: string
  price: string
  image_url?: string | null
  badge?: string | null
}

export interface MenuGridProps {
  heading: string
  subheading?: string
  items: MenuItem[]
}

export interface GalleryImage {
  url: string
  alt: string
}

export interface GalleryMasonryProps {
  heading: string
  images: GalleryImage[]
}

export interface TestimonialReview {
  name: string
  text: string
  rating: number
  avatar_fallback: string
}

export interface TestimonialCardsProps {
  heading: string
  reviews: TestimonialReview[]
}

export interface ContactSplitProps {
  heading: string
  whatsapp_number?: string
  whatsapp_cta?: string
  address?: string
  hours?: string
  show_map?: boolean
  map_query?: string
  email?: string
}

export interface FooterBrandProps {
  business_name: string
  tagline?: string
  social_links?: { platform: string; url: string; icon: string }[]
  copyright_year?: number
  powered_by?: boolean
  whatsapp_number?: string
}
