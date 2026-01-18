# Chat System Schema Reference

**CRITICAL**: This document defines the AUTHORITATIVE schema for chat tables.
All code MUST use these exact column names.

## ⚠️ Common Errors

### PGRST204: Schema Cache Error
**Error**: `Could not find the 'column_name' column in the schema cache`

**Cause**: PostgREST's schema cache is out of sync with the database

**Solution**: Run migration 011:
```sql
-- In Supabase SQL Editor:
\i backend/migrations/011_reload_schema_cache.sql
```

---

## 📋 Table Schemas

### 1. `chat_messages`

**Purpose**: Stores all chat messages

| Column | Type | Required | Description |
|--------|------|----------|-------------|
| `id` | UUID | ✅ | Primary key |
| `conversation_id` | UUID | ✅ | FK to chat_conversations |
| `sender_type` | TEXT | ✅ | 'customer', 'owner', 'rider', 'system' |
| `sender_id` | TEXT | ❌ | User/customer ID |
| `sender_name` | TEXT | ❌ | Display name |
| `message_type` | TEXT | ❌ | Default: 'text' |
| `message_text` | TEXT | ✅ | **THE ONLY MESSAGE CONTENT COLUMN** |
| `media_url` | TEXT | ❌ | Cloudinary URL for images/voice |
| `metadata` | JSONB | ❌ | Extra data (location, payment info) |
| `is_read` | BOOLEAN | ❌ | Default: false |
| `read_at` | TIMESTAMPTZ | ❌ | When message was read |
| `read_by` | JSONB | ❌ | Array of user types who read |
| `created_at` | TIMESTAMPTZ | ❌ | Default: NOW() |

**❌ REMOVED COLUMNS** (DO NOT USE):
- ~~`content`~~ - Does not exist!
- ~~`message`~~ - Does not exist!

**✅ CORRECT INSERT**:
```python
{
    "id": str(uuid.uuid4()),
    "conversation_id": "abc-123",
    "sender_type": "customer",
    "message_text": "Hello",  # ✅ Use this
    "is_read": False,
    "created_at": datetime.utcnow().isoformat()
}
```

**❌ WRONG INSERT**:
```python
{
    "message_text": "Hello",
    "content": "Hello",   # ❌ Column doesn't exist!
    "message": "Hello"    # ❌ Column doesn't exist!
}
```

---

### 2. `chat_participants`

**Purpose**: Tracks who is in each conversation

| Column | Type | Required | Description |
|--------|------|----------|-------------|
| `id` | UUID | ✅ | Primary key |
| `conversation_id` | UUID | ✅ | FK to chat_conversations |
| `user_type` | TEXT | ✅ | 'customer', 'owner', 'rider' |
| `user_id` | TEXT | ❌ | User identifier |
| `user_name` | TEXT | ❌ | Display name |
| `is_online` | BOOLEAN | ❌ | Default: false |
| `last_seen` | TIMESTAMPTZ | ❌ | Last activity time |
| `created_at` | TIMESTAMPTZ | ❌ | Default: NOW() |

**UNIQUE CONSTRAINT**: `(conversation_id, user_type, user_id)`

**❌ REMOVED COLUMNS** (DO NOT USE):
- ~~`participant_type`~~ - Does not exist! (use `user_type`)
- ~~`participant_name`~~ - Does not exist! (use `user_name`)
- ~~`participant_phone`~~ - Does not exist!

**✅ CORRECT INSERT**:
```python
{
    "conversation_id": "abc-123",
    "user_type": "customer",      # ✅ Use this
    "user_id": "customer_123",
    "user_name": "Ahmad"           # ✅ Use this
}
```

**❌ WRONG INSERT**:
```python
{
    "conversation_id": "abc-123",
    "participant_type": "customer",   # ❌ Column doesn't exist!
    "user_type": "customer",          # ❌ Redundant
    "participant_name": "Ahmad",      # ❌ Column doesn't exist!
    "user_name": "Ahmad",
    "participant_phone": "+60123"     # ❌ Column doesn't exist!
}
```

---

### 3. `chat_conversations`

**Purpose**: Main conversation records

| Column | Type | Required | Description |
|--------|------|----------|-------------|
| `id` | UUID | ✅ | Primary key |
| `order_id` | UUID | ❌ | FK to orders (optional) |
| `website_id` | UUID | ✅ | FK to websites |
| `website_name` | TEXT | ❌ | Cached website name |
| `customer_id` | TEXT | ✅ | Customer identifier |
| `customer_name` | TEXT | ❌ | Customer display name |
| `customer_phone` | TEXT | ❌ | Customer phone number |
| `status` | TEXT | ❌ | 'active', 'closed' |
| `unread_customer` | INTEGER | ❌ | Default: 0 |
| `unread_owner` | INTEGER | ❌ | Default: 0 |
| `unread_rider` | INTEGER | ❌ | Default: 0 |
| `created_at` | TIMESTAMPTZ | ❌ | Default: NOW() |
| `updated_at` | TIMESTAMPTZ | ❌ | Default: NOW() |

---

## 🔧 Code Guidelines

### DO ✅

```python
# Use message_text for all messages
message_data = {
    "message_text": text
}

# Use user_type and user_name for participants
participant_data = {
    "user_type": "customer",
    "user_name": "Ahmad"
}

# Read message_text from database
messages = supabase.table("chat_messages").select(
    "id, conversation_id, message_text, sender_type, created_at"
).execute()
```

### DON'T ❌

```python
# Don't use content or message columns
message_data = {
    "content": text,        # ❌ Column doesn't exist
    "message": text         # ❌ Column doesn't exist
}

# Don't use participant_* columns
participant_data = {
    "participant_type": "customer",   # ❌ Column doesn't exist
    "participant_name": "Ahmad"       # ❌ Column doesn't exist
}

# Don't select non-existent columns
messages = supabase.table("chat_messages").select(
    "content, message"    # ❌ Columns don't exist
).execute()
```

---

## 🚨 Troubleshooting

### Error: "Could not find the 'content' column"
**Fix**: Use `message_text` instead of `content` or `message`

### Error: "Could not find the 'participant_type' column"
**Fix**: Use `user_type` instead of `participant_type`

### Error: "Could not find the 'conversation_id' column"
**Fix**: Run migration 011 to reload schema cache

---

## 📚 Migrations

**Schema Evolution**:
1. `004_chat_system.sql` - Initial chat tables (original columns)
2. `009_phone_based_chat.sql` - Added `message_text` column
3. `011_reload_schema_cache.sql` - Force schema cache reload

**To Apply All**:
```sql
-- Run in Supabase SQL Editor in order:
\i backend/migrations/004_chat_system.sql
\i backend/migrations/009_phone_based_chat.sql
\i backend/migrations/011_reload_schema_cache.sql
```

---

## ✅ Validation

Run this to verify your schema:

```sql
-- Check chat_messages columns
SELECT column_name
FROM information_schema.columns
WHERE table_name = 'chat_messages'
ORDER BY ordinal_position;

-- Check chat_participants columns
SELECT column_name
FROM information_schema.columns
WHERE table_name = 'chat_participants'
ORDER BY ordinal_position;

-- Expected results:
-- chat_messages: id, conversation_id, sender_type, sender_id, sender_name,
--                message_type, message_text, media_url, metadata, is_read,
--                read_at, read_by, created_at
--
-- chat_participants: id, conversation_id, user_type, user_id, user_name,
--                    is_online, last_seen, created_at
```

---

**Last Updated**: 2026-01-18
**Authoritative Source**: `DATABASE_SCHEMA.sql` + Migration 009
