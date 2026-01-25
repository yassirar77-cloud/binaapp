#!/usr/bin/env python3
"""
Sync Websites Between Supabase Storage and Database

This script identifies and fixes websites that exist in Storage but are missing
from the database, which can cause foreign key constraint errors when customers
try to place orders.

Usage:
    python scripts/sync_websites_storage_db.py --dry-run    # Check without making changes
    python scripts/sync_websites_storage_db.py              # Fix orphaned websites

Environment Variables Required:
    SUPABASE_URL - Your Supabase project URL
    SUPABASE_SERVICE_ROLE_KEY - Service role key for admin access
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


class WebsiteSyncService:
    """Service for syncing websites between Storage and Database"""

    def __init__(self):
        self.url = os.getenv("SUPABASE_URL", "")
        self.service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "") or os.getenv("SUPABASE_SERVICE_KEY", "")
        self.bucket_name = os.getenv("STORAGE_BUCKET_NAME", "websites")

        if not self.url or not self.service_key:
            raise RuntimeError("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY environment variables")

        self.headers = {
            "apikey": self.service_key,
            "Authorization": f"Bearer {self.service_key}",
            "Content-Type": "application/json"
        }

    async def list_storage_folders(self) -> List[str]:
        """List all top-level folders in the websites storage bucket"""
        try:
            url = f"{self.url}/storage/v1/object/list/{self.bucket_name}"

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    headers=self.headers,
                    json={
                        "prefix": "",
                        "limit": 1000,
                        "offset": 0,
                        "sortBy": {"column": "name", "order": "asc"}
                    },
                    timeout=30.0
                )

            if response.status_code == 200:
                items = response.json()
                # Get folder names (subdomains - no file extension)
                folders = []
                for item in items:
                    name = item.get("name", "")
                    if name and item.get("metadata") is None:  # It's a folder
                        folders.append(name)
                    elif name and not name.endswith(".html") and not name.endswith(".css") and not name.endswith(".js"):
                        # Also include items that look like folders
                        folders.append(name)
                return folders
            else:
                print(f"❌ Failed to list storage: {response.status_code} - {response.text}")
                return []
        except Exception as e:
            print(f"❌ Error listing storage: {e}")
            return []

    async def list_db_websites(self) -> Dict[str, Dict]:
        """Get all websites from the database as a dict keyed by subdomain"""
        try:
            url = f"{self.url}/rest/v1/websites"
            params = {"select": "id,subdomain,user_id,business_name,status"}

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url,
                    headers=self.headers,
                    params=params
                )

            if response.status_code == 200:
                websites = response.json()
                return {w["subdomain"]: w for w in websites if w.get("subdomain")}
            else:
                print(f"❌ Failed to list websites: {response.status_code}")
                return {}
        except Exception as e:
            print(f"❌ Error listing websites: {e}")
            return {}

    async def get_storage_file_content(self, path: str) -> Optional[str]:
        """Get content of a file from storage"""
        try:
            url = f"{self.url}/storage/v1/object/public/{self.bucket_name}/{path}"

            async with httpx.AsyncClient() as client:
                response = await client.get(url, timeout=30.0)

            if response.status_code == 200:
                return response.text
            return None
        except Exception as e:
            print(f"❌ Error getting file content: {e}")
            return None

    async def extract_website_id_from_html(self, subdomain: str) -> Optional[str]:
        """Try to extract website_id from the stored HTML content"""
        html_content = await self.get_storage_file_content(f"{subdomain}/index.html")

        if not html_content:
            return None

        # Look for data-website-id attribute
        import re
        match = re.search(r'data-website-id=["\']([a-f0-9-]{36})["\']', html_content, re.IGNORECASE)
        if match:
            return match.group(1)

        # Look for /delivery/{uuid} pattern
        match = re.search(r'/delivery/([a-f0-9-]{36})', html_content, re.IGNORECASE)
        if match:
            return match.group(1)

        return None

    async def create_missing_website(
        self,
        subdomain: str,
        website_id: Optional[str] = None,
        user_id: Optional[str] = None,
        business_name: Optional[str] = None
    ) -> Optional[Dict]:
        """Create a missing website record in the database"""
        import uuid

        try:
            # Use provided website_id or generate new one
            if not website_id:
                website_id = str(uuid.uuid4())

            # Derive business name from subdomain if not provided
            if not business_name:
                business_name = subdomain.replace("-", " ").replace("_", " ").title()

            website_data = {
                "id": website_id,
                "subdomain": subdomain,
                "business_name": business_name,
                "status": "published",
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
                print(f"❌ Failed to create website: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            print(f"❌ Error creating website: {e}")
            return None

    async def sync(self, dry_run: bool = True) -> Dict:
        """
        Sync websites between Storage and Database

        Args:
            dry_run: If True, only report issues without making changes

        Returns:
            Summary of sync operation
        """
        print("=" * 60)
        print("BINAAPP WEBSITE SYNC")
        print(f"Mode: {'DRY RUN (no changes)' if dry_run else 'LIVE (making changes)'}")
        print("=" * 60)
        print()

        # Step 1: Get all storage folders
        print("📂 Listing storage folders...")
        storage_folders = await self.list_storage_folders()
        print(f"   Found {len(storage_folders)} folders in storage")

        # Step 2: Get all database websites
        print("🗄️  Listing database websites...")
        db_websites = await self.list_db_websites()
        print(f"   Found {len(db_websites)} websites in database")

        # Step 3: Find orphaned websites (in storage but not in DB)
        orphaned = []
        for folder in storage_folders:
            if folder not in db_websites:
                # Skip if it looks like a user_id (UUID)
                if len(folder) == 36 and folder.count("-") == 4:
                    continue
                orphaned.append(folder)

        print()
        print(f"🔍 Found {len(orphaned)} orphaned websites (in Storage, not in DB)")

        if not orphaned:
            print("✅ All websites are synced!")
            return {
                "status": "synced",
                "storage_count": len(storage_folders),
                "db_count": len(db_websites),
                "orphaned": 0,
                "fixed": 0
            }

        # Step 4: Report or fix orphaned websites
        fixed = []
        failed = []

        for subdomain in orphaned:
            print()
            print(f"📋 Orphaned: {subdomain}")

            # Try to extract website_id from HTML
            website_id = await self.extract_website_id_from_html(subdomain)
            if website_id:
                print(f"   Found website_id in HTML: {website_id}")
            else:
                print(f"   No website_id found in HTML - will generate new one")

            if dry_run:
                print(f"   [DRY RUN] Would create database record for: {subdomain}")
            else:
                # Create the missing record
                result = await self.create_missing_website(
                    subdomain=subdomain,
                    website_id=website_id
                )
                if result:
                    print(f"   ✅ Created: {result.get('id')}")
                    fixed.append(subdomain)
                else:
                    print(f"   ❌ Failed to create record")
                    failed.append(subdomain)

        # Summary
        print()
        print("=" * 60)
        print("SYNC SUMMARY")
        print("=" * 60)
        print(f"Storage folders: {len(storage_folders)}")
        print(f"Database websites: {len(db_websites)}")
        print(f"Orphaned found: {len(orphaned)}")
        if not dry_run:
            print(f"Fixed: {len(fixed)}")
            print(f"Failed: {len(failed)}")
            if failed:
                print(f"Failed subdomains: {', '.join(failed)}")

        return {
            "status": "completed",
            "storage_count": len(storage_folders),
            "db_count": len(db_websites),
            "orphaned": len(orphaned),
            "fixed": len(fixed),
            "failed": len(failed),
            "orphaned_subdomains": orphaned,
            "fixed_subdomains": fixed,
            "failed_subdomains": failed
        }


async def main():
    parser = argparse.ArgumentParser(
        description="Sync BinaApp websites between Storage and Database"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Check without making changes (default)"
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Actually fix orphaned websites by creating database records"
    )

    args = parser.parse_args()

    # Default to dry-run unless --fix is specified
    dry_run = not args.fix

    try:
        sync_service = WebsiteSyncService()
        result = await sync_service.sync(dry_run=dry_run)

        if result["orphaned"] > 0 and dry_run:
            print()
            print("💡 To fix orphaned websites, run:")
            print("   python scripts/sync_websites_storage_db.py --fix")

        return 0 if result.get("failed", 0) == 0 else 1

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
