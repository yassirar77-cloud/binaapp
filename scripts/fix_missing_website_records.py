#!/usr/bin/env python3
"""
Fix Missing Website Records - One-time Script

This script fixes specific known orphaned websites by creating their
database records with the correct website_id.

The issue: Website exists in Storage with a specific website_id in the HTML,
but the database record is missing, causing foreign key constraint errors
when customers try to place orders.

Known Issue:
- Website: wowo.binaapp.my
- Website ID: 22d8d212-1834-48a2-97a5-0062105da61e
- Error: "delivery_orders_website_id_fkey" violation

Usage:
    python scripts/fix_missing_website_records.py --dry-run  # Check without changes
    python scripts/fix_missing_website_records.py            # Apply fix
"""

import asyncio
import os
import sys
import argparse
from datetime import datetime
from typing import List, Dict, Optional

# Add backend to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

import httpx
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


# Known orphaned websites to fix
# Format: {"subdomain": {"website_id": "...", "business_name": "...", "user_id": "..." (optional)}}
KNOWN_ORPHANED_WEBSITES = {
    "wowo": {
        "website_id": "22d8d212-1834-48a2-97a5-0062105da61e",
        "business_name": "Wowo",
        "user_id": None  # Unknown - will be set to system default or left null
    }
}


class WebsiteFixService:
    """Service for fixing missing website records"""

    def __init__(self):
        self.url = os.getenv("SUPABASE_URL", "")
        self.service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "") or os.getenv("SUPABASE_SERVICE_KEY", "")

        if not self.url or not self.service_key:
            raise RuntimeError("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY environment variables")

        self.headers = {
            "apikey": self.service_key,
            "Authorization": f"Bearer {self.service_key}",
            "Content-Type": "application/json"
        }

    async def check_website_exists(self, website_id: str) -> Optional[Dict]:
        """Check if a website record exists in the database"""
        try:
            url = f"{self.url}/rest/v1/websites"
            params = {"id": f"eq.{website_id}", "select": "id,subdomain,business_name,status"}

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url,
                    headers=self.headers,
                    params=params
                )

            if response.status_code == 200:
                records = response.json()
                return records[0] if records else None
            return None
        except Exception as e:
            print(f"❌ Error checking website: {e}")
            return None

    async def check_subdomain_exists(self, subdomain: str) -> Optional[Dict]:
        """Check if a subdomain is already in use"""
        try:
            url = f"{self.url}/rest/v1/websites"
            params = {"subdomain": f"eq.{subdomain}", "select": "id,subdomain,business_name"}

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url,
                    headers=self.headers,
                    params=params
                )

            if response.status_code == 200:
                records = response.json()
                return records[0] if records else None
            return None
        except Exception as e:
            print(f"❌ Error checking subdomain: {e}")
            return None

    async def create_website_record(
        self,
        website_id: str,
        subdomain: str,
        business_name: str,
        user_id: Optional[str] = None
    ) -> Optional[Dict]:
        """Create a website record with a specific ID"""
        try:
            website_data = {
                "id": website_id,
                "subdomain": subdomain,
                "business_name": business_name,
                "status": "published",
                "include_ecommerce": True,  # Assume e-commerce since they're trying to order
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }

            if user_id:
                website_data["user_id"] = user_id

            url = f"{self.url}/rest/v1/websites"

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    headers={**self.headers, "Prefer": "return=representation"},
                    json=website_data
                )

            if response.status_code in [200, 201]:
                result = response.json()
                return result[0] if isinstance(result, list) else result
            else:
                print(f"❌ Failed to create: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            print(f"❌ Error creating website: {e}")
            return None

    async def fix_websites(self, dry_run: bool = True) -> Dict:
        """Fix known orphaned websites"""
        print("=" * 60)
        print("FIX MISSING WEBSITE RECORDS")
        print(f"Mode: {'DRY RUN (no changes)' if dry_run else 'LIVE (applying fixes)'}")
        print("=" * 60)
        print()

        results = {
            "checked": 0,
            "already_exists": [],
            "fixed": [],
            "failed": []
        }

        for subdomain, config in KNOWN_ORPHANED_WEBSITES.items():
            website_id = config["website_id"]
            business_name = config["business_name"]
            user_id = config.get("user_id")

            print(f"📋 Checking: {subdomain}")
            print(f"   Expected ID: {website_id}")
            results["checked"] += 1

            # Check if website already exists by ID
            existing = await self.check_website_exists(website_id)
            if existing:
                print(f"   ✅ Already exists in database!")
                print(f"      Subdomain: {existing.get('subdomain')}")
                print(f"      Status: {existing.get('status')}")
                results["already_exists"].append(subdomain)
                continue

            # Check if subdomain is already in use by different ID
            existing_subdomain = await self.check_subdomain_exists(subdomain)
            if existing_subdomain:
                print(f"   ⚠️  Subdomain '{subdomain}' already in use by different website:")
                print(f"      ID: {existing_subdomain.get('id')}")
                print(f"      This may indicate a duplicate - skipping")
                results["failed"].append(subdomain)
                continue

            # Website doesn't exist - create it
            if dry_run:
                print(f"   [DRY RUN] Would create record:")
                print(f"      ID: {website_id}")
                print(f"      Subdomain: {subdomain}")
                print(f"      Business: {business_name}")
                results["fixed"].append(subdomain)  # Count as would-be-fixed
            else:
                print(f"   Creating record...")
                result = await self.create_website_record(
                    website_id=website_id,
                    subdomain=subdomain,
                    business_name=business_name,
                    user_id=user_id
                )
                if result:
                    print(f"   ✅ Created successfully!")
                    print(f"      ID: {result.get('id')}")
                    print(f"      URL: https://{subdomain}.binaapp.my")
                    results["fixed"].append(subdomain)
                else:
                    print(f"   ❌ Failed to create record")
                    results["failed"].append(subdomain)

            print()

        # Summary
        print("=" * 60)
        print("SUMMARY")
        print("=" * 60)
        print(f"Checked: {results['checked']}")
        print(f"Already exists: {len(results['already_exists'])}")
        if dry_run:
            print(f"Would fix: {len(results['fixed'])}")
        else:
            print(f"Fixed: {len(results['fixed'])}")
        print(f"Failed: {len(results['failed'])}")

        if results["failed"]:
            print()
            print("⚠️  Failed websites need manual investigation:")
            for subdomain in results["failed"]:
                print(f"   - {subdomain}")

        return results


async def discover_orphaned_websites():
    """Discover orphaned websites by scanning storage"""
    print("=" * 60)
    print("DISCOVERING ORPHANED WEBSITES")
    print("=" * 60)
    print()
    print("For discovery, use the sync script:")
    print("  python scripts/sync_websites_storage_db.py --dry-run")
    print()
    print("This script fixes KNOWN orphaned websites defined in:")
    print("  KNOWN_ORPHANED_WEBSITES dictionary")
    print()
    print("Currently known orphaned websites:")
    for subdomain, config in KNOWN_ORPHANED_WEBSITES.items():
        print(f"  - {subdomain} (ID: {config['website_id']})")


async def main():
    parser = argparse.ArgumentParser(
        description="Fix known missing website records in BinaApp database"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Check without making changes (default behavior)"
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Actually apply the fixes"
    )
    parser.add_argument(
        "--discover",
        action="store_true",
        help="Show how to discover orphaned websites"
    )

    args = parser.parse_args()

    if args.discover:
        await discover_orphaned_websites()
        return 0

    # Default to dry-run unless --fix is specified
    dry_run = not args.fix

    try:
        fix_service = WebsiteFixService()
        results = await fix_service.fix_websites(dry_run=dry_run)

        if dry_run and results["fixed"]:
            print()
            print("💡 To apply these fixes, run:")
            print("   python scripts/fix_missing_website_records.py --fix")

        return 0 if len(results["failed"]) == 0 else 1

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
