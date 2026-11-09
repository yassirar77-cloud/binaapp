-- Operator alerts (services/ops_alerts.py): one row per Telegram alert —
-- a build the visual gate blocked (gate_failed) or a start refused with the
-- location question (location_conflict) — so the weekly summary can count
-- them. Written with the service role only.
create table if not exists public.ops_events (
    id          uuid primary key default gen_random_uuid(),
    kind        text not null,
    business_name text,
    email       text,
    user_id     uuid,
    website_id  uuid,
    job_id      text,
    reason      text,
    details     jsonb not null default '{}'::jsonb,
    created_at  timestamptz not null default now()
);
create index if not exists ops_events_created_at_idx on public.ops_events (created_at desc);
create index if not exists ops_events_kind_idx on public.ops_events (kind, created_at desc);
alter table public.ops_events enable row level security;
-- No policies: only the service role (which bypasses RLS) reads or writes.
