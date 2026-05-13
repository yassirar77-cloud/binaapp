'use client';

// Duplicated from /dashboard/penghantar-live/lib/useIsMobile.ts to avoid
// cross-feature coupling.
//
// useIsMobile — single matchMedia subscription at the desktop breakpoint.
// Returns false on the server and during the first client paint, then resolves
// to the real value via a useEffect. Match `md:` from Tailwind (768px).

import { useEffect, useState } from 'react';

const QUERY = '(max-width: 767px)';

export function useIsMobile(): boolean {
  const [mobile, setMobile] = useState(false);

  useEffect(() => {
    if (typeof window === 'undefined' || !window.matchMedia) return;
    const mq = window.matchMedia(QUERY);
    setMobile(mq.matches);
    const handler = (e: MediaQueryListEvent) => setMobile(e.matches);
    mq.addEventListener('change', handler);
    return () => mq.removeEventListener('change', handler);
  }, []);

  return mobile;
}
