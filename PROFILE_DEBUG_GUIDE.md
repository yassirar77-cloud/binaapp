# Profile Page Debug Guide

## Current Status
Profile page at https://www.binaapp.my/profile

## Common Issues & Fixes

### Issue 1: "Sila Log Masuk" (Not Authenticated)
**Fixed:** ✅ Authentication now uses consistent Supabase client

### Issue 2: Backend API Calls Failing

**Symptoms:**
- Orders tab shows loading forever
- Riders section shows errors
- Menu items don't load

**Root Cause:**
Backend on Render is not responding

**Check:**
```bash
# Test if backend is up
curl https://binaapp-backend.onrender.com/health

# Should return:
# {"status": "ok", "service": "BinaApp API"}
```

**Fix:**
1. Go to Render Dashboard
2. Check "binaapp-backend" service status
3. Check logs for errors
4. Verify environment variables are set:
   - SUPABASE_URL
   - SUPABASE_ANON_KEY
   - SUPABASE_SERVICE_ROLE_KEY
   - DATABASE_URL
   - JWT_SECRET_KEY

### Issue 3: Frontend Environment Variables Missing

**Check Vercel Environment Variables:**
```
NEXT_PUBLIC_API_URL=https://binaapp-backend.onrender.com
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_anon_key
```

**How to Set:**
1. Go to Vercel Dashboard
2. Select "binaapp" project
3. Settings → Environment Variables
4. Add missing variables
5. Redeploy

### Issue 4: CORS Errors

**Symptoms:**
- Console shows "CORS policy" errors
- API calls blocked by browser

**Fix:**
Backend already has CORS configured for all origins.
If still failing, check browser console for specific error.

## Quick Diagnostic Script

Run this in browser console on profile page:

```javascript
// Test 1: Check if authenticated
console.log("=== Authentication Test ===");
const { supabase } = await import('@/lib/supabase');
const { data: { user } } = await supabase.auth.getUser();
console.log("User:", user ? "✅ Logged in" : "❌ Not logged in");

// Test 2: Check API connection
console.log("\n=== API Connection Test ===");
try {
  const response = await fetch('https://binaapp-backend.onrender.com/health');
  const data = await response.json();
  console.log("Backend:", data.status === 'ok' ? "✅ Online" : "❌ Offline");
} catch (e) {
  console.log("Backend:", "❌ Not responding");
  console.error(e);
}

// Test 3: Check environment variables
console.log("\n=== Environment Variables ===");
console.log("NEXT_PUBLIC_API_URL:", process.env.NEXT_PUBLIC_API_URL || "❌ Not set (using default)");
console.log("NEXT_PUBLIC_SUPABASE_URL:", process.env.NEXT_PUBLIC_SUPABASE_URL ? "✅ Set" : "❌ Not set");
console.log("NEXT_PUBLIC_SUPABASE_ANON_KEY:", process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ? "✅ Set" : "❌ Not set");

// Test 4: Check if website exists
console.log("\n=== Website Check ===");
if (user) {
  const { data: websites } = await supabase
    .from('websites')
    .select('id, business_name, subdomain')
    .eq('user_id', user.id);
  console.log("Websites:", websites?.length || 0);
  console.log(websites);
}
```

## Expected Behavior

### Profile Tab
- ✅ Shows user email (read-only)
- ✅ Shows/allows editing: Name, Business Name, Phone
- ✅ "Simpan" button saves changes
- ✅ "Kembali" button goes to /my-projects
- ✅ "Log Keluar" button logs out

### Pesanan (Orders) Tab
- ✅ Shows delivery orders for user's websites
- ✅ Can update order status
- ✅ Can assign riders to orders
- ✅ Shows rider management section
- ✅ Can add new riders

### Menu Tab
- ✅ Shows menu items for user's website
- ✅ Can add/edit/delete menu items
- ✅ Can toggle item availability
- ✅ Dynamic categories based on business type

## Priority Fixes

1. **First**: Fix Render backend (see backend section above)
2. **Second**: Verify Vercel environment variables
3. **Third**: Test profile page functionality

## Contact for Help

If issues persist, provide:
1. Screenshot of profile page
2. Browser console errors (F12 → Console tab)
3. Network tab showing failed requests (F12 → Network tab)
4. Which tab is not working (Profile/Pesanan/Menu)
