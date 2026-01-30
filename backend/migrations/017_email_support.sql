-- =====================================================
-- Migration: 017_email_support.sql
-- Description: AI Email Support System Tables
-- Date: 2026-01-30
-- =====================================================

-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =====================================================
-- Table: email_threads
-- Stores email conversation threads from customers
-- =====================================================
CREATE TABLE IF NOT EXISTS email_threads (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_email VARCHAR(255) NOT NULL,
    customer_name VARCHAR(255),
    subject TEXT NOT NULL,
    status VARCHAR(50) DEFAULT 'open' CHECK (status IN ('open', 'in_progress', 'resolved', 'escalated', 'closed')),
    priority VARCHAR(20) DEFAULT 'normal' CHECK (priority IN ('low', 'normal', 'high', 'urgent')),
    category VARCHAR(100),
    assigned_to VARCHAR(255),
    first_response_at TIMESTAMP WITH TIME ZONE,
    resolved_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create index for faster lookups
CREATE INDEX IF NOT EXISTS idx_email_threads_customer_email ON email_threads(customer_email);
CREATE INDEX IF NOT EXISTS idx_email_threads_status ON email_threads(status);
CREATE INDEX IF NOT EXISTS idx_email_threads_priority ON email_threads(priority);
CREATE INDEX IF NOT EXISTS idx_email_threads_created_at ON email_threads(created_at DESC);

-- =====================================================
-- Table: email_messages
-- Stores individual messages within email threads
-- =====================================================
CREATE TABLE IF NOT EXISTS email_messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    thread_id UUID NOT NULL REFERENCES email_threads(id) ON DELETE CASCADE,
    sender_email VARCHAR(255) NOT NULL,
    sender_type VARCHAR(50) NOT NULL CHECK (sender_type IN ('customer', 'ai', 'admin', 'support')),
    content TEXT NOT NULL,
    html_content TEXT,
    ai_generated BOOLEAN DEFAULT false,
    ai_confidence DECIMAL(3,2) CHECK (ai_confidence >= 0 AND ai_confidence <= 1),
    ai_model VARCHAR(100),
    message_id VARCHAR(255),
    in_reply_to VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create index for faster lookups
CREATE INDEX IF NOT EXISTS idx_email_messages_thread_id ON email_messages(thread_id);
CREATE INDEX IF NOT EXISTS idx_email_messages_sender_type ON email_messages(sender_type);
CREATE INDEX IF NOT EXISTS idx_email_messages_created_at ON email_messages(created_at);

-- =====================================================
-- Table: ai_escalations
-- Tracks when AI escalates to human support
-- =====================================================
CREATE TABLE IF NOT EXISTS ai_escalations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    thread_id UUID NOT NULL REFERENCES email_threads(id) ON DELETE CASCADE,
    message_id UUID REFERENCES email_messages(id) ON DELETE SET NULL,
    reason TEXT NOT NULL,
    escalation_type VARCHAR(50) CHECK (escalation_type IN ('low_confidence', 'negative_sentiment', 'keyword_trigger', 'repeated_contact', 'manual')),
    confidence_score DECIMAL(3,2),
    sentiment_score DECIMAL(3,2),
    detected_keywords TEXT[],
    escalated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    acknowledged_at TIMESTAMP WITH TIME ZONE,
    acknowledged_by VARCHAR(255),
    resolved_at TIMESTAMP WITH TIME ZONE,
    resolved_by VARCHAR(255),
    resolution_notes TEXT
);

-- Create index for faster lookups
CREATE INDEX IF NOT EXISTS idx_ai_escalations_thread_id ON ai_escalations(thread_id);
CREATE INDEX IF NOT EXISTS idx_ai_escalations_escalated_at ON ai_escalations(escalated_at DESC);
CREATE INDEX IF NOT EXISTS idx_ai_escalations_resolved_at ON ai_escalations(resolved_at);

-- =====================================================
-- Table: email_support_settings
-- Global settings for AI email support system
-- =====================================================
CREATE TABLE IF NOT EXISTS email_support_settings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    setting_key VARCHAR(100) UNIQUE NOT NULL,
    setting_value TEXT NOT NULL,
    description TEXT,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_by VARCHAR(255)
);

