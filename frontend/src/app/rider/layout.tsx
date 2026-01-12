import type { Metadata, Viewport } from 'next';

export const metadata: Metadata = {
  title: 'BinaApp Rider',
  description: 'Aplikasi rider untuk penghantaran makanan BinaApp',
  manifest: '/rider-manifest.json',
  appleWebApp: {
    capable: true,
    statusBarStyle: 'black-translucent',
    title: 'BinaApp Rider',
  },
  icons: {
    icon: '/rider-icon-192.png',
    apple: '/rider-icon-192.png',
  },
};

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  maximumScale: 1,
  userScalable: false,
  themeColor: '#ea580c',
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
