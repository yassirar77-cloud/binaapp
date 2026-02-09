"""
BinaApp AI Order Verifier Service
Compares delivery photos against order items to detect issues.
Uses Qwen VL for image analysis.
"""
import httpx
from typing import Dict, Any, Optional, List
from loguru import logger

from app.core.config import settings


class AIOrderVerifier:
    """Verifies delivery orders using AI vision analysis."""

    def __init__(self):
        self.supabase_url = settings.SUPABASE_URL
        self.headers = {
            "apikey": settings.SUPABASE_SERVICE_ROLE_KEY,
            "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
            "Content-Type": "application/json"
        }
        self.qwen_url = settings.QWEN_API_URL
        self.qwen_key = settings.QWEN_API_KEY
        self.match_threshold = 0.7

    async def verify_order(self, order_id: str) -> Optional[Dict[str, Any]]:
        """Verify a specific order by analyzing delivery photo."""
        try:
            async with httpx.AsyncClient() as client:
                # Get order details
                order_resp = await client.get(
                    f"{self.supabase_url}/rest/v1/delivery_orders",
                    headers=self.headers,
                    params={"id": f"eq.{order_id}", "select": "*"}
                )

                if order_resp.status_code != 200 or not order_resp.json():
                    return {"error": "Pesanan tidak dijumpai"}

                order = order_resp.json()[0]
                website_id = order.get("website_id")
                customer_id = order.get("customer_id") or order.get("user_id")

                # Get delivery photo
                delivery_photo = order.get("delivery_photo_url") or order.get("proof_photo")
                if not delivery_photo:
                    return await self._save_verification(
                        order_id, website_id, None, [], [],
                        1.0, "verified", [], customer_id,
                        "Tiada foto penghantaran - anggap sah"
                    )

                # Get order items
                items_resp = await client.get(
                    f"{self.supabase_url}/rest/v1/order_items",
                    headers=self.headers,
                    params={"order_id": f"eq.{order_id}", "select": "*"}
                )
                order_items = items_resp.json() if items_resp.status_code == 200 else []

                if not order_items:
                    return await self._save_verification(
                        order_id, website_id, delivery_photo, [], [],
                        1.0, "verified", [], customer_id,
                        "Tiada item pesanan untuk disemak"
                    )

                # Get menu item details
                expected_items = []
                for item in order_items:
                    menu_id = item.get("menu_item_id")
                    if menu_id:
                        menu_resp = await client.get(
                            f"{self.supabase_url}/rest/v1/menu_items",
                            headers=self.headers,
                            params={"id": f"eq.{menu_id}", "select": "name,description"}
                        )
                        if menu_resp.status_code == 200 and menu_resp.json():
                            menu = menu_resp.json()[0]
                            expected_items.append({
                                "name": menu.get("name", item.get("item_name", "Unknown")),
                                "quantity": item.get("quantity", 1)
                            })
                    else:
                        expected_items.append({
                            "name": item.get("item_name", "Unknown"),
                            "quantity": item.get("quantity", 1)
                        })

            # Analyze with AI
            analysis = await self._analyze_photo(delivery_photo, expected_items)

            match_score = analysis.get("match_score", 0.5)
            detected_items = analysis.get("detected_items", [])
            issues = analysis.get("issues", [])
            status = "verified" if match_score >= self.match_threshold else "issues_found"

            # Auto-credit if issues found
            auto_credited = False
            credit_amount = 0
            if status == "issues_found" and customer_id:
                credit_amount = min(float(order.get("total_amount", 5)), 10.0)
                await self._auto_credit_customer(customer_id, credit_amount, order_id)
                auto_credited = True

            return await self._save_verification(
                order_id, website_id, delivery_photo, expected_items,
                detected_items, match_score, status, issues, customer_id,
                analysis.get("summary", ""),
                auto_credited, credit_amount
            )

        except Exception as e:
            logger.error(f"Error verifying order {order_id}: {e}")
            return {"error": f"Ralat pengesahan: {str(e)}"}

    async def _analyze_photo(self, photo_url: str, expected_items: List[Dict]) -> Dict:
        """Analyze delivery photo using Qwen VL."""
        try:
            if not self.qwen_key:
                # Fallback without AI
                return {
                    "match_score": 0.8,
                    "detected_items": expected_items,
                    "issues": [],
                    "summary": "Analisis AI tidak tersedia - pengesahan manual diperlukan"
                }

            items_text = "\n".join([f"- {item['name']} x{item['quantity']}" for item in expected_items])

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.qwen_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.qwen_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "qwen-vl-max",
                        "messages": [
                            {
                                "role": "system",
                                "content": """You are a food delivery verification AI. Analyze the delivery photo and compare it against the expected order items.
Return a JSON object with:
- match_score: 0.0 to 1.0 (how well the delivery matches the order)
- detected_items: list of items you can see in the photo
- issues: list of any discrepancies (missing items, wrong items, etc.)
- summary: brief summary in Bahasa Melayu"""
                            },
                            {
                                "role": "user",
                                "content": [
                                    {"type": "image_url", "image_url": {"url": photo_url}},
                                    {"type": "text", "text": f"Item pesanan yang sepatutnya:\n{items_text}\n\nSemak sama ada foto penghantaran ini sepadan dengan pesanan."}
                                ]
                            }
                        ],
                        "max_tokens": 500
                    }
                )

                if response.status_code == 200:
                    data = response.json()
                    content = data["choices"][0]["message"]["content"]
                    # Try to parse JSON from response
                    import json
                    try:
                        # Find JSON in response
                        start = content.find("{")
                        end = content.rfind("}") + 1
                        if start >= 0 and end > start:
                            return json.loads(content[start:end])
                    except json.JSONDecodeError:
                        pass
                    return {
                        "match_score": 0.7,
                        "detected_items": expected_items,
                        "issues": [],
                        "summary": content[:200]
                    }

        except Exception as e:
            logger.error(f"Error analyzing photo: {e}")

        return {
            "match_score": 0.8,
            "detected_items": expected_items,
            "issues": [],
            "summary": "Analisis automatik gagal - semakan manual diperlukan"
        }

    async def _save_verification(
        self, order_id, website_id, photo_url, expected, detected,
        score, status, issues, customer_id, summary,
        auto_credited=False, credit_amount=0
    ) -> Dict:
        """Save verification result to database."""
        try:
            import json
            data = {
                "order_id": order_id,
                "website_id": website_id,
                "delivery_photo_url": photo_url,
                "expected_items": json.dumps(expected) if isinstance(expected, list) else expected,
                "detected_items": json.dumps(detected) if isinstance(detected, list) else detected,
                "match_score": score,
                "verification_status": status,
                "issues_found": json.dumps(issues) if isinstance(issues, list) else issues,
                "auto_credited": auto_credited,
                "credit_amount": credit_amount,
                "customer_id": customer_id,
                "ai_analysis": summary,
                "model_used": "qwen-vl-max"
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.supabase_url}/rest/v1/order_verifications",
                    headers={**self.headers, "Prefer": "return=representation"},
                    json=data
                )

            if response.status_code in [200, 201]:
                result = response.json()
                return result[0] if isinstance(result, list) else result

            return data
        except Exception as e:
            logger.error(f"Error saving verification: {e}")
            return {"error": str(e)}

    async def _auto_credit_customer(self, customer_id: str, amount: float, order_id: str):
        """Auto-credit customer for order issues."""
        try:
            async with httpx.AsyncClient() as client:
                await client.post(
                    f"{self.supabase_url}/rest/v1/credit_transactions",
                    headers={**self.headers, "Prefer": "return=minimal"},
                    json={
                        "user_id": customer_id,
                        "amount": amount,
                        "transaction_type": "order_issue_refund",
                        "description": f"Pampasan isu pesanan #{order_id[:8]}",
                        "status": "completed"
                    }
                )

                balance_resp = await client.get(
                    f"{self.supabase_url}/rest/v1/bina_credits",
                    headers=self.headers,
                    params={"user_id": f"eq.{customer_id}", "select": "id,balance"}
                )

                if balance_resp.status_code == 200:
                    data = balance_resp.json()
                    if data:
                        new_bal = float(data[0].get("balance", 0)) + amount
                        await client.patch(
                            f"{self.supabase_url}/rest/v1/bina_credits",
                            headers={**self.headers, "Prefer": "return=minimal"},
                            params={"user_id": f"eq.{customer_id}"},
                            json={"balance": new_bal}
                        )
                    else:
                        await client.post(
                            f"{self.supabase_url}/rest/v1/bina_credits",
                            headers={**self.headers, "Prefer": "return=minimal"},
                            json={"user_id": customer_id, "balance": amount}
                        )

            logger.info(f"Auto-credited RM{amount} to customer {customer_id}")
        except Exception as e:
            logger.error(f"Error auto-crediting: {e}")

    async def get_verification(self, order_id: str) -> Optional[Dict]:
        """Get verification result for an order."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.supabase_url}/rest/v1/order_verifications",
                    headers=self.headers,
                    params={"order_id": f"eq.{order_id}", "select": "*", "order": "created_at.desc", "limit": "1"}
                )
            if response.status_code == 200 and response.json():
                return response.json()[0]
            return None
        except Exception as e:
            logger.error(f"Error getting verification: {e}")
            return None

    async def get_recent_verifications(self, website_id: str, limit: int = 20) -> List[Dict]:
        """Get recent verifications for a website."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.supabase_url}/rest/v1/order_verifications",
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
            logger.error(f"Error getting recent verifications: {e}")
            return []


ai_order_verifier = AIOrderVerifier()
