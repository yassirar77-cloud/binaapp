#!/usr/bin/env python3
"""
Test script for BinaApp Email Service
Tests Zoho SMTP connection and email sending
"""

import asyncio
import sys
import os

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

from app.services.email_service import email_service
from app.core.config import settings


async def test_order_confirmation():
    """Test sending an order confirmation email"""
    print("\n" + "="*60)
    print("BinaApp Email Service Test")
    print("="*60)

    # Check configuration
    print("\n[1] Checking email configuration...")
    print(f"    SMTP Host: {settings.SMTP_HOST}")
    print(f"    SMTP Port: {settings.SMTP_PORT}")
    print(f"    SMTP User: {settings.SMTP_USER}")
    print(f"    SMTP Password: {'*' * len(settings.SMTP_PASSWORD) if settings.SMTP_PASSWORD else 'NOT SET'}")
    print(f"    From Email: {settings.FROM_EMAIL}")
    print(f"    From Name: {settings.FROM_NAME}")

    if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
        print("\n[ERROR] SMTP credentials not configured!")
        print("Please check your .env file has SMTP_USER and SMTP_PASSWORD set.")
        return False

    # Test email details
    test_email = "yassirabdulrahman77@gmail.com"

    print(f"\n[2] Sending test order confirmation to: {test_email}")
    print("    Please wait...")

    # Sample order data
    order_items = [
        {"name": "Nasi Lemak Ayam", "quantity": 2, "price": 12.00},
        {"name": "Teh Tarik", "quantity": 2, "price": 3.50},
        {"name": "Roti Canai", "quantity": 1, "price": 4.00}
    ]

    try:
        result = await email_service.send_order_confirmation(
            customer_email=test_email,
            customer_name="Test User",
            order_id="TEST-001",
            order_items=order_items,
            total_amount=35.00,
            delivery_address="123 Jalan Test, Kuala Lumpur, 50000",
            restaurant_name="Restoran BinaApp Demo"
        )

        if result:
            print("\n[SUCCESS] Email sent successfully!")
            print(f"    Check your inbox at: {test_email}")
            print("    (Also check spam folder just in case)")
            return True
        else:
            print("\n[FAILED] Email was not sent.")
            print("    The email service returned False.")
            print("    Check the logs above for error details.")
            return False

    except Exception as e:
        print(f"\n[ERROR] Failed to send email: {str(e)}")
        print("\nPossible issues:")
        print("  1. Wrong SMTP password")
        print("  2. Zoho account not verified")
        print("  3. Network/firewall blocking SMTP")
        print("  4. Zoho requires app-specific password")
        return False


async def test_admin_notification():
    """Test sending an admin notification email"""
    print("\n[3] Sending test admin notification...")

    try:
        result = await email_service.send_admin_notification(
            subject="Test Notification from BinaApp",
            message="This is a test notification to verify the email system is working correctly.",
            notification_type="success",
            details={
                "Test Type": "Email Service Verification",
                "Timestamp": "2025-01-30",
                "Status": "Testing"
            }
        )

        if result:
            print(f"    [SUCCESS] Admin notification sent to: {settings.ADMIN_EMAIL}")
            return True
        else:
            print("    [FAILED] Admin notification was not sent.")
            return False

    except Exception as e:
        print(f"    [ERROR] Failed: {str(e)}")
        return False


async def main():
    """Run all email tests"""
    print("\nStarting email tests...\n")

    # Test 1: Order confirmation
    order_test = await test_order_confirmation()

    # Test 2: Admin notification
    admin_test = await test_admin_notification()

    # Summary
    print("\n" + "="*60)
    print("Test Summary")
    print("="*60)
    print(f"  Order Confirmation: {'PASS' if order_test else 'FAIL'}")
    print(f"  Admin Notification: {'PASS' if admin_test else 'FAIL'}")
    print("="*60)

    if order_test and admin_test:
        print("\nAll tests passed! Your email service is working correctly.")
    else:
        print("\nSome tests failed. Please check the errors above.")

    return order_test and admin_test


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
