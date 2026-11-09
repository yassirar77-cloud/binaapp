-- Migration 061: let a merchant publish under binaapp.my OR mysyg.com
--
-- websites.site_domain is the apex domain the site lives on:
--   https://<subdomain>.<site_domain>
-- The subdomain stays globally unique (existing UNIQUE on websites.subdomain),
-- so "kedai" can only ever belong to one site on any domain. The subdomain
-- middleware answers on every allowed domain and 302s to the chosen one.
--
-- Every existing row defaults to binaapp.my, i.e. nothing moves.
-- Allowed values must match settings.MAIN_DOMAIN + settings.ALT_SITE_DOMAINS
-- (backend/app/services/site_domains.py). Adding a third domain later means
-- widening this CHECK and that env var together.

ALTER TABLE public.websites
    ADD COLUMN IF NOT EXISTS site_domain TEXT NOT NULL DEFAULT 'binaapp.my';

ALTER TABLE public.websites
    DROP CONSTRAINT IF EXISTS websites_site_domain_check;

ALTER TABLE public.websites
    ADD CONSTRAINT websites_site_domain_check
    CHECK (site_domain IN ('binaapp.my', 'mysyg.com'));

COMMENT ON COLUMN public.websites.site_domain IS
    'Apex domain the published site lives on (binaapp.my or mysyg.com). See migration 061.';
