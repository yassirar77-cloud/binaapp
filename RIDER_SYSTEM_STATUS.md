# Rider System Status Report
**Generated:** 2026-01-11
**Purpose:** Comprehensive overview of implemented rider features

---

## ✅ Implemented Features

### 1. Backend API Endpoints (`backend/app/api/v1/endpoints/delivery.py`)

#### Rider Management Endpoints (RLS-Protected)
- ✅ `GET /admin/websites/{website_id}/riders` - List all riders for a website (delivery.py:989-1003)
- ✅ `POST /admin/websites/{website_id}/riders` - Create new rider (delivery.py:1006-1027)
- ✅ `GET /admin/websites/{website_id}/settings` - Get delivery settings (delivery.py:1030-1053)
- ✅ `PUT /admin/websites/{website_id}/settings` - Update delivery settings (delivery.py:1056-1081)

#### Public Rider Endpoints (For Dashboards)
- ✅ `GET /website/{website_id}/riders` - Get riders for website (delivery.py:1263-1296)
- ✅ `POST /website/{website_id}/riders` - Create rider (delivery.py:1299-1327)
- ✅ `PUT /website/{website_id}/riders/{rider_id}` - Update rider (delivery.py:1330-1370)

#### Rider Assignment
- ✅ `PUT /admin/orders/{order_id}/assign-rider` - Assign rider with WhatsApp notification (delivery.py:886-986)
- ✅ `PUT /orders/{order_id}/assign-rider` - Public assign endpoint (delivery.py:1373-1497)

#### Rider GPS Location Tracking
- ✅ `PUT /riders/{rider_id}/location` - Update GPS location (delivery.py:1672-1767)
- ✅ `GET /riders/{rider_id}/location` - Get current GPS location (delivery.py:1770-1809)
- ✅ `GET /riders/{rider_id}/location/history` - Get location history (delivery.py:1812-1842)

#### Rider App Endpoints
- ✅ `POST /riders/login` - Rider authentication (delivery.py:2016-2086)
- ✅ `GET /riders/{rider_id}/orders` - Get orders assigned to rider (delivery.py:1845-1906)
- ✅ `PUT /riders/{rider_id}/orders/{order_id}/status` - Update order status by rider (delivery.py:1909-2004)

#### Order Tracking with Rider Info
- ✅ `GET /orders/{order_number}/track` - Track order with rider GPS data (delivery.py:597-680)
- ✅ `GET /orders/{order_number}/status` - Simplified order status (delivery.py:1596-1648)

---

### 2. Database Schema (`backend/migrations/002_delivery_system.sql`)

#### Riders Table (Lines 77-109)
```sql
CREATE TABLE riders (
    id UUID PRIMARY KEY,
    website_id UUID,              -- Can be null for shared riders
    name VARCHAR(200),
    phone VARCHAR(20),
    email VARCHAR(200),
    photo_url TEXT,
    vehicle_type VARCHAR(50),     -- motorcycle, bicycle, car
    vehicle_plate VARCHAR(20),
    vehicle_model VARCHAR(100),
    is_active BOOLEAN,
    is_online BOOLEAN,
    current_latitude DECIMAL(10,8),    -- GPS tracking
    current_longitude DECIMAL(11,8),   -- GPS tracking
    last_location_update TIMESTAMPTZ,
    total_deliveries INTEGER,
    rating DECIMAL(3,2),
    total_ratings INTEGER,
    password_hash TEXT,
    auth_token TEXT,
    created_at TIMESTAMPTZ
)
```

#### Rider Locations Table (Lines 184-192)
```sql
CREATE TABLE rider_locations (
    id UUID PRIMARY KEY,
    rider_id UUID,
    order_id UUID,                -- Optional: link to order
    latitude DECIMAL(10,8),
    longitude DECIMAL(11,8),
    recorded_at TIMESTAMPTZ
)
```

#### Orders Table - Rider Relationship (Line 159)
```sql
CREATE TABLE delivery_orders (
    ...
    rider_id UUID REFERENCES riders(id),  -- Rider assignment
    ...
)
```

