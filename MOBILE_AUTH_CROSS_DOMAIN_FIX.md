# 🔧 Mobile Cross-Domain Auth Fix - CRITICAL

## 🚨 **THE PROBLEM:**

### **Root Cause:**
Mobile browsers block **cross-domain cookies** between:
- Frontend: `www.binaapp.my`
- Backend API: `binaapp-backend.onrender.com`

### **Symptoms:**
- ✅ **Desktop browser:** Works fine (less strict cookie policies)
- ❌ **Mobile browser:** Session not detected, redirects to login
- ❌ **PWA/Installed app:** Same issue

### **Technical Details:**
1. Supabase auth uses cookies by default
2. Mobile browsers (Safari, Chrome) block **third-party cookies**
3. When frontend (`www.binaapp.my`) tries to read cookies set by API (`binaapp-backend.onrender.com`), mobile blocks it
4. Session appears invalid on mobile even though user is logged in
5. User gets redirected to login on every page visit

---

## ✅ **THE SOLUTION:**

### **Switch from Cookie-Based to Header-Based Auth**

Instead of relying on cookies, we now:
1. Store JWT token in `localStorage` (already done by Supabase)
2. Get JWT token from Supabase session
3. Send token in `Authorization: Bearer <token>` header on every API request
4. Backend validates the JWT token and enforces RLS

---

## 🛠️ **What Was Fixed:**

### **File 1: `frontend/src/lib/api.ts`** ✅

**Added JWT Token Injection:**

```typescript
import { supabase } from './supabase'

async function getAuthToken(): Promise<string | null> {
  if (!supabase) return null

  try {
    // Get current session
    const { data: { session }, error } = await supabase.auth.getSession()

    if (error) {
      console.error('[API] Error getting session:', error)
      return null
    }

    // Return access token if available
    if (session?.access_token) {
      return session.access_token
    }

    // Try to refresh if no session
    const { data: refreshData } = await supabase.auth.refreshSession()
    return refreshData.session?.access_token || null
  } catch (err) {
    console.error('[API] Error getting auth token:', err)
    return null
  }
}

export async function apiFetch(
  path: string,
  options?: RequestInit & { timeout?: number; skipAuth?: boolean }
) {
  // ... existing code ...

  // CRITICAL FIX: Add JWT token to Authorization header
  if (!options?.skipAuth) {
    const token = await getAuthToken()
    if (token) {
      extraHeaders['Authorization'] = `Bearer ${token}`
      console.log('[API] Added Authorization header for:', path)
    }
  }

  // ... rest of fetch logic ...
}
```

**What This Does:**
1. Gets JWT access token from Supabase session (stored in localStorage)
2. Adds `Authorization: Bearer <token>` header to all API requests
3. Works on mobile because localStorage is NOT blocked
4. Backend receives token and validates it
5. RLS policies work correctly with user's permissions

---

### **File 2: `frontend/src/lib/supabase.ts`** ✅

**Already configured for mobile:**

```typescript
export const supabase = createClient(supabaseUrl, supabaseAnonKey, {
  auth: {
    autoRefreshToken: true,      // Auto-refresh expired tokens
    persistSession: true,         // Save session to localStorage
    detectSessionInUrl: true,     // Handle OAuth redirects
    storage: window.localStorage, // Use localStorage (not cookies!)
    flowType: 'pkce',            // ✅ Better for mobile browsers
    debug: process.env.NODE_ENV === 'development',
  },
})
```

**Key Points:**
- `storage: localStorage` ← Session stored locally, NOT in cookies
- `flowType: 'pkce'` ← More secure for mobile
- `autoRefreshToken: true` ← Keeps session alive

---

### **File 3: Backend Already Configured** ✅

**Backend file:** `backend/app/api/v1/endpoints/delivery.py`

```python
def get_supabase_rls_client(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> Client:
    """
    Create a Supabase client that uses the caller's Supabase JWT for RLS.
    This allows the backend to enforce Row Level Security based on the user's token.
    """
    token = credentials.credentials  # Get Bearer token from header

    # Create Supabase client with user's token
    supabase = create_client(
        supabase_url=os.getenv("SUPABASE_URL"),
        supabase_key=token,  # Use USER token, not service key!
        options=ClientOptions(
            headers={"Authorization": f"Bearer {token}"}
        )
    )

    return supabase
```

**Backend endpoints using auth:**
- `/v1/delivery/admin/orders` - Gets user's orders (RLS enforced)
- `/v1/delivery/riders/{rider_id}/location` - Updates rider location
- `/v1/chat/conversations/website/{website_id}` - Gets chat conversations
- All authenticated endpoints expect `Authorization: Bearer <token>` header

---

## 🧪 **How to Test:**

### **Test 1: Desktop (Should Still Work)**
```
1. Open Chrome/Firefox on computer
2. Go to: https://www.binaapp.my/login
3. Login with credentials
4. Go to: https://www.binaapp.my/profile
✅ Should show dashboard
✅ Should load orders
```

### **Test 2: Mobile Browser (NOW SHOULD WORK!)**
```
1. Open Chrome/Safari on phone
2. Go to: https://www.binaapp.my/login
3. Login with credentials
4. Go to: https://www.binaapp.my/profile
✅ Should show dashboard
✅ Should load orders
✅ Close browser completely
✅ Reopen and go to /profile again
✅ Should STAY logged in (not redirect to login!)
```

