'use client';

// /chat — owner chat inbox page.
// Thin shell: auth gate + render ChatClient. All data + UI state live in
// ChatClient so this file stays a one-screen overview. Mirrors the
// /pesanan/page.tsx pattern shipped with PR #637.

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { getCurrentUser, getStoredToken } from '@/lib/supabase';
import ChatClient from './ChatClient';
import '@/components/dashboard-new/dashboard.css';
import './chat.css';

export default function ChatPage() {
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

  return <ChatClient />;
}
