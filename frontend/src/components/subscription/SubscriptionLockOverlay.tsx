'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Lock, CreditCard, CheckCircle, XCircle, HelpCircle, LogOut } from 'lucide-react';
import { supabase } from '@/lib/supabase';
import { AppModal } from '@/components/ui/AppModal';

interface SubscriptionLockOverlayProps {
  /** Subscription tier name */
  tier?: string;
  /** Reason for lock */
  lockReason?: string | null;
  /** Custom payment URL */
  paymentUrl?: string;
  /** When the lock occurred */
  lockedAt?: string | null;
}

/**
 * Full-screen overlay when subscription is LOCKED.
 * Blocks the entire dashboard until payment is made.
 *
 * Rehoused into the shared AppModal (dark-navy + lime) so it matches the rest
 * of BinaApp's popups. Wording unchanged. Backend/payment logic untouched.
 */
export function SubscriptionLockOverlay({
  tier = 'starter',
  lockReason,
  paymentUrl = '/dashboard/billing',
  lockedAt,
}: SubscriptionLockOverlayProps) {
  const router = useRouter();
  const [isNavigating, setIsNavigating] = useState(false);

  const handlePayment = () => {
    setIsNavigating(true);
    router.push(paymentUrl);
  };

  const handleLogout = async () => {
    if (supabase) {
      await supabase.auth.signOut();
    }
    router.push('/');
  };

  const handleSupport = () => {
    window.location.href = 'mailto:support@binaapp.com?subject=Bantuan%20Akaun%20Dikunci';
  };

  // Get tier display name and price
  const tierInfo: Record<string, { name: string; price: number }> = {
    starter: { name: 'Starter', price: 5 },
    basic: { name: 'Basic', price: 29 },
    pro: { name: 'Pro', price: 49 },
  };

  const currentTier = tierInfo[tier] || tierInfo.starter;

  // Get lock reason text
  const getLockReasonText = () => {
    switch (lockReason) {
      case 'subscription_expired':
        return 'Langganan anda telah tamat tempoh';
      case 'payment_failed':
        return 'Pembayaran gagal diproses';
      case 'subscription_locked':
        return 'Langganan tidak aktif';
      default:
        return 'Langganan anda telah tamat';
    }
  };

  return (
    <AppModal
      open
      onClose={() => {}}
      staticOverlay
      variant="error"
      icon={<Lock className="h-6 w-6 text-err-400" />}
      title="Akaun Anda Telah Dikunci"
      description={getLockReasonText()}
    >
      {/* Current status */}
      <div className="rounded-2xl border border-err-400/20 bg-err-400/5 p-4">
        <h2 className="flex items-center gap-2 font-semibold text-err-400">
          <XCircle className="h-5 w-5" />
          Status Semasa
        </h2>
        <ul className="mt-3 space-y-2 text-sm text-white/70">
          <li className="flex items-center gap-2">
            <span className="h-1.5 w-1.5 rounded-full bg-err-400" />
            Dashboard tidak boleh diakses
          </li>
          <li className="flex items-center gap-2">
            <span className="h-1.5 w-1.5 rounded-full bg-err-400" />
            Website tidak aktif untuk pelanggan
          </li>
          <li className="flex items-center gap-2">
            <span className="h-1.5 w-1.5 rounded-full bg-err-400" />
            Pesanan tidak boleh diterima
          </li>
        </ul>
      </div>

      {/* Plan info */}
      <div className="mt-4 flex items-center justify-between rounded-2xl border border-white/[0.08] bg-white/[0.02] p-4">
        <div>
          <p className="text-sm text-white/50">Pakej Semasa</p>
          <p className="font-semibold text-white">{currentTier.name}</p>
        </div>
        <div className="text-right">
          <p className="text-sm text-white/50">Harga</p>
          <p className="text-lg font-bold text-white">
            RM{currentTier.price}
            <span className="text-sm font-normal text-white/50">/bulan</span>
          </p>
        </div>
      </div>

      {/* Payment button */}
      <button
        onClick={handlePayment}
        disabled={isNavigating}
        className="mt-5 inline-flex h-12 w-full items-center justify-center gap-3 rounded-xl bg-volt-400 px-6 text-sm font-semibold text-ink-900 transition-all hover:bg-volt-300 active:scale-[0.98] disabled:opacity-60 disabled:cursor-not-allowed"
      >
        <CreditCard className="h-5 w-5" />
        {isNavigating ? 'Memproses...' : 'Bayar Sekarang - Aktif Serta-merta'}
      </button>

      {/* After payment benefits */}
      <div className="mt-5 rounded-2xl border border-ok-400/20 bg-ok-400/5 p-4">
        <h3 className="flex items-center gap-2 font-semibold text-ok-400">
          <CheckCircle className="h-5 w-5" />
          Selepas Pembayaran
        </h3>
        <ul className="mt-3 space-y-2 text-sm text-white/70">
          <li className="flex items-center gap-2">
            <span className="h-1.5 w-1.5 rounded-full bg-ok-400" />
            Akaun aktif semula secara automatik
          </li>
          <li className="flex items-center gap-2">
            <span className="h-1.5 w-1.5 rounded-full bg-ok-400" />
            Semua data anda masih selamat
          </li>
          <li className="flex items-center gap-2">
            <span className="h-1.5 w-1.5 rounded-full bg-ok-400" />
            Website boleh diakses semula
          </li>
        </ul>
      </div>

      {/* Reassurance */}
      <p className="mt-5 text-center text-sm text-white/50">
        Akaun dan data anda <strong className="text-white/70">tidak</strong> dipadam.
        <br />
        Ia akan diaktifkan semula selepas pembayaran dibuat.
      </p>

      {/* Secondary actions */}
      <div className="mt-5 flex justify-center gap-4">
        <button
          onClick={handleSupport}
          className="flex items-center gap-1 text-sm text-white/50 transition-colors hover:text-white"
        >
          <HelpCircle className="h-4 w-4" />
          Hubungi Sokongan
        </button>
        <button
          onClick={handleLogout}
          className="flex items-center gap-1 text-sm text-white/50 transition-colors hover:text-white"
        >
          <LogOut className="h-4 w-4" />
          Log Keluar
        </button>
      </div>

      {/* Footer */}
      <p className="mt-5 border-t border-white/[0.06] pt-4 text-center text-xs text-white/40">
        BinaApp - Platform Restoran Digital Malaysia
      </p>
    </AppModal>
  );
}

export default SubscriptionLockOverlay;
