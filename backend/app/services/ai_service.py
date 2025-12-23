"""
AI Service - Qwen & DeepSeek Integration
Handles website generation using task-based AI routing:
- DeepSeek: Backend logic, Bug fixing, API design, Code generation
- Qwen: UI ideas, Text & copy, Chatbot, Code explanation
"""
from openai import AsyncOpenAI
from typing import Dict, Optional
from loguru import logger
from enum import Enum
import json
import httpx
from app.core.config import settings
from app.models.schemas import WebsiteGenerationRequest, AIGenerationResponse
from app.services.design_system import design_system


class AITask(Enum):
    """Task-based AI routing - assigns the best AI for each task type"""
    # DeepSeek excels at: Backend logic, Code generation, API design, Bug fixing
    BACKEND_LOGIC = "deepseek"
    BUG_FIXING = "deepseek"
    API_DESIGN = "deepseek"
    CODE_GENERATION = "deepseek"
    CODE_STRUCTURE = "deepseek"

    # Qwen excels at: UI design, Content writing, Chatbot, Explanations
    UI_IDEAS = "qwen"
    TEXT_COPY = "qwen"
    CHATBOT = "qwen"
    CODE_EXPLANATION = "qwen"
    CONTENT_WRITING = "qwen"

    # Website generation - use both strategically
    WEBSITE_GENERATION = "both"

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
    
    def _detect_business_type(self, description: str) -> dict:
        """Detect business type and return relevant configuration"""
        import random

        desc_lower = description.lower()

        # Food/Restaurant
        if any(w in desc_lower for w in ['makan', 'restoran', 'cafe', 'kedai makan', 'nasi', 'makanan', 'food', 'restaurant', 'kafe']):
            return {
                "type": "restaurant",
                "components": ["FoodMenuGrid", "WhatsAppOrdering", "GoogleMaps"],
                "image_style": "food photography, dishes, restaurant interior",
                "color_scheme": random.choice(["red-orange warm", "green natural", "brown cozy"]),
                "unsplash_queries": ["malaysian-food", "nasi-lemak", "restaurant-interior", "food-plating"]
            }

        # Pet Shop / Animals
        if any(w in desc_lower for w in ['kucing', 'cat', 'pet', 'haiwan', 'anjing', 'dog', 'binatang']):
            return {
                "type": "pet_shop",
                "components": ["ProductGallery", "ServiceList", "ContactForm"],
                "image_style": "cute cats, pet shop, pet supplies, animals",
                "color_scheme": random.choice(["orange playful", "blue calm", "purple cute"]),
                "unsplash_queries": ["cat", "cute-cat", "pet-shop", "kitten", "dog"]
            }

        # Salon / Beauty
        if any(w in desc_lower for w in ['salon', 'rambut', 'hair', 'beauty', 'spa', 'kecantikan', 'gunting']):
            return {
                "type": "salon",
                "components": ["ServiceList", "BookingForm", "Gallery"],
                "image_style": "salon interior, hair styling, beauty",
                "color_scheme": random.choice(["pink elegant", "gold luxury", "white minimal"]),
                "unsplash_queries": ["hair-salon", "beauty-salon", "hairstyle", "spa"]
            }

        # Photography
        if any(w in desc_lower for w in ['photo', 'gambar', 'wedding', 'photographer', 'fotografi', 'kamera']):
            return {
                "type": "portfolio",
                "components": ["ImageGallery", "Portfolio", "ContactForm"],
                "image_style": "photography, camera, studio",
                "color_scheme": random.choice(["black white minimal", "dark moody", "clean white"]),
                "unsplash_queries": ["photography", "camera", "wedding-photo", "portrait"]
            }

        # Fitness / Gym
        if any(w in desc_lower for w in ['gym', 'fitness', 'sukan', 'senaman', 'workout']):
            return {
                "type": "fitness",
                "components": ["ClassSchedule", "MembershipPricing", "ContactForm"],
                "image_style": "fitness, gym equipment, workout",
                "color_scheme": random.choice(["red energetic", "black bold", "blue strong"]),
                "unsplash_queries": ["gym", "fitness", "workout", "exercise"]
            }

        # Default - General Business
        return {
            "type": "general",
            "components": ["Hero", "Services", "About", "Contact"],
            "image_style": "professional business",
            "color_scheme": random.choice(["blue professional", "green fresh", "purple modern"]),
            "unsplash_queries": ["business", "office", "professional", "workspace"]
        }

    def _get_design_vibe(self) -> dict:
        """Get random design vibe for variety"""
        import random

        vibes = [
            {
                "name": "Modern",
                "font": "font-sans",
                "rounded": "rounded-xl",
                "shadow": "shadow-lg",
                "primary": "bg-gradient-to-r from-blue-600 to-purple-600",
                "style": "Clean gradients, smooth animations, card-based layout"
            },
            {
                "name": "Minimal",
                "font": "font-serif",
                "rounded": "rounded-none",
                "shadow": "border-b-2",
                "primary": "bg-gray-900",
                "style": "Lots of whitespace, typography-focused, elegant"
            },
            {
                "name": "Bold",
                "font": "font-sans font-bold",
                "rounded": "rounded-sm",
                "shadow": "border-4",
                "primary": "bg-yellow-400",
                "style": "Strong colors, thick borders, impactful headlines"
            },
            {
                "name": "Gradient",
                "font": "font-sans",
                "rounded": "rounded-2xl",
                "shadow": "shadow-2xl",
                "primary": "bg-gradient-to-r from-purple-600 to-pink-500",
                "style": "Colorful gradients, glass morphism, trendy"
            }
        ]
        return random.choice(vibes)

    def _get_system_prompt(self, style: Optional[str] = None) -> str:
        """Get enhanced system prompt for professional website generation"""

        return """You are an expert web designer creating stunning, professional websites for businesses.

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
        """Build intelligent generation prompt with business detection and smart image handling"""

        # Detect business type and get configuration
        business_config = self._detect_business_type(request.description)
        logger.info(f"🔍 Detected business type: {business_config['type']}")
        logger.info(f"🎨 Color scheme: {business_config['color_scheme']}")

        # Get design vibe for variety
        vibe = self._get_design_vibe()
        logger.info(f"✨ Design vibe: {vibe['name']}")

        # PRIORITIZE USER-UPLOADED IMAGES
        has_uploaded_images = request.uploaded_images and len(request.uploaded_images) > 0

        if has_uploaded_images:
            # User uploaded their own images - use them!
            logger.info(f"🖼️  Using {len(request.uploaded_images)} user-uploaded images")
            hero_image = request.uploaded_images[0]  # First image as hero
            gallery_images = request.uploaded_images[1:5] if len(request.uploaded_images) > 1 else request.uploaded_images * 4  # Repeat if needed
            service_images = request.uploaded_images[:3] if len(request.uploaded_images) >= 3 else request.uploaded_images * 3

            image_section = f"""### 🖼️ USER-UPLOADED IMAGES (MUST USE THESE!)

