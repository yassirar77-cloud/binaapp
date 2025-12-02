# BinaApp Database

This directory contains database schemas and migrations for BinaApp.

## Supabase Setup

### 1. Create a Supabase Project

1. Go to [supabase.com](https://supabase.com)
2. Create a new project
3. Note down your project URL and API keys

### 2. Run the Schema

1. Open your Supabase project dashboard
2. Go to **SQL Editor**
3. Copy the contents of `supabase/schema.sql`
4. Paste and run the SQL

### 3. Configure Environment Variables

Add these to your `.env` file:

```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
```

## Database Tables

### Core Tables

1. **profiles** - Extended user information
2. **subscriptions** - User subscription plans
3. **websites** - Generated websites
4. **analytics** - Website analytics
5. **templates** - Pre-made templates

### Relationships

```
auth.users (Supabase Auth)
    ↓
profiles (1:1)
    ↓
subscriptions (1:1)
    ↓
websites (1:many)
    ↓
analytics (1:1)
```

## Row Level Security (RLS)

All tables have RLS enabled. Users can only:
- View their own data
- Create websites under their account
- Update/delete their own websites

## Functions

- `increment_views(website_id)` - Increment website view count
- `update_updated_at_column()` - Auto-update timestamps
- `handle_new_user()` - Initialize new user data

## Triggers

- Auto-create profile and subscription on user signup
- Auto-update `updated_at` timestamps

## Migrations

For future schema changes, create migration files:

```sql
-- migrations/001_add_custom_domains.sql
ALTER TABLE websites ADD COLUMN custom_domain TEXT;
```

Run migrations through Supabase dashboard or CLI.
