# Profile Page Authentication Issue - Diagnosis

## Problem
When users click "Profil" link, they are redirected to login page even though they are logged in.

## Root Cause Analysis

### Issue #1: Missing Environment Variables (CRITICAL)

**File:** `frontend/src/lib/supabase.ts`

```typescript
const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY

export const supabase =
  supabaseUrl && supabaseAnonKey
    ? createClient(supabaseUrl, supabaseAnonKey)
    : null  // ⚠️ Returns NULL if env vars not set!
```

**Profile Page Check:** `frontend/src/app/profile/page.tsx` (Line 117-120)

```typescript
useEffect(() => {
  const check = async () => {
    if (!supabase) {  // ⚠️ If supabase is null
      setState('noauth');  // Sets state to 'noauth'
      return;
    }
    // ... rest of auth check
  }
}, []);
```

**Result When state='noauth':** (Line 483-492)

```typescript
if (state === 'noauth') return (
  <div>
    <h1>Sila Log Masuk</h1>
    <p>Anda perlu log masuk untuk melihat profil</p>
    <button onClick={() => router.push('/login')}>Log Masuk</button>
  </div>
);
```

### The Problem Flow:

1. ❌ Vercel environment variables NOT SET:
   - `NEXT_PUBLIC_SUPABASE_URL` = undefined
   - `NEXT_PUBLIC_SUPABASE_ANON_KEY` = undefined

2. ❌ Supabase client = `null` (because env vars missing)

3. ❌ Profile page checks `if (!supabase)` → TRUE

4. ❌ Sets state to 'noauth'

5. ❌ Shows "Sila Log Masuk" screen

6. ✅ User clicks "Log Masuk" button

7. ❌ Redirects to /login

**Even though user IS logged in!**

## Required Environment Variables

### Frontend (Vercel)
```bash
NEXT_PUBLIC_SUPABASE_URL=https://xxxxxxxxxxxxx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
NEXT_PUBLIC_API_URL=https://binaapp-backend.onrender.com
NEXT_PUBLIC_STRIPE_PUBLIC_KEY=pk_test_...
NEXT_PUBLIC_GOOGLE_MAPS_API_KEY=AIza...
```

### Backend (Render)
```bash
SUPABASE_URL=https://xxxxxxxxxxxxx.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
DATABASE_URL=postgresql://...
JWT_SECRET_KEY=your-secret-key
QWEN_API_KEY=...
DEEPSEEK_API_KEY=...
```

## How to Fix

### Step 1: Get Your Supabase Credentials

1. Go to: https://app.supabase.com
2. Select your project
3. Go to: **Settings** → **API**
4. Copy:
   - **Project URL** (this is `NEXT_PUBLIC_SUPABASE_URL`)
   - **anon/public key** (this is `NEXT_PUBLIC_SUPABASE_ANON_KEY`)

### Step 2: Add Environment Variables to Vercel

1. Go to: https://vercel.com/dashboard
2. Select your **binaapp** project
3. Go to: **Settings** → **Environment Variables**
4. Add these variables:

```
NEXT_PUBLIC_SUPABASE_URL = https://xxxxxxxxxxxxx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY = eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

5. Click **Save**

### Step 3: Redeploy

After adding environment variables:
1. Go to **Deployments** tab
2. Click on latest deployment
3. Click **⋮** (three dots)
4. Click **Redeploy**

OR

1. Push any commit to trigger new deployment
2. Environment variables will be included

### Step 4: Verify

After redeployment:
1. Go to https://www.binaapp.my/profile
2. You should see your profile (not login screen)
3. All tabs should work

## Quick Diagnostic Script

Run this in browser console on https://www.binaapp.my:

```javascript
console.log('=== Environment Variables Check ===');
console.log('NEXT_PUBLIC_SUPABASE_URL:', process.env.NEXT_PUBLIC_SUPABASE_URL || '❌ NOT SET');
console.log('NEXT_PUBLIC_SUPABASE_ANON_KEY:', process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ? '✅ SET' : '❌ NOT SET');
console.log('NEXT_PUBLIC_API_URL:', process.env.NEXT_PUBLIC_API_URL || '❌ NOT SET (using default)');

// Check if supabase client exists
import('@/lib/supabase').then(({ supabase }) => {
  console.log('Supabase client:', supabase ? '✅ Initialized' : '❌ NULL');
});
```

Expected output:
```
✅ NEXT_PUBLIC_SUPABASE_URL: https://xxxxx.supabase.co
✅ NEXT_PUBLIC_SUPABASE_ANON_KEY: SET
✅ NEXT_PUBLIC_API_URL: https://binaapp-backend.onrender.com
✅ Supabase client: Initialized
```

If you see `❌ NOT SET`, that's the problem!

## Additional Fixes Applied

### Fix #1: Better Error Messaging

Updated profile page to show clear error when Supabase is not configured:

```typescript
if (!supabase) {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
      <div className="bg-white p-8 rounded-xl shadow text-center max-w-md w-full">
        <div className="text-5xl mb-4">⚠️</div>
        <h1 className="text-xl font-bold mb-2">Configuration Error</h1>
        <p className="text-gray-600 mb-6">
          Supabase tidak dikonfigurasi. Sila hubungi admin untuk set environment variables.
        </p>
        <div className="text-xs text-left bg-gray-100 p-3 rounded">
          <p className="font-mono text-red-600">Missing:</p>
          <p className="font-mono">NEXT_PUBLIC_SUPABASE_URL</p>
          <p className="font-mono">NEXT_PUBLIC_SUPABASE_ANON_KEY</p>
        </div>
      </div>
    </div>
  );
}
```

### Fix #2: Debug Logging

Added console logging to help diagnose issues:

```typescript
useEffect(() => {
  const check = async () => {
    console.log('[Profile] Checking authentication...');
    console.log('[Profile] Supabase client:', supabase ? 'initialized' : 'NULL');

    if (!supabase) {
      console.error('[Profile] Supabase not initialized - missing environment variables');
      setState('noauth');
      return;
    }

    try {
      const { data: { user } } = await supabase.auth.getUser();
      console.log('[Profile] User:', user ? user.email : 'not logged in');
      // ... rest of logic
    } catch (error) {
      console.error('[Profile] Auth check failed:', error);
    }
  };
  check();
}, []);
```

## Summary

**The issue is NOT a code bug - it's a configuration issue.**

✅ Code is correct
❌ Environment variables are missing in Vercel

**Fix:** Add Supabase environment variables to Vercel and redeploy.

Once environment variables are set, the profile page will work perfectly!