⚠️ CRITICAL: The user uploaded {len(request.uploaded_images)} REAL PHOTOS of their business.
YOU MUST USE THESE EXACT URLs - DO NOT use Unsplash or placeholder images!

Hero Image (Main Banner): {hero_image}

All uploaded images:
{chr(10).join([f"  {i+1}. {img}" for i, img in enumerate(request.uploaded_images)])}

Use these images in:
- Hero section background
- Gallery/Portfolio section
- Service/Product showcases
- About section

IMPORTANT: These are the user's actual business photos - showcase them prominently!"""
        else:
            # No uploaded images - use relevant Unsplash based on business type
            logger.info(f"📷 No user images - using Unsplash for {business_config['type']}")

            # Generate relevant Unsplash URLs based on business type
            unsplash_queries = business_config['unsplash_queries']

            hero_image = f"https://images.unsplash.com/photo-1551963831-b3b1ca40c98e?w=1920&q=80"  # Default
            gallery_images = [
                f"https://images.unsplash.com/photo-{1551963831-i}?w=800&q=80" for i in range(1, 5)
            ]
            service_images = [
                f"https://images.unsplash.com/photo-{1551963831-i}?w=600&q=80" for i in range(1, 4)
            ]

            image_section = f"""### 📷 IMAGES TO USE (Relevant to {business_config['type']})

IMPORTANT: Use images related to "{business_config['image_style']}"

Search Unsplash for: {', '.join(unsplash_queries)}

Hero Background: Use a high-quality {business_config['image_style']} image
Gallery Images: 4-6 images showcasing {business_config['image_style']}
Service Images: 3-4 images relevant to the business type

⚠️ CRITICAL: Images MUST match the business type ({business_config['type']})!
- For cat shop → Use cat/pet images, NOT office/food images
- For restaurant → Use food/dining images, NOT corporate images
- For salon → Use salon/beauty images, NOT tech/office images"""

        # Build color scheme based on business type
        style_colors = {
            'modern': {'primary': '#3B82F6', 'accent': '#8B5CF6'},
            'minimal': {'primary': '#1F2937', 'accent': '#6B7280'},
            'bold': {'primary': '#EF4444', 'accent': '#F59E0B'}
        }
        colors = style_colors.get(style, {'primary': '#3B82F6', 'accent': '#8B5CF6'})

        prompt = f"""Create a stunning, UNIQUE, professional website for:

## BUSINESS INFORMATION
- **Name:** {request.business_name}
- **Type:** {business_config['type'].upper()} (Detected: {request.business_type or 'Auto-detected'})
- **Description:** {request.description}

## DESIGN VIBE: {vibe['name'].upper()}
- Style: {vibe['style']}
- Font: {vibe['font']}
- Border radius: {vibe['rounded']}
- Shadow style: {vibe['shadow']}
- Primary styling: {vibe['primary']}

## COLOR SCHEME ({business_config['color_scheme']})
- Primary Color: {colors['primary']}
- Accent Color: {colors['accent']}
- Use colors that match the business mood and type

{image_section}

## BUSINESS-SPECIFIC COMPONENTS
Recommended sections for {business_config['type']}:
{chr(10).join([f"- {comp}" for comp in business_config['components']])}

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
2. Google Fonts (use appropriate font for the design vibe)
3. Smooth scroll behavior
4. MOBILE-RESPONSIVE (CRITICAL - must work perfectly on phones!)
5. Hover animations on all interactive elements
6. Use the {vibe['name']} design vibe throughout
7. Apply {business_config['color_scheme']} color scheme

### CRITICAL REQUIREMENTS FOR UNIQUENESS
⚠️ Each website MUST be DIFFERENT and UNIQUE!
- Use the {vibe['name']} design vibe specified above
- Apply {vibe['rounded']} for border radius
- Use {vibe['shadow']} for shadows
- Colors must match {business_config['color_scheme']}
- Layout should reflect the {vibe['style']}
- Make it look professional and match the business type ({business_config['type']})

🎨 DESIGN VARIETY RULES:
- Different businesses should have DIFFERENT designs
- Color schemes should match the business type and mood
- Layouts should vary based on the design vibe
- Images MUST be relevant to the specific business type"""

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

    def select_ai_for_task(self, task: AITask) -> str:
        """
        Select the best AI for a given task type

        Args:
            task: The task type from AITask enum

        Returns:
            'qwen', 'deepseek', or 'both'
        """
        return task.value

    async def generate_with_task_routing(
        self,
        prompt: str,
        task: AITask,
        max_tokens: int = 4000
    ) -> Optional[str]:
        """
        Generate content using task-based AI routing

        Args:
            prompt: The generation prompt
            task: Task type to determine which AI to use
            max_tokens: Maximum tokens to generate

        Returns:
            Generated content string
        """
        ai_choice = self.select_ai_for_task(task)

        logger.info(f"🎯 Task-based routing: {task.name} → {ai_choice.upper()}")

        if ai_choice == "deepseek":
            # Try DeepSeek first (best for code/logic)
            if self.deepseek_client:
                try:
                    logger.info("🤖 Using DeepSeek (Code/Logic specialist)")
                    response = await self.deepseek_client.chat.completions.create(
                        model=settings.DEEPSEEK_MODEL,
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0.7,
                        max_tokens=max_tokens
                    )
                    result = response.choices[0].message.content
                    logger.info(f"✓ DeepSeek returned {len(result)} chars")
                    return result
                except Exception as e:
                    logger.error(f"DeepSeek failed: {e}")

            # Fallback to Qwen
            if self.qwen_client:
                logger.info("⚠️ Falling back to Qwen")
                try:
                    response = await self.qwen_client.chat.completions.create(
                        model=settings.QWEN_MODEL,
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0.7,
                        max_tokens=max_tokens
                    )
                    return response.choices[0].message.content
                except Exception as e:
                    logger.error(f"Qwen fallback failed: {e}")

        elif ai_choice == "qwen":
            # Try Qwen first (best for UI/content)
            if self.qwen_client:
                try:
                    logger.info("🤖 Using Qwen (UI/Content specialist)")
                    response = await self.qwen_client.chat.completions.create(
                        model=settings.QWEN_MODEL,
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0.7,
                        max_tokens=max_tokens
                    )
                    result = response.choices[0].message.content
                    logger.info(f"✓ Qwen returned {len(result)} chars")
                    return result
                except Exception as e:
                    logger.error(f"Qwen failed: {e}")

            # Fallback to DeepSeek
            if self.deepseek_client:
                logger.info("⚠️ Falling back to DeepSeek")
                try:
                    response = await self.deepseek_client.chat.completions.create(
                        model=settings.DEEPSEEK_MODEL,
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0.7,
                        max_tokens=max_tokens
                    )
                    return response.choices[0].message.content
                except Exception as e:
                    logger.error(f"DeepSeek fallback failed: {e}")

        elif ai_choice == "both":
            # Use both AIs strategically
            logger.info("🚀 Using both AIs strategically")
            results = await self.generate_website_dual(
                WebsiteGenerationRequest(
                    description=prompt,
                    business_name="Generated",
                    business_type="website",
                    subdomain="preview"
                )
            )
            # Return DeepSeek result if available (better for code structure)
            return results.get("deepseek") or results.get("qwen")

        return None

    async def generate_website_strategic(
        self,
        request: WebsiteGenerationRequest,
        style: Optional[str] = None
    ) -> AIGenerationResponse:
        """
        Strategic website generation using task-based routing:
        1. DeepSeek generates HTML structure and code (CODE_STRUCTURE task)
        2. Qwen enhances content and copy (CONTENT_WRITING task)

        This combines the strengths of both AIs for optimal results.
        """
        logger.info(f"🎯 Strategic generation for {request.business_name}")
        logger.info("Step 1: DeepSeek generating code structure...")

        # Step 1: Use DeepSeek for HTML structure and code
        structure_prompt = f"""Generate a complete HTML website structure with Tailwind CSS for:

Business: {request.business_name}
Type: {request.business_type or 'Business'}
Description: {request.description}
Style: {style or 'modern'}

Focus on:
- Clean, well-structured HTML5 code
- Proper semantic markup
- Responsive Tailwind CSS classes
- Modern JavaScript if needed
- Professional layout and structure

Use placeholder text like [BUSINESS_NAME], [TAGLINE], [ABOUT_TEXT], etc. for content that will be enhanced later.

Generate ONLY the HTML code."""

        structure_html = await self.generate_with_task_routing(
            structure_prompt,
            AITask.CODE_STRUCTURE,
            max_tokens=4000
        )

        if not structure_html:
            # Fallback to standard generation
            logger.warning("Strategic generation failed, using standard method")
            return await self.generate_website(request, style)

        # Extract HTML
        structure_html = self._extract_html(structure_html)

        logger.info("Step 2: Qwen enhancing content and copy...")

        # Step 2: Use Qwen to enhance content and copy
        content_prompt = f"""Improve this website HTML by replacing placeholder text with compelling, professional content.

Business: {request.business_name}
Type: {request.business_type or 'Business'}
Description: {request.description}

HTML to improve:
{structure_html[:6000]}

Replace all placeholder text with:
- Engaging, professional copy
- Appropriate language (Bahasa Malaysia for Malaysian businesses, English otherwise)
- Compelling calls-to-action
- SEO-friendly content

Return the complete improved HTML with enhanced content."""

        final_html = await self.generate_with_task_routing(
            content_prompt,
            AITask.CONTENT_WRITING,
            max_tokens=4000
        )

        if not final_html:
            logger.warning("Content enhancement failed, using structure only")
            final_html = structure_html

        # Extract and parse
        final_html = self._extract_html(final_html)

        logger.info("✅ Strategic generation complete")

        return AIGenerationResponse(
            html_content=final_html,
            css_content=None,
            js_content=None,
            meta_title=request.business_name,
            meta_description=f"{request.business_name} - {request.description[:150]}",
            sections=["Hero", "About", "Services", "Contact"],
            integrations_included=["Contact Form", "WhatsApp", "Social Sharing"]
        )

    def _extract_html(self, text: str) -> str:
        """Extract HTML from text that might contain markdown code blocks"""
        if not text:
            return text
        if "```html" in text:
            text = text.split("```html")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]
        return text.strip()

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