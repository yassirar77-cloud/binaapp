#!/usr/bin/env python3
"""
Fix chat_conversations customer_id column schema cache issue
Ensures the column exists and refreshes PostgREST schema
"""

import os
import sys
from supabase import create_client, Client

def get_supabase_client() -> Client:
    """Get Supabase client using environment variables"""
    SUPABASE_URL = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY = (
        os.getenv("SUPABASE_SERVICE_KEY") or
        os.getenv("SUPABASE_SERVICE_ROLE_KEY") or
        os.getenv("SUPABASE_KEY") or
        os.getenv("SUPABASE_ANON_KEY") or
        ""
    )

    if not SUPABASE_URL or not SUPABASE_KEY:
        print("❌ Error: SUPABASE_URL and SUPABASE_KEY environment variables must be set")
        sys.exit(1)

    return create_client(SUPABASE_URL, SUPABASE_KEY)


def fix_chat_customer_id():
    """Apply the fix migration"""
    print("🔧 Fixing chat_conversations customer_id column schema cache issue...")
    print()

    supabase = get_supabase_client()

    # Read the migration SQL
    migration_path = "backend/migrations/008_fix_chat_conversations_customer_id.sql"

    if not os.path.exists(migration_path):
        print(f"❌ Migration file not found: {migration_path}")
        sys.exit(1)

    with open(migration_path, 'r') as f:
        sql_content = f.read()

    print(f"📄 Loaded migration from: {migration_path}")
    print()

    # Execute the migration using rpc
    try:
        print("⏳ Executing migration...")

        # Split the SQL into individual statements for better error handling
        statements = [
            # Ensure customer_id column exists
            """
            ALTER TABLE chat_conversations ADD COLUMN IF NOT EXISTS customer_id TEXT;
            """,

            # Update NULL values and set NOT NULL constraint
            """
            DO $$
            BEGIN
                UPDATE chat_conversations
                SET customer_id = COALESCE(customer_id, 'customer_' || customer_phone, 'customer_unknown_' || id::TEXT)
                WHERE customer_id IS NULL;

                ALTER TABLE chat_conversations ALTER COLUMN customer_id SET NOT NULL;
            EXCEPTION
                WHEN OTHERS THEN
                    RAISE NOTICE 'customer_id column constraints already set: %', SQLERRM;
            END $$;
            """,

            # Ensure index exists
            """
            CREATE INDEX IF NOT EXISTS idx_chat_conversations_customer ON chat_conversations(customer_id);
            """,

            # CRITICAL: Notify PostgREST to reload schema
            """
            NOTIFY pgrst, 'reload schema';
            """,

            # Verify column exists
            """
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1
                    FROM information_schema.columns
                    WHERE table_name = 'chat_conversations'
                    AND column_name = 'customer_id'
                ) THEN
                    RAISE NOTICE 'SUCCESS: customer_id column exists in chat_conversations table';
                ELSE
                    RAISE EXCEPTION 'FAILED: customer_id column not found';
                END IF;
            END $$;
            """
        ]

        # Execute each statement
        for i, statement in enumerate(statements, 1):
            print(f"   Step {i}/{len(statements)}...")
            try:
                # Use the RPC endpoint to execute raw SQL
                result = supabase.rpc('exec_sql', {'sql': statement}).execute()
                print(f"   ✅ Step {i} completed")
            except Exception as e:
                error_msg = str(e)
                if "does not exist" in error_msg and "exec_sql" in error_msg:
                    print(f"   ⚠️  RPC method not available. Please run the migration manually in Supabase SQL Editor.")
                    print()
                    print("=" * 70)
                    print("📋 MANUAL FIX REQUIRED:")
                    print("=" * 70)
                    print()
                    print("1. Go to https://app.supabase.com")
                    print("2. Select your BinaApp project")
                    print("3. Click 'SQL Editor' in the left sidebar")
                    print("4. Click 'New Query'")
                    print(f"5. Copy and paste the contents of: {migration_path}")
                    print("6. Click 'Run' (or press Ctrl+Enter / Cmd+Enter)")
                    print()
                    print("=" * 70)
                    return
                else:
                    print(f"   ⚠️  Step {i} warning: {error_msg}")

        print()
        print("✅ Migration completed successfully!")
        print()
        print("🔄 PostgREST schema cache has been refreshed")
        print("✅ customer_id column is now available in the schema")
        print()
        print("🎉 The chat conversation creation should now work!")

    except Exception as e:
        print(f"❌ Error executing migration: {e}")
        print()
        print("Please run the migration manually in Supabase SQL Editor:")
        print(f"   File: {migration_path}")
        sys.exit(1)


if __name__ == "__main__":
    print()
    print("=" * 70)
    print("  BinaApp - Fix Chat Conversations customer_id Column")
    print("=" * 70)
    print()

    fix_chat_customer_id()

    print()
    print("=" * 70)
