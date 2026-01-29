"""
Stability AI Service - Image Generation
Generates images using Stability AI API for menu items.
"""
import os
import base64
import logging
import httpx
from typing import Optional

logger = logging.getLogger(__name__)

# Import Malaysian prompts for re-export
from app.data.malaysian_prompts import (
    MALAYSIAN_FOOD_PROMPTS as MALAYSIAN_PROMPTS,
    get_smart_stability_prompt as get_malaysian_prompt,
)

# Get API key from environment
STABILITY_API_KEY = os.getenv("STABILITY_API_KEY")
STABILITY_API_URL = "https://api.stability.ai/v1/generation/stable-diffusion-xl-1024-v1-0/text-to-image"

# Cloudinary config for uploading generated images
CLOUDINARY_CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME")
CLOUDINARY_API_KEY = os.getenv("CLOUDINARY_API_KEY")
CLOUDINARY_API_SECRET = os.getenv("CLOUDINARY_API_SECRET")


def generate_stability_image(prompt: str, width: int = 512, height: int = 512) -> Optional[str]:
    """
    Generate an image using Stability AI's SDXL model.
    
    Args:
        prompt: Text prompt describing the image
        width: Image width (default 512)
        height: Image height (default 512)
        
    Returns:
        URL of the generated image, or None if generation fails
    """
    if not STABILITY_API_KEY:
        logger.warning("⚠️ STABILITY_API_KEY not set, cannot generate image")
        return None
    
    try:
        logger.info(f"🎨 Generating image: {prompt[:50]}...")
        
        # Enhanced prompt for better quality
        enhanced_prompt = f"{prompt}, professional photography, high quality, realistic, 4k, sharp focus"
        negative_prompt = "blurry, bad quality, cartoon, illustration, anime, drawing, sketch, low resolution"
        
        response = httpx.post(
            STABILITY_API_URL,
            headers={
                "Authorization": f"Bearer {STABILITY_API_KEY}",
                "Content-Type": "application/json",
                "Accept": "application/json"
            },
            json={
                "text_prompts": [
                    {"text": enhanced_prompt, "weight": 1.0},
                    {"text": negative_prompt, "weight": -1.0}
                ],
                "cfg_scale": 7,
                "width": width,
                "height": height,
                "steps": 30,
                "samples": 1,
                "style_preset": "photographic"
            },
            timeout=60.0
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get('artifacts') and len(data['artifacts']) > 0:
                image_base64 = data['artifacts'][0]['base64']
                
                # Upload to Cloudinary if configured
                if CLOUDINARY_CLOUD_NAME and CLOUDINARY_API_KEY:
                    image_url = upload_to_cloudinary(image_base64)
                    if image_url:
                        logger.info(f"🎨 ✅ Image generated and uploaded: {image_url[:60]}...")
                        return image_url
                
                # Return as data URL if no Cloudinary
                data_url = f"data:image/png;base64,{image_base64}"
                logger.info("🎨 ✅ Image generated as data URL")
                return data_url
            else:
                logger.error("🎨 ❌ No artifacts in Stability AI response")
                return None
        elif response.status_code == 402:
            logger.warning("🎨 ⚠️ Stability AI credits exhausted")
            return None
        elif response.status_code == 429:
            logger.warning("🎨 ⚠️ Stability AI rate limit exceeded")
            return None
        else:
            logger.error(f"🎨 ❌ Stability AI error: {response.status_code} - {response.text[:200]}")
            return None
            
    except httpx.TimeoutException:
        logger.error("🎨 ❌ Stability AI request timed out")
        return None
    except Exception as e:
        logger.error(f"🎨 ❌ Stability AI exception: {e}")
        return None


def upload_to_cloudinary(image_base64: str) -> Optional[str]:
    """
    Upload base64 image to Cloudinary and return URL.
    
    Args:
        image_base64: Base64-encoded image data
        
    Returns:
        URL of the uploaded image, or None if upload fails
    """
    if not CLOUDINARY_CLOUD_NAME or not CLOUDINARY_API_KEY or not CLOUDINARY_API_SECRET:
        logger.warning("⚠️ Cloudinary not configured, cannot upload image")
        return None
    
    try:
        import cloudinary
        import cloudinary.uploader
        
        # Configure cloudinary
        cloudinary.config(
            cloud_name=CLOUDINARY_CLOUD_NAME,
            api_key=CLOUDINARY_API_KEY,
            api_secret=CLOUDINARY_API_SECRET
        )
        
        # Upload image
        data_uri = f"data:image/png;base64,{image_base64}"
        result = cloudinary.uploader.upload(
            data_uri,
            folder="binaapp-menu-items",
            resource_type="image"
        )
        
        if result and result.get('secure_url'):
            return result['secure_url']
        
        return None
        
    except ImportError:
        logger.warning("⚠️ Cloudinary package not installed")
        return None
    except Exception as e:
        logger.error(f"❌ Cloudinary upload failed: {e}")
        return None


async def generate_stability_image_async(prompt: str, width: int = 512, height: int = 512) -> Optional[str]:
    """
    Async version of generate_stability_image.
    """
    if not STABILITY_API_KEY:
        logger.warning("⚠️ STABILITY_API_KEY not set, cannot generate image")
        return None
    
    try:
        logger.info(f"🎨 Generating image (async): {prompt[:50]}...")
        
        # Enhanced prompt for better quality
        enhanced_prompt = f"{prompt}, professional photography, high quality, realistic, 4k, sharp focus"
        negative_prompt = "blurry, bad quality, cartoon, illustration, anime, drawing, sketch, low resolution"
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                STABILITY_API_URL,
                headers={
                    "Authorization": f"Bearer {STABILITY_API_KEY}",
                    "Content-Type": "application/json",
                    "Accept": "application/json"
                },
                json={
                    "text_prompts": [
                        {"text": enhanced_prompt, "weight": 1.0},
                        {"text": negative_prompt, "weight": -1.0}
                    ],
                    "cfg_scale": 7,
                    "width": width,
                    "height": height,
                    "steps": 30,
                    "samples": 1,
                    "style_preset": "photographic"
                }
            )
        
        if response.status_code == 200:
            data = response.json()
            if data.get('artifacts') and len(data['artifacts']) > 0:
                image_base64 = data['artifacts'][0]['base64']
                
                # Upload to Cloudinary if configured
                if CLOUDINARY_CLOUD_NAME and CLOUDINARY_API_KEY:
                    image_url = upload_to_cloudinary(image_base64)
                    if image_url:
                        logger.info(f"🎨 ✅ Image generated and uploaded: {image_url[:60]}...")
                        return image_url
                
                # Return as data URL if no Cloudinary
                data_url = f"data:image/png;base64,{image_base64}"
                logger.info("🎨 ✅ Image generated as data URL")
                return data_url
        
        logger.error(f"🎨 ❌ Stability AI error: {response.status_code}")
        return None
            
    except Exception as e:
        logger.error(f"🎨 ❌ Stability AI async exception: {e}")
        return None


