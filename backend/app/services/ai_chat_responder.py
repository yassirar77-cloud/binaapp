"""
BinaApp AI Chat Responder Service
Auto-responds to customer messages when restaurant owner is offline.
Uses DeepSeek API with restaurant context.
"""
import httpx
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from loguru import logger

from app.core.config import settings


class AIChatResponder:
    """Auto-responds to customer chats using AI when owner is offline."""

    def __init__(self):
        self.supabase_url = settings.SUPABASE_URL
        self.headers = {
            "apikey": settings.SUPABASE_SERVICE_ROLE_KEY,
            "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
            "Content-Type": "application/json"
        }
        self.deepseek_url = settings.DEEPSEEK_API_URL
        self.deepseek_key = settings.DEEPSEEK_API_KEY

    async def get_chat_settings(self, website_id: str) -> Optional[Dict[str, Any]]:
        """Get AI chat settings for a website."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.supabase_url}/rest/v1/ai_chat_settings",
                    headers=self.headers,
                    params={"website_id": f"eq.{website_id}", "select": "*"}
                )
            if response.status_code == 200:
                data = response.json()
                return data[0] if data else None
            return None
        except Exception as e:
            logger.error(f"Error getting chat settings: {e}")
            return None

    async def update_chat_settings(self, website_id: str, user_id: str, update_data: Dict) -> Optional[Dict]:
        """Update or create AI chat settings."""
        try:
            existing = await self.get_chat_settings(website_id)
            async with httpx.AsyncClient() as client:
                if existing:
                    update_data["updated_at"] = datetime.utcnow().isoformat()
                    response = await client.patch(
                        f"{self.supabase_url}/rest/v1/ai_chat_settings",
                        headers={**self.headers, "Prefer": "return=representation"},
                        params={"website_id": f"eq.{website_id}"},
                        json=update_data
                    )
                else:
                    update_data.update({
                        "website_id": website_id,
                        "user_id": user_id
                    })
                    response = await client.post(
                        f"{self.supabase_url}/rest/v1/ai_chat_settings",
                        headers={**self.headers, "Prefer": "return=representation"},
                        json=update_data
                    )

                if response.status_code in [200, 201]:
                    data = response.json()
                    return data[0] if isinstance(data, list) else data
            return None
        except Exception as e:
            logger.error(f"Error updating chat settings: {e}")
            return None

    async def get_response_history(self, website_id: str, limit: int = 50) -> List[Dict]:
        """Get AI response history for a website."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.supabase_url}/rest/v1/ai_chat_responses",
                    headers=self.headers,
                    params={
                        "website_id": f"eq.{website_id}",
                        "select": "*",
                        "order": "created_at.desc",
                        "limit": str(limit)
                    }
                )
            if response.status_code == 200:
                return response.json()
            return []
        except Exception as e:
            logger.error(f"Error getting response history: {e}")
            return []

    async def _load_restaurant_context(self, website_id: str) -> Dict[str, Any]:
        """Load restaurant context data for AI."""
        context = {"menu_items": [], "delivery_settings": None, "website_info": None}
        try:
            async with httpx.AsyncClient() as client:
                # Get menu items
                menu_resp = await client.get(
                    f"{self.supabase_url}/rest/v1/menu_items",
                    headers=self.headers,
                    params={"website_id": f"eq.{website_id}", "select": "name,description,price,is_available"}
                )
                if menu_resp.status_code == 200:
                    context["menu_items"] = menu_resp.json()

                # Get delivery settings
                delivery_resp = await client.get(
                    f"{self.supabase_url}/rest/v1/delivery_settings",
                    headers=self.headers,
                    params={"website_id": f"eq.{website_id}", "select": "*"}
                )
                if delivery_resp.status_code == 200 and delivery_resp.json():
                    context["delivery_settings"] = delivery_resp.json()[0]

                # Get website info (only select columns that exist)
                web_resp = await client.get(
                    f"{self.supabase_url}/rest/v1/websites",
                    headers=self.headers,
                    params={"id": f"eq.{website_id}", "select": "business_name,subdomain"}
                )
                if web_resp.status_code == 200 and web_resp.json():
                    context["website_info"] = web_resp.json()[0]

        except Exception as e:
            logger.error(f"Error loading restaurant context: {e}")
        return context

    async def _generate_ai_response(self, customer_message: str, context: Dict, personality: str = "friendly") -> str:
        """Generate AI response using DeepSeek."""
        try:
            business_name = context.get("website_info", {}).get("business_name", "kedai ini")

            # Build menu text
            menu_text = ""
            for item in context.get("menu_items", [])[:20]:
                avail = "Ada" if item.get("is_available", True) else "Habis"
                menu_text += f"- {item['name']}: RM{item.get('price', 0):.2f} ({avail})\n"

            # Build delivery info
            delivery_info = ""
            ds = context.get("delivery_settings")
            if ds:
                delivery_info = f"Penghantaran: {'Ya' if ds.get('is_delivery_enabled') else 'Tidak'}. "
                if ds.get("min_order_amount"):
                    delivery_info += f"Minimum order: RM{ds['min_order_amount']}. "

            personality_prompt = {
                "friendly": "Jawab dengan mesra, gunakan emoji sesekali, dan sentiasa membantu.",
                "professional": "Jawab dengan profesional dan ringkas.",
                "casual": "Jawab dengan santai seperti kawan. Boleh guna bahasa Melayu slang."
            }.get(personality, "Jawab dengan mesra dan membantu.")

            system_prompt = f"""Anda adalah BinaBot, pembantu AI untuk {business_name}.
{personality_prompt}

Maklumat kedai:
Menu:
{menu_text if menu_text else 'Tiada menu tersedia.'}

{delivery_info}

Peraturan:
1. Sentiasa kenal pasti diri anda sebagai "BinaBot" jika ditanya.
2. Jawab dalam Bahasa Melayu kecuali pelanggan menulis dalam bahasa lain.
3. Jika tidak tahu jawapan, maklumkan pemilik kedai akan membalas nanti.
4. Jangan buat janji yang tidak pasti.
5. Jawapan pendek dan padat."""

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.deepseek_url}/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.deepseek_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": settings.DEEPSEEK_MODEL,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": customer_message}
                        ],
                        "max_tokens": 300,
                        "temperature": 0.7
                    }
                )

            if response.status_code == 200:
                data = response.json()
                return data["choices"][0]["message"]["content"]

            logger.error(f"DeepSeek API error: {response.status_code}")
            return f"Terima kasih atas mesej anda! Pemilik {business_name} akan membalas sebentar lagi."

        except Exception as e:
            logger.error(f"Error generating AI response: {e}")
            return "Terima kasih atas mesej anda! Pemilik kedai akan membalas sebentar lagi."

    async def process_pending_messages(self) -> Dict[str, Any]:
        """Process pending unanswered customer messages."""
        results = {"processed": 0, "responded": 0, "errors": 0}

        try:
            # Get all enabled AI chat settings
            async with httpx.AsyncClient() as client:
                settings_resp = await client.get(
                    f"{self.supabase_url}/rest/v1/ai_chat_settings",
                    headers=self.headers,
                    params={"is_enabled": "eq.true", "select": "*"}
                )

            if settings_resp.status_code != 200:
                return results

            all_settings = settings_resp.json()

            for chat_setting in all_settings:
                website_id = chat_setting["website_id"]
                delay = chat_setting.get("delay_seconds", 120)
                cutoff = (datetime.utcnow() - timedelta(seconds=delay)).isoformat()

                try:
                    async with httpx.AsyncClient() as client:
                        # Get conversations for this website
                        conv_resp = await client.get(
                            f"{self.supabase_url}/rest/v1/chat_conversations",
                            headers=self.headers,
                            params={
                                "website_id": f"eq.{website_id}",
                                "select": "id"
                            }
                        )

                        if conv_resp.status_code != 200:
                            continue

                        conversations = conv_resp.json()

                        for conv in conversations:
                            conv_id = conv["id"]
                            # Get last message
                            msg_resp = await client.get(
                                f"{self.supabase_url}/rest/v1/chat_messages",
                                headers=self.headers,
                                params={
                                    "conversation_id": f"eq.{conv_id}",
                                    "select": "id,sender_type,content,created_at",
                                    "order": "created_at.desc",
                                    "limit": "1"
                                }
                            )

                            if msg_resp.status_code != 200 or not msg_resp.json():
                                continue

                            last_msg = msg_resp.json()[0]
                            results["processed"] += 1

                            # Only respond if last message is from customer and old enough
                            if last_msg["sender_type"] != "customer":
                                continue
                            if last_msg["created_at"] > cutoff:
                                continue

                            # Check if we already responded to this message
                            check_resp = await client.get(
                                f"{self.supabase_url}/rest/v1/ai_chat_responses",
                                headers=self.headers,
                                params={
                                    "original_message_id": f"eq.{last_msg['id']}",
                                    "select": "id"
                                }
                            )
                            if check_resp.status_code == 200 and check_resp.json():
                                continue

                            # Generate and send response
                            context = await self._load_restaurant_context(website_id)
                            personality = chat_setting.get("personality", "friendly")

                            start_time = time.time()
                            ai_text = await self._generate_ai_response(
                                last_msg["content"] or "",
                                context,
                                personality
                            )
                            response_time = int((time.time() - start_time) * 1000)

                            # Insert AI response as chat message (matches existing schema)
                            msg_data = {
                                "conversation_id": conv_id,
                                "sender_type": "system",
                                "sender_name": "BinaBot",
                                "message_type": "text",
                                "content": ai_text,
                                "metadata": {"ai_generated": True, "model": settings.DEEPSEEK_MODEL}
                            }
                            insert_resp = await client.post(
                                f"{self.supabase_url}/rest/v1/chat_messages",
                                headers={**self.headers, "Prefer": "return=representation"},
                                json=msg_data
                            )

                            if insert_resp.status_code in [200, 201]:
                                ai_msg = insert_resp.json()
                                ai_msg_id = ai_msg[0]["id"] if isinstance(ai_msg, list) else ai_msg.get("id")

                                # Log the AI response
                                await client.post(
                                    f"{self.supabase_url}/rest/v1/ai_chat_responses",
                                    headers={**self.headers, "Prefer": "return=minimal"},
                                    json={
                                        "website_id": website_id,
                                        "conversation_id": conv_id,
                                        "original_message_id": last_msg["id"],
                                        "ai_response_message_id": ai_msg_id,
                                        "customer_message": last_msg.get("content", ""),
                                        "ai_response": ai_text,
                                        "context_used": {"menu_count": len(context.get("menu_items", []))},
                                        "model_used": settings.DEEPSEEK_MODEL,
                                        "response_time_ms": response_time
                                    }
                                )
                                results["responded"] += 1
                            else:
                                results["errors"] += 1

                except Exception as e:
                    logger.error(f"Error processing website {website_id}: {e}")
                    results["errors"] += 1

        except Exception as e:
            logger.error(f"Error in process_pending_messages: {e}")

        logger.info(f"AI Chat Responder: {results}")
        return results


ai_chat_responder = AIChatResponder()
