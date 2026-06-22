'use client';

import React, { useCallback, useEffect, useState } from 'react';
import { getStoredToken } from '@/lib/supabase';
import SectionHeader from './SectionHeader';

const API_URL = process.env.NEXT_PUBLIC_API_URL || '';

interface PromoStatus {
  active: boolean;
  remaining: number;
  max: number;
  used?: number;
  already_redeemed: boolean;
}

interface Props {
  /** Called after a successful redemption so the parent can refresh billing data. */
  onRedeemed?: () => void;
}

function formatDateBM(iso: string) {
  try {
    return new Date(iso).toLocaleDateString('ms-MY', {
      day: 'numeric',
      month: 'long',
      year: 'numeric',
    });
  } catch {
    return iso;
  }
}

/**
 * Promo code redemption card for the billing page.
 *
 * Fetches promo availability on mount and hides itself entirely when the promo
 * is inactive or the user already redeemed. On "promo full" it shows a clear
 * message and points the user at the normal plans below (graceful fallback to
 * ToyyibPay checkout — the PlanCards section is always rendered on this page).
 */
export default function PromoCodeCard({ onRedeemed }: Props) {
  const [status, setStatus] = useState<PromoStatus | null>(null);
  const [loaded, setLoaded] = useState(false);
  const [code, setCode] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [success, setSuccess] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [promoFull, setPromoFull] = useState(false);

  const fetchStatus = useCallback(async () => {
    try {
      const token = getStoredToken();
      if (!token) {
        setLoaded(true);
        return;
      }
      const res = await fetch(`${API_URL}/api/v1/subscription/promo/status`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data: PromoStatus = await res.json();
        setStatus(data);
        if (data.remaining <= 0) setPromoFull(true);
      }
    } catch (e) {
      console.error('Error fetching promo status:', e);
    } finally {
      setLoaded(true);
    }
  }, []);

  useEffect(() => {
    fetchStatus();
  }, [fetchStatus]);

  const handleSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      if (submitting || !code.trim()) return;
      setSubmitting(true);
      setError(null);
      setSuccess(null);
      try {
        const token = getStoredToken();
        const res = await fetch(`${API_URL}/api/v1/subscription/redeem-promo`, {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ code: code.trim() }),
        });
        const data = await res.json();
        if (data.success) {
          setSuccess(
            data.expires_at
              ? `Starter percuma sehingga ${formatDateBM(data.expires_at)}`
              : data.message || 'Berjaya!'
          );
          setCode('');
          onRedeemed?.();
        } else {
          if (data.reason === 'promo_full') setPromoFull(true);
          setError(data.message || 'Kod promosi tidak sah.');
        }
      } catch (err) {
        console.error('Promo redeem error:', err);
        setError('Ralat semasa menebus kod. Sila cuba lagi.');
      } finally {
        setSubmitting(false);
      }
    },
    [code, submitting, onRedeemed]
  );

  // Hide the whole card when there's nothing to show: not loaded yet, promo
  // inactive, or the user already redeemed (their plan is shown in the banner).
  if (!loaded || !status || !status.active || status.already_redeemed) {
    return null;
  }

  return (
    <div className="rounded-xl2 border border-ink-100 bg-white p-6 shadow-card sm:p-7">
      <SectionHeader
        eyebrow="Promosi Pelancaran"
        title="Tebus Kod Promosi"
        sub="20 pengguna pertama dapat pelan Starter PERCUMA selama 1 bulan."
        right={
          !promoFull && status.remaining > 0 ? (
            <span className="rounded-full bg-brand-50 px-3 py-1 font-geist-mono text-[11px] font-semibold uppercase tracking-[0.1em] text-brand-600">
              {status.remaining} slot lagi
            </span>
          ) : undefined
        }
      />

      {success ? (
        <div
          role="status"
          className="rounded-xl bg-ok-500 px-5 py-4 text-sm font-medium text-white"
        >
          ✓ {success}
        </div>
      ) : promoFull ? (
        <div className="rounded-xl bg-ink-050 px-5 py-4 text-[13px] text-ink-600">
          Maaf, semua slot promosi telah ditebus. Anda masih boleh melanggan pelan
          Starter seperti biasa di bahagian <span className="font-semibold">Pelan</span> di bawah.
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="flex flex-col gap-3 sm:flex-row">
          <input
            type="text"
            value={code}
            onChange={(e) => setCode(e.target.value.toUpperCase())}
            placeholder="Masukkan kod promosi"
            autoCapitalize="characters"
            spellCheck={false}
            className="flex-1 rounded-xl border border-ink-200 bg-white px-4 py-3 text-sm font-medium uppercase tracking-[0.06em] text-ink-900 outline-none transition focus:border-brand-500 focus:ring-2 focus:ring-brand-500/20"
            disabled={submitting}
          />
          <button
            type="submit"
            disabled={submitting || !code.trim()}
            className="rounded-xl bg-ink-900 px-6 py-3 text-sm font-semibold text-white transition hover:bg-ink-800 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {submitting ? 'Menebus…' : 'Tebus'}
          </button>
        </form>
      )}

      {error && !success && (
        <p className="mt-3 text-[13px] font-medium text-err-500">{error}</p>
      )}
    </div>
  );
}
