'use client';

// /pesanan — owner order management page.
// Thin shell: auth gate + render PesananClient. All data + UI state live in
// PesananClient so this file stays a one-screen overview.

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { getCurrentUser, getStoredToken } from '@/lib/supabase';
import PesananClient from './PesananClient';
import '@/components/dashboard-new/dashboard.css';
import './pesanan.css';

export default function PesananPage() {
  const router = useRouter();
  const [authed, setAuthed] = useState<boolean | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const token = getStoredToken();
      const user = await getCurrentUser();
      if (cancelled) return;
      if (!token || !user) {
        router.push('/login');
        return;
      }
      setAuthed(true);
    })();
    return () => {
      cancelled = true;
    };
  }, [router]);

  if (authed === null) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#0a0e1a]">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-white/40" />
      </div>
    );
  }

  return <PesananClient />;
}
