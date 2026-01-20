# Rider Query Debug Report

## Issue Summary
**Problem:** Rider "Yassir" exists in database but dashboard shows "Tiada rider tersedia"

**Confirmed Data:**
```
Website ID: 7ab2bbac-ff45-4447-84c5-f3e1513223c7
Rider "Yassir" website_id: 7ab2bbac-ff45-4447-84c5-f3e1513223c7
```

These IDs match perfectly, yet riders are not appearing in the dashboard.

---

## Investigation Summary

### Code Analysis

#### 1. Frontend Rider Loading (`frontend/src/app/profile/page.tsx:347-410`)

The frontend loads riders using this flow:

1. **Loads websites for current user** (line 196-203):
   ```javascript
   const { data: websitesData } = await supabase
     .from('websites')
     .select('*')
     .eq('user_id', currentUser.id)  // ← Only loads websites owned by current user
   ```

2. **Fetches riders for each website** (line 370-398):
   ```javascript
   for (const website of websites) {
     const response = await fetch(
       `${API_URL}/api/v1/delivery/admin/websites/${website.id}/riders`,
       { headers: { 'Authorization': `Bearer ${token}` } }
     )
   }
   ```

#### 2. Backend Rider Query (`backend/app/api/v1/endpoints/delivery.py:1205-1248`)

The backend has a **security check** that validates ownership:

```python
# Line 1222: Check if user owns the website
website_check = supabase.table("websites").select("id").eq("id", website_id).eq("user_id", user_id).execute()

if not website_check.data:
    # User doesn't own this website → return 403 error
    raise HTTPException(status_code=403, detail="Access denied: You don't own this website")

# Line 1235: Only if ownership passes, query riders
resp = supabase.table("riders").select("*").or_(f"website_id.eq.{website_id},website_id.is.null").execute()
```

#### 3. Database RLS Policy (`backend/migrations/002_delivery_system.sql:332-336`)

Row Level Security (RLS) policy on `riders` table:

```sql
CREATE POLICY "Users can view own riders" ON riders
    FOR SELECT USING (
        website_id IN (SELECT id FROM websites WHERE user_id = auth.uid())
        OR website_id IS NULL  -- Shared riders
    );
```

---

## Potential Root Causes

### Most Likely: User Account Mismatch

The rider query will fail if:

1. **Website `7ab2bbac-ff45-4447-84c5-f3e1513223c7` belongs to a different user**
   - Website was created under User A
   - Rider "Yassir" was created for that website (correct website_id)
   - Currently logged in as User B
   - User B's `websites` array does not include this website
   - `loadRiders()` never queries this website
   - Rider never appears in the list

2. **Website ownership changed or data was migrated**
   - Website's `user_id` doesn't match current user's ID
   - Backend returns 403 error when trying to fetch riders

### Other Possibilities

3. **Authentication issue**
   - JWT token has wrong user ID
   - `auth.uid()` in RLS policy doesn't match expected user

4. **Database permissions issue**
   - RLS policy blocking access
   - Service role key not configured, falling back to RLS

---

## Debug Logging Added

### Frontend Changes (`profile/page.tsx`)

**Added logging to show:**
- Current user ID when loading websites (line 197)
- All websites loaded with IDs and user_ids (line 199-206)
- Each website being queried for riders (line 371)
- API response status and data for each website (line 383-407)
- Any errors with full stack traces (line 444)

**Example output you should see in browser console:**
```
[DEBUG] Current user ID: abc123-xyz-...
[DEBUG] Loaded websites: [{ id: '7ab2bbac-...', name: 'ghhfgduuju', user_id: 'abc123-...' }]
=== LOADING RIDERS DEBUG START ===
[DEBUG] Fetching riders for website_id: 7ab2bbac-ff45-4447-84c5-f3e1513223c7
[DEBUG] Response status for website 7ab2bbac-...: 200
[DEBUG] Response data: [{ id: '...', name: 'Yassir', website_id: '7ab2bbac-...' }]
```

### Backend Changes (`delivery.py`)

**Added logging to show:**
- User ID and website ID before ownership check (line 1225)
- Ownership check result (line 1227)
- If check fails, whether website exists but belongs to different user (line 1230-1236)
- Query filter used (line 1239)
- All riders found with their website_ids (line 1244)

