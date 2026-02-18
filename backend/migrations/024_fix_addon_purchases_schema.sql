-- =============================================
-- Migration 024: Fix addon_purchases schema
-- =============================================
-- Reconciles migration 005 (intended schema with quantity_used, unit_price, etc.)
-- with migration 015 (production schema missing these columns).
--
-- The application code needs quantity_used to track addon credit consumption,
-- and unit_price/total_price/expires_at for complete purchase records.
-- This migration adds the missing columns without dropping existing data.

-- Add missing columns needed by the application
ALTER TABLE public.addon_purchases
    ADD COLUMN IF NOT EXISTS quantity_used INTEGER DEFAULT 0;

ALTER TABLE public.addon_purchases
    ADD COLUMN IF NOT EXISTS unit_price DECIMAL(10,2);

ALTER TABLE public.addon_purchases
    ADD COLUMN IF NOT EXISTS total_price DECIMAL(10,2);

ALTER TABLE public.addon_purchases
    ADD COLUMN IF NOT EXISTS expires_at TIMESTAMPTZ;

-- Make bill_code nullable — addon purchases created via ToyyibPay callback
-- use a transaction_id link instead of storing bill_code directly
DO $$
BEGIN
    -- Only alter if the column exists and has a NOT NULL constraint
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'addon_purchases'
          AND column_name = 'bill_code'
          AND is_nullable = 'NO'
    ) THEN
        ALTER TABLE public.addon_purchases ALTER COLUMN bill_code DROP NOT NULL;
    END IF;
END $$;

-- Make amount nullable — code uses unit_price/total_price instead
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'addon_purchases'
          AND column_name = 'amount'
          AND is_nullable = 'NO'
    ) THEN
        ALTER TABLE public.addon_purchases ALTER COLUMN amount DROP NOT NULL;
    END IF;
END $$;

-- Change default status from 'pending' to 'active'
-- Addon purchases created after successful payment should be active immediately
ALTER TABLE public.addon_purchases
    ALTER COLUMN status SET DEFAULT 'active';

-- Add missing indexes for query performance
CREATE INDEX IF NOT EXISTS idx_addon_purchases_status ON public.addon_purchases(status);
CREATE INDEX IF NOT EXISTS idx_addon_purchases_type ON public.addon_purchases(addon_type);

-- Backfill: any existing rows with status='pending' that have a matching
-- successful transaction should be marked 'active'
UPDATE public.addon_purchases ap
SET status = 'active'
WHERE ap.status = 'pending'
  AND EXISTS (
      SELECT 1 FROM public.transactions t
      WHERE t.toyyibpay_bill_code = ap.bill_code
        AND t.payment_status = 'success'
  );
