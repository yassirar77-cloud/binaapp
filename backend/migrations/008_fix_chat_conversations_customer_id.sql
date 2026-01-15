-- Fix chat_conversations customer_id column schema cache issue
-- This migration ensures the customer_id column exists and refreshes PostgREST schema cache

-- Ensure customer_id column exists (idempotent - safe to run multiple times)
ALTER TABLE chat_conversations ADD COLUMN IF NOT EXISTS customer_id TEXT;

-- Make customer_id NOT NULL (if adding, set default for existing rows first)
DO $$
BEGIN
    -- Update any NULL customer_id values with a placeholder
    UPDATE chat_conversations
    SET customer_id = COALESCE(customer_id, 'customer_' || customer_phone, 'customer_unknown_' || id::TEXT)
    WHERE customer_id IS NULL;

    -- Now make it NOT NULL
    ALTER TABLE chat_conversations ALTER COLUMN customer_id SET NOT NULL;
EXCEPTION
    WHEN OTHERS THEN
        -- Column might already be NOT NULL, which is fine
        RAISE NOTICE 'customer_id column constraints already set or error occurred: %', SQLERRM;
END $$;

-- Ensure the index exists
CREATE INDEX IF NOT EXISTS idx_chat_conversations_customer ON chat_conversations(customer_id);

-- CRITICAL: Notify PostgREST to reload the schema cache
-- This resolves the PGRST204 error
NOTIFY pgrst, 'reload schema';

-- Verify the column exists
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
        RAISE EXCEPTION 'FAILED: customer_id column not found in chat_conversations table';
    END IF;
END $$;
