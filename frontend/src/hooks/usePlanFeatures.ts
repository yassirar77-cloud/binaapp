'use client';

import { useEffect, useState } from 'react';
import { getStoredToken } from '@/lib/supabase';

const API_URL = process.env.NEXT_PUBLIC_API_URL || '';

export interface PlanFeatures {
  /**
   * Whether the user's plan includes rider/GPS delivery operations
   * (Bisnes/Pro, or grandfathered rider addon credits).
   * null = not known yet (loading, logged out, or fetch failed) — treat as
   * UNLOCKED in UIs to avoid flashing locks at paying users; the backend
   * remains the real gate.
   */
  hasRiderFeatures: boolean | null;
  /** Current plan name (e.g. 'starter', 'basic', 'pro'), null while unknown. */
  planName: string | null;
}

const UNKNOWN: PlanFeatures = { hasRiderFeatures: null, planName: null };

// Module-level cache: the dashboard header renders on many pages, and plan
// features change rarely (only via a payment round-trip that reloads the
// app), so one fetch per full page load is enough.
let cache: PlanFeatures | null = null;

export function usePlanFeatures(): PlanFeatures {
  const [features, setFeatures] = useState<PlanFeatures>(cache ?? UNKNOWN);

  useEffect(() => {
    if (cache) return;
    let cancelled = false;
    (async () => {
      try {
        const token = getStoredToken();
        if (!token) return;
        const res = await fetch(`${API_URL}/api/v1/subscription/usage`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!res.ok) return;
        const data = await res.json();
        const riders = data?.usage?.riders;
        if (!riders) return;
        const next: PlanFeatures = {
          hasRiderFeatures: Boolean(
            riders.unlimited || (riders.limit ?? 0) > 0 || (riders.addon_credits ?? 0) > 0
          ),
          planName: data?.plan?.name ?? null,
        };
        cache = next;
        if (!cancelled) setFeatures(next);
      } catch {
        // Fail open (unlocked UI) — the backend still enforces the gate.
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  return features;
}
