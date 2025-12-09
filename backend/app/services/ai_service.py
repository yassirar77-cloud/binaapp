"""
AI Service - DeepSeek Integration
Handles website generation using DeepSeek V3
"""

from openai import AsyncOpenAI
from typing import Dict, Optional
from loguru import logger
import json

from app.core.config import settings
from app.models.schemas import WebsiteGenerationRequest, AIGenerationResponse
from app.services.design_system import design_system


class AIService:
    """Service for AI-powered website generation"""

    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=settings.DEEPSEEK_API_KEY,
            base_url=settings.DEEPSEEK_API_URL
        )
        logger.info("DeepSeek AI client initialized")

    async def generate_website(
        self,
        request: WebsiteGenerationRequest,
        style: Optional[str] = None
    ) -> AIGenerationResponse:
        """
        Generate complete website HTML using DeepSeek V3

        Args:
            request: Website generation request
            style: Optional design style (modern, minimal, bold)
        """
        try:
            # Build the prompt with optional style
            prompt = self._build_generation_prompt(request, style)

            # Call DeepSeek API
            response = await self.client.chat.completions.create(
                model=settings.DEEPSEEK_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": self._get_system_prompt(style)
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.7,
                max_tokens=8000,
            )

            # Parse response
            content = response.choices[0].message.content

            # Extract HTML and metadata
            result = self._parse_ai_response(content, request, style)

            logger.info(f"Website generated successfully for {request.business_name} (style: {style or 'default'})")
            return result

        except Exception as e:
            logger.error(f"Error generating website: {e}")
            raise

    async def generate_multi_style(
        self,
        request: WebsiteGenerationRequest
    ) -> Dict[str, AIGenerationResponse]:
        """
        Generate 3 design variations simultaneously (Modern, Minimal, Bold)

        Returns:
            Dict with keys: 'modern', 'minimal', 'bold'
        """
        import asyncio

        logger.info(f"Generating multi-style variations for {request.business_name}")

        # Define the 3 styles
        styles = ['modern', 'minimal', 'bold']

        # Generate all 3 styles in parallel
        tasks = [
            self.generate_website(request, style)
            for style in styles
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Build response dictionary
        variations = {}
        for style, result in zip(styles, results):
            if isinstance(result, Exception):
                logger.error(f"Failed to generate {style} style: {result}")
                # Continue with other styles
                continue
            variations[style] = result

        if not variations:
            raise Exception("Failed to generate any style variations")

        logger.info(f"Generated {len(variations)} style variations successfully")
        return variations

    def _get_system_prompt(self, style: Optional[str] = None) -> str:
        """Get enhanced system prompt with design system guidelines"""

        base_prompt = """You are an expert web developer and UI/UX designer specializing in creating beautiful, professional, production-ready websites for Malaysian SMEs.

Your expertise includes:
- Component-based architecture with reusable patterns
- Professional design systems with consistent visual language
- Modern web technologies (HTML5, CSS3, JavaScript ES6+)
- Mobile-first responsive design
- Accessibility standards (WCAG 2.1)
- Malaysian business context and cultural understanding

## YOUR TASK

Generate a complete, single-file HTML website that includes:
1. **Semantic HTML5** - Proper document structure with header, main, sections, footer
2. **Inline CSS** - Modern, professional styles using CSS Grid, Flexbox, custom properties
3. **Interactive JavaScript** - Smooth scroll, animations, form handling, dynamic features
4. **Responsive Design** - Mobile-first approach with breakpoints (640px, 768px, 1024px)
5. **SEO Optimization** - Meta tags, Open Graph, structured headings
6. **Accessibility** - ARIA labels, keyboard navigation, color contrast
7. **Malaysian Context** - RM currency, +60 phone format, local business practices

## DESIGN PRINCIPLES

- **Consistency**: Use a cohesive design system throughout
- **Hierarchy**: Clear visual hierarchy with typography and spacing
- **White Space**: Generous spacing for readability and focus
- **Performance**: Optimize for fast loading and smooth interactions
- **Quality**: Production-ready code that looks professional"""

        # Add design system guidelines
        if style:
            base_prompt += design_system.get_design_system_prompt(style)
            base_prompt += design_system.get_component_architecture_prompt(style)

        # Add style-specific guidelines
        if style == 'modern':
            base_prompt += """

### MODERN STYLE SPECIFICS
- **Visual Language**: Contemporary, tech-forward, innovative
- **Colors**: Vibrant gradients, bold accent colors, depth with shadows
- **Effects**: Glassmorphism (backdrop-filter: blur), soft shadows, glow effects
- **Typography**: Contemporary sans-serif (Inter, Poppins style), varied weights
- **Animations**: Smooth transitions, micro-interactions, hover effects, fade-ins
- **Layout**: Asymmetric layouts, overlapping elements, creative grids
- **Imagery**: Gradient overlays, modern illustrations, geometric shapes
- **Components**: Rounded corners (12px+), floating elements, gradient buttons

**Code Example:**
```css
.card {
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(10px);
  border-radius: 16px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
  transition: transform 0.3s ease;
}
.card:hover {
  transform: translateY(-8px);
}
```"""

        elif style == 'minimal':
            base_prompt += """

### MINIMAL STYLE SPECIFICS
- **Visual Language**: Clean, sophisticated, timeless, elegant
- **Colors**: Monochromatic (black/white/gray), single accent color
- **Effects**: Subtle shadows, thin borders, no gradients
- **Typography**: System fonts or clean sans-serif, generous line spacing
- **Animations**: Subtle or none, focus on content
- **Layout**: Grid-based, generous whitespace, perfect alignment
- **Imagery**: High-quality photos, minimal processing, natural look
- **Components**: Simple borders, lots of padding, clean lines

**Code Example:**
```css
.card {
  background: #ffffff;
  border: 1px solid #e5e7eb;
  padding: 48px;
  transition: border-color 0.2s ease;
}
.card:hover {
  border-color: #3b82f6;
}
```"""

        elif style == 'bold':
            base_prompt += """

### BOLD STYLE SPECIFICS
- **Visual Language**: Energetic, attention-grabbing, confident, dynamic
- **Colors**: High-contrast combinations, vibrant primaries, saturated colors
- **Effects**: Dramatic shadows, 3D effects, strong borders
- **Typography**: Large, chunky fonts, all-caps headings, strong weight contrast
- **Animations**: Energetic transitions, scale effects, dramatic reveals
- **Layout**: Asymmetric, overlapping sections, creative compositions
- **Imagery**: Vibrant colors, high contrast, bold overlays
- **Components**: Large buttons, thick borders, dramatic hover states

**Code Example:**
```css
.card {
  background: linear-gradient(135deg, #FF3CAC 0%, #784BA0 100%);
  border: 4px solid #000;
  padding: 40px;
  box-shadow: 8px 8px 0px #000;
  transition: all 0.3s ease;
}
.card:hover {
  transform: translate(-4px, -4px);
  box-shadow: 12px 12px 0px #000;
}
```"""

        # Add quality checklist
        base_prompt += design_system.get_quality_checklist()

        base_prompt += """

## OUTPUT FORMAT

Generate ONLY the complete HTML code.
- Start with <!DOCTYPE html>
- Include ALL styles in <style> tag within <head>
- Include ALL JavaScript in <script> tag before </body>
- Do NOT include markdown code blocks (no ```)
- Do NOT include explanations or comments outside the HTML
- Ensure the code is ready to save as .html and open in a browser

Begin generation now:"""

        return base_prompt

    def _build_generation_prompt(self, request: WebsiteGenerationRequest, style: Optional[str] = None) -> str:
        """Build enhanced generation prompt with business-type templates"""
        style_label = f" in {style.upper()} style" if style else ""

        prompt = f"""Generate a professional, production-ready website{style_label} for this Malaysian business:

## BUSINESS INFORMATION

**Business Name**: {request.business_name}
**Business Type**: {request.business_type or 'General Business'}
**Content Language**: {'Bahasa Malaysia' if request.language == 'ms' else 'English'}

**Business Description**:
{request.description}
"""

        # Add business-type specific template
        if request.business_type:
            prompt += design_system.get_business_template_prompt(request.business_type)

        prompt += """

## INTEGRATION REQUIREMENTS
"""

        # WhatsApp integration
        if request.include_whatsapp and request.whatsapp_number:
            prompt += f"""
### WhatsApp Integration
- Floating WhatsApp button (bottom-right, fixed position)
- Phone number: {request.whatsapp_number}
- Green color (#25D366) with hover effects
- Click-to-chat functionality
- Include in hero section CTA as well
"""

        # Maps integration
        if request.include_maps and request.location_address:
            prompt += f"""
### Google Maps Integration
- Embed interactive Google Maps in dedicated section
- Location: {request.location_address}
- Responsive iframe (aspect-ratio: 16/9)
- Include address text display
- "Get Directions" link
"""

        # E-commerce features
        if request.include_ecommerce:
            prompt += """
### E-Commerce Features
- Product grid with professional cards
- Each product: image, name, price (RM), description, "Add to Cart" button
- Shopping cart icon (top-right, fixed)
- Cart count badge
- localStorage-based cart (persistent across page refreshes)
- Sidebar cart panel with checkout
- WhatsApp checkout integration
- Price totals in Malaysian Ringgit (RM)
"""

        # Always include these
        prompt += f"""
### Contact Form
- Professional contact form with validation
- Fields: Name (required), Email (required), Phone, Message (required)
- Submit button with loading state
- Success/error messages
- Email to: {request.contact_email or 'contact@' + request.business_name.lower().replace(' ', '') + '.com'}
- Alternative: WhatsApp submission if available

### Additional Features
- Smooth scroll navigation
- Mobile-responsive hamburger menu
- Social sharing buttons (WhatsApp, Facebook, Twitter)
- Footer with business information
- QR code for website (in footer)
- Scroll-to-top button
- Professional animations (fade-in on scroll)

## WEBSITE STRUCTURE

Create a single-page website with these sections (in order):

1. **Header/Navigation**
   - Logo/business name
   - Navigation menu (links to sections)
   - Mobile hamburger menu
   - Sticky header on scroll

2. **Hero Section**
   - Compelling headline about the business
   - Subheadline with value proposition
   - Primary CTA button (WhatsApp/Contact)
   - Background image or gradient

3. **About/Introduction**
   - Business introduction
   - Key features or values (3-4 items)
   - Professional layout with icons

4. **Main Content** (based on business type)
   - Products/Services/Menu/Portfolio
   - Grid layout with cards
   - Images, descriptions, prices (if applicable)

5. **Location** (if maps enabled)
   - Google Maps embed
   - Address and directions

6. **Contact**
   - Contact form
   - Business contact information
   - Opening hours (if mentioned)

7. **Footer**
   - Copyright
   - Social links
   - QR code
   - Quick links

## TECHNICAL SPECIFICATIONS

- **File Format**: Single HTML file
- **CSS**: All styles in <style> tag within <head>
- **JavaScript**: All scripts in <script> tag before </body>
- **No External Dependencies**: Except Google Maps if needed
- **Meta Tags**: Include comprehensive SEO and Open Graph tags
- **Viewport**: <meta name="viewport" content="width=device-width, initial-scale=1.0">
- **Character Set**: UTF-8
- **Favicon**: Use emoji data URI or default

## QUALITY REQUIREMENTS

✓ Mobile-first responsive design (breakpoints: 640px, 768px, 1024px)
✓ Professional color scheme with consistent palette
✓ Clear typography hierarchy
✓ Smooth animations and transitions
✓ Accessible (ARIA labels, semantic HTML, keyboard nav)
✓ Fast loading (optimized code, lazy loading)
✓ Cross-browser compatible
✓ Production-ready quality

Generate the complete, professional HTML website now:"""

        return prompt

    def _parse_ai_response(
        self,
        content: str,
        request: WebsiteGenerationRequest,
        style: Optional[str] = None
    ) -> AIGenerationResponse:
        """Parse AI response and extract components"""

        # Clean the content (remove markdown code blocks if present)
        html_content = content.strip()
        if html_content.startswith("```html"):
            html_content = html_content[7:]
        if html_content.startswith("```"):
            html_content = html_content[3:]
        if html_content.endswith("```"):
            html_content = html_content[:-3]
        html_content = html_content.strip()

        # Extract meta information
        meta_title = request.business_name
        meta_description = f"{request.business_name} - {request.description[:150]}"

        # Detect sections (basic parsing)
        sections = []
        if "hero" in html_content.lower() or "jumbotron" in html_content.lower():
            sections.append("Hero")
        if "about" in html_content.lower() or "tentang" in html_content.lower():
            sections.append("About")
        if "service" in html_content.lower() or "perkhidmatan" in html_content.lower():
            sections.append("Services")
        if "product" in html_content.lower() or "produk" in html_content.lower():
            sections.append("Products")
        if "contact" in html_content.lower() or "hubungi" in html_content.lower():
            sections.append("Contact")

        # Track integrations
        integrations = []
        if request.include_whatsapp:
            integrations.append("WhatsApp")
        if request.include_maps:
            integrations.append("Google Maps")
        if request.include_ecommerce:
            integrations.append("Shopping Cart")
        integrations.extend(["Contact Form", "Social Sharing", "QR Code"])

        return AIGenerationResponse(
            html_content=html_content,
            css_content=None,  # CSS is inline
            js_content=None,   # JS is inline
            meta_title=meta_title,
            meta_description=meta_description,
            sections=sections,
            integrations_included=integrations
        )


# Create singleton instance
ai_service = AIService()