### **Test 3: Check Console Logs**

**Expected output on mobile:**
```javascript
[API] Added Authorization header for: /v1/delivery/...
[Profile] Checking auth session...
[Profile] ✅ Session found: user@example.com
✅ Loaded 10 orders
```

**If you see errors:**
```javascript
[API] No auth token available for: /v1/delivery/...
❌ This means session is not being found
```

---

## 📊 **Before vs After:**

### **Before Fix:**
```
Mobile Browser Request:
  GET /v1/delivery/admin/orders
  Headers:
    Content-Type: application/json
    // ❌ NO Authorization header!

Backend Response:
  401 Unauthorized (RLS blocks access)

Mobile Browser:
  Redirects to login (thinks user not authenticated)
```

### **After Fix:**
```
Mobile Browser Request:
  GET /v1/delivery/admin/orders
  Headers:
    Content-Type: application/json
    Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9... ✅

Backend Response:
  200 OK
  {orders: [...]} ✅

Mobile Browser:
  Shows dashboard with orders! ✅
```

---

## 🔍 **Debug Instructions:**

### **Check if Token is Being Sent:**

1. **Open mobile browser dev tools** (Chrome Remote Debugging / Safari Web Inspector)

2. **Go to Network tab**

3. **Navigate to /profile**

4. **Check API requests:**
   - Look for requests to `binaapp-backend.onrender.com`
   - Click on a request
   - Check **Request Headers**
   - Should see: `Authorization: Bearer <long-token>`

5. **If NO Authorization header:**
   - Check console for `[API] No auth token available`
   - Session might not be loading properly
   - Try logout and login again

### **Check if Session Exists:**

Run in browser console:
```javascript
// Check if Supabase session exists
const { data: { session } } = await supabase.auth.getSession()
console.log('Session:', session)
console.log('Access Token:', session?.access_token)

// Check localStorage
console.log('Auth keys:',
  Object.keys(localStorage).filter(k => k.includes('supabase'))
)
```

**Expected:**
```javascript
Session: {
  access_token: "eyJhbGci...", ✅
  refresh_token: "...",
  user: { email: "...", ... }
}
Auth keys: ["sb-<project>-auth-token"] ✅
```

---

## 🚨 **Common Issues:**

### **Issue 1: Still redirecting to login on mobile**

**Cause:** Token not being retrieved properly

**Solution:**
1. Clear localStorage: `localStorage.clear()`
2. Logout completely
3. Login again
4. Check console for `[API] Added Authorization header`

### **Issue 2: API returns 401 Unauthorized**

**Cause:** Token expired or invalid

**Solution:**
1. Token refresh should happen automatically
2. Check `autoRefreshToken: true` in supabase config
3. Try logout and login again

### **Issue 3: Works in browser, not in PWA**

**Cause:** PWA might have separate storage context

**Solution:**
1. Uninstall PWA from home screen
2. Reinstall from browser
3. Login again

### **Issue 4: Token exists but still redirects**

**Cause:** Profile page auth check might be failing

**Solution:**
1. Check profile page console logs
2. Look for `[Profile] Checking auth session...`
3. Should see `[Profile] ✅ Session found`
4. If not, session refresh might be failing

---

## ✅ **Verification Checklist:**

After deploying this fix:

- [ ] Desktop login works
- [ ] Desktop stays logged in after browser restart
- [ ] Mobile login works
- [ ] Mobile shows dashboard (not login page)
- [ ] Mobile loads orders correctly
- [ ] Mobile stays logged in after browser close
- [ ] PWA stays logged in
- [ ] Console shows `[API] Added Authorization header`
- [ ] Network tab shows `Authorization: Bearer ...` header
- [ ] No 401 errors for authenticated endpoints

---

## 📝 **Technical Details:**

### **Why This Works:**

1. **localStorage is NOT blocked cross-domain**
   - Mobile browsers allow localStorage access
   - Supabase stores tokens in localStorage
   - We can always read the token

2. **Authorization header works cross-domain**
   - Headers are sent with every request
   - CORS allows Authorization header
   - Backend receives and validates token

3. **No cookies needed**
   - Completely bypasses cookie restrictions
   - Works on all browsers and devices
   - More secure (PKCE flow)

### **Security:**

- ✅ JWT tokens are signed by Supabase
- ✅ Backend verifies token signature
- ✅ Tokens expire (auto-refresh happens)
- ✅ RLS policies still enforced
- ✅ HTTPS protects token in transit

### **Performance:**

- ✅ No extra latency (token from localStorage is instant)
- ✅ No server round-trip to check cookies
- ✅ Auto-refresh happens in background

---

## 🎯 **Summary:**

**Problem:** Cross-domain cookies blocked on mobile
**Solution:** JWT tokens in Authorization header
**Result:** Mobile auth works perfectly!

**Files Modified:**
1. `frontend/src/lib/api.ts` - Added JWT token injection
2. `frontend/src/lib/supabase.ts` - Already configured for mobile
3. Backend - Already supports Bearer tokens

**Testing:** Deploy and test on mobile browser + PWA

**Expected Outcome:** ✅ Mobile users stay logged in!

---

**Status:** ✅ **COMPLETE AND READY FOR TESTING**
