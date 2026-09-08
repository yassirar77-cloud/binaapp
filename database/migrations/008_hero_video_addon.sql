-- 008: Hero video background sold as a RM5 add-on credit (addon_type
-- 'hero_video'), and 'depleted' admitted as an addon_purchases status —
-- the credit consumer has always written it; the old check rejected it,
-- so a fully used credit row could never be marked.
-- Applied to production via Supabase on 2026-09-08 as
-- hero_video_addon_and_depleted_status.
ALTER TABLE public.addon_purchases DROP CONSTRAINT IF EXISTS addon_purchases_addon_type_check;
ALTER TABLE public.addon_purchases
  ADD CONSTRAINT addon_purchases_addon_type_check
  CHECK (addon_type IN ('ai_image', 'rider', 'website', 'ai_hero', 'zone', 'hero_video'));

ALTER TABLE public.addon_purchases DROP CONSTRAINT IF EXISTS addon_purchases_status_check;
ALTER TABLE public.addon_purchases
  ADD CONSTRAINT addon_purchases_status_check
  CHECK (status IN ('active', 'cancelled', 'expired', 'depleted'));
