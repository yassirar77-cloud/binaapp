import type { Metadata, Viewport } from 'next';
import { ServiceWorkerRegister } from '@/components/ServiceWorkerRegister';
import { PWAInstallPrompt } from '@/components/PWAInstallPrompt';

export const metadata: Metadata = {
  title: 'BinaApp Rider',
  description: 'Aplikasi penghantaran untuk rider',
  manifest: '/rider/manifest.json',
  appleWebApp: {
    capable: true,
    statusBarStyle: 'default',
    title: 'Rider',
  },
};

export const viewport: Viewport = {
  themeColor: '#ea580c',
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
      <head>
        <link rel="manifest" href="/rider/manifest.json" />
        <link rel="apple-touch-icon" href="/icons/rider-192x192.png" />
        <meta name="apple-mobile-web-app-capable" content="yes" />
        <meta name="apple-mobile-web-app-status-bar-style" content="default" />
        <meta name="apple-mobile-web-app-title" content="Rider" />
        <meta name="theme-color" content="#ea580c" />
      </head>
      <div className="min-h-screen bg-gray-100">
        {children}
      </div>
      <ServiceWorkerRegister swPath="/rider/sw.js" scope="/rider" />
      <PWAInstallPrompt appName="BinaApp Rider" themeColor="#ea580c" />
    </>
  );
}
