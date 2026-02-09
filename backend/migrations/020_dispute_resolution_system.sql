-- ==========================================================================
-- MIGRATION 020: AI Dispute Resolution System (Phase 1)
-- ==========================================================================
-- Adds tables for customer dispute creation, AI-powered analysis,
-- and resolution workflow for the BinaApp delivery platform.
-- ==========================================================================

-- ===================================
-- Disputes Table
-- ===================================
CREATE TABLE IF NOT EXISTS public.disputes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    dispute_number TEXT UNIQUE NOT NULL,  -- Auto-generated: DSP-20260209-0001
    order_id UUID REFERENCES public.delivery_orders(id) ON DELETE CASCADE NOT NULL,
    website_id UUID REFERENCES public.websites(id) ON DELETE CASCADE NOT NULL,

    -- Parties
    customer_id TEXT NOT NULL,           -- Phone or user ID
    customer_name TEXT NOT NULL,
    customer_phone TEXT,
    customer_email TEXT,
    owner_id UUID REFERENCES auth.users(id),

    -- Dispute Details
    category TEXT NOT NULL,
    /* Categories:
       'wrong_items'      - Received wrong items
       'missing_items'    - Items missing from order
       'quality_issue'    - Food quality problem
       'late_delivery'    - Delivery took too long
       'damaged_items'    - Items arrived damaged
       'overcharged'      - Charged more than expected
       'never_delivered'  - Order never arrived
       'rider_issue'      - Problem with delivery rider
       'other'            - Other issues
    */

    description TEXT NOT NULL,           -- Customer's description of the issue
    evidence_urls TEXT[],                -- Photos/screenshots as evidence

    -- Amounts
    order_amount DECIMAL(10,2) NOT NULL, -- Original order total
    disputed_amount DECIMAL(10,2),       -- Amount in dispute
    refund_amount DECIMAL(10,2),         -- Final refund amount (if any)

    -- AI Analysis
    ai_category_confidence DECIMAL(3,2), -- AI confidence in category (0.00-1.00)
    ai_severity_score INTEGER,           -- 1-10 severity rating from AI
    ai_recommendation TEXT,              -- AI suggested resolution
    ai_analysis JSONB,                   -- Full AI analysis payload

    -- Resolution
    status TEXT DEFAULT 'open',
    /* Status flow:
       open → under_review → awaiting_response → resolved → closed
       OR: escalated, rejected
    */
    resolution_type TEXT,
    /* Resolution types:
       'full_refund'      - Full refund issued
       'partial_refund'   - Partial refund issued
       'replacement'      - Replacement order
       'credit'           - Store credit issued
       'apology'          - Apology / no compensation
       'rejected'         - Dispute rejected (no merit)
       'escalated'        - Escalated to platform admin
    */
    resolution_notes TEXT,               -- Notes about the resolution
    resolved_by TEXT,                    -- 'ai', 'owner', 'admin', 'system'

    -- Priority
    priority TEXT DEFAULT 'medium',      -- 'low', 'medium', 'high', 'urgent'

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    reviewed_at TIMESTAMPTZ,
    resolved_at TIMESTAMPTZ,
    closed_at TIMESTAMPTZ
);

-- Indexes
CREATE INDEX idx_disputes_order ON public.disputes(order_id);
CREATE INDEX idx_disputes_website ON public.disputes(website_id);
CREATE INDEX idx_disputes_status ON public.disputes(status);
CREATE INDEX idx_disputes_category ON public.disputes(category);
CREATE INDEX idx_disputes_priority ON public.disputes(priority);
CREATE INDEX idx_disputes_created ON public.disputes(created_at DESC);
CREATE INDEX idx_disputes_customer ON public.disputes(customer_phone);
CREATE INDEX idx_disputes_number ON public.disputes(dispute_number);

-- RLS
ALTER TABLE public.disputes ENABLE ROW LEVEL SECURITY;

-- Business owners can view disputes for their orders
CREATE POLICY "Owners can view own disputes"
    ON public.disputes FOR SELECT
    USING (
        website_id IN (SELECT id FROM public.websites WHERE user_id = auth.uid())
    );

-- Business owners can update disputes for their orders
CREATE POLICY "Owners can update own disputes"
    ON public.disputes FOR UPDATE
    USING (
        website_id IN (SELECT id FROM public.websites WHERE user_id = auth.uid())
    );

-- Anyone can create disputes (customers)
CREATE POLICY "Anyone can create disputes"
    ON public.disputes FOR INSERT
    WITH CHECK (true);

-- Anyone can view disputes (filtered in application layer by order_number)
CREATE POLICY "Anyone can view disputes"
    ON public.disputes FOR SELECT
    USING (true);


-- ===================================
-- Dispute Messages Table
-- ===================================
CREATE TABLE IF NOT EXISTS public.dispute_messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    dispute_id UUID REFERENCES public.disputes(id) ON DELETE CASCADE NOT NULL,

    -- Sender
    sender_type TEXT NOT NULL DEFAULT 'user',  -- 'customer', 'owner', 'admin', 'ai', 'system', 'user'
    sender_id TEXT,
    sender_name TEXT,

    -- Content
    message TEXT NOT NULL,
    attachments TEXT[],                  -- URLs to attached files

    -- Metadata
    is_internal BOOLEAN DEFAULT false,   -- Internal notes (not visible to customer)
    metadata JSONB,                      -- Extra data (AI analysis results, etc.)

    -- Read & Status Tracking
    read_at TIMESTAMPTZ,                 -- When the message was read
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    status TEXT DEFAULT 'sent',          -- 'sent', 'delivered', 'read'
    reply_to UUID REFERENCES public.dispute_messages(id) ON DELETE SET NULL,  -- Threading

    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_dispute_messages_dispute ON public.dispute_messages(dispute_id);