-- Insert default settings
INSERT INTO email_support_settings (setting_key, setting_value, description) VALUES
    ('ai_enabled', 'true', 'Enable/disable AI email responses'),
    ('confidence_threshold', '0.7', 'Minimum confidence score before escalating'),
    ('response_tone', 'professional_friendly', 'AI response tone: professional, friendly, professional_friendly'),
    ('auto_reply_enabled', 'true', 'Send automatic AI replies to customers'),
    ('escalation_email', 'admin@binaapp.my', 'Email to notify on escalations'),
    ('max_ai_turns', '3', 'Maximum AI responses before auto-escalating'),
    ('working_hours_only', 'false', 'Only send AI replies during working hours')
ON CONFLICT (setting_key) DO NOTHING;

-- =====================================================
-- Table: email_analytics
-- Track email support metrics
-- =====================================================
CREATE TABLE IF NOT EXISTS email_analytics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    date DATE NOT NULL DEFAULT CURRENT_DATE,
    total_emails_received INTEGER DEFAULT 0,
    ai_responses_sent INTEGER DEFAULT 0,
    escalations_count INTEGER DEFAULT 0,
    avg_response_time_seconds INTEGER,
    avg_confidence_score DECIMAL(3,2),
    resolution_rate DECIMAL(3,2),
    categories_breakdown JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create unique index for daily analytics
CREATE UNIQUE INDEX IF NOT EXISTS idx_email_analytics_date ON email_analytics(date);

-- =====================================================
-- Function: Update updated_at timestamp
-- =====================================================
CREATE OR REPLACE FUNCTION update_email_thread_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger for email_threads
DROP TRIGGER IF EXISTS trigger_email_threads_updated_at ON email_threads;
CREATE TRIGGER trigger_email_threads_updated_at
    BEFORE UPDATE ON email_threads
    FOR EACH ROW
    EXECUTE FUNCTION update_email_thread_updated_at();

-- =====================================================
-- Function: Update thread on new message
-- =====================================================
CREATE OR REPLACE FUNCTION update_thread_on_message()
RETURNS TRIGGER AS $$
BEGIN
    -- Update thread updated_at
    UPDATE email_threads
    SET updated_at = NOW(),
        first_response_at = COALESCE(first_response_at,
            CASE WHEN NEW.sender_type IN ('ai', 'admin', 'support') THEN NOW() ELSE NULL END
        )
    WHERE id = NEW.thread_id;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger for email_messages
DROP TRIGGER IF EXISTS trigger_email_message_insert ON email_messages;
CREATE TRIGGER trigger_email_message_insert
    AFTER INSERT ON email_messages
    FOR EACH ROW
    EXECUTE FUNCTION update_thread_on_message();

-- =====================================================
-- Row Level Security (RLS)
-- =====================================================

-- Enable RLS on tables
ALTER TABLE email_threads ENABLE ROW LEVEL SECURITY;
ALTER TABLE email_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE ai_escalations ENABLE ROW LEVEL SECURITY;
ALTER TABLE email_support_settings ENABLE ROW LEVEL SECURITY;
ALTER TABLE email_analytics ENABLE ROW LEVEL SECURITY;

-- Allow service role full access (for backend API)
CREATE POLICY "Service role has full access to email_threads"
    ON email_threads FOR ALL
    USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');

CREATE POLICY "Service role has full access to email_messages"
    ON email_messages FOR ALL
    USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');

CREATE POLICY "Service role has full access to ai_escalations"
    ON ai_escalations FOR ALL
    USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');

CREATE POLICY "Service role has full access to email_support_settings"
    ON email_support_settings FOR ALL
    USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');

CREATE POLICY "Service role has full access to email_analytics"
    ON email_analytics FOR ALL
    USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');

-- =====================================================
-- Comments for documentation
-- =====================================================
COMMENT ON TABLE email_threads IS 'Email conversation threads from support requests';
COMMENT ON TABLE email_messages IS 'Individual messages within email threads';
COMMENT ON TABLE ai_escalations IS 'Records of AI escalations to human support';
COMMENT ON TABLE email_support_settings IS 'Configuration settings for AI email support';
COMMENT ON TABLE email_analytics IS 'Daily analytics for email support performance';

COMMENT ON COLUMN email_threads.status IS 'Thread status: open, in_progress, resolved, escalated, closed';
COMMENT ON COLUMN email_threads.priority IS 'Priority level: low, normal, high, urgent';
COMMENT ON COLUMN email_messages.sender_type IS 'Type of sender: customer, ai, admin, support';
COMMENT ON COLUMN email_messages.ai_confidence IS 'AI confidence score for generated responses (0.00-1.00)';
COMMENT ON COLUMN ai_escalations.escalation_type IS 'Reason category: low_confidence, negative_sentiment, keyword_trigger, repeated_contact, manual';
