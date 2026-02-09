-- =====================================================
-- BinaApp AI Phase 2 - Database Migration
-- Tables: website_health_scans, website_fixes,
--         ai_monitor_events, restaurant_health,
--         ai_support_chats, ai_support_messages,
--         admin_actions
-- =====================================================

-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =====================================================
-- FEATURE 1: AI AUTO-FIX WEBSITES
-- =====================================================

-- Website health scans
CREATE TABLE IF NOT EXISTS website_health_scans (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  website_id UUID NOT NULL REFERENCES websites(id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,

  -- Scan results
  scan_type TEXT DEFAULT 'auto' CHECK (scan_type IN ('auto', 'manual', 'dispute_triggered')),
  overall_score INTEGER CHECK (overall_score BETWEEN 0 AND 100),

  -- Issue categories
  design_score INTEGER CHECK (design_score BETWEEN 0 AND 100),
  performance_score INTEGER CHECK (performance_score BETWEEN 0 AND 100),
  content_score INTEGER CHECK (content_score BETWEEN 0 AND 100),
  mobile_score INTEGER CHECK (mobile_score BETWEEN 0 AND 100),

  -- Issues found
  issues JSONB DEFAULT '[]',
  total_issues INTEGER DEFAULT 0,
  critical_issues INTEGER DEFAULT 0,
  auto_fixable_issues INTEGER DEFAULT 0,

  -- Fix status
  fixes_applied JSONB DEFAULT '[]',
  fixes_pending JSONB DEFAULT '[]',
  auto_fixed_count INTEGER DEFAULT 0,

  -- AI analysis
  ai_summary TEXT,
  ai_recommendations JSONB DEFAULT '[]',
  model_used TEXT,

  status TEXT DEFAULT 'completed' CHECK (status IN ('scanning', 'completed', 'fixing', 'fixed', 'failed')),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Individual fix records
CREATE TABLE IF NOT EXISTS website_fixes (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  scan_id UUID NOT NULL REFERENCES website_health_scans(id) ON DELETE CASCADE,
  website_id UUID NOT NULL REFERENCES websites(id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,

  -- Fix details
  issue_type TEXT NOT NULL,
  issue_description TEXT NOT NULL,
  severity TEXT DEFAULT 'medium' CHECK (severity IN ('minor', 'medium', 'major', 'critical')),

  -- The fix
  fix_type TEXT CHECK (fix_type IN ('auto', 'suggested', 'manual')),
  fix_description TEXT,
  code_before TEXT,
  code_after TEXT,

  -- Status
  status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'applied', 'rejected', 'reverted')),
  applied_at TIMESTAMPTZ,
  applied_by TEXT CHECK (applied_by IN ('ai_auto', 'user_approved', 'admin')),

  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Enable RLS
ALTER TABLE website_health_scans ENABLE ROW LEVEL SECURITY;
ALTER TABLE website_fixes ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users view own scans" ON website_health_scans FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "System insert scans" ON website_health_scans FOR INSERT WITH CHECK (true);
CREATE POLICY "System update scans" ON website_health_scans FOR UPDATE USING (true);

CREATE POLICY "Users view own fixes" ON website_fixes FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users update own fixes" ON website_fixes FOR UPDATE USING (auth.uid() = user_id);
CREATE POLICY "System insert fixes" ON website_fixes FOR INSERT WITH CHECK (true);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_health_scans_website ON website_health_scans(website_id);
CREATE INDEX IF NOT EXISTS idx_health_scans_user ON website_health_scans(user_id);
CREATE INDEX IF NOT EXISTS idx_health_scans_created ON website_health_scans(created_at);
CREATE INDEX IF NOT EXISTS idx_website_fixes_scan ON website_fixes(scan_id);
CREATE INDEX IF NOT EXISTS idx_website_fixes_website ON website_fixes(website_id);
CREATE INDEX IF NOT EXISTS idx_website_fixes_status ON website_fixes(status);


-- =====================================================
-- FEATURE 2: AI PROACTIVE MONITOR
-- =====================================================

-- Proactive monitoring events
CREATE TABLE IF NOT EXISTS ai_monitor_events (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
  website_id UUID REFERENCES websites(id) ON DELETE SET NULL,
  order_id UUID REFERENCES delivery_orders(id) ON DELETE SET NULL,

  -- Event type
  event_type TEXT NOT NULL CHECK (event_type IN (
    'website_down', 'website_slow', 'website_broken',
    'payment_failed', 'payment_webhook_missing',
    'delivery_stalled', 'delivery_no_rider',
    'order_stuck', 'order_no_response',
    'high_complaint_rate', 'subscription_expiring',
    'storage_limit', 'unusual_activity'
  )),

  -- Details
  description TEXT,
  severity TEXT DEFAULT 'info' CHECK (severity IN ('info', 'warning', 'critical')),
  details JSONB,

  -- Action taken
  action_taken TEXT CHECK (action_taken IN ('notified', 'auto_fixed', 'credited', 'escalated', 'ignored')),
  action_details TEXT,
  credit_awarded DECIMAL(10,2) DEFAULT 0.00,

  -- Status
  acknowledged BOOLEAN DEFAULT FALSE,
  acknowledged_at TIMESTAMPTZ,

  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Restaurant health tracking
CREATE TABLE IF NOT EXISTS restaurant_health (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  website_id UUID NOT NULL REFERENCES websites(id) ON DELETE CASCADE UNIQUE,
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,

  -- Metrics
  total_orders INTEGER DEFAULT 0,
  completed_orders INTEGER DEFAULT 0,
  cancelled_orders INTEGER DEFAULT 0,
  disputed_orders INTEGER DEFAULT 0,
  avg_preparation_time_mins DECIMAL(5,2),
  avg_delivery_time_mins DECIMAL(5,2),
  avg_rating DECIMAL(3,2),

  -- Health
  fulfillment_rate DECIMAL(5,2) DEFAULT 100.00,
  complaint_rate DECIMAL(5,2) DEFAULT 0.00,
  health_status TEXT DEFAULT 'healthy' CHECK (health_status IN ('healthy', 'warning', 'critical', 'suspended')),

  -- Auto-actions
  warning_sent_at TIMESTAMPTZ,
  suspension_sent_at TIMESTAMPTZ,
  auto_suspended BOOLEAN DEFAULT FALSE,
  suspension_reason TEXT,

  last_order_at TIMESTAMPTZ,
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Enable RLS
ALTER TABLE ai_monitor_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE restaurant_health ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users view own monitor events" ON ai_monitor_events FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "System insert monitor events" ON ai_monitor_events FOR INSERT WITH CHECK (true);
CREATE POLICY "System update monitor events" ON ai_monitor_events FOR UPDATE USING (true);

CREATE POLICY "Users view own restaurant health" ON restaurant_health FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "System manage restaurant health" ON restaurant_health FOR ALL USING (true);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_monitor_events_user ON ai_monitor_events(user_id);
CREATE INDEX IF NOT EXISTS idx_monitor_events_type ON ai_monitor_events(event_type);
CREATE INDEX IF NOT EXISTS idx_monitor_events_created ON ai_monitor_events(created_at);
CREATE INDEX IF NOT EXISTS idx_monitor_events_unack ON ai_monitor_events(acknowledged) WHERE acknowledged = false;
CREATE INDEX IF NOT EXISTS idx_restaurant_health_website ON restaurant_health(website_id);
CREATE INDEX IF NOT EXISTS idx_restaurant_health_status ON restaurant_health(health_status);

-- Backfill restaurant_health for existing websites
INSERT INTO restaurant_health (website_id, user_id)
SELECT w.id, w.user_id FROM websites w
WHERE w.user_id IS NOT NULL
ON CONFLICT (website_id) DO NOTHING;


-- =====================================================
-- FEATURE 3: AI CHATBOT SUPPORT WITH VISION
-- =====================================================

-- AI Support Chat
CREATE TABLE IF NOT EXISTS ai_support_chats (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,

  -- Context
  website_id UUID REFERENCES websites(id) ON DELETE SET NULL,
  order_id UUID REFERENCES delivery_orders(id) ON DELETE SET NULL,
  dispute_id UUID REFERENCES ai_disputes(id) ON DELETE SET NULL,

  -- Chat metadata
  title TEXT,
  category TEXT,
  status TEXT DEFAULT 'active' CHECK (status IN ('active', 'resolved', 'escalated', 'closed')),

  -- Resolution
  resolution_type TEXT CHECK (resolution_type IN ('info_provided', 'issue_fixed', 'credit_awarded', 'dispute_created', 'escalated', 'no_action')),
  credit_awarded DECIMAL(10,2) DEFAULT 0.00,

  -- AI performance
  messages_count INTEGER DEFAULT 0,
  ai_model_used TEXT,
  satisfaction_rating INTEGER CHECK (satisfaction_rating BETWEEN 1 AND 5),

  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- AI Support Messages
CREATE TABLE IF NOT EXISTS ai_support_messages (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  chat_id UUID NOT NULL REFERENCES ai_support_chats(id) ON DELETE CASCADE,

  -- Message
  role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
  content TEXT NOT NULL,

  -- Attachments
  image_urls TEXT[] DEFAULT '{}',
  image_analysis JSONB,

  -- If AI took an action
  action_taken TEXT,
  action_data JSONB,

  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Enable RLS
ALTER TABLE ai_support_chats ENABLE ROW LEVEL SECURITY;
ALTER TABLE ai_support_messages ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users view own support chats" ON ai_support_chats FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users create own support chats" ON ai_support_chats FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "System update support chats" ON ai_support_chats FOR UPDATE USING (true);

CREATE POLICY "Users view own support messages" ON ai_support_messages FOR SELECT
  USING (chat_id IN (SELECT id FROM ai_support_chats WHERE user_id = auth.uid()));
CREATE POLICY "System insert support messages" ON ai_support_messages FOR INSERT WITH CHECK (true);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_support_chats_user ON ai_support_chats(user_id);
CREATE INDEX IF NOT EXISTS idx_support_chats_status ON ai_support_chats(status);
CREATE INDEX IF NOT EXISTS idx_support_messages_chat ON ai_support_messages(chat_id);
CREATE INDEX IF NOT EXISTS idx_support_messages_created ON ai_support_messages(created_at);


-- =====================================================
-- FEATURE 4: ADMIN DASHBOARD
-- =====================================================

-- Admin actions log
CREATE TABLE IF NOT EXISTS admin_actions (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  admin_user_id UUID NOT NULL REFERENCES auth.users(id),

  -- What was acted on
  target_type TEXT NOT NULL CHECK (target_type IN ('dispute', 'chat', 'user', 'website', 'restaurant', 'monitor_event')),
  target_id UUID NOT NULL,

  -- Action
  action TEXT NOT NULL CHECK (action IN (
    'approve_dispute', 'reject_dispute', 'override_decision',
    'award_credit', 'revoke_credit', 'suspend_user', 'unsuspend_user',
    'suspend_restaurant', 'unsuspend_restaurant',
    'resolve_chat', 'add_note', 'escalate'
  )),

  -- Details
  details JSONB,
  notes TEXT,

  -- Before/after
  previous_state JSONB,
  new_state JSONB,

  created_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE admin_actions ENABLE ROW LEVEL SECURITY;

-- Admin only policy using environment-configured admin emails
CREATE POLICY "Admins only" ON admin_actions FOR ALL USING (
  auth.uid() IN (SELECT id FROM auth.users WHERE email IN ('yassirar77@gmail.com'))
);

CREATE INDEX IF NOT EXISTS idx_admin_actions_target ON admin_actions(target_type, target_id);
CREATE INDEX IF NOT EXISTS idx_admin_actions_created ON admin_actions(created_at);
