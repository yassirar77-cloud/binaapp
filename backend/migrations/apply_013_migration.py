#!/usr/bin/env python3
"""
Apply migration 013 - Add missing media_url and metadata columns to chat_messages

Usage:
    python apply_013_migration.py

Requirements:
    - SUPABASE_URL environment variable
    - SUPABASE_SERVICE_KEY or SUPABASE_SERVICE_ROLE_KEY environment variable
"""

import os
import sys
from pathlib import Path

# Add parent directory to path to import from app
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from supabase import create_client
except ImportError:
    print("ERROR: supabase-py not installed. Run: pip install supabase")
    sys.exit(1)


def get_supabase_client():
    """Get authenticated Supabase client"""
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = (
        os.getenv("SUPABASE_SERVICE_KEY") or
        os.getenv("SUPABASE_SERVICE_ROLE_KEY") or
        os.getenv("SUPABASE_KEY")
    )

    if not supabase_url:
        print("ERROR: SUPABASE_URL environment variable not set")
        sys.exit(1)

    if not supabase_key:
        print("ERROR: SUPABASE_SERVICE_KEY environment variable not set")
        sys.exit(1)

    return create_client(supabase_url, supabase_key)


def check_columns_exist(supabase):
    """Check if media_url and metadata columns already exist"""
    query = """
    SELECT column_name
    FROM information_schema.columns
    WHERE table_schema = 'public'
    AND table_name = 'chat_messages'
    AND column_name IN ('media_url', 'metadata');
    """

    try:
        result = supabase.rpc('sql', {'query': query}).execute()
        existing_columns = [row['column_name'] for row in result.data] if result.data else []
        return existing_columns
    except Exception as e:
        print(f"Warning: Could not check existing columns: {e}")
        return []


def apply_migration(supabase):
    """Apply the migration SQL"""
    migration_file = Path(__file__).parent / "013_add_missing_chat_columns.sql"

    if not migration_file.exists():
        print(f"ERROR: Migration file not found: {migration_file}")
        sys.exit(1)

    with open(migration_file, 'r') as f:
        sql = f.read()

    print("=" * 60)
    print("Applying Migration 013: Add Missing Chat Columns")
    print("=" * 60)

    # Check current state
    existing = check_columns_exist(supabase)
    if 'media_url' in existing and 'metadata' in existing:
        print("\n✓ Both columns already exist. Migration not needed.")
        return True

    print(f"\nMissing columns: {set(['media_url', 'metadata']) - set(existing)}")
    print("\nExecuting migration SQL...")

    # Note: Supabase Python client doesn't directly support running arbitrary SQL
    # We need to use the REST API's sql endpoint or PostgreSQL connection
    print("\n" + "!" * 60)
    print("IMPORTANT: This script cannot directly execute SQL migrations.")
    print("Please run the migration manually via:")
    print("1. Supabase Dashboard SQL Editor, OR")
    print("2. psql command line tool")
    print("!" * 60)
    print("\nMigration SQL location:")
    print(f"  {migration_file}")
    print("\nSee README_013.md for detailed instructions.")
    print("=" * 60)

    return False


def verify_migration(supabase):
    """Verify that the migration was applied successfully"""
    existing = check_columns_exist(supabase)

    print("\n" + "=" * 60)
    print("Migration Verification")
    print("=" * 60)

    if 'media_url' in existing and 'metadata' in existing:
        print("\n✓ SUCCESS: Both columns exist!")
        print("  - media_url: ✓")
        print("  - metadata: ✓")
        return True
    else:
        print("\n✗ INCOMPLETE: Missing columns:")
        if 'media_url' not in existing:
            print("  - media_url: ✗")
        else:
            print("  - media_url: ✓")

        if 'metadata' not in existing:
            print("  - metadata: ✗")
        else:
            print("  - metadata: ✓")
        return False


def main():
    print("\nBinaApp Migration 013 - Add Missing Chat Columns")
    print("=" * 60)

    try:
        supabase = get_supabase_client()
        print("✓ Connected to Supabase")

        # Check current state
        print("\nChecking current schema...")
        existing = check_columns_exist(supabase)
        print(f"Existing columns: {existing}")

        # Apply migration
        success = apply_migration(supabase)

        if not success:
            print("\nPlease apply the migration manually and run this script again to verify.")
            sys.exit(0)

        # Verify
        if verify_migration(supabase):
            print("\n✓ Migration completed successfully!")
            sys.exit(0)
        else:
            print("\n✗ Migration incomplete. Please check the logs above.")
            sys.exit(1)

    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
