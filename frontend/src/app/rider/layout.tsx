// app/rider/layout.tsx - FIXED VERSION
import type { Metadata, Viewport } from 'next';

export const metadata: Metadata = {
  title: 'BinaApp Rider',
  description: 'Aplikasi penghantaran untuk rider',
  manifest: '/rider/manifest.json',
};

export const viewport: Viewport = {
  themeColor: '#ea580c',
};

export default function RiderLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}
