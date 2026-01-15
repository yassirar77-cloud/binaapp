# BinaApp - Complete Project Guide & Documentation

**Generated**: 2026-01-11
**Purpose**: Complete backup for account transition
**Project**: AI-Powered No-Code Website Builder for Malaysian SMEs

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [System Architecture](#system-architecture)
3. [Database Schema](#database-schema)
4. [Features & Functionality](#features--functionality)
5. [API Endpoints](#api-endpoints)
6. [Authentication System](#authentication-system)
7. [Order & Delivery System](#order--delivery-system)
8. [Chat System](#chat-system)
9. [Website Generation](#website-generation)
10. [Payment Processing](#payment-processing)
11. [Deployment](#deployment)
12. [Known Issues & Fixes](#known-issues--fixes)

---

## Project Overview

### What is BinaApp?

BinaApp is an **AI-powered no-code website builder specifically designed for Malaysian SMEs**. Users can create fully functional business websites by simply describing their business in Bahasa Malaysia or English.

### Key Value Propositions

- **Zero Coding Required**: Just describe your business in plain language
- **Instant Deployment**: Website published to `yourname.binaapp.my` in minutes
- **Pre-Integrated Features**: WhatsApp ordering, shopping cart, Google Maps, contact forms automatically included
- **Malaysian-Optimized**: AI trained on Malaysian business types, food items, and local context
- **Full Order Management**: Built-in delivery system with rider tracking

### Tech Stack

```
Frontend:
- Next.js 14 (App Router)
- React 18
- TypeScript
- Tailwind CSS
- Supabase Client
- Stripe.js

Backend:
- FastAPI (Python 3.11)
- Uvicorn
- Pydantic
- Supabase Python Client
- OpenAI SDK (for DeepSeek)

Database & Storage:
- Supabase (PostgreSQL)
- Supabase Storage (for website HTML files)
- Cloudinary (for images)

AI & Services:
- DeepSeek V3 (primary AI model)
- Qwen Max (fallback AI)
- Stability AI (food image generation)
- Stripe (payments)

Deployment:
- Frontend: Vercel
- Backend: Render (https://binaapp-backend.onrender.com)
- Database: Supabase (Singapore region)
```

---

## System Architecture

### Overall Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                        USER DEVICES                          │
│  Desktop Browser  │  Mobile Browser  │  PWA/Installed App   │
└───────────────┬─────────────────────────────────────────────┘
                │
                ↓
┌───────────────────────────────────────────────────────────────┐
│                     NEXT.JS FRONTEND                          │
│  - App Router Pages (/create, /profile, /editor, etc.)       │
│  - Supabase Auth Client (JWT tokens)                         │
│  - API Client (lib/api.ts) with auto JWT injection           │
└───────────────┬───────────────────────────────────────────────┘
                │
                ↓
┌───────────────────────────────────────────────────────────────┐
│                    FASTAPI BACKEND                            │
│  - Subdomain Middleware (serves .binaapp.my sites)           │
│  - API Routes (/v1/auth, /v1/websites, /v1/delivery, etc.)   │
│  - AI Service (DeepSeek + Qwen fallback)                     │
│  - WebSocket Manager (for real-time chat)                    │
└───────────────┬───────────────────────────────────────────────┘
                │
        ┌───────┴───────┬───────────────┬──────────────┐
        ↓               ↓               ↓              ↓
┌──────────────┐ ┌─────────────┐ ┌────────────┐ ┌────────────┐
│   SUPABASE   │ │  DeepSeek   │ │ Cloudinary │ │   Stripe   │
│              │ │    API      │ │   Images   │ │  Payments  │
│ - PostgreSQL │ │  AI Model   │ │  Storage   │ │            │
│ - Auth       │ │             │ │            │ │            │
│ - Storage    │ └─────────────┘ └────────────┘ └────────────┘
│ - RLS        │
└──────────────┘
```

### Request Flow

#### 1. Website Generation Request
```
User describes business in /create page
    ↓
Frontend sends POST to /v1/websites/generate
    ↓
Backend validates subdomain availability
    ↓
Call DeepSeek V3 API with Malaysian business context
    ↓
Generate complete HTML with integrations
    ↓
Store HTML in Supabase Storage (websites/{subdomain}/index.html)
    ↓
Update database record (status = published, public_url)
    ↓
Return success to frontend
    ↓
User visits {subdomain}.binaapp.my
    ↓
Middleware intercepts request
    ↓
Fetch HTML from Supabase Storage
    ↓
Serve HTML to user
```

#### 2. Order & Delivery Flow
```
Customer places order on website
    ↓
POST /v1/delivery/orders (creates order record)
    ↓
Create conversation in chat_conversations table
    ↓
Send system message to conversation
    ↓
Business owner sees order in /profile (Orders tab)
    ↓
Owner confirms order → status: confirmed
    ↓
Owner assigns rider → status: assigned
    ↓
Rider accepts in /rider app → status: picked_up
    ↓
Rider delivers → status: delivering
    ↓
Order complete → status: delivered
```

#### 3. Real-time Chat Flow
```
User opens chat interface
    ↓
WebSocket connection to /chat/ws/{conversationId}
    ↓
ConnectionManager tracks active connections
    ↓
User sends message
    ↓
Message stored in chat_messages table
    ↓
Broadcast to all participants in conversation
    ↓
Update read status when viewed
    ↓
Increment unread counts for others
```

### Subdomain Routing

The middleware in `backend/app/main.py` handles subdomain routing:

```python
# Request to: https://nasikandar.binaapp.my

1. Check if host ends with .binaapp.my
2. Extract subdomain: "nasikandar"
3. Query Supabase Storage for websites/nasikandar/index.html
4. Return HTML content
5. If not found, return 404
```

---

## Database Schema

### Core Tables

#### 1. `auth.users` (Supabase Auth)
- Managed by Supabase authentication system
- Stores email, encrypted password, metadata
- JWT tokens generated from this table

#### 2. `profiles`
```sql
id UUID (FK → auth.users.id)
full_name TEXT
avatar_url TEXT
phone TEXT
business_name TEXT  -- Added later
created_at TIMESTAMPTZ
updated_at TIMESTAMPTZ

RLS Policies:
- Users can view/update their own profile only
```

#### 3. `subscriptions`
```sql
id UUID PRIMARY KEY
user_id UUID (FK → auth.users)
tier TEXT (free, basic, pro, enterprise)
status TEXT (active, cancelled, expired)
stripe_customer_id TEXT
stripe_subscription_id TEXT
current_period_start TIMESTAMPTZ
current_period_end TIMESTAMPTZ

RLS Policies:
- Users can view their own subscription only

Subscription Tiers:
- Free: 1 website, 3 generations/day
- Basic: 5 websites, unlimited gen (RM29/mo)
- Pro: Unlimited websites (RM79/mo)
```

#### 4. `websites`
```sql
id UUID PRIMARY KEY
user_id UUID (FK → auth.users)
business_name TEXT
business_type TEXT
subdomain TEXT UNIQUE
status TEXT (draft, generating, published, failed)
language TEXT (default: 'ms')

-- Content
html_content TEXT  -- Full HTML stored here
meta_title TEXT
meta_description TEXT
sections TEXT[]
integrations TEXT[]

-- Integrations
include_whatsapp BOOLEAN
whatsapp_number TEXT
include_maps BOOLEAN
location_address TEXT
include_ecommerce BOOLEAN
contact_email TEXT

-- Publishing
published_at TIMESTAMPTZ
public_url TEXT  -- https://subdomain.binaapp.my
preview_url TEXT

-- Metadata
error_message TEXT
created_at TIMESTAMPTZ
updated_at TIMESTAMPTZ

Indexes:
- idx_websites_user_id
- idx_websites_subdomain
- idx_websites_status

RLS Policies:
- Users CRUD only their own websites
```

#### 5. `analytics`
```sql
id UUID PRIMARY KEY
website_id UUID (FK → websites)
total_views INTEGER
unique_visitors INTEGER
whatsapp_clicks INTEGER
form_submissions INTEGER
cart_interactions INTEGER
last_updated TIMESTAMPTZ
created_at TIMESTAMPTZ

UNIQUE(website_id)
```

### Menu & Delivery Tables

#### 6. `menu_categories`
```sql
id UUID PRIMARY KEY
website_id UUID (FK → websites)
name TEXT  -- "Nasi", "Mee", "Minuman"
slug TEXT
sort_order INTEGER
created_at TIMESTAMPTZ
updated_at TIMESTAMPTZ

UNIQUE(website_id, slug)
```

#### 7. `menu_items`
```sql
id UUID PRIMARY KEY
website_id UUID (FK → websites)
category_id UUID (FK → menu_categories)
name TEXT  -- "Nasi Lemak", "Teh Tarik"
description TEXT
price DECIMAL(10,2)
image_url TEXT  -- Cloudinary URL
is_available BOOLEAN
sort_order INTEGER
created_at TIMESTAMPTZ
updated_at TIMESTAMPTZ
```

#### 8. `delivery_zones`
```sql
id UUID PRIMARY KEY
website_id UUID (FK → websites)
zone_name TEXT  -- "Shah Alam", "Petaling Jaya"
delivery_fee DECIMAL(10,2)
estimated_time TEXT  -- "30-45 min"
is_active BOOLEAN
sort_order INTEGER
```

#### 9. `delivery_orders`
```sql
id UUID PRIMARY KEY
website_id UUID (FK → websites)
customer_id UUID
rider_id UUID (FK → riders)
order_number TEXT  -- "ORD-20250111-001"
status TEXT  -- pending, confirmed, assigned, picked_up, delivering, delivered, cancelled

-- Customer Info
customer_name TEXT
customer_phone TEXT
customer_address TEXT
delivery_notes TEXT

-- Order Details
order_items JSONB[]
subtotal DECIMAL(10,2)
delivery_fee DECIMAL(10,2)
total_amount DECIMAL(10,2)
payment_method TEXT  -- cash, online

-- Timestamps
created_at TIMESTAMPTZ
confirmed_at TIMESTAMPTZ
delivered_at TIMESTAMPTZ
cancelled_at TIMESTAMPTZ
```

#### 10. `order_items`
```sql
id UUID PRIMARY KEY
order_id UUID (FK → delivery_orders)
menu_item_id UUID (FK → menu_items)
item_name TEXT
quantity INTEGER
unit_price DECIMAL(10,2)
total_price DECIMAL(10,2)
created_at TIMESTAMPTZ
```

#### 11. `riders`
```sql
id UUID PRIMARY KEY
user_id UUID (FK → auth.users)
website_id UUID (FK → websites)
name TEXT
phone TEXT
vehicle_type TEXT  -- motorcycle, car, bicycle
vehicle_plate TEXT
is_active BOOLEAN
is_online BOOLEAN

-- Real-time Location
current_latitude DECIMAL(10,8)
current_longitude DECIMAL(10,8)
location_updated_at TIMESTAMPTZ

created_at TIMESTAMPTZ
updated_at TIMESTAMPTZ
```

### Chat System Tables

#### 12. `chat_conversations`
```sql
id UUID PRIMARY KEY
order_id UUID (FK → delivery_orders, nullable)
website_id UUID (FK → websites)

-- Customer
customer_id TEXT  -- phone or generated ID
customer_name TEXT
customer_phone TEXT

-- Status
status TEXT  -- active, closed, archived

-- Unread Counts
unread_owner INTEGER
unread_customer INTEGER
unread_rider INTEGER

created_at TIMESTAMPTZ
updated_at TIMESTAMPTZ
```

#### 13. `chat_messages`
```sql
id UUID PRIMARY KEY
conversation_id UUID (FK → chat_conversations)

-- Sender
sender_type TEXT  -- customer, owner, rider, system
sender_id TEXT
sender_name TEXT

-- Content
message_type TEXT  -- text, image, location, payment, status, voice
content TEXT
media_url TEXT  -- Cloudinary URL for images/voice
metadata JSONB  -- Location coords, payment info, etc.

-- Read Status
is_read BOOLEAN
read_at TIMESTAMPTZ
read_by JSONB  -- Array of user types who read

created_at TIMESTAMPTZ
```

#### 14. `chat_participants`
```sql
id UUID PRIMARY KEY
conversation_id UUID (FK → chat_conversations)

-- User
user_type TEXT  -- customer, owner, rider
user_id TEXT
user_name TEXT

-- Online Status
is_online BOOLEAN
last_seen TIMESTAMPTZ

created_at TIMESTAMPTZ

UNIQUE(conversation_id, user_type, user_id)
```

### Templates Table

#### 15. `templates`
```sql
id UUID PRIMARY KEY
name TEXT
category TEXT  -- restaurant, retail, services
description TEXT
html_template TEXT
thumbnail_url TEXT
preview_url TEXT
is_active BOOLEAN
created_at TIMESTAMPTZ
updated_at TIMESTAMPTZ

Public readable (for browsing templates)
```

---

## Features & Functionality

### 1. AI Website Generation

**Location**: `/create` page

**Process**:
1. User enters:
   - Business name
   - Business type (restaurant, salon, retail, etc.)
   - Business description (Bahasa/English)
   - Subdomain preference
   - Optional: WhatsApp number, location

2. Frontend validates subdomain availability
3. Backend calls DeepSeek V3 API with prompt:
   ```
   Generate a complete HTML website for a Malaysian {business_type}:
   - Business: {business_name}
   - Description: {description}
   - Include: Navigation, hero section, about, services/menu, contact
   - Auto-integrate: WhatsApp ordering, Google Maps, shopping cart
   - Style: Modern, responsive, Malaysian-friendly
   ```

4. AI generates complete HTML (5000+ lines)
5. HTML includes:
   - Responsive design (mobile-first)
   - Malaysian color schemes
   - WhatsApp floating button
   - Shopping cart system
   - Contact forms
   - Google Maps embed
   - QR codes
   - Social sharing buttons

6. Store in Supabase Storage: `websites/{subdomain}/index.html`
7. Update database record with public_url

**Key Files**:
- Frontend: `frontend/src/app/create/page.tsx`
- Backend: `backend/app/services/ai_service.py`
- Prompts: `backend/app/data/malaysian_prompts.py`

### 2. Order & Delivery Management

**Location**: `/profile` page (Orders tab)

**Features**:
- View all orders for all your websites
- Confirm/reject incoming orders
- Assign riders to orders
- Track order status in real-time
- View customer details and delivery info
- See order items and total amount

**Order Statuses**:
```
pending → confirmed → assigned → picked_up → delivering → delivered
                 ↓
              cancelled
```

**Workflow**:
1. Customer places order on website
2. Owner sees order in dashboard (pending)
3. Owner confirms → status: confirmed
4. Owner assigns rider → status: assigned
5. Rider accepts in rider app → status: picked_up
6. Rider starts delivery → status: delivering
7. Rider completes → status: delivered

**Key Files**:
- Frontend: `frontend/src/app/profile/page.tsx` (lines 204-360)
- Backend: `backend/app/api/v1/endpoints/delivery.py`

### 3. Real-time Chat System

**Location**: `/profile` page (Chat tab)

**Features**:
- Real-time messaging with customers
- WebSocket-based live updates
- Media uploads (images, location, voice)
- Read receipts
- Online status indicators
- System messages for order updates
- Unread message counts

**Architecture**:
```
Frontend (BinaChat component)
    ↓ WebSocket
Backend (ConnectionManager)
    ↓ Store message
Database (chat_messages)
    ↓ Broadcast
All participants in conversation
```

**Message Types**:
- `text`: Regular text message
- `image`: Image upload from Cloudinary
- `location`: GPS coordinates
- `payment`: Payment confirmation
- `status`: Order status update
- `voice`: Voice message recording
- `system`: Automated system messages

**Key Files**:
- Frontend: `frontend/src/components/BinaChat.tsx`
- Backend: `backend/app/api/v1/endpoints/chat.py`
- WebSocket: `backend/app/main.py` (ConnectionManager class)

### 4. Menu Designer (Restaurant Feature)

**Location**: `/menu-designer` page

**Features**:
- Create menu categories (Nasi, Mee, Minuman, etc.)
- Add menu items with pricing
- AI food image generation using Stability AI
- Malaysian-specific prompts (Nasi Lemak → detailed English prompt)
- Drag-and-drop reordering
- Toggle item availability

**AI Image Generation**:
```python
# User enters: "Nasi Lemak"
# System looks up in malaysian_prompts.py
# Finds: "Malaysian nasi lemak with fragrant coconut rice,
#        sambal, fried anchovies ikan bilis, peanuts, cucumber
#        slices, hard boiled egg, wrapped in banana leaf,
#        food photography"
# Sends to Stability AI
# Returns professional food photo
```

**Key Files**:
- Backend: `backend/app/data/malaysian_prompts.py` (80+ food items)
- API: `backend/app/api/v1/endpoints/menu_delivery.py`

### 5. Rider Management System

**Location**: `/rider` page (PWA for riders)

**Features**:
- Mobile-optimized PWA
- Accept/reject order assignments
- Update delivery status
- Real-time GPS tracking
- Customer contact info
- Navigation to delivery address
- Delivery completion confirmation

**GPS Tracking**:
```javascript
// Rider app updates location every 10 seconds
navigator.geolocation.watchPosition((position) => {
  updateRiderLocation({
    latitude: position.coords.latitude,
    longitude: position.coords.longitude
  })
})

// Customer sees rider location on map in real-time
```

**Key Files**:
- Frontend: `frontend/src/app/rider/page.tsx`
- Component: `frontend/src/components/RiderChat.tsx`

### 6. Analytics Dashboard

**Location**: `/analytics/[id]` page

**Metrics Tracked**:
- Total page views
- Unique visitors (cookie-based)
- WhatsApp button clicks
- Form submissions
- Cart interactions (add to cart, checkout)

**Implementation**:
```javascript
// In generated website HTML:
<script>
  // Track page view on load
  fetch('/api/analytics/track', {
    method: 'POST',
    body: JSON.stringify({
      website_id: '{id}',
      event_type: 'page_view'
    })
  })

  // Track WhatsApp clicks
  document.querySelector('.whatsapp-button').addEventListener('click', () => {
    fetch('/api/analytics/track', {
      method: 'POST',
      body: JSON.stringify({
        website_id: '{id}',
        event_type: 'whatsapp_click'
      })
    })
  })
</script>
```

**Key Files**:
- Frontend: `frontend/src/app/analytics/[id]/page.tsx`
- Component: `frontend/src/components/AnalyticsDashboard.tsx`

### 7. Payment Processing (Stripe)

**Subscription Plans**:
```
Free Tier:
- 1 website
- 3 AI generations per day
- All features included
- RM0/month

Basic Tier:
- 5 websites
- Unlimited AI generations
- Priority support
- RM29/month

Pro Tier:
- Unlimited websites
- Unlimited AI generations
- Priority support
- Custom domain support (coming soon)
- RM79/month
```

**Checkout Flow**:
1. User clicks "Upgrade" in dashboard
2. Frontend calls `/v1/payments/create-checkout-session`
3. Backend creates Stripe checkout session
4. User redirected to Stripe payment page
5. User completes payment
6. Stripe sends webhook to `/v1/payments/webhook`
7. Backend updates subscription record
8. User can now create more websites

**Key Files**:
- Backend: `backend/app/api/v1/endpoints/payments.py`
- Service: `backend/app/services/payment_service.py`

---

## API Endpoints

### Authentication Routes

```
POST   /v1/auth/register
Request:  { email, password, full_name }
Response: { user, session }

POST   /v1/auth/login
Request:  { email, password }
Response: { user, session, access_token }

GET    /v1/auth/me
Headers:  Authorization: Bearer {token}
Response: { id, email, full_name, subscription }

POST   /v1/auth/logout
Headers:  Authorization: Bearer {token}
Response: { success: true }
```

### Website Routes

```
POST   /v1/websites/generate
Request:  {
  business_name: "Nasi Kandar Yassir",
  business_type: "restaurant",
  description: "Restoran mamak 24 jam...",
  subdomain: "nasikandaryassir",
  include_whatsapp: true,
  whatsapp_number: "60123456789"
}
Response: { id, subdomain, public_url, status }

GET    /v1/websites
Response: [{ id, business_name, subdomain, status, ... }]

GET    /v1/websites/{id}
Response: { id, business_name, html_content, ... }

PUT    /v1/websites/{id}
Request:  { html_content, business_name, ... }
Response: { id, updated_at }

DELETE /v1/websites/{id}
Response: { success: true }

POST   /v1/websites/{id}/publish
Response: { public_url, published_at }

GET    /api/site/{subdomain}
Response: HTML content (served directly)

GET    /api/subdomain/check/{subdomain}
Response: { available: true/false }
```

### Order Routes

```
POST   /v1/delivery/orders
Request:  {
  website_id: "uuid",
  customer_name: "Ahmad",
  customer_phone: "0123456789",
  customer_address: "Jalan...",
  items: [
    { menu_item_id: "uuid", quantity: 2 }
  ],
  delivery_zone: "Shah Alam",
  payment_method: "cash"
}
Response: { id, order_number, total_amount, status }

GET    /v1/delivery/orders?website_id={id}
Response: [{ id, order_number, customer_name, status, ... }]

PUT    /v1/delivery/orders/{id}/status
Request:  { status: "confirmed" }
Response: { id, status, confirmed_at }

POST   /v1/delivery/rider/assign
Request:  { order_id: "uuid", rider_id: "uuid" }
Response: { order_id, rider_id, status: "assigned" }

PUT    /v1/delivery/rider/location
Request:  {
  rider_id: "uuid",
  latitude: 3.0738,
  longitude: 101.5183
}
Response: { success: true, updated_at }
```

### Menu Routes

```
POST   /v1/menu/websites/{website_id}/menu-categories
Request:  { name: "Nasi", slug: "nasi" }
Response: { id, name, slug, sort_order }

GET    /v1/menu/websites/{website_id}/menu-categories
Response: [{ id, name, slug, items_count }]

POST   /v1/menu/websites/{website_id}/menu-items
Request:  {
  category_id: "uuid",
  name: "Nasi Lemak",
  description: "With sambal",
  price: 6.50,
  image_url: "https://..."
}
Response: { id, name, price, image_url }

POST   /v1/menu/generate-food-image
Request:  { item_name: "Nasi Lemak", business_type: "restaurant" }
Response: { image_url: "https://cloudinary.../image.jpg" }
```

### Chat Routes

```
POST   /chat/create-conversation
Request:  {
  website_id: "uuid",
  order_id: "uuid",
  customer_id: "0123456789",
  customer_name: "Ahmad"
}
Response: { id, created_at }

GET    /chat/{conversation_id}/messages
Response: [
  {
    id, sender_type, sender_name,
    message_type, content, created_at
  }
]

POST   /chat/{conversation_id}/send
Request:  {
  sender_type: "customer",
  sender_id: "0123456789",
  sender_name: "Ahmad",
  message_type: "text",
  content: "Berapa lama lagi?"
}
Response: { id, created_at }

WS     /chat/ws/{conversation_id}
Send:     { type: "message", content: "Hello", sender_type: "owner" }
Receive:  { type: "message", id: "uuid", content: "Hello", ... }
```

### Analytics Routes

```
POST   /api/analytics/track
Request:  {
  website_id: "uuid",
  event_type: "page_view", // or whatsapp_click, form_submit, etc.
  visitor_id: "cookie_value"
}
Response: { success: true }

GET    /api/analytics/{website_id}
Response: {
  total_views: 1234,
  unique_visitors: 567,
  whatsapp_clicks: 89,
  form_submissions: 23,
  cart_interactions: 45
}
```

---

## Authentication System

### JWT Token Flow

```
1. User registers/logs in
    ↓
2. Supabase Auth creates user in auth.users
    ↓
3. Trigger creates profile + subscription records
    ↓
4. Supabase returns access_token (JWT)
    ↓
5. Frontend stores token in localStorage
    ↓
6. All API requests include: Authorization: Bearer {token}
    ↓
7. Backend verifies JWT signature
    ↓
8. Extract user_id from token.sub
    ↓
9. Use user_id in database queries
    ↓
10. RLS policies enforce data isolation
```

### Mobile Authentication Fix

**Problem**: Mobile browsers don't persist sessions across browser restarts

**Solution** (implemented in `frontend/src/app/profile/page.tsx`):

```typescript
// 1. Check for existing session
const { data: { session } } = await supabase.auth.getSession()

// 2. If no session, try to refresh (CRITICAL for mobile!)
if (!session) {
  const { data: refreshData } = await supabase.auth.refreshSession()

  if (refreshData.session?.user) {
    // Session recovered! ✅
    setUser(refreshData.session.user)
  } else {
    // Actually needs to login
    setTimeout(() => router.push('/login'), 1500)
  }
}

// 3. Listen for auth state changes
supabase.auth.onAuthStateChange((event, session) => {
  if (event === 'TOKEN_REFRESHED') {
    setUser(session.user)
    loadUserData() // Reload dashboard
  }
})
```

**Key Features**:
- PKCE flow for better mobile security
- Auto token refresh
- Delayed redirects to allow client hydration
- Auth state listener for real-time updates

### RLS (Row Level Security)

Every table has RLS policies to ensure users only access their own data:

```sql
-- Example: websites table
CREATE POLICY "Users can view own websites"
  ON public.websites FOR SELECT
  USING (auth.uid() = user_id);

-- This ensures:
SELECT * FROM websites WHERE id = 'any-id'
-- Automatically becomes:
SELECT * FROM websites WHERE id = 'any-id' AND user_id = auth.uid()
```

---

## Order & Delivery System

### Order Creation Flow

```javascript
// Customer on website clicks "Order Now"
const orderData = {
  website_id: websiteId,
  customer_name: "Ahmad",
  customer_phone: "0123456789",
  customer_address: "Jalan Sultan, Shah Alam",
  delivery_notes: "Call before arriving",
  items: [
    { menu_item_id: "uuid-1", quantity: 2 },
    { menu_item_id: "uuid-2", quantity: 1 }
  ],
  delivery_zone: "Shah Alam",
  payment_method: "cash"
}

// Backend processes:
1. Calculate subtotal from menu_items prices
2. Add delivery fee from delivery_zones
3. Calculate total_amount
4. Generate order_number (ORD-20250111-001)
5. Create order record
6. Create order_items records
7. Create chat conversation
8. Send system message: "Order #001 created"
9. Return order confirmation
```

### Order Status Workflow

```
PENDING:
- Just created by customer
- Waiting for owner confirmation
- Owner actions: Confirm or Reject

CONFIRMED:
- Owner accepted the order
- Ready to assign rider
- Owner action: Assign Rider

ASSIGNED:
- Rider assigned to order
- Rider sees order in rider app
- Rider action: Accept Assignment

PICKED_UP:
- Rider collected order from restaurant
- Starting delivery
- Rider action: Start Delivery

DELIVERING:
- Order in transit
- GPS tracking active
- Customer sees rider location on map
- Rider action: Mark as Delivered

DELIVERED:
- Order successfully delivered
- Rider confirms delivery
- Payment collected (if COD)
- Order complete

CANCELLED:
- Owner or customer cancelled
- Reason provided
- No further actions
```

### Rider Assignment

```typescript
// Owner selects rider from dropdown
async function assignRider(orderId: string, riderId: string) {
  const { data, error } = await supabase
    .from('delivery_orders')
    .update({
      status: 'assigned',
      rider_id: riderId,
      assigned_at: new Date().toISOString()
    })
    .eq('id', orderId)

  if (!error) {
    // Send notification to rider
    await sendRiderNotification(riderId, orderId)

    // Update chat conversation
    await sendSystemMessage(orderId, `Rider assigned: ${riderName}`)
  }
}
```

### GPS Tracking

```javascript
// Rider app (runs every 10 seconds)
navigator.geolocation.watchPosition(
  (position) => {
    updateLocation({
      rider_id: currentRider.id,
      latitude: position.coords.latitude,
      longitude: position.coords.longitude,
      accuracy: position.coords.accuracy
    })
  },
  (error) => console.error('GPS error:', error),
  {
    enableHighAccuracy: true,
    timeout: 5000,
    maximumAge: 0
  }
)

// Customer sees rider on map
const riderMarker = new google.maps.Marker({
  position: { lat: rider.latitude, lng: rider.longitude },
  map: map,
  icon: '/rider-icon.png',
  title: `Rider: ${rider.name}`
})

// Update marker position when rider moves
supabase
  .channel('rider-location')
  .on('postgres_changes', {
    event: 'UPDATE',
    schema: 'public',
    table: 'riders',
    filter: `id=eq.${rider.id}`
  }, (payload) => {
    riderMarker.setPosition({
      lat: payload.new.current_latitude,
      lng: payload.new.current_longitude
    })
  })
  .subscribe()
```

---

## Chat System

### WebSocket Connection

```typescript
// Frontend establishes WebSocket
const ws = new WebSocket('wss://binaapp-backend.onrender.com/chat/ws/{conversationId}')

ws.onopen = () => {
  console.log('Chat connected')
  // Send identification
  ws.send(JSON.stringify({
    type: 'identify',
    user_type: 'owner',
    user_id: websiteId,
    user_name: businessName
  }))
}

ws.onmessage = (event) => {
  const data = JSON.parse(event.data)

  if (data.type === 'message') {
    // New message received
    addMessageToChat(data)
  } else if (data.type === 'user_online') {
    // User came online
    updateUserStatus(data.user_type, true)
  }
}
```

### Connection Manager (Backend)

```python
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, conversation_id: str):
        await websocket.accept()
        if conversation_id not in self.active_connections:
            self.active_connections[conversation_id] = []
        self.active_connections[conversation_id].append(websocket)

    async def broadcast(self, conversation_id: str, message: dict):
        if conversation_id in self.active_connections:
            for connection in self.active_connections[conversation_id]:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    # Connection lost, remove it
                    self.active_connections[conversation_id].remove(connection)
```

### Message Types

```javascript
// Text message
{
  type: 'message',
  message_type: 'text',
  sender_type: 'customer',
  sender_name: 'Ahmad',
  content: 'Berapa lama lagi pesanan saya?'
}

// Image message
{
  type: 'message',
  message_type: 'image',
  sender_type: 'owner',
  sender_name: 'Kedai Nasi Kandar',
  content: 'Pesanan anda sedang disediakan',
  media_url: 'https://cloudinary.com/..../image.jpg'
}

// Location message
{
  type: 'message',
  message_type: 'location',
  sender_type: 'rider',
  sender_name: 'Ali',
  metadata: {
    latitude: 3.0738,
    longitude: 101.5183,
    address: 'Jalan Sultan, Shah Alam'
  }
}

// System message
{
  type: 'message',
  message_type: 'status',
  sender_type: 'system',
  content: 'Order status updated: Delivering'
}
```

---

## Website Generation

### DeepSeek V3 Prompt Structure

```python
system_prompt = """
You are an expert web developer specializing in creating beautiful,
responsive websites for Malaysian SMEs. Generate complete, production-ready
HTML that includes:

1. Modern, mobile-first responsive design
2. Malaysian-appropriate color schemes and imagery
3. Bahasa Malaysia and English bilingual support
4. Pre-integrated features:
   - WhatsApp ordering button
   - Shopping cart system (localStorage)
   - Google Maps embed
   - Contact forms
   - QR codes for sharing
   - Social media integration

5. Professional food photography (if restaurant)
6. Accessibility features
7. Fast loading, optimized code
8. SEO-friendly structure
"""

user_prompt = f"""
Create a complete website for:

Business Name: {business_name}
Business Type: {business_type}
Description: {description}

Requirements:
- Fully functional HTML/CSS/JavaScript
- No external dependencies (inline everything)
- Include sample menu/services based on business type
- WhatsApp: {whatsapp_number}
- Location: {location_address}
- Professional, ready to publish

Generate the COMPLETE HTML now:
"""

response = openai.ChatCompletion.create(
    model="deepseek-chat",
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ],
    max_tokens=16000,  # DeepSeek V3 supports long outputs
    temperature=0.7
)

html_content = response.choices[0].message.content
```

### Auto-Integrated Features

Every generated website includes:

#### 1. WhatsApp Ordering
```javascript
// Floating WhatsApp button (bottom right)
<a href="https://wa.me/60123456789?text=Saya%20nak%20order"
   class="whatsapp-float"
   target="_blank">
  <i class="fab fa-whatsapp"></i>
</a>

<style>
.whatsapp-float {
  position: fixed;
  bottom: 20px;
  right: 20px;
  width: 60px;
  height: 60px;
  background: #25D366;
  color: white;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 30px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.3);
  z-index: 1000;
}
</style>
```

#### 2. Shopping Cart
```javascript
// Cart stored in localStorage
const cart = {
  items: [],

  addItem(item) {
    this.items.push(item)
    this.save()
    this.updateCount()
  },

  removeItem(index) {
    this.items.splice(index, 1)
    this.save()
  },

  save() {
    localStorage.setItem('cart', JSON.stringify(this.items))
  },

  load() {
    const saved = localStorage.getItem('cart')
    this.items = saved ? JSON.parse(saved) : []
  },

  getTotal() {
    return this.items.reduce((sum, item) => sum + item.price, 0)
  },

  checkout() {
    const message = this.items.map(item =>
      `${item.name} x${item.quantity} - RM${item.price}`
    ).join('\n')

    const url = `https://wa.me/60123456789?text=${encodeURIComponent(message)}`
    window.open(url, '_blank')
  }
}
```

#### 3. Google Maps Embed
```html
<div class="map-container">
  <iframe
    src="https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d..."
    width="100%"
    height="400"
    frameborder="0"
    allowfullscreen>
  </iframe>
</div>
```

#### 4. Contact Form
```html
<form class="contact-form" onsubmit="handleSubmit(event)">
  <input type="text" name="name" placeholder="Nama" required>
  <input type="email" name="email" placeholder="Email" required>
  <textarea name="message" placeholder="Mesej" required></textarea>
  <button type="submit">Hantar</button>
</form>

<script>
function handleSubmit(e) {
  e.preventDefault()
  const formData = new FormData(e.target)
  const data = Object.fromEntries(formData)

  // Send to backend or WhatsApp
  const message = `
    Nama: ${data.name}
    Email: ${data.email}
    Mesej: ${data.message}
  `
  window.open(`https://wa.me/60123456789?text=${encodeURIComponent(message)}`)
}
</script>
```

---

## Payment Processing

### Stripe Integration

#### 1. Create Checkout Session

```python
# Backend: payment_service.py
import stripe

def create_checkout_session(user_id: str, tier: str):
    # Get or create Stripe customer
    customer = get_or_create_stripe_customer(user_id)

    # Price IDs (from Stripe dashboard)
    prices = {
        'basic': 'price_basic_monthly',
        'pro': 'price_pro_monthly'
    }

    # Create checkout session
    session = stripe.checkout.Session.create(
        customer=customer.id,
        payment_method_types=['card', 'fpx'],  # Malaysian FPX
        line_items=[{
            'price': prices[tier],
            'quantity': 1
        }],
        mode='subscription',
        success_url='https://www.binaapp.my/dashboard?payment=success',
        cancel_url='https://www.binaapp.my/dashboard?payment=cancelled',
        metadata={
            'user_id': user_id,
            'tier': tier
        }
    )

    return session.url
```

#### 2. Handle Webhook

```python
@router.post('/webhook')
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get('stripe-signature')

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, WEBHOOK_SECRET
        )
    except ValueError:
        raise HTTPException(status_code=400)

    if event.type == 'checkout.session.completed':
        session = event.data.object
        user_id = session.metadata.user_id
        tier = session.metadata.tier

        # Update subscription in database
        await update_subscription(
            user_id=user_id,
            tier=tier,
            status='active',
            stripe_subscription_id=session.subscription,
            stripe_customer_id=session.customer
        )

    elif event.type == 'invoice.payment_failed':
        # Handle failed payment
        subscription_id = event.data.object.subscription
        await handle_payment_failure(subscription_id)

    return {"success": True}
```

---

## Deployment

### Frontend (Vercel)

```bash
# Repository: Connected to GitHub
# Framework Preset: Next.js
# Build Command: npm run build
# Output Directory: .next

# Environment Variables (Vercel Dashboard):
NEXT_PUBLIC_SUPABASE_URL=https://xxx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbGc...
NEXT_PUBLIC_API_URL=https://binaapp-backend.onrender.com
NEXT_PUBLIC_STRIPE_KEY=pk_live_xxx
```

### Backend (Render)

```bash
# Service Type: Web Service
# Repository: Connected to GitHub
# Root Directory: backend
# Build Command: pip install -r requirements.txt
# Start Command: uvicorn app.main:app --host 0.0.0.0 --port 8000

# Environment Variables (Render Dashboard):
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJhbGc...
DEEPSEEK_API_KEY=sk-xxx
QWEN_API_KEY=sk-xxx
STRIPE_SECRET_KEY=sk_live_xxx
STRIPE_WEBHOOK_SECRET=whsec_xxx
CLOUDINARY_URL=cloudinary://xxx

# Health Check Path: /health
# Auto-Deploy: Yes (on push to main)
```

### Database (Supabase)

```sql
-- Run all migrations in order:
1. database/supabase/schema.sql (core tables)
2. supabase/002_delivery_and_menu_system.sql (menu + delivery)
3. backend/migrations/004_chat_system.sql (chat tables)
4. backend/migrations/006_fix_owner_orders_access.sql (RLS fix)

-- Enable Storage Bucket:
Bucket Name: websites
Public: Yes
File Size Limit: 10MB per file
Allowed MIME types: text/html

-- Enable Realtime:
Tables: chat_messages, chat_conversations, riders
```

---

## Known Issues & Fixes

### 1. Mobile Authentication Issue

**Problem**: Users logged out after browser restart on mobile

**Root Cause**: Mobile browsers don't persist Supabase sessions reliably

**Solution**: Implemented session refresh logic (see `MOBILE_AUTH_FIX.md`)

**Files Changed**:
- `frontend/src/app/profile/page.tsx` (lines 74-134)
- `frontend/src/lib/supabase.ts` (added PKCE flow)

**Status**: ✅ FIXED

### 2. Order Confirmation RLS Error

**Problem**: Owners couldn't confirm orders (RLS policy blocked updates)

**Error**: `PGRST301: row-level security policy violation`

**Solution**: Updated RLS policies to allow owners to update orders for their websites

**Migration**: `backend/migrations/006_fix_owner_orders_access.sql`

**Status**: ✅ FIXED

### 3. Cross-Domain Mobile Auth

**Problem**: Mobile browsers block cookies from different domains

**Root Cause**: Frontend (binaapp.my) → Backend (render.com) = cross-domain

**Solution**: Use JWT tokens in Authorization header instead of cookies

**Implementation** (`frontend/src/lib/api.ts`):
```typescript
async function getAuthToken(): Promise<string | null> {
  const { data: { session } } = await supabase.auth.getSession()
  return session?.access_token || null
}

// Add to all API requests
extraHeaders['Authorization'] = `Bearer ${token}`
```

**Status**: ✅ FIXED

### 4. Chat System Not Loading

**Problem**: Chat tab shows "Chat System Setup Required"

**Root Cause**: Chat tables not created in database

**Solution**: Run migration `backend/migrations/004_chat_system.sql`

**Status**: ⚠️ Requires migration (documented in profile page)

---

## Critical Files Reference

### Frontend Core Files

```
frontend/src/
├── app/
│   ├── page.tsx                    # Landing page
│   ├── create/page.tsx             # AI website generation (CRITICAL)
│   ├── profile/page.tsx            # Owner dashboard (CRITICAL)
│   ├── editor/[id]/page.tsx        # HTML editor
│   ├── my-projects/page.tsx        # Website list
│   ├── rider/page.tsx              # Rider PWA app
│   └── analytics/[id]/page.tsx     # Analytics dashboard
│
├── components/
│   ├── BinaChat.tsx                # Real-time chat (CRITICAL)
│   ├── ChatList.tsx                # Conversation list
│   ├── RiderChat.tsx               # Rider-specific chat
│   └── AnalyticsDashboard.tsx      # Charts
│
└── lib/
    ├── api.ts                      # API client with JWT (CRITICAL)
    ├── supabase.ts                 # Supabase client config (CRITICAL)
    └── env.ts                      # Environment variables
```

### Backend Core Files

```
backend/app/
├── main.py                         # FastAPI app + subdomain routing (CRITICAL)
│
├── api/v1/
│   └── endpoints/
│       ├── auth.py                 # Authentication
│       ├── websites.py             # Website CRUD
│       ├── delivery.py             # Orders & riders
│       ├── menu_delivery.py        # Menu management
│       ├── chat.py                 # WebSocket chat (CRITICAL)
│       └── payments.py             # Stripe integration
│
├── services/
│   ├── ai_service.py               # DeepSeek integration (CRITICAL)
│   ├── supabase_client.py          # Database operations
│   ├── storage_service.py          # File uploads
│   └── payment_service.py          # Stripe operations
│
├── core/
│   ├── config.py                   # Environment config (CRITICAL)
│   └── security.py                 # JWT verification
│
└── data/
    └── malaysian_prompts.py        # AI prompts for Malaysian items (CRITICAL)
```

### Database Migrations

```
database/supabase/schema.sql                          # Core tables
supabase/002_delivery_and_menu_system.sql            # Menu + delivery
backend/migrations/004_chat_system.sql               # Chat tables
backend/migrations/006_fix_owner_orders_access.sql   # RLS fixes
```

---

## Development Setup

### Prerequisites

```bash
# Required Software
Node.js >= 20.0.0
Python >= 3.11
npm or yarn
pip

# Required Accounts
- Supabase account (database + auth + storage)
- DeepSeek API key (https://platform.deepseek.com)
- Stripe account (payments)
- Cloudinary account (image uploads)
```

### Local Development

```bash
# 1. Clone repository
git clone https://github.com/yassirar77-cloud/binaapp.git
cd binaapp

# 2. Frontend setup
cd frontend
cp .env.example .env.local
# Edit .env.local with your keys
npm install
npm run dev
# Frontend runs on http://localhost:3000

# 3. Backend setup (new terminal)
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your keys
uvicorn app.main:app --reload
# Backend runs on http://localhost:8000

# 4. Database setup
# Go to Supabase dashboard
# Run migrations in SQL editor (in order):
#   1. database/supabase/schema.sql
#   2. supabase/002_delivery_and_menu_system.sql
#   3. backend/migrations/004_chat_system.sql

# 5. Storage setup
# Create bucket named "websites" (public)
# Enable Realtime for chat tables
```

---

## Next Steps & Roadmap

### Immediate Priorities

1. **Custom Domain Support**
   - Allow users to point their own domain to BinaApp
   - SSL certificate automation
   - DNS configuration guide

2. **Mobile App (React Native)**
   - Native iOS & Android apps
   - Push notifications for orders
   - Offline mode for rider app

3. **Advanced E-commerce**
   - Product inventory management
   - Multiple payment gateways (FPX, TNG, Grab Pay)
   - Discount codes & promotions
   - Customer loyalty program

4. **White-Label Solution**
   - Allow agencies to resell BinaApp
   - Custom branding
   - Multi-tenant architecture

### Feature Requests

- Multi-language support (Chinese, Tamil)
- Advanced analytics (Google Analytics integration)
- Email marketing integration
- Automated social media posting
- AI chatbot for customer support
- Voice ordering via WhatsApp
- Table reservation system (for restaurants)
- Appointment booking (for salons)

---

## Support & Maintenance

### Monitoring

```bash
# Check backend health
curl https://binaapp-backend.onrender.com/health

# Check frontend
curl https://www.binaapp.my

# Database status
# Login to Supabase dashboard → Database → Health

# Error logs
# Render dashboard → Logs
# Vercel dashboard → Functions → Logs
```

### Common Maintenance Tasks

```sql
-- Check active subscriptions
SELECT tier, status, COUNT(*)
FROM subscriptions
GROUP BY tier, status;

-- Find websites needing republishing
SELECT id, business_name, subdomain, status
FROM websites
WHERE status = 'failed' OR error_message IS NOT NULL;

-- Monitor order volume
SELECT DATE(created_at), COUNT(*), SUM(total_amount)
FROM delivery_orders
WHERE created_at > NOW() - INTERVAL '7 days'
GROUP BY DATE(created_at)
ORDER BY DATE(created_at) DESC;

-- Active conversations
SELECT COUNT(*)
FROM chat_conversations
WHERE status = 'active';
```

### Backup Strategy

```bash
# Database (Supabase handles automatic backups)
# Point-in-time recovery available
# Export via Supabase dashboard → Database → Backups

# Storage (Supabase Storage)
# Automatic replication
# Manual export: Use Supabase CLI

# Code
# GitHub repository (main branch)
# Tags for releases
```

---

## Security Considerations

### API Security

```python
# All protected endpoints require JWT
@router.get('/websites')
async def get_websites(user_id: str = Depends(get_current_user)):
    # user_id extracted from verified JWT
    return get_user_websites(user_id)

# Rate limiting (per user)
from slowapi import Limiter
limiter = Limiter(key_func=get_user_id)

@limiter.limit("10/minute")
@router.post('/websites/generate')
async def generate_website(...):
    ...
```

### Content Security

```python
# Subdomain validation (prevent abuse)
BLOCKED_WORDS = [
    'admin', 'api', 'www', 'mail', 'ftp',
    'porn', 'sex', 'gambling',  # Inappropriate
    'mamak', 'islam', 'masjid',  # Sensitive
    'google', 'facebook', 'microsoft'  # Trademarks
]

def validate_subdomain(subdomain: str) -> bool:
    subdomain = subdomain.lower()

    # Check blocked words
    for word in BLOCKED_WORDS:
        if word in subdomain:
            raise ValueError(f"Subdomain contains blocked word: {word}")

    # Check format
    if not re.match(r'^[a-z0-9\-]{3,30}$', subdomain):
        raise ValueError("Invalid subdomain format")

    return True
```

### Database Security

```sql
-- RLS ensures data isolation
-- Users CANNOT access other users' data even if they try

-- Example attack attempt:
SELECT * FROM websites WHERE id = 'someone-else-website-id'

-- RLS automatically converts to:
SELECT * FROM websites
WHERE id = 'someone-else-website-id'
AND user_id = auth.uid()  -- FAILS if not owner

-- Result: Empty set (no data leaked)
```

---

## Performance Optimization

### Frontend

```javascript
// Code splitting
const BinaChat = dynamic(() => import('@/components/BinaChat'), {
  ssr: false,
  loading: () => <div>Loading chat...</div>
})

// Image optimization
<Image
  src="/hero.jpg"
  width={1200}
  height={600}
  placeholder="blur"
  loading="lazy"
/>

// API caching
const { data, error } = useSWR('/api/websites', fetcher, {
  revalidateOnFocus: false,
  dedupingInterval: 60000  // 1 minute
})
```

### Backend

```python
# Database connection pooling
supabase_client = create_client(
    supabase_url,
    supabase_key,
    options={
        'pool_size': 10,  # Max connections
        'max_overflow': 5  # Extra if needed
    }
)

# Response caching
from functools import lru_cache

@lru_cache(maxsize=100)
def get_menu_items(website_id: str):
    return supabase.table('menu_items').select('*').eq('website_id', website_id).execute()

# Async operations
import asyncio

async def process_order(order_id):
    # Multiple operations in parallel
    await asyncio.gather(
        create_conversation(order_id),
        send_notification(order_id),
        update_analytics(order_id)
    )
```

---

## Conclusion

This guide contains everything needed to continue BinaApp development:

✅ Complete system architecture
✅ Database schema with all tables
✅ All API endpoints documented
✅ Authentication flow explained
✅ Order & delivery system details
✅ Chat system WebSocket implementation
✅ AI website generation process
✅ Payment processing with Stripe
✅ Deployment instructions
✅ Known issues & fixes applied
✅ Critical files reference
✅ Development setup guide

**For any questions**, refer to:
- Code comments in critical files
- Additional documentation in `/docs` folder
- Database schema SQL files
- Environment variable templates

**Project Repository**: https://github.com/yassirar77-cloud/binaapp

---

**Last Updated**: 2026-01-11
**Version**: 1.0
**Status**: Production-ready ✅
