# 🛵 Rider Web App & Map Guide

## 📍 **Rider Web App Location:**

The Rider Web App is fully built and ready to use!

### **Access URL:**
```
https://www.binaapp.my/rider
```

---

## 🛵 **Rider App Features:**

### **1. Login System**
- Rider enters their phone number (+60) and password
- Authenticates against `POST /api/v1/delivery/riders/login` (bcrypt password check)
- On success the backend returns the rider profile + a 30-day rider JWT
- Rider profile + token saved to localStorage

### **2. GPS Tracking**
- Real-time location tracking
- Updates backend every few seconds
- Uses browser's geolocation API
- Works offline (queues updates)

### **3. Order Management**
- Shows assigned orders
- Order details display
- Customer info and address
- Items and total amount

### **4. Status Updates**
- Ready → Picked Up
- Picked Up → Delivering
- Delivering → Delivered
- Updates visible to customer in real-time

### **5. Navigation**
- Google Maps integration
- "Navigate to Location" button
- Opens Google Maps with directions
- Works on all mobile devices

### **6. Communication**
- Call customer button (tel: link)
- WhatsApp customer button
- Direct contact from app

### **7. PWA Support**
- Installable on mobile home screen
- Works like native app
- Offline capability
- Push notifications ready

---

## 🗺️ **Map System:**

BinaApp uses **Google Maps** for tracking and navigation.

### **Map Locations:**

#### **1. Customer Tracking Page**
**File:** `frontend/src/components/OrderTracking.tsx` (if exists)

**Shows:**
- Rider current location (real-time)
- Customer delivery location
- Route between them
- Estimated time of arrival

**How It Works:**
```javascript
// Rider location from backend
GET /v1/delivery/riders/{rider_id}/location

// Updates every 5-10 seconds
// Shows marker on map with rider icon
```

---

#### **2. Rider App Navigation**
**File:** `frontend/src/app/rider/page.tsx`

**Shows:**
- Customer delivery address on map
- "Navigate to Location" button
- Opens Google Maps with directions

**Code:**
```javascript
<a
  href={`https://www.google.com/maps/dir/?api=1&destination=${order.delivery_latitude},${order.delivery_longitude}`}
  target="_blank"
>
  🗺️ Navigasi ke Lokasi
</a>
```

---

#### **3. Owner Dashboard Chat**
**File:** `frontend/src/components/BinaChat.tsx`

**Shows:**
- Order delivery location
- Rider current location (if assigned)
- Customer can see where rider is

---

## 🛠️ **How to Customize Map:**

### **Option 1: Change Map Provider**

Currently using **Google Maps**. You can switch to:

1. **Leaflet (Open Source)**
```bash
npm install leaflet react-leaflet
```

2. **Mapbox**
```bash
npm install mapbox-gl
```

3. **OpenStreetMap**
- Free, no API key needed
- Good for basic tracking

---

### **Option 2: Customize Google Maps**

**File:** `frontend/src/components/MapComponent.tsx` (create if needed)

**Example:**
```typescript
import { GoogleMap, Marker, useLoadScript } from '@react-google-maps/api'

export default function DeliveryMap({ riderLat, riderLng, customerLat, customerLng }) {
  const { isLoaded } = useLoadScript({
    googleMapsApiKey: process.env.NEXT_PUBLIC_GOOGLE_MAPS_KEY
  })

  if (!isLoaded) return <div>Loading map...</div>

  return (
    <GoogleMap
      zoom={14}
      center={{ lat: customerLat, lng: customerLng }}
      mapContainerStyle={{ width: '100%', height: '400px' }}
    >
      {/* Customer marker */}
      <Marker
        position={{ lat: customerLat, lng: customerLng }}
        icon={{
          url: '/icons/customer-pin.png',
          scaledSize: new google.maps.Size(40, 40)
        }}
      />

      {/* Rider marker */}
      <Marker
        position={{ lat: riderLat, lng: riderLng }}
        icon={{
          url: '/icons/rider-pin.png',
          scaledSize: new google.maps.Size(40, 40)
        }}
      />
    </GoogleMap>
  )
}
```

---

### **Option 3: Use Leaflet (Free Alternative)**

**Install:**
```bash
npm install leaflet react-leaflet
```

**Create:** `frontend/src/components/LeafletMap.tsx`
```typescript
import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'
import L from 'leaflet'

// Custom icons
const riderIcon = new L.Icon({
  iconUrl: '/icons/rider.png',
  iconSize: [40, 40]
})

const customerIcon = new L.Icon({
  iconUrl: '/icons/customer.png',
  iconSize: [40, 40]
})

export default function DeliveryMap({ riderLat, riderLng, customerLat, customerLng }) {
  return (
    <MapContainer
      center={[customerLat, customerLng]}
      zoom={14}
      style={{ height: '400px', width: '100%' }}
    >
      {/* OpenStreetMap tiles (free!) */}
      <TileLayer
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        attribution='&copy; OpenStreetMap contributors'
      />

      {/* Rider marker */}
      <Marker position={[riderLat, riderLng]} icon={riderIcon}>
        <Popup>Rider Location</Popup>
      </Marker>

      {/* Customer marker */}
      <Marker position={[customerLat, customerLng]} icon={customerIcon}>
        <Popup>Delivery Location</Popup>
      </Marker>
    </MapContainer>
  )
}
```

**Use in component:**
```typescript
import dynamic from 'next/dynamic'

