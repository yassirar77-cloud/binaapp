"""
Customer Support Chatbot using Qwen AI
Provides instant customer support for BinaApp users
"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import List
import httpx
import os
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

# Qwen API configuration
QWEN_API_KEY = os.getenv("QWEN_API_KEY")

# Qwen API endpoints - try both formats
DASHSCOPE_URL = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"
OPENAI_COMPATIBLE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"

# BinaApp support knowledge base (condensed for better performance)
SYSTEM_PROMPT = """Anda adalah BinaBot, pembantu sokongan pelanggan BinaApp.

TENTANG BINAAPP:
- Platform pembina website AI untuk SME Malaysia
- Bina website dalam 60 saat
- Tiada perlu coding

PELAN HARGA:
- PERCUMA (RM0): 1 website, subdomain binaapp.my
- PRO (RM19/bulan): 5 websites, custom domain
- BUSINESS (RM39/bulan): Unlimited websites

TROUBLESHOOTING:
- Website stuck 20%: Refresh page, clear cache, cuba browser lain
- Domain tak connect: Tunggu 24-48 jam untuk DNS propagate
- Gambar tak upload: Max 5MB, format JPG/PNG sahaja

CARA RESPOND:
- Jawab dalam bahasa user (BM atau English)
- Ringkas dan jelas
- Mesra dengan emoji 😊
"""


class ChatMessage(BaseModel):
    """Single chat message"""
    role: str  # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    """Request for chat completion"""
    message: str
    history: List[ChatMessage] = []


class ChatResponse(BaseModel):
    """Response from chat completion"""
    reply: str
    success: bool


@router.post("/api/chat/support", response_model=ChatResponse)
async def customer_support_chat(request: ChatRequest):
    """
    Customer support chatbot endpoint using Qwen AI

    Args:
        request: ChatRequest containing user message and conversation history

    Returns:
        ChatResponse with AI-generated reply
    """

    if not QWEN_API_KEY:
        logger.error("❌ QWEN_API_KEY not set")
        return ChatResponse(
            reply="Maaf, sistem chat belum dikonfigurasi. Sila hubungi WhatsApp support.",
            success=False
        )

    try:
        # Build messages array
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]

        # Add conversation history (last 6 messages only for performance)
        for msg in request.history[-6:]:
            messages.append({"role": msg.role, "content": msg.content})

        # Add current user message
        messages.append({"role": "user", "content": request.message})

        logger.info(f"📨 Chat request: {request.message[:50]}...")

        async with httpx.AsyncClient(timeout=30.0) as client:

            # TRY METHOD 1: OpenAI-compatible format (recommended)
            logger.info("🔄 Trying OpenAI-compatible format...")
            response = await client.post(
                OPENAI_COMPATIBLE_URL,
                headers={
                    "Authorization": f"Bearer {QWEN_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "qwen-turbo",
                    "messages": messages,
                    "max_tokens": 300,
                    "temperature": 0.7
                }
            )

            logger.info(f"📊 Qwen response status: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                logger.info(f"✅ Qwen response received")

                # OpenAI-compatible format
                if "choices" in data:
                    reply = data["choices"][0]["message"]["content"]
                # DashScope format
                elif "output" in data:
                    output = data["output"]
                    reply = output.get("text", "") or output.get("choices", [{}])[0].get("message", {}).get("content", "")
                else:
                    reply = ""

                if reply:
                    logger.info(f"💬 Reply generated: {reply[:50]}...")
                    return ChatResponse(reply=reply.strip(), success=True)
                else:
                    logger.warning(f"⚠️ Empty reply from Qwen. Response data: {data}")
                    return ChatResponse(
                        reply="Maaf, saya tidak faham. Boleh terangkan dengan lebih jelas? 🤔",
                        success=True
                    )
            else:
                logger.error(f"❌ Qwen API error (OpenAI format): {response.status_code}")
                logger.error(f"Response: {response.text[:500]}")

                # TRY METHOD 2: DashScope native format (fallback)
                logger.info("🔄 Trying DashScope native format...")
                response2 = await client.post(
                    DASHSCOPE_URL,
                    headers={
                        "Authorization": f"Bearer {QWEN_API_KEY}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "qwen-turbo",
                        "input": {"messages": messages},
                        "parameters": {
                            "max_tokens": 300,
                            "temperature": 0.7
                        }
                    }
                )

                logger.info(f"📊 DashScope response status: {response2.status_code}")

                if response2.status_code == 200:
                    data2 = response2.json()
                    logger.info(f"✅ DashScope response received")
                    reply = data2.get("output", {}).get("text", "")
                    if reply:
                        logger.info(f"💬 Reply from DashScope: {reply[:50]}...")
                        return ChatResponse(reply=reply.strip(), success=True)
                else:
                    logger.error(f"❌ DashScope API also failed: {response2.status_code}")
                    logger.error(f"Response: {response2.text[:500]}")

                return ChatResponse(
                    reply="Maaf, sistem sibuk sekarang. Cuba lagi sebentar atau hubungi WhatsApp. 🙏",
                    success=False
                )

    except httpx.TimeoutException:
        logger.error("⏱️ Qwen API timeout")
        return ChatResponse(
            reply="Maaf, sambungan lambat. Sila cuba lagi. ⏳",
            success=False
        )
    except Exception as e:
        logger.error(f"❌ Chat error: {type(e).__name__}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return ChatResponse(
            reply="Maaf, berlaku ralat teknikal. Sila hubungi WhatsApp support. 🙏",
            success=False
        )


@router.get("/api/chat/health")
async def chat_health():
    """
    Check if chat service is working

    Returns:
        Health status and configuration info
    """
    return {
        "status": "ok",
        "qwen_configured": bool(QWEN_API_KEY),
        "qwen_key_preview": QWEN_API_KEY[:10] + "..." if QWEN_API_KEY else None,
        "service": "BinaApp Customer Support Chatbot"
    }


@router.get("/api/chat/test")
async def chat_test():
    """
    Test Qwen API directly for debugging

    Returns:
        Test results with API response
    """
    if not QWEN_API_KEY:
        return {
            "error": "QWEN_API_KEY not configured",
            "status": "failed"
        }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            # Test OpenAI-compatible format
            response = await client.post(
                OPENAI_COMPATIBLE_URL,
                headers={
                    "Authorization": f"Bearer {QWEN_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "qwen-turbo",
                    "messages": [{"role": "user", "content": "Hi, test message. Reply with 'OK'."}],
                    "max_tokens": 50
                }
            )

            result = {
                "status_code": response.status_code,
                "api_format": "openai-compatible",
                "response": response.json() if response.status_code == 200 else response.text[:500]
            }

            # If OpenAI format fails, try DashScope format
            if response.status_code != 200:
                response2 = await client.post(
                    DASHSCOPE_URL,
                    headers={
                        "Authorization": f"Bearer {QWEN_API_KEY}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "qwen-turbo",
                        "input": {"messages": [{"role": "user", "content": "Hi, test message. Reply with 'OK'."}]},
                        "parameters": {"max_tokens": 50}
                    }
                )

                result["fallback"] = {
                    "status_code": response2.status_code,
                    "api_format": "dashscope-native",
                    "response": response2.json() if response2.status_code == 200 else response2.text[:500]
                }

            return result

    except Exception as e:
        return {
            "error": str(e),
            "error_type": type(e).__name__,
            "status": "exception"
        }
