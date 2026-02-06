"""
Image Moderation Service using Qwen-VL API
Created: 2026-02-06
Purpose: Check uploaded images for inappropriate content

This is a NEW service - does not modify any existing code.
To use: Import and call from upload endpoints.
"""

import httpx
import base64
import os
import json
from loguru import logger

QWEN_API_KEY = os.getenv("QWEN_API_KEY")
QWEN_API_URL = os.getenv("QWEN_API_URL", "https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation")
QWEN_MODEL = os.getenv("QWEN_MODEL", "qwen-vl-max")


async def check_image_safety(image_data: bytes = None, image_url: str = None) -> dict:
    """
    Check if image contains inappropriate content using Qwen-VL

    Args:
        image_data: Raw image bytes
        image_url: URL of image to check

    Returns:
        {
            "is_safe": True/False,
            "reason": "explanation if unsafe",
            "confidence": 0-100,
            "detected_categories": []
        }
    """
    try:
        if not QWEN_API_KEY:
            logger.warning("[MODERATION] QWEN_API_KEY not set, skipping moderation")
            return {"is_safe": True, "reason": "Moderation skipped - no API key", "confidence": 0}

        # Prepare image content
        if image_data:
            image_base64 = base64.b64encode(image_data).decode('utf-8')
            image_content = f"data:image/jpeg;base64,{image_base64}"
        elif image_url:
            image_content = image_url
        else:
            return {"is_safe": False, "reason": "No image provided", "confidence": 100}

        # Moderation prompt
        moderation_prompt = """Analyze this image for content moderation. Check if it contains ANY of these:

1. Adult/Sexual content (nudity, pornography, sexually suggestive)
2. Drugs (illegal drugs, drug paraphernalia, drug use)
3. Violence (gore, blood, weapons being used violently)
4. Weapons (guns, knives, explosives displayed threateningly)
5. Hate symbols (racist, extremist symbols)
6. Graphic disturbing content

Respond ONLY with this exact JSON format, nothing else:
{"is_safe": true, "reason": "brief explanation", "confidence": 85, "detected_categories": []}

If the image is a normal food photo, menu item, restaurant, or safe content, respond with is_safe: true.
If ANY inappropriate content is detected, respond with is_safe: false and list detected_categories."""

        headers = {
            "Authorization": f"Bearer {QWEN_API_KEY}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": QWEN_MODEL,
            "input": {
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"image": image_content},
                            {"text": moderation_prompt}
                        ]
                    }
                ]
            },
            "parameters": {
                "max_tokens": 300
            }
        }

        logger.info("[MODERATION] Checking image safety...")

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                QWEN_API_URL,
                headers=headers,
                json=payload
            )

            if response.status_code != 200:
                logger.error(f"[MODERATION] Qwen API error: {response.status_code}")
                return {"is_safe": True, "reason": "API error, allowing image", "confidence": 0}

            result = response.json()

            # Parse Qwen response - handle different response formats
            try:
                output_text = ""

                # Try different response structures
                if "output" in result:
                    output = result["output"]
                    if "choices" in output:
                        output_text = output["choices"][0].get("message", {}).get("content", "")
                    elif "text" in output:
                        output_text = output["text"]

                # Handle if content is a list
                if isinstance(output_text, list):
                    for item in output_text:
                        if isinstance(item, dict) and "text" in item:
                            output_text = item["text"]
                            break

                logger.info(f"[MODERATION] Raw response: {output_text[:200]}")

                # Extract JSON from response
                json_match = output_text
                if "{" in output_text and "}" in output_text:
                    start = output_text.find("{")
                    end = output_text.rfind("}") + 1
                    json_match = output_text[start:end]

                moderation_result = json.loads(json_match)

                logger.info(f"[MODERATION] Result: is_safe={moderation_result.get('is_safe')}")

                return {
                    "is_safe": moderation_result.get("is_safe", True),
                    "reason": moderation_result.get("reason", ""),
                    "confidence": moderation_result.get("confidence", 0),
                    "detected_categories": moderation_result.get("detected_categories", [])
                }

            except json.JSONDecodeError as e:
                logger.warning(f"[MODERATION] JSON parse error: {e}")
                # Keyword-based fallback
                output_lower = str(output_text).lower()
                if any(word in output_lower for word in ["unsafe", "inappropriate", "adult", "drug", "violence", "nude", "sexual"]):
                    return {"is_safe": False, "reason": "Content flagged as potentially inappropriate", "confidence": 60}
                return {"is_safe": True, "reason": "Content appears safe", "confidence": 60}

    except httpx.TimeoutException:
        logger.error("[MODERATION] Qwen API timeout")
        return {"is_safe": True, "reason": "Timeout, allowing image", "confidence": 0}
    except Exception as e:
        logger.error(f"[MODERATION] Error: {str(e)}")
        return {"is_safe": True, "reason": f"Error: {str(e)}", "confidence": 0}


async def moderate_uploaded_image(file_content: bytes, filename: str = "") -> dict:
    """
    Wrapper function for moderating uploaded files

    Args:
        file_content: Raw bytes of uploaded file
        filename: Original filename (for logging)

    Returns:
        {
            "allowed": True/False,
            "message": "Success or rejection message in Malay"
        }
    """
    logger.info(f"[MODERATION] Moderating file: {filename}")

    result = await check_image_safety(image_data=file_content)

    if result["is_safe"]:
        logger.info(f"[MODERATION] Image allowed: {filename}")
        return {
            "allowed": True,
            "message": "Gambar diluluskan"
        }
    else:
        # Rejection messages in Malay
        category_messages = {
            "adult": "Kandungan dewasa tidak dibenarkan",
            "sexual": "Kandungan seksual tidak dibenarkan",
            "drugs": "Kandungan dadah tidak dibenarkan",
            "violence": "Kandungan keganasan tidak dibenarkan",
            "weapons": "Kandungan senjata tidak dibenarkan",
            "hate": "Simbol kebencian tidak dibenarkan"
        }

        detected = result.get("detected_categories", [])
        if detected:
            reasons = [category_messages.get(cat.lower(), cat) for cat in detected]
            reason = ", ".join(reasons)
        else:
            reason = result.get("reason", "Kandungan tidak sesuai")

        logger.warning(f"[MODERATION] Image rejected: {filename} - {reason}")

        return {
            "allowed": False,
            "message": f"Gambar ditolak: {reason}"
        }
