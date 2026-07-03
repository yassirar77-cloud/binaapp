'use client';

import { useEffect } from 'react';

interface Props {
  swPath: string;
  scope?: string;
}

export function ServiceWorkerRegister({ swPath, scope = '/' }: Props) {
  useEffect(() => {
    if (typeof window === 'undefined' || !('serviceWorker' in navigator)) return;

    const register = () => {
      navigator.serviceWorker
        .register(swPath, { scope })
        .then((registration) => {
          console.log(`[SW] Registered for scope: ${scope}`, registration);

          // Check for updates
          registration.addEventListener('updatefound', () => {
            const newWorker = registration.installing;
            if (newWorker) {
              newWorker.addEventListener('statechange', () => {
                if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
                  // New content available
                  console.log('[SW] New content available, refresh to update');
                }
              });
            }
          });
        })
        .catch((error) => {
          console.error('[SW] Registration failed:', error);
        });
    };

    // Hydration usually completes after the window load event has already
    // fired, so a bare addEventListener('load') never runs and the SW is
    // silently never registered. Register immediately if the page has
    // loaded, otherwise defer to the load event.
    if (document.readyState === 'complete') {
      register();
      return;
    }
    window.addEventListener('load', register);
    return () => window.removeEventListener('load', register);
  }, [swPath, scope]);

  return null;
}
