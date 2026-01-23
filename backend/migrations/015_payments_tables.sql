-- =============================================
-- Migration: Payment Tables
-- Description: Creates tables for tracking payments and addon purchases
-- =============================================

-- Create payments table for subscription payments
CREATE TABLE IF NOT EXISTS public.payments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    bill_code VARCHAR(100) NOT NULL,
    amount DECIMAL(10, 2) NOT NULL,
    type VARCHAR(50) NOT NULL DEFAULT 'subscription',
    tier VARCHAR(50),
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    transaction_id VARCHAR(100),
    reference_no VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create addon_purchases table
CREATE TABLE IF NOT EXISTS public.addon_purchases (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    bill_code VARCHAR(100) NOT NULL,
    addon_type VARCHAR(50) NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 1,
    amount DECIMAL(10, 2) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    transaction_id VARCHAR(100),
    reference_no VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for faster lookups
CREATE INDEX IF NOT EXISTS idx_payments_user_id ON public.payments(user_id);
CREATE INDEX IF NOT EXISTS idx_payments_bill_code ON public.payments(bill_code);
CREATE INDEX IF NOT EXISTS idx_payments_status ON public.payments(status);

CREATE INDEX IF NOT EXISTS idx_addon_purchases_user_id ON public.addon_purchases(user_id);
CREATE INDEX IF NOT EXISTS idx_addon_purchases_bill_code ON public.addon_purchases(bill_code);

-- Enable RLS
ALTER TABLE public.payments ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.addon_purchases ENABLE ROW LEVEL SECURITY;

-- RLS Policies for payments
CREATE POLICY "Users can view their own payments"
    ON public.payments FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Service role can manage all payments"
    ON public.payments FOR ALL
    USING (auth.role() = 'service_role');

-- RLS Policies for addon_purchases
CREATE POLICY "Users can view their own addon purchases"
    ON public.addon_purchases FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Service role can manage all addon purchases"
    ON public.addon_purchases FOR ALL
    USING (auth.role() = 'service_role');

-- Updated at trigger
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS update_payments_updated_at ON public.payments;
CREATE TRIGGER update_payments_updated_at
    BEFORE UPDATE ON public.payments
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_addon_purchases_updated_at ON public.addon_purchases;
CREATE TRIGGER update_addon_purchases_updated_at
    BEFORE UPDATE ON public.addon_purchases
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Comments
COMMENT ON TABLE public.payments IS 'Tracks subscription payment transactions via ToyyibPay';
COMMENT ON TABLE public.addon_purchases IS 'Tracks addon purchase transactions';
