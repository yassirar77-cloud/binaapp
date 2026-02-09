"""
AI Chatbot Support Service
Conversational AI support agent using:
- DeepSeek API for text chat/reasoning/action decisions
- Qwen VL API only for image analysis when user uploads photos
"""

import json
import re
import uuid
from datetime import datetime, timedelta
from typing import Optional

import httpx
from loguru import logger
from openai import AsyncOpenAI

from app.core.config import settings
from app.core.supabase import get_supabase_client


SYSTEM_PROMPT = """You are BinaBot, the AI support assistant for BinaApp, a Malaysian food delivery and restaurant website platform. You communicate in Bahasa Melayu (primary) and English.

You have access to the user's data and can take these actions:
- CHECK_ORDER: Look up order details (params: {"order_id": "..."})
- CHECK_WEBSITE: Check website status and health (params: {"website_id": "..."})
- CHECK_PAYMENT: Verify payment status (params: {"order_id": "..."})
- CREATE_DISPUTE: Create a formal dispute (params: {"order_id": "...", "category": "...", "description": "..."})
- AWARD_CREDIT: Give BinaCredit to user's wallet (params: {"amount": 5.00, "reason": "..."})
- SCAN_WEBSITE: Trigger website health scan (params: {"website_id": "..."})
- FIX_WEBSITE: Apply an auto-fix to website (params: {"website_id": "..."})
- ESCALATE: Send to human admin (params: {"reason": "..."})

Rules:
- Always be empathetic and helpful
- Verify claims using system data before awarding credits
- For minor issues (< RM10 value), resolve immediately with credits
- For major issues, create a formal dispute
- If you can't resolve, escalate politely
- Never reveal internal system details or fraud scores
- Always explain what action you're taking

When you receive image analysis context, use it to inform your response.

Respond in this JSON format:
{
  "message": "your response to the user in Malay/English",
  "action": null,
  "action_params": {}
}

IMPORTANT: Always return valid JSON. The "action" field should be null if no action is needed, or one of the action names listed above."""


