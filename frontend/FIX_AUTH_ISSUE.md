# 🔧 Fix: Invalid Refresh Token Error

## 🔴 The Problem

You're seeing this error in browser console:
```
AuthApiError: Invalid Refresh Token: Refresh Token Not Found
wjaztxkbaeqjabybxhct.supabase.co/auth/v1/token?grant_type=refresh_token
Failed to load resource: the server responded with a status of 400 ()
```

**What This Means:**
- Your authentication session is broken
- The refresh token has expired or is invalid
- Supabase can't automatically refresh your session
- You get logged out and redirected to login page
- Orders can't load because you're not authenticated

---

## 🚀 IMMEDIATE FIX (Do This Now!)

### Step 1: Clear Browser Storage

**Option A: Use Browser Console**
1. Open www.binaapp.my
2. Press F12 to open Developer Tools
3. Go to "Console" tab
4. Copy and paste this:

```javascript
// Clear all auth tokens and storage
localStorage.clear()
sessionStorage.clear()

// Clear Supabase-specific keys
Object.keys(localStorage).forEach(key => {
  if (key.includes('supabase')) {
    localStorage.removeItem(key)
  }
})

console.log('✅ All storage cleared!')
console.log('Next: Close this tab and log in fresh')
```

5. Press Enter
6. Close ALL BinaApp tabs
7. Open new tab and go to www.binaapp.my/login

**Option B: Use Browser Settings**
1. Chrome: Settings → Privacy → Clear browsing data
2. Select "Cookies and other site data"
3. Select "Cached images and files"
4. Time range: "Last 24 hours"
5. Click "Clear data"

### Step 2: Log Out Completely
1. If you can access the profile page, click "Log Keluar"
2. Close all BinaApp browser tabs
3. Clear browser cache (Ctrl+Shift+Delete)

### Step 3: Log In Fresh
1. Go to https://www.binaapp.my/login
2. Enter your credentials
3. Click login
4. This creates NEW valid tokens
5. Go to https://www.binaapp.my/profile
6. ✅ Should work now!

---

## 🔍 Diagnostic: Check Auth Status

Run this in browser console to see your current auth status:

```javascript
// Check if Supabase client exists
console.log('Supabase client:', window.supabase ? '✅ Exists' : '❌ Missing')

// Check localStorage for auth tokens
const authKeys = Object.keys(localStorage).filter(k => k.includes('supabase'))
console.log('Auth keys in storage:', authKeys.length)
authKeys.forEach(key => {
  const value = localStorage.getItem(key)
  console.log(`- ${key}:`, value ? value.substring(0, 50) + '...' : 'empty')
})

// Try to get current user
if (window.supabase) {
  supabase.auth.getUser().then(({ data, error }) => {
    if (error) {
      console.error('❌ Auth error:', error.message)
      console.log('Solution: Clear storage and log in again')
    } else if (data.user) {
      console.log('✅ User authenticated:', data.user.email)
    } else {
      console.log('⚠️  No user - need to log in')
    }
  })
}
```

---

## 🛠️ What We Fixed in the Code

### 1. Better Error Handling for Auth Failures
```typescript
// Before: No error handling
const { data: { user } } = await supabase.auth.getUser()

// After: Handle auth errors
const { data: { user }, error: authError } = await supabase.auth.getUser()

if (authError) {
  console.error('Auth error:', authError)
  await supabase.auth.signOut()  // Clear stale tokens
  router.push('/login')
  return
}
```

### 2. Auth Error Detection in API Calls
```typescript
// Detect auth errors when loading orders
if (error) {
  console.error('Error loading orders:', error)
  // Check if it's an auth/token error
  if (error.message?.includes('JWT') || error.message?.includes('token')) {
    console.error('Auth token expired, redirecting to login...')
    await supabase.auth.signOut()
    router.push('/login')
    return
  }
}
```

### 3. Better Supabase Client Configuration
```typescript
// Added auto token refresh and session persistence
export const supabase = createClient(supabaseUrl, supabaseAnonKey, {
  auth: {
    autoRefreshToken: true,      // Auto-refresh tokens before expiry
    persistSession: true,         // Save session in localStorage
    detectSessionInUrl: true,     // Handle OAuth redirects
    storage: window.localStorage, // Where to store tokens
  },
})
```

