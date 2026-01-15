# 🧪 TEST PLAN - User Selection Fixes

## ✅ What Was Fixed Today

### 1. Backend Logic (4 locations)
- **File:** `backend/app/api/simple/generate.py`
- **Lines:** 685-735, 1322-1338, 1728-1744, 1968-1984
- **Fix:** Changed `default=True` to `default=False` for WhatsApp
- **Fix:** Features now built ONLY from user selections (no auto-detection merge)

### 2. HTML Sanitization Safety Net
- **File:** `backend/app/api/simple/generate.py`
- **Lines:** 1218-1286
- **Fix:** Added `sanitize_html()` function to remove unauthorized content
- **Applied:** Line 1115 (called after AI generation)

### 3. Frontend Logging
- **File:** `frontend/src/app/create/page.tsx`
- **Lines:** 261-271
- **Fix:** Added comprehensive console logging

---

## 🧪 How to Test (Step by Step)

### Test Case 1: No Images + No WhatsApp

1. **Deploy Changes:**
   ```bash
   # Deploy backend and frontend to Render/Vercel
   ```

2. **Open Browser Console** (F12 → Console tab)

3. **Fill Form:**
   - Description: "Kedai Runcit Pak Ali"
   - Image Selection: **Select "Tiada Gambar" (None)** ✅
   - Features: **UNCHECK WhatsApp** ❌
   - Features: **UNCHECK Social Media** ❌

4. **Click "Jana Website"**

5. **Check Console Logs** - Should see:
   ```
   ==========================================
   📤 SENDING TO BACKEND:
     🖼️ Image Choice: none
     ✅ Features: {whatsapp: false, googleMap: false, ...}
     📱 WhatsApp: false
     📱 Social Media: false
   ==========================================
   ```

6. **Check Backend Logs** (Render Dashboard → Logs) - Should see:
   ```
   ============================================================
   USER FEATURE SELECTIONS (from frontend):
     Raw features dict: {'whatsapp': False, 'googleMap': False, ...}
     WhatsApp: False
     Social Media: False
     Image Choice: none
   ============================================================
   ✗ WhatsApp: DISABLED by user
   🚫 Removing ALL images (user selected 'Tiada Gambar')
   🚫 Removing WhatsApp links (user did not select WhatsApp)
   🚫 Removing social media links (user did not select Social Media)
   ✅ Sanitization complete - Removed XXX bytes of unauthorized content
   ```

7. **Check Generated HTML:**
   - ❌ Should have **NO** `<img>` tags
   - ❌ Should have **NO** `wa.me` links
   - ❌ Should have **NO** `unsplash.com` URLs
   - ❌ Should have **NO** Instagram/Facebook links
   - ✅ Should have gradient backgrounds instead

---

### Test Case 2: WhatsApp Enabled (Default)

1. **Fill Form:**
   - Description: "Restoran Nasi Lemak"
   - Image Selection: **Select "Jana Gambar AI"** ✅
   - Features: **LEAVE WhatsApp CHECKED** ✅

2. **Check Console:**
   ```
   📱 WhatsApp: true
   ```

3. **Check Backend:**
   ```
   ✓ WhatsApp: ENABLED by user
   ```

4. **Check HTML:**
   - ✅ Should have WhatsApp button with `wa.me` link
   - ✅ Should have AI-generated images

---

## 🔍 Debugging If It Fails

### If Images Still Appear When "Tiada Gambar" Selected:

1. Check console - is `Image Choice: none`?
   - ❌ NO → Frontend bug (not sending correctly)
   - ✅ YES → Check backend logs

2. Check backend logs - is `image_choice='none'` received?
   - ❌ NO → API route not forwarding data
   - ✅ YES → Check sanitization logs

3. Check sanitization logs - does it say "Removing ALL images"?
   - ❌ NO → sanitize_html() not being called
   - ✅ YES → Images removed but regenerated elsewhere

### If WhatsApp Appears When Unchecked:

1. Check console - is `📱 WhatsApp: false`?
   - ❌ NO → User didn't uncheck the box!
   - ✅ YES → Check backend logs

2. Check backend logs - is `✗ WhatsApp: DISABLED by user`?
   - ❌ NO → Backend not reading features correctly
   - ✅ YES → Check if sanitization ran

3. Check sanitization - does it say "Removing WhatsApp links"?
   - ❌ NO → WhatsApp is in features list somehow
   - ✅ YES → WhatsApp removed but AI regenerated it

---

## 📊 Expected Results Summary

| User Action | Frontend Sends | Backend Receives | AI Gets | Final HTML |
|-------------|----------------|------------------|---------|------------|
| ✅ "Tiada Gambar" | `image_choice: "none"` | `image_choice='none'` | "DO NOT use images" prompt | No images |
| ✅ Uncheck WhatsApp | `whatsapp: false` | `features.get("whatsapp")` → `False` | No WhatsApp instructions | No WhatsApp |
| ✅ Check WhatsApp | `whatsapp: true` | `features.get("whatsapp")` → `True` | WhatsApp instructions | WhatsApp included |

---

## 🚀 Deploy Instructions

1. **Backend:**
   ```bash
   git push origin claude/fix-ai-user-selections-V5jdE
   # Render auto-deploys from this branch
   ```

2. **Frontend:**
   ```bash
   git push origin claude/fix-ai-user-selections-V5jdE
   # Vercel auto-deploys from this branch
   ```

3. **Wait 2-3 minutes** for deployment

4. **Run Test Cases** above

---

## ✅ Success Criteria

All of these must be true:

- [ ] Console logs show correct values being sent
- [ ] Backend logs show "USER FEATURE SELECTIONS" with correct values
- [ ] Backend logs show "✗ WhatsApp: DISABLED by user" when unchecked
- [ ] Backend logs show "🚫 Removing ALL images" when none selected
- [ ] Sanitization logs show "Removed XXX bytes" when content removed
- [ ] Final HTML has NO unauthorized images
- [ ] Final HTML has NO unauthorized WhatsApp links

If ALL boxes checked → **FIX WORKS!** ✅
If ANY box unchecked → **More debugging needed** ❌

