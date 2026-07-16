'use client';

// /dashboard/penghantar-live — owner-side live monitoring page.
// Mirrors penghantaran/page.tsx for outlet bootstrap; the live UI itself is in
// PenghantarLiveClient.

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Lock } from 'lucide-react';
import { supabase, getCurrentUser, getStoredToken } from '@/lib/supabase';
import { usePlanFeatures } from '@/hooks/usePlanFeatures';
import PenghantarLiveClient from './PenghantarLiveClient';
import type { Outlet } from './lib/types';
import './penghantar-live.css';

export default function PenghantarLivePage() {
  const router = useRouter();
  const [outlets, setOutlets] = useState<Outlet[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  // Rider/GPS ops are Bisnes-only — deep links from Permulaan get the upsell
  // panel below instead of the live map. null (unknown) renders normally;
  // the backend still enforces rider quotas either way.
  const { hasRiderFeatures } = usePlanFeatures();

  useEffect(() => {
    let cancelled = false;
    (async () => {
      if (!supabase) {
        setError('Supabase not configured');
        setLoading(false);
        return;
      }
      const token = getStoredToken();
      const user = await getCurrentUser();
      if (!token || !user) {
        router.push('/login');
        return;
      }
      const { data, error: dbErr } = await supabase
        .from('websites')
        .select('id, name, business_name, subdomain, location_address, lat, lng')
        .eq('user_id', user.id)
        .order('created_at', { ascending: false });
      if (cancelled) return;
      if (dbErr) {
        setError(dbErr.message);
        setLoading(false);
        return;
      }
      const mapped: Outlet[] = (data ?? []).map(
        (w: {
          id: string;
          name?: string | null;
          business_name?: string | null;
          subdomain?: string | null;
          location_address?: string | null;
          lat?: number | null;
          lng?: number | null;
        }) => ({
          id: w.id,
          name: w.business_name || w.name || 'Outlet',
          subdomain: w.subdomain || '',
          lat: w.lat ?? null,
          lng: w.lng ?? null,
          location_address: w.location_address ?? null,
          business_name: w.business_name ?? null,
        }),
      );
      setOutlets(mapped);
      setLoading(false);
    })();
    return () => {
      cancelled = true;
    };
  }, [router]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#0a0e1a]">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-white/40" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-[#0a0e1a] text-white p-8">
        <h1 className="text-xl font-semibold">Ralat</h1>
        <p className="mt-2 text-white/60">{error}</p>
      </div>
    );
  }

  if (hasRiderFeatures === false) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#0a0e1a] px-6">
        <div className="max-w-md text-center">
          <div className="mx-auto mb-5 grid h-14 w-14 place-items-center rounded-2xl bg-[#C7FF3D]/10 text-[#C7FF3D]">
            <Lock size={24} strokeWidth={2} />
          </div>
          <span className="rounded-full bg-[#C7FF3D]/15 px-3 py-1 text-[11px] font-bold tracking-wide text-[#C7FF3D]">
            CIRI PELAN BISNES
          </span>
          <h1 className="mt-4 text-2xl font-semibold text-white">Penghantar Live</h1>
          <p className="mt-3 text-sm leading-relaxed text-white/60">
            Pantau lokasi penghantar anda secara real-time dengan GPS tracking.
            Ciri ini termasuk dalam pelan Bisnes (RM49/bulan) — bersama 10
            rider sendiri, dashboard order, chat pelanggan, dan tiada komisen.
          </p>
          <button
            type="button"
            onClick={() => router.push('/dashboard/billing')}
            className="mt-6 rounded-xl bg-[#C7FF3D] px-6 py-3 text-sm font-bold text-[#0B0B15] transition-colors hover:bg-[#d4ff66]"
          >
            Naik taraf ke Bisnes →
          </button>
        </div>
      </div>
    );
  }

  return <PenghantarLiveClient outlets={outlets} />;
}
