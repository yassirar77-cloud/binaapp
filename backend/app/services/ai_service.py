"""
AI Service - Qwen & DeepSeek Integration
Handles website generation using Qwen Max 3 (primary) and DeepSeek V3 (fallback)
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
        # Initialize Qwen client (primary)
        if settings.QWEN_API_KEY:
            self.qwen_client = AsyncOpenAI(
                api_key=settings.QWEN_API_KEY,
                base_url="https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
            )
            logger.info("✅ Qwen Max 3 AI client initialized (PRIMARY)")
        else:
            self.qwen_client = None
            logger.warning("⚠️ Qwen API key not found")
        
        # Initialize DeepSeek client (fallback)
        self.deepseek_client = AsyncOpenAI(
            api_key=settings.DEEPSEEK_API_KEY,
            base_url=settings.DEEPSEEK_API_URL
        )
        logger.info("✅ DeepSeek AI client initialized (FALLBACK)")
    
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
                logger.info(f"🎨 Generating website with Qwen Max 3 for {request.business_name} (style: {style or 'default'})")
                return await self._generate_with_qwen(request, style)
            except Exception as e:
                logger.error(f"❌ Qwen generation failed: {e}")
                logger.info("🔄 Falling back to DeepSeek...")
        
        # Fallback to DeepSeek
        try:
            logger.info(f"⚡ Generating website with DeepSeek for {request.business_name} (style: {style or 'default'})")
            return await self._generate_with_deepseek(request, style)
        except Exception as e:
            logger.error(f"❌ DeepSeek generation also failed: {e}")
            raise
    
    async def _generate_with_qwen(
        self,
        request: WebsiteGenerationRequest,
        style: Optional[str] = None
    ) -> AIGenerationResponse:
        """Generate website using Qwen Max 3"""
        
        prompt = self._build_generation_prompt(request, style)
        
        response = await self.qwen_client.chat.completions.create(
            model="qwen-max-latest",
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
            temperature=0.8,
            max_tokens=8000,
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
            max_tokens=8000,
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
        
        return """You are an expert web developer creating beautiful websites for Malaysian businesses.

Generate a complete, single-file HTML website with:
- Semantic HTML5
- Inline CSS (modern, responsive)
- JavaScript for interactivity
- Mobile-first design
- Malaysian context (RM currency, Bahasa Malaysia support)

Output ONLY the HTML code, no explanations."""
    
    def _build_generation_prompt(self, request: WebsiteGenerationRequest, style: Optional[str] = None) -> str:
        """Build generation prompt"""
        
        style_label = f" in {style.upper()} style" if style else ""
        
        prompt = f"""Generate a professional website{style_label} for:

Business Name: {request.business_name}
Business Type: {request.business_type or 'General Business'}
Description: {request.description}

Include:
- Navigation header
- Hero section
- About section
- Services/Products
- Contact form
- Footer

"""
        
        if request.include_whatsapp and request.whatsapp_number:
            prompt += f"- WhatsApp button ({request.whatsapp_number})\n"
        
        if request.include_maps and request.location_address:
            prompt += f"- Google Maps ({request.location_address})\n"
        
        prompt += "\nGenerate complete HTML now:"
        
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

# Create singleton instance
ai_service = AIService()