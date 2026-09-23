-- Migration 058: Lock down promo_redemptions_admin view
-- Supabase advisor: security_definer_view (ERROR).
-- The view joins promo redemptions to profiles (email, full_name). It ran with
-- the owner's rights and was readable by anon/authenticated through the REST
-- API. Only the backend (service_role) reads it, so run it as the caller and
-- revoke client access.
-- Applied to production 2026-09-23.

ALTER VIEW public.promo_redemptions_admin SET (security_invoker = true);
REVOKE ALL ON public.promo_redemptions_admin FROM anon, authenticated, public;
GRANT SELECT ON public.promo_redemptions_admin TO service_role;

-- Note: public.spatial_ref_sys (advisor: rls_disabled_in_public) is a PostGIS
-- table owned by supabase_admin. The postgres role can neither enable RLS on it
-- nor revoke its grants; that has to be done by Supabase support.
