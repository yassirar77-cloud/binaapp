# 🔧 Fix: Orders Not Showing in Profile Dashboard

## 🎯 Problem
You see the profile page with "Website Saya" tab working, but the "📦 Pesanan" (Orders) tab is missing or shows no orders.

## 🔍 Root Causes

### Most Common Issues:
1. **❌ RLS Policies Too Restrictive** - Database blocking owners from seeing their orders
2. **❌ No Orders in Database** - No orders have been created yet
3. **❌ Tables Not Created** - Delivery system tables missing
4. **❌ Missing Permissions** - Supabase permissions not granted
5. **❌ Frontend Not Deployed** - Latest code not deployed to Vercel

---

## 🚀 **STEP-BY-STEP FIX**

### Step 1: Verify Tables Exist
Run this in **Supabase SQL Editor**:

```sql
-- Check if delivery tables exist
SELECT tablename FROM pg_tables
WHERE schemaname = 'public'
AND tablename IN ('delivery_orders', 'riders', 'order_items')
ORDER BY tablename;
```

**Expected output:** Should show 3 tables

**If tables are missing:**
1. Go to `/home/user/binaapp/backend/migrations/`
2. Run `002_delivery_system.sql` in Supabase SQL Editor

---

### Step 2: Run Diagnostic Script
Run this file in **Supabase SQL Editor**:

📁 **File:** `/home/user/binaapp/backend/migrations/DIAGNOSE_ORDERS_ISSUE.sql`

This will tell you exactly what's wrong:
- ✅ Do you have websites?
- ✅ Are there any orders?
- ✅ Can you see orders via RLS?
- ✅ Are there riders?

---

### Step 3: Fix RLS Policies
Run this file in **Supabase SQL Editor**:

📁 **File:** `/home/user/binaapp/backend/migrations/006_fix_owner_orders_access.sql`

This fixes:
- ✅ Owners can VIEW their website's orders
- ✅ Owners can UPDATE order status
- ✅ Owners can VIEW and MANAGE riders
- ✅ Customers can still place orders

---

### Step 4: Verify Backend Setup
Run this file in **Supabase SQL Editor**:

📁 **File:** `/home/user/binaapp/backend/migrations/VERIFY_BACKEND_SETUP.sql`

This comprehensive check shows:
- ✅ All tables exist
- ✅ RLS is enabled
- ✅ Permissions are correct
- ✅ Policies are in place
- ✅ Sample data

Look for ❌ or ⚠️ symbols and fix those issues.

---

### Step 5: Add Test Data (If No Orders)
If the diagnostic shows you have NO orders, create test data:

📁 **File:** `/home/user/binaapp/backend/migrations/003_test_data.sql`

**Before running:**
1. Find your website ID:
   ```sql
   SELECT id, name FROM websites WHERE user_id = auth.uid();
   ```
2. Replace `YOUR_WEBSITE_ID_HERE` in the file with your actual website ID
3. Run the modified SQL

---

### Step 6: Deploy Frontend to Vercel

The frontend code with Orders tab is on branch: `claude/fix-profile-auth-bug-DUS18`

**Option A: Deploy via Vercel Dashboard**
1. Go to https://vercel.com/dashboard
2. Find your `binaapp` project
3. Go to Settings → Git → Branch
4. Deploy branch `claude/fix-profile-auth-bug-DUS18`

**Option B: Merge to Main**
1. Create PR from `claude/fix-profile-auth-bug-DUS18` to `main`
2. Review and merge
3. Vercel auto-deploys main branch

---

### Step 7: Test the Fix

1. **Clear browser cache** (Ctrl+Shift+Delete)
2. Go to https://www.binaapp.my/profile
3. Login with your account
4. You should see **TWO tabs:**
   - 🌐 Website Saya
   - 📦 Pesanan (X baru)
5. Click "📦 Pesanan" tab
6. You should see your orders!

---

## 🔍 **Debugging Checklist**

If orders still don't show:

### ✅ Backend Checks (in Supabase)
- [ ] Tables exist: `delivery_orders`, `riders`, `order_items`
- [ ] RLS is enabled on tables
- [ ] Policies allow owners to SELECT from delivery_orders
- [ ] Permissions granted to `authenticated` role
- [ ] At least one order exists in database
- [ ] Your website ID matches orders' website_id

