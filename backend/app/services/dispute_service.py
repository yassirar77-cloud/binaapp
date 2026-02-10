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

    # =====================================================
    # AI AUTO-REPLY GENERATION
    # =====================================================

    AI_REPLY_SYSTEM_PROMPT = (
        "You are BinaApp AI, a professional and empathetic customer service representative "
        "for BinaApp, a Malaysian food delivery and restaurant platform. "
        "You communicate in a warm, solution-oriented manner following Malaysian business "
        "communication norms. You use polite language and show genuine concern for the customer. "
        "You are bilingual in Bahasa Malaysia and English. "
        "Always reply in the same language the customer used in their most recent message. "
        "If unsure, default to Bahasa Malaysia. "
        "Keep responses concise (2-4 paragraphs max). "
        "Never make promises you cannot keep. "
        "Always remind customers they can request to speak with a human operator."
    )

    AI_OWNER_SUPPORT_PROMPT = (
        "You are BinaApp Support AI. You help restaurant owners who have complaints "
        "about the BinaApp platform. You are responding to the restaurant OWNER, not a customer. "
        "Respond in the same language the owner used. If unsure, default to Bahasa Melayu. "
        "Be professional, empathetic, and helpful. "
        "You can: acknowledge their issue, provide troubleshooting steps, explain how BinaApp "
        "features work, promise to escalate to admin if needed. "
        "Keep responses short and helpful (2-4 sentences). "
        "Do NOT promise things you cannot deliver. "
        "If the issue is serious (payment problems, data loss), recommend escalation to admin. "
        "Sign off as 'BinaApp Support'."
    )

    async def generate_ai_reply(
        self,
        dispute_id: str,
        trigger_type: str,
        dispute_data: Dict[str, Any],
        conversation_history: Optional[List[Dict[str, Any]]] = None,
        customer_message: Optional[str] = None,
    ) -> Optional[str]:
        """
        Generate an AI auto-reply for a dispute.

        Args:
            dispute_id: The dispute UUID
            trigger_type: One of 'creation', 'customer_message', 'escalation', 'owner_complaint'
            dispute_data: Full dispute record from DB
            conversation_history: List of previous messages in the dispute
            customer_message: The latest customer/owner message

        Returns:
            The generated reply text, or None if generation failed
        """
        try:
            prompt = self._build_reply_prompt(
                trigger_type, dispute_data, conversation_history, customer_message
            )

            # Use owner support system prompt for owner complaints
            system_prompt = (
                self.AI_OWNER_SUPPORT_PROMPT
                if trigger_type == "owner_complaint"
                else self.AI_REPLY_SYSTEM_PROMPT
            )

            # Try DeepSeek first
            reply = None
            if self.deepseek_api_key:
                reply = await self._generate_reply_with_deepseek(prompt, system_prompt)

            # Fallback to Anthropic
            if not reply and self.anthropic_api_key:
                reply = await self._generate_reply_with_anthropic(prompt, system_prompt)

            # Fallback to template-based reply
            if not reply:
                reply = self._generate_template_reply(
                    trigger_type, dispute_data
                )

            return reply

        except Exception as e:
            logger.error(f"Failed to generate AI reply for dispute {dispute_id}: {e}")
            return self._generate_template_reply(trigger_type, dispute_data)

    def _build_reply_prompt(
        self,
        trigger_type: str,
        dispute_data: Dict[str, Any],
        conversation_history: Optional[List[Dict[str, Any]]] = None,
        customer_message: Optional[str] = None,
    ) -> str:
        """Build the prompt for AI reply generation based on trigger type."""
        category = dispute_data.get("category", "other")
        description = dispute_data.get("description", "")
        evidence_analysis = dispute_data.get("evidence_analysis") or {}
        severity = evidence_analysis.get("severity_score", dispute_data.get("ai_severity_score", 5))
        recommendation = evidence_analysis.get(
            "recommended_resolution",
            dispute_data.get("ai_decision", "escalated"),
        )
        reasoning = evidence_analysis.get(
            "reasoning", dispute_data.get("ai_reasoning", "")
        )
        dispute_number = dispute_data.get("dispute_number", "N/A")
        status = dispute_data.get("status", "open")

        # Build conversation context
        convo_context = ""
        if conversation_history:
            convo_lines = []
            for msg in conversation_history[-10:]:  # Last 10 messages for context
                sender = msg.get("sender_name") or msg.get("sender_type", "unknown")
                convo_lines.append(f"[{sender}]: {msg.get('message', '')}")
            convo_context = "\n".join(convo_lines)

        if trigger_type == "creation":
            return f"""A new dispute has been created. Generate an initial AI response to the customer.

Dispute #{dispute_number}
Category: {category.replace('_', ' ').title()}
Customer's complaint: {description}
AI Analysis - Severity: {severity}/10
AI Analysis - Recommendation: {recommendation}
AI Analysis - Reasoning: {reasoning}

Instructions:
- Acknowledge the customer's complaint empathetically
- Explain what the AI analysis found (severity level and recommendation) in simple terms
- If recommendation is 'approved': Explain the resolution (refund/replacement) and that it will be processed within 1-3 business days
- If recommendation is 'rejected': Explain politely why the claim could not be approved and suggest next steps (provide more evidence, contact support)
- If recommendation is 'partial': Explain the partial resolution and why
- If recommendation is 'escalated': Explain that the case needs human review and give estimated response time
- Always mention they can request escalation to a human operator at any time
- Reply in Bahasa Malaysia (default for new disputes)
- Sign off as "BinaApp AI"
"""

        elif trigger_type == "customer_message":
            return f"""A customer has sent a new message in an existing dispute. Generate a contextual AI reply.

Dispute #{dispute_number}
Category: {category.replace('_', ' ').title()}
Original complaint: {description}
Current status: {status}
AI Analysis - Severity: {severity}/10
AI Analysis - Recommendation: {recommendation}
AI Analysis - Reasoning: {reasoning}

Conversation history:
{convo_context}

Latest customer message: {customer_message or '(no message)'}

Instructions:
- Reply contextually based on what the customer is asking or saying
- Reference the original dispute context when relevant
- If the customer is asking for an update, provide the current status
- If the customer provides new information/evidence, acknowledge it and explain it will be reviewed
- If the customer is frustrated, be extra empathetic and offer escalation
- Reply in the SAME LANGUAGE the customer used in their latest message
- Keep it conversational and helpful
- Sign off as "BinaApp AI"
"""

        elif trigger_type == "escalation":
            return f"""A dispute has been escalated to human review. Generate an escalation notification message to the customer.

Dispute #{dispute_number}
Category: {category.replace('_', ' ').title()}
Original complaint: {description}

Conversation history:
{convo_context}

Instructions:
- Inform the customer that their case has been escalated to a human operator
- Explain that a human representative will review their case
- Give an estimated response time of 1-2 business days (hari bekerja)
- Reassure them that their case is being taken seriously
- Thank them for their patience
- Reply in Bahasa Malaysia
- Sign off as "BinaApp AI"
"""

        elif trigger_type == "owner_complaint":
            return f"""A restaurant owner has sent a new message in a complaint against the BinaApp platform. Generate a support reply.

Dispute #{dispute_number}
Category: {category.replace('_', ' ').title()}
Original complaint: {description}
Current status: {status}

Conversation history:
{convo_context}

Latest owner message: {customer_message or '(no message)'}

Instructions:
- You are BinaApp Support replying to a restaurant OWNER who has a complaint about the platform
- Reply contextually based on what the owner is saying
- Acknowledge their issue and provide helpful troubleshooting steps if applicable
- If the issue is serious (payment, data loss), recommend escalation to admin
- Reply in the SAME LANGUAGE the owner used in their latest message
- Keep it short (2-4 sentences) and helpful
- Sign off as "BinaApp Support"
"""

        return f"Generate a helpful customer service reply for dispute #{dispute_number} about {category}."

    async def _generate_reply_with_deepseek(
        self, prompt: str, system_prompt: Optional[str] = None
    ) -> Optional[str]:
        """Generate reply using DeepSeek API."""
        try:
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
                            {"role": "system", "content": system_prompt or self.AI_REPLY_SYSTEM_PROMPT},
                            {"role": "user", "content": prompt},
                        ],
                        "temperature": 0.6,
                        "max_tokens": 800,
                    },
                )

                if response.status_code == 200:
                    data = response.json()
                    return data["choices"][0]["message"]["content"].strip()

        except Exception as e:
            logger.warning(f"DeepSeek reply generation failed: {e}")

        return None

    async def _generate_reply_with_anthropic(
        self, prompt: str, system_prompt: Optional[str] = None
    ) -> Optional[str]:
        """Generate reply using Anthropic Claude API as fallback."""
        try:
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
                        "max_tokens": 800,
                        "messages": [
                            {"role": "user", "content": prompt},
                        ],
                        "system": system_prompt or self.AI_REPLY_SYSTEM_PROMPT,
                    },
                )

                if response.status_code == 200:
                    data = response.json()
                    return data["content"][0]["text"].strip()

        except Exception as e:
            logger.warning(f"Anthropic reply generation failed: {e}")

        return None

    def _generate_template_reply(
        self,
        trigger_type: str,
        dispute_data: Dict[str, Any],
    ) -> str:
        """Generate a template-based reply when AI APIs are unavailable."""
        category = dispute_data.get("category", "other")
        dispute_number = dispute_data.get("dispute_number", "N/A")
        evidence_analysis = dispute_data.get("evidence_analysis") or {}
        recommendation = evidence_analysis.get(
            "recommended_resolution",
            dispute_data.get("ai_decision", "escalated"),
        )

        if trigger_type == "creation":
            base_response = self._get_default_response(category)

            if recommendation in ("approved",):
                resolution_note = (
                    "Berdasarkan analisis kami, aduan anda telah diluluskan. "
                    "Bayaran balik akan diproses dalam masa 1-3 hari bekerja."
                )
            elif recommendation in ("rejected",):
                resolution_note = (
                    "Setelah semakan, kami memerlukan maklumat tambahan untuk memproses aduan anda. "
                    "Sila berikan bukti tambahan jika ada."
                )
            elif recommendation in ("partial",):
                resolution_note = (
                    "Berdasarkan analisis kami, bayaran balik separa akan diproses. "
                    "Kami akan menghubungi anda dengan butiran lanjut."
                )
            else:
                resolution_note = (
                    "Aduan anda sedang disemak oleh pasukan kami. "
                    "Kami akan memberikan maklum balas dalam masa 1-2 hari bekerja."
                )

            return (
                f"Terima kasih kerana menghubungi kami mengenai aduan #{dispute_number}.\n\n"
                f"{base_response}\n\n"
                f"{resolution_note}\n\n"
                f"Jika anda ingin bercakap dengan wakil manusia, sila maklumkan kami.\n\n"
                f"- BinaApp AI"
            )

        elif trigger_type == "customer_message":
            return (
                f"Terima kasih atas mesej anda mengenai aduan #{dispute_number}. "
                f"Kami telah menerima mesej anda dan sedang menyemaknya. "
                f"Kami akan memberikan maklum balas secepat mungkin.\n\n"
                f"Jika anda ingin bercakap dengan wakil manusia, sila maklumkan kami.\n\n"
                f"- BinaApp AI"
            )

        elif trigger_type == "escalation":
            return (
                f"Aduan #{dispute_number} anda telah dinaik taraf kepada pasukan sokongan manusia kami. "
                f"Wakil kami akan menyemak kes anda dan menghubungi anda dalam masa 1-2 hari bekerja.\n\n"
                f"Terima kasih atas kesabaran anda. Kami mengambil serius setiap aduan pelanggan.\n\n"
                f"- BinaApp AI"
            )

        elif trigger_type == "owner_complaint":
            return (
                f"Terima kasih atas mesej anda mengenai aduan #{dispute_number}. "
                f"Kami telah menerima maklum balas anda dan pasukan kami sedang menyemaknya. "
                f"Kami akan memberikan penyelesaian secepat mungkin.\n\n"
                f"Jika masalah ini mendesak, sila maklumkan kami untuk eskalasi kepada admin.\n\n"
                f"- BinaApp Support"
            )

        return (
            f"Terima kasih kerana menghubungi kami. Aduan #{dispute_number} anda "
            f"sedang diproses. Kami akan maklumkan anda sebarang perkembangan.\n\n"
            f"- BinaApp AI"
        )

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
