-- Migration 060: New public tables are granted to service_role only
-- Supabase stops auto-granting Data API access to new public tables on
-- 2026-10-30. The backend talks to Supabase with the service_role key, so new
-- tables are granted to service_role by default. anon/authenticated no longer
-- receive any access to new tables unless a migration grants it explicitly.
-- Existing tables are not affected.
-- Applied to production 2026-09-23.

ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public
    REVOKE ALL ON TABLES FROM anon, authenticated;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public
    REVOKE ALL ON SEQUENCES FROM anon, authenticated;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO service_role;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public
    GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO service_role;
