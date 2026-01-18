#!/usr/bin/env python3
"""
BinaApp Chat Widget Fix Script
Injects chat widget into existing websites that don't have it
"""

import os
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.core.supabase import supabase


API_URL = "https://binaapp-backend.onrender.com"


def inject_chat_widget(html: str, website_id: str) -> str:
    """Inject chat widget script into HTML"""

    # Check if already has chat widget
    if "chat-widget.js" in html:
        return html

    # Create chat widget script tag
    chat_widget = f'''
<!-- BinaApp Chat Widget - Customer to Owner Chat -->
<script src="{API_URL}/static/widgets/chat-widget.js"
        data-website-id="{website_id}"
        data-api-url="{API_URL}"></script>'''

    # Inject before </body>
    if "</body>" in html:
        html = html.replace("</body>", chat_widget + "\n</body>")
    else:
        html += chat_widget

    return html


def fix_websites():
    """Fix all websites by injecting chat widget if missing"""

    print("🔧 BinaApp Chat Widget Fix Script")
    print("=" * 60)
    print()

    # Ask for confirmation
    confirm = input("This will update HTML content for websites missing chat widget. Continue? (yes/no): ")
    if confirm.lower() not in ['yes', 'y']:
        print("❌ Aborted")
        return

    try:
        # Fetch all websites
        result = supabase.table("websites").select("id, business_name").order("created_at", desc=True).execute()

        websites = result.data or []

        if not websites:
            print("❌ No websites found")
            return

        print(f"📊 Found {len(websites)} websites")
        print()

        fixed_count = 0
        skipped_count = 0
        error_count = 0

        for website in websites:
            website_id = website['id']
            business_name = website['business_name']

            print(f"🏪 {business_name} ({website_id[:8]}...)")

            try:
                # Get HTML content from generations table
                gen_result = supabase.table("generations").select("id, html_content, selected_html").eq("website_id", website_id).order("created_at", desc=True).limit(1).execute()

                if not gen_result.data:
                    print(f"   ⚠️  No generation found - SKIPPED")
                    skipped_count += 1
                    continue

                gen = gen_result.data[0]
                gen_id = gen['id']
                html = gen.get("selected_html") or gen.get("html_content") or ""

                if not html:
                    print(f"   ⚠️  No HTML content - SKIPPED")
                    skipped_count += 1
                    continue

                # Check if already has chat widget
                if "chat-widget.js" in html:
                    print(f"   ✅ Chat widget already present - SKIPPED")
                    skipped_count += 1
                    continue

                # Inject chat widget
                fixed_html = inject_chat_widget(html, website_id)

                # Update in database
                if gen.get("selected_html"):
                    supabase.table("generations").update({
                        "selected_html": fixed_html
                    }).eq("id", gen_id).execute()
                else:
                    supabase.table("generations").update({
                        "html_content": fixed_html
                    }).eq("id", gen_id).execute()

                print(f"   ✅ FIXED - Chat widget injected")
                fixed_count += 1

            except Exception as e:
                print(f"   ❌ ERROR: {e}")
                error_count += 1

        print()
        print("=" * 60)
        print(f"✅ Fix complete!")
        print(f"   Fixed: {fixed_count}")
        print(f"   Skipped: {skipped_count}")
        print(f"   Errors: {error_count}")
        print()

        if fixed_count > 0:
            print("🎉 Chat widget has been injected into websites!")
            print("   Users can now see the chat button on their sites")
            print()

    except Exception as e:
        print(f"❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    fix_websites()
