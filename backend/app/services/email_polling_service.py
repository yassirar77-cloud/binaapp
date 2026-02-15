"""
Email Polling Service for BinaApp
Polls IMAP inbox (Zoho Mail) for new support emails and processes them with AI
"""
import asyncio
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Set
from loguru import logger

try:
    from imap_tools import MailBox, MailMessage, AND, OR
    IMAP_TOOLS_AVAILABLE = True
except ImportError:
    IMAP_TOOLS_AVAILABLE = False
    logger.warning("imap-tools package not installed. Email polling will be disabled.")

try:
    import html2text
    HTML2TEXT_AVAILABLE = True
except ImportError:
    HTML2TEXT_AVAILABLE = False
    logger.warning("html2text package not installed. HTML emails will use basic parsing.")

from app.core.config import settings
from app.services.ai_email_support import ai_email_support
from app.services.supabase_client import get_supabase_client

# Timeout for IMAP operations (seconds)
IMAP_TIMEOUT = 30
# Maximum time for a single poll cycle (seconds)
POLL_TIMEOUT = 180


class EmailPollingService:
    """Service for polling IMAP inbox and processing emails with AI"""

    # Custom IMAP flags for tracking processed emails
    FLAG_PROCESSED_BY_AI = "PROCESSED_BY_AI"
    FLAG_ESCALATED = "ESCALATED"

    def __init__(self):
        """Initialize the Email Polling Service"""
        self.enabled = settings.EMAIL_POLLING_ENABLED
        self.polling_interval = settings.EMAIL_POLLING_INTERVAL_SECONDS
        self.imap_server = settings.IMAP_SERVER
        self.imap_port = settings.IMAP_PORT
        self.email = settings.SUPPORT_EMAIL
        self.password = settings.SUPPORT_EMAIL_PASSWORD

        # Polling state
        self.is_running = False
        self.last_poll_time: Optional[datetime] = None
        self.last_poll_status: str = "never_run"
        self.last_error: Optional[str] = None
        self.imap_connection_status: str = "disconnected"
        self.emails_processed_today: int = 0
        self.errors_today: List[Dict[str, Any]] = []
        self._processed_uids: Set[str] = set()  # Track processed email UIDs
        self._last_reset_date: Optional[datetime] = None

        # Rate limiting
        self._last_email_sent_time: Optional[datetime] = None
        self._min_email_interval_seconds: int = 5  # Minimum 5 seconds between sends

        logger.info("=" * 60)
        logger.info("EMAIL POLLING SERVICE INITIALIZATION")
        logger.info("=" * 60)
        logger.info(f"Enabled: {self.enabled}")
        logger.info(f"IMAP Server: {self.imap_server}:{self.imap_port}")
        logger.info(f"Email Account: {self.email}")
        logger.info(f"Polling Interval: {self.polling_interval} seconds")
        logger.info(f"Password configured: {'Yes' if self.password else 'NO - MISSING!'}")
        logger.info("=" * 60)

    def is_available(self) -> bool:
        """Check if email polling is available and properly configured"""
        if not IMAP_TOOLS_AVAILABLE:
            return False
        if not self.enabled:
            return False
        if not self.email or not self.password:
            return False
        if not self.imap_server or not self.imap_port:
            return False
        return True

    def _reset_daily_stats(self):
        """Reset daily statistics at midnight"""
        now = datetime.utcnow()
        if self._last_reset_date is None or self._last_reset_date.date() != now.date():
            self.emails_processed_today = 0
            self.errors_today = []
            self._last_reset_date = now
            logger.info("Daily email polling statistics reset")

    def _generate_email_hash(self, msg: Any) -> str:
        """Generate a unique hash for an email to prevent duplicate processing"""
        # Use message ID, subject, sender, and date to create a unique identifier
        unique_str = f"{msg.uid}:{msg.subject}:{msg.from_}:{msg.date}"
        return hashlib.md5(unique_str.encode()).hexdigest()

    def _extract_plain_text(self, msg: Any) -> str:
        """Extract plain text content from email message"""
        # Try to get plain text first
        if msg.text:
            return msg.text.strip()

        # Fall back to HTML parsing
        if msg.html:
            if HTML2TEXT_AVAILABLE:
                h = html2text.HTML2Text()
                h.ignore_links = False
                h.ignore_images = True
                h.body_width = 0  # Don't wrap text
                return h.handle(msg.html).strip()
            else:
                # Basic HTML stripping
                import re
                text = re.sub(r'<script[^>]*>.*?</script>', '', msg.html, flags=re.DOTALL | re.IGNORECASE)
                text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
                text = re.sub(r'<[^>]+>', ' ', text)
                text = re.sub(r'\s+', ' ', text)
                return text.strip()

        return ""

    def _extract_sender_name(self, from_address: str) -> tuple[str, str]:
        """Extract name and email from sender address"""
        # Format can be: "Name <email@domain.com>" or just "email@domain.com"
        import re
        match = re.match(r'^"?([^"<]+)"?\s*<([^>]+)>$', from_address)
        if match:
            name = match.group(1).strip().strip('"')
            email = match.group(2).strip()
            return name, email
        else:
            # Just an email address
            email = from_address.strip()
            name = email.split('@')[0]
            return name, email

    async def _rate_limit_check(self):
        """Ensure we don't send emails too quickly"""
        if self._last_email_sent_time:
            elapsed = (datetime.utcnow() - self._last_email_sent_time).total_seconds()
            if elapsed < self._min_email_interval_seconds:
                wait_time = self._min_email_interval_seconds - elapsed
                logger.debug(f"Rate limiting: waiting {wait_time:.1f} seconds before next email")
                await asyncio.sleep(wait_time)
        self._last_email_sent_time = datetime.utcnow()

    def _fetch_unseen_emails_sync(self) -> List[Dict[str, Any]]:
        """
        Synchronous IMAP fetch - runs in thread pool to avoid blocking event loop.
        Connects to IMAP, fetches unseen emails, extracts data, and disconnects.

        Returns:
            List of dicts with extracted email data
        """
        fetched = []
        mailbox = None
        try:
            logger.info(f"[IMAP] Connecting to {self.imap_server}:{self.imap_port} (timeout={IMAP_TIMEOUT}s)")
            self.imap_connection_status = "connecting"

            max_retries = 3
            for attempt in range(max_retries):
                try:
                    logger.info(f"[IMAP] Connection attempt {attempt + 1}/{max_retries}")
                    mailbox = MailBox(self.imap_server, self.imap_port, timeout=IMAP_TIMEOUT)
                    mailbox.login(self.email, self.password)
                    logger.info("[IMAP] LOGIN SUCCESSFUL!")
                    self.imap_connection_status = "connected"
                    break
                except Exception as conn_error:
                    logger.error(f"[IMAP] Connection attempt {attempt + 1} FAILED: {conn_error}")
                    self.imap_connection_status = "failed"
                    if mailbox:
                        try:
                            mailbox.logout()
                        except Exception:
                            pass
                        mailbox = None
                    if attempt < max_retries - 1:
                        import time
                        wait_time = 2 ** (attempt + 1)
                        logger.warning(f"[IMAP] Retrying in {wait_time}s...")
                        time.sleep(wait_time)
                    else:
                        raise conn_error

            mailbox.folder.set("INBOX")
            logger.info("[IMAP] Fetching unread emails (limit: 20)...")
            messages = list(mailbox.fetch(AND(seen=False), limit=20, reverse=True))
            logger.info(f"[IMAP] Found {len(messages)} unread emails")

            for msg in messages:
                # Extract all data from IMAP message while connection is open
                email_hash = self._generate_email_hash(msg)
                sender_name, sender_email = self._extract_sender_name(msg.from_)
                body_text = self._extract_plain_text(msg)
                html_body = msg.html if msg.html else None

                fetched.append({
                    "uid": msg.uid,
                    "subject": msg.subject or "(No Subject)",
                    "from": msg.from_,
                    "sender_name": sender_name,
                    "sender_email": sender_email,
                    "body_text": body_text,
                    "html_body": html_body,
                    "email_hash": email_hash,
                    "date": str(msg.date) if msg.date else None,
                })

        finally:
            if mailbox:
                try:
                    mailbox.logout()
                    self.imap_connection_status = "disconnected"
                except Exception as e:
                    logger.warning(f"[IMAP] Error closing fetch connection: {e}")

        return fetched

    def _mark_emails_in_imap_sync(self, uid_actions: List[Dict[str, Any]]):
        """
        Synchronous IMAP flag update - runs in thread pool.
        Reconnects to IMAP and applies flags for processed emails.
        """
        if not uid_actions:
            return

        mailbox = None
        try:
            mailbox = MailBox(self.imap_server, self.imap_port, timeout=IMAP_TIMEOUT)
            mailbox.login(self.email, self.password)
            mailbox.folder.set("INBOX")

            for action in uid_actions:
                uid = action["uid"]
                escalated = action.get("escalated", False)
                try:
                    if escalated:
                        # Keep unread for admin, try custom flag
                        mailbox.flag(uid, ['\\Seen'], False)
                        try:
                            mailbox.flag(uid, [self.FLAG_ESCALATED], True)
                        except Exception:
                            pass
                    else:
                        mailbox.flag(uid, ['\\Seen'], True)
                        try:
                            mailbox.flag(uid, [self.FLAG_PROCESSED_BY_AI], True)
                        except Exception:
                            pass
                except Exception as flag_err:
                    logger.warning(f"[IMAP] Could not flag UID {uid}: {flag_err}")

        except Exception as e:
            logger.warning(f"[IMAP] Failed to update flags: {e}")
        finally:
            if mailbox:
                try:
                    mailbox.logout()
                except Exception:
                    pass

    async def process_email_data(self, email_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a single email from extracted data (async-safe, no IMAP calls).

        Args:
            email_data: Dict with extracted email fields from _fetch_unseen_emails_sync

        Returns:
            Dict with processing results
        """
        result = {
            "success": False,
            "uid": email_data["uid"],
            "subject": email_data["subject"],
            "from": email_data["from"],
            "processed": False,
            "escalated": False,
            "error": None
        }

        try:
            email_hash = email_data["email_hash"]
            if email_hash in self._processed_uids:
                logger.info(f"Skipping already processed email: {email_data['subject']}")
                result["success"] = True
                result["processed"] = True
                return result

            sender_name = email_data["sender_name"]
            sender_email = email_data["sender_email"]

            # Skip self-emails to prevent loops
            if sender_email.lower() == self.email.lower():
                logger.debug(f"Skipping email from self: {email_data['subject']}")
                result["success"] = True
                return result

            # Skip noreply addresses
            if "noreply" in sender_email.lower() or "no-reply" in sender_email.lower():
                logger.debug(f"Skipping noreply email: {email_data['subject']}")
                result["success"] = True
                return result

            body_text = email_data["body_text"]
            html_body = email_data["html_body"]

            if not body_text and not html_body:
                logger.warning(f"Empty email body: {email_data['subject']}")
                result["error"] = "Empty email body"
                return result

            logger.info(f"Processing email from {sender_email}: {email_data['subject']}")

            # Apply rate limiting
            await self._rate_limit_check()

            # Process with AI email support (fully async)
            ai_result = await ai_email_support.process_incoming_email(
                sender_email=sender_email,
                sender_name=sender_name,
                subject=email_data["subject"],
                body=body_text,
                html_body=html_body
            )

            result["thread_id"] = ai_result.get("thread_id")
            result["ai_response_sent"] = ai_result.get("ai_response_sent", False)
            result["escalated"] = ai_result.get("escalated", False)

            # Track processed UID
            self._processed_uids.add(email_hash)
            if len(self._processed_uids) > 1000:
                self._processed_uids = set(list(self._processed_uids)[-500:])

            result["success"] = True
            result["processed"] = True
            self.emails_processed_today += 1

            logger.info(
                f"Email processed successfully: {email_data['subject']} | "
                f"AI Response: {result['ai_response_sent']} | "
                f"Escalated: {result['escalated']}"
            )

        except Exception as e:
            logger.error(f"Error processing email {email_data['uid']}: {e}")
            result["error"] = str(e)
            self.errors_today.append({
                "time": datetime.utcnow().isoformat(),
                "uid": email_data["uid"],
                "subject": email_data["subject"],
                "error": str(e)
            })
            if len(self.errors_today) > 50:
                self.errors_today = self.errors_today[-50:]

        return result

    async def poll_inbox(self) -> Dict[str, Any]:
        """
        Poll the IMAP inbox for new unread emails and process them.
        IMAP operations run in a thread pool to avoid blocking the event loop.

        Returns:
            Dict with polling results
        """
        poll_result = {
            "success": False,
            "started_at": datetime.utcnow().isoformat(),
            "completed_at": None,
            "emails_found": 0,
            "emails_processed": 0,
            "emails_escalated": 0,
            "errors": []
        }

        if not self.is_available():
            poll_result["error"] = "Email polling service not available"
            logger.warning("Email polling attempted but service not available")
            return poll_result

        self._reset_daily_stats()
        self.last_poll_time = datetime.utcnow()
        self.last_poll_status = "in_progress"
        self.last_error = None

        logger.info("=" * 60)
        logger.info("EMAIL POLLING - STARTING INBOX POLL")
        logger.info("=" * 60)
        logger.info(f"Poll started at: {self.last_poll_time.isoformat()}")

        try:
            # Step 1: Fetch emails via thread pool (non-blocking)
            logger.info("[POLL] Fetching emails from IMAP (in thread pool)...")
            fetched_emails = await asyncio.to_thread(self._fetch_unseen_emails_sync)
            poll_result["emails_found"] = len(fetched_emails)

            if not fetched_emails:
                logger.info("[EMAIL] No unread emails to process")
            else:
                logger.info(f"[EMAIL] Found {len(fetched_emails)} emails, starting processing...")

            # Step 2: Process each email asynchronously (AI + DB, no IMAP blocking)
            uid_actions = []
            for idx, email_data in enumerate(fetched_emails, 1):
                logger.info(f"[EMAIL {idx}/{len(fetched_emails)}] Processing: {email_data['subject']} | From: {email_data['from']}")
                try:
                    email_result = await self.process_email_data(email_data)
                    if email_result.get("processed"):
                        poll_result["emails_processed"] += 1
                        uid_actions.append({
                            "uid": email_data["uid"],
                            "escalated": email_result.get("escalated", False)
                        })
                    if email_result.get("escalated"):
                        poll_result["emails_escalated"] += 1
                    if email_result.get("error"):
                        poll_result["errors"].append({
                            "uid": email_data["uid"],
                            "error": email_result["error"]
                        })
                except Exception as email_error:
                    logger.error(f"Failed to process email {email_data['uid']}: {email_error}")
                    poll_result["errors"].append({
                        "uid": email_data["uid"],
                        "error": str(email_error)
                    })

            # Step 3: Mark processed emails in IMAP via thread pool (non-blocking)
            if uid_actions:
                logger.info(f"[IMAP] Marking {len(uid_actions)} emails as processed...")
                try:
                    await asyncio.to_thread(self._mark_emails_in_imap_sync, uid_actions)
                except Exception as flag_err:
                    logger.warning(f"[IMAP] Flag update failed (non-critical): {flag_err}")

            poll_result["success"] = True
            self.last_poll_status = "success"
            logger.info("[EMAIL] Polling completed successfully")

        except Exception as e:
            logger.error("=" * 60)
            logger.error("EMAIL POLLING - ERROR OCCURRED")
            logger.error("=" * 60)
            logger.error(f"Error polling inbox: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            poll_result["error"] = str(e)
            self.last_poll_status = "error"
            self.last_error = str(e)
            self.imap_connection_status = "error"
            self.errors_today.append({
                "time": datetime.utcnow().isoformat(),
                "error": f"Polling error: {str(e)}"
            })

        poll_result["completed_at"] = datetime.utcnow().isoformat()

        logger.info("=" * 60)
        logger.info("EMAIL POLLING - SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Status: {self.last_poll_status.upper()}")
        logger.info(f"Emails Found: {poll_result['emails_found']}")
        logger.info(f"Emails Processed: {poll_result['emails_processed']}")
        logger.info(f"Emails Escalated: {poll_result['emails_escalated']}")
        logger.info(f"Errors: {len(poll_result['errors'])}")
        logger.info(f"Total Processed Today: {self.emails_processed_today}")
        logger.info("=" * 60)

        return poll_result

    def get_status(self) -> Dict[str, Any]:
        """Get current status of the email polling service"""
        return {
            "is_available": self.is_available(),
            "is_running": self.is_running,
            "enabled": self.enabled,
            "last_poll_time": self.last_poll_time.isoformat() if self.last_poll_time else None,
            "last_poll_status": self.last_poll_status,
            "last_error": self.last_error,
            "imap_connection_status": self.imap_connection_status,
            "emails_processed_today": self.emails_processed_today,
            "errors_today_count": len(self.errors_today),
            "recent_errors": self.errors_today[-5:] if self.errors_today else [],
            "polling_interval_seconds": self.polling_interval,
            "imap_server": self.imap_server,
            "imap_port": self.imap_port,
            "email_account": self.email
        }

    def _test_connection_sync(self) -> Dict[str, Any]:
        """Synchronous IMAP connection test - runs in thread pool."""
        result = {
            "success": False,
            "message": "",
            "server": self.imap_server,
            "port": self.imap_port,
            "email": self.email
        }

        mailbox = None
        try:
            mailbox = MailBox(self.imap_server, self.imap_port, timeout=IMAP_TIMEOUT)
            mailbox.login(self.email, self.password)

            folder_status = mailbox.folder.status("INBOX")
            result["inbox_messages"] = folder_status.get("MESSAGES", 0)
            result["inbox_unseen"] = folder_status.get("UNSEEN", 0)

            result["success"] = True
            result["message"] = "Connection successful"

        except Exception as e:
            result["message"] = f"Connection failed: {str(e)}"

        finally:
            if mailbox:
                try:
                    mailbox.logout()
                except Exception:
                    pass

        return result

    async def test_connection(self) -> Dict[str, Any]:
        """Test IMAP connection without processing emails (non-blocking)."""
        if not IMAP_TOOLS_AVAILABLE:
            return {"success": False, "message": "imap-tools package not installed",
                    "server": self.imap_server, "port": self.imap_port, "email": self.email}

        if not self.email or not self.password:
            return {"success": False, "message": "Email credentials not configured",
                    "server": self.imap_server, "port": self.imap_port, "email": self.email}

        try:
            return await asyncio.wait_for(
                asyncio.to_thread(self._test_connection_sync),
                timeout=IMAP_TIMEOUT + 10
            )
        except asyncio.TimeoutError:
            return {"success": False, "message": f"Connection timed out after {IMAP_TIMEOUT + 10}s",
                    "server": self.imap_server, "port": self.imap_port, "email": self.email}


# Create singleton instance
email_polling_service = EmailPollingService()
