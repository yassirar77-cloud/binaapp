# 🛵 BinaApp Delivery System - Setup Guide

## Phase 1 MVP Implementation Complete! ✅

This guide will help you set up and run the BinaApp Delivery System.

---

## 📋 What's Been Built

### 1. Database Schema ✅
- **File:** `/backend/migrations/002_delivery_system.sql`
- **Tables Created:**
  - `delivery_zones` - Delivery coverage areas
  - `menu_categories` - Menu organization
  - `menu_items` - Food items with prices
  - `menu_item_options` - Add-ons, sizes, etc.
  - `delivery_orders` - Customer orders
  - `order_items` - Items in each order
  - `riders` - Delivery riders
  - `rider_locations` - Real-time tracking
  - `order_status_history` - Status change logs
  - `delivery_settings` - Business configuration

### 2. API Endpoints ✅
- **File:** `/backend/app/api/v1/endpoints/delivery.py`
- **Endpoints:**
  - `GET /v1/delivery/zones/{website_id}` - Get delivery zones
  - `POST /v1/delivery/check-coverage` - Check if address is covered
  - `GET /v1/delivery/menu/{website_id}` - Get menu with categories
  - `GET /v1/delivery/menu/{website_id}/item/{item_id}` - Get single item
  - `POST /v1/delivery/orders` - Create new order
  - `GET /v1/delivery/orders/{order_number}/track` - Track order
  - `GET /v1/delivery/health` - Health check

### 3. Customer Widget ✅
- **File:** `/frontend/public/widgets/delivery-widget.js`
- **Features:**
  - Floating order button
  - Menu browsing with images
  - Shopping cart
  - Checkout form
  - Bilingual (Malay/English)

### 4. Pydantic Models ✅
- **File:** `/backend/app/models/delivery_schemas.py`
- Complete type validation for all requests/responses

---

## 🚀 Setup Instructions

### Step 1: Run Database Migration

1. Go to your Supabase Dashboard: https://app.supabase.com
2. Select your project
3. Go to **SQL Editor**
4. Click **New Query**
5. Copy the entire contents of `/backend/migrations/002_delivery_system.sql`
6. Paste and click **RUN**

You should see: "Success. No rows returned"

### Step 2: Verify Tables Created

In Supabase, go to **Table Editor**. You should see these new tables:
- delivery_zones
- menu_categories
- menu_items
- menu_item_options
- delivery_orders
- order_items
- riders
- rider_locations
- order_status_history
- delivery_settings

### Step 3: Start the Backend Server

```bash
cd backend
python -m uvicorn app.api.server:app --reload --port 8000
```

### Step 4: Test the API

Visit: http://localhost:8000/docs

You'll see the new **Delivery System** endpoints in the Swagger UI.

### Step 5: Test Endpoints

#### 5.1 Get Zones (should return empty array first time)
```bash
GET http://localhost:8000/v1/delivery/zones/{your-website-id}
```

#### 5.2 Create a Test Delivery Zone

Use Supabase Table Editor or SQL:
```sql
INSERT INTO delivery_zones (website_id, zone_name, delivery_fee, minimum_order)
VALUES ('your-website-id', 'Zone 1 - Downtown', 5.00, 30.00);
```

#### 5.3 Create Test Menu Categories

```sql
INSERT INTO menu_categories (website_id, name, icon, sort_order)
VALUES
  ('your-website-id', 'Nasi', '🍚', 1),
  ('your-website-id', 'Lauk', '🍗', 2),
  ('your-website-id', 'Minuman', '🥤', 3);
```

#### 5.4 Create Test Menu Items

```sql
INSERT INTO menu_items (website_id, category_id, name, description, price, image_url)
VALUES
  ('your-website-id', 'category-id-here', 'Nasi Lemak', 'Nasi lemak dengan sambal, ikan bilis, telur', 8.50, 'https://images.unsplash.com/photo-1598514983318-2f64f8f4796c?w=400'),
  ('your-website-id', 'category-id-here', 'Ayam Goreng', 'Ayam goreng berempah', 12.00, 'https://images.unsplash.com/photo-1626082927389-6cd097cdc6ec?w=400');
```