def get_business_image_prompts(description: str) -> dict:
    """
    Get image prompts based on business description.
    Returns prompts for hero image and gallery images.
    """
    desc_lower = description.lower()
    
    # Photography
    if any(kw in desc_lower for kw in ['photographer', 'photography', 'jurugambar', 'fotografi', 'gambar']):
        return {
            "hero": "Professional photography studio with camera equipment, elegant lighting setup, modern interior",
            "gallery": [
                "Professional portrait photography session with studio lighting",
                "Wedding photography with beautiful decorations and romantic setting",
                "Product photography setup with white background",
                "Corporate headshot photography in office environment"
            ]
        }
    
    # Salon/Beauty
    if any(kw in desc_lower for kw in ['salon', 'spa', 'beauty', 'kecantikan', 'rambut', 'hair']):
        return {
            "hero": "Modern luxury hair salon interior with styling chairs and mirrors, elegant lighting",
            "gallery": [
                "Professional hairstylist cutting hair in salon",
                "Hair coloring treatment being applied",
                "Luxury spa treatment room with massage bed",
                "Nail salon manicure service in progress"
            ]
        }
    
    # Food/Restaurant
    if any(kw in desc_lower for kw in ['makanan', 'food', 'restaurant', 'restoran', 'cafe', 'nasi', 'mee']):
        return {
            "hero": "Modern Malaysian restaurant interior with warm lighting and elegant seating",
            "gallery": [
                "Delicious nasi lemak with fried chicken and sambal on banana leaf",
                "Malaysian fried noodles mee goreng with egg",
                "Chef cooking in restaurant kitchen",
                "Malaysian teh tarik being poured"
            ]
        }
    
    # Clothing/Fashion
    if any(kw in desc_lower for kw in ['pakaian', 'baju', 'fashion', 'boutique', 'butik', 'tudung', 'hijab']):
        return {
            "hero": "Modern fashion boutique interior with elegant clothing displays",
            "gallery": [
                "Beautiful baju kurung on mannequin display",
                "Colorful hijab collection arrangement",
                "Traditional kebaya with intricate embroidery",
                "Fashion accessories display with jewelry"
            ]
        }
    
    # Default
    return {
        "hero": f"Professional {description} business interior, modern and elegant",
        "gallery": [
            f"{description} products display",
            f"{description} service in action",
            f"Customer at {description} business",
            f"{description} workspace interior"
        ]
    }


