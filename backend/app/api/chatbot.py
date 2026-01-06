"""
Customer Support Chatbot using Qwen AI
Provides instant customer support for BinaApp users
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import httpx
import os
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

# Qwen API configuration
QWEN_API_URL = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"
QWEN_API_KEY = os.getenv("QWEN_API_KEY")

# BinaApp support knowledge base
BINAAPP_SUPPORT_PROMPT = """
Anda adalah pembantu sokongan pelanggan BinaApp. Nama anda "BinaBot".

## TENTANG BINAAPP:
BinaApp adalah platform pembina website AI untuk SME Malaysia.
- Bina website dalam 60 saat menggunakan AI
- Tiada perlu coding
- Bahasa Melayu sepenuhnya

## PELAN HARGA:
1. PERCUMA (RM0):
   - 1 website
   - Subdomain: namaanda.binaapp.my
   - BinaApp branding
   - 3 AI generation/hari

2. PRO (RM19/bulan):
   - 5 websites
   - Custom domain
   - Tiada branding
   - 20 AI generation/hari
   - Analytics

3. BUSINESS (RM39/bulan):
   - Unlimited websites
   - Custom domain
   - Tiada branding
   - Unlimited AI generation
   - Advanced analytics
   - Email marketing

## CIRI-CIRI UTAMA:
- AI Website Builder: Jana website automatik dari description bisnes
- Delivery System: Untuk restoran/F&B dengan menu online
- Custom Domain: Sambung domain sendiri
- PWA Support: Website boleh install macam app

## TROUBLESHOOTING BIASA:

### Website stuck at 20%:
1. Refresh page (F5 atau Cmd+R)
2. Clear browser cache
3. Cuba browser lain (Chrome/Safari)
4. Jika masih stuck, tunggu 2-3 minit

### Custom domain tak connect:
1. Pastikan DNS settings betul:
   - CNAME: www → binaapp.my
   - A Record: @ → [IP BinaApp]
2. DNS ambil masa 24-48 jam untuk propagate
3. Check domain status di Dashboard

### Gambar tak upload:
1. Max size: 5MB per gambar
2. Format: JPG, PNG, WebP sahaja
3. Cuba compress gambar dulu

### Website tak publish:
1. Check semua required fields filled
2. Pastikan business name ada
3. Cuba logout dan login semula

### Delivery system tak muncul:
1. Enable delivery di Dashboard → Settings
2. Pastikan ada menu items
3. Refresh page selepas enable

## CARA CONTACT SUPPORT:
- WhatsApp: 011-XXXX XXXX
- Email: support@binaapp.my

## CARA RESPOND:
1. Jawab dalam bahasa yang user guna (BM atau English)
2. Berikan step-by-step jelas
3. Jika tak pasti, minta user contact WhatsApp support
4. Sentiasa mesra dan helpful
5. Guna emoji untuk friendly tone 😊

## PERKARA YANG TIDAK BOLEH:
- Jangan beri maklumat salah
- Jangan promise features yang tiada
- Jangan share internal/technical details
- Jika soalan diluar BinaApp, politely redirect

## CONTOH RESPONSES:

User: "Macam mana nak buat website?"
Response: "Senang je! 😊 Ikut langkah ni:
1. Pergi ke binaapp.my
2. Klik 'Mula Sekarang'
3. Masukkan nama bisnes dan description
4. AI akan generate website untuk anda dalam 60 saat!

Ada apa-apa soalan lain?"

User: "How much is pro plan?"
Response: "The Pro plan is RM19/month! 🎉 You'll get:
- 5 websites
- Custom domain support
- No BinaApp branding
- 20 AI generations per day
- Analytics dashboard

Would you like to upgrade? Go to Dashboard → Billing → Upgrade"
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
        logger.error("Qwen API key not configured")
        raise HTTPException(500, "Chatbot service not configured")

    try:
        # Build messages array for Qwen API
        messages = [
            {"role": "system", "content": BINAAPP_SUPPORT_PROMPT}
        ]

        # Add conversation history (last 10 messages to keep context manageable)
        for msg in request.history[-10:]:
            messages.append({
                "role": msg.role,
                "content": msg.content
            })

        # Add current user message
        messages.append({
            "role": "user",
            "content": request.message
        })

        logger.info(f"Processing chat request with {len(messages)} messages")

        # Call Qwen API
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                QWEN_API_URL,
                headers={
                    "Authorization": f"Bearer {QWEN_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "qwen-turbo",
                    "input": {
                        "messages": messages
                    },
                    "parameters": {
                        "max_tokens": 500,
                        "temperature": 0.7,
                        "top_p": 0.9
                    }
                }
            )

            if response.status_code == 200:
                data = response.json()
                reply = data.get("output", {}).get("text", "")

                if not reply:
                    logger.warning("Empty reply from Qwen API")
                    reply = "Maaf, saya tidak dapat memproses soalan anda. Sila hubungi WhatsApp support kami. 🙏"

                logger.info("Chat response generated successfully")
                return ChatResponse(reply=reply, success=True)
            else:
                logger.error(f"Qwen API error: {response.status_code} - {response.text}")
                return ChatResponse(
                    reply="Maaf, sistem sedang sibuk. Sila cuba sebentar lagi atau hubungi WhatsApp support. 🙏",
                    success=False
                )

    except httpx.TimeoutException:
        logger.error("Qwen API timeout")
        return ChatResponse(
            reply="Maaf, sistem mengambil masa terlalu lama. Sila cuba lagi atau hubungi WhatsApp support. 🙏",
            success=False
        )
    except Exception as e:
        logger.error(f"Chat error: {e}")
        return ChatResponse(
            reply="Maaf, berlaku ralat. Sila hubungi WhatsApp support kami untuk bantuan. 🙏",
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
        "service": "BinaApp Customer Support Chatbot"
    }
