-- Migration 040: Add websites.error_message column
--
-- Background: PR #665 introduced the regenerate flow at
-- /api/v1/websites/{id}/regenerate, whose background task writes
-- websites.error_message on failure so the dashboard can surface the
-- reason a generation failed. The column was added retroactively in
-- production via the Supabase SQL Editor when the first failed-regen
-- write crashed; it landed in DATABASE_SCHEMA.sql but never received
-- a dedicated migration file. As a result, any fresh Supabase project
-- bootstrapped from the migrations/ directory (rather than the schema
-- dump) would lack the column and the regenerate endpoint would 500.
--
-- This migration backfills the missing DDL so the migrations/ directory
-- is the single source of truth for fresh deploys.
--
-- Safety: IF NOT EXISTS guard makes this idempotent — re-running on
-- production (where the column already exists) is a no-op.

ALTER TABLE public.websites
  ADD COLUMN IF NOT EXISTS error_message TEXT NULL;