async def generate_malaysian_image(
    item_name: str,
    business_type: str = "",
    aspect_ratio: str = "1:1"
) -> Optional[str]:
    """
    Generate an image for a Malaysian item using Stability AI.

    Args:
        item_name: Name of the item (e.g., "Nasi Lemak")
        business_type: Type of business (e.g., "restaurant")
        aspect_ratio: Image aspect ratio (e.g., "1:1", "16:9")

    Returns:
        Base64-encoded image data, or None if generation fails
    """
    if not STABILITY_API_KEY:
        logger.warning("⚠️ STABILITY_API_KEY not set, cannot generate image")
        return None

    try:
        # Get smart prompt for the item
        prompt = get_malaysian_prompt(item_name, business_type)
        logger.info(f"🎨 Generating Malaysian image: {item_name} -> {prompt[:60]}...")

        # Parse aspect ratio to get dimensions
        width, height = 1024, 1024  # Default square
        if aspect_ratio == "16:9":
            width, height = 1344, 768
        elif aspect_ratio == "9:16":
            width, height = 768, 1344
        elif aspect_ratio == "4:3":
            width, height = 1152, 896
        elif aspect_ratio == "3:4":
            width, height = 896, 1152

        # Enhanced prompt for better quality
        enhanced_prompt = f"{prompt}, professional photography, high quality, realistic, 4k, sharp focus"
        negative_prompt = "blurry, bad quality, cartoon, illustration, anime, drawing, sketch, low resolution"

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                STABILITY_API_URL,
                headers={
                    "Authorization": f"Bearer {STABILITY_API_KEY}",
                    "Content-Type": "application/json",
                    "Accept": "application/json"
                },
                json={
                    "text_prompts": [
                        {"text": enhanced_prompt, "weight": 1.0},
                        {"text": negative_prompt, "weight": -1.0}
                    ],
                    "cfg_scale": 7,
                    "width": width,
                    "height": height,
                    "steps": 30,
                    "samples": 1,
                    "style_preset": "photographic"
                }
            )

        if response.status_code == 200:
            data = response.json()
            if data.get('artifacts') and len(data['artifacts']) > 0:
                image_base64 = data['artifacts'][0]['base64']
                logger.info(f"🎨 ✅ Generated image for: {item_name}")
                return image_base64
            else:
                logger.error("🎨 ❌ No artifacts in Stability AI response")
                return None
        elif response.status_code == 402:
            logger.warning("🎨 ⚠️ Stability AI credits exhausted")
            return None
        elif response.status_code == 429:
            logger.warning("🎨 ⚠️ Stability AI rate limit exceeded")
            return None
        else:
            logger.error(f"🎨 ❌ Stability AI error: {response.status_code} - {response.text[:200]}")
            return None

    except httpx.TimeoutException:
        logger.error("🎨 ❌ Stability AI request timed out")
        return None
    except Exception as e:
        logger.error(f"🎨 ❌ Stability AI exception: {e}")
        return None


async def save_image_to_storage(
    image_base64: str,
    filename: str,
    supabase_url: str,
    supabase_key: str
) -> Optional[str]:
    """
    Save a base64-encoded image to Supabase storage.

    Args:
        image_base64: Base64-encoded image data
        filename: Desired filename for the image
        supabase_url: Supabase project URL
        supabase_key: Supabase API key

    Returns:
        Public URL of the saved image, or None if save fails
    """
    if not supabase_url or not supabase_key:
        logger.warning("⚠️ Supabase not configured, cannot save image")
        return None

    try:
        # Decode base64 to bytes
        image_bytes = base64.b64decode(image_base64)

        # Upload to Supabase Storage
        storage_url = f"{supabase_url}/storage/v1/object/ai-images/{filename}"

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                storage_url,
                headers={
                    "Authorization": f"Bearer {supabase_key}",
                    "Content-Type": "image/webp",
                    "x-upsert": "true"
                },
                content=image_bytes
            )

        if response.status_code in [200, 201]:
            # Return public URL
            public_url = f"{supabase_url}/storage/v1/object/public/ai-images/{filename}"
            logger.info(f"💾 ✅ Saved image to storage: {filename}")
            return public_url
        else:
            logger.error(f"💾 ❌ Storage upload failed: {response.status_code} - {response.text[:200]}")
            return None

    except Exception as e:
        logger.error(f"💾 ❌ Storage exception: {e}")
        return None
