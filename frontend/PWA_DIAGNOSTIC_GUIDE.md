# 🔍 BinaApp Rider PWA - Diagnostic Guide

## ⚠️ Install Prompt Not Showing? Follow These Steps

### Step 1: Use the PWA Diagnostic Tool

Visit: **`https://binaapp.my/pwa-check.html`**

This tool will automatically check:
- ✅ HTTPS requirement
- ✅ Manifest file accessibility
- ✅ Service worker registration
- ✅ Icon files
- ✅ Install prompt availability

**Expected Results:**
- All checks should show ✅ green checkmarks
- If any show ❌ red, that's the issue to fix

---

### Step 2: Check Browser Console

1. **Open Rider App:**
   - Visit: `https://binaapp.my/rider`

2. **Open DevTools:**
   - **Desktop:** Press `F12`
   - **Android Chrome:**
     - Menu (⋮) → More tools → Developer tools
     - Or use USB debugging + Chrome inspect

3. **Look for these console messages:**
   ```
   [Rider PWA] Attempting to register service worker...
   [Rider PWA] ✅ Service Worker registered successfully
   [Rider PWA] Scope: https://binaapp.my/
   [Rider PWA] Setting up install prompt listener...
   [Rider PWA] ⏳ Waiting for install prompt...
   ```

4. **If you see:**
   ```
   [Rider PWA] ✅ Install prompt event captured!
   ```
   → **SUCCESS!** Install banner should appear

5. **If you see:**
   ```
   [Rider PWA] ❌ Service worker registration failed
   ```
   → **PROBLEM:** Service worker file not accessible

---

### Step 3: Manual Checks

#### Check 1: Manifest Accessible
```
Visit: https://binaapp.my/rider-manifest.json
```
**Expected:** JSON file with app details
**If 404:** File not deployed or wrong path

#### Check 2: Service Worker Accessible
```
Visit: https://binaapp.my/sw-rider.js
```
**Expected:** JavaScript service worker code
**If 404:** File not deployed

#### Check 3: Icons Accessible
```
Visit: https://binaapp.my/rider-icon-192.png
Visit: https://binaapp.my/rider-icon-512.png
```
**Expected:** Orange scooter icons
**If 404:** Icons not deployed

---

### Step 4: Chrome DevTools PWA Audit

1. **Open Rider App:** `https://binaapp.my/rider`

2. **Open DevTools:** Press `F12`

3. **Go to Application tab**

4. **Check Manifest:**
   - Application → Manifest
   - Should show all fields populated
   - Icons should load

5. **Check Service Worker:**
   - Application → Service Workers
   - Should show: `sw-rider.js` (activated and running)

6. **Run Lighthouse Audit:**
   - Lighthouse tab → Select "Progressive Web App"
   - Click "Generate report"
   - **Target Score:** 90-100

---

### Step 5: Understand PWA Install Criteria

**Chrome will ONLY show install prompt if ALL these are met:**

✅ **1. HTTPS**
- Site must be served over HTTPS
- OR localhost for testing

✅ **2. Valid Manifest**
- Must have `name`, `short_name`
- Must have `start_url`
- Must have `display: standalone` or `fullscreen`
- Must have at least one icon (192x192 or larger)

✅ **3. Service Worker**
- Must be registered
- Must have `fetch` event handler
- Must be activated

✅ **4. User Engagement**
- User must have visited site at least once before
- **Chrome may delay prompt for ~30 seconds**
- Some users may have dismissed prompt before

✅ **5. Not Already Installed**
- If app is already installed, prompt won't show

---

### Step 6: Common Issues & Solutions

#### Issue 1: "Install prompt never appears"

**Possible Causes:**
1. **Browser doesn't support PWA** (iOS Safari doesn't use `beforeinstallprompt`)
2. **App already installed** (check home screen)
3. **Service worker not registered** (check console)
4. **Manifest invalid** (check DevTools → Application → Manifest)
5. **Not enough engagement** (Chrome waits 30-60 seconds sometimes)

