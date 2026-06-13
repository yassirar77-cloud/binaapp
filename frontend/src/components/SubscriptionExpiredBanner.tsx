'use client';

import React, { useState, useEffect } from 'react';
import toast from 'react-hot-toast';
import { getStoredToken } from '@/lib/supabase';

interface SubscriptionStatus {
  plan_name: string;
  status: string;
  days_remaining: number;
  end_date: string | null;
  is_expired: boolean;
  auto_renew?: boolean;
}

interface SubscriptionExpiredBannerProps {
  onRenewClick?: () => void;
}

export function SubscriptionExpiredBanner({ onRenewClick }: SubscriptionExpiredBannerProps) {
  const [status, setStatus] = useState<SubscriptionStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [renewLoading, setRenewLoading] = useState(false);
  const [dismissed, setDismissed] = useState(false);

  useEffect(() => {
    checkSubscriptionStatus();
  }, []);

  const checkSubscriptionStatus = async () => {
    try {
      const token = getStoredToken();
      if (!token) {
        setLoading(false);
        return;
      }

      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || ''}/api/v1/subscription/status`,
        {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          }
        }
      );

      if (response.ok) {
        const data = await response.json();
        setStatus(data);
      }
    } catch (error) {
      console.error('Error checking subscription status:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleRenew = async () => {
    if (onRenewClick) {
      onRenewClick();
      return;
    }

    setRenewLoading(true);
    try {
      const token = getStoredToken();
      if (!token) {
        toast.error('Sila log masuk semula');
        setRenewLoading(false);
        return;
      }

      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || ''}/api/v1/subscription/renew`,
        {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          }
        }
      );

      const data = await response.json();

      if (data.success && data.payment_url) {
        localStorage.setItem('pending_renewal', 'true');
        window.location.href = data.payment_url;
      } else {
        toast.error('Ralat: ' + (data.detail || 'Gagal mencipta pembayaran'));
      }
    } catch (error) {
      console.error('Renew error:', error);
      toast.error('Ralat semasa memproses pembaharuan');
    } finally {
      setRenewLoading(false);
    }
  };

  // Don't show if loading, no status, or dismissed
  if (loading || !status || dismissed) {
    return null;
  }

  // Active subscription with auto-renew: don't show expiry warnings
  // (subscription will renew automatically at end of billing cycle)
  const isActiveAutoRenew = (status.status === 'active' || status.status === 'aktif') && status.auto_renew;

  // Determine which banner to show
  const isExpired = status.is_expired || status.status === 'expired' || status.status === 'suspended';
  const isExpiringSoon = !isExpired && !isActiveAutoRenew && status.days_remaining <= 7;

  // Don't show if not expired and not expiring soon
  if (!isExpired && !isExpiringSoon) {
    return null;
  }

  const prices: Record<string, number> = {
    starter: 5,
    basic: 29,
    pro: 49
  };

  const price = prices[status.plan_name] || 5;

  return (
    <div
      className={`flex flex-col gap-3 border-b px-4 py-3 sm:flex-row sm:items-center sm:justify-between ${
        isExpired
          ? 'border-err-400/20 bg-err-400/[0.08]'
          : 'border-warn-400/20 bg-warn-400/[0.08]'
      }`}
    >
      <div className="flex items-start gap-3">
        <div
          className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-base font-bold ${
            isExpired ? 'bg-err-400/15 text-err-400' : 'bg-warn-400/15 text-warn-400'
          }`}
          aria-hidden
        >
          {isExpired ? '!' : '⚠'}
        </div>
        <div>
          <h3 className="text-sm font-semibold text-white">
            {isExpired ? 'Langganan Anda Telah Tamat' : 'Langganan Akan Tamat'}
          </h3>
          <p className="mt-0.5 text-sm text-white/60">
            {isExpired ? (
              'Perkhidmatan anda telah digantung. Perbaharui sekarang untuk meneruskan penggunaan BinaApp.'
            ) : (
              <>
                Pelan {status.plan_name.toUpperCase()} anda akan tamat dalam{' '}
                <strong className="text-white">{status.days_remaining} hari</strong>. Perbaharui
                sekarang untuk mengelakkan gangguan perkhidmatan.
              </>
            )}
          </p>
        </div>
      </div>

      <div className="flex shrink-0 items-center gap-2 pl-11 sm:pl-0">
        <button
          onClick={handleRenew}
          disabled={renewLoading}
          className="inline-flex h-9 items-center justify-center rounded-xl bg-volt-400 px-4 text-sm font-semibold text-ink-900 transition-all hover:bg-volt-300 active:scale-[0.98] disabled:opacity-60"
        >
          {renewLoading
            ? 'Memproses...'
            : isExpired
            ? `Perbaharui Langganan (RM${price})`
            : `Perbaharui Sekarang (RM${price})`}
        </button>
        {!isExpired && (
          <button
            onClick={() => setDismissed(true)}
            className="inline-flex h-9 items-center justify-center rounded-xl border border-white/[0.12] bg-white/[0.04] px-4 text-sm font-medium text-white/70 transition-colors hover:bg-white/[0.08] hover:text-white"
          >
            Tutup
          </button>
        )}
      </div>
    </div>
  );
}

export default SubscriptionExpiredBanner;
