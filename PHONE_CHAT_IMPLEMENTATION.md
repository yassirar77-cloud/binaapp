# 💬 Phone-Based Chat System Implementation

## Overview

Simple phone-based chat system that allows customers to chat with business owners without creating accounts. Uses phone number as unique identifier with localStorage for persistent sessions.

---

## ✅ What Was Implemented

### 1. **Database Migration** (`backend/migrations/009_phone_based_chat.sql`)

- ✅ Added `message_text` column to `chat_messages` table
- ✅ Migrated existing data from `message`/`content` columns
- ✅ Added phone-based indexes for fast lookups:
  - `idx_chat_conversations_phone`
  - `idx_chat_conversations_website_phone`
- ✅ Verified permissions for anonymous users

### 2. **Backend API Endpoints** (`backend/app/api/v1/endpoints/chat.py`)

Added 3 simplified endpoints for phone-based chat:

#### `POST /api/v1/chat/conversations`
Create or get existing conversation for a phone number.

**Request:**
```json
{
  "website_id": "uuid",
  "customer_name": "Ahmad",
  "customer_phone": "0123456789"
}
```

**Response:** Conversation object

#### `POST /api/v1/chat/messages`
Send a chat message.

**Request:**
```json
{
  "conversation_id": "uuid",
  "sender_type": "customer",
  "sender_name": "Ahmad",
  "message_text": "Hello!"
}
```

**Response:** Message object

#### `GET /api/v1/chat/conversations/{conversation_id}/messages`
Get all messages for a conversation.

**Response:** Array of message objects

### 3. **Frontend Widget** (`backend/static/widgets/delivery-widget.js`)

Added complete chat UI to the delivery widget:

**Features:**
- Customer info form (name + phone) - shown once
- Phone number stored in `localStorage` for persistence
- Chat window with message history
- Real-time message sending
- Auto-scroll to latest message
- Responsive design with emoji support
- Bilingual (Malay/English)

**New Functions:**
- `openChat()` - Entry point for chat
- `showCustomerInfoForm()` - Collect customer details
- `saveCustomerInfo()` - Save to localStorage
- `startConversation()` - Create/resume chat
- `loadChatMessages()` - Fetch message history
- `showChatWindow()` - Display chat UI
- `renderChatMessages()` - Render message bubbles
- `sendChatMessage()` - Send new message

---

## 🚀 Deployment Instructions

### Step 1: Run Database Migration

1. Go to **Supabase Dashboard** → **SQL Editor**
2. Open `backend/migrations/009_phone_based_chat.sql`
3. Run the migration
4. Verify success:
   ```sql
   -- Check message_text column exists
   SELECT column_name, data_type
   FROM information_schema.columns
   WHERE table_name = 'chat_messages'
   AND column_name = 'message_text';
   ```

### Step 2: Deploy Backend

```bash
git add backend/app/api/v1/endpoints/chat.py
git add backend/migrations/009_phone_based_chat.sql
git commit -m "Add phone-based chat system"
git push
```

Backend will auto-deploy on Render (if connected).

### Step 3: Deploy Frontend Widget

```bash
git add backend/static/widgets/delivery-widget.js
git add frontend/public/widgets/delivery-widget.js
git commit -m "Add chat widget UI"
git push
```

Widget is served from both locations for flexibility.

---

## 🧪 Testing Instructions

### Test 1: Customer Chat Flow

1. Visit any website (e.g., `bububu.binaapp.my`)
2. Look for **"Chat dengan Kami"** button (appears if conversation exists)
3. OR create an order first, then chat button will appear in tracking
4. Click chat button
5. Enter name and phone number (first time only)
6. Type a message and click "Hantar"
7. ✅ Message should appear in chat window
8. Refresh page → chat history should load automatically

### Test 2: Message Persistence

1. Send a message
2. Close browser completely
3. Open browser again
4. Visit same website
5. Click chat button
6. ✅ Previous messages should load
7. ✅ Name/phone should be pre-filled

### Test 3: Multiple Customers

1. Open website in **normal browser**
2. Chat as "Ahmad" (0123456789)
3. Open website in **incognito/private**
4. Chat as "Siti" (0198765432)
5. ✅ Each should have separate conversations
6. ✅ Check Supabase → `chat_conversations` table should have 2 rows

### Test 4: Owner Dashboard

1. Login as business owner
2. Go to `/profile` → **Chat** tab
3. ✅ Should see all customer conversations
4. ✅ Should see latest messages
5. (Owner reply feature - to be implemented in dashboard)

---

## 📊 Database Schema

