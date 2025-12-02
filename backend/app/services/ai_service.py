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
        request: WebsiteGenerationRequest
    ) -> AIGenerationResponse:
        """
        Generate complete website HTML using DeepSeek V3
        """
        try:
            # Build the prompt
            prompt = self._build_generation_prompt(request)

            # Call DeepSeek API
            response = await self.client.chat.completions.create(
                model=settings.DEEPSEEK_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": self._get_system_prompt()
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
            result = self._parse_ai_response(content, request)

            logger.info(f"Website generated successfully for {request.business_name}")
            return result

        except Exception as e:
            logger.error(f"Error generating website: {e}")
            raise

    def _get_system_prompt(self) -> str:
        """Get system prompt for AI"""
        return """You are an expert web developer specializing in creating beautiful, modern, responsive websites for Malaysian SMEs.

Your task is to generate complete, production-ready HTML that includes:
1. Modern, responsive design with mobile-first approach
2. Professional color schemes and typography
3. Inline CSS (Tailwind-inspired or custom)
4. Interactive JavaScript for dynamic features
5. SEO-optimized meta tags
6. Integration components (WhatsApp, Maps, Contact Forms, etc.)

Important guidelines:
- Use semantic HTML5
- Ensure mobile responsiveness
- Include proper accessibility features
- Add smooth animations and transitions
- Use modern CSS Grid and Flexbox
- Support both Bahasa Malaysia and English content
- Include Malaysian ringgit (RM) for pricing
- Use Malaysian phone format (+60)

Return ONLY valid HTML without any markdown code blocks or explanations."""

    def _build_generation_prompt(self, request: WebsiteGenerationRequest) -> str:
        """Build the generation prompt"""
        prompt = f"""Create a complete, modern website for a Malaysian business with these specifications:

Business Name: {request.business_name}
Business Type: {request.business_type or 'General Business'}
Language: {'Bahasa Malaysia' if request.language == 'ms' else 'English'}

Description:
{request.description}

Required Integrations:
"""

        # WhatsApp integration
        if request.include_whatsapp and request.whatsapp_number:
            prompt += f"""
- WhatsApp Business Button (floating): {request.whatsapp_number}
  * Add a floating WhatsApp button (bottom-right corner)
  * Include quick order/inquiry functionality
  * Use WhatsApp green color (#25D366)
"""

        # Maps integration
        if request.include_maps and request.location_address:
            prompt += f"""
- Google Maps Embed: {request.location_address}
  * Embed interactive Google Maps
  * Add location marker and address display
"""

        # E-commerce features
        if request.include_ecommerce:
            prompt += """
- Shopping Cart System:
  * Add product cards with "Add to Cart" buttons
  * Implement localStorage-based shopping cart
  * Cart icon with item count in header
  * Simple checkout flow
  * Price display in Malaysian Ringgit (RM)
"""

        # Always include these
        prompt += f"""
- Contact Form:
  * Name, email, phone, message fields
  * Form validation
  * Submit to: {request.contact_email or 'contact@' + request.business_name.lower() + '.com'}

- Social Sharing Buttons:
  * Facebook, WhatsApp, Twitter, LinkedIn
  * Share current page

- QR Code:
  * Generate QR code for the website URL
  * Display in footer or contact section

Design Requirements:
- Modern, professional design
- Responsive (mobile, tablet, desktop)
- Fast loading and optimized
- Use attractive color scheme matching the business type
- Include hero section, services/products, about, contact sections
- Add smooth scroll and animations
- Include navigation menu with smooth scroll to sections

Technical Requirements:
- Single HTML file with inline CSS and JavaScript
- No external dependencies (except Google Maps API if needed)
- SEO optimized with proper meta tags
- Open Graph tags for social sharing
- Clean, well-commented code

Generate the complete HTML now:"""

        return prompt

    def _parse_ai_response(
        self,
        content: str,
        request: WebsiteGenerationRequest
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
