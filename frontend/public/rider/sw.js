const CACHE_NAME = 'rider-cache-v1';
const urlsToCache = [
  '/rider',
  '/rider/offline.html'
];

// Install event
self.addEventListener('install', (event) => {
  console.log('[Rider SW] Installing...');
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => {
        console.log('[Rider SW] Caching rider shell');
        return cache.addAll(urlsToCache);
      })
      .then(() => self.skipWaiting())
  );
});

// Activate event
self.addEventListener('activate', (event) => {
  console.log('[Rider SW] Activating...');
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames
          .filter((name) => name.startsWith('rider-') && name !== CACHE_NAME)
          .map((name) => {
            console.log('[Rider SW] Deleting old cache:', name);
            return caches.delete(name);
          })
      );
    }).then(() => self.clients.claim())
  );
});

// Fetch event
self.addEventListener('fetch', (event) => {
  // Only handle rider URLs
  if (!event.request.url.includes('/rider')) return;

  // Skip API calls
  if (event.request.url.includes('/api/')) return;

  event.respondWith(
    fetch(event.request)
      .then((response) => {
        const responseClone = response.clone();
        if (response.status === 200) {
          caches.open(CACHE_NAME).then((cache) => {
            cache.put(event.request, responseClone);
          });
        }
        return response;
      })
      .catch(() => {
        return caches.match(event.request).then((response) => {
          if (response) return response;
          if (event.request.headers.get('accept').includes('text/html')) {
            return caches.match('/rider/offline.html');
          }
        });
      })
  );
});

// Push notification for rider
self.addEventListener('push', (event) => {
  const data = event.data ? event.data.json() : {};
  const title = data.title || 'Pesanan Baru!';
  const options = {
    body: data.body || 'Ada pesanan baru untuk dihantar',
    icon: '/icons/rider-192x192.png',
    badge: '/icons/rider-badge-72x72.png',
    tag: 'rider-order',
    vibrate: [200, 100, 200, 100, 200],
    requireInteraction: true,
    data: data.url || '/rider'
  };

  event.waitUntil(
    self.registration.showNotification(title, options)
  );
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  event.waitUntil(
    clients.openWindow(event.notification.data)
  );
});