### `chat_conversations` Table

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `website_id` | UUID | Business website |
| `customer_name` | TEXT | Customer name |
| `customer_phone` | TEXT | Phone number (identifier) |
| `customer_id` | TEXT | Generated: `customer_{phone}` |
| `status` | TEXT | 'active' or 'closed' |
| `created_at` | TIMESTAMP | When conversation started |
| `updated_at` | TIMESTAMP | Last activity |

**New Indexes:**
- `idx_chat_conversations_phone` (customer_phone)
- `idx_chat_conversations_website_phone` (website_id, customer_phone)

### `chat_messages` Table

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `conversation_id` | UUID | Foreign key |
| `sender_type` | TEXT | 'customer', 'owner', 'system' |
| `sender_name` | TEXT | Display name |
| `message_text` | TEXT | **NEW** - message content |
| `message` | TEXT | Legacy (kept for compatibility) |
| `created_at` | TIMESTAMP | When sent |

---

## 🎯 Customer Flow

```
1. Customer visits website (bububu.binaapp.my)
   ↓
2. Clicks "Chat dengan Kami" button
   ↓
3. [First time] Enter name + phone number
   ↓
4. Phone saved to localStorage
   ↓
5. Conversation created in Supabase
   ↓
6. Chat window opens
   ↓
7. Type and send messages
   ↓
8. [Next visit] Auto-load chat history
```

---

## 🔧 Key Implementation Details

### Phone Number as Unique ID

```javascript
// In widget
customerInfo = {
  name: "Ahmad",
  phone: "0123456789"
}
localStorage.setItem('binaapp_customer', JSON.stringify(customerInfo))

// In backend
customer_id = f"customer_{customer_phone}"
```

### Message Compatibility

The backend saves to both `message_text` and `message` for backward compatibility:

```python
message_data = {
    'message_text': text,  # NEW column
    'message': text,       # Legacy column
    ...
}
```

### Auto-Resume Conversation

Widget checks for existing conversation by `website_id` + `customer_phone`:

```sql
SELECT * FROM chat_conversations
WHERE website_id = ?
  AND customer_phone = ?
  AND status = 'active'
LIMIT 1
```

If found → resume
If not found → create new

---

## 🚨 Known Limitations

1. **No WebSocket** - Messages don't update in real-time (need manual refresh)
2. **Owner Reply** - Dashboard UI for owner to reply not implemented yet
3. **No Notifications** - No push notifications when new message arrives
4. **No Media** - Text-only (images/files not supported yet)
5. **No Typing Indicator** - Can't see when other person is typing

---

## 🔮 Future Enhancements

- [ ] WebSocket integration for real-time updates
- [ ] Owner dashboard chat interface
- [ ] Push notifications (WhatsApp/Email)
- [ ] Image/file upload support
- [ ] Typing indicators
- [ ] Read receipts
- [ ] Chat search/filtering
- [ ] Export chat history

---

## 📝 API Examples

### Create Conversation (cURL)

```bash
curl -X POST https://binaapp-backend.onrender.com/api/v1/chat/conversations \
  -H "Content-Type: application/json" \
  -d '{
    "website_id": "your-website-id",
    "customer_name": "Ahmad",
    "customer_phone": "0123456789"
  }'
```

### Send Message (cURL)

```bash
curl -X POST https://binaapp-backend.onrender.com/api/v1/chat/messages \
  -H "Content-Type: application/json" \
  -d '{
    "conversation_id": "conversation-id",
    "sender_type": "customer",
    "sender_name": "Ahmad",
    "message_text": "Hello, I have a question!"
  }'
```

### Get Messages (cURL)

```bash
curl https://binaapp-backend.onrender.com/api/v1/chat/conversations/{conversation_id}/messages
```

---

## ✅ Verification Checklist

After deployment:

- [ ] Migration ran successfully in Supabase
- [ ] `message_text` column exists in `chat_messages`
- [ ] Phone indexes created
- [ ] Backend deployed without errors
- [ ] Widget shows chat button
- [ ] Customer info form appears
- [ ] Can send messages
- [ ] Messages saved to database
- [ ] Chat history loads on refresh
- [ ] Multiple customers work separately

---

## 🐛 Troubleshooting

### Error: "message_text column does not exist"

**Solution:** Run migration `009_phone_based_chat.sql` in Supabase

### Error: "Failed to create conversation"

**Solution:** Check:
1. `website_id` is valid
2. Supabase permissions allow anon insert
3. Backend logs for detailed error

### Chat button not showing

**Solution:** Check:
1. Widget is loaded correctly
2. `BinaAppDelivery.init()` called with valid `websiteId`
3. Browser console for errors

### Messages not persisting

**Solution:** Check:
1. localStorage enabled in browser
2. `binaapp_customer` item exists in localStorage
3. Same phone number used

---

**Created:** 2026-01-17
**Status:** ✅ Ready for deployment
**Version:** 1.0.0
