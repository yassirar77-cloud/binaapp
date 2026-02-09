-- =====================================================
-- BinaApp AI Phase 3 - Database Migration
-- Tables: sla_definitions, sla_breaches, referral_codes,
--         referral_uses, ai_chat_settings, ai_chat_responses,
--         order_verifications, notifications, push_subscriptions,
--         website_rebuilds, restaurant_penalties, penalty_appeals,
--         user_trust_scores, trust_score_history, webhook_endpoints,
--         webhook_deliveries
-- =====================================================

-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =====================================================
-- FEATURE 1: AI SLA SYSTEM
-- =====================================================

-- SLA definitions per subscription plan
CREATE TABLE IF NOT EXISTS sla_definitions (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  plan_name TEXT NOT NULL UNIQUE,
  max_response_time_hours INTEGER NOT NULL DEFAULT 24,
  max_downtime_minutes INTEGER NOT NULL DEFAULT 60,
  max_build_time_minutes INTEGER NOT NULL DEFAULT 30,
  uptime_guarantee_percent NUMERIC(5,2) NOT NULL DEFAULT 95.00,
  credit_compensation_amount NUMERIC(10,2) NOT NULL DEFAULT 5.00,
  description TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Seed SLA definitions for 3 plans
INSERT INTO sla_definitions (plan_name, max_response_time_hours, max_downtime_minutes, max_build_time_minutes, uptime_guarantee_percent, credit_compensation_amount, description)
VALUES
  ('basic', 24, 120, 30, 95.00, 5.00, 'Pelan Asas - Jaminan standard'),
  ('pro', 12, 60, 15, 99.00, 10.00, 'Pelan Pro - Jaminan premium'),
  ('enterprise', 4, 15, 10, 99.90, 25.00, 'Pelan Enterprise - Jaminan tertinggi')
ON CONFLICT (plan_name) DO NOTHING;

-- SLA breach records
CREATE TABLE IF NOT EXISTS sla_breaches (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  sla_definition_id UUID NOT NULL REFERENCES sla_definitions(id) ON DELETE CASCADE,
  breach_type TEXT NOT NULL CHECK (breach_type IN ('response_time', 'downtime', 'build_time', 'uptime')),
  expected_value NUMERIC(10,2) NOT NULL,
  actual_value NUMERIC(10,2) NOT NULL,
  credit_awarded NUMERIC(10,2) DEFAULT 0,
  description TEXT,
  month_year TEXT NOT NULL,
  auto_compensated BOOLEAN DEFAULT false,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Enable RLS
ALTER TABLE sla_definitions ENABLE ROW LEVEL SECURITY;
ALTER TABLE sla_breaches ENABLE ROW LEVEL SECURITY;

-- SLA policies
CREATE POLICY "Anyone can view SLA definitions" ON sla_definitions FOR SELECT USING (true);
CREATE POLICY "Users view own SLA breaches" ON sla_breaches FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Service can insert SLA breaches" ON sla_breaches FOR INSERT WITH CHECK (true);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_sla_breaches_user ON sla_breaches(user_id);
CREATE INDEX IF NOT EXISTS idx_sla_breaches_month ON sla_breaches(month_year);

-- =====================================================
-- FEATURE 2: REFERRAL SYSTEM
-- =====================================================

CREATE TABLE IF NOT EXISTS referral_codes (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE UNIQUE,
  code TEXT NOT NULL UNIQUE,
  total_referrals INTEGER DEFAULT 0,
  total_credits_earned NUMERIC(10,2) DEFAULT 0,
  is_active BOOLEAN DEFAULT true,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS referral_uses (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  referral_code_id UUID NOT NULL REFERENCES referral_codes(id) ON DELETE CASCADE,
  referrer_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  referred_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  referrer_credit NUMERIC(10,2) DEFAULT 5.00,
  referred_credit NUMERIC(10,2) DEFAULT 5.00,
  status TEXT DEFAULT 'completed' CHECK (status IN ('pending', 'completed', 'revoked')),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(referred_id)
);

-- Enable RLS
ALTER TABLE referral_codes ENABLE ROW LEVEL SECURITY;
ALTER TABLE referral_uses ENABLE ROW LEVEL SECURITY;

-- Referral policies
CREATE POLICY "Users view own referral code" ON referral_codes FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Service can manage referral codes" ON referral_codes FOR ALL WITH CHECK (true);
CREATE POLICY "Users view own referral uses" ON referral_uses FOR SELECT USING (auth.uid() = referrer_id OR auth.uid() = referred_id);
CREATE POLICY "Service can manage referral uses" ON referral_uses FOR INSERT WITH CHECK (true);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_referral_codes_code ON referral_codes(code);
CREATE INDEX IF NOT EXISTS idx_referral_codes_user ON referral_codes(user_id);
CREATE INDEX IF NOT EXISTS idx_referral_uses_referrer ON referral_uses(referrer_id);

-- =====================================================
-- FEATURE 3: AI AUTO-RESPOND CHAT
-- =====================================================

CREATE TABLE IF NOT EXISTS ai_chat_settings (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  website_id UUID NOT NULL REFERENCES websites(id) ON DELETE CASCADE UNIQUE,
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  is_enabled BOOLEAN DEFAULT true,
  delay_seconds INTEGER DEFAULT 120,
  custom_greeting TEXT DEFAULT 'Salam! Saya BinaBot, pembantu AI kedai ini. Ada apa yang boleh saya bantu?',
  personality TEXT DEFAULT 'friendly' CHECK (personality IN ('friendly', 'professional', 'casual')),
  auto_respond_hours JSONB DEFAULT '{"start": 0, "end": 24}',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ai_chat_responses (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  website_id UUID NOT NULL REFERENCES websites(id) ON DELETE CASCADE,
  conversation_id UUID NOT NULL,
  original_message_id UUID,
  ai_response_message_id UUID,
  customer_message TEXT,
  ai_response TEXT,
  context_used JSONB DEFAULT '{}',
  model_used TEXT DEFAULT 'deepseek-chat',
  response_time_ms INTEGER,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Enable RLS
ALTER TABLE ai_chat_settings ENABLE ROW LEVEL SECURITY;
ALTER TABLE ai_chat_responses ENABLE ROW LEVEL SECURITY;

-- AI chat policies
CREATE POLICY "Users view own AI chat settings" ON ai_chat_settings FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users manage own AI chat settings" ON ai_chat_settings FOR ALL USING (auth.uid() = user_id);
CREATE POLICY "Service can manage AI chat settings" ON ai_chat_settings FOR ALL WITH CHECK (true);
CREATE POLICY "Users view own AI chat responses" ON ai_chat_responses FOR SELECT USING (
  website_id IN (SELECT id FROM websites WHERE user_id = auth.uid())
);
CREATE POLICY "Service can insert AI chat responses" ON ai_chat_responses FOR INSERT WITH CHECK (true);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_ai_chat_settings_website ON ai_chat_settings(website_id);
CREATE INDEX IF NOT EXISTS idx_ai_chat_responses_website ON ai_chat_responses(website_id);
CREATE INDEX IF NOT EXISTS idx_ai_chat_responses_conversation ON ai_chat_responses(conversation_id);

-- =====================================================
-- FEATURE 4: AI ORDER ISSUE DETECTOR
-- =====================================================

CREATE TABLE IF NOT EXISTS order_verifications (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  order_id UUID NOT NULL,
  website_id UUID NOT NULL REFERENCES websites(id) ON DELETE CASCADE,
  delivery_photo_url TEXT,
  expected_items JSONB DEFAULT '[]',
  detected_items JSONB DEFAULT '[]',
  match_score NUMERIC(3,2) DEFAULT 0.00,
  issues_found JSONB DEFAULT '[]',
  verification_status TEXT DEFAULT 'pending' CHECK (verification_status IN ('pending', 'verified', 'issues_found', 'failed')),
  auto_credited BOOLEAN DEFAULT false,
  credit_amount NUMERIC(10,2) DEFAULT 0,
  customer_id UUID,
  ai_analysis TEXT,
  model_used TEXT DEFAULT 'qwen-vl-max',
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Enable RLS
ALTER TABLE order_verifications ENABLE ROW LEVEL SECURITY;

-- Order verification policies
CREATE POLICY "Service can manage order verifications" ON order_verifications FOR ALL WITH CHECK (true);
CREATE POLICY "Users view verifications for their websites" ON order_verifications FOR SELECT USING (
  website_id IN (SELECT id FROM websites WHERE user_id = auth.uid())
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_order_verifications_order ON order_verifications(order_id);
CREATE INDEX IF NOT EXISTS idx_order_verifications_website ON order_verifications(website_id);
CREATE INDEX IF NOT EXISTS idx_order_verifications_status ON order_verifications(verification_status);

-- =====================================================
-- FEATURE 5: AI SMART NOTIFICATIONS
-- =====================================================

CREATE TABLE IF NOT EXISTS notifications (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  title TEXT NOT NULL,
  message TEXT NOT NULL,
  notification_type TEXT NOT NULL CHECK (notification_type IN (
    'sla_breach', 'referral', 'credit', 'dispute', 'order',
    'website', 'penalty', 'trust', 'system', 'announcement'
  )),
  priority TEXT DEFAULT 'normal' CHECK (priority IN ('low', 'normal', 'high', 'urgent')),
  is_read BOOLEAN DEFAULT false,
  read_at TIMESTAMPTZ,
  action_url TEXT,
  metadata JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS push_subscriptions (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  endpoint TEXT NOT NULL,
  p256dh TEXT NOT NULL,
  auth_key TEXT NOT NULL,
  is_active BOOLEAN DEFAULT true,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(user_id, endpoint)
);

-- Enable RLS
ALTER TABLE notifications ENABLE ROW LEVEL SECURITY;
ALTER TABLE push_subscriptions ENABLE ROW LEVEL SECURITY;

-- Notification policies
CREATE POLICY "Users view own notifications" ON notifications FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users update own notifications" ON notifications FOR UPDATE USING (auth.uid() = user_id);
CREATE POLICY "Service can insert notifications" ON notifications FOR INSERT WITH CHECK (true);
CREATE POLICY "Users manage own push subscriptions" ON push_subscriptions FOR ALL USING (auth.uid() = user_id);
CREATE POLICY "Service can manage push subscriptions" ON push_subscriptions FOR ALL WITH CHECK (true);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications(user_id);
CREATE INDEX IF NOT EXISTS idx_notifications_unread ON notifications(user_id, is_read) WHERE is_read = false;
CREATE INDEX IF NOT EXISTS idx_notifications_created ON notifications(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_push_subscriptions_user ON push_subscriptions(user_id);

-- =====================================================
-- FEATURE 6: AI WEBSITE AUTO-REBUILD
-- =====================================================

CREATE TABLE IF NOT EXISTS website_rebuilds (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  website_id UUID NOT NULL REFERENCES websites(id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  trigger_reason TEXT NOT NULL CHECK (trigger_reason IN ('low_health_score', 'manual', 'ai_recommended')),
  old_health_score INTEGER,
  new_health_score INTEGER,
  old_html TEXT,
  new_html TEXT,
  changes_summary JSONB DEFAULT '[]',
  status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'generating', 'preview_ready', 'approved', 'rejected', 'applied', 'failed')),
  approved_at TIMESTAMPTZ,
  applied_at TIMESTAMPTZ,
  rejected_reason TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Enable RLS
ALTER TABLE website_rebuilds ENABLE ROW LEVEL SECURITY;

-- Website rebuild policies
CREATE POLICY "Users view own website rebuilds" ON website_rebuilds FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Service can manage website rebuilds" ON website_rebuilds FOR ALL WITH CHECK (true);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_website_rebuilds_website ON website_rebuilds(website_id);
CREATE INDEX IF NOT EXISTS idx_website_rebuilds_user ON website_rebuilds(user_id);
CREATE INDEX IF NOT EXISTS idx_website_rebuilds_status ON website_rebuilds(status);

-- =====================================================
-- FEATURE 8: RESTAURANT PENALTY SYSTEM
-- =====================================================

CREATE TABLE IF NOT EXISTS restaurant_penalties (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  website_id UUID NOT NULL REFERENCES websites(id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  penalty_type TEXT NOT NULL CHECK (penalty_type IN ('warning', 'fine', 'suspension', 'permanent_ban')),
  reason TEXT NOT NULL,
  complaint_rate NUMERIC(5,2),
  fine_amount NUMERIC(10,2) DEFAULT 0,
  is_active BOOLEAN DEFAULT true,
  expires_at TIMESTAMPTZ,
  resolved_at TIMESTAMPTZ,
  resolved_by TEXT,
  resolution_note TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS penalty_appeals (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  penalty_id UUID NOT NULL REFERENCES restaurant_penalties(id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  appeal_reason TEXT NOT NULL,
  supporting_evidence TEXT,
  status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'reviewing', 'approved', 'rejected')),
  admin_response TEXT,
  reviewed_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Enable RLS
ALTER TABLE restaurant_penalties ENABLE ROW LEVEL SECURITY;
ALTER TABLE penalty_appeals ENABLE ROW LEVEL SECURITY;

-- Penalty policies
CREATE POLICY "Users view own penalties" ON restaurant_penalties FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Service can manage penalties" ON restaurant_penalties FOR ALL WITH CHECK (true);
CREATE POLICY "Users view own appeals" ON penalty_appeals FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can create appeals" ON penalty_appeals FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Service can manage appeals" ON penalty_appeals FOR ALL WITH CHECK (true);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_penalties_website ON restaurant_penalties(website_id);
CREATE INDEX IF NOT EXISTS idx_penalties_user ON restaurant_penalties(user_id);
CREATE INDEX IF NOT EXISTS idx_penalties_active ON restaurant_penalties(is_active) WHERE is_active = true;
CREATE INDEX IF NOT EXISTS idx_penalty_appeals_penalty ON penalty_appeals(penalty_id);

-- =====================================================
-- FEATURE 9: USER TRUST SCORE
-- =====================================================

CREATE TABLE IF NOT EXISTS user_trust_scores (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE UNIQUE,
  score INTEGER DEFAULT 400 CHECK (score BETWEEN 0 AND 1000),
  trust_level TEXT DEFAULT 'new' CHECK (trust_level IN ('low', 'new', 'standard', 'trusted', 'premium')),
  credit_multiplier NUMERIC(3,2) DEFAULT 1.00,

  -- Factor breakdowns
  successful_orders INTEGER DEFAULT 0,
  subscription_months INTEGER DEFAULT 0,
  referral_count INTEGER DEFAULT 0,
  legitimate_disputes INTEGER DEFAULT 0,
  fraudulent_disputes INTEGER DEFAULT 0,
  rejected_disputes INTEGER DEFAULT 0,
  payment_failures INTEGER DEFAULT 0,
  terms_violations INTEGER DEFAULT 0,

  last_calculated_at TIMESTAMPTZ DEFAULT NOW(),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS trust_score_history (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  old_score INTEGER,
  new_score INTEGER,
  change_reason TEXT NOT NULL,
  change_amount INTEGER NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Enable RLS
ALTER TABLE user_trust_scores ENABLE ROW LEVEL SECURITY;
ALTER TABLE trust_score_history ENABLE ROW LEVEL SECURITY;

-- Trust score policies
CREATE POLICY "Users view own trust score" ON user_trust_scores FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Service can manage trust scores" ON user_trust_scores FOR ALL WITH CHECK (true);
CREATE POLICY "Users view own trust history" ON trust_score_history FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Service can insert trust history" ON trust_score_history FOR INSERT WITH CHECK (true);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_trust_scores_user ON user_trust_scores(user_id);
CREATE INDEX IF NOT EXISTS idx_trust_scores_level ON user_trust_scores(trust_level);
CREATE INDEX IF NOT EXISTS idx_trust_history_user ON trust_score_history(user_id);

-- =====================================================
-- FEATURE 10: API WEBHOOKS
-- =====================================================

CREATE TABLE IF NOT EXISTS webhook_endpoints (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  url TEXT NOT NULL,
  secret TEXT NOT NULL,
  events JSONB NOT NULL DEFAULT '[]',
  is_active BOOLEAN DEFAULT true,
  failure_count INTEGER DEFAULT 0,
  last_triggered_at TIMESTAMPTZ,
  description TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS webhook_deliveries (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  webhook_endpoint_id UUID NOT NULL REFERENCES webhook_endpoints(id) ON DELETE CASCADE,
  event_type TEXT NOT NULL,
  payload JSONB NOT NULL,
  response_status INTEGER,
  response_body TEXT,
  delivered BOOLEAN DEFAULT false,
  attempt_count INTEGER DEFAULT 0,
  next_retry_at TIMESTAMPTZ,
  error_message TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Enable RLS
ALTER TABLE webhook_endpoints ENABLE ROW LEVEL SECURITY;
ALTER TABLE webhook_deliveries ENABLE ROW LEVEL SECURITY;

-- Webhook policies
CREATE POLICY "Users view own webhooks" ON webhook_endpoints FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users manage own webhooks" ON webhook_endpoints FOR ALL USING (auth.uid() = user_id);
CREATE POLICY "Service can manage webhooks" ON webhook_endpoints FOR ALL WITH CHECK (true);
CREATE POLICY "Users view own webhook deliveries" ON webhook_deliveries FOR SELECT USING (
  webhook_endpoint_id IN (SELECT id FROM webhook_endpoints WHERE user_id = auth.uid())
);
CREATE POLICY "Service can manage webhook deliveries" ON webhook_deliveries FOR ALL WITH CHECK (true);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_webhook_endpoints_user ON webhook_endpoints(user_id);
CREATE INDEX IF NOT EXISTS idx_webhook_endpoints_active ON webhook_endpoints(is_active) WHERE is_active = true;
CREATE INDEX IF NOT EXISTS idx_webhook_deliveries_endpoint ON webhook_deliveries(webhook_endpoint_id);
CREATE INDEX IF NOT EXISTS idx_webhook_deliveries_event ON webhook_deliveries(event_type);

-- =====================================================
-- DONE: Phase 3 Migration Complete
-- =====================================================
