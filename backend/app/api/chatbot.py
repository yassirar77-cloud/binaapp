"""
Customer Support Chatbot using DeepSeek AI
Provides instant customer support for BinaApp users
"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import List
import httpx
import os

router = APIRouter()

# Use DeepSeek API (faster and cheaper than Qwen)
# Check multiple possible environment variable names
DEEPSEEK_API_KEY = (
    os.getenv("DEEPSEEK_API_KEY") or
    os.getenv("DEEPSEEK_KEY") or
    os.getenv("DASHSCOPE_API_KEY")
)
DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

# Debug: Log which env var was found
if DEEPSEEK_API_KEY:
    for var_name in ["DEEPSEEK_API_KEY", "DEEPSEEK_KEY", "DASHSCOPE_API_KEY"]:
        if os.getenv(var_name):
            print(f"✅ Using API key from: {var_name}")
            break
else:
    print("❌ No API key found in: DEEPSEEK_API_KEY, DEEPSEEK_KEY, DASHSCOPE_API_KEY")

# BinaApp support knowledge base
SYSTEM_PROMPT = """Anda adalah BinaBot, pembantu sokongan pelanggan BinaApp. Respond dalam bahasa yang user guna (BM atau English).

TENTANG BINAAPP:
- Platform digital lengkap untuk perniagaan makanan & restoran Malaysia
- Bina website perniagaan dalam masa minit menggunakan AI
- Tiada perlu coding - hanya terangkan perniagaan anda
- Termasuk: website builder, order management, delivery system, payment integration

PELAN HARGA (dikemaskini Mac 2026):
- STARTER (RM5/bulan): 1 website, subdomain .binaapp.my, 20 menu items, 1 AI hero/bulan, 5 AI images/bulan, 1 delivery zone, email support
- BASIC (RM29/bulan): 5 websites, custom subdomain, unlimited menu items, 10 AI hero/bulan, 30 AI images/bulan, 5 delivery zones, priority AI, analytics, priority support, QR payment, contact form
- PRO (RM49/bulan): Unlimited websites, unlimited menu items, unlimited AI, unlimited delivery zones, 10 riders GPS, advanced AI, priority support

ADDON CREDITS (beli extra bila capai had):
- AI Image: RM1.00/credit
- AI Hero: RM2.00/credit
- Website: RM5.00/credit
- Rider: RM3.00/credit
- Delivery Zone: RM2.00/credit

FEATURES UTAMA:
- AI Website Builder: Jana website lengkap dengan AI dalam masa minit
- Order Management: Terima, urus & track pesanan (Pending → Confirmed → Preparing → Ready → Delivered)
- Delivery System: Tambah rider, GPS tracking real-time, assign order ke rider
- Payment Integration: ToyyibPay (FPX, credit/debit card, e-wallet)
- BinaChat: Real-time messaging antara customer, restaurant & rider
- Menu Management: Tambah item, kategori, variasi & add-ons
- AI Support: BinaBot sokongan 24/7, analisis gambar, dispute resolution

CARA SETUP TOYYIBPAY:
1. Buat akaun di toyyibpay.com
2. Complete merchant verification
3. Dapatkan API Secret Key & Category Code
4. Masukkan di BinaApp: Settings → Payments → ToyyibPay
5. Test dengan transaksi kecil

TROUBLESHOOTING:
1. Website stuck / tak load: Refresh page, clear cache, cuba browser lain
2. Domain tak connect: Tunggu 24-48 jam untuk DNS propagate
3. Gambar tak upload: Max 5MB, format JPG/PNG sahaja
4. Delivery tak muncul: Enable di Dashboard → Settings → Delivery
5. Pesanan tak diterima: Check notification settings, pastikan logged in
6. Payment gagal: Check ToyyibPay credentials, pastikan akaun verified
7. Menu tak update: Clear browser cache, tunggu 5 minit untuk CDN update
8. Session tamat: Log in semula

SUBSCRIPTION:
- Naik taraf: Settings → Subscription → Naik Taraf
- Payment melalui ToyyibPay
- Perbaharui: Settings → Subscription → Perbaharui Sekarang
- Expiry reminder: Email 7/3/1 hari sebelum tamat