class AIChatbotService:
    """
    Conversational AI support agent.
    - DeepSeek API for text chat/reasoning/action decisions
    - Qwen VL API only for image analysis when user uploads photos
    """

    def __init__(self):
        self.deepseek_client = AsyncOpenAI(
            api_key=settings.DEEPSEEK_API_KEY,
            base_url=settings.DEEPSEEK_API_URL,
        )
        self.qwen_client = AsyncOpenAI(
            api_key=settings.QWEN_API_KEY or "",
            base_url=settings.QWEN_API_URL,
        ) if settings.QWEN_API_KEY else None

    async def start_chat(self, user_id: str, website_id: Optional[str] = None, order_id: Optional[str] = None) -> dict:
        """Start a new support chat session."""
        supabase = get_supabase_client()

        chat_id = str(uuid.uuid4())
        chat_data = {
            "id": chat_id,
            "user_id": user_id,
            "status": "active",
            "messages_count": 0,
            "ai_model_used": "deepseek-chat",
        }
        if website_id:
            chat_data["website_id"] = website_id
        if order_id:
            chat_data["order_id"] = order_id

        supabase.table("ai_support_chats").insert(chat_data).execute()

        # Insert welcome message
        welcome_msg = {
            "id": str(uuid.uuid4()),
            "chat_id": chat_id,
            "role": "assistant",
            "content": "Assalamualaikum! Saya BinaBot, pembantu AI BinaApp. Bagaimana saya boleh membantu anda hari ini? Anda boleh:\n\n- Tanyakan tentang pesanan anda\n- Laporkan masalah dengan laman web\n- Minta bantuan pembayaran\n- Hantar gambar masalah anda\n\nSila terangkan isu anda.",
        }
        supabase.table("ai_support_messages").insert(welcome_msg).execute()
        supabase.table("ai_support_chats").update({"messages_count": 1}).eq("id", chat_id).execute()

        return {
            "chat_id": chat_id,
            "status": "active",
            "welcome_message": welcome_msg["content"],
        }

    async def chat(self, chat_id: str, user_id: str, user_message: str, image_urls: Optional[list] = None) -> dict:
        """
        Process a user message with optional images.
        """
        supabase = get_supabase_client()

        # Verify chat belongs to user
        chat_result = supabase.table("ai_support_chats").select("*").eq("id", chat_id).execute()
        if not chat_result.data:
            raise ValueError("Chat not found")

        chat = chat_result.data[0]
        if chat["user_id"] != user_id:
            raise ValueError("Access denied")

        if chat["status"] not in ("active", "escalated"):
            raise ValueError("Chat is closed")

        # 1. Load conversation history
        history_result = supabase.table("ai_support_messages").select(
            "role, content"
        ).eq("chat_id", chat_id).order("created_at").execute()

        history = history_result.data or []

        # 2. Load user context
        user_context = await self._get_user_context(user_id)

        # 3. Analyze images with Qwen VL if present
        image_analysis_text = ""
        image_analyses = []
        if image_urls:
            for url in image_urls:
                try:
                    analysis = await self.analyze_image_with_qwen(url, user_message)
                    image_analyses.append({"url": url, "analysis": analysis})
                    image_analysis_text += f"\n[IMAGE ANALYSIS: {analysis}]"
                except Exception as e:
                    logger.warning(f"Image analysis failed for {url}: {e}")
                    image_analyses.append({"url": url, "analysis": "Image analysis unavailable"})

        # 4. Build message with image context
        full_user_message = user_message
        if image_analysis_text:
            full_user_message += image_analysis_text

        # 5. Build messages for DeepSeek
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]

        # Add user context as system message
        context_msg = f"""User context:
- User ID: {user_id}
- Recent orders: {json.dumps(user_context.get('recent_orders', [])[:3])}
- Websites: {json.dumps(user_context.get('websites', [])[:3])}
- Wallet balance: RM{user_context.get('wallet_balance', 0):.2f}"""
        messages.append({"role": "system", "content": context_msg})

        # Add conversation history (limit to last 20 messages to avoid token limit)
        for msg in history[-20:]:
            messages.append({"role": msg["role"], "content": msg["content"]})

        messages.append({"role": "user", "content": full_user_message})

        # 6. Call DeepSeek
        ai_response = await self._call_deepseek(messages)

        # 7. Parse response
        ai_message = ai_response.get("message", "Maaf, saya menghadapi masalah teknikal. Sila cuba lagi.")
        action = ai_response.get("action")
        action_params = ai_response.get("action_params", {})

        # 8. Execute action if any
        action_result = None
        action_taken = None
        action_data = None
        if action:
            try:
                action_params["chat_id"] = chat_id
                action_result = await self.execute_action(action, action_params, user_id)
                action_taken = action.lower()
                action_data = action_result
            except Exception as e:
                logger.error(f"Action execution failed: {action} - {e}")
                action_result = {"error": str(e)}

        # 9. Save user message
        user_msg_data = {
            "id": str(uuid.uuid4()),
            "chat_id": chat_id,
            "role": "user",
            "content": user_message,
            "image_urls": image_urls or [],
            "image_analysis": image_analyses if image_analyses else None,
        }
        supabase.table("ai_support_messages").insert(user_msg_data).execute()

        # 10. Save AI response
        ai_msg_data = {
            "id": str(uuid.uuid4()),
            "chat_id": chat_id,
            "role": "assistant",
            "content": ai_message,
            "action_taken": action_taken,
            "action_data": action_data,
        }
        supabase.table("ai_support_messages").insert(ai_msg_data).execute()

        # 11. Update chat metadata
        new_count = (chat.get("messages_count", 0) or 0) + 2
        update_data = {
            "messages_count": new_count,
            "updated_at": datetime.utcnow().isoformat(),
        }

        # Auto-detect category from first user message
        if not chat.get("category") and new_count <= 3:
            category = self._detect_category(user_message)
            if category:
                update_data["category"] = category

        # Generate title from first message
        if not chat.get("title"):
            update_data["title"] = user_message[:80]

        # Track credits awarded
        if action == "AWARD_CREDIT" and action_result and not action_result.get("error"):
            awarded = float(action_params.get("amount", 0))
            current_awarded = float(chat.get("credit_awarded", 0) or 0)
            update_data["credit_awarded"] = current_awarded + awarded

        supabase.table("ai_support_chats").update(update_data).eq("id", chat_id).execute()

        return {
            "message": ai_message,
            "action": action,
            "action_result": action_result,
            "image_analyses": image_analyses if image_analyses else None,
        }

    async def analyze_image_with_qwen(self, image_url: str, context: str = "") -> str:
        """
        Send image to Qwen VL for analysis. Returns text description.
        """
        if not self.qwen_client:
            return "Image analysis not available (Qwen VL not configured)"

        try:
            prompt = "Describe this image in detail. "
            if context:
                prompt += f"The user is reporting: '{context}'. Focus on issues visible in the image related to their complaint."
            else:
                prompt += "If this is food, describe its condition. If this is a screenshot, describe what you see."

            response = await self.qwen_client.chat.completions.create(
                model="qwen-vl-max",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "image_url", "image_url": {"url": image_url}},
                            {"type": "text", "text": prompt},
                        ],
                    }
                ],
                max_tokens=500,
            )

            return response.choices[0].message.content or "Unable to analyze image"
        except Exception as e:
            logger.error(f"Qwen VL analysis failed: {e}")
            return f"Image analysis failed: {str(e)}"

    async def _call_deepseek(self, messages: list) -> dict:
        """Send chat messages to DeepSeek API. Returns parsed response."""
        try:
            response = await self.deepseek_client.chat.completions.create(
                model=settings.DEEPSEEK_MODEL,
                messages=messages,
                temperature=0.5,
                max_tokens=1500,
            )

            content = response.choices[0].message.content or ""

            # Strip markdown code blocks
            content = re.sub(r"^```(?:json)?\s*", "", content.strip())
            content = re.sub(r"\s*```$", "", content.strip())

            try:
                return json.loads(content)
            except json.JSONDecodeError:
                # If not valid JSON, treat as plain message
                return {"message": content, "action": None, "action_params": {}}

        except Exception as e:
            logger.error(f"DeepSeek chat failed: {e}")
            return {
                "message": "Maaf, saya menghadapi masalah teknikal. Sila cuba lagi sebentar.",
                "action": None,
                "action_params": {},
            }

    async def execute_action(self, action: str, params: dict, user_id: str) -> dict:
        """Execute an AI-decided action."""
        if action == "CHECK_ORDER":
            return await self._check_order(params.get("order_id"), user_id)
        elif action == "CHECK_WEBSITE":
            return await self._check_website(params.get("website_id"), user_id)
        elif action == "CHECK_PAYMENT":
            return await self._check_order(params.get("order_id"), user_id)
        elif action == "AWARD_CREDIT":
            return await self._award_credit(user_id, params.get("amount", 0), params.get("reason", "AI support"))
        elif action == "CREATE_DISPUTE":
            return await self._create_dispute(user_id, params)
        elif action == "SCAN_WEBSITE":
            return await self._scan_website(params.get("website_id"), user_id)
        elif action == "ESCALATE":
            return await self._escalate(params.get("chat_id"), params.get("reason", ""))
        else:
            return {"error": f"Unknown action: {action}"}

    async def _check_order(self, order_id: Optional[str], user_id: str) -> dict:
        """Fetch order details from delivery_orders + order_items."""
        if not order_id:
            return {"error": "No order ID provided"}

        supabase = get_supabase_client()
        result = supabase.table("delivery_orders").select(
            "id, status, total_amount, created_at, updated_at, customer_name, delivery_address"
        ).eq("id", order_id).execute()

        if not result.data:
            return {"error": "Order not found"}

        order = result.data[0]

        # Get order items
        items_result = supabase.table("order_items").select(
            "item_name, quantity, price"
        ).eq("order_id", order_id).execute()

        order["items"] = items_result.data or []
        return order

    async def _check_website(self, website_id: Optional[str], user_id: str) -> dict:
        """Check website status."""
        if not website_id:
            return {"error": "No website ID provided"}

        supabase = get_supabase_client()
        result = supabase.table("websites").select(
            "id, business_name, subdomain, created_at"
        ).eq("id", website_id).eq("user_id", user_id).execute()

        if not result.data:
            return {"error": "Website not found"}

        website = result.data[0]

        # Check latest health scan
        scan_result = supabase.table("website_health_scans").select(
            "overall_score, status, created_at"
        ).eq("website_id", website_id).order("created_at", desc=True).limit(1).execute()

        if scan_result.data:
            website["latest_scan"] = scan_result.data[0]

        return website

    async def _award_credit(self, user_id: str, amount: float, reason: str) -> dict:
        """
        Award credits directly from chatbot.
        Max RM10 without dispute creation.
        """
        amount = float(amount)
        if amount <= 0:
            return {"error": "Invalid amount"}
        if amount > 10:
            return {"error": "Amount exceeds chatbot limit (RM10). Please create a formal dispute."}

        supabase = get_supabase_client()

        # Check for duplicate awards in last hour
        since = (datetime.utcnow() - timedelta(hours=1)).isoformat()
        recent_awards = supabase.table("credit_transactions").select("id").eq(
            "user_id", user_id
        ).eq("type", "earned").gt("created_at", since).execute()

        if len(recent_awards.data or []) >= 3:
            return {"error": "Too many credit awards recently. Please try again later."}

        # Get or create wallet
        wallet_result = supabase.table("bina_credits").select("balance").eq("user_id", user_id).execute()
        if wallet_result.data:
            current_balance = float(wallet_result.data[0].get("balance", 0))
            new_balance = current_balance + amount
            supabase.table("bina_credits").update({"balance": new_balance}).eq("user_id", user_id).execute()
        else:
            supabase.table("bina_credits").insert({
                "user_id": user_id,
                "balance": amount,
            }).execute()
            new_balance = amount

        # Create transaction
        supabase.table("credit_transactions").insert({
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "type": "earned",
            "amount": amount,
            "description": f"AI Support: {reason}",
            "source": "ai_chatbot",
        }).execute()

        return {
            "credited": amount,
            "new_balance": new_balance,
            "reason": reason,
        }

    async def _create_dispute(self, user_id: str, params: dict) -> dict:
        """Create a dispute record and link to chat."""
        supabase = get_supabase_client()

        dispute_id = str(uuid.uuid4())
        dispute_data = {
            "id": dispute_id,
            "order_id": params.get("order_id"),
            "user_id": user_id,
            "category": params.get("category", "other"),
            "description": params.get("description", "Created via AI chatbot"),
            "status": "open",
            "source": "ai_chatbot",
        }
        supabase.table("ai_disputes").insert(dispute_data).execute()

        # Link dispute to chat
        chat_id = params.get("chat_id")
        if chat_id:
            supabase.table("ai_support_chats").update({
                "dispute_id": dispute_id,
            }).eq("id", chat_id).execute()

        return {"dispute_id": dispute_id, "status": "open"}

    async def _scan_website(self, website_id: Optional[str], user_id: str) -> dict:
        """Trigger AIWebsiteDoctor.scan_website()."""
        if not website_id:
            return {"error": "No website ID provided"}

        from app.services.ai_website_doctor import website_doctor
        result = await website_doctor.scan_website(website_id, user_id, scan_type="dispute_triggered")
        return result

    async def _escalate(self, chat_id: Optional[str], reason: str) -> dict:
        """Mark chat as escalated."""
        if not chat_id:
            return {"error": "No chat ID"}

        supabase = get_supabase_client()
        supabase.table("ai_support_chats").update({
            "status": "escalated",
            "resolution_type": "escalated",
        }).eq("id", chat_id).execute()

        return {"status": "escalated", "reason": reason}

    async def _get_user_context(self, user_id: str) -> dict:
        """Load user context for AI."""
        supabase = get_supabase_client()
        context: dict = {}

        try:
            # Recent orders
            orders_result = supabase.table("delivery_orders").select(
                "id, status, total_amount, created_at"
            ).eq("customer_phone", user_id).order("created_at", desc=True).limit(5).execute()
            context["recent_orders"] = orders_result.data or []
        except Exception:
            context["recent_orders"] = []

        try:
            # User's websites
            websites_result = supabase.table("websites").select(
                "id, business_name, subdomain"
            ).eq("user_id", user_id).execute()
            context["websites"] = websites_result.data or []
        except Exception:
            context["websites"] = []

        try:
            # Wallet balance
            wallet_result = supabase.table("bina_credits").select("balance").eq("user_id", user_id).execute()
            context["wallet_balance"] = float(wallet_result.data[0]["balance"]) if wallet_result.data else 0.0
        except Exception:
            context["wallet_balance"] = 0.0

        return context

    def _detect_category(self, message: str) -> Optional[str]:
        """Detect support category from message text."""
        text = message.lower()
        categories = {
            "order": ["pesanan", "order", "makanan", "food", "delivery", "penghantaran"],
            "payment": ["bayar", "payment", "duit", "refund", "wang", "credit"],
            "website": ["laman", "website", "web", "subdomain", "broken", "rosak"],
            "account": ["akaun", "account", "login", "password", "langganan"],
        }
        for cat, keywords in categories.items():
            for kw in keywords:
                if kw in text:
                    return cat
        return None

    async def get_chat_messages(self, chat_id: str, user_id: str) -> list:
        """Get all messages for a chat."""
        supabase = get_supabase_client()

        # Verify ownership
        chat_result = supabase.table("ai_support_chats").select("user_id").eq("id", chat_id).execute()
        if not chat_result.data or chat_result.data[0]["user_id"] != user_id:
            raise ValueError("Access denied")

        messages_result = supabase.table("ai_support_messages").select("*").eq(
            "chat_id", chat_id
        ).order("created_at").execute()

        return messages_result.data or []

    async def get_active_chats(self, user_id: str) -> list:
        """Get user's active chats."""
        supabase = get_supabase_client()
        result = supabase.table("ai_support_chats").select("*").eq(
            "user_id", user_id
        ).in_("status", ["active", "escalated"]).order("updated_at", desc=True).execute()
        return result.data or []

    async def close_chat(self, chat_id: str, user_id: str) -> dict:
        """Close a chat."""
        supabase = get_supabase_client()

        chat_result = supabase.table("ai_support_chats").select("user_id, status").eq("id", chat_id).execute()
        if not chat_result.data or chat_result.data[0]["user_id"] != user_id:
            raise ValueError("Access denied")

        supabase.table("ai_support_chats").update({
            "status": "closed",
            "updated_at": datetime.utcnow().isoformat(),
        }).eq("id", chat_id).execute()

        return {"message": "Chat closed", "chat_id": chat_id}

    async def rate_chat(self, chat_id: str, user_id: str, rating: int) -> dict:
        """Rate a chat satisfaction."""
        if rating < 1 or rating > 5:
            raise ValueError("Rating must be between 1 and 5")

        supabase = get_supabase_client()

        chat_result = supabase.table("ai_support_chats").select("user_id").eq("id", chat_id).execute()
        if not chat_result.data or chat_result.data[0]["user_id"] != user_id:
            raise ValueError("Access denied")

        supabase.table("ai_support_chats").update({
            "satisfaction_rating": rating,
        }).eq("id", chat_id).execute()

        return {"message": "Rating saved", "rating": rating}


# Singleton instance
chatbot_service = AIChatbotService()
