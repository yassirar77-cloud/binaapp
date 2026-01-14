const CACHE_NAME = 'binaapp-v3';  // Updated: separate from Rider PWA
const urlsToCache = [
  '/',
  '/create',
  '/profile',
  '/manifest.json',
  '/icons/icon-192x192.png',
  '/icons/icon-512x512.png'
];
// Note: /rider is handled by sw-rider.js separately

// Install event - cache files
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => {
        console.log('BinaApp: Caching app shell');
        return cache.addAll(urlsToCache);
      })
  );
  self.skipWaiting();
});

// Activate event - clean old caches
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((cacheName) => {
          if (cacheName !== CACHE_NAME) {
            console.log('BinaApp: Removing old cache', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    })
  );
  self.clients.claim();
});

// Fetch event - serve from cache, fallback to network
self.addEventListener('fetch', (event) => {
  // Skip non-GET requests
  if (event.request.method !== 'GET') {
    return;
  }

  // Skip API requests - always fetch from network
  if (event.request.url.includes('/api/') || event.request.url.includes('/v1/')) {
    return;
  }

  // Skip /rider paths - handled by sw-rider.js
  if (event.request.url.includes('/rider')) {
    return;
  }

  event.respondWith(
    caches.match(event.request)
      .then((response) => {
        // Return cached version or fetch from network
        return response || fetch(event.request)
          .then((fetchResponse) => {
            // Only cache successful responses
            if (fetchResponse.status === 200 && fetchResponse.type === 'basic') {
              const responseClone = fetchResponse.clone();
              caches.open(CACHE_NAME)
                .then((cache) => {
                  cache.put(event.request, responseClone);
                });
            }
            return fetchResponse;
          });
      })
      .catch(() => {
        // Offline fallback - return cached home page for navigation requests
        if (event.request.mode === 'navigate') {
          return caches.match('/');
        }
      })
  );
});

// Handle messages from the app
self.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
});

// Push notifications (Phase 2 - Rider App)
self.addEventListener('push', (event) => {
  const data = event.data ? event.data.json() : {};

  const options = {
    body: data.body || 'Pesanan baru tersedia!',
    icon: '/icons/icon-192x192.png',
    badge: '/icons/icon-72x72.png',
    vibrate: [200, 100, 200],
    tag: data.tag || 'notification',
    data: data,
    actions: [
      { action: 'view', title: 'Lihat Pesanan' },
      { action: 'dismiss', title: 'Tutup' }
    ]
  };

  event.waitUntil(
    self.registration.showNotification(data.title || 'BinaApp Rider', options)
  );
});

// Notification click handler
self.addEventListener('notificationclick', (event) => {
  event.notification.close();

  if (event.action === 'view' || !event.action) {
    event.waitUntil(
      clients.openWindow(event.notification.data.url || '/rider')
    );
  }
});

// Background sync for GPS updates (future enhancement)
self.addEventListener('sync', (event) => {
  if (event.tag === 'sync-gps-updates') {
    console.log('[SW] Background sync: Sending queued GPS updates');
    // TODO: Send queued GPS updates when back online
  }
});
