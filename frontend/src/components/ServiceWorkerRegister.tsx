'use client';

import { useEffect } from 'react';

interface Props {
  swPath: string;
  scope?: string;
}

export function ServiceWorkerRegister({ swPath, scope = '/' }: Props) {
  useEffect(() => {
    if (typeof window !== 'undefined' && 'serviceWorker' in navigator) {
      // Wait for page load
      window.addEventListener('load', () => {
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
      });
    }
  }, [swPath, scope]);

  return null;
}
