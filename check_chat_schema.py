#!/usr/bin/env python3
"""
Check the actual schema of chat tables in Supabase
Diagnoses type mismatches and missing tables/columns
"""
import os
import sys
from supabase import create_client

def get_supabase():
    SUPABASE_URL = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY = (
        os.getenv("SUPABASE_SERVICE_KEY") or
        os.getenv("SUPABASE_SERVICE_ROLE_KEY") or
        os.getenv("SUPABASE_KEY") or
        os.getenv("SUPABASE_ANON_KEY") or
        ""
    )

    if not SUPABASE_URL or not SUPABASE_KEY:
        print("ERROR: Supabase credentials not found in environment")
        print("Please set:")
        print("  export SUPABASE_URL='your-url'")
        print("  export SUPABASE_SERVICE_KEY='your-key'")
        sys.exit(1)

    return create_client(SUPABASE_URL, SUPABASE_KEY)

def check_table_schema(supabase, table_name):
    """Check what columns exist in a table"""
    print(f"\n{'='*60}")
    print(f"Table: {table_name}")
    print(f"{'='*60}")

    try:
        # Try to select with limit 0 to check schema
        result = supabase.table(table_name).select("*").limit(0).execute()
        print(f"✓ Table exists and is accessible")

        # Try to get a sample row to see columns
        sample = supabase.table(table_name).select("*").limit(1).execute()
        if sample.data:
            print(f"\nColumns found in sample data:")
            for col in sample.data[0].keys():
                print(f"  - {col}")
        else:
            print("\n⚠ No data in table, cannot determine all columns")

    except Exception as e:
        error = str(e)
        print(f"✗ Error accessing table: {error}")

        if "does not exist" in error.lower():
            print(f"  → Table '{table_name}' does NOT exist in database")
        elif "could not find" in error.lower() or "PGRST204" in error:
            print(f"  → Table exists but schema cache issue or missing columns")
        else:
            print(f"  → Unknown error: {error}")

def check_column_types_via_query(supabase):
    """Check column types using SQL query"""
    print("\n" + "="*60)
    print("Checking Column Types (SQL Query)")
    print("="*60)

    query = """
    SELECT
        table_name,
        column_name,
        data_type
    FROM information_schema.columns
    WHERE table_schema = 'public'
    AND table_name IN ('chat_conversations', 'chat_messages', 'chat_participants')
    AND column_name IN ('id', 'conversation_id')
    ORDER BY table_name, column_name;
    """

    try:
        # Note: Most Supabase clients don't support direct SQL execution
        # This is just to show what needs to be checked
        print("\nRun this SQL in Supabase SQL Editor:")
        print(query)
        print("\nExpected results:")
        print("  chat_conversations | id              | uuid")
        print("  chat_messages      | id              | uuid")
        print("  chat_messages      | conversation_id | uuid")
        print("  chat_participants  | id              | uuid")
        print("  chat_participants  | conversation_id | uuid")
    except Exception as e:
        print(f"Could not check: {e}")

def diagnose_and_recommend(issues):
    """Provide recommendations based on found issues"""
    print("\n" + "="*60)
    print("DIAGNOSIS & RECOMMENDATIONS")
    print("="*60)

    if not issues:
        print("\n✅ No major issues detected!")
        print("If you're still seeing errors, check application logs.")
        return

    print("\n❌ Issues Found:")
    for issue in issues:
        print(f"  - {issue}")

    print("\n📋 Recommended Actions:")

    if any("BIGINT" in issue for issue in issues):
        print("\n⚠️  CRITICAL: Type mismatch detected (BIGINT vs UUID)")
        print("   You need to recreate tables with correct schema.")
        print("   See: FIX_CHAT_SCHEMA_MISMATCH.md")
        print("\n   Quick fix if NO important data:")
        print("     1. DROP existing chat tables")
        print("     2. Run migration 004_chat_system.sql")
        print("     3. Reload schema cache")

    if any("missing" in issue.lower() for issue in issues):
        print("\n⚠️  Missing tables or columns detected")
        print("   Run the appropriate migration:")
        print("     - chat_participants missing: See FIX_CHAT_SCHEMA_MISMATCH.md Option C")
        print("     - Other columns missing: Run migration 013 or 014")

    if any("cache" in issue.lower() for issue in issues):
        print("\n⚠️  Schema cache issue")
        print("   Run in Supabase SQL Editor:")
        print("     NOTIFY pgrst, 'reload schema';")

def main():
    print("BinaApp Chat Schema Inspector")
    print("="*60)
    print("This tool diagnoses chat table schema issues")
    print()

    issues = []

    try:
        supabase = get_supabase()
        print("✓ Connected to Supabase\n")

        # Check all chat-related tables
        tables = [
            "chat_conversations",
            "chat_messages",
            "chat_participants"
        ]

        for table in tables:
            check_table_schema(supabase, table)

        # Try to detect type issues
        print("\n" + "="*60)
        print("Testing for Type Mismatches...")
        print("="*60)

        # Try to query with UUID to detect bigint issue
        try:
            test_uuid = "00000000-0000-0000-0000-000000000000"
            supabase.table("chat_messages").select("id").eq("id", test_uuid).limit(0).execute()
            print("✓ chat_messages.id accepts UUID format")
        except Exception as e:
            error_str = str(e)
            if "bigint" in error_str.lower() or "22P02" in error_str:
                print("✗ BIGINT type mismatch detected!")
                print(f"  Error: {error_str}")
                issues.append("chat_messages has BIGINT IDs instead of UUID")
            elif "does not exist" in error_str.lower():
                print("✗ chat_messages table does not exist")
                issues.append("chat_messages table missing")
            else:
                print(f"⚠ Unexpected error: {error_str}")

        # Check column types via SQL
        check_column_types_via_query(supabase)

        # Provide diagnosis
        diagnose_and_recommend(issues)

    except Exception as e:
        print(f"\nFATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
