/**
 * Service Worker Registration for PWA
 * Handles both main BinaApp and Rider App service workers
 */

export function registerServiceWorker(): void {
  if (typeof window !== 'undefined' && 'serviceWorker' in navigator) {
    window.addEventListener('load', async () => {
      const isRiderPage = window.location.pathname.startsWith('/rider');

      if (isRiderPage) {
        // Register Rider service worker for /rider pages
        try {
          const registration = await navigator.serviceWorker.register('/sw-rider.js', {
            scope: '/rider'
          });
          console.log('[Rider SW] Registered:', registration.scope);
          setupUpdateHandler(registration, 'Rider');
        } catch (error) {
          console.log('[Rider SW] Registration failed:', error);
        }
      } else {
        // Register main BinaApp service worker for all other pages
        try {
          const registration = await navigator.serviceWorker.register('/sw.js', {
            scope: '/'
          });
          console.log('[BinaApp SW] Registered:', registration.scope);
          setupUpdateHandler(registration, 'BinaApp');
        } catch (error) {
          console.log('[BinaApp SW] Registration failed:', error);
        }
      }
    });
  }
}

function setupUpdateHandler(registration: ServiceWorkerRegistration, appName: string): void {
  registration.addEventListener('updatefound', () => {
    const newWorker = registration.installing;
    if (newWorker) {
      newWorker.addEventListener('statechange', () => {
        if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
          console.log(`[${appName}] New version available!`);
          window.dispatchEvent(new CustomEvent('swUpdate', { detail: registration }));
        }
      });
    }
  });
}

export function unregisterServiceWorker(): void {
  if (typeof window !== 'undefined' && 'serviceWorker' in navigator) {
    navigator.serviceWorker.ready.then((registration) => {
      registration.unregister();
    });
  }
}

/**
 * Unregister all service workers and clear caches
 * Useful for debugging PWA issues
 */
export async function clearAllServiceWorkers(): Promise<void> {
  if (typeof window !== 'undefined' && 'serviceWorker' in navigator) {
    const registrations = await navigator.serviceWorker.getRegistrations();
    for (const registration of registrations) {
      await registration.unregister();
      console.log('Unregistered SW:', registration.scope);
    }

    // Clear all caches
    const cacheNames = await caches.keys();
    for (const cacheName of cacheNames) {
      await caches.delete(cacheName);
      console.log('Deleted cache:', cacheName);
    }
  }
}
