'use client';

// Thin shell — the real /rider app lives in RiderApp.tsx and its children.
// layout.tsx (PWA contract: manifest, themeColor, service worker scope) is
// preserved untouched.

import RiderApp from './RiderApp';

export default function RiderPage() {
  return <RiderApp />;
}
