#!/usr/bin/env python3
"""Test IMAP connection to Zoho Mail"""

import imaplib
import email
from email.header import decode_header
from datetime import datetime

# Configuration
IMAP_SERVER = "imap.zoho.com"
IMAP_PORT = 993
EMAIL = "support.team@binaapp.my"
PASSWORD = "d1JNkVH7yQRk"

def test_imap_connection():
    print("=" * 50)
    print("IMAP CONNECTION TEST")
    print("=" * 50)
    print(f"Server: {IMAP_SERVER}:{IMAP_PORT}")
    print(f"Email: {EMAIL}")
    print(f"Time: {datetime.now()}")
    print("-" * 50)

    try:
        # Connect to IMAP server
        print("\n1. Connecting to IMAP server...")
        mail = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT)
        print("   ✅ Connected successfully!")

        # Login
        print("\n2. Logging in...")
        mail.login(EMAIL, PASSWORD)
        print("   ✅ Login successful!")

        # List mailboxes
        print("\n3. Listing mailboxes...")
        status, mailboxes = mail.list()
        print(f"   Found {len(mailboxes)} mailboxes:")
        for mb in mailboxes[:5]:  # Show first 5
            print(f"   - {mb.decode()}")

        # Select INBOX
        print("\n4. Selecting INBOX...")
        status, messages = mail.select("INBOX")
        total_messages = int(messages[0])
        print(f"   ✅ Total messages in INBOX: {total_messages}")

        # Search for unread emails
        print("\n5. Searching for UNREAD emails...")
        status, unread_ids = mail.search(None, "UNSEEN")
        unread_list = unread_ids[0].split()
        print(f"   ✅ Found {len(unread_list)} unread emails")

        # Show unread email subjects
        if unread_list:
            print("\n6. Unread email details:")
            for email_id in unread_list[-5:]:  # Last 5 unread
                status, msg_data = mail.fetch(email_id, "(RFC822)")
                for response_part in msg_data:
                    if isinstance(response_part, tuple):
                        msg = email.message_from_bytes(response_part[1])
                        subject, encoding = decode_header(msg["Subject"])[0]
                        if isinstance(subject, bytes):
                            subject = subject.decode(encoding or "utf-8")
                        from_addr = msg.get("From")
                        date = msg.get("Date")
                        print(f"\n   Email ID: {email_id.decode()}")
                        print(f"   From: {from_addr}")
                        print(f"   Subject: {subject}")
                        print(f"   Date: {date}")

        # Close connection
        mail.close()
        mail.logout()
        print("\n" + "=" * 50)
        print("✅ ALL TESTS PASSED - IMAP CONNECTION WORKING!")
        print("=" * 50)
        return True

    except imaplib.IMAP4.error as e:
        print(f"\n❌ IMAP Error: {e}")
        print("\nPossible issues:")
        print("- Wrong password (check App-Specific Password)")
        print("- IMAP not enabled in Zoho settings")
        print("- Account security blocking access")
        return False

    except Exception as e:
        print(f"\n❌ Error: {type(e).__name__}: {e}")
        return False

if __name__ == "__main__":
    test_imap_connection()