#### RLS Policies
- ✅ Business owners can view/manage riders for their websites (Lines 330-342)
- ✅ Public can view riders (for simple dashboards)
- ✅ Rider location history tied to order permissions (Lines 388-414)

#### Indexes
- ✅ `idx_riders_online` - Fast lookup of online riders (Line 256)
- ✅ `idx_rider_locations_rider` - Location history by rider (Line 254)
- ✅ `idx_orders_rider` - Orders by rider (Line 251)

---

### 3. Frontend Pages

#### Profile Page (`frontend/src/app/profile/page.tsx`)
**Location:** Lines 242-263, 329-355, 644-766

**Implemented:**
- ✅ Load riders for user's websites (loadRiders function)
- ✅ Display rider info on orders (name, phone, vehicle plate)
- ✅ Assign rider to order via dropdown (assignRider function)
- ✅ Filter riders by website (own riders + shared riders)

**Missing:**
- ❌ No UI to create/add new riders
- ❌ No UI to edit rider details
- ❌ No UI to view rider list/management panel
- ❌ No UI to deactivate/delete riders

#### Rider App (`frontend/src/app/rider/page.tsx`)
**Fully Implemented Mobile App**

**Features:**
- ✅ Rider login with phone + password (Lines 84-110)
- ✅ GPS tracking (Lines 125-169)
  - Watches position every 15 seconds
  - Sends to API: `PUT /riders/{id}/location`
  - Shows GPS status indicator
- ✅ View assigned orders (Lines 192-218)
  - Auto-refresh every 30 seconds
  - Shows order details, customer info, address
- ✅ Update order status (Lines 220-264)
  - Mark as picked_up, delivering, delivered
  - Sends to API with timestamp
- ✅ View active order details
- ✅ Persistent login (localStorage)
- ✅ Logout functionality

---

### 4. Data Models & Schemas (`backend/app/models/delivery_schemas.py`)

#### Rider Schemas
- ✅ `RiderBase` - Base rider fields (Lines 383-391)
- ✅ `RiderCreate` - Create with password (Lines 394-396)
- ✅ `RiderUpdate` - Update rider info (Lines 399-407)
- ✅ `RiderResponse` - Full rider data (Lines 410-423)
- ✅ `RiderCreateBusiness` - Phase 1 creation (no password) (Lines 435-441)
- ✅ `AssignRiderRequest` - Assign payload (Lines 444-445)
- ✅ `RiderLocationUpdate` - GPS update (Lines 426-428)
- ✅ `RiderInfoResponse` - Tracking info (Lines 292-304)
- ✅ `RiderLocationResponse` - GPS data (Lines 283-289)

#### Enums
- ✅ `VehicleType` - motorcycle, bicycle, car (Lines 42-45)

---

## ⚠️ Partially Implemented

### Owner Dashboard - Rider Management UI
**What exists:**
- Can view riders assigned to orders
- Can assign riders from dropdown

**What's missing:**
- No dedicated "Riders" section/tab in profile
- No list view of all riders
- No "Add Rider" button/form
- No edit rider details UI
- No delete/deactivate rider UI

### WhatsApp Notifications
**What exists:**
- Backend generates WhatsApp link when rider assigned (delivery.py:948-976)
- Returns `whatsapp_notification` object with clickable link

**What's missing:**
- Frontend doesn't display WhatsApp link to owner
- No automatic WhatsApp sending (manual click required)

### Rider Performance Analytics
**What exists:**
- Database fields: `total_deliveries`, `rating`, `total_ratings`

**What's missing:**
- No UI to view rider stats
- No rating system implementation
- No delivery count tracking (field exists but not incremented)

---

## ❌ Missing Features

### 1. Owner Flow - Add/Manage Riders
**Critical Gap:** No UI to create riders

**Current workaround:**
- Must use API directly: `POST /admin/websites/{website_id}/riders`
- Or insert via Supabase dashboard

