# 🚀 Test Your Delivery System NOW

## Your Setup:
- **Website:** khulafa
- **Website ID:** `5d208c1d-70bb-46c6-9bf8-e9700b33736c`
- **Database:** ✅ All tables created
- **Test Data:** ✅ 4 zones, 5 categories, 16 menu items loaded

---

## 🎯 Quick Test (5 Minutes)

### Step 1: Start Backend Server

```bash
cd /home/user/binaapp/backend
uvicorn app.api.server:app --reload --port 8000
```

**Expected output:**
```
INFO:     Started server process
INFO:     Uvicorn running on http://127.0.0.1:8000
```

---

### Step 2: Open Swagger UI

Open browser: **http://localhost:8000/docs**

You should see **"Delivery System"** section with 7 endpoints.

---

### Step 3: Test Get Zones

In Swagger UI:
1. Find `GET /v1/delivery/zones/{website_id}`
2. Click "Try it out"
3. Enter website_id: `5d208c1d-70bb-46c6-9bf8-e9700b33736c`
4. Click "Execute"

**Expected Response:**
```json
{
  "zones": [
    {
      "zone_name": "Shah Alam Seksyen 7",
      "delivery_fee": 5.00,
      "minimum_order": 25.00
    },
    // ... 3 more zones
  ],
  "settings": {
    "minimum_order": 25.00,
    "accept_cod": true
  }
}
```

✅ **If you see zones** → API is working!

---

### Step 4: Test Get Menu

In Swagger UI:
1. Find `GET /v1/delivery/menu/{website_id}`
2. Click "Try it out"
3. Enter same website_id
4. Click "Execute"

**Expected Response:**
```json
{
  "categories": [
    {"name": "Nasi Kandar", "icon": "🍚"},
    {"name": "Lauk Ayam", "icon": "🍗"},
    // ... 3 more categories
  ],
  "items": [
    {
      "name": "Nasi Kandar Biasa",
      "price": 6.00,
      "category_id": "..."
    },
    // ... 15 more items
  ]
}
```

✅ **If you see 5 categories and 16 items** → Menu API working!

---

### Step 5: Create Test Order

In Swagger UI:
1. Find `POST /v1/delivery/orders`
2. Click "Try it out"
3. **Copy the zone_id from Step 3 response**
4. **Copy a menu item_id from Step 4 response**
5. Paste this JSON (update IDs):

```json
{
  "website_id": "5d208c1d-70bb-46c6-9bf8-e9700b33736c",
  "customer_name": "Ahmad Test",
  "customer_phone": "+60123456789",
  "delivery_address": "No 123, Jalan Test, Seksyen 7, Shah Alam",
  "delivery_notes": "Test order",
  "delivery_zone_id": "PASTE_ZONE_ID_HERE",
  "items": [
    {
      "menu_item_id": "PASTE_ITEM_ID_HERE",
      "quantity": 2
    }
  ],
  "payment_method": "cod"
}
```

6. Click "Execute"

**Expected Response:**
```json
{
  "order_number": "BNA-20241229-0001",
  "status": "pending",
  "total_amount": 17.00,
  "subtotal": 12.00,
  "delivery_fee": 5.00
}
```

✅ **If you get order_number** → Order creation working!

**COPY THE ORDER NUMBER!**

---

### Step 6: Track Order

In Swagger UI:
1. Find `GET /v1/delivery/orders/{order_number}/track`
2. Click "Try it out"
3. Paste your order number (e.g., `BNA-20241229-0001`)
4. Click "Execute"

**Expected Response:**
```json
{
  "order": {
    "order_number": "BNA-20241229-0001",
    "status": "pending",
    "customer_name": "Ahmad Test",
    "total_amount": 17.00
  },
  "items": [
    {
      "item_name": "Nasi Kandar Biasa",
      "quantity": 2,
      "total_price": 12.00
    }
  ],
  "status_history": [
    {
      "status": "pending",
      "notes": "Status changed from pending to pending"
    }
  ]
}
```

✅ **If you see order details** → Tracking working!

---

## 🎉 All Tests Passed?

If all 6 steps worked:

### ✅ **YOU HAVE A WORKING DELIVERY SYSTEM!**

Your system can now:
- ✅ Show delivery zones
- ✅ Display menu with categories
- ✅ Accept customer orders
- ✅ Auto-generate order numbers
- ✅ Track orders in real-time
- ✅ Log status changes

---

## 🔧 Troubleshooting

### Server won't start?
```bash
# Install dependencies
cd /home/user/binaapp/backend
pip install -r requirements.txt

# Try again
uvicorn app.api.server:app --reload --port 8000
```

### "Internal Server Error"?
Check backend console for errors. Usually means:
- Supabase credentials missing
- Database table doesn't exist
- Wrong website_id

### Can't see data?
Verify in Supabase SQL Editor:
```sql
SELECT COUNT(*) FROM delivery_zones WHERE website_id = '5d208c1d-70bb-46c6-9bf8-e9700b33736c';
-- Should return 4
```

---

## 📱 Next: Test Customer Widget

Once API tests pass, create this HTML file:

**test-widget.html:**
```html
<!DOCTYPE html>
<html>
<head>
    <title>Khulafa Delivery Test</title>
</head>
<body>
    <h1>Khulafa Restaurant</h1>
    <p>Click the floating button to order! →</p>

    <!-- Widget -->
    <script src="/home/user/binaapp/frontend/public/widgets/delivery-widget.js"></script>
    <script>
      BinaAppDelivery.init({
        websiteId: '5d208c1d-70bb-46c6-9bf8-e9700b33736c',
        apiUrl: 'http://localhost:8000/v1',
        primaryColor: '#ea580c',
        language: 'ms'
      });
    </script>
</body>
</html>
```

Open in browser → You'll see floating "Pesan Sekarang" button!

---

## ✅ Success Criteria

**Phase 1 MVP is complete when:**
- [x] Database tables created ✅
- [x] Test data loaded ✅
- [x] API server starts ✅
- [ ] GET /zones returns 4 zones
- [ ] GET /menu returns 16 items
- [ ] POST /orders creates order
- [ ] GET /track shows order details
- [ ] Widget button appears
- [ ] Can place order via widget

---

## 🎯 Summary

**What to do NOW:**
1. Start backend server
2. Open http://localhost:8000/docs
3. Run the 6 API tests above
4. Take screenshots
5. Report results

**Time needed:** 5-10 minutes

**Files to check:**
- `PHASE_1_COMPLETE.md` - Full documentation
- `backend/test_delivery_api.py` - Automated tests
- `DELIVERY_SYSTEM_QUICKSTART.md` - Setup guide

---

Ready? **Start the server and let's test!** 🚀
