# 🚀 BinaApp Rider PWA Testing Guide

## ✅ What's Implemented

The Rider App now has **full Progressive Web App (PWA)** capabilities:

- ✅ PWA Manifest (`/rider-manifest.json`)
- ✅ Service Worker (`/sw-rider.js`)
- ✅ App Icons (192x192 & 512x512)
- ✅ iOS Support (splash screens, meta tags)
- ✅ Install Prompt UI
- ✅ Offline Capability
- ✅ Push Notifications (ready)
- ✅ Background GPS Sync

## 📱 How to Test PWA Installation

### Android (Chrome)

1. **Open the app:**
   - Visit: `https://binaapp.my/rider`
   - Or your deployment URL

2. **Install the app:**
   - **Option A:** Tap the floating install banner at the bottom
   - **Option B:** Tap the menu (⋮) → "Add to Home screen"
   - **Option C:** Look for the install icon in the address bar

3. **Verify installation:**
   - App icon appears on home screen
   - Opens in standalone mode (no browser UI)
   - Orange splash screen shows on launch
   - Works offline (try airplane mode)

### iPhone (Safari)

1. **Open the app:**
   - Visit: `https://binaapp.my/rider` in Safari
   - **Note:** Must use Safari, not Chrome/Firefox

2. **Install the app:**
   - Tap the Share button (square with arrow)
   - Scroll down and tap "Add to Home Screen"
   - Confirm by tapping "Add"

3. **Verify installation:**
   - App icon appears on home screen
   - Opens fullscreen (no Safari UI)
   - Orange status bar
   - Works offline

### Desktop (Chrome/Edge)

1. **Open the app:**
   - Visit: `https://binaapp.my/rider`

2. **Install the app:**
   - Click the install icon (⊕) in the address bar
   - Or: Menu → "Install BinaApp Rider"

3. **Verify installation:**
   - App opens in its own window
   - No browser tabs/address bar
   - Works offline

## 🔍 Testing Checklist

### Basic PWA Features
- [ ] Install prompt appears on first visit
- [ ] App installs successfully
- [ ] Icon appears on home screen/desktop
- [ ] App opens in standalone mode (no browser UI)
- [ ] Orange theme color shows correctly

### Offline Functionality
- [ ] Turn on airplane mode
- [ ] Open installed app
- [ ] Cached orders still visible
- [ ] Login persists
- [ ] GPS location cached
- [ ] Reconnects when online

### iOS Specific
- [ ] Splash screen shows (orange background)
- [ ] Status bar is black-translucent
- [ ] Full screen mode (no Safari UI)
- [ ] Landscape orientation locked to portrait

### Android Specific
- [ ] Install banner shows
- [ ] Mask icon displays correctly
- [ ] Theme color in taskbar
- [ ] App shortcut works

### Advanced Features
- [ ] Service worker registers successfully
- [ ] GPS tracking works in PWA mode
- [ ] Orders update when online
- [ ] Push notifications (if enabled)
- [ ] Background sync works

## 🐛 Debugging PWA

### Chrome DevTools (Desktop/Android)

1. **Open DevTools:** Press F12
2. **Check Manifest:**
   - Go to "Application" tab
   - Click "Manifest"
   - Verify all fields are correct
   - Check icons load

3. **Check Service Worker:**
   - Go to "Application" tab
   - Click "Service Workers"
   - Should show: "sw-rider.js" (activated and running)

4. **Test Offline:**
   - Go to "Network" tab
   - Check "Offline" checkbox
   - Reload app - should still work

5. **Lighthouse Audit:**
   - Go to "Lighthouse" tab
   - Select "Progressive Web App"
   - Click "Generate report"
   - **Target Score:** 90-100

### Safari DevTools (iOS)

1. **Enable Web Inspector:**
   - Settings → Safari → Advanced → Web Inspector

2. **Connect iPhone to Mac:**
   - Open Safari on Mac
   - Develop → [Your iPhone] → binaapp.my

3. **Check Console:**
   - Look for "[SW Rider]" messages
   - Verify service worker loads

### Common Issues & Fixes

**Problem:** Install prompt doesn't show
- **Fix:** Must be HTTPS (not HTTP)
- **Fix:** Clear browser cache
- **Fix:** Service worker must register successfully

**Problem:** Service worker not registering
- **Fix:** Check browser console for errors
- **Fix:** Ensure `sw-rider.js` is in `/public/`
- **Fix:** Check file path in `page.tsx` line 174

**Problem:** Icons not loading
- **Fix:** Verify files exist in `/public/`
- **Fix:** Check manifest paths are correct
- **Fix:** Clear cache and hard reload

**Problem:** Not working offline
- **Fix:** Open app online first (to cache)
- **Fix:** Check service worker is active
- **Fix:** Verify cache strategy in `sw-rider.js`

## 📊 PWA Compliance Check

Use these tools to verify PWA compliance:

1. **PWA Builder:**
   - Visit: https://www.pwabuilder.com/
   - Enter: `https://binaapp.my/rider`
   - Check score (should be 100/100)

2. **Lighthouse (Chrome):**
   - F12 → Lighthouse → PWA Audit
   - **Target:** 100/100

3. **Web.dev Measure:**
   - Visit: https://web.dev/measure/
   - Enter URL and run test

## 🎯 Expected Results

### Perfect PWA Score Checklist
- [x] Registers a service worker
- [x] Responds with 200 when offline
- [x] Has a web app manifest
- [x] Uses HTTPS
- [x] Redirects HTTP to HTTPS
- [x] Has a viewport meta tag
- [x] Contains themed icons
- [x] Has a maskable icon
- [x] Provides a valid apple-touch-icon
- [x] Configured for a custom splash screen
- [x] Sets a theme color
- [x] Content is sized correctly for viewport
- [x] Display set to standalone/fullscreen

## 🚀 Post-Deployment Testing

After deploying to production:

1. **Test on real devices:**
   - Android phone (Chrome)
   - iPhone (Safari)
   - Desktop (Chrome/Edge)

2. **Test different networks:**
   - 4G/5G mobile
   - Slow 3G (DevTools throttling)
   - Offline mode

3. **Test GPS in PWA:**
   - Login as rider
   - Grant location permission
   - Verify GPS updates every 15 seconds
   - Check GPS works offline (cached)

4. **Test order flow:**
   - Receive new order
   - Accept order
   - Navigate to customer
   - Update status
   - Complete delivery

## 📸 Screenshots for Verification

Take these screenshots to verify PWA works:

1. **Install prompt showing**
2. **App icon on home screen**
3. **App running in standalone mode**
4. **Splash screen (if possible)**
5. **Offline mode working**
6. **Lighthouse PWA score (100/100)**

## 🔗 Resources

- [PWA Checklist](https://web.dev/pwa-checklist/)
- [Service Worker API](https://developer.mozilla.org/en-US/docs/Web/API/Service_Worker_API)
- [Web App Manifest](https://developer.mozilla.org/en-US/docs/Web/Manifest)
- [iOS PWA Support](https://webkit.org/blog/7929/designing-websites-for-iphone-x/)

---

**Last Updated:** January 14, 2026
**PWA Version:** v1.0
**Service Worker:** sw-rider.js v1
