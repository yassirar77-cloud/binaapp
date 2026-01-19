# Migration 013: Add Missing Chat Columns

## Issue
The `chat_messages` table is missing the `media_url` and `metadata` columns, causing warnings:
```
WARNING:app.api.v1.endpoints.chat:[Chat] chat_messages select: missing column 'media_url', retrying without it
WARNING:app.api.v1.endpoints.chat:[Chat] chat_messages select: missing column 'metadata', retrying without it
```

## Root Cause
While the original migration `004_chat_system.sql` included these columns, they were not applied to the production database. This could be due to:
1. Migrations run in wrong order
2. Only partial migrations applied
3. Table recreated manually without all columns

## Solution
Run migration `013_add_missing_chat_columns.sql` to add these missing columns safely.

## How to Apply

### Option 1: Via Supabase Dashboard (Recommended)
1. Go to your Supabase project dashboard
2. Navigate to **SQL Editor**
3. Copy the contents of `013_add_missing_chat_columns.sql`
4. Paste into the SQL editor
5. Click **Run**

### Option 2: Via Command Line
```bash
# Set your Supabase database URL
export DATABASE_URL="postgresql://[user]:[password]@[host]:[port]/[database]"

# Run the migration
psql $DATABASE_URL < backend/migrations/013_add_missing_chat_columns.sql
```

## What This Migration Does

1. **Checks if table exists** - Ensures `chat_messages` table exists before proceeding
2. **Adds media_url column** - TEXT type, for storing image/voice URLs from Cloudinary
3. **Adds metadata column** - JSONB type, for storing extra data like:
   - Location coordinates
   - Payment information
   - Custom message attributes
4. **Creates indexes** - Optimizes queries on these new columns
5. **Verifies success** - Confirms both columns were added successfully

## Expected Output
When successful, you should see:
```
NOTICE: Added media_url column to chat_messages
NOTICE: Added metadata column to chat_messages
NOTICE: SUCCESS: chat_messages now has media_url and metadata columns
```

If columns already exist:
```
NOTICE: media_url column already exists in chat_messages
NOTICE: metadata column already exists in chat_messages
NOTICE: SUCCESS: chat_messages now has media_url and metadata columns
```

## Verification

After running the migration, verify the columns exist:

```sql
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'chat_messages'
  AND column_name IN ('media_url', 'metadata');
```

Expected result:
```
 column_name | data_type
-------------+-----------
 media_url   | text
 metadata    | jsonb
```

## Impact

- **No downtime** - Migration is safe to run on live database
- **No data loss** - Only adds new columns, doesn't modify existing data
- **Backward compatible** - Existing code continues to work
- **Performance** - Indexes added for optimal query performance

## Post-Migration

After applying this migration:
1. The warnings will disappear from application logs
2. Chat messages can now include:
   - Images and voice notes (via `media_url`)
   - Payment proof uploads
   - Location sharing data (via `metadata`)
   - Custom message attributes

## Rollback (if needed)

If you need to rollback:
```sql
ALTER TABLE public.chat_messages DROP COLUMN IF EXISTS media_url;
ALTER TABLE public.chat_messages DROP COLUMN IF EXISTS metadata;
```

**Note**: Only rollback if absolutely necessary, as this will remove any data stored in these columns.
