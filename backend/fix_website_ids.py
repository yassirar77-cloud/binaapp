"""
Fix Website ID Mismatches

This script fixes all existing websites in the database by replacing any incorrect
website_id values in their HTML with the correct database ID.

The bug: During generation, random UUIDs were injected into HTML that don't match
the actual database website ID. This script repairs all affected websites.

Usage:
    python fix_website_ids.py

Requirements:
    - SUPABASE_URL environment variable
    - SUPABASE_KEY environment variable
"""

import os
import re
import asyncio
from supabase import create_client, Client
from loguru import logger


def fix_website_id_in_html(html: str, correct_website_id: str) -> tuple[str, int]:
    """
    Replace all incorrect website_id references with the correct one.

    Returns:
        tuple: (fixed_html, number_of_replacements)
    """
    if not html:
        return html, 0

    replacements = 0

    # Pattern 1: data-website-id="..." attribute
    pattern1 = r'data-website-id="[a-f0-9-]{36}"'
    matches1 = re.findall(pattern1, html)
    if matches1:
        logger.debug(f"  Found {len(matches1)} data-website-id attributes to fix")
        html = re.sub(pattern1, f'data-website-id="{correct_website_id}"', html)
        replacements += len(matches1)

    # Pattern 2: const WEBSITE_ID = '...' in JavaScript
    pattern2 = r"const WEBSITE_ID = ['\"]([a-f0-9-]{36})['\"]"
    matches2 = re.findall(pattern2, html)
    if matches2:
        logger.debug(f"  Found {len(matches2)} const WEBSITE_ID declarations to fix")
        html = re.sub(pattern2, f"const WEBSITE_ID = '{correct_website_id}'", html)
        replacements += len(matches2)

    # Pattern 3: websiteId: '...' in JavaScript objects
    pattern3 = r"websiteId:\s*['\"]([a-f0-9-]{36})['\"]"
    matches3 = re.findall(pattern3, html)
    if matches3:
        logger.debug(f"  Found {len(matches3)} websiteId properties to fix")
        html = re.sub(pattern3, f"websiteId: '{correct_website_id}'", html)
        replacements += len(matches3)

    # Pattern 4: Delivery URLs: binaapp.my/delivery/UUID
    pattern4 = r'binaapp\.my/delivery/[a-f0-9-]{36}'
    matches4 = re.findall(pattern4, html)
    if matches4:
        logger.debug(f"  Found {len(matches4)} delivery URLs to fix")
        html = re.sub(pattern4, f'binaapp.my/delivery/{correct_website_id}', html)
        replacements += len(matches4)

    return html, replacements


async def fix_all_websites():
    """
    Fix all websites in the database by replacing incorrect website_ids.
    """
    # Initialize Supabase client
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_KEY")

    if not supabase_url or not supabase_key:
        logger.error("❌ SUPABASE_URL and SUPABASE_KEY environment variables must be set")
        return

    logger.info("=" * 80)
    logger.info("🔧 FIXING WEBSITE ID MISMATCHES")
    logger.info("=" * 80)

    supabase: Client = create_client(supabase_url, supabase_key)

    # Fetch all websites
    logger.info("📥 Fetching all websites from database...")
    response = supabase.table('websites').select('id, subdomain, html_content, business_name').execute()

    if not response.data:
        logger.info("✅ No websites found in database")
        return

    websites = response.data
    logger.info(f"📊 Found {len(websites)} websites to check")
    logger.info("")

    fixed_count = 0
    skipped_count = 0
    error_count = 0
    total_replacements = 0

    for idx, website in enumerate(websites, 1):
        website_id = str(website['id'])
        subdomain = website.get('subdomain', 'unknown')
        business_name = website.get('business_name', 'N/A')
        html_content = website.get('html_content')

        logger.info(f"[{idx}/{len(websites)}] Processing: {subdomain} (ID: {website_id})")

        if not html_content:
            logger.warning(f"  ⏭️  Skipped: No HTML content")
            skipped_count += 1
            continue

        # Check if HTML contains any wrong UUIDs
        # Extract all UUIDs from the HTML
        uuid_pattern = r'[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}'
        found_uuids = set(re.findall(uuid_pattern, html_content))

        # Remove the correct website_id from the set
        found_uuids.discard(website_id)

        if not found_uuids:
            logger.info(f"  ✅ Already correct (no wrong UUIDs found)")
            skipped_count += 1
            continue

        logger.info(f"  🔍 Found {len(found_uuids)} different UUID(s) to replace:")
        for wrong_uuid in found_uuids:
            logger.info(f"     - {wrong_uuid}")

        try:
            # Fix the HTML
            fixed_html, replacements = fix_website_id_in_html(html_content, website_id)
            total_replacements += replacements

            if replacements > 0:
                # Update in database
                update_response = supabase.table('websites').update({
                    'html_content': fixed_html
                }).eq('id', website_id).execute()

                logger.info(f"  ✅ Fixed {replacements} reference(s) and updated database")
                fixed_count += 1
            else:
                logger.warning(f"  ⚠️  No fixable patterns found (UUIDs may be in other contexts)")
                skipped_count += 1

        except Exception as e:
            logger.error(f"  ❌ Error: {str(e)}")
            error_count += 1

        logger.info("")

    # Summary
    logger.info("=" * 80)
    logger.info("📊 SUMMARY")
    logger.info("=" * 80)
    logger.info(f"Total websites checked:    {len(websites)}")
    logger.info(f"✅ Fixed:                  {fixed_count}")
    logger.info(f"⏭️  Skipped:                {skipped_count}")
    logger.info(f"❌ Errors:                 {error_count}")
    logger.info(f"🔧 Total replacements:     {total_replacements}")
    logger.info("=" * 80)

    if fixed_count > 0:
        logger.info("✅ Website ID mismatches have been fixed!")
    else:
        logger.info("ℹ️  No websites needed fixing")


def main():
    """Main entry point"""
    asyncio.run(fix_all_websites())


if __name__ == "__main__":
    main()
