import type { Metadata, Viewport } from 'next';

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
  return children;
}
