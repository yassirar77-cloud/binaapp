'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { AlertTriangle, CreditCard, X, Clock } from 'lucide-react';

interface SubscriptionBannerProps {
  /** Number of days remaining before lock */
  daysRemaining: number;
  /** Whether subscription is in grace period */
  isGrace?: boolean;
  /** Whether subscription is expired but not yet in grace */
  isExpired?: boolean;
  /** Subscription tier name */
  tier?: string;
  /** Custom payment URL */
  paymentUrl?: string;
  /** Callback when banner is dismissed */
  onDismiss?: () => void;
  /** Whether to allow dismissing */
  canDismiss?: boolean;
}

/**
 * Warning banner shown during GRACE or EXPIRED period
 * Sticky at top of dashboard
 * Shows: days remaining, payment button
 *
 * Design:
 * - Yellow/orange background for expired
 * - Red background for grace period
 * - Icon: Warning
 * - Text in Malay
 * - Prominent payment button
 */
export function SubscriptionBanner({
  daysRemaining,
  isGrace = false,
  isExpired = false,
  tier = 'starter',
  paymentUrl = '/dashboard/billing',
  onDismiss,
  canDismiss = false,
}: SubscriptionBannerProps) {
  const router = useRouter();
  const [dismissed, setDismissed] = useState(false);
  const [isNavigating, setIsNavigating] = useState(false);

  const handlePayment = () => {
    setIsNavigating(true);
    router.push(paymentUrl);
  };

  const handleDismiss = () => {
    setDismissed(true);
    onDismiss?.();
  };

  if (dismissed) {
    return null;
  }

  // Determine banner style based on urgency
  const isUrgent = isGrace || daysRemaining <= 1;
  const isWarning = isExpired || daysRemaining <= 3;

  const getBannerStyle = () => {
    if (isUrgent) {
      return 'bg-gradient-to-r from-red-600 to-red-700 text-white';
    }
    if (isWarning) {
      return 'bg-gradient-to-r from-orange-500 to-amber-500 text-white';
    }
    return 'bg-gradient-to-r from-amber-400 to-yellow-400 text-amber-900';
  };

  const getButtonStyle = () => {
    if (isUrgent) {
      return 'bg-white text-red-600 hover:bg-red-50';
    }
    if (isWarning) {
      return 'bg-white text-orange-600 hover:bg-orange-50';
    }
    return 'bg-amber-900 text-white hover:bg-amber-800';
  };

  const getMessage = () => {
    if (isGrace) {
      if (daysRemaining <= 0) {
        return 'Website anda akan dilocked hari ini!';
      }
      if (daysRemaining === 1) {
        return 'Website anda akan dilocked esok!';
      }
      return `Website akan dilocked dalam ${daysRemaining} hari!`;
    }

    if (isExpired) {
      return 'Langganan anda telah tamat. Sila bayar untuk elak website dilocked.';
    }

    if (daysRemaining <= 1) {
      return 'Langganan anda akan tamat esok!';
    }
    if (daysRemaining <= 3) {
      return `Langganan tamat dalam ${daysRemaining} hari!`;
    }
    return `Langganan akan tamat dalam ${daysRemaining} hari.`;
  };

  return (
    <div
      className={`sticky top-0 z-50 w-full ${getBannerStyle()} shadow-lg`}
      role="alert"
      aria-live="polite"
    >
      <div className="container mx-auto px-4 py-3">
        <div className="flex flex-col sm:flex-row items-center justify-between gap-3">
          {/* Message Section */}
          <div className="flex items-center gap-3 flex-1">
            <div className="flex-shrink-0">
              {isUrgent ? (
                <AlertTriangle className="w-6 h-6 animate-pulse" />
              ) : (
                <Clock className="w-6 h-6" />
              )}
            </div>
            <div className="flex-1">
              <p className="font-semibold text-sm sm:text-base">
                {getMessage()}
              </p>
              {isGrace && (
                <p className="text-xs sm:text-sm opacity-90 mt-0.5">
                  Selepas dilocked, dashboard dan website tidak boleh diakses.
                </p>
              )}
            </div>
          </div>

          {/* Action Section */}
          <div className="flex items-center gap-2 flex-shrink-0">
            <button
              onClick={handlePayment}
              disabled={isNavigating}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg font-semibold text-sm transition-all duration-200 ${getButtonStyle()} disabled:opacity-50 disabled:cursor-not-allowed shadow-md hover:shadow-lg`}
            >
              <CreditCard className="w-4 h-4" />
              {isNavigating ? (
                'Memproses...'
              ) : (
                <>Bayar Sekarang</>
              )}
            </button>

            {canDismiss && !isGrace && (
              <button
                onClick={handleDismiss}
                className="p-2 rounded-lg hover:bg-black/10 transition-colors"
                aria-label="Tutup"
              >
                <X className="w-5 h-5" />
              </button>
            )}
          </div>
        </div>

        {/* Progress indicator for grace period */}
        {isGrace && daysRemaining > 0 && (
          <div className="mt-2">
            <div className="h-1 bg-white/30 rounded-full overflow-hidden">
              <div
                className="h-full bg-white transition-all duration-500"
                style={{ width: `${Math.max(0, ((5 - daysRemaining) / 5) * 100)}%` }}
              />
            </div>
            <p className="text-xs mt-1 text-center opacity-75">
              Tempoh tangguh: {daysRemaining} dari 5 hari
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

export default SubscriptionBanner;