**Solutions:**
- **iOS users:** Must use manual install (Share → Add to Home Screen)
- **Wait 30-60 seconds** after page load
- **Clear browser cache** and revisit
- **Check console for errors**

#### Issue 2: "Service worker registration failed"

**Possible Causes:**
1. File not found (404)
2. HTTPS certificate issue
3. CORS issue

**Solutions:**
```bash
# Check if file exists
curl -I https://binaapp.my/sw-rider.js

# Should return: HTTP/2 200
```

#### Issue 3: "Manifest not found"

**Possible Causes:**
1. File not deployed
2. Wrong path in HTML `<link>` tag

**Solutions:**
```bash
# Check if manifest exists
curl https://binaapp.my/rider-manifest.json

# Should return valid JSON
```

#### Issue 4: "Icons not loading"

**Possible Causes:**
1. Files not uploaded to `/public/`
2. Wrong paths in manifest
3. CORS issues

**Solutions:**
```bash
# Check icons
curl -I https://binaapp.my/rider-icon-192.png
curl -I https://binaapp.my/rider-icon-512.png

# Both should return: HTTP/2 200
```

---

### Step 7: Force Install Prompt (Testing Only)

For testing purposes, you can force the install prompt:

1. **Open DevTools Console**

2. **Type this:**
   ```javascript
   // Check if already installed
   console.log('Is PWA?', window.matchMedia('(display-mode: standalone)').matches);

   // Check service worker
   navigator.serviceWorker.getRegistrations().then(regs => {
     console.log('Service Workers:', regs.length);
     regs.forEach(r => console.log('  Scope:', r.scope));
   });

   // Listen for install prompt
   window.addEventListener('beforeinstallprompt', (e) => {
     console.log('✅ INSTALL PROMPT AVAILABLE!');
   });
   ```

3. **If service worker not registered, register manually:**
   ```javascript
   navigator.serviceWorker.register('/sw-rider.js')
     .then(reg => console.log('✅ SW Registered:', reg.scope))
     .catch(err => console.error('❌ SW Failed:', err));
   ```

---

### Step 8: Platform-Specific Install Methods

#### Android (Chrome)

**Method 1: Automatic Prompt**
1. Visit `https://binaapp.my/rider`
2. Wait 30 seconds
3. Floating orange banner should appear
4. Tap "📲 Install Sekarang"

**Method 2: Manual Install**
1. Visit `https://binaapp.my/rider`
2. Tap menu (⋮) → "Add to Home screen"
3. Confirm "Add"

**Method 3: Chrome Menu**
1. Visit `https://binaapp.my/rider`
2. Look for install icon (⊕) in address bar
3. Tap icon

#### iPhone (Safari)

**Only Method: Manual Install**
1. Visit `https://binaapp.my/rider` **in Safari** (not Chrome!)
2. Tap Share button (⬆️) at bottom
3. Scroll down → "Add to Home Screen"
4. Confirm "Add"

**Note:** iOS Safari does NOT support `beforeinstallprompt` API!

#### Desktop (Chrome/Edge)

**Method 1: Address Bar**
1. Visit `https://binaapp.my/rider`
2. Look for install icon (⊕) in address bar
3. Click icon

**Method 2: Menu**
1. Visit `https://binaapp.my/rider`
2. Menu (⋮) → "Install BinaApp Rider..."
3. Confirm "Install"

---

### Step 9: Verify Installation

After installing, verify:

1. **Icon on Home Screen**
   - Should show orange scooter icon
   - Name: "BinaApp Rider"

2. **Opens in Standalone Mode**
   - No browser address bar
   - No browser tabs
   - Full screen app

3. **Orange Splash Screen**
   - Shows briefly on startup
   - Orange background with icon

4. **Works Offline**
   - Enable airplane mode
   - Open app
   - Should still load

5. **Check in DevTools:**
   ```javascript
   window.matchMedia('(display-mode: standalone)').matches
   // Should return: true
   ```

---

### Step 10: Debugging Tips