**Needed:**
```tsx
// Add to profile page:
- "Riders" tab alongside Websites/Orders/Chat
- "Add Rider" button
- Modal/form with fields:
  - Name, Phone, Email
  - Vehicle type, plate, model
  - Photo upload
  - Password (for rider app login)
- Rider list table:
  - Edit, Delete actions
  - Toggle active/inactive
  - View deliveries count
```

### 2. Real-time GPS Tracking Map
**What exists:**
- Rider sends GPS every 15 seconds
- GPS stored in database
- API returns GPS in order tracking

**What's missing:**
- No map display in customer order tracking
- No map display in owner dashboard
- No live rider location on map

**Needed:**
```tsx
// For customer tracking page:
- Google Maps embed
- Show rider marker (moving in real-time)
- Show customer location marker
- Polyline route
- ETA calculation

// For owner dashboard:
- Map view of all active riders
- Real-time updates via Supabase Realtime
```

### 3. Rider Ratings & Reviews
**Database ready but not implemented:**

**Needed:**
```sql
-- New table
CREATE TABLE rider_reviews (
    id UUID PRIMARY KEY,
    rider_id UUID,
    order_id UUID,
    customer_id UUID,
    rating INTEGER,  -- 1-5
    review TEXT,
    created_at TIMESTAMPTZ
)
```

**Frontend:**
- Rating prompt after delivery
- Display average rating on rider profile
- Reviews list in rider details

### 4. Rider Earnings & Payouts
**No implementation:**

**Needed:**
```sql
CREATE TABLE rider_earnings (
    id UUID PRIMARY KEY,
    rider_id UUID,
    order_id UUID,
    delivery_fee DECIMAL,
    commission DECIMAL,
    net_earning DECIMAL,
    paid BOOLEAN,
    paid_at TIMESTAMPTZ
)
```

**UI:**
- Rider earnings dashboard
- Weekly/monthly summaries
- Payout history

### 5. Rider Availability Scheduling
**No implementation:**

**Needed:**
- Rider sets available hours
- Auto-offline when outside hours
- Shift management

### 6. Push Notifications
**No implementation:**

**Needed:**
- Web Push API for browser notifications
- FCM for mobile apps
- Notify rider of new order assignment
- Notify owner when rider accepts/rejects

### 7. Rider Auto-Assignment
**No implementation:**

**Needed:**
- Algorithm to auto-assign nearest available rider
- Based on:
  - Distance from restaurant
  - Current deliveries
  - Availability
  - Rating

---

## 🗺️ Current User Flows

### Owner Flow

#### 1. How does owner add riders?
**Currently:**
❌ **NO UI EXISTS** - Must use one of these methods:

**Option A: Direct API call**
```bash
curl -X POST https://api.binaapp.my/v1/delivery/admin/websites/{website_id}/riders \
  -H "Authorization: Bearer {JWT}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Ahmad Rider",
    "phone": "+60123456789",
    "vehicle_type": "motorcycle",
    "vehicle_plate": "ABC1234"
  }'
```

**Option B: Supabase Dashboard**
1. Go to Supabase SQL Editor
2. Run:
```sql
INSERT INTO riders (name, phone, website_id, vehicle_type, vehicle_plate, password)
VALUES ('Ahmad', '+60123456789', '{website_id}', 'motorcycle', 'ABC1234', 'password123');
```

#### 2. How does owner assign rider to order?
**Currently: ✅ WORKS**

1. Go to `/profile`
2. Click "Orders" tab
3. Find order in pending/confirmed status
4. Scroll to "🛵 Pilih Rider untuk Hantar" section
5. Select rider from dropdown
6. Order status auto-updates to "ready"
7. Rider appears in order details

**Code:** `frontend/src/app/profile/page.tsx:759-770`

#### 3. How does owner view order with rider?
**Currently: ✅ WORKS**

1. In Orders tab
2. Each order card shows:
   - Rider name
   - Rider phone (clickable to call)
   - Vehicle plate number

**Code:** `frontend/src/app/profile/page.tsx:712-724`

---

### Rider Flow

#### 1. How does rider login?
**Currently: ✅ WORKS**

