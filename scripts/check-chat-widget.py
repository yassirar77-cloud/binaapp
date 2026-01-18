#!/usr/bin/env python3
"""
BinaApp Chat Widget Diagnostic Tool
Checks if generated websites have the chat widget injected correctly
"""

import os
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.core.supabase import supabase


def check_chat_widget_in_websites():
    """Check all websites in database for chat widget presence"""

    print("🔍 BinaApp Chat Widget Diagnostic")
    print("=" * 60)
    print()

    try:
        # Fetch all websites
        result = supabase.table("websites").select("id, business_name, created_at").order("created_at", desc=True).limit(20).execute()

        websites = result.data or []

        if not websites:
            print("❌ No websites found in database")
            return

        print(f"📊 Found {len(websites)} websites\n")

        # Check each website's HTML content
        for website in websites:
            website_id = website['id']
            business_name = website['business_name']
            created_at = website['created_at']

            print(f"\n🏪 {business_name}")
            print(f"   ID: {website_id}")
            print(f"   Created: {created_at}")

            # Get HTML content from generations table
            gen_result = supabase.table("generations").select("html_content, selected_html").eq("website_id", website_id).order("created_at", desc=True).limit(1).execute()

            if not gen_result.data:
                print(f"   ⚠️  No generation found")
                continue

            gen = gen_result.data[0]
            html = gen.get("selected_html") or gen.get("html_content") or ""

            if not html:
                print(f"   ⚠️  No HTML content")
                continue

            # Check for chat widget
            has_chat_script = "chat-widget.js" in html
            has_chat_button = "binaapp-chat-btn" in html or "binaapp-chat-widget" in html
            has_website_id_attr = f'data-website-id="{website_id}"' in html

            print(f"   Chat script tag: {'✅' if has_chat_script else '❌'}")
            print(f"   Chat button/widget: {'✅' if has_chat_button else '❌'}")
            print(f"   Correct website_id: {'✅' if has_website_id_attr else '❌'}")

            if has_chat_script:
                print(f"   Status: ✅ CHAT WIDGET INJECTED")
            else:
                print(f"   Status: ❌ CHAT WIDGET MISSING - Needs regeneration")

                # Show relevant snippet
                if "</body>" in html:
                    body_idx = html.rfind("</body>")
                    snippet = html[max(0, body_idx-200):body_idx+20]
                    print(f"   Last 200 chars before </body>:")
                    print(f"   {snippet[-150:]}")

        print("\n" + "=" * 60)
        print("✅ Diagnostic complete")
        print()
        print("RECOMMENDATIONS:")
        print("- Websites without chat widget need to be regenerated")
        print("- Or run manual fix to inject chat widget into existing HTML")
        print()

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    check_chat_widget_in_websites()
