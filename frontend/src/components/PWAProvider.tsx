'use client';

import { useEffect } from 'react';
import { registerServiceWorker } from '@/lib/registerSW';
import InstallPrompt from './InstallPrompt';

interface PWAProviderProps {
  children: React.ReactNode;
}

export default function PWAProvider({ children }: PWAProviderProps) {
  useEffect(() => {
    registerServiceWorker();
  }, []);

  return (
    <>
      {children}
      <InstallPrompt />
    </>
  );
}
