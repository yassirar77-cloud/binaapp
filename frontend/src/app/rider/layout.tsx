import type { Metadata, Viewport } from 'next';
import { ServiceWorkerRegister } from '@/components/ServiceWorkerRegister';

export const metadata: Metadata = {
  title: 'BinaApp Rider',
  description: 'Aplikasi penghantaran untuk rider',
  manifest: '/rider/manifest.json',
  appleWebApp: {
    capable: true,
    statusBarStyle: 'default',
    title: 'BinaApp Rider',
  },
  other: {
    'mobile-web-app-capable': 'yes',
  },
};

export const viewport: Viewport = {
  themeColor: '#0a0e1a',
  width: 'device-width',
  initialScale: 1,
  maximumScale: 1,
  userScalable: false,
};

export default function RiderLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <>
      {children}
      {/* Scope "/rider" (no trailing slash) so the SW controls the /rider
          page itself — Next serves the app at /rider, and scope "/rider/"
          would never match it. Widening past the sw.js directory is allowed
          by the Service-Worker-Allowed: /rider header in next.config.js. */}
      <ServiceWorkerRegister swPath="/rider/sw.js" scope="/rider" />
    </>
  );
}
