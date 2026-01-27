# BinaApp Chat System

A complete real-time messaging system for BinaApp delivery orders.

## Features

- **Real-time messaging** via WebSocket
- **Three-way chat** between Customer, Owner, and Rider
- **Live rider tracking** with GPS location sharing
- **Image upload** for photos and payment proofs
- **Typing indicators** and read receipts
- **Responsive design** for mobile and desktop

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    BINAAPP CHAT                         │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  👤 CUSTOMER          🏪 OWNER           🛵 RIDER       │
│     App                  Dashboard          PWA         │
│      │                      │                │          │
│      └──────────┬───────────┴────────────────┘          │
│                 │                                       │
│         ┌──────▼──────┐                                │
│         │  WEBSOCKET  │                                │
│         │   SERVER    │                                │
│         └──────┬──────┘                                │
│                │                                       │
│    ┌───────────┼───────────┐                           │
│    │           │           │                           │
│    ▼           ▼           ▼                           │
│ 💬 Messages  📍 Live Map  📷 Images                    │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

## Database Schema

Run the migration file: `backend/migrations/004_chat_system.sql`

### Tables:
- `chat_conversations` - Chat sessions linked to orders
- `chat_messages` - All messages with type support
- `chat_participants` - Users in each conversation

## Backend API

**Endpoint prefix:** `/v1/chat`

### REST Endpoints:
- `POST /conversations/create` - Create new conversation
- `GET /conversations/{id}` - Get conversation with messages
- `GET /conversations/website/{id}` - Get all conversations for owner
- `GET /conversations/order/{id}` - Get conversation by order
- `POST /messages/send` - Send message via REST
- `POST /messages/upload-image` - Upload image message
- `POST /messages/upload-payment` - Upload payment proof
- `POST /messages/mark-read` - Mark messages as read
- `POST /rider/update-location` - Update rider GPS
- `GET /rider/location/{order_id}` - Get rider location

### WebSocket:
- `WS /ws/{conversation_id}/{user_type}/{user_id}`

**Message types:**
- `message` - Send text/image/location message
- `typing` - Typing indicator
- `read` - Mark messages read
- `location` - Rider location update
- `ping` - Keep-alive

## Frontend Components

### BinaChat.tsx
Main chat component with full functionality.

```tsx
<BinaChat
  conversationId="uuid"
  userType="customer|owner|rider"
  userId="user-id"
  userName="Display Name"
  orderId="order-uuid"
  showMap={true}
  onClose={() => {}}
/>
```

### ChatList.tsx
Conversation list for owner dashboard.

```tsx
<ChatList
  websiteId="website-uuid"
  onSelectConversation={(convId, orderId) => {}}
  selectedConversationId="uuid"
/>
```

### CustomerChatButton.tsx
Floating button for customers to start chat.

```tsx
<CustomerChatButton
  orderId="order-uuid"
  websiteId="website-uuid"
  customerName="John Doe"
  customerPhone="+60123456789"
/>
```

### RiderChat.tsx
Rider-specific chat with location sharing.

```tsx
<RiderChat
  orderId="order-uuid"
  riderId="rider-uuid"
  riderName="Rider Name"
  onClose={() => {}}
/>
```

## Pages

- `/dashboard/chat` - Owner chat dashboard

## Usage Flow

### Customer:
1. Place order → Conversation created automatically
2. Click chat button on order tracking page
3. Chat with owner about order
4. Upload payment proof if needed
5. Track rider on map

### Owner:
1. Go to `/dashboard/chat`
2. See all conversations
3. Reply to customers
4. Verify payment proofs
5. Track rider locations

### Rider:
1. Accept delivery assignment
2. Open rider chat
3. Enable location sharing
4. Chat with customer/owner
5. Location auto-updates every 10 seconds

## Environment Variables

No additional environment variables needed - uses existing Supabase and Cloudinary configuration.

## Dependencies

- FastAPI WebSocket support (built-in)
- Leaflet.js for maps (CDN loaded)
- Cloudinary for image uploads (existing)
- Supabase for database (existing)