#### Enable Verbose Logging

All PWA events are logged to console with `[Rider PWA]` prefix:

```javascript
// In browser console, filter by:
[Rider PWA]

// You should see:
[Rider PWA] Attempting to register service worker...
[Rider PWA] ✅ Service Worker registered successfully
[Rider PWA] Setting up install prompt listener...
[Rider PWA] ⏳ Waiting for install prompt...
```

#### Clear Everything and Start Fresh

```javascript
// In DevTools Console:

// 1. Unregister all service workers
navigator.serviceWorker.getRegistrations()
  .then(regs => regs.forEach(r => r.unregister()));

// 2. Clear all caches
caches.keys()
  .then(keys => Promise.all(keys.map(k => caches.delete(k))));

// 3. Reload page
location.reload();
```

#### Test Service Worker Offline

1. DevTools → Application → Service Workers
2. Check "Offline" checkbox
3. Reload page
4. App should still load (from cache)

---

## 📊 Quick Diagnostic Checklist

Run through this checklist:

- [ ] ✅ Site is HTTPS (not HTTP)
- [ ] ✅ `/rider-manifest.json` returns 200 (not 404)
- [ ] ✅ `/sw-rider.js` returns 200 (not 404)
- [ ] ✅ `/rider-icon-192.png` returns 200
- [ ] ✅ `/rider-icon-512.png` returns 200
- [ ] ✅ Console shows "Service Worker registered successfully"
- [ ] ✅ Console shows "Waiting for install prompt"
- [ ] ✅ No console errors
- [ ] ✅ DevTools → Application → Manifest shows all fields
- [ ] ✅ DevTools → Application → Service Workers shows active
- [ ] ✅ Lighthouse PWA score > 90
- [ ] ✅ Waited at least 30 seconds on page
- [ ] ✅ App not already installed

If ALL checked ✅ → Install prompt SHOULD appear (except iOS Safari)

---

## 🆘 Still Not Working?

### Option 1: Use Diagnostic Tool
Visit: **https://binaapp.my/pwa-check.html**

### Option 2: Check Deployment
```bash
# SSH to server
ssh user@server

# Check files exist
ls -la /path/to/frontend/public/ | grep rider

# Should see:
rider-icon-192.png
rider-icon-512.png
rider-manifest.json
sw-rider.js
```

### Option 3: Manual Install
Even if auto-prompt doesn't work, users can ALWAYS install manually:

- **Android:** Menu → Add to Home screen
- **iPhone:** Share → Add to Home Screen
- **Desktop:** Address bar icon or Menu → Install

---

## 📱 Testing on Real Devices

### Android Testing (USB Debugging)

1. **Enable USB Debugging on phone**
2. **Connect to computer**
3. **Chrome DevTools:**
   - Visit: `chrome://inspect`
   - Select your device
   - Inspect `binaapp.my/rider`
4. **View console logs in real-time**

### iOS Testing (Safari Web Inspector)

1. **Enable Web Inspector:**
   - Settings → Safari → Advanced → Web Inspector

2. **Connect iPhone to Mac**

3. **Safari on Mac:**
   - Develop → [Your iPhone] → binaapp.my

4. **View console logs**

---

## 🎯 Expected Behavior Summary

### First Visit (Not Installed)

1. User visits `/rider`
2. Service worker registers (console log)
3. Install prompt listener sets up (console log)
4. **After 0-60 seconds:** `beforeinstallprompt` event fires
5. Orange floating banner appears at bottom
6. User taps "Install Sekarang"
7. Browser native install dialog shows
8. User confirms
9. App installs to home screen

### Subsequent Visits (Installed)

1. User taps icon on home screen
2. Orange splash screen shows briefly
3. App opens fullscreen (no browser UI)
4. GPS tracking starts
5. Orders load
6. Offline capability works

---

**Last Updated:** January 14, 2026
**For Issues:** Check browser console for `[Rider PWA]` logs
**Diagnostic Tool:** https://binaapp.my/pwa-check.html
