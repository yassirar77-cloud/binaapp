"""
Design System and Prompt Engineering
SuperDesign-inspired component architecture and design guidelines
"""

from typing import Dict, Optional
from loguru import logger


class DesignSystem:
    """Professional design system guidelines for AI generation"""

    # Color Palettes by Style
    COLOR_PALETTES = {
        "modern": {
            "primary": ["#8B5CF6", "#6366F1", "#3B82F6"],  # Purple, Indigo, Blue
            "secondary": ["#06B6D4", "#10B981", "#14B8A6"],  # Cyan, Green, Teal
            "accent": ["#F59E0B", "#EF4444", "#EC4899"],  # Amber, Red, Pink
            "neutral": ["#F9FAFB", "#E5E7EB", "#1F2937"],  # Light, Mid, Dark gray
            "gradients": [
                "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
                "linear-gradient(135deg, #f093fb 0%, #f5576c 100%)",
                "linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)"
            ]
        },
        "minimal": {
            "primary": ["#000000", "#1F2937", "#374151"],  # Black, Dark grays
            "secondary": ["#6B7280", "#9CA3AF", "#D1D5DB"],  # Mid grays
            "accent": ["#3B82F6"],  # Single blue accent
            "neutral": ["#FFFFFF", "#F9FAFB", "#F3F4F6"],  # Whites, Light grays
            "gradients": []  # No gradients in minimal
        },
        "bold": {
            "primary": ["#DC2626", "#F59E0B", "#8B5CF6"],  # Red, Orange, Purple
            "secondary": ["#059669", "#0EA5E9", "#EC4899"],  # Green, Blue, Pink
            "accent": ["#FBBF24", "#34D399", "#F472B6"],  # Yellow, Mint, Pink
            "neutral": ["#FEF3C7", "#FEE2E2", "#1F2937"],  # Warm backgrounds
            "gradients": [
                "linear-gradient(135deg, #FA8BFF 0%, #2BD2FF 52%, #2BFF88 90%)",
                "linear-gradient(135deg, #FF3CAC 0%, #784BA0 50%, #2B86C5 100%)",
                "linear-gradient(135deg, #F97794 0%, #623AA2 100%)"
            ]
        }
    }

    # Typography Systems
    TYPOGRAPHY = {
        "modern": {
            "font_family": "Inter, system-ui, -apple-system, sans-serif",
            "headings": "Poppins, Inter, sans-serif",
            "body": "Inter, system-ui, sans-serif",
            "scale": {
                "h1": "3.5rem",
                "h2": "2.5rem",
                "h3": "2rem",
                "h4": "1.5rem",
                "body": "1rem",
                "small": "0.875rem"
            },
            "weights": {
                "regular": "400",
                "medium": "500",
                "semibold": "600",
                "bold": "700",
                "extrabold": "800"
            }
        },
        "minimal": {
            "font_family": "-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
            "headings": "-apple-system, sans-serif",
            "body": "-apple-system, sans-serif",
            "scale": {
                "h1": "3rem",
                "h2": "2.25rem",
                "h3": "1.875rem",
                "h4": "1.5rem",
                "body": "1rem",
                "small": "0.875rem"
            },
            "weights": {
                "regular": "300",
                "medium": "400",
                "semibold": "500",
                "bold": "600",
                "extrabold": "700"
            }
        },
        "bold": {
            "font_family": "Montserrat, 'Arial Black', sans-serif",
            "headings": "Montserrat, Impact, sans-serif",
            "body": "Open Sans, Arial, sans-serif",
            "scale": {
                "h1": "4rem",
                "h2": "3rem",
                "h3": "2.25rem",
                "h4": "1.75rem",
                "body": "1.125rem",
                "small": "1rem"
            },
            "weights": {
                "regular": "400",
                "medium": "600",
                "semibold": "700",
                "bold": "800",
                "extrabold": "900"
            }
        }
    }

    # Spacing System (8px grid)
    SPACING = {
        "xs": "0.5rem",   # 8px
        "sm": "1rem",     # 16px
        "md": "1.5rem",   # 24px
        "lg": "2rem",     # 32px
        "xl": "3rem",     # 48px
        "2xl": "4rem",    # 64px
        "3xl": "6rem",    # 96px
    }

    # Component Patterns
    COMPONENTS = {
        "button": {
            "modern": "Rounded corners (12px), gradient background, subtle shadow, hover scale",
            "minimal": "Simple border (1px), no shadow, subtle hover underline",
            "bold": "Chunky padding, all-caps text, strong shadow, dramatic hover transform"
        },
        "card": {
            "modern": "Glassmorphism effect, backdrop blur, gradient border, floating shadow",
            "minimal": "Clean white background, thin border, lots of whitespace",
            "bold": "Colorful background, thick borders, overlapping elements, strong shadows"
        },
        "navigation": {
            "modern": "Sticky header, gradient background, smooth scroll, animated indicators",
            "minimal": "Simple top bar, black text, minimal padding, thin divider",
            "bold": "Large header, contrasting colors, chunky menu items, bold separators"
        },
        "hero": {
            "modern": "Full viewport height, gradient overlay, animated elements, CTA with gradient",
            "minimal": "Centered content, lots of whitespace, single accent color, clean typography",
            "bold": "Diagonal sections, vibrant background, large text, multiple CTAs"
        }
    }

    # Business Type Templates
    BUSINESS_TEMPLATES = {
        "restaurant": {
            "sections": ["Hero", "Menu", "About", "Gallery", "Location", "Contact"],
            "components": ["Menu cards with images", "Category filters", "Special offers banner"],
            "features": ["Online menu with prices", "Photo gallery", "Opening hours", "Delivery info"]
        },
        "booking": {
            "sections": ["Hero", "Services", "Pricing", "Team", "Booking", "Contact"],
            "components": ["Service cards", "Pricing tables", "Calendar availability", "Team profiles"],
            "features": ["Appointment booking", "Service selection", "Time slots", "Confirmation"]
        },
        "portfolio": {
            "sections": ["Hero", "About", "Portfolio", "Services", "Testimonials", "Contact"],
            "components": ["Project grid", "Lightbox gallery", "Testimonial cards", "Skill badges"],
            "features": ["Image gallery", "Project details", "Client testimonials", "Contact form"]
        },
        "shop": {
            "sections": ["Hero", "Products", "Categories", "About", "Shipping", "Contact"],
            "components": ["Product grid", "Category filters", "Product cards", "Add to cart"],
            "features": ["Product catalog", "Shopping cart", "WhatsApp checkout", "Product search"]
        },
        "general": {
            "sections": ["Hero", "About", "Services", "Features", "Contact"],
            "components": ["Feature cards", "Icon boxes", "CTA sections"],
            "features": ["Contact form", "Social links", "Business info"]
        }
    }

    @staticmethod
    def get_design_system_prompt(style: Optional[str] = None) -> str:
        """Get comprehensive design system guidelines"""

        if not style:
            return ""

        colors = DesignSystem.COLOR_PALETTES.get(style, DesignSystem.COLOR_PALETTES["modern"])
        typography = DesignSystem.TYPOGRAPHY.get(style, DesignSystem.TYPOGRAPHY["modern"])

        prompt = f"""

## DESIGN SYSTEM GUIDELINES

### Color Palette
Primary Colors: {', '.join(colors['primary'])}
Secondary Colors: {', '.join(colors['secondary'])}
Accent Colors: {', '.join(colors['accent'])}
Neutral Colors: {', '.join(colors['neutral'])}
"""

        if colors['gradients']:
            prompt += f"Gradients: {', '.join(colors['gradients'][:2])}\n"

        prompt += f"""
### Typography
Font Family: {typography['font_family']}
Heading Font: {typography['headings']}
Body Font: {typography['body']}

Font Sizes:
- H1: {typography['scale']['h1']} (weight: {typography['weights']['bold']})
- H2: {typography['scale']['h2']} (weight: {typography['weights']['semibold']})
- H3: {typography['scale']['h3']} (weight: {typography['weights']['semibold']})
- Body: {typography['scale']['body']} (weight: {typography['weights']['regular']})

### Spacing System (8px grid)
- XS: 8px
- SM: 16px
- MD: 24px
- LG: 32px
- XL: 48px
- 2XL: 64px
- 3XL: 96px

Use consistent spacing throughout the design.
"""

        return prompt

    @staticmethod
    def get_component_architecture_prompt(style: Optional[str] = None) -> str:
        """Get component-based architecture guidelines"""

        components = DesignSystem.COMPONENTS

        prompt = """

## COMPONENT ARCHITECTURE

Build the website using these reusable component patterns:

### 1. Navigation Component
"""
        if style:
            prompt += f"Style: {components['navigation'].get(style, components['navigation']['modern'])}\n"

        prompt += """
- Logo on the left
- Navigation links (smooth scroll to sections)
- Mobile hamburger menu (responsive)
- Sticky on scroll with shadow

### 2. Hero Section
"""
        if style:
            prompt += f"Style: {components['hero'].get(style, components['hero']['modern'])}\n"

        prompt += """
- Eye-catching headline
- Compelling subheadline
- Primary CTA button
- Supporting image/illustration
- Background design matching style

### 3. Card Component (reusable)
"""
        if style:
            prompt += f"Style: {components['card'].get(style, components['card']['modern'])}\n"

        prompt += """
- Consistent padding
- Hover effects
- Icon/image at top
- Title, description, CTA
- Use for services, products, features

### 4. Button Component (reusable)
"""
        if style:
            prompt += f"Style: {components['button'].get(style, components['button']['modern'])}\n"

        prompt += """
- Primary variant (main actions)
- Secondary variant (alternative actions)
- Outline variant (less prominent)
- Consistent sizing and spacing
- Hover and active states

### 5. Section Container (reusable)
- Max width: 1200px
- Centered with auto margins
- Consistent vertical padding (64px-96px)
- Responsive padding (smaller on mobile)

### 6. Grid System
- Use CSS Grid for layouts
- 12-column grid for desktop
- 1-2 columns for mobile
- Consistent gaps (24px-32px)
"""

        return prompt

    @staticmethod
    def get_business_template_prompt(business_type: str) -> str:
        """Get business-type specific template structure"""

        template = DesignSystem.BUSINESS_TEMPLATES.get(
            business_type,
            DesignSystem.BUSINESS_TEMPLATES["general"]
        )

        prompt = f"""

## BUSINESS TYPE: {business_type.upper()}

### Required Sections (in order):
{', '.join(template['sections'])}

### Key Components:
"""
        for component in template['components']:
            prompt += f"- {component}\n"

        prompt += "\n### Must-Have Features:\n"
        for feature in template['features']:
            prompt += f"- {feature}\n"

        # Add business-specific guidelines
        if business_type == "restaurant":
            prompt += """
### Restaurant-Specific Guidelines:
- Showcase food imagery prominently
- Display menu with categories and prices in RM
- Highlight special dishes or promotions
- Include delivery/takeaway information
- Show opening hours clearly
- Add "Order Now" CTAs
"""
        elif business_type == "booking":
            prompt += """
### Booking-Specific Guidelines:
- Display services with clear descriptions
- Show pricing transparently
- Include team member profiles with photos
- Add testimonials/reviews
- Prominent "Book Now" buttons
- Show availability or operating hours
"""
        elif business_type == "portfolio":
            prompt += """
### Portfolio-Specific Guidelines:
- Showcase best work in hero section
- Use grid layout for portfolio items
- Add hover effects on project cards
- Include project details/descriptions
- Show skills or services offered
- Add client testimonials
- Include downloadable resume/CV option
"""
        elif business_type == "shop":
            prompt += """
### Shop-Specific Guidelines:
- Product grid with clear images
- Display prices in RM prominently
- Add "Add to Cart" buttons
- Show product categories
- Include product descriptions
- Add search/filter functionality
- Highlight bestsellers or new arrivals
"""

        return prompt

    @staticmethod
    def get_quality_checklist() -> str:
        """Get quality assurance checklist"""

        return """

## QUALITY ASSURANCE CHECKLIST

Before generating, ensure the website has:

### Visual Design
✓ Consistent color palette throughout
✓ Proper typography hierarchy
✓ Balanced white space
✓ Professional imagery placement
✓ Cohesive visual style

### Responsiveness
✓ Mobile-first approach
✓ Breakpoints: 640px (mobile), 768px (tablet), 1024px (desktop)
✓ Flexible images (max-width: 100%)
✓ Readable text on all devices
✓ Touch-friendly buttons (min 44px)

### Performance
✓ Minimal inline styles (prefer CSS classes)
✓ Optimized animations
✓ Lazy loading for images
✓ Efficient JavaScript
✓ No unnecessary dependencies

### Accessibility
✓ Semantic HTML tags
✓ Alt text for images
✓ Proper heading hierarchy (h1-h6)
✓ Sufficient color contrast (WCAG AA)
✓ Keyboard navigation support
✓ ARIA labels where needed

### Interactivity
✓ Smooth scroll navigation
✓ Hover effects on interactive elements
✓ Form validation
✓ Loading states
✓ Success/error messages

### Malaysian Context
✓ Currency in RM (Malaysian Ringgit)
✓ Phone numbers in +60 format
✓ Bahasa Malaysia or English content
✓ Local business context
✓ WhatsApp integration (popular in Malaysia)
"""


# Create singleton instance
design_system = DesignSystem()
