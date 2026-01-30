"""
AI Email Support Service for BinaApp
Uses Claude AI to automatically respond to customer support emails
"""
import os
import re
import json
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timedelta
from decimal import Decimal
from loguru import logger

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    logger.warning("anthropic package not installed. AI email support will be disabled.")

from app.core.config import settings
from app.services.email_service import email_service
from app.services.supabase_client import get_supabase_client


class AIEmailSupportService:
    """AI-powered email support service using Claude"""

    # Keywords that trigger automatic escalation
    ESCALATION_KEYWORDS = [
        "refund", "bayar balik", "pulangan wang",
        "cancel subscription", "batal langganan",
        "legal", "lawyer", "peguam", "mahkamah", "court",
        "scam", "penipuan", "fraud",
        "police", "polis", "report",
        "sue", "saman",
        "compensation", "pampasan",
        "urgent", "emergency", "kecemasan",
        "not working", "tidak berfungsi",
        "money lost", "wang hilang",
        "hack", "hacked", "digodam"
    ]

    # Category detection keywords
    CATEGORY_KEYWORDS = {
        "account": ["login", "password", "kata laluan", "akaun", "account", "register", "daftar", "email", "verification"],
        "billing": ["payment", "bayaran", "invoice", "invois", "subscription", "langganan", "charge", "caj", "refund", "toyyibpay"],
        "menu": ["menu", "item", "makanan", "food", "price", "harga", "category", "kategori", "image", "gambar"],
        "orders": ["order", "pesanan", "delivery", "penghantaran", "status", "tracking", "rider"],
        "website": ["website", "laman web", "domain", "subdomain", "design", "template", "publish"],
        "technical": ["error", "bug", "crash", "slow", "loading", "not working", "tidak berfungsi", "masalah"],
        "delivery": ["delivery", "penghantaran", "rider", "gps", "tracking", "location", "lokasi"],
        "chat": ["chat", "message", "mesej", "binachat", "conversation"]
    }

    def __init__(self):
        """Initialize the AI Email Support Service"""
        self.client = None
        self.knowledge_base = ""
        self.model = settings.ANTHROPIC_MODEL
        self.enabled = settings.AI_EMAIL_SUPPORT_ENABLED
        self.confidence_threshold = settings.AI_CONFIDENCE_THRESHOLD

        # Initialize Claude client if available
        if ANTHROPIC_AVAILABLE and settings.ANTHROPIC_API_KEY:
            try:
                self.client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
                logger.info("Claude AI client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Claude client: {e}")
                self.client = None

        # Load knowledge base
        self._load_knowledge_base()

    def _load_knowledge_base(self):
        """Load the support FAQ knowledge base"""
        try:
            kb_path = Path(__file__).parent.parent.parent / "knowledge_base" / "support_faq.md"
            if kb_path.exists():
                self.knowledge_base = kb_path.read_text(encoding="utf-8")
                logger.info(f"Knowledge base loaded: {len(self.knowledge_base)} characters")
            else:
                logger.warning(f"Knowledge base not found at {kb_path}")
                self.knowledge_base = ""
        except Exception as e:
            logger.error(f"Failed to load knowledge base: {e}")
            self.knowledge_base = ""

    def is_available(self) -> bool:
        """Check if AI email support is available and enabled"""
        return bool(self.client and self.enabled and self.knowledge_base)

    async def analyze_email(self, email_content: str, subject: str, sender_email: str) -> Dict[str, Any]:
        """
        Analyze incoming email for sentiment, urgency, and category

        Returns:
            Dict with keys: sentiment, urgency, category, escalation_reasons, confidence
        """
        if not self.is_available():
            return {
                "sentiment": "neutral",
                "urgency": "normal",
                "category": "general",
                "escalation_reasons": ["AI service unavailable"],
                "confidence": 0.0,
                "should_escalate": True
            }

        # Check for escalation keywords first
        content_lower = (email_content + " " + subject).lower()
        detected_keywords = [kw for kw in self.ESCALATION_KEYWORDS if kw in content_lower]

        # Detect category based on keywords
        category = self._detect_category(content_lower)

        try:
            # Use Claude to analyze the email
            analysis_prompt = f"""Analyze this customer support email and provide a JSON response with the following fields:
- sentiment: one of "positive", "neutral", "negative", "angry"
- urgency: one of "low", "normal", "high", "urgent"
- confidence: a number between 0 and 1 indicating how confident you are in understanding the request
- summary: a brief 1-2 sentence summary of what the customer needs

Email Subject: {subject}
Email From: {sender_email}
Email Content:
{email_content}

Respond ONLY with valid JSON, no other text."""

            response = self.client.messages.create(
                model=self.model,
                max_tokens=500,
                messages=[{"role": "user", "content": analysis_prompt}]
            )

            # Parse the response
            response_text = response.content[0].text.strip()
            # Clean up response if it has markdown code blocks
            if response_text.startswith("```"):
                response_text = re.sub(r"```json?\n?", "", response_text)
                response_text = response_text.replace("```", "").strip()

            analysis = json.loads(response_text)

            # Determine if we should escalate
            escalation_reasons = []
            should_escalate = False

            # Check confidence threshold
            confidence = float(analysis.get("confidence", 0.5))
            if confidence < self.confidence_threshold:
                escalation_reasons.append(f"Low confidence: {confidence:.2f}")
                should_escalate = True

            # Check sentiment
            sentiment = analysis.get("sentiment", "neutral")
            if sentiment in ["angry", "negative"]:
                escalation_reasons.append(f"Negative sentiment detected: {sentiment}")
                should_escalate = True

            # Check urgency
            urgency = analysis.get("urgency", "normal")
            if urgency == "urgent":
                escalation_reasons.append("Urgent request")
                should_escalate = True

            # Check escalation keywords
            if detected_keywords:
                escalation_reasons.append(f"Escalation keywords: {', '.join(detected_keywords[:5])}")
                should_escalate = True

            return {
                "sentiment": sentiment,
                "urgency": urgency,
                "category": category,
                "escalation_reasons": escalation_reasons,
                "confidence": confidence,
                "should_escalate": should_escalate,
                "detected_keywords": detected_keywords,
                "summary": analysis.get("summary", "")
            }

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI analysis response: {e}")
            return {
                "sentiment": "neutral",
                "urgency": "normal",
                "category": category,
                "escalation_reasons": ["Failed to analyze email"],
                "confidence": 0.3,
                "should_escalate": True,
                "detected_keywords": detected_keywords
            }
        except Exception as e:
            logger.error(f"Error analyzing email: {e}")
            return {
                "sentiment": "neutral",
                "urgency": "normal",
                "category": category,
                "escalation_reasons": [f"Analysis error: {str(e)}"],
                "confidence": 0.0,
                "should_escalate": True,
                "detected_keywords": detected_keywords
            }

    def _detect_category(self, content_lower: str) -> str:
        """Detect email category based on keywords"""
        category_scores = {}
        for category, keywords in self.CATEGORY_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in content_lower)
            if score > 0:
                category_scores[category] = score

        if category_scores:
            return max(category_scores, key=category_scores.get)
        return "general"

    async def generate_response(
        self,
        email_content: str,
        subject: str,
        sender_name: str,
        analysis: Dict[str, Any],
        conversation_history: Optional[List[Dict]] = None
    ) -> Tuple[str, float]:
        """
        Generate an AI response to the customer email

        Returns:
            Tuple of (response_text, confidence_score)
        """
        if not self.is_available():
            return ("", 0.0)

        # Build conversation context
        history_context = ""
        if conversation_history:
            history_context = "\n\nPrevious conversation:\n"
            for msg in conversation_history[-5:]:  # Last 5 messages
                sender = "Customer" if msg.get("sender_type") == "customer" else "Support"
                history_context += f"{sender}: {msg.get('content', '')[:500]}\n"

        system_prompt = f"""You are a helpful, professional, and friendly customer support agent for BinaApp, a digital restaurant platform in Malaysia.

Your role is to:
1. Help restaurant owners with their BinaApp accounts, websites, menus, orders, and subscriptions
2. Provide clear, step-by-step instructions when needed
3. Be empathetic and understanding
4. Use a mix of English and Bahasa Malaysia naturally (the customer may write in either language)
5. Keep responses concise but complete
6. Always sign off as "Pasukan Sokongan BinaApp" (BinaApp Support Team)

Important guidelines:
- For billing/refund issues, explain the process but mention that a human will follow up
- For technical issues, provide troubleshooting steps
- If you're unsure, be honest and say a specialist will help
- Never make up information not in the knowledge base
- Include relevant links to binaapp.my when helpful

Contact information:
- Support: support.team@binaapp.my
- Admin: admin@binaapp.my
- Website: https://binaapp.my

Here is the BinaApp knowledge base for reference:
{self.knowledge_base[:15000]}"""

        user_prompt = f"""Please respond to this customer support email:

From: {sender_name}
Subject: {subject}
Category: {analysis.get('category', 'general')}
{history_context}

Customer's message:
{email_content}

Write a helpful, professional response in the same language the customer used (English or Bahasa Malaysia). If they mixed languages, you may also mix languages naturally."""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1500,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}]
            )

            response_text = response.content[0].text.strip()
            confidence = analysis.get("confidence", 0.7)

            return (response_text, confidence)

        except Exception as e:
            logger.error(f"Error generating AI response: {e}")
            return ("", 0.0)

    async def should_escalate(
        self,
        analysis: Dict[str, Any],
        thread_id: Optional[str] = None
    ) -> Tuple[bool, List[str]]:
        """
        Determine if the email should be escalated to human support

        Returns:
            Tuple of (should_escalate, reasons)
        """
        reasons = analysis.get("escalation_reasons", [])
        should_escalate = analysis.get("should_escalate", False)

        # Check for repeated contact (multiple emails in short time)
        if thread_id:
            try:
                supabase = await get_supabase_client()
                # Count messages in the last hour
                one_hour_ago = (datetime.utcnow() - timedelta(hours=1)).isoformat()
                result = supabase.table("email_messages").select("id").eq(
                    "thread_id", thread_id
                ).eq(
                    "sender_type", "customer"
                ).gte(
                    "created_at", one_hour_ago
                ).execute()

                if result.data and len(result.data) >= 3:
                    reasons.append("Multiple emails in short time (3+ in 1 hour)")
                    should_escalate = True

                # Check if already escalated
                existing = supabase.table("ai_escalations").select("id").eq(
                    "thread_id", thread_id
                ).is_("resolved_at", "null").execute()

                if existing.data:
                    reasons.append("Thread already escalated")
                    should_escalate = True

            except Exception as e:
                logger.error(f"Error checking escalation history: {e}")

        return (should_escalate, reasons)

    async def send_reply(
        self,
        to_email: str,
        to_name: str,
        subject: str,
        content: str,
        thread_id: str
    ) -> bool:
        """Send the AI-generated reply via email"""
        try:
            # Format the HTML email
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background: #10b981; color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; }}
                    .content {{ background: #f9fafb; padding: 20px; border-radius: 0 0 8px 8px; white-space: pre-wrap; }}
                    .footer {{ text-align: center; margin-top: 20px; color: #666; font-size: 0.9em; padding: 20px; }}
                    .ref {{ font-size: 0.8em; color: #999; margin-top: 20px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h2>BinaApp Support</h2>
                    </div>
                    <div class="content">
                        {content.replace(chr(10), '<br>')}
                    </div>
                    <div class="footer">
                        <p>BinaApp - Platform Restoran Digital Malaysia</p>
                        <p>https://binaapp.my</p>
                        <p class="ref">Ref: {thread_id[:8]}</p>
                    </div>
                </div>
            </body>
            </html>
            """

            # Use the existing email service
            result = await email_service._send_email(
                to_email=to_email,
                subject=f"Re: {subject}",
                html_content=html_content,
                text_content=content,
                from_email=settings.SUPPORT_EMAIL,
                from_name="BinaApp Support",
                reply_to=settings.SUPPORT_EMAIL
            )

            if result:
                logger.info(f"AI reply sent to {to_email} for thread {thread_id}")
            else:
                logger.error(f"Failed to send AI reply to {to_email}")

            return result

        except Exception as e:
            logger.error(f"Error sending AI reply: {e}")
            return False

    async def notify_admin(
        self,
        thread_id: str,
        customer_email: str,
        customer_name: str,
        subject: str,
        escalation_reasons: List[str],
        email_content: str
    ) -> bool:
        """Notify admin about an escalated email"""
        try:
            reasons_html = "<ul>" + "".join(f"<li>{r}</li>" for r in escalation_reasons) + "</ul>"

            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background: #ef4444; color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; }}
                    .content {{ background: #f9fafb; padding: 20px; border-radius: 0 0 8px 8px; }}
                    .info-box {{ background: #fff; border: 1px solid #e5e7eb; padding: 15px; border-radius: 6px; margin: 15px 0; }}
                    .message-box {{ background: #fff; border-left: 4px solid #ef4444; padding: 15px; margin: 15px 0; white-space: pre-wrap; }}
                    .reasons {{ background: #fef2f2; border: 1px solid #fecaca; padding: 15px; border-radius: 6px; margin: 15px 0; }}
                    .action-btn {{ display: inline-block; padding: 10px 20px; background: #3b82f6; color: white; text-decoration: none; border-radius: 6px; margin: 5px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>Email Escalation Alert</h1>
                        <p>AI Support requires human intervention</p>
                    </div>
                    <div class="content">
                        <div class="info-box">
                            <p><strong>Thread ID:</strong> {thread_id}</p>
                            <p><strong>From:</strong> {customer_name} ({customer_email})</p>
                            <p><strong>Subject:</strong> {subject}</p>
                            <p><strong>Time:</strong> {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}</p>
                        </div>

                        <div class="reasons">
                            <strong>Escalation Reasons:</strong>
                            {reasons_html}
                        </div>

                        <p><strong>Customer Message:</strong></p>
                        <div class="message-box">
                            {email_content[:2000]}
                        </div>

                        <p style="text-align: center; margin-top: 20px;">
                            <a href="mailto:{customer_email}?subject=Re: {subject}" class="action-btn">Reply to Customer</a>
                        </p>
                    </div>
                </div>
            </body>
            </html>
            """

            result = await email_service._send_email(
                to_email=settings.ADMIN_EMAIL,
                subject=f"[ESCALATION] {subject} - from {customer_email}",
                html_content=html_content,
                text_content=f"Escalated email from {customer_name} ({customer_email})\n\nReasons: {', '.join(escalation_reasons)}\n\nMessage:\n{email_content[:2000]}",
                from_email=settings.NOREPLY_EMAIL,
                from_name="BinaApp AI Support"
            )

            if result:
                logger.info(f"Admin notified about escalation for thread {thread_id}")
            else:
                logger.error(f"Failed to notify admin about escalation")

            return result

        except Exception as e:
            logger.error(f"Error notifying admin: {e}")
            return False

    async def track_conversation(
        self,
        customer_email: str,
        customer_name: Optional[str],
        subject: str,
        message_content: str,
        sender_type: str,
        ai_generated: bool = False,
        ai_confidence: Optional[float] = None,
        thread_id: Optional[str] = None,
        analysis: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, str]:
        """
        Track email conversation in database

        Returns:
            Tuple of (thread_id, message_id)
        """
        try:
            supabase = await get_supabase_client()

            # Create or get thread
            if not thread_id:
                # Check for existing open thread from this email
                existing = supabase.table("email_threads").select("id").eq(
                    "customer_email", customer_email
                ).in_(
                    "status", ["open", "in_progress"]
                ).order(
                    "created_at", desc=True
                ).limit(1).execute()

                if existing.data:
                    thread_id = existing.data[0]["id"]
                else:
                    # Create new thread
                    priority = "normal"
                    category = "general"
                    status = "open"

                    if analysis:
                        if analysis.get("urgency") == "urgent":
                            priority = "urgent"
                        elif analysis.get("urgency") == "high":
                            priority = "high"
                        category = analysis.get("category", "general")
                        if analysis.get("should_escalate"):
                            status = "escalated"

                    thread_result = supabase.table("email_threads").insert({
                        "customer_email": customer_email,
                        "customer_name": customer_name,
                        "subject": subject,
                        "status": status,
                        "priority": priority,
                        "category": category
                    }).execute()

                    thread_id = thread_result.data[0]["id"]

            # Add message to thread
            message_data = {
                "thread_id": thread_id,
                "sender_email": customer_email if sender_type == "customer" else settings.SUPPORT_EMAIL,
                "sender_type": sender_type,
                "content": message_content,
                "ai_generated": ai_generated,
                "ai_model": self.model if ai_generated else None
            }

            if ai_confidence is not None:
                message_data["ai_confidence"] = ai_confidence

            message_result = supabase.table("email_messages").insert(message_data).execute()
            message_id = message_result.data[0]["id"]

            # Record escalation if needed
            if analysis and analysis.get("should_escalate"):
                escalation_type = "low_confidence"
                if analysis.get("detected_keywords"):
                    escalation_type = "keyword_trigger"
                elif analysis.get("sentiment") in ["angry", "negative"]:
                    escalation_type = "negative_sentiment"

                supabase.table("ai_escalations").insert({
                    "thread_id": thread_id,
                    "message_id": message_id,
                    "reason": "; ".join(analysis.get("escalation_reasons", ["Unknown"])),
                    "escalation_type": escalation_type,
                    "confidence_score": analysis.get("confidence"),
                    "detected_keywords": analysis.get("detected_keywords", [])
                }).execute()

                # Update thread status to escalated
                supabase.table("email_threads").update({
                    "status": "escalated",
                    "priority": "high" if analysis.get("urgency") != "urgent" else "urgent"
                }).eq("id", thread_id).execute()

            logger.info(f"Tracked message {message_id} in thread {thread_id}")
            return (thread_id, message_id)

        except Exception as e:
            logger.error(f"Error tracking conversation: {e}")
            raise

    async def process_incoming_email(
        self,
        sender_email: str,
        sender_name: Optional[str],
        subject: str,
        body: str,
        html_body: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process an incoming support email end-to-end

        Returns:
            Dict with processing results
        """
        result = {
            "success": False,
            "thread_id": None,
            "message_id": None,
            "ai_response_sent": False,
            "escalated": False,
            "error": None
        }

        try:
            # Use plain text body, strip HTML if only HTML provided
            email_content = body or ""
            if not email_content and html_body:
                # Basic HTML stripping
                email_content = re.sub(r'<[^>]+>', '', html_body)
                email_content = re.sub(r'\s+', ' ', email_content).strip()

            # Step 1: Analyze the email
            analysis = await self.analyze_email(email_content, subject, sender_email)
            logger.info(f"Email analysis: {analysis}")

            # Step 2: Track the incoming email
            thread_id, message_id = await self.track_conversation(
                customer_email=sender_email,
                customer_name=sender_name,
                subject=subject,
                message_content=email_content,
                sender_type="customer",
                analysis=analysis
            )
            result["thread_id"] = thread_id
            result["message_id"] = message_id

            # Step 3: Check if should escalate
            should_escalate, escalation_reasons = await self.should_escalate(analysis, thread_id)

            if should_escalate:
                result["escalated"] = True
                # Notify admin
                await self.notify_admin(
                    thread_id=thread_id,
                    customer_email=sender_email,
                    customer_name=sender_name or "Customer",
                    subject=subject,
                    escalation_reasons=escalation_reasons,
                    email_content=email_content
                )
                logger.info(f"Email escalated to human support: {escalation_reasons}")

            # Step 4: Generate and send AI response (even if escalated, send acknowledgment)
            if self.is_available():
                # Get conversation history
                supabase = await get_supabase_client()
                history_result = supabase.table("email_messages").select(
                    "sender_type", "content"
                ).eq(
                    "thread_id", thread_id
                ).order(
                    "created_at", desc=False
                ).limit(10).execute()

                conversation_history = history_result.data if history_result.data else []

                # Generate response
                ai_response, confidence = await self.generate_response(
                    email_content=email_content,
                    subject=subject,
                    sender_name=sender_name or "Customer",
                    analysis=analysis,
                    conversation_history=conversation_history
                )

                if ai_response and confidence >= 0.5:  # Only send if somewhat confident
                    # If escalated, add note about human follow-up
                    if should_escalate:
                        ai_response += "\n\n---\nNota: Mesej anda telah dimaklumkan kepada pasukan sokongan kami dan mereka akan menghubungi anda secepat mungkin.\n(Note: Your message has been forwarded to our support team and they will contact you as soon as possible.)"

                    # Send the reply
                    sent = await self.send_reply(
                        to_email=sender_email,
                        to_name=sender_name or "Customer",
                        subject=subject,
                        content=ai_response,
                        thread_id=thread_id
                    )

                    if sent:
                        result["ai_response_sent"] = True
                        # Track the AI response
                        await self.track_conversation(
                            customer_email=sender_email,
                            customer_name=sender_name,
                            subject=subject,
                            message_content=ai_response,
                            sender_type="ai",
                            ai_generated=True,
                            ai_confidence=confidence,
                            thread_id=thread_id
                        )

            result["success"] = True
            return result

        except Exception as e:
            logger.error(f"Error processing incoming email: {e}")
            result["error"] = str(e)
            return result

    async def get_settings(self) -> Dict[str, Any]:
        """Get current AI email support settings"""
        try:
            supabase = await get_supabase_client()
            result = supabase.table("email_support_settings").select("*").execute()

            settings_dict = {}
            for row in result.data:
                settings_dict[row["setting_key"]] = row["setting_value"]

            return settings_dict
        except Exception as e:
            logger.error(f"Error getting settings: {e}")
            return {}

    async def update_settings(self, updates: Dict[str, Any]) -> bool:
        """Update AI email support settings"""
        try:
            supabase = await get_supabase_client()

            for key, value in updates.items():
                supabase.table("email_support_settings").upsert({
                    "setting_key": key,
                    "setting_value": str(value),
                    "updated_at": datetime.utcnow().isoformat()
                }).execute()

            # Update local settings
            if "ai_enabled" in updates:
                self.enabled = updates["ai_enabled"].lower() == "true"
            if "confidence_threshold" in updates:
                self.confidence_threshold = float(updates["confidence_threshold"])

            return True
        except Exception as e:
            logger.error(f"Error updating settings: {e}")
            return False


# Create singleton instance
ai_email_support = AIEmailSupportService()
