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
  icons: {
    apple: '/icons/rider-192x192.png',
  },
  other: {
    'mobile-web-app-capable': 'yes',
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
      <div className="min-h-screen bg-gray-100">
        {children}
      </div>
      <ServiceWorkerRegister swPath="/rider/sw.js" scope="/rider" />
      <PWAInstallPrompt appName="BinaApp Rider" themeColor="#ea580c" />
    </>
  );
}
