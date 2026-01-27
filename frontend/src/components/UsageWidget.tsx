'use client';

import React, { useState, useEffect } from 'react';
import { getCurrentUser, getStoredToken } from '@/lib/supabase';
import './UsageWidget.css';

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

interface UsageResponse {
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

interface UsageWidgetProps {
  onUpgradeClick?: () => void;
  onRenewClick?: () => void;
  compact?: boolean;
}

const UsageBar: React.FC<{
  label: string;
  used: number;
  limit: number | null;
  unlimited: boolean;
  blocked?: boolean;
  addonCredits?: number;
}> = ({ label, used, limit, unlimited, blocked, addonCredits }) => {
  const percentage = unlimited || limit === null
    ? 0
    : Math.min(100, (used / (limit + (addonCredits || 0))) * 100);

  const getBarColor = () => {
    if (blocked) return '#6b7280';
    if (percentage >= 100) return '#ef4444';
    if (percentage >= 80) return '#f59e0b';
    return '#10b981';
  };

  const getLimitText = () => {
    if (blocked) return 'Tidak tersedia';
    if (unlimited) return 'Tanpa had';
    if (addonCredits && addonCredits > 0) {
      return `${used} / ${limit} (+${addonCredits} addon)`;
    }
    return `${used} / ${limit}`;
  };

  return (
    <div className="usage-bar-container">
      <div className="usage-bar-header">
        <span className="usage-label">{label}</span>
        <span className="usage-value">{getLimitText()}</span>
      </div>
      <div className="usage-bar-track">
        <div
          className="usage-bar-fill"
          style={{
            width: blocked ? '0%' : unlimited ? '0%' : `${percentage}%`,
            backgroundColor: getBarColor()
          }}
        />
      </div>
    </div>
  );
};

export function UsageWidget({ onUpgradeClick, onRenewClick, compact = false }: UsageWidgetProps) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<UsageResponse | null>(null);

  useEffect(() => {
    fetchUsageData();
  }, []);

  const fetchUsageData = async () => {
    try {
      setLoading(true);
      setError(null);

      const token = getStoredToken();
      if (!token) {
        setError('Sila log masuk untuk melihat penggunaan');
        setLoading(false);
        return;
      }

      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || ''}/api/v1/subscription/usage`,
        {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          }
        }
      );

      if (!response.ok) {
        throw new Error('Gagal mendapatkan data penggunaan');
      }

      const usageData = await response.json();
      setData(usageData);
    } catch (err) {
      console.error('Error fetching usage:', err);
      setError(err instanceof Error ? err.message : 'Ralat tidak diketahui');
    } finally {
      setLoading(false);
    }
  };

  const getPlanBadgeClass = () => {
    if (!data) return 'plan-badge-starter';
    switch (data.plan.name) {
      case 'pro': return 'plan-badge-pro';
      case 'basic': return 'plan-badge-basic';
      default: return 'plan-badge-starter';
    }
  };

  const formatEndDate = (dateStr: string | null) => {
    if (!dateStr) return '-';
    const date = new Date(dateStr);
    return date.toLocaleDateString('ms-MY', {
      day: 'numeric',
      month: 'short',
      year: 'numeric'
    });
  };

  if (loading) {
    return (
      <div className={`usage-widget ${compact ? 'compact' : ''}`}>
        <div className="usage-loading">
          <div className="loading-spinner" />
          <span>Memuatkan...</span>
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className={`usage-widget ${compact ? 'compact' : ''}`}>
        <div className="usage-error">
          <p>{error || 'Gagal memuatkan data'}</p>
          <button onClick={fetchUsageData}>Cuba lagi</button>
        </div>
      </div>
    );
  }

  const { plan, usage } = data;

  return (
    <div className={`usage-widget ${compact ? 'compact' : ''}`}>
      <div className="usage-header">
        <h3>Penggunaan Anda</h3>
        <span className={`plan-badge ${getPlanBadgeClass()}`}>
          {plan.name.toUpperCase()}
        </span>
      </div>

      {plan.is_expired && (
        <div className="expired-alert">
          <span className="alert-icon">!</span>
          <span>Langganan tamat</span>
        </div>
      )}

      <div className="usage-items">
        <UsageBar
          label="Laman Web"
          used={usage.websites.used}
          limit={usage.websites.limit}
          unlimited={usage.websites.unlimited}
          addonCredits={usage.websites.addon_credits}
        />
        <UsageBar
          label="Item Menu"
          used={usage.menu_items.used}
          limit={usage.menu_items.limit}
          unlimited={usage.menu_items.unlimited}
        />
        <UsageBar
          label="AI Hero"
          used={usage.ai_hero.used}
          limit={usage.ai_hero.limit}
          unlimited={usage.ai_hero.unlimited}
          addonCredits={usage.ai_hero.addon_credits}
        />
        <UsageBar
          label="Imej AI"
          used={usage.ai_images.used}
          limit={usage.ai_images.limit}
          unlimited={usage.ai_images.unlimited}
          addonCredits={usage.ai_images.addon_credits}
        />
        <UsageBar
          label="Zon Penghantaran"
          used={usage.delivery_zones.used}
          limit={usage.delivery_zones.limit}
          unlimited={usage.delivery_zones.unlimited}
          addonCredits={usage.delivery_zones.addon_credits}
        />
        <UsageBar
          label="Rider"
          used={usage.riders.used}
          limit={usage.riders.limit}
          unlimited={usage.riders.unlimited}
          blocked={usage.riders.limit === 0}
          addonCredits={usage.riders.addon_credits}
        />
      </div>

      {!compact && (
        <div className="subscription-info">
          {plan.end_date && (
            <>
              <p className="expiry-date">
                Tamat: <strong>{formatEndDate(plan.end_date)}</strong>
              </p>
              {!plan.is_expired && plan.days_remaining <= 7 && (
                <p className="days-warning">
                  {plan.days_remaining} hari lagi
                </p>
              )}
            </>
          )}
        </div>
      )}

      <div className="action-buttons">
        {plan.is_expired ? (
          <button
            className="btn-renew"
            onClick={onRenewClick}
          >
            Perbaharui Sekarang
          </button>
        ) : (
          <>
            {plan.name !== 'pro' && (
              <button
                className="btn-upgrade"
                onClick={onUpgradeClick}
              >
                Naik Taraf
              </button>
            )}
            {plan.days_remaining <= 7 && (
              <button
                className="btn-renew-secondary"
                onClick={onRenewClick}
              >
                Perbaharui
              </button>
            )}
          </>
        )}
      </div>
    </div>
  );
}

export default UsageWidget;
