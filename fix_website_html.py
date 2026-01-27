#!/usr/bin/env python3
"""
Fix existing websites to add data-website-id to delivery widget script tag
This script updates the HTML in the Supabase database for existing websites
"""

import os
import re
from supabase import create_client, Client
from datetime import datetime

# Supabase credentials
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ Error: SUPABASE_URL and SUPABASE_KEY environment variables required")
    exit(1)

print(f"✓ Connecting to Supabase: {SUPABASE_URL}")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def fix_website_html(website_id: str = None, subdomain: str = None):
    """Fix HTML for a specific website or all websites"""

    try:
        # Get website(s)
        query = supabase.table("websites").select("*")

        if website_id:
            query = query.eq("id", website_id)
        elif subdomain:
            query = query.eq("subdomain", subdomain)
        else:
            # Get all websites with html_content
            print("⚠️  No specific website specified - will process ALL websites")

        result = query.execute()

        if not result.data:
            print(f"❌ No websites found")
            return

        websites = result.data
        print(f"✓ Found {len(websites)} website(s) to process")

        for website in websites:
            website_id = website['id']
            subdomain = website['subdomain']
            html_content = website.get('html_content') or website.get('html_code') or ""

            if not html_content:
                print(f"⚠️  {subdomain}: No HTML content, skipping")
                continue

            print(f"\n📝 Processing: {subdomain} (ID: {website_id})")
            print(f"   Original HTML length: {len(html_content)} characters")

            # Check if already has data-website-id
            if 'data-website-id' in html_content:
                print(f"   ✓ Already has data-website-id, skipping")
                continue

            # Pattern to match old script tag
            old_pattern = r'<script\s+src="[^"]*delivery-widget\.js">\s*</script>\s*(?:<script>.*?BinaAppDelivery\.init\(.*?\).*?</script>)?'

            # Check if old pattern exists
            if not re.search(old_pattern, html_content, re.DOTALL):
                print(f"   ⚠️  No delivery widget script tag found, skipping")
                continue

            # New script tag with data-website-id
            new_script = f'''<script
  src="https://binaapp-backend.onrender.com/widgets/delivery-widget.js"
  data-website-id="{website_id}"
  data-api-url="https://binaapp-backend.onrender.com"
  data-primary-color="#ea580c"
  data-language="ms"
></script>
<div id="binaapp-widget"></div>'''

            # Replace old script with new script
            new_html = re.sub(old_pattern, new_script, html_content, flags=re.DOTALL)

            if new_html == html_content:
                print(f"   ⚠️  No changes made (pattern didn't match)")
                # Try simpler pattern
                simple_pattern = r'<script\s+src="[^"]*delivery-widget\.js"[^>]*>\s*</script>'
                if re.search(simple_pattern, html_content):
                    print(f"   🔍 Found simpler pattern, trying that...")
                    new_html = re.sub(simple_pattern, new_script, html_content)

            if new_html != html_content:
                print(f"   ✓ HTML updated, new length: {len(new_html)} characters")
                print(f"   📤 Updating database...")

                # Update in database
                update_result = supabase.table("websites").update({
                    "html_content": new_html,
                    "updated_at": datetime.utcnow().isoformat()
                }).eq("id", website_id).execute()

                if update_result.data:
                    print(f"   ✅ SUCCESS! {subdomain} updated in database")
                else:
                    print(f"   ❌ Failed to update database")
            else:
                print(f"   ⚠️  No changes made")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

def list_websites():
    """List all websites"""
    try:
        result = supabase.table("websites").select("id, subdomain, name, status").execute()

        if not result.data:
            print("No websites found")
            return

        print(f"\n📋 Found {len(result.data)} websites:")
        print(f"{'Subdomain':<20} {'Name':<30} {'Status':<15} {'ID':<40}")
        print("-" * 105)

        for website in result.data:
            subdomain = website.get('subdomain', '')
            name = website.get('name', '')
            status = website.get('status', '')
            website_id = website.get('id', '')

            print(f"{subdomain:<20} {name:<30} {status:<15} {website_id:<40}")

    except Exception as e:
        print(f"❌ Error listing websites: {e}")

if __name__ == "__main__":
    import sys

    print("=" * 80)
    print("  BinaApp Website HTML Fixer")
    print("  Adds data-website-id to delivery widget script tags")
    print("=" * 80)
    print()

    # Parse command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == "list":
            list_websites()
        elif sys.argv[1] == "all":
            fix_website_html()
        else:
            # Assume it's a subdomain or website_id
            arg = sys.argv[1]
            if arg.startswith("jojo") or arg.startswith("mymy") or "." in arg:
                # Treat as subdomain
                fix_website_html(subdomain=arg.replace(".binaapp.my", ""))
            else:
                # Treat as website_id
                fix_website_html(website_id=arg)
    else:
        print("Usage:")
        print("  python fix_website_html.py list                    # List all websites")
        print("  python fix_website_html.py all                     # Fix all websites")
        print("  python fix_website_html.py <subdomain>             # Fix specific website by subdomain")
        print("  python fix_website_html.py <website_id>            # Fix specific website by ID")
        print()
        print("Examples:")
        print("  python fix_website_html.py list")
        print("  python fix_website_html.py jojo")
        print("  python fix_website_html.py jojo.binaapp.my")
        print("  python fix_website_html.py abc-123-def-456")
        print()

        # Default: list websites
        list_websites()
