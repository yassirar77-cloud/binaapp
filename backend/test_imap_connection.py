#!/usr/bin/env python3
"""
IMAP Connection Test Script
Tests connection to Zoho Mail IMAP server for email polling service debugging

Usage: python backend/test_imap_connection.py
"""

import imaplib
import ssl
from datetime import datetime

# IMAP Configuration
IMAP_SERVER = "imap.zoho.com"
IMAP_PORT = 993
EMAIL = "support.team@binaapp.my"
PASSWORD = "d1JNkVH7yQRk"


def test_imap_connection():
    """Test IMAP connection to Zoho Mail"""
    print("=" * 60)
    print("IMAP CONNECTION TEST")
    print("=" * 60)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print(f"Server: {IMAP_SERVER}")
    print(f"Port: {IMAP_PORT}")
    print(f"Email: {EMAIL}")
    print("=" * 60)

    imap = None

    try:
        # Step 1: Create SSL context
        print("\n[1] Creating SSL context...")
        ssl_context = ssl.create_default_context()
        print("    SSL context created successfully")

        # Step 2: Connect to IMAP server
        print(f"\n[2] Connecting to {IMAP_SERVER}:{IMAP_PORT}...")
        imap = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT, ssl_context=ssl_context)
        print("    Connection established!")

        # Step 3: Login
        print(f"\n[3] Logging in as {EMAIL}...")
        imap.login(EMAIL, PASSWORD)
        print("    LOGIN SUCCESSFUL!")

        # Step 4: Select INBOX
        print("\n[4] Selecting INBOX...")
        status, messages = imap.select("INBOX")
        if status == "OK":
            total_messages = int(messages[0])
            print(f"    INBOX selected successfully")
            print(f"    Total messages in INBOX: {total_messages}")
        else:
            print(f"    Failed to select INBOX: {status}")
            return False

        # Step 5: Search for unread emails
        print("\n[5] Searching for unread emails (UNSEEN)...")
        status, data = imap.search(None, "UNSEEN")
        if status == "OK":
            unread_ids = data[0].split()
            unread_count = len(unread_ids)
            print(f"    Unread emails found: {unread_count}")

            # Step 6: List unread email subjects (up to 10)
            if unread_count > 0:
                print(f"\n[6] Listing unread emails (showing up to 10):")
                print("-" * 50)

                for idx, email_id in enumerate(unread_ids[:10], 1):
                    try:
                        # Fetch email headers
                        status, msg_data = imap.fetch(email_id, "(BODY.PEEK[HEADER.FIELDS (SUBJECT FROM DATE)])")
                        if status == "OK":
                            header_data = msg_data[0][1].decode('utf-8', errors='replace')
                            lines = header_data.strip().split('\r\n')

                            subject = ""
                            from_addr = ""
                            date = ""

                            for line in lines:
                                if line.lower().startswith("subject:"):
                                    subject = line[8:].strip()
                                elif line.lower().startswith("from:"):
                                    from_addr = line[5:].strip()
                                elif line.lower().startswith("date:"):
                                    date = line[5:].strip()

                            print(f"\n    [{idx}] Email ID: {email_id.decode()}")
                            print(f"        Subject: {subject[:60]}{'...' if len(subject) > 60 else ''}")
                            print(f"        From: {from_addr[:50]}{'...' if len(from_addr) > 50 else ''}")
                            print(f"        Date: {date}")
                    except Exception as e:
                        print(f"    [{idx}] Error fetching email {email_id}: {e}")

                if unread_count > 10:
                    print(f"\n    ... and {unread_count - 10} more unread emails")
        else:
            print(f"    Failed to search: {status}")

        # Step 7: List mailbox folders
        print("\n[7] Listing available mailbox folders...")
        status, folders = imap.list()
        if status == "OK":
            print("    Available folders:")
            for folder in folders[:10]:
                folder_name = folder.decode().split(' "/" ')[-1].strip('"')
                print(f"      - {folder_name}")
            if len(folders) > 10:
                print(f"      ... and {len(folders) - 10} more folders")

        print("\n" + "=" * 60)
        print("TEST RESULT: SUCCESS")
        print("=" * 60)
        print("\nSummary:")
        print(f"  - Connection: OK")
        print(f"  - Authentication: OK")
        print(f"  - INBOX Access: OK")
        print(f"  - Total Messages: {total_messages}")
        print(f"  - Unread Messages: {unread_count}")
        print("=" * 60)

        return True

    except imaplib.IMAP4.error as e:
        print("\n" + "=" * 60)
        print("TEST RESULT: FAILED - IMAP ERROR")
        print("=" * 60)
        print(f"IMAP Error: {e}")
        print("\nPossible causes:")
        print("  - Invalid credentials (wrong email/password)")
        print("  - IMAP access not enabled in Zoho Mail settings")
        print("  - Account locked or requires 2FA")
        print("  - App-specific password required")
        print("=" * 60)
        return False

    except ssl.SSLError as e:
        print("\n" + "=" * 60)
        print("TEST RESULT: FAILED - SSL ERROR")
        print("=" * 60)
        print(f"SSL Error: {e}")
        print("\nPossible causes:")
        print("  - SSL certificate verification failed")
        print("  - Network/firewall blocking HTTPS")
        print("=" * 60)
        return False

    except ConnectionError as e:
        print("\n" + "=" * 60)
        print("TEST RESULT: FAILED - CONNECTION ERROR")
        print("=" * 60)
        print(f"Connection Error: {e}")
        print("\nPossible causes:")
        print("  - Server unreachable")
        print("  - Network connectivity issues")
        print("  - Firewall blocking port 993")
        print("=" * 60)
        return False

    except Exception as e:
        print("\n" + "=" * 60)
        print("TEST RESULT: FAILED - UNEXPECTED ERROR")
        print("=" * 60)
        print(f"Error type: {type(e).__name__}")
        print(f"Error message: {e}")
        import traceback
        print(f"\nFull traceback:\n{traceback.format_exc()}")
        print("=" * 60)
        return False

    finally:
        if imap:
            try:
                imap.close()
                imap.logout()
                print("\n[Cleanup] IMAP connection closed")
            except Exception:
                pass


if __name__ == "__main__":
    success = test_imap_connection()
    exit(0 if success else 1)
