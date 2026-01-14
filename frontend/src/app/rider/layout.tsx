import type { Metadata, Viewport } from 'next';

export const metadata: Metadata = {
  title: 'BinaApp Rider - Sistem Penghantaran',
  description: 'Aplikasi penghantaran real-time untuk rider BinaApp. Track pesanan, GPS auto-update, dan manage deliveries dengan mudah.',
  manifest: '/rider-manifest.json',
  appleWebApp: {
    capable: true,
    statusBarStyle: 'black-translucent',
    title: 'BinaApp Rider',
    startupImage: [
      {
        url: '/rider-icon-512.png',
        media: '(device-width: 375px) and (device-height: 812px) and (-webkit-device-pixel-ratio: 3)',
      },
      {
        url: '/rider-icon-512.png',
        media: '(device-width: 390px) and (device-height: 844px) and (-webkit-device-pixel-ratio: 3)',
      },
      {
        url: '/rider-icon-512.png',
        media: '(device-width: 414px) and (device-height: 896px) and (-webkit-device-pixel-ratio: 3)',
      },
    ],
  },
  icons: {
    icon: [
      { url: '/rider-icon-192.png', sizes: '192x192', type: 'image/png' },
      { url: '/rider-icon-512.png', sizes: '512x512', type: 'image/png' },
    ],
    apple: [
      { url: '/rider-icon-192.png', sizes: '192x192', type: 'image/png' },
    ],
  },
  other: {
    'mobile-web-app-capable': 'yes',
    'apple-mobile-web-app-capable': 'yes',
    'apple-touch-fullscreen': 'yes',
  },
};

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  maximumScale: 1,
  userScalable: false,
  themeColor: [
    { media: '(prefers-color-scheme: light)', color: '#ea580c' },
    { media: '(prefers-color-scheme: dark)', color: '#ea580c' },
  ],
};

export default function RiderLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-screen bg-gray-100">
      {children}
    </div>
  );
}
