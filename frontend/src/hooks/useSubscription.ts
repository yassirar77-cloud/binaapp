'use client';

import { useState, useEffect, useCallback } from 'react';
import { getStoredToken } from '@/lib/supabase';

interface UsageData {
  used: number;
  limit: number | null;
  percentage: number;
  unlimited: boolean;
  addon_credits: number;
}

interface PlanData {
  name: string;
  status: string;
  days_remaining: number;
  end_date: string | null;
  is_expired: boolean;
}

interface SubscriptionUsage {
  plan: PlanData;
  usage: {
    websites: UsageData;
    menu_items: UsageData;
    ai_hero: UsageData;
    ai_images: UsageData;
    delivery_zones: UsageData;
    riders: UsageData;
  };
  addon_prices: Record<string, number>;
}

interface LimitCheckResult {
  allowed: boolean;
  current_usage?: number;
  limit?: number | null;
  unlimited?: boolean;
  using_addon?: boolean;
  addon_credits?: number;
  can_buy_addon?: boolean;
  addon_type?: string;
  addon_price?: number;
  message?: string;
  requires_renewal?: boolean;
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || '';

export function useSubscription() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [usage, setUsage] = useState<SubscriptionUsage | null>(null);

  const fetchUsage = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const token = getStoredToken();
      if (!token) {
        setError('Not authenticated');
        setLoading(false);
        return;
      }

      const response = await fetch(`${API_URL}/api/v1/subscription/usage`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });

      if (!response.ok) {
        throw new Error('Failed to fetch usage data');
      }

      const data = await response.json();
      setUsage(data);
    } catch (err) {
      console.error('Error fetching subscription usage:', err);
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchUsage();
  }, [fetchUsage]);

  const checkLimit = useCallback(async (action: string): Promise<LimitCheckResult> => {
    try {
      const token = getStoredToken();
      if (!token) {
        return {
          allowed: false,
          message: 'Sila log masuk semula'
        };
      }

      const response = await fetch(`${API_URL}/api/v1/subscription/check-limit`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ action })
      });

      if (!response.ok) {
        const errorData = await response.json();
        return {
          allowed: false,
          message: errorData.detail?.message || errorData.detail || 'Gagal menyemak had'
        };
      }

      return await response.json();
    } catch (err) {
      console.error('Error checking limit:', err);
      return {
        allowed: false,
        message: 'Ralat semasa menyemak had'
      };
    }
  }, []);

  const isExpired = usage?.plan?.is_expired || usage?.plan?.status === 'expired';
  const isExpiringSoon = !isExpired && (usage?.plan?.days_remaining || 0) <= 7;

  return {
    loading,
    error,
    usage,
    plan: usage?.plan,
    isExpired,
    isExpiringSoon,
    refreshUsage: fetchUsage,
    checkLimit
  };
}

export function useCheckLimit(action: string) {
  const [checking, setChecking] = useState(false);
  const [result, setResult] = useState<LimitCheckResult | null>(null);

  const check = useCallback(async (): Promise<LimitCheckResult> => {
    setChecking(true);
    try {
      const token = getStoredToken();
      if (!token) {
        const res: LimitCheckResult = {
          allowed: false,
          message: 'Sila log masuk semula'
        };
        setResult(res);
        return res;
      }

      const response = await fetch(`${API_URL}/api/v1/subscription/check-limit`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ action })
      });

      const data = await response.json();

      if (!response.ok) {
        const res: LimitCheckResult = {
          allowed: false,
          ...data.detail
        };
        setResult(res);
        return res;
      }

      setResult(data);
      return data;
    } catch (err) {
      console.error('Error checking limit:', err);
      const res: LimitCheckResult = {
        allowed: false,
        message: 'Ralat semasa menyemak had'
      };
      setResult(res);
      return res;
    } finally {
      setChecking(false);
    }
  }, [action]);

  return {
    checking,
    result,
    check
  };
}

export default useSubscription;
