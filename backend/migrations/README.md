# Database migrations

Migrations are numbered SQL files applied to the Supabase project in order.

## Grants for new tables

Supabase no longer grants Data API access to new tables in `public`
automatically (from 2026-10-30). Every migration that creates a table must
grant access explicitly, in the same file:

```sql
CREATE TABLE public.my_table (...);
ALTER TABLE public.my_table ENABLE ROW LEVEL SECURITY;

GRANT SELECT, INSERT, UPDATE, DELETE ON public.my_table TO service_role;
```

The backend uses the `service_role` key for all database access, so that is
the only grant needed. Do not grant `anon` or `authenticated` unless the
browser really queries the table directly, and then add RLS policies for it.

Migration 060 also sets default privileges so new tables created by
`postgres` get the `service_role` grant automatically. Keep the explicit
grant anyway: default privileges do not carry over to new projects, preview
branches or a local `supabase db reset`.

## SECURITY DEFINER functions

Functions that run as `SECURITY DEFINER` are callable through
`/rest/v1/rpc/*`. Revoke client access and grant only the backend:

```sql
REVOKE EXECUTE ON FUNCTION public.my_fn(uuid) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.my_fn(uuid) TO service_role;
```
