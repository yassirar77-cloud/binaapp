'use client';

import { useState, useEffect, useCallback } from 'react';
import { getStoredToken } from '@/lib/supabase';

/**
 * Subscription Status Types
 */
export type SubscriptionStatusType = 'active' | 'expired' | 'grace' | 'locked' | 'cancelled' | 'pending';

export interface SubscriptionStatusData {
  subscription_id?: string;
  user_id?: string;
  status: SubscriptionStatusType;
  tier: string;
  end_date: string | null;
  grace_period_end: string | null;
  locked_at: string | null;
  lock_reason: string | null;
  is_locked: boolean;
  is_grace: boolean;
  is_expired: boolean;
  days_remaining: number | null;
  grace_days_remaining: number | null;
  can_use_dashboard: boolean;
  can_use_website: boolean;
  payment_url: string;
  status_message?: string;
  status_message_en?: string;
  urgency?: 'none' | 'low' | 'medium' | 'high' | 'critical';
  error?: string;
}

interface UseSubscriptionStatusReturn {
  status: SubscriptionStatusType;
  data: SubscriptionStatusData | null;
  isLoading: boolean;
  isLocked: boolean;
  isGrace: boolean;
  isExpired: boolean;
  isActive: boolean;
  daysRemaining: number | null;
  graceDaysRemaining: number | null;
  canUseDashboard: boolean;
  tier: string;
  lockReason: string | null;
  paymentUrl: string;
  error: string | null;
  refetch: () => Promise<void>;
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || '';

/**
 * Hook to fetch and cache subscription status
 * Specifically designed for checking lock status and displaying warnings
 *
 * @returns Subscription status data and helper flags
 */
export function useSubscriptionStatus(): UseSubscriptionStatusReturn {
  const [data, setData] = useState<SubscriptionStatusData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchStatus = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);

      const token = getStoredToken();
      if (!token) {
        // Not authenticated - treat as active (will be redirected by auth)
        setData({
          status: 'active',
          tier: 'starter',
          end_date: null,
          grace_period_end: null,
          locked_at: null,
          lock_reason: null,
          is_locked: false,
          is_grace: false,
          is_expired: false,
          days_remaining: null,
          grace_days_remaining: null,
          can_use_dashboard: true,
          can_use_website: true,
          payment_url: '/dashboard/billing',
        });
        setIsLoading(false);
        return;
      }

      const response = await fetch(`${API_URL}/api/v1/subscription/status`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });

      if (!response.ok) {
        // Handle 403 (locked) specifically
        if (response.status === 403) {
          const errorData = await response.json();
          setData({
            status: 'locked',
            tier: errorData.tier || 'starter',
            end_date: null,
            grace_period_end: null,
            locked_at: errorData.locked_at || null,
            lock_reason: errorData.lock_reason || 'subscription_expired',
            is_locked: true,
            is_grace: false,
            is_expired: true,
            days_remaining: 0,
            grace_days_remaining: 0,
            can_use_dashboard: false,
            can_use_website: false,
            payment_url: errorData.payment_url || '/dashboard/billing',
          });
          setIsLoading(false);
          return;
        }

        throw new Error('Failed to fetch subscription status');
      }

      const statusData: SubscriptionStatusData = await response.json();
      setData(statusData);
    } catch (err) {
      console.error('Error fetching subscription status:', err);
      setError(err instanceof Error ? err.message : 'Unknown error');

      // On error, assume active to not block user
      setData({
        status: 'active',
        tier: 'starter',
        end_date: null,
        grace_period_end: null,
        locked_at: null,
        lock_reason: null,
        is_locked: false,
        is_grace: false,
        is_expired: false,
        days_remaining: null,
        grace_days_remaining: null,
        can_use_dashboard: true,
        can_use_website: true,
        payment_url: '/dashboard/billing',
        error: err instanceof Error ? err.message : 'Unknown error',
      });
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchStatus();

    // Refetch every 5 minutes to keep status current
    const interval = setInterval(fetchStatus, 5 * 60 * 1000);
    return () => clearInterval(interval);
  }, [fetchStatus]);

  // Derived values
  const status = data?.status || 'active';
  const isLocked = data?.is_locked || status === 'locked';
  const isGrace = data?.is_grace || status === 'grace';
  const isExpired = data?.is_expired || status === 'expired';
  const isActive = status === 'active' && !isLocked && !isGrace && !isExpired;

  return {
    status,
    data,
    isLoading,
    isLocked,
    isGrace,
    isExpired,
    isActive,
    daysRemaining: data?.days_remaining ?? null,
    graceDaysRemaining: data?.grace_days_remaining ?? null,
    canUseDashboard: data?.can_use_dashboard ?? true,
    tier: data?.tier || 'starter',
    lockReason: data?.lock_reason ?? null,
    paymentUrl: data?.payment_url || '/dashboard/billing',
    error,
    refetch: fetchStatus,
  };
}

export default useSubscriptionStatus;