CREATE INDEX idx_dispute_messages_created ON public.dispute_messages(created_at DESC);
CREATE INDEX idx_dispute_messages_sender ON public.dispute_messages(sender_type);
CREATE INDEX idx_dispute_messages_reply_to ON public.dispute_messages(reply_to);
CREATE INDEX idx_dispute_messages_read_at ON public.dispute_messages(read_at) WHERE read_at IS NULL;
CREATE INDEX idx_dispute_messages_status ON public.dispute_messages(status);

ALTER TABLE public.dispute_messages ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Anyone can view dispute messages"
    ON public.dispute_messages FOR SELECT
    USING (true);

CREATE POLICY "Anyone can insert dispute messages"
    ON public.dispute_messages FOR INSERT
    WITH CHECK (true);


-- ===================================
-- Dispute Status History
-- ===================================
CREATE TABLE IF NOT EXISTS public.dispute_status_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    dispute_id UUID REFERENCES public.disputes(id) ON DELETE CASCADE NOT NULL,

    old_status TEXT,
    new_status TEXT NOT NULL,
    changed_by TEXT,                     -- 'customer', 'owner', 'admin', 'ai', 'system'
    notes TEXT,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_dispute_status_history_dispute ON public.dispute_status_history(dispute_id);
CREATE INDEX idx_dispute_status_history_time ON public.dispute_status_history(created_at DESC);

ALTER TABLE public.dispute_status_history ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Anyone can view dispute status history"
    ON public.dispute_status_history FOR SELECT
    USING (true);

CREATE POLICY "Anyone can insert dispute status history"
    ON public.dispute_status_history FOR INSERT
    WITH CHECK (true);


-- ===================================
-- Functions
-- ===================================

-- Generate Dispute Number
CREATE OR REPLACE FUNCTION generate_dispute_number()
RETURNS TEXT AS $$
DECLARE
    new_number TEXT;
    counter INTEGER;
BEGIN
    SELECT COUNT(*) INTO counter
    FROM public.disputes
    WHERE DATE(created_at) = CURRENT_DATE;

    new_number := 'DSP-' || TO_CHAR(CURRENT_DATE, 'YYYYMMDD') || '-' || LPAD((counter + 1)::TEXT, 4, '0');
    RETURN new_number;
END;
$$ LANGUAGE plpgsql;

-- Auto-generate Dispute Number
CREATE OR REPLACE FUNCTION set_dispute_number()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.dispute_number IS NULL OR NEW.dispute_number = '' THEN
        NEW.dispute_number := generate_dispute_number();
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER set_dispute_number_trigger
    BEFORE INSERT ON public.disputes
    FOR EACH ROW EXECUTE FUNCTION set_dispute_number();

-- Log Dispute Status Changes
CREATE OR REPLACE FUNCTION log_dispute_status_change()
RETURNS TRIGGER AS $$
BEGIN
    IF (TG_OP = 'UPDATE' AND OLD.status IS DISTINCT FROM NEW.status) THEN
        INSERT INTO public.dispute_status_history (dispute_id, old_status, new_status, changed_by, notes)
        VALUES (
            NEW.id,
            OLD.status,
            NEW.status,
            'system',
            'Status changed from ' || COALESCE(OLD.status, 'null') || ' to ' || NEW.status
        );
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER log_dispute_status_trigger
    AFTER UPDATE ON public.disputes
    FOR EACH ROW EXECUTE FUNCTION log_dispute_status_change();

-- Updated_at trigger for disputes
CREATE TRIGGER update_disputes_updated_at
    BEFORE UPDATE ON public.disputes
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();


-- ===================================
-- Permissions
-- ===================================

GRANT SELECT, INSERT, UPDATE ON public.disputes TO authenticated;
GRANT SELECT, INSERT, UPDATE ON public.dispute_messages TO authenticated;
GRANT SELECT, INSERT ON public.dispute_status_history TO authenticated;

GRANT SELECT, INSERT ON public.disputes TO anon;
GRANT SELECT, INSERT ON public.dispute_messages TO anon;
GRANT SELECT ON public.dispute_status_history TO anon;

-- Enable realtime for disputes
ALTER PUBLICATION supabase_realtime ADD TABLE public.disputes;
ALTER PUBLICATION supabase_realtime ADD TABLE public.dispute_messages;

-- Comments
COMMENT ON TABLE public.disputes IS 'Customer disputes for delivery orders with AI analysis';
COMMENT ON TABLE public.dispute_messages IS 'Messages in dispute conversations';
COMMENT ON TABLE public.dispute_status_history IS 'Audit trail of dispute status changes';

-- ==========================================================================
-- MIGRATION 020 COMPLETE
-- ==========================================================================
