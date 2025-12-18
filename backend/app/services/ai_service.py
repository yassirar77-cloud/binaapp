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
    
    def _get_system_prompt(self, style: Optional[str] = None) -> str:
        """Get enhanced system prompt"""

        return """You are a web developer. Generate a single-file HTML website with inline CSS. Keep it simple and clean. Output ONLY the HTML code, no explanations."""
    
    def _build_generation_prompt(self, request: WebsiteGenerationRequest, style: Optional[str] = None) -> str:
        """Build generation prompt - simplified for faster response"""

        style_label = f" ({style} style)" if style else ""

        prompt = f"""Create a simple website{style_label}:
- Business: {request.business_name}
- Type: {request.business_type or 'Business'}
- About: {request.description[:200]}

Include: header, hero, about, services, contact form, footer."""

        if request.include_whatsapp and request.whatsapp_number:
            prompt += f" WhatsApp: {request.whatsapp_number}."

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