'use client';

import React from 'react';
import { useSubscriptionStatus } from '@/hooks/useSubscriptionStatus';
import SubscriptionBanner from '@/components/subscription/SubscriptionBanner';
import SubscriptionLockOverlay from '@/components/subscription/SubscriptionLockOverlay';

interface DashboardLayoutProps {
  children: React.ReactNode;
}

/**
 * Dashboard Layout with Subscription Status Checks
 *
 * This layout wraps all dashboard pages and:
 * 1. Shows warning banner during GRACE period
 * 2. Shows lock overlay when subscription is LOCKED
 * 3. Passes through normally when subscription is ACTIVE
 */
export default function DashboardLayout({ children }: DashboardLayoutProps) {
  const {
    status,
    isLoading,
    isLocked,
    isGrace,
    isExpired,
    daysRemaining,
    graceDaysRemaining,
    tier,
    lockReason,
    paymentUrl,
    data,
  } = useSubscriptionStatus();

  // Show loading state briefly
  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50">
        {children}
      </div>
    );
  }

  // Determine which days remaining to show
  const displayDays = isGrace
    ? (graceDaysRemaining ?? 0)
    : (daysRemaining ?? 0);

  // Show banner for grace or expired status
  const showBanner = isGrace || isExpired || (daysRemaining !== null && daysRemaining <= 5);

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Subscription Lock Overlay - blocks everything when locked */}
      {isLocked && (
        <SubscriptionLockOverlay
          tier={tier}
          lockReason={lockReason}
          paymentUrl={paymentUrl}
          lockedAt={data?.locked_at}
        />
      )}

      {/* Subscription Warning Banner - shown during grace/expired */}
      {showBanner && !isLocked && (
        <SubscriptionBanner
          daysRemaining={displayDays}
          isGrace={isGrace}
          isExpired={isExpired}
          tier={tier}
          paymentUrl={paymentUrl}
          canDismiss={!isGrace && !isExpired}
        />
      )}

      {/* Dashboard Content */}
      {children}
    </div>
  );
}
