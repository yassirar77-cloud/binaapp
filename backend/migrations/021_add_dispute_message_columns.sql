-- ==========================================================================
-- MIGRATION 021: Add columns to dispute_messages table
-- ==========================================================================
-- Adds read_at, updated_at, status, and reply_to columns to support
-- message read receipts, threading, and status tracking.
-- ==========================================================================

-- Add new columns (IF NOT EXISTS for idempotency)
ALTER TABLE public.dispute_messages
    ADD COLUMN IF NOT EXISTS read_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW(),
    ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'sent',
    ADD COLUMN IF NOT EXISTS reply_to UUID;

-- Add foreign key constraint for reply_to (self-referencing)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'fk_dispute_messages_reply_to'
    ) THEN
        ALTER TABLE public.dispute_messages
            ADD CONSTRAINT fk_dispute_messages_reply_to
            FOREIGN KEY (reply_to) REFERENCES public.dispute_messages(id)
            ON DELETE SET NULL;
    END IF;
END $$;

-- Index for reply threading
CREATE INDEX IF NOT EXISTS idx_dispute_messages_reply_to
    ON public.dispute_messages(reply_to);

-- Index for unread message queries
CREATE INDEX IF NOT EXISTS idx_dispute_messages_read_at
    ON public.dispute_messages(read_at)
    WHERE read_at IS NULL;

-- Index for message status
CREATE INDEX IF NOT EXISTS idx_dispute_messages_status
    ON public.dispute_messages(status);

-- Add updated_at trigger for dispute_messages
CREATE OR REPLACE FUNCTION update_dispute_message_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS update_dispute_messages_updated_at ON public.dispute_messages;
CREATE TRIGGER update_dispute_messages_updated_at
    BEFORE UPDATE ON public.dispute_messages
    FOR EACH ROW EXECUTE FUNCTION update_dispute_message_updated_at();

-- Allow authenticated users to update messages (for read receipts, status)
GRANT UPDATE ON public.dispute_messages TO authenticated;

-- RLS policy for updates
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE tablename = 'dispute_messages' AND policyname = 'Anyone can update dispute messages'
    ) THEN
        CREATE POLICY "Anyone can update dispute messages"
            ON public.dispute_messages FOR UPDATE
            USING (true);
    END IF;
END $$;

-- Reload PostgREST schema cache
NOTIFY pgrst, 'reload schema';

-- ==========================================================================
-- MIGRATION 021 COMPLETE
-- ==========================================================================
