'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Lock, CreditCard, CheckCircle, XCircle, HelpCircle, LogOut } from 'lucide-react';
import { supabase } from '@/lib/supabase';

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
 * Full-screen overlay when subscription is LOCKED
 * Blocks entire dashboard
 * Only shows payment option
 *
 * Design:
 * - Dark overlay covering dashboard
 * - Center card with lock icon
 * - Malay text
 * - Payment button (prominent, green)
 * - Reassurance that data is safe
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
    <div
      className="fixed inset-0 z-[100] bg-gray-900/95 backdrop-blur-sm flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="lock-title"
    >
      {/* Animated background pattern */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute inset-0 opacity-5">
          <svg className="w-full h-full" xmlns="http://www.w3.org/2000/svg">
            <defs>
              <pattern id="lock-pattern" x="0" y="0" width="40" height="40" patternUnits="userSpaceOnUse">
                <path d="M0 20h40M20 0v40" stroke="white" strokeWidth="0.5" fill="none" />
              </pattern>
            </defs>
            <rect width="100%" height="100%" fill="url(#lock-pattern)" />
          </svg>
        </div>
      </div>

      {/* Main Card */}
      <div className="relative bg-white rounded-2xl shadow-2xl max-w-md w-full overflow-hidden animate-in zoom-in-95 duration-300">
        {/* Header with gradient */}
        <div className="bg-gradient-to-br from-gray-800 to-gray-900 px-6 py-8 text-center">
          <div className="inline-flex items-center justify-center w-20 h-20 bg-white/10 rounded-full mb-4 backdrop-blur">
            <Lock className="w-10 h-10 text-white" />
          </div>
          <h1
            id="lock-title"
            className="text-2xl font-bold text-white mb-2"
          >
            Akaun Anda Telah Dikunci
          </h1>
          <p className="text-gray-300 text-sm">
            {getLockReasonText()}
          </p>
        </div>

        {/* Content */}
        <div className="px-6 py-6">
          {/* Current status */}
          <div className="bg-red-50 border border-red-200 rounded-xl p-4 mb-6">
            <h2 className="font-semibold text-red-800 mb-3 flex items-center gap-2">
              <XCircle className="w-5 h-5" />
              Status Semasa
            </h2>
            <ul className="space-y-2 text-sm text-red-700">
              <li className="flex items-center gap-2">
                <span className="w-2 h-2 bg-red-500 rounded-full"></span>
                Dashboard tidak boleh diakses
              </li>
              <li className="flex items-center gap-2">
                <span className="w-2 h-2 bg-red-500 rounded-full"></span>
                Website tidak aktif untuk pelanggan
              </li>
              <li className="flex items-center gap-2">
                <span className="w-2 h-2 bg-red-500 rounded-full"></span>
                Pesanan tidak boleh diterima
              </li>
            </ul>
          </div>

          {/* Plan info */}
          <div className="bg-gray-50 rounded-xl p-4 mb-6">
            <div className="flex justify-between items-center">
              <div>
                <p className="text-sm text-gray-600">Pakej Semasa</p>
                <p className="font-semibold text-gray-900">{currentTier.name}</p>
              </div>
              <div className="text-right">
                <p className="text-sm text-gray-600">Harga</p>
                <p className="font-bold text-lg text-gray-900">
                  RM{currentTier.price}<span className="text-sm font-normal">/bulan</span>
                </p>
              </div>
            </div>
          </div>

          {/* Payment button */}
          <button
            onClick={handlePayment}
            disabled={isNavigating}
            className="w-full bg-gradient-to-r from-emerald-500 to-green-600 hover:from-emerald-600 hover:to-green-700 text-white font-bold py-4 px-6 rounded-xl flex items-center justify-center gap-3 transition-all duration-200 shadow-lg hover:shadow-xl disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <CreditCard className="w-5 h-5" />
            {isNavigating ? 'Memproses...' : 'Bayar Sekarang - Aktif Serta-merta'}
          </button>

          {/* After payment benefits */}
          <div className="mt-6 p-4 bg-green-50 border border-green-200 rounded-xl">
            <h3 className="font-semibold text-green-800 mb-3 flex items-center gap-2">
              <CheckCircle className="w-5 h-5" />
              Selepas Pembayaran
            </h3>
            <ul className="space-y-2 text-sm text-green-700">
              <li className="flex items-center gap-2">
                <span className="w-2 h-2 bg-green-500 rounded-full"></span>
                Akaun aktif semula secara automatik
              </li>
              <li className="flex items-center gap-2">
                <span className="w-2 h-2 bg-green-500 rounded-full"></span>
                Semua data anda masih selamat
              </li>
              <li className="flex items-center gap-2">
                <span className="w-2 h-2 bg-green-500 rounded-full"></span>
                Website boleh diakses semula
              </li>
            </ul>
          </div>

          {/* Reassurance */}
          <div className="mt-6 text-center">
            <p className="text-sm text-gray-500">
              Akaun dan data anda <strong>tidak</strong> dipadam.
              <br />
              Ia akan diaktifkan semula selepas pembayaran dibuat.
            </p>
          </div>

          {/* Secondary actions */}
          <div className="mt-6 flex justify-center gap-4">
            <button
              onClick={handleSupport}
              className="text-sm text-gray-600 hover:text-gray-900 flex items-center gap-1 transition-colors"
            >
              <HelpCircle className="w-4 h-4" />
              Hubungi Sokongan
            </button>
            <button
              onClick={handleLogout}
              className="text-sm text-gray-600 hover:text-gray-900 flex items-center gap-1 transition-colors"
            >
              <LogOut className="w-4 h-4" />
              Log Keluar
            </button>
          </div>
        </div>

        {/* Footer */}
        <div className="bg-gray-50 px-6 py-4 text-center border-t">
          <p className="text-xs text-gray-500">
            BinaApp - Platform Restoran Digital Malaysia
          </p>
        </div>
      </div>
    </div>
  );
}

export default SubscriptionLockOverlay;
