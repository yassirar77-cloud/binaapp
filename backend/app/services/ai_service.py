"""
AI Service - Qwen & DeepSeek Integration
Handles website generation using Qwen Max 3 (primary) and DeepSeek V3 (fallback)
"""
from openai import AsyncOpenAI
from typing import Dict, Optional
from loguru import logger
import json
import httpx
from app.core.config import settings
from app.models.schemas import WebsiteGenerationRequest, AIGenerationResponse
from app.services.design_system import design_system

class AIService:
    """Service for AI-powered website generation"""
    
    def __init__(self):
        logger.info("=" * 80)
        logger.info("🤖 Initializing AI Service...")
        logger.info("=" * 80)

        # DEBUG: Log all API configuration
        logger.info("🔍 API Configuration Debug:")
        logger.info(f"   QWEN_API_KEY: {settings.QWEN_API_KEY[:15]}..." if settings.QWEN_API_KEY else "   QWEN_API_KEY: NOT SET")
        logger.info(f"   QWEN_API_URL: {settings.QWEN_API_URL}")
        logger.info(f"   QWEN_MODEL: {settings.QWEN_MODEL}")
        logger.info(f"   DEEPSEEK_API_KEY: {settings.DEEPSEEK_API_KEY[:15]}..." if settings.DEEPSEEK_API_KEY else "   DEEPSEEK_API_KEY: NOT SET")
        logger.info(f"   DEEPSEEK_API_URL: {settings.DEEPSEEK_API_URL}")
        logger.info(f"   DEEPSEEK_MODEL: {settings.DEEPSEEK_MODEL}")

        # Configure timeout for API calls (critical for Render)
        # 2-minute timeout for AI generation (DeepSeek can be slow)
        timeout = httpx.Timeout(
            timeout=120.0,     # Total timeout (2 minutes)
            connect=15.0,      # Connection timeout
            read=120.0,        # Read timeout (match total)
            write=30.0         # Write timeout
        )
        logger.info(f"⏱️  Configured API timeout: 120s total, 15s connect")

        # Initialize Qwen client (primary)
        if settings.QWEN_API_KEY:
            try:
                # Strip whitespace/newlines from API key (common env var issue)
                qwen_key = settings.QWEN_API_KEY.strip()
                logger.info(f"🔗 Connecting to Qwen API ({settings.QWEN_API_URL})...")
                self.qwen_client = AsyncOpenAI(
                    api_key=qwen_key,
                    base_url=settings.QWEN_API_URL,
                    timeout=timeout,
                    http_client=httpx.AsyncClient(
                        verify=True,
                        timeout=timeout,
                        follow_redirects=True,
                        limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
                    )
                )
                logger.info("✅ Qwen Max 3 AI client initialized (PRIMARY)")
            except Exception as e:
                self.qwen_client = None
                logger.error(f"❌ Failed to initialize Qwen client: {e}")
                logger.error(f"   Error type: {type(e).__name__}")
        else:
            self.qwen_client = None
            logger.warning("⚠️ Qwen API key not found - Qwen disabled")

        # Initialize DeepSeek client (fallback)
        if settings.DEEPSEEK_API_KEY:
            try:
                # Strip whitespace/newlines from API key (common env var issue)
                deepseek_key = settings.DEEPSEEK_API_KEY.strip()
                logger.info("🔗 Connecting to DeepSeek API (api.deepseek.com)...")
                self.deepseek_client = AsyncOpenAI(
                    api_key=deepseek_key,
                    base_url="https://api.deepseek.com",  # Hardcoded to ensure correct URL
                    timeout=timeout,
                    http_client=httpx.AsyncClient(
                        verify=True,
                        timeout=timeout,
                        follow_redirects=True,
                        limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
                    )
                )
                logger.info("✅ DeepSeek AI client initialized (FALLBACK)")
            except Exception as e:
                self.deepseek_client = None
                logger.error(f"❌ Failed to initialize DeepSeek client: {e}")
                logger.error(f"   Error type: {type(e).__name__}")
        else:
            self.deepseek_client = None
            logger.warning("⚠️ DeepSeek API key not found - DeepSeek disabled")

        # Validate at least one AI service is available
        if not self.qwen_client and not self.deepseek_client:
            logger.error("=" * 80)
            logger.error("❌ CRITICAL: No AI services available!")
            logger.error("Please set either QWEN_API_KEY or DEEPSEEK_API_KEY")
            logger.error("=" * 80)
            raise RuntimeError("No AI services configured. Set QWEN_API_KEY or DEEPSEEK_API_KEY environment variables.")

        logger.info("=" * 80)
        logger.info("✅ AI Service initialized successfully")
        logger.info(f"   Qwen: {'Available' if self.qwen_client else 'Disabled'}")
        logger.info(f"   DeepSeek: {'Available' if self.deepseek_client else 'Disabled'}")
        logger.info("=" * 80)
    
    async def generate_website(
        self,
        request: WebsiteGenerationRequest,
        style: Optional[str] = None
    ) -> AIGenerationResponse:
        """
        Generate complete website HTML using Qwen Max 3 (primary) or DeepSeek (fallback)

        Args:
            request: Website generation request
            style: Optional design style (modern, minimal, bold)
        """
        # Try Qwen first
        if self.qwen_client:
            try:
                logger.info(f"🎨 Generating website with Qwen for {request.business_name} (style: {style or 'default'})")
                return await self._generate_with_qwen(request, style)
            except Exception as e:
                logger.error(f"❌ Qwen generation failed!")
                logger.error(f"   Error type: {type(e).__name__}")
                logger.error(f"   Error message: {str(e)}")
                if hasattr(e, 'response'):
                    logger.error(f"   Response status: {getattr(e.response, 'status_code', 'N/A')}")
                    logger.error(f"   Response body: {getattr(e.response, 'text', 'N/A')[:500]}")
                if hasattr(e, '__cause__') and e.__cause__:
                    logger.error(f"   Root cause: {type(e.__cause__).__name__}: {e.__cause__}")
                if self.deepseek_client:
                    logger.info("🔄 Falling back to DeepSeek...")
                else:
                    logger.error("❌ No fallback available - DeepSeek not configured")
                    raise

        # Fallback to DeepSeek
        if self.deepseek_client:
            try:
                logger.info(f"⚡ Generating website with DeepSeek for {request.business_name} (style: {style or 'default'})")
                return await self._generate_with_deepseek(request, style)
            except Exception as e:
                logger.error(f"❌ DeepSeek generation also failed!")
                logger.error(f"   Error type: {type(e).__name__}")
                logger.error(f"   Error message: {str(e)}")
                if hasattr(e, 'response'):
                    logger.error(f"   Response status: {getattr(e.response, 'status_code', 'N/A')}")
                    logger.error(f"   Response body: {getattr(e.response, 'text', 'N/A')[:500]}")
                if hasattr(e, '__cause__') and e.__cause__:
                    logger.error(f"   Root cause: {type(e.__cause__).__name__}: {e.__cause__}")
                raise

        # No AI service available
        logger.error("❌ No AI service is available for generation")
        raise RuntimeError("No AI service configured. Please check your API keys.")
    
    async def _generate_with_qwen(
        self,
        request: WebsiteGenerationRequest,
        style: Optional[str] = None
    ) -> AIGenerationResponse:
        """Generate website using Qwen Max 3"""
        
        prompt = self._build_generation_prompt(request, style)

        logger.info(f"🔗 Calling Qwen API with model: {settings.QWEN_MODEL}")
        logger.info(f"   Base URL: {settings.QWEN_API_URL}")
        response = await self.qwen_client.chat.completions.create(
            model=settings.QWEN_MODEL,
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
            max_tokens=4000,  # Reduced for faster response
        )

        content = response.choices[0].message.content
        result = self._parse_ai_response(content, request, style)

        logger.info(f"✅ Website generated successfully with Qwen Max 3 ({len(result.html_content)} chars)")
        return result

    async def _generate_with_deepseek(
        self,
        request: WebsiteGenerationRequest,
        style: Optional[str] = None
    ) -> AIGenerationResponse:
        """Generate website using DeepSeek V3 (fallback)"""

        prompt = self._build_generation_prompt(request, style)

        logger.info(f"🔗 Calling DeepSeek API with model: {settings.DEEPSEEK_MODEL}")
        logger.info(f"   Base URL: https://api.deepseek.com")
        response = await self.deepseek_client.chat.completions.create(
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
            max_tokens=4000,  # Reduced for faster response
        )
        
        content = response.choices[0].message.content
        result = self._parse_ai_response(content, request, style)
        
        logger.info(f"✅ Website generated successfully with DeepSeek ({len(result.html_content)} chars)")
        return result
    
    async def generate_multi_style(
        self,
        request: WebsiteGenerationRequest
    ) -> Dict[str, AIGenerationResponse]:
        """
        Generate 3 design variations simultaneously (Modern, Minimal, Bold)
        Uses Qwen Max 3 for best quality

        Returns:
            Dict with keys: 'modern', 'minimal', 'bold'
        """
        import asyncio

        logger.info(f"🎨 Generating multi-style variations for {request.business_name}")

        styles = ['modern', 'minimal', 'bold']
        tasks = [self.generate_website(request, style) for style in styles]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        variations = {}
        for style, result in zip(styles, results):
            if isinstance(result, Exception):
                logger.error(f"❌ Failed to generate {style} style: {result}")
                continue
            variations[style] = result

        if not variations:
            raise Exception("Failed to generate any style variations")

        logger.info(f"✅ Generated {len(variations)} style variations successfully")
        return variations

    async def generate_website_dual(
        self,
        request: WebsiteGenerationRequest,
        style: Optional[str] = None
    ) -> Dict[str, Optional[str]]:
        """
        Generate websites using BOTH AIs in parallel, return both results

        Args:
            request: Website generation request
            style: Optional design style

        Returns:
            Dict with keys: 'qwen', 'deepseek', 'success'
        """
        import asyncio

        logger.info(f"🎨 Dual AI generation for {request.business_name}")
        logger.info("Running Qwen and DeepSeek in parallel...")

        # Run both APIs in parallel
        qwen_task = self._generate_with_qwen(request, style) if self.qwen_client else None
        deepseek_task = self._generate_with_deepseek(request, style) if self.deepseek_client else None

        tasks = []
        if qwen_task:
            tasks.append(qwen_task)
        if deepseek_task:
            tasks.append(deepseek_task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        qwen_result = None
        deepseek_result = None

        if qwen_task and len(results) > 0:
            if not isinstance(results[0], Exception):
                qwen_result = results[0].html_content
            else:
                logger.error(f"Qwen generation failed: {results[0]}")

        if deepseek_task:
            result_idx = 1 if qwen_task else 0
            if len(results) > result_idx and not isinstance(results[result_idx], Exception):
                deepseek_result = results[result_idx].html_content
            elif len(results) > result_idx:
                logger.error(f"DeepSeek generation failed: {results[result_idx]}")

        logger.info(f"✅ Dual generation complete - Qwen: {bool(qwen_result)}, DeepSeek: {bool(deepseek_result)}")

        return {
            "qwen": qwen_result,
            "deepseek": deepseek_result,
            "success": bool(qwen_result or deepseek_result)
        }

    async def generate_website_best(
        self,
        request: WebsiteGenerationRequest,
        style: Optional[str] = None
    ) -> str:
        """
        Generate with both AIs, use DeepSeek to pick/combine the best parts

        Args:
            request: Website generation request
            style: Optional design style

        Returns:
            Combined/best HTML content
        """
        logger.info(f"🎨 Best-of-both generation for {request.business_name}")

        # Get both designs
        results = await self.generate_website_dual(request, style)

        if not results["qwen"] and not results["deepseek"]:
            raise Exception("Both AI services failed to generate website")

        # If only one succeeded, return that
        if not results["qwen"]:
            logger.info("Only DeepSeek succeeded, returning its result")
            return results["deepseek"]
        if not results["deepseek"]:
            logger.info("Only Qwen succeeded, returning its result")
            return results["qwen"]

        # Both succeeded - use DeepSeek to combine best parts
        logger.info("Both AIs succeeded, combining best parts...")

        try:
            combine_prompt = f"""You are a web design expert. I have two website designs for the same business: {request.business_name}.

DESIGN A (Qwen):
```html
{results["qwen"][:4000]}
```

DESIGN B (DeepSeek):
```html
{results["deepseek"][:4000]}
```

Create the BEST final website by combining the best elements from both:
- Best layout and structure
- Best colors and styling
- Best animations and effects
- Best content organization
- Most professional appearance

Output ONLY the final HTML code, no explanations."""

            if self.deepseek_client:
                logger.info("Using DeepSeek to combine designs...")
                response = await self.deepseek_client.chat.completions.create(
                    model=settings.DEEPSEEK_MODEL,
                    messages=[
                        {"role": "system", "content": "You are an expert web designer."},
                        {"role": "user", "content": combine_prompt}
                    ],
                    temperature=0.7,
                    max_tokens=4000
                )

                final = response.choices[0].message.content

                # Extract HTML
                if "```html" in final:
                    final = final.split("```html")[1].split("```")[0]
                elif "```" in final:
                    final = final.split("```")[1].split("```")[0]

                logger.info("✅ Successfully combined designs")
                return final.strip()

        except Exception as e:
            logger.error(f"Failed to combine designs: {e}")
            logger.info("Falling back to DeepSeek result")

        # Fallback to DeepSeek result
        return results["deepseek"]
    
    def _get_system_prompt(self, style: Optional[str] = None) -> str:
        """Get enhanced system prompt for professional hospitality website generation"""

        return """You are an expert web designer creating stunning, professional websites for restaurants and hospitality businesses.

Generate a complete, production-ready HTML file with embedded Tailwind CSS using this exact structure:

## DESIGN FRAMEWORK WITH NUMBERED ZONES

### 1. HEADER & NAVIGATION
- Top full-width red accent bar (bg-red-600 or #E31E24)
- White utility bar with business contact info
- Main Navigation: HOME | ABOUT | SERVICES | MENU | CONTACT
- Sticky header on scroll

### 2. HERO SECTION (ZONE 1)
- Full-width image/video container with overlay
- Use high-quality restaurant images from Unsplash
- Overlay with centered white text:
  - Business establishment info (uppercase, tracking-widest)
  - Compelling tagline about the business
- Dark overlay (bg-black/50) for text readability
- Minimum height: 80vh

### 3. SERVICE GRID (ZONES 2, 3, 4)
Create a 3-column responsive grid (grid-cols-1 md:grid-cols-3):
- Each column: image at top, service list below with hover effects
- Smooth transitions on all interactive elements

### 4. PORTFOLIO/GALLERY MOSAIC (ZONES 5, 6, 7, 8)
2x2 grid (grid-cols-1 md:grid-cols-2), each card:
- Background image covering full card
- On hover: dark overlay with title + CTA button
- Smooth transition (transition-all duration-300)

### 5. FOOTER
- Dark gray background (#333333 or bg-gray-800)
- 3-column layout: Address | Phone | Email
- Centered social icons (Facebook, Instagram, Twitter) using SVG
- Bottom accent bar with Copyright text

## TECHNICAL REQUIREMENTS

1. Include Tailwind CSS via CDN:
   <script src="https://cdn.tailwindcss.com"></script>

2. Include Google Fonts (Poppins):
   <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&display=swap" rel="stylesheet">

3. Add smooth scroll behavior:
   <style>html { scroll-behavior: smooth; } body { font-family: 'Poppins', sans-serif; }</style>

4. Mobile responsive (all grids collapse to single column)

5. Hover effects on all interactive elements

6. Professional color scheme with primary brand color

7. Add subtle animations:
   - Scale on hover for cards
   - Smooth transitions everywhere

8. Include placeholder comments like <!-- ZONE 1: Hero --> for easy editing

Generate the COMPLETE HTML file with all sections. Output ONLY the HTML code, no explanations."""
    
    def _build_generation_prompt(self, request: WebsiteGenerationRequest, style: Optional[str] = None) -> str:
        """Build generation prompt for professional hospitality website design"""

        # Determine business type for appropriate imagery
        business_type = (request.business_type or 'restaurant').lower()

        # Select appropriate Unsplash images based on business type
        if 'restaurant' in business_type or 'cafe' in business_type or 'food' in business_type:
            hero_image = "https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?w=1920"
            gallery_images = [
                "https://images.unsplash.com/photo-1466978913421-dad2ebd01d17?w=800",
                "https://images.unsplash.com/photo-1504674900247-0877df9cc836?w=800",
                "https://images.unsplash.com/photo-1555396273-367ea4eb4db5?w=800",
                "https://images.unsplash.com/photo-1559329007-40df8a9345d8?w=800"
            ]
            service_images = [
                "https://images.unsplash.com/photo-1460925895917-afdab827c52f?w=600",
                "https://images.unsplash.com/photo-1611162617474-5b21e879e113?w=600",
                "https://images.unsplash.com/photo-1556742049-0cfed4f6a45d?w=600"
            ]
        else:
            hero_image = "https://images.unsplash.com/photo-1497366216548-37526070297c?w=1920"
            gallery_images = [
                "https://images.unsplash.com/photo-1497366811353-6870744d04b2?w=800",
                "https://images.unsplash.com/photo-1497215728101-856f4ea42174?w=800",
                "https://images.unsplash.com/photo-1542744173-8e7e53415bb0?w=800",
                "https://images.unsplash.com/photo-1521737711867-e3b97375f902?w=800"
            ]
            service_images = [
                "https://images.unsplash.com/photo-1460925895917-afdab827c52f?w=600",
                "https://images.unsplash.com/photo-1611162617474-5b21e879e113?w=600",
                "https://images.unsplash.com/photo-1556742049-0cfed4f6a45d?w=600"
            ]

        style_colors = {
            'modern': {'primary': '#E31E24', 'accent': '#FFD700'},
            'minimal': {'primary': '#2563EB', 'accent': '#10B981'},
            'bold': {'primary': '#7C3AED', 'accent': '#F59E0B'}
        }
        colors = style_colors.get(style, {'primary': '#E31E24', 'accent': '#FFD700'})

        prompt = f"""Create a stunning, professional website for:

## BUSINESS INFORMATION
- **Name:** {request.business_name}
- **Type:** {request.business_type or 'Restaurant & Hospitality'}
- **Description:** {request.description}

## DESIGN SPECIFICATIONS

### COLOR SCHEME
- Primary Color: {colors['primary']}
- Accent Color: {colors['accent']}
- Dark Background: #333333
- Light Background: #FFFFFF

### IMAGES TO USE
- Hero Background: {hero_image}
- Service Grid Images: {', '.join(service_images)}
- Gallery/Portfolio Images: {', '.join(gallery_images)}

### REQUIRED SECTIONS WITH ZONES

<!-- ZONE 1: Hero Section -->
- Full-screen hero with "{request.business_name}" as main heading
- Tagline based on: "{request.description[:100]}"
- "View Our Services" CTA button

<!-- ZONE 2-4: Services Grid -->
3-column grid showcasing services:
- Column 1: Creative Services (Website, Design, Branding)
- Column 2: Marketing (Social Media, Campaigns, Content)
- Column 3: Operations (Online Ordering, Management, Support)

<!-- ZONE 5-8: Portfolio Gallery -->
2x2 mosaic grid with hover effects showing:
- Interior shots
- Signature dishes/products
- Branding materials
- Customer experience

<!-- Contact Section -->
- Professional contact form
- Business address, phone, email
- Operating hours if applicable

<!-- Footer -->
- Multi-column layout
- Social media icons (Facebook, Instagram, Twitter SVGs)
- Copyright: "© 2024 {request.business_name}. All rights reserved."

### TECHNICAL MUST-HAVES
1. Tailwind CSS via CDN: <script src="https://cdn.tailwindcss.com"></script>
2. Google Fonts Poppins
3. Smooth scroll behavior
4. Mobile-responsive (single column on mobile)
5. Hover animations on all cards and buttons
6. Dark overlay on hero image for text readability"""

        if request.include_whatsapp and request.whatsapp_number:
            whatsapp_num = request.whatsapp_number.replace('+', '').replace(' ', '').replace('-', '')
            prompt += f"""

### WHATSAPP INTEGRATION
Add a floating WhatsApp button in the bottom-right corner:
- Green background (#25D366)
- WhatsApp icon (SVG)
- Links to: https://wa.me/{whatsapp_num}
- Pulse animation to draw attention
- Fixed position, always visible"""

        prompt += "\n\nGenerate the COMPLETE HTML file now. Output ONLY the HTML code."

        return prompt
    
    def _parse_ai_response(
        self,
        content: str,
        request: WebsiteGenerationRequest,
        style: Optional[str] = None
    ) -> AIGenerationResponse:
        """Parse AI response"""
        
        html_content = content.strip()
        if html_content.startswith("```html"):
            html_content = html_content[7:]
        if html_content.startswith("```"):
            html_content = html_content[3:]
        if html_content.endswith("```"):
            html_content = html_content[:-3]
        html_content = html_content.strip()
        
        return AIGenerationResponse(
            html_content=html_content,
            css_content=None,
            js_content=None,
            meta_title=request.business_name,
            meta_description=f"{request.business_name} - {request.description[:150]}",
            sections=["Hero", "About", "Services", "Contact"],
            integrations_included=["Contact Form", "WhatsApp", "Social Sharing"]
        )

    async def test_api_connectivity(self) -> Dict[str, any]:
        """Test API connectivity for debugging"""
        results = {
            "qwen": {"available": False, "status": "not_configured"},
            "deepseek": {"available": False, "status": "not_configured"}
        }

        # Test Qwen
        if self.qwen_client:
            try:
                logger.info("🧪 Testing Qwen API connectivity...")
                response = await self.qwen_client.chat.completions.create(
                    model=settings.QWEN_MODEL,
                    messages=[{"role": "user", "content": "test"}],
                    max_tokens=10
                )
                results["qwen"] = {
                    "available": True,
                    "status": "connected",
                    "model": settings.QWEN_MODEL,
                    "response": response.choices[0].message.content[:50] if response.choices else "no response"
                }
                logger.info("✅ Qwen API test successful!")
            except Exception as e:
                error_msg = str(e)
                results["qwen"] = {
                    "available": False,
                    "status": "error",
                    "error_type": type(e).__name__,
                    "error_message": error_msg[:200],
                    "model": settings.QWEN_MODEL
                }
                logger.error(f"❌ Qwen API test failed: {error_msg}")

        # Test DeepSeek
        if self.deepseek_client:
            try:
                logger.info("🧪 Testing DeepSeek API connectivity...")
                response = await self.deepseek_client.chat.completions.create(
                    model=settings.DEEPSEEK_MODEL,
                    messages=[{"role": "user", "content": "test"}],
                    max_tokens=10
                )
                results["deepseek"] = {
                    "available": True,
                    "status": "connected",
                    "model": settings.DEEPSEEK_MODEL,
                    "response": response.choices[0].message.content[:50] if response.choices else "no response"
                }
                logger.info("✅ DeepSeek API test successful!")
            except Exception as e:
                error_msg = str(e)
                results["deepseek"] = {
                    "available": False,
                    "status": "error",
                    "error_type": type(e).__name__,
                    "error_message": error_msg[:200],
                    "model": settings.DEEPSEEK_MODEL
                }
                logger.error(f"❌ DeepSeek API test failed: {error_msg}")

        return results

# Create singleton instance
ai_service = AIService()