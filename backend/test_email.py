#!/usr/bin/env python3
"""
===========================================
BinaApp Email Test Script
===========================================

HOW TO RUN THIS SCRIPT:
-----------------------
1. Open Render Dashboard: https://dashboard.render.com
2. Click on your BinaApp backend service
3. Click "Shell" tab
4. Run: python test_email.py

OR locally:
-----------
cd backend
python test_email.py

"""

import asyncio
import sys
import os

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

from app.services.email_service import email_service
from app.core.config import settings


async def test_order_confirmation():
    """Send a test order confirmation email"""

    print("=" * 50)
    print("   BinaApp Email Test")
    print("=" * 50)
    print()

    # Show current configuration
    print("📧 Email Configuration:")
    print(f"   SMTP Host: {settings.SMTP_HOST}")
    print(f"   SMTP Port: {settings.SMTP_PORT}")
    print(f"   SMTP User: {settings.SMTP_USER}")
    print(f"   Password:  {'✓ Set' if settings.SMTP_PASSWORD else '✗ NOT SET'}")
    print()

    # Check if configured
    if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
        print("❌ ERROR: Email not configured!")
        print("   Please set SMTP_USER and SMTP_PASSWORD in Render environment variables.")
        return False

    # Test email recipient
    test_email = "yassirabdulrahman77@gmail.com"

    # Sample order data
    order_data = {
        "customer_email": test_email,
        "customer_name": "Yassir",
        "order_id": "12345",
        "order_items": [
            {"name": "Nasi Lemak Ayam Goreng", "quantity": 2, "price": 15.00},
            {"name": "Teh Tarik Ais", "quantity": 2, "price": 5.00}
        ],
        "total_amount": 50.00,
        "delivery_address": "123 Jalan Ampang, Kuala Lumpur 50450",
        "restaurant_name": "Restoran BinaApp Demo"
    }

    print(f"📤 Sending test email to: {test_email}")
    print(f"   Order ID: #{order_data['order_id']}")
    print(f"   Total: RM{order_data['total_amount']:.2f}")
    print()
    print("   Please wait...")
    print()

    try:
        # Send the email
        result = await email_service.send_order_confirmation(
            customer_email=order_data["customer_email"],
            customer_name=order_data["customer_name"],
            order_id=order_data["order_id"],
            order_items=order_data["order_items"],
            total_amount=order_data["total_amount"],
            delivery_address=order_data["delivery_address"],
            restaurant_name=order_data["restaurant_name"]
        )

        if result:
            print("=" * 50)
            print("✅ SUCCESS! Email sent!")
            print("=" * 50)
            print()
            print(f"📬 Check your inbox at: {test_email}")
            print("   (Also check spam folder)")
            print()
            return True
        else:
            print("=" * 50)
            print("❌ FAILED! Email was not sent.")
            print("=" * 50)
            print()
            print("Possible reasons:")
            print("   1. Wrong SMTP password")
            print("   2. Zoho account issue")
            print("   3. Network problem")
            print()
            return False

    except Exception as e:
        print("=" * 50)
        print(f"❌ ERROR: {str(e)}")
        print("=" * 50)
        print()
        print("Troubleshooting:")
        print("   1. Check SMTP_PASSWORD is correct")
        print("   2. Verify Zoho account is active")
        print("   3. Check environment variables in Render")
        print()
        return False


if __name__ == "__main__":
    print()
    result = asyncio.run(test_order_confirmation())
    print()
    sys.exit(0 if result else 1)