1. Go to `/rider`
2. Enter phone number (e.g., +60123456789)
3. Enter password
4. Click "Log Masuk"
5. System validates credentials via `POST /riders/login`
6. On success:
   - Saves rider data to localStorage
   - Starts GPS tracking automatically
   - Shows rider dashboard

**Code:** `frontend/src/app/rider/page.tsx:84-110`

#### 2. How does rider see their orders?
**Currently: ✅ WORKS**

1. After login, orders auto-load
2. Shows list of assigned orders with:
   - Order number
   - Customer name, phone
   - Delivery address
   - Total amount
   - Status
3. Auto-refreshes every 30 seconds
4. Filter by status: ready, picked_up, delivering

**Code:** `frontend/src/app/rider/page.tsx:192-218`

#### 3. How does rider update GPS location?
**Currently: ✅ WORKS (Automatic)**

1. On login, requests GPS permission
2. Starts watching position (high accuracy mode)
3. Every ~15 seconds when position changes:
   - Sends `PUT /riders/{id}/location`
   - Updates `riders.current_latitude/longitude`
   - Logs to `rider_locations` table
4. Shows GPS status:
   - ✅ Green = Active
   - ❌ Red = Failed/Disabled

**Code:** `frontend/src/app/rider/page.tsx:125-189`

#### 4. How does rider update order status?
**Currently: ✅ WORKS**

1. Click on order to view details
2. Click status button:
   - "Ambil Pesanan" → `picked_up`
   - "Dalam Perjalanan" → `delivering`
   - "Telah Dihantar" → `delivered`
3. System updates order via `PUT /riders/{id}/orders/{order_id}/status`
4. Updates timestamp (picked_up_at, delivered_at)
5. Logs to order_status_history

**Code:** `frontend/src/app/rider/page.tsx:220-264`

---

### Customer Flow

#### 1. How does customer track rider?
**Currently: ⚠️ PARTIAL**

**What works:**
1. Go to order tracking URL with order number
2. See order status
3. See rider name, phone, vehicle (if assigned)

**What's missing:**
- ❌ No map showing rider location
- ❌ No real-time GPS updates visible
- ❌ No ETA calculation
- ⚠️ GPS data exists in API but not displayed

**Backend ready:** `GET /orders/{order_number}/track` returns:
```json
{
  "rider": {
    "name": "Ahmad",
    "phone": "+60123456789",
    "vehicle_type": "motorcycle"
  },
  "rider_location": {
    "latitude": 3.1390,
    "longitude": 101.6869,
    "recorded_at": "2026-01-11T10:30:00Z"
  },
  "eta_minutes": 15
}
```

**Code:** `backend/app/api/v1/endpoints/delivery.py:636-670`

---

## 📋 Next Steps - Priority Order

### 🔴 CRITICAL (Must have for basic functionality)

#### 1. Add Rider Management UI in Owner Dashboard
**Effort:** Medium | **Impact:** High

**Implementation:**
```tsx
// Add to frontend/src/app/profile/page.tsx

1. Add "Riders" tab (Line 25, alongside 'websites' | 'orders' | 'chat')
2. Create riders state and loadRiders() already exists (Lines 24, 242-263)
3. Add UI section:
   - Header: "🛵 Pengurusan Rider"
   - "Tambah Rider Baru" button
   - Riders table with columns:
     - Name, Phone, Vehicle, Status
     - Actions: Edit, Delete, Toggle Active
4. Add modal for creating rider:
   - Form fields: name, phone, email, vehicle_type, vehicle_plate, password
   - POST to /admin/websites/{website_id}/riders
5. Add edit modal (same form, PUT to update endpoint)
```

**Files to modify:**
- `frontend/src/app/profile/page.tsx`

**API endpoints already exist:**
- ✅ `GET /admin/websites/{website_id}/riders`
- ✅ `POST /admin/websites/{website_id}/riders`
- ✅ `PUT /website/{website_id}/riders/{rider_id}`

---

#### 2. Fix Rider Password Field in Database
**Effort:** Small | **Impact:** High