### ✅ Frontend Checks (in Browser)
- [ ] Latest code deployed to Vercel
- [ ] Environment variables set in Vercel:
  - `NEXT_PUBLIC_SUPABASE_URL`
  - `NEXT_PUBLIC_SUPABASE_ANON_KEY`
- [ ] No JavaScript errors in browser console (F12)
- [ ] Network tab shows successful API calls to Supabase

### ✅ Quick Test Query
Run this in Supabase to simulate frontend query:

```sql
-- This is what the frontend does
SELECT o.*,
       array_agg(oi.*) as order_items
FROM delivery_orders o
LEFT JOIN order_items oi ON oi.order_id = o.id
WHERE o.website_id IN (
    SELECT id FROM websites WHERE user_id = auth.uid()
)
GROUP BY o.id
ORDER BY o.created_at DESC;
```

If this returns orders but frontend doesn't show them → Frontend issue
If this returns empty but orders exist → RLS policy issue

---

## 📊 **Expected Results**

### After Fix, You Should See:

#### Profile Page Tabs:
```
┌─────────────────┬──────────────────┐
│ 🌐 Website (5)  │ 📦 Pesanan (2 baru) │
└─────────────────┴──────────────────┘
```

#### Orders Tab Content:
```
📦 Pesanan                     🔄 Refresh

┌──────────────────────────────────────┐
│ #BNA-20260109-0008                   │
│ 9 Jan 2026, 14:30                    │
│ [Menunggu Pengesahan]                │
│                                      │
│ 👤 Ahmad bin Ali                     │
│ 📱 013-456 7890                      │
│ 📍 No 123, Jalan Merdeka            │
│                                      │
│ 🍽️ 2x Nasi Lemak - RM20.00         │
│                                      │
│ Total: RM25.00                       │
│                                      │
│ ┌─────────────┬─────────────┐       │
│ │ ✅ TERIMA   │  ❌ TOLAK    │       │
│ └─────────────┴─────────────┘       │
└──────────────────────────────────────┘
```

---

## 🆘 **Still Not Working?**

### Check Browser Console (F12)
Look for errors like:
- `Failed to fetch` → Supabase connection issue
- `RLS policy violation` → RLS blocking access
- `null is not an object` → Environment variables missing

### Check Supabase Logs
1. Go to Supabase Dashboard
2. Click "Logs" → "API Logs"
3. Look for failed queries from your profile page

### Test with Direct Query
Use browser console on profile page:

```javascript
// Test if supabase client works
console.log('Supabase:', window.supabase)

// Test loading orders
const { data, error } = await supabase
  .from('delivery_orders')
  .select('*')
  .limit(1)

console.log('Orders:', data, error)
```

---

## 📁 **Files Reference**

All fix scripts are in: `/home/user/binaapp/backend/migrations/`

| File | Purpose |
|------|---------|
| `002_delivery_system.sql` | Creates all delivery tables |
| `006_fix_owner_orders_access.sql` | **RUN THIS FIRST** - Fixes RLS policies |
| `DIAGNOSE_ORDERS_ISSUE.sql` | Diagnose what's wrong |
| `VERIFY_BACKEND_SETUP.sql` | Comprehensive verification |
| `003_test_data.sql` | Add test orders/riders |

---

## ✅ **Success Checklist**

When everything is working:
- ✅ Profile page loads without errors
- ✅ Two tabs visible: Website & Pesanan
- ✅ Pesanan tab shows order count badge
- ✅ Clicking tab shows orders list
- ✅ Each order shows complete details
- ✅ Buttons work: Terima, Tolak, Assign Rider
- ✅ Order status updates in real-time

---

## 🎉 **After Fix Works**

You can now:
1. ✅ See all orders from your websites
2. ✅ Confirm orders (Terima Pesanan)
3. ✅ Reject orders (Tolak)
4. ✅ Assign riders to deliver
5. ✅ Track order status changes
6. ✅ Manage riders

The complete delivery system is now functional! 🚀
