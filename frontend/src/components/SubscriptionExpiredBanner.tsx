'use client';

import React, { useState, useEffect } from 'react';
import { getStoredToken } from '@/lib/supabase';
import './SubscriptionExpiredBanner.css';

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
        alert('Sila log masuk semula');
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
        alert('Ralat: ' + (data.detail || 'Gagal mencipta pembayaran'));
      }
    } catch (error) {
      console.error('Renew error:', error);
      alert('Ralat semasa memproses pembaharuan');
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

  if (isExpired) {
    return (
      <div className="subscription-banner expired">
        <div className="banner-content">
          <div className="banner-icon">!</div>
          <div className="banner-text">
            <h3>Langganan Anda Telah Tamat</h3>
            <p>
              Perkhidmatan anda telah digantung. Perbaharui sekarang untuk meneruskan penggunaan BinaApp.
            </p>
          </div>
        </div>
        <div className="banner-actions">
          <button
            className="renew-btn"
            onClick={handleRenew}
            disabled={renewLoading}
          >
            {renewLoading ? 'Memproses...' : `Perbaharui Langganan (RM${price})`}
          </button>
        </div>
      </div>
    );
  }

  // Expiring soon banner
  return (
    <div className="subscription-banner warning">
      <div className="banner-content">
        <div className="banner-icon">&#9888;</div>
        <div className="banner-text">
          <h3>Langganan Akan Tamat</h3>
          <p>
            Pelan {status.plan_name.toUpperCase()} anda akan tamat dalam{' '}
            <strong>{status.days_remaining} hari</strong>. Perbaharui sekarang untuk mengelakkan
            gangguan perkhidmatan.
          </p>
        </div>
      </div>
      <div className="banner-actions">
        <button
          className="renew-btn"
          onClick={handleRenew}
          disabled={renewLoading}
        >
          {renewLoading ? 'Memproses...' : `Perbaharui Sekarang (RM${price})`}
        </button>
        <button
          className="dismiss-btn"
          onClick={() => setDismissed(true)}
        >
          Tutup
        </button>
      </div>
    </div>
  );
}

export default SubscriptionExpiredBanner;