**Problem:**
- Schema has `password_hash` but API uses plain `password`
- Rider login compares plain text (insecure)

**Solution:**
```sql
-- Migration
ALTER TABLE riders ADD COLUMN password TEXT;
UPDATE riders SET password = password_hash WHERE password_hash IS NOT NULL;
ALTER TABLE riders DROP COLUMN password_hash;
```

**Backend:** Add bcrypt hashing in `delivery.py:2016-2086`

---

### 🟡 HIGH PRIORITY (Needed for good UX)

#### 3. Add Google Maps to Customer Tracking Page
**Effort:** Medium | **Impact:** High

**Implementation:**
```tsx
// Create new component: frontend/src/components/OrderTrackingMap.tsx

1. Embed Google Maps
2. Show customer location (delivery_latitude/longitude)
3. Show rider location (from API: rider_location)
4. Use Supabase Realtime to subscribe to rider GPS updates:
   - Subscribe to riders table changes where id = rider_id
   - Update marker position in real-time
5. Calculate route and ETA using Google Maps Directions API
```

**API integration:**
```typescript
// Subscribe to rider location
const subscription = supabase
  .channel('rider-location')
  .on('postgres_changes',
    { event: 'UPDATE', schema: 'public', table: 'riders', filter: `id=eq.${riderId}` },
    (payload) => {
      updateMapMarker(payload.new.current_latitude, payload.new.current_longitude)
    }
  )
  .subscribe()
```