---

## 🔄 How Token Refresh Works

**Normal Flow:**
```
User logs in
  ↓
Gets Access Token (expires in 1 hour)
Gets Refresh Token (expires in 30 days)
  ↓
After 55 minutes, Supabase auto-refreshes
  ↓
New Access Token issued
  ↓
Session continues seamlessly
```

**When It Breaks:**
```
User logs in
  ↓
Gets tokens
  ↓
Refresh token gets corrupted/expired
  ↓
Auto-refresh fails with 400 error
  ↓
❌ "Invalid Refresh Token" error
  ↓
User logged out
```

**Why Tokens Break:**
- User cleared cookies but not localStorage (partial clear)
- Refresh token expired (if not used for 30 days)
- Supabase auth settings changed
- Multiple tabs with different sessions
- Browser extensions interfering

---

## 📊 Check Supabase Auth Settings

Go to Supabase Dashboard → Authentication → Settings:

### 1. JWT Expiry (Should be reasonable)
- Access Token: 3600 seconds (1 hour) ✅
- Refresh Token: 2592000 seconds (30 days) ✅

### 2. Enable Auto Refresh
- Should be ON ✅

### 3. Site URL
- Must include: https://www.binaapp.my ✅
- Must include: http://localhost:3000 (for dev) ✅

### 4. Redirect URLs
- Add: https://www.binaapp.my/** ✅

---

## 🆘 Still Not Working?

### Scenario 1: Error Persists After Fresh Login
**Solution:** Check Supabase Auth settings above

### Scenario 2: Works But Logs Out After Few Minutes
**Solution:** Check JWT expiry settings in Supabase

### Scenario 3: Only Happens in Production
**Solution:**
1. Verify environment variables in Vercel:
   - `NEXT_PUBLIC_SUPABASE_URL`
   - `NEXT_PUBLIC_SUPABASE_ANON_KEY`
2. Make sure they match Supabase dashboard values

### Scenario 4: Multiple Tabs Issue
**Solution:**
- Close all BinaApp tabs
- Open only ONE tab
- Log in
- Should sync across tabs now

---

## ✅ Success Checklist

After the fix:
- [ ] No "Invalid Refresh Token" error in console
- [ ] Can access profile page without redirect
- [ ] Can see orders in "📦 Pesanan" tab
- [ ] Session persists across page refreshes
- [ ] Can stay logged in for extended period
- [ ] Multiple tabs work correctly

---

## 🔐 Best Practices Going Forward

1. **Don't Partially Clear Storage**
   - If clearing cookies, clear localStorage too
   - Use "Clear all data" option

2. **Regular Login**
   - Log in at least once every 30 days
   - Keeps refresh token valid

3. **One Session Per Browser**
   - Avoid logging in multiple accounts in same browser
   - Use incognito for testing

4. **Check Console Regularly**
   - Press F12 and check for auth errors
   - Address them before they escalate

---

## 📝 Files Modified

To fix this auth issue:

1. `frontend/src/app/profile/page.tsx`
   - Added error handling for auth failures
   - Added JWT error detection in loadOrders
   - Auto-signs out on auth errors

2. `frontend/src/lib/supabase.ts`
   - Added auth configuration options
   - Enabled autoRefreshToken
   - Enabled persistSession
   - Configured localStorage

---

## 🎉 After Fix is Deployed

1. **Clear your browser storage** (use Step 1 above)
2. **Log in fresh**
3. **Orders should load** in profile page
4. **Session should persist** without logout issues
5. **No more 400 errors** in console

The auth system will now:
- ✅ Auto-refresh tokens before expiry
- ✅ Handle expired tokens gracefully
- ✅ Redirect to login on auth errors
- ✅ Clear stale tokens automatically
- ✅ Persist session across browser restarts

---

## 🔗 Related Issues

If orders still don't show AFTER fixing auth:
1. Run backend diagnostic: `DIAGNOSE_ORDERS_ISSUE.sql`
2. Check RLS policies: `006_fix_owner_orders_access.sql`
3. Verify tables exist: `VERIFY_BACKEND_SETUP.sql`

But fix the AUTH ISSUE FIRST before checking backend!
