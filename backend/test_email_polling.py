#!/usr/bin/env python3
"""
Test Script for Email Polling Service

This script tests the email polling functionality:
1. Tests IMAP connection to Zoho Mail
2. Tests email parsing
3. Tests AI response generation
4. Tests manual polling trigger

Usage:
    # First, set environment variables or create .env file
    export SUPPORT_EMAIL_PASSWORD="your_password"

    # Run tests
    python test_email_polling.py

    # Or run specific tests
    python test_email_polling.py --test connection
    python test_email_polling.py --test poll
"""
import os
import sys
import asyncio
import argparse
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()


def print_header(title: str):
    """Print a formatted header"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def print_result(label: str, value, success: bool = None):
    """Print a formatted result"""
    if success is True:
        status = "✅"
    elif success is False:
        status = "❌"
    else:
        status = "ℹ️"
    print(f"  {status} {label}: {value}")


async def test_connection():
    """Test IMAP connection to Zoho Mail"""
    print_header("Testing IMAP Connection")

    from app.core.config import settings

    print_result("IMAP Server", settings.IMAP_SERVER)
    print_result("IMAP Port", settings.IMAP_PORT)
    print_result("Email Account", settings.SUPPORT_EMAIL)
    print_result("Password Set", "Yes" if settings.SUPPORT_EMAIL_PASSWORD else "No",
                 settings.SUPPORT_EMAIL_PASSWORD is not None)

    if not settings.SUPPORT_EMAIL_PASSWORD:
        print("\n  ⚠️  SUPPORT_EMAIL_PASSWORD not set!")
        print("  Set it in .env file or as environment variable")
        return False

    # Test connection
    from app.services.email_polling_service import email_polling_service

    print("\n  Attempting connection...")
    result = await email_polling_service.test_connection()

    print_result("Connection", result.get("message"), result.get("success"))

    if result.get("success"):
        print_result("Inbox Messages", result.get("inbox_messages", 0))
        print_result("Unseen Messages", result.get("inbox_unseen", 0))
        return True
    else:
        return False


async def test_service_status():
    """Test email polling service status"""
    print_header("Testing Service Status")

    from app.services.email_polling_service import email_polling_service
    from app.core.scheduler import email_polling_scheduler

    # Service status
    service_status = email_polling_service.get_status()
    print("\n  Email Polling Service:")
    print_result("Available", service_status["is_available"], service_status["is_available"])
    print_result("Enabled", service_status["enabled"])
    print_result("Polling Interval", f"{service_status['polling_interval_seconds']}s")
    print_result("Last Poll", service_status["last_poll_time"] or "Never")
    print_result("Last Status", service_status["last_poll_status"])
    print_result("Processed Today", service_status["emails_processed_today"])

    # Scheduler status
    scheduler_status = email_polling_scheduler.get_status()
    print("\n  Scheduler:")
    print_result("Available", scheduler_status["scheduler_available"], scheduler_status["scheduler_available"])
    print_result("Running", scheduler_status["is_running"], scheduler_status["is_running"])
    print_result("Next Run", scheduler_status.get("next_run_time") or "Not scheduled")

    return service_status["is_available"]


async def test_manual_poll():
    """Test manual email polling"""
    print_header("Testing Manual Poll")

    from app.services.email_polling_service import email_polling_service

    if not email_polling_service.is_available():
        print("  ❌ Service not available. Run connection test first.")
        return False

    print("\n  Starting manual poll...")
    print("  This will process unread emails in the inbox")
    print("  (AI responses will be sent if enabled)\n")

    # Confirm
    confirm = input("  Continue? (y/N): ").strip().lower()
    if confirm != 'y':
        print("  Cancelled.")
        return False

    result = await email_polling_service.poll_inbox()

    print_result("Success", result.get("success"), result.get("success"))
    print_result("Emails Found", result.get("emails_found", 0))
    print_result("Emails Processed", result.get("emails_processed", 0))
    print_result("Emails Escalated", result.get("emails_escalated", 0))

    if result.get("errors"):
        print("\n  Errors:")
        for error in result["errors"]:
            print(f"    - {error}")

    return result.get("success", False)


async def test_ai_service():
    """Test AI email support service"""
    print_header("Testing AI Email Support Service")

    from app.services.ai_email_support import ai_email_support

    print_result("Available", ai_email_support.is_available(), ai_email_support.is_available())
    print_result("Model", ai_email_support.model)
    print_result("Enabled", ai_email_support.enabled)
    print_result("Confidence Threshold", ai_email_support.confidence_threshold)
    print_result("Knowledge Base Loaded", len(ai_email_support.knowledge_base) > 0,
                 len(ai_email_support.knowledge_base) > 0)

    if ai_email_support.is_available():
        # Test email analysis
        print("\n  Testing email analysis...")
        test_email = """
        Hi, I'm having trouble logging into my BinaApp account.
        I've tried resetting my password but it's still not working.
        Can you please help?
        Thanks,
        Test User
        """

        analysis = await ai_email_support.analyze_email(
            email_content=test_email,
            subject="Login Problem",
            sender_email="test@example.com"
        )

        print_result("Sentiment", analysis.get("sentiment"))
        print_result("Urgency", analysis.get("urgency"))
        print_result("Category", analysis.get("category"))
        print_result("Confidence", f"{analysis.get('confidence', 0):.2f}")
        print_result("Should Escalate", analysis.get("should_escalate"))

        return True
    else:
        print("\n  ⚠️  AI service not available. Check ANTHROPIC_API_KEY.")
        return False


async def test_scheduler():
    """Test scheduler start/stop"""
    print_header("Testing Scheduler")

    from app.core.scheduler import email_polling_scheduler, start_email_polling, stop_email_polling
    from app.services.email_polling_service import email_polling_service

    if not email_polling_service.is_available():
        print("  ❌ Email polling service not available")
        return False

    print("\n  Starting scheduler...")
    started = await start_email_polling()
    print_result("Started", started, started)

    if started:
        status = email_polling_scheduler.get_status()
        print_result("Running", status["is_running"], status["is_running"])
        print_result("Next Run", status.get("next_run_time") or "Not scheduled")

        print("\n  Waiting 5 seconds...")
        await asyncio.sleep(5)

        print("\n  Stopping scheduler...")
        stop_email_polling()
        print_result("Stopped", not email_polling_scheduler.is_running,
                     not email_polling_scheduler.is_running)

    return started


def print_instructions():
    """Print setup and testing instructions"""
    print_header("Email Polling Service - Setup Instructions")

    print("""
  1. Get the support.team@binaapp.my password from Zoho Mail:
     - Login to Zoho Mail admin
     - Go to Users > support.team@binaapp.my
     - Reset or retrieve the password

  2. Configure environment variables:
     Add to backend/.env:

     SUPPORT_EMAIL_PASSWORD=your_password_here
     EMAIL_POLLING_ENABLED=true
     EMAIL_POLLING_INTERVAL_SECONDS=120

  3. Install dependencies:
     pip install imap-tools apscheduler html2text --break-system-packages

  4. Test locally:
     python test_email_polling.py --test connection
     python test_email_polling.py --test poll

  5. Deploy to Render:
     - Add SUPPORT_EMAIL_PASSWORD to environment variables
     - Redeploy the application

  6. Monitor logs:
     - Check Render logs for "Email polling" messages
     - Check Supabase for email_threads table entries

  API Endpoints (requires authentication):
     GET  /api/v1/email/polling/status     - Get polling status
     POST /api/v1/email/polling/start      - Start polling
     POST /api/v1/email/polling/stop       - Stop polling
     POST /api/v1/email/polling/trigger    - Manual poll
     GET  /api/v1/email/polling/test-connection  - Test IMAP connection
     GET  /api/v1/email/polling/health     - Health check (public)
""")


async def main():
    """Main test runner"""
    parser = argparse.ArgumentParser(description="Test Email Polling Service")
    parser.add_argument("--test", choices=["connection", "status", "poll", "ai", "scheduler", "all", "instructions"],
                        default="status", help="Test to run")

    args = parser.parse_args()

    print("\n" + "🔧" * 30)
    print("  BinaApp Email Polling Service Tester")
    print("🔧" * 30)

    if args.test == "instructions":
        print_instructions()
        return

    # Initialize
    print("\n  Initializing...")

    try:
        if args.test == "connection" or args.test == "all":
            await test_connection()

        if args.test == "status" or args.test == "all":
            await test_service_status()

        if args.test == "ai" or args.test == "all":
            await test_ai_service()

        if args.test == "scheduler" or args.test == "all":
            await test_scheduler()

        if args.test == "poll":
            await test_manual_poll()

    except Exception as e:
        print(f"\n  ❌ Error: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 60)
    print("  Tests completed")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