#### 5.5 Test Order Creation

Use the Swagger UI at `/docs` or make a POST request:

```json
POST /v1/delivery/orders
{
  "website_id": "your-website-id",
  "customer_name": "Ahmad Abdullah",
  "customer_phone": "+60123456789",
  "delivery_address": "123 Jalan Merdeka, KL",
  "delivery_zone_id": "zone-id-here",
  "items": [
    {
      "menu_item_id": "item-id-here",
      "quantity": 2
    }
  ],
  "payment_method": "cod"
}
```

Response:
```json
{
  "id": "...",
  "order_number": "BNA-20241229-0001",
  "status": "pending",
  "total_amount": 26.00,
  ...
}
```

#### 5.6 Test Order Tracking

```bash
GET /v1/delivery/orders/BNA-20241229-0001/track
```

---

## 🌐 Using the Customer Widget

### Add to Any Website

Add this code to your HTML:

```html
<!-- Load Widget Script -->
<script src="https://binaapp.my/widgets/delivery-widget.js"></script>

<!-- Initialize Widget -->
<script>
  BinaAppDelivery.init({
    websiteId: 'your-website-id-here',
    apiUrl: 'https://api.binaapp.my/v1',
    primaryColor: '#ea580c',
    language: 'ms'  // 'ms' or 'en'
  });
</script>
```

### For Local Testing

```html
<script src="http://localhost:3000/widgets/delivery-widget.js"></script>
<script>
  BinaAppDelivery.init({
    websiteId: 'your-website-id-here',
    apiUrl: 'http://localhost:8000/v1',
    primaryColor: '#ea580c',
    language: 'ms'
  });
</script>
```

---

## 📊 Database Schema Overview

```
websites (existing)
  └── delivery_zones (1:many)
  └── menu_categories (1:many)
  └── menu_items (1:many)
      └── menu_item_options (1:many)
  └── delivery_orders (1:many)
      └── order_items (1:many)
      └── order_status_history (1:many)
      └── rider (many:1) → riders
          └── rider_locations (1:many)
  └── delivery_settings (1:1)
```

---

## 🔄 Order Status Flow

```
pending → confirmed → preparing → ready → picked_up → delivering → delivered → completed

Alternative paths:
- cancelled (at any stage)
- rejected (from pending)
```

---

## ✅ Phase 1 MVP Checklist

- [x] Database schema with all tables
- [x] Row Level Security (RLS) policies
- [x] Auto-generated order numbers (BNA-YYYYMMDD-XXXX)
- [x] Status change logging (triggers)
- [x] API endpoints for zones, menu, orders
- [x] Order creation with price calculation
- [x] Order tracking by order number
- [x] Customer widget with cart functionality
- [x] Bilingual support (Malay/English)

---

## 🎯 What's Next (Phase 2)

For Phase 2, we'll add:
- [ ] Real-time order updates (WebSocket)
- [ ] Rider management endpoints
- [ ] Live location tracking
- [ ] ETA calculation with Google Maps API
- [ ] WhatsApp notifications
- [ ] Business dashboard UI

---

## 🐛 Troubleshooting

### API Returns 500 Error
- Check Supabase credentials in `.env`
- Verify tables were created successfully
- Check backend logs for detailed errors

### Widget Not Loading
- Check browser console for errors
- Verify `websiteId` is correct
- Ensure backend API is running
- Check CORS settings

### Order Creation Fails
- Ensure delivery zone exists
- Check minimum order amount
- Verify menu items exist and are available
- Check request payload format

---

## 📞 Support

For issues or questions:
- Check `/docs` endpoint for API documentation
- Review Supabase logs in dashboard
- Check backend console logs

---

**Last Updated:** December 29, 2024
**Version:** 1.0.0 - Phase 1 MVP
**Status:** ✅ Ready for Testing