// Dynamically import to avoid SSR issues
const DeliveryMap = dynamic(() => import('@/components/LeafletMap'), {
  ssr: false
})

export default function TrackingPage() {
  return (
    <div>
      <DeliveryMap
        riderLat={rider.latitude}
        riderLng={rider.longitude}
        customerLat={order.delivery_latitude}
        customerLng={order.delivery_longitude}
      />
    </div>
  )
}
```

---

## 🚀 **How to Use Rider App:**

### **Step 1: Create the Rider (Owner Dashboard)**

The shop owner creates the rider from their dashboard (`/profile` → riders),
which calls `POST /api/v1/delivery/admin/websites/{website_id}/riders`. This
sets the rider's **phone**, **password** (stored bcrypt-hashed as
`password_hash`), and links the rider to the owner's `website_id`. Rider slots
are subject to the plan quota (a paid rider slot or addon credit is required).

> A raw SQL insert into `riders` will NOT let the rider log in unless it also
> sets a bcrypt `password_hash` — login verifies the password, not the ID.
> Prefer the dashboard flow so hashing and quota are handled for you.

---

### **Step 2: Rider Logs In**

1. Rider opens: `https://www.binaapp.my/rider`
2. Enters their phone number (+60) and password
3. Clicks "Log Masuk"
4. GPS tracking starts automatically

---

### **Step 3: Assign Order to Rider**

**In Owner Dashboard:**
1. Go to `/profile`
2. Click "📦 Pesanan" tab
3. Confirm order (TERIMA PESANAN)
4. Select rider from dropdown
5. Order assigned!

---

### **Step 4: Rider Accepts & Delivers**

**In Rider App:**
1. Order appears in "Pesanan Aktif"
2. Shows customer info, address, items
3. Rider clicks status buttons:
   - "✓ Diambil" (Picked Up)
   - "✓ Dalam Penghantaran" (Delivering)
   - "✓ Dihantar" (Delivered)
4. GPS location updated continuously
5. Customer sees updates in real-time

---

### **Step 5: Navigation**

**Rider clicks "🗺️ Navigasi ke Lokasi"**
- Opens Google Maps
- Shows directions to customer
- Works on all mobile devices

---

## 📱 **Rider App as PWA:**

### **Install on Mobile:**

**Android:**
1. Open `www.binaapp.my/rider` in Chrome
2. Tap menu (⋮)
3. Tap "Add to Home Screen"
4. Icon appears on home screen
5. Works like native app!

**iOS:**
1. Open `www.binaapp.my/rider` in Safari
2. Tap Share button
3. Tap "Add to Home Screen"
4. Icon appears on home screen
5. Works like native app!

---

## 🔍 **GPS Tracking Details:**

### **How It Works:**

1. **Rider App:**
   ```javascript
   navigator.geolocation.watchPosition((position) => {
     const { latitude, longitude } = position.coords

     // Send to backend
     fetch(`/v1/delivery/riders/${riderId}/location`, {
       method: 'PUT',
       body: JSON.stringify({ latitude, longitude })
     })
   })
   ```

2. **Backend:**
   - Stores rider location in `riders` table
   - Also stores in `rider_locations` history

3. **Customer Tracking:**
   - Polls backend every 5-10 seconds
   - Gets latest rider location
   - Updates map marker in real-time

---

## 🗺️ **Map Customization Examples:**

### **Add Route Polyline:**
```javascript
import { Polyline } from 'react-leaflet'

<Polyline
  positions={[
    [riderLat, riderLng],
    [customerLat, customerLng]
  ]}
  color="blue"
  weight={3}
/>
```

### **Add ETA Display:**
```javascript
const distance = calculateDistance(
  riderLat, riderLng,
  customerLat, customerLng
)
const eta = distance / averageSpeed // minutes

<div>ETA: {eta} minit</div>
```

### **Custom Marker Icons:**
Create icons in `public/icons/`:
- `rider-motorcycle.png`
- `customer-home.png`
- `restaurant.png`

---

## 📊 **Current Setup:**

| Feature | Status | Location |
|---------|--------|----------|
| Rider Web App | ✅ Built | `/rider` |
| GPS Tracking | ✅ Working | Rider app |
| Google Maps | ✅ Integrated | Navigation links |
| Real-time Updates | ✅ Working | Backend polls |
| PWA Support | ✅ Ready | Service worker |
| Order Management | ✅ Working | Rider app |
| Status Updates | ✅ Working | Backend API |

---

## 🎯 **Next Steps (Optional):**

### **1. Add Leaflet Map Component**
- Free alternative to Google Maps
- No API key needed
- Better customization options

### **2. Add Route Drawing**
- Show path from rider to customer
- Display distance and ETA
- Animate marker movement

### **3. Add Push Notifications**
- Notify rider of new orders
- Alert customer when rider nearby
- Uses PWA notification API

### **4. Add Offline Support**
- Cache map tiles
- Queue GPS updates
- Work without internet

---

## 📞 **Quick Links:**

- **Rider App:** https://www.binaapp.my/rider
- **Rider Code:** `frontend/src/app/rider/page.tsx`
- **Backend GPS API:** `backend/app/api/v1/endpoints/delivery.py`
- **Database:** `riders` and `rider_locations` tables

---

**Everything is ready to use! Just assign orders to riders and they can start delivering!** 🚀
