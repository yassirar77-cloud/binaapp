'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { supabase, getCurrentUser, getStoredToken } from '@/lib/supabase';
import PenghantaranClient from './PenghantaranClient';
import type { Outlet } from './lib/types';

export default function PenghantaranPage() {
  const router = useRouter();
  const [outlets, setOutlets] = useState<Outlet[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

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
      const mapped: Outlet[] = (data ?? []).map((w: { id: string; name?: string | null; business_name?: string | null; subdomain?: string | null; location_address?: string | null; lat?: number | null; lng?: number | null }) => ({
        id: w.id,
        name: w.business_name || w.name || 'Outlet',
        subdomain: w.subdomain || '',
        lat: w.lat ?? null,
        lng: w.lng ?? null,
        location_address: w.location_address ?? null,
        business_name: w.business_name ?? null,
      }));
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

  return <PenghantaranClient outlets={outlets} />;
}