**Example output in server logs:**
```
[Rider LIST] Checking ownership - user_id=abc123, website_id=7ab2bbac-...
[Rider LIST] Website ownership check result: [{'id': '7ab2bbac-...', 'user_id': 'abc123'}]
[Rider LIST] Query filter: website_id.eq.7ab2bbac-...,website_id.is.null
[Rider LIST] Found 1 riders
[Rider LIST] Rider website_ids: ['7ab2bbac-...']
```

---

## How to Diagnose

### Step 1: Check Browser Console

1. Open the restaurant dashboard in a browser
2. Open Developer Tools (F12)
3. Go to Console tab
4. Navigate to the Orders tab (where "Tiada rider tersedia" appears)
5. Look for the debug output

**What to check:**
- ✅ Does `[DEBUG] Current user ID` show the expected user?
- ✅ Does `[DEBUG] Loaded websites` include website `7ab2bbac-ff45-4447-84c5-f3e1513223c7`?
- ✅ Does the website's `user_id` match the current user ID?
- ✅ Does `[DEBUG] Response status` show 200 or an error?
- ✅ Does `[DEBUG] Response data` show the rider "Yassir"?

### Step 2: Check Server Logs

1. Check your backend logs (Render, Railway, or local console)
2. Look for `[Rider LIST]` entries
3. Check for ownership check failures

**What to check:**
- ✅ Does the `user_id` in the ownership check match the website's owner?
- ✅ Does the ownership check pass or fail?
- ✅ If it fails, does the website exist but belong to a different user?

### Step 3: Verify Database

Run this SQL query in Supabase SQL Editor:

```sql
-- Check website ownership
SELECT
    w.id as website_id,
    w.name as website_name,
    w.user_id as website_owner_id,
    r.id as rider_id,
    r.name as rider_name,
    r.website_id as rider_website_id
FROM websites w
LEFT JOIN riders r ON r.website_id = w.id
WHERE w.id = '7ab2bbac-ff45-4447-84c5-f3e1513223c7'
OR r.id IN (SELECT id FROM riders WHERE name = 'Yassir');
```

**What to check:**
- ✅ Does the website exist?
- ✅ What is the `website_owner_id`?
- ✅ Does the rider exist?
- ✅ Does `rider_website_id` match `website_id`?

---

## Likely Fixes

### If Website Belongs to Different User

**Option 1: Update website ownership**
```sql
UPDATE websites
SET user_id = '<current_user_id>'
WHERE id = '7ab2bbac-ff45-4447-84c5-f3e1513223c7';
```

**Option 2: Make rider shared (no website_id)**
```sql
UPDATE riders
SET website_id = NULL
WHERE name = 'Yassir';
```
*Note: Shared riders appear in all dashboards*

### If Authentication Issue

- Verify JWT token is correct
- Check user is logged in with correct account
- Try logging out and logging back in

### If Permission Issue

- Verify service role key is configured in backend env
- Check RLS policies are not overly restrictive

---

## Additional Finding

**Potential Issue in Add Rider Form:**

Line 1262 in `profile/page.tsx`:
```javascript
<AddRiderForm websiteId={websites[0]?.id} />
```

This **always uses the first website** when adding riders. If a user has multiple websites, riders are always created for `websites[0]`, not necessarily the website they're viewing.

**Suggested improvement:**
- Add a website selector dropdown in the Add Rider form
- OR create riders for the currently selected website (if tracking active website)

---

## Next Steps

1. **Check browser console** for debug output
2. **Check server logs** for ownership check results
3. **Run database query** to verify data
4. **Share debug output** to identify exact issue
5. **Apply appropriate fix** based on findings

---

## Changes Committed

**Commits:**
1. `d81c975` - Add comprehensive debug logging to trace rider query issue
2. `288d0ea` - Add detailed website ownership check logging

**Branch:** `claude/fix-rider-query-website-id-JUDTS`

**Files Modified:**
- `frontend/src/app/profile/page.tsx` - Enhanced rider loading debug logs
- `backend/app/api/v1/endpoints/delivery.py` - Added ownership check logging

---

**Status:** Debug logging deployed. Waiting for diagnostic output to identify root cause and apply fix.
