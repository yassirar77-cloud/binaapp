// BinaApp Rider Service Worker
const CACHE_NAME = 'binaapp-rider-v1';
const STATIC_CACHE_NAME = 'binaapp-rider-static-v1';

// Static assets to cache
const STATIC_ASSETS = [
  '/rider',
  '/rider-manifest.json',
  '/rider-icon-192.png',
  '/rider-icon-512.png'
];

// API endpoints to cache for offline
const API_CACHE_URLS = [
  '/v1/delivery/riders/'
];

// Install event - cache static assets
self.addEventListener('install', (event) => {
  console.log('[SW Rider] Installing service worker...');
  event.waitUntil(
    caches.open(STATIC_CACHE_NAME).then((cache) => {
      console.log('[SW Rider] Caching static assets');
      return cache.addAll(STATIC_ASSETS).catch((err) => {
        console.log('[SW Rider] Failed to cache some assets:', err);
      });
    })
  );
  self.skipWaiting();
});

// Activate event - clean up old caches
self.addEventListener('activate', (event) => {
  console.log('[SW Rider] Activating service worker...');
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((cacheName) => {
          if (cacheName !== CACHE_NAME && cacheName !== STATIC_CACHE_NAME) {
            console.log('[SW Rider] Deleting old cache:', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    })
  );
  self.clients.claim();
});

// Fetch event - network first, fall back to cache
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Skip non-GET requests
  if (request.method !== 'GET') {
    return;
  }

  // Skip chrome-extension and other non-http requests
  if (!url.protocol.startsWith('http')) {
    return;
  }

  // Handle API requests
  if (url.pathname.includes('/v1/delivery/') || url.pathname.includes('/api/')) {
    event.respondWith(networkFirstStrategy(request));
    return;
  }

  // Handle static assets and pages
  if (url.pathname.startsWith('/rider') ||
      url.pathname.includes('rider-icon') ||
      url.pathname.includes('rider-manifest')) {
    event.respondWith(staleWhileRevalidate(request));
    return;
  }

  // Default: network first
  event.respondWith(networkFirstStrategy(request));
});

// Network first strategy - try network, fall back to cache
async function networkFirstStrategy(request) {
  try {
    const networkResponse = await fetch(request);

    // Cache successful responses
    if (networkResponse.ok) {
      const cache = await caches.open(CACHE_NAME);
      cache.put(request, networkResponse.clone());
    }

    return networkResponse;
  } catch (error) {
    console.log('[SW Rider] Network failed, trying cache:', request.url);
    const cachedResponse = await caches.match(request);

    if (cachedResponse) {
      return cachedResponse;
    }

    // Return offline fallback for API requests
    if (request.url.includes('/v1/')) {
      return new Response(
        JSON.stringify({
          error: 'offline',
          message: 'Anda dalam mod offline',
          cached: false
        }),
        {
          status: 503,
          headers: { 'Content-Type': 'application/json' }
        }
      );
    }

    throw error;
  }
}

// Stale-while-revalidate strategy
async function staleWhileRevalidate(request) {
  const cachedResponse = await caches.match(request);

  const networkPromise = fetch(request).then((networkResponse) => {
    if (networkResponse.ok) {
      const cache = caches.open(STATIC_CACHE_NAME);
      cache.then((c) => c.put(request, networkResponse.clone()));
    }
    return networkResponse;
  }).catch(() => cachedResponse);

  return cachedResponse || networkPromise;
}

// Background sync for GPS updates (when back online)
self.addEventListener('sync', (event) => {
  console.log('[SW Rider] Sync event:', event.tag);

  if (event.tag === 'gps-sync') {
    event.waitUntil(syncGPSUpdates());
  }
});

// Sync GPS updates that were queued while offline
async function syncGPSUpdates() {
  try {
    const cache = await caches.open(CACHE_NAME);
    const pendingGPS = await cache.match('pending-gps');

    if (pendingGPS) {
      const data = await pendingGPS.json();

      for (const update of data.updates) {
        try {
          await fetch(update.url, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(update.body)
          });
        } catch (err) {
          console.log('[SW Rider] Failed to sync GPS update:', err);
        }
      }

      // Clear pending updates
      await cache.delete('pending-gps');
    }
  } catch (error) {
    console.log('[SW Rider] GPS sync failed:', error);
  }
}

// Push notifications (for new order alerts)
self.addEventListener('push', (event) => {
  console.log('[SW Rider] Push received:', event);

  let data = { title: 'BinaApp Rider', body: 'Pesanan baru!' };

  if (event.data) {
    try {
      data = event.data.json();
    } catch (e) {
      data.body = event.data.text();
    }
  }

  const options = {
    body: data.body,
    icon: '/rider-icon-192.png',
    badge: '/rider-icon-192.png',
    vibrate: [200, 100, 200],
    tag: 'rider-notification',
    requireInteraction: true,
    actions: [
      { action: 'open', title: 'Buka App' },
      { action: 'dismiss', title: 'Tutup' }
    ]
  };

  event.waitUntil(
    self.registration.showNotification(data.title, options)
  );
});

// Handle notification clicks
self.addEventListener('notificationclick', (event) => {
  console.log('[SW Rider] Notification clicked:', event.action);

  event.notification.close();

  if (event.action === 'dismiss') {
    return;
  }

  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true })
      .then((windowClients) => {
        // Focus existing window if open
        for (const client of windowClients) {
          if (client.url.includes('/rider') && 'focus' in client) {
            return client.focus();
          }
        }
        // Open new window
        if (clients.openWindow) {
          return clients.openWindow('/rider');
        }
      })
  );
});

console.log('[SW Rider] Service worker loaded');