**Files to create:**
- `frontend/src/components/OrderTrackingMap.tsx`
- `frontend/src/app/track/[orderNumber]/page.tsx` (if doesn't exist)

---

#### 4. Display WhatsApp Notification Link to Owner
**Effort:** Small | **Impact:** Medium

**Current:** Backend generates WhatsApp link but frontend doesn't show it

**Implementation:**
```tsx
// In frontend/src/app/profile/page.tsx

// After assignRider() success:
if (response.whatsapp_notification) {
  const { whatsapp_link, message_preview } = response.whatsapp_notification

  // Show modal or toast:
  alert(`✅ Rider assigned!\n\nClick to notify via WhatsApp:\n${whatsapp_link}`)

  // Or auto-open:
  window.open(whatsapp_link, '_blank')
}
```

---

### 🟢 MEDIUM PRIORITY (Nice to have)

#### 5. Rider Performance Dashboard
**Effort:** Medium | **Impact:** Medium

**Features:**
- Total deliveries count (increment on delivery completion)
- Average rating
- Total earnings this week/month
- Delivery history

**Implementation:**
- Add triggers to increment `total_deliveries` on order completion
- Create rider stats page in `/rider` app
- Add earnings calculation logic

---

#### 6. Auto-assign Nearest Rider
**Effort:** High | **Impact:** High

**Algorithm:**
```sql
-- Find available riders sorted by distance
SELECT r.*,
  SQRT(POW(r.current_latitude - {order_lat}, 2) + POW(r.current_longitude - {order_lng}, 2)) as distance
FROM riders r
WHERE r.website_id = {website_id}
  AND r.is_active = true
  AND r.is_online = true
  AND r.id NOT IN (
    SELECT rider_id FROM delivery_orders
    WHERE status IN ('picked_up', 'delivering')
  )
ORDER BY distance ASC
LIMIT 1
```

**Implementation:**
- Add "Auto Assign" button in owner dashboard
- Add API endpoint: `POST /orders/{order_id}/auto-assign-rider`
- Return assigned rider info

---

#### 7. Push Notifications
**Effort:** High | **Impact:** High

**Technologies:**
- Web Push API (for web browsers)
- Firebase Cloud Messaging (for mobile)

**Use cases:**
- Notify rider when order assigned
- Notify owner when rider accepts/declines
- Notify customer when order status changes

**Implementation:**
- Add push notification service
- Store device tokens in database
- Send notifications on order events

---

### 🔵 LOW PRIORITY (Future enhancements)

#### 8. Rider Ratings & Reviews
**Effort:** Medium | **Impact:** Low

- Customer rates rider after delivery (1-5 stars)
- Optional review text
- Display average rating on rider profile

#### 9. Rider Scheduling & Availability
**Effort:** Medium | **Impact:** Low

- Rider sets working hours
- Auto offline when outside schedule
- Shift management for multiple riders

#### 10. Rider Earnings & Payouts
**Effort:** High | **Impact:** Low

- Track delivery fees
- Calculate commission
- Generate payout reports
- Mark as paid

---

## 📊 Feature Completion Matrix

| Feature | Backend API | Database | Owner UI | Rider UI | Status |
|---------|------------|----------|----------|----------|--------|
| Create Rider | ✅ | ✅ | ❌ | N/A | 66% |
| List Riders | ✅ | ✅ | ⚠️ | N/A | 66% |
| Edit Rider | ✅ | ✅ | ❌ | N/A | 66% |
| Delete Rider | ✅ | ✅ | ❌ | N/A | 66% |
| Assign Rider | ✅ | ✅ | ✅ | N/A | 100% |
| Rider Login | ✅ | ✅ | N/A | ✅ | 100% |
| Rider Orders List | ✅ | ✅ | N/A | ✅ | 100% |
| Rider GPS Tracking | ✅ | ✅ | N/A | ✅ | 100% |
| Rider Update Status | ✅ | ✅ | N/A | ✅ | 100% |
| Customer Track Order | ✅ | ✅ | N/A | ⚠️ | 66% |
| GPS Map Display | ✅ | ✅ | ❌ | ❌ | 33% |
| WhatsApp Notification | ✅ | N/A | ⚠️ | N/A | 66% |
| Rider Ratings | ❌ | ⚠️ | ❌ | ❌ | 25% |
| Auto-assignment | ❌ | N/A | ❌ | N/A | 0% |
| Push Notifications | ❌ | ❌ | ❌ | ❌ | 0% |
| Earnings Tracking | ❌ | ❌ | ❌ | ❌ | 0% |

**Overall Completion:** ~65%

**Legend:**
- ✅ Fully implemented
- ⚠️ Partially implemented
- ❌ Not implemented
- N/A Not applicable

---

## 🔧 Technical Debt

### Security Issues
1. **Plain text passwords** - Rider passwords stored in plain text
   - Fix: Add bcrypt hashing
   - Priority: 🔴 CRITICAL

2. **No rate limiting** - API endpoints unprotected
   - Fix: Add rate limiting middleware
   - Priority: 🟡 HIGH

3. **Public rider endpoints** - Some endpoints bypass RLS
   - Review: Lines 1263-1497 in delivery.py
   - Priority: 🟡 HIGH

### Performance Issues
1. **No pagination** - Rider list loads all records
   - Fix: Add limit/offset to API
   - Priority: 🟢 MEDIUM

2. **Missing indexes** - Some GPS queries could be slow
   - Fix: Add composite indexes
   - Priority: 🟢 MEDIUM

### Code Quality
1. **Duplicate rider endpoints** - Both admin and public versions
   - Refactor: Consolidate to single endpoint
   - Priority: 🔵 LOW

2. **Missing error handling** - Some API calls lack try/catch
   - Fix: Add comprehensive error handling
   - Priority: 🟡 HIGH

---

## 📝 Summary

### What Works Well
- ✅ Complete backend API for all rider operations
- ✅ Robust database schema with GPS tracking
- ✅ Functional rider mobile app with GPS
- ✅ Order assignment system works
- ✅ Real-time location updates work

### Critical Gaps
- ❌ **No UI to create/manage riders** (owners must use Supabase/API)
- ❌ No map display for GPS tracking (data exists but not shown)
- ❌ Plain text password storage (security risk)

### Quick Wins (Easy to implement)
1. Add "Riders" tab to owner dashboard (reuse existing load function)
2. Display WhatsApp link after rider assignment
3. Add bcrypt password hashing

### Long-term Improvements
1. Build Google Maps tracking page
2. Implement auto-assignment algorithm
3. Add push notifications
4. Build rider analytics dashboard

---

**Report Complete** ✅
