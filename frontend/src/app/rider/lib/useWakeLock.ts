// /rider — screen wake lock.
//
// Riders keep the phone mounted on the handlebar; letting the screen sleep
// kills GPS uploads on iOS/Android. While `enabled` (logged in) we hold a
// `navigator.wakeLock` screen sentinel, re-acquire it when the tab becomes
// visible again (the UA auto-releases on background), and release on
// logout/unmount. Silently no-ops where the API is unsupported or the UA
// refuses (e.g. low-battery mode).

import { useEffect } from 'react';

export function useWakeLock(enabled: boolean): void {
  useEffect(() => {
    if (!enabled) return;
    if (
      typeof navigator === 'undefined' ||
      typeof document === 'undefined' ||
      !('wakeLock' in navigator)
    ) {
      return;
    }

    let sentinel: WakeLockSentinel | null = null;
    let cancelled = false;

    const acquire = async () => {
      try {
        const s = await navigator.wakeLock.request('screen');
        if (cancelled) {
          void s.release().catch(() => {});
          return;
        }
        sentinel = s;
      } catch {
        /* silently no-op — unsupported / UA refused */
      }
    };

    void acquire();

    const onVisibilityChange = () => {
      // The UA releases the lock whenever the page is hidden; grab a fresh
      // sentinel when the rider comes back.
      if (document.visibilityState === 'visible') void acquire();
    };
    document.addEventListener('visibilitychange', onVisibilityChange);

    return () => {
      cancelled = true;
      document.removeEventListener('visibilitychange', onVisibilityChange);
      if (sentinel) {
        void sentinel.release().catch(() => {});
        sentinel = null;
      }
    };
  }, [enabled]);
}
