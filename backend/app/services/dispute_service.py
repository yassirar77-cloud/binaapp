"""
AI Dispute Resolution Service for BinaApp
Provides AI-powered analysis and resolution recommendations for order disputes
"""

import os
import json
import httpx
from loguru import logger
from typing import Optional, Dict, Any, List
from datetime import datetime


class DisputeAIService:
    """AI-powered dispute analysis and resolution service"""

    # Category descriptions for AI context
    CATEGORY_DESCRIPTIONS = {
        "wrong_items": "Customer received incorrect items that differ from what was ordered",
        "missing_items": "Some items from the order were not delivered",
        "quality_issue": "Food quality is poor - cold, stale, undercooked, or not as described",
        "late_delivery": "Delivery arrived significantly later than the estimated time",
        "damaged_items": "Items arrived damaged, spilled, or in poor condition",
        "overcharged": "Customer was charged more than the expected order total",
        "never_delivered": "The order was never received by the customer",
        "rider_issue": "Problem with the delivery rider - rude, unprofessional, or other issues",
        "other": "Other issue not covered by standard categories",
    }

    # Severity guidelines per category
    SEVERITY_GUIDELINES = {
        "never_delivered": {"base": 9, "priority": "urgent"},
        "wrong_items": {"base": 7, "priority": "high"},
        "missing_items": {"base": 6, "priority": "high"},
        "overcharged": {"base": 7, "priority": "high"},
        "damaged_items": {"base": 6, "priority": "medium"},
        "quality_issue": {"base": 5, "priority": "medium"},
        "late_delivery": {"base": 4, "priority": "medium"},
        "rider_issue": {"base": 5, "priority": "medium"},
        "other": {"base": 3, "priority": "low"},
    }

    def __init__(self):
        self.deepseek_api_key = os.getenv("DEEPSEEK_API_KEY", "")
        self.anthropic_api_key = os.getenv("ANTHROPIC_API_KEY", "")

    async def analyze_dispute(
        self,
        category: str,
        description: str,
        order_amount: float,
        disputed_amount: Optional[float],
        order_details: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Analyze a dispute using AI and return resolution recommendations.

        Falls back to rule-based analysis if AI APIs are unavailable.
        """
        # Try AI-powered analysis first
        try:
            if self.deepseek_api_key:
                result = await self._analyze_with_deepseek(
                    category, description, order_amount, disputed_amount, order_details
                )
                if result:
                    return result
        except Exception as e:
            logger.warning(f"DeepSeek dispute analysis failed: {e}")

        try:
            if self.anthropic_api_key:
                result = await self._analyze_with_anthropic(
                    category, description, order_amount, disputed_amount, order_details
                )
                if result:
                    return result
        except Exception as e:
            logger.warning(f"Anthropic dispute analysis failed: {e}")

        # Fallback to rule-based analysis
        logger.info("Using rule-based dispute analysis (no AI API available)")
        return self._rule_based_analysis(
            category, description, order_amount, disputed_amount
        )

    async def _analyze_with_deepseek(
        self,
        category: str,
        description: str,
        order_amount: float,
        disputed_amount: Optional[float],
        order_details: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Use DeepSeek V3 for dispute analysis"""
        prompt = self._build_analysis_prompt(
            category, description, order_amount, disputed_amount, order_details
        )

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.deepseek.com/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.deepseek_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "deepseek-chat",
                    "messages": [
                        {
                            "role": "system",
                            "content": (
                                "You are an AI dispute resolution analyst for BinaApp, "
                                "a Malaysian food delivery platform. Analyze customer disputes "
                                "fairly and recommend resolutions. Always respond in valid JSON format."
                            ),
                        },
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.3,
                    "max_tokens": 1000,
                },
            )

            if response.status_code == 200:
                data = response.json()
                content = data["choices"][0]["message"]["content"]
                return self._parse_ai_response(content, category)

        return None

    async def _analyze_with_anthropic(
        self,
        category: str,
        description: str,
        order_amount: float,
        disputed_amount: Optional[float],
        order_details: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Use Claude as fallback for dispute analysis"""
        prompt = self._build_analysis_prompt(
            category, description, order_amount, disputed_amount, order_details
        )

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": self.anthropic_api_key,
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "claude-3-haiku-20240307",
                    "max_tokens": 1000,
                    "messages": [
                        {"role": "user", "content": prompt},
                    ],
                    "system": (
                        "You are an AI dispute resolution analyst for BinaApp, "
                        "a Malaysian food delivery platform. Analyze customer disputes "
                        "fairly and recommend resolutions. Always respond in valid JSON format."
                    ),
                },
            )

            if response.status_code == 200:
                data = response.json()
                content = data["content"][0]["text"]
                return self._parse_ai_response(content, category)

        return None

    def _build_analysis_prompt(
        self,
        category: str,
        description: str,
        order_amount: float,
        disputed_amount: Optional[float],
        order_details: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Build the prompt for AI dispute analysis"""
        category_desc = self.CATEGORY_DESCRIPTIONS.get(category, "Unknown category")

        order_info = ""
        if order_details:
            order_info = f"""
Order Details:
- Order Number: {order_details.get('order_number', 'N/A')}
- Items: {json.dumps(order_details.get('items', []))}
- Payment Method: {order_details.get('payment_method', 'N/A')}
- Order Status: {order_details.get('status', 'N/A')}
- Created: {order_details.get('created_at', 'N/A')}
- Delivered: {order_details.get('delivered_at', 'N/A')}
"""

        return f"""Analyze this customer dispute for a Malaysian food delivery order and respond with a JSON object.

Dispute Category: {category} ({category_desc})
Customer Description: {description}
Order Amount: RM {order_amount:.2f}
Disputed Amount: RM {(disputed_amount if disputed_amount is not None else order_amount):.2f}
{order_info}

Respond with ONLY a valid JSON object (no markdown, no extra text):
{{
    "category_confidence": <float 0.0-1.0, how confident the category matches>,
    "severity_score": <int 1-10>,
    "recommended_resolution": <one of: "full_refund", "partial_refund", "replacement", "credit", "apology", "rejected">,
    "recommended_refund_percentage": <int 0-100, percentage of order to refund>,
    "priority": <one of: "low", "medium", "high", "urgent">,
    "reasoning": "<brief explanation of your analysis in English>",
    "suggested_response": "<a polite response to send to the customer in Bahasa Malaysia>",
    "risk_flags": [<list of any risk flags like "repeat_complaint", "high_value", "potential_fraud">]
}}"""

    def _map_severity_score_to_level(self, severity_score: int) -> str:
        """Map integer severity score (1-10) to valid severity text level."""
        score = max(1, min(10, int(severity_score)))
        if score <= 3:
            return 'minor'
        elif score <= 5:
            return 'medium'
        elif score <= 7:
            return 'major'
        else:
            return 'critical'

    def _map_to_valid_decision(self, ai_recommendation: str) -> str:
        """Map any AI recommendation to a valid ai_decision value."""
        VALID = {'approved', 'rejected', 'partial', 'escalated'}

        MAP = {
            # Negative responses
            'apology': 'rejected',
            'deny': 'rejected',
            'reject': 'rejected',
            'rejected': 'rejected',
            'decline': 'rejected',
            'inappropriate': 'rejected',
            'invalid': 'rejected',
            'no_action': 'rejected',
            # Positive responses
            'refund': 'approved',
            'full_refund': 'approved',
            'credit': 'approved',
            'approve': 'approved',
            'approved': 'approved',
            'compensate': 'approved',
            'replacement': 'approved',
            # Partial
            'partial_refund': 'partial',
            'partial_credit': 'partial',
            'partial': 'partial',
            # Escalate
            'escalate': 'escalated',
            'escalated': 'escalated',
            'investigate': 'escalated',
            'review': 'escalated',
        }

        mapped = MAP.get(ai_recommendation.lower().strip(), None)
        if mapped and mapped in VALID:
            return mapped
        return 'escalated'  # safe fallback

    def _parse_ai_response(
        self, content: str, category: str
    ) -> Optional[Dict[str, Any]]:
        """Parse AI response into structured analysis"""
        try:
            # Try to extract JSON from response
            content = content.strip()
            # Remove markdown code blocks if present
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
                content = content.strip()

            analysis = json.loads(content)

            # Validate and normalize fields
            raw_resolution = analysis.get("recommended_resolution", "partial_refund")
            result = {
                "category_confidence": min(
                    1.0, max(0.0, float(analysis.get("category_confidence", 0.5)))
                ),
                "severity_score": min(
                    10, max(1, int(analysis.get("severity_score", 5)))
                ),
                "recommended_resolution": self._map_to_valid_decision(str(raw_resolution)),
                "recommended_refund_percentage": analysis.get(
                    "recommended_refund_percentage"
                ),
                "priority": analysis.get("priority", "medium"),
                "reasoning": analysis.get("reasoning", ""),
                "suggested_response": analysis.get("suggested_response", ""),
                "risk_flags": analysis.get("risk_flags", []),
                "similar_dispute_pattern": analysis.get(
                    "similar_dispute_pattern", False
                ),
                "analysis_source": "ai",
            }

            logger.info(
                f"AI dispute analysis complete: severity={result['severity_score']}, "
                f"recommendation={result['recommended_resolution']}"
            )
            return result

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning(f"Failed to parse AI response: {e}")
            return None

    def _rule_based_analysis(
        self,
        category: str,
        description: str,
        order_amount: float,
        disputed_amount: Optional[float],
    ) -> Dict[str, Any]:
        """Rule-based dispute analysis fallback"""
        guidelines = self.SEVERITY_GUIDELINES.get(
            category, {"base": 3, "priority": "low"}
        )

        severity = guidelines["base"]
        priority = guidelines["priority"]

        # Adjust severity based on order amount
        if order_amount > 100:
            severity = min(10, severity + 1)
            if priority == "medium":
                priority = "high"

        # Determine resolution recommendation
        if category in ("never_delivered", "wrong_items"):
            resolution = "full_refund"
            refund_pct = 100
        elif category in ("missing_items", "damaged_items"):
            resolution = "partial_refund"
            refund_pct = 50
        elif category in ("quality_issue", "late_delivery"):
            resolution = "partial_refund"
            refund_pct = 30
        elif category == "overcharged":
            resolution = "partial_refund"
            refund_pct = min(
                100,
                int(
                    ((disputed_amount or order_amount) / order_amount) * 100
                )
                if order_amount > 0
                else 50,
            )
        elif category == "rider_issue":
            resolution = "apology"
            refund_pct = 0
        else:
            resolution = "partial_refund"
            refund_pct = 20

        suggested_response = self._get_default_response(category)

        return {
            "category_confidence": 0.85,
            "severity_score": severity,
            "recommended_resolution": self._map_to_valid_decision(resolution),
            "recommended_refund_percentage": refund_pct,
            "priority": priority,
            "reasoning": (
                f"Rule-based analysis: Category '{category}' "
                f"with order amount RM{order_amount:.2f}. "
                f"Standard resolution applied."
            ),
            "suggested_response": suggested_response,
            "risk_flags": [],
            "similar_dispute_pattern": False,
            "analysis_source": "rules",
        }

    def _get_default_response(self, category: str) -> str:
        """Get default response template in Bahasa Malaysia"""
        responses = {
            "wrong_items": (
                "Kami memohon maaf atas kesilapan pesanan anda. "
                "Kami akan menyemak dan memproses bayaran balik dalam masa 1-3 hari bekerja."
            ),
            "missing_items": (
                "Kami memohon maaf kerana item yang hilang daripada pesanan anda. "
                "Kami akan memproses bayaran balik untuk item yang tidak diterima."
            ),
            "quality_issue": (
                "Kami memohon maaf atas kualiti makanan yang tidak memuaskan. "
                "Kami akan mengambil tindakan segera untuk memperbaiki masalah ini."
            ),
            "late_delivery": (
                "Kami memohon maaf atas kelewatan penghantaran. "
                "Kami sedang berusaha untuk meningkatkan perkhidmatan penghantaran kami."
            ),
            "damaged_items": (
                "Kami memohon maaf kerana pesanan anda rosak semasa penghantaran. "
                "Kami akan memproses bayaran balik untuk item yang rosak."
            ),
            "overcharged": (
                "Kami memohon maaf atas caj berlebihan. "
                "Kami akan menyemak dan membuat pembetulan segera."
            ),
            "never_delivered": (
                "Kami amat memohon maaf kerana pesanan anda tidak sampai. "
                "Kami akan memproses bayaran balik penuh dengan segera."
            ),
            "rider_issue": (
                "Kami memohon maaf atas pengalaman kurang memuaskan dengan penunggang kami. "
                "Kami akan mengambil tindakan yang sewajarnya."
            ),
            "other": (
                "Terima kasih kerana memaklumkan kami tentang masalah ini. "
                "Kami akan menyemak dan menghubungi anda secepat mungkin."
            ),
        }
        return responses.get(category, responses["other"])

    async def generate_resolution_summary(
        self, dispute_data: Dict[str, Any]
    ) -> str:
        """Generate a human-readable resolution summary"""
        category = dispute_data.get("category", "other")
        resolution = dispute_data.get("resolution_type", "pending")
        refund = dispute_data.get("refund_amount", 0)
        order_amount = dispute_data.get("order_amount", 0)

        summary_parts = [
            f"Dispute #{dispute_data.get('dispute_number', 'N/A')}",
            f"Category: {category.replace('_', ' ').title()}",
            f"Resolution: {resolution.replace('_', ' ').title()}",
        ]

        if refund and refund > 0:
            summary_parts.append(
                f"Refund: RM{refund:.2f} of RM{order_amount:.2f}"
            )

        return " | ".join(summary_parts)


# Singleton instance
dispute_ai_service = DisputeAIService()