CONTACT:
- Email: support.team@binaapp.my (respon dalam 24 jam hari bekerja)
- Admin/Billing: admin@binaapp.my
- Urgent: Email admin@binaapp.my dengan subject "URGENT"
- Waktu sokongan: Isnin-Jumaat 9AM-6PM, Sabtu 9AM-1PM (MYT)

CARA RESPOND:
- Ringkas dan jelas
- Mesra dengan emoji 😊
- Step-by-step jika perlu
- Jika tak pasti, arahkan ke support.team@binaapp.my
"""


class ChatMessage(BaseModel):
    """Single chat message"""
    role: str
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
    Customer support chatbot endpoint using DeepSeek AI

    Args:
        request: ChatRequest containing user message and conversation history

    Returns:
        ChatResponse with AI-generated reply
    """

    # Debug: Show API key configuration status
    print(f"🔑 API Key configured: {bool(DEEPSEEK_API_KEY)}")
    if DEEPSEEK_API_KEY:
        print(f"🔑 Key preview: {DEEPSEEK_API_KEY[:10]}...")

    if not DEEPSEEK_API_KEY:
        print("❌ ERROR: No DEEPSEEK_API_KEY found in environment")
        return ChatResponse(
            reply="Maaf, sistem chat belum dikonfigurasi. Sila hubungi WhatsApp support. 🙏",
            success=False
        )

    try:
        # Build messages array
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]

        # Add conversation history (last 6 messages for context)
        for msg in request.history[-6:]:
            messages.append({"role": msg.role, "content": msg.content})

        # Add current user message
        messages.append({"role": "user", "content": request.message})

        print(f"📨 Chat request: {request.message[:50]}...")

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                DEEPSEEK_URL,
                headers={
                    "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": DEEPSEEK_MODEL,
                    "messages": messages,
                    "max_tokens": 300,
                    "temperature": 0.7
                }
            )

            print(f"📊 DeepSeek status: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                reply = data["choices"][0]["message"]["content"]
                print(f"✅ Reply: {reply[:50]}...")
                return ChatResponse(reply=reply.strip(), success=True)
            else:
                print(f"❌ DeepSeek error: {response.status_code} - {response.text[:200]}")
                return ChatResponse(
                    reply="Maaf, sistem sibuk. Cuba lagi sebentar. 🙏",
                    success=False
                )

    except httpx.TimeoutException:
        print("⏱️ DeepSeek timeout")
        return ChatResponse(
            reply="Maaf, sambungan lambat. Sila cuba lagi. ⏳",
            success=False
        )
    except Exception as e:
        print(f"❌ Chat error: {type(e).__name__}: {e}")
        return ChatResponse(
            reply="Maaf, berlaku ralat. Hubungi WhatsApp support. 🙏",
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
        "deepseek_configured": bool(DEEPSEEK_API_KEY),
        "service": "BinaBot (DeepSeek)",
        "api_key_preview": DEEPSEEK_API_KEY[:10] + "..." if DEEPSEEK_API_KEY else None
    }


@router.get("/api/chat/test")
async def chat_test():
    """
    Test DeepSeek API directly for debugging

    Returns:
        Test results with API response
    """
    if not DEEPSEEK_API_KEY:
        return {
            "error": "No API key found",
            "status": "failed",
            "checked_vars": ["DEEPSEEK_API_KEY", "DEEPSEEK_KEY", "DASHSCOPE_API_KEY"]
        }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                DEEPSEEK_URL,
                headers={
                    "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": DEEPSEEK_MODEL,
                    "messages": [{"role": "user", "content": "Hi, test. Reply with 'OK'."}],
                    "max_tokens": 20
                }
            )

            if response.status_code == 200:
                data = response.json()
                return {
                    "status": "ok",
                    "reply": data["choices"][0]["message"]["content"],
                    "model": DEEPSEEK_MODEL
                }
            else:
                return {
                    "status": "error",
                    "code": response.status_code,
                    "detail": response.text[:200]
                }
    except Exception as e:
        return {
            "status": "error",
            "error_type": type(e).__name__,
            "message": str(e)
        }
