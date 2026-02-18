'use client';

import React, { useState, useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { getStoredToken, backupAuthState } from '@/lib/supabase';
import { UsageWidget } from '@/components/UsageWidget';
import './billing.css';

// Mobile collapsible usage section
function MobileUsageSection({
  onUpgradeClick,
  onRenewClick
}: {
  onUpgradeClick: () => void;
  onRenewClick: () => void;
}) {
  const [isExpanded, setIsExpanded] = useState(false);

  return (
    <div className="mobile-usage-section">
      <button
        className="mobile-usage-toggle"
        onClick={() => setIsExpanded(!isExpanded)}
        aria-expanded={isExpanded}
      >
        <span className="toggle-icon">{isExpanded ? '▼' : '▶'}</span>
        <span className="toggle-text">Penggunaan Anda</span>
        <span className="toggle-hint">{isExpanded ? 'Tutup' : 'Lihat'}</span>
      </button>
      {isExpanded && (
        <div className="mobile-usage-content">
          <UsageWidget
            onUpgradeClick={onUpgradeClick}
            onRenewClick={onRenewClick}
            compact={true}
          />
        </div>
      )}
    </div>
  );
}

interface Plan {
  plan_name: string;
  display_name: string;
  price: number;
  websites_limit: number | null;
  menu_items_limit: number | null;
  ai_hero_limit: number | null;
  ai_images_limit: number | null;
  delivery_zones_limit: number | null;
  riders_limit: number | null;
  feature_list: string[];
}

interface SubscriptionStatus {
  plan_name: string;
  status: string;
  days_remaining: number;
  end_date: string | null;
  is_expired: boolean;
}

interface Addon {
  type: string;
  name: string;
  description: string;
  price: number;
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || '';

export default function BillingPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [loading, setLoading] = useState(true);
  const [plans, setPlans] = useState<Plan[]>([]);
  const [addons, setAddons] = useState<Addon[]>([]);
  const [subscription, setSubscription] = useState<SubscriptionStatus | null>(null);
  const [processing, setProcessing] = useState(false);
  const [activeTab, setActiveTab] = useState<'plans' | 'addons' | 'history'>('plans');
  const [paymentMessage, setPaymentMessage] = useState<string | null>(null);

  useEffect(() => {
    fetchData();

    // Check if returning from payment
    const paymentStatus = searchParams.get('payment');
    if (paymentStatus === 'success') {
      setPaymentMessage('Pembayaran berjaya! Data telah dikemaskini.');
      // Clear the URL parameter without reload
      const newUrl = window.location.pathname;
      window.history.replaceState({}, '', newUrl);

      // Clear message after 5 seconds
      setTimeout(() => setPaymentMessage(null), 5000);
    }
  }, [searchParams]);

  const fetchData = async () => {
    try {
      setLoading(true);
      const token = getStoredToken();

      if (!token) {
        router.push('/login');
        return;
      }

      // Fetch all data in parallel
      const [plansRes, statusRes, addonsRes] = await Promise.all([
        fetch(`${API_URL}/api/v1/subscription/plans`),
        fetch(`${API_URL}/api/v1/subscription/status`, {
          headers: { 'Authorization': `Bearer ${token}` }
        }),
        fetch(`${API_URL}/api/v1/subscription/addons/available`)
      ]);

      if (plansRes.ok) {
        const plansData = await plansRes.json();
        setPlans(plansData.plans || []);
      }

      if (statusRes.ok) {
        const statusData = await statusRes.json();
        setSubscription(statusData);
      }

      if (addonsRes.ok) {
        const addonsData = await addonsRes.json();
        setAddons(addonsData.addons || []);
      }
    } catch (error) {
      console.error('Error fetching data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleUpgrade = async (tier: string) => {
    if (processing) return;
    setProcessing(true);

    try {
      const token = getStoredToken();
      const response = await fetch(`${API_URL}/api/v1/subscription/upgrade`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ new_plan: tier, prorate: false })
      });

      const data = await response.json();

      if (data.success && data.payment_url) {
        localStorage.setItem('pending_tier', tier);
        localStorage.setItem('pending_bill_code', data.bill_code);
        // Backup auth state before external redirect
        backupAuthState();
        window.location.href = data.payment_url;
      } else {
        alert('Ralat: ' + (data.detail?.message || data.detail || 'Gagal memproses'));
      }
    } catch (error) {
      console.error('Upgrade error:', error);
      alert('Ralat semasa memproses naik taraf');
    } finally {
      setProcessing(false);
    }
  };

  const handleRenew = async () => {
    if (processing) return;
    setProcessing(true);

    try {
      const token = getStoredToken();
      const response = await fetch(`${API_URL}/api/v1/subscription/renew`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });

      const data = await response.json();

      if (data.success && data.auto_confirmed) {
        // Free plan renewal — auto-confirmed, no payment needed
        setPaymentMessage(data.message || 'Pembaharuan percuma berjaya!');
        fetchData(); // Refresh subscription status
        setTimeout(() => setPaymentMessage(null), 5000);
      } else if (data.success && data.payment_url) {
        localStorage.setItem('pending_renewal', 'true');
        localStorage.setItem('pending_bill_code', data.bill_code);
        // Backup auth state before external redirect
        backupAuthState();
        window.location.href = data.payment_url;
      } else {
        alert('Ralat: ' + (data.detail || 'Gagal memproses'));
      }
    } catch (error) {
      console.error('Renew error:', error);
      alert('Ralat semasa memproses pembaharuan');
    } finally {
      setProcessing(false);
    }
  };

  const handleBuyAddon = async (addonType: string, quantity: number = 1) => {
    if (processing) return;
    setProcessing(true);

    try {
      const token = getStoredToken();
      const response = await fetch(`${API_URL}/api/v1/subscription/addons/purchase`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ addon_type: addonType, quantity })
      });

      const data = await response.json();

      if (data.success && data.payment_url) {
        localStorage.setItem('pending_addon_type', addonType);
        localStorage.setItem('pending_bill_code', data.bill_code);
        // Backup auth state before external redirect
        backupAuthState();
        window.location.href = data.payment_url;
      } else {
        alert('Ralat: ' + (data.detail || 'Gagal memproses'));
      }
    } catch (error) {
      console.error('Addon purchase error:', error);
      alert('Ralat semasa memproses pembelian');
    } finally {
      setProcessing(false);
    }
  };

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return '-';
    return new Date(dateStr).toLocaleDateString('ms-MY', {
      day: 'numeric',
      month: 'long',
      year: 'numeric'
    });
  };

  const formatLimit = (limit: number | null) => {
    if (limit === null) return 'Tanpa had';
    if (limit === 0) return 'Tidak tersedia';
    return limit.toString();
  };

  if (loading) {
    return (
      <div className="billing-page">
        <div className="loading-container">
          <div className="spinner" />
          <p>Memuatkan...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="billing-page">
      <div className="billing-header">
        <button className="back-btn" onClick={() => router.back()}>
          &larr; Kembali
        </button>
        <h1>Pengurusan Langganan</h1>
      </div>

      {/* Payment Success Message */}
      {paymentMessage && (
        <div className="payment-success-banner">
          <span className="success-icon">&#x2713;</span>
          {paymentMessage}
        </div>
      )}

      {/* Current Subscription Status */}
      <div className="current-subscription">
        <div className="subscription-info">
          <div className="plan-badge-large">
            {subscription?.plan_name?.toUpperCase() || 'STARTER'}
          </div>
          <div className="subscription-details">
            <p className="status">
              Status: <span className={subscription?.is_expired ? 'expired' : 'active'}>
                {subscription?.is_expired ? 'Tamat' : 'Aktif'}
              </span>
            </p>
            {subscription?.end_date && (
              <p className="expiry">
                Tamat: <strong>{formatDate(subscription.end_date)}</strong>
                {!subscription.is_expired && subscription.days_remaining <= 7 && (
                  <span className="days-warning"> ({subscription.days_remaining} hari lagi)</span>
                )}
              </p>
            )}
          </div>
          {(subscription?.is_expired || (subscription?.days_remaining || 0) <= 7) && (
            <button
              className="renew-btn-large"
              onClick={handleRenew}
              disabled={processing}
            >
              {processing ? 'Memproses...' : 'Perbaharui Sekarang'}
            </button>
          )}
        </div>
      </div>

      {/* Tabs */}
      <div className="billing-tabs">
        <button
          className={`tab ${activeTab === 'plans' ? 'active' : ''}`}
          onClick={() => setActiveTab('plans')}
        >
          Pelan Langganan
        </button>
        <button
          className={`tab ${activeTab === 'addons' ? 'active' : ''}`}
          onClick={() => setActiveTab('addons')}
        >
          Addon
        </button>
        <button
          className={`tab ${activeTab === 'history' ? 'active' : ''}`}
          onClick={() => router.push('/dashboard/transactions')}
        >
          Sejarah Transaksi
        </button>
      </div>

      {/* Mobile Usage Section - visible only on smaller screens */}
      <MobileUsageSection
        onUpgradeClick={() => setActiveTab('plans')}
        onRenewClick={handleRenew}
      />

      {/* Plans Tab */}
      {activeTab === 'plans' && (
        <div className="plans-grid">
          {plans.map((plan) => {
            const isCurrentPlan = plan.plan_name === subscription?.plan_name;
            const canUpgrade = !isCurrentPlan &&
              (plan.plan_name === 'basic' && subscription?.plan_name === 'starter') ||
              (plan.plan_name === 'pro');

            return (
              <div
                key={plan.plan_name}
                className={`plan-card ${plan.plan_name} ${isCurrentPlan ? 'current' : ''}`}
              >
                {plan.plan_name === 'basic' && (
                  <div className="popular-badge">Paling Popular</div>
                )}
                <div className="plan-header">
                  <h3>{plan.display_name}</h3>
                  <div className="plan-price">
                    <span className="currency">RM</span>
                    <span className="amount">{plan.price}</span>
                    <span className="period">/bulan</span>
                  </div>
                </div>

                <div className="plan-limits">
                  <div className="limit-item">
                    <span className="label">Laman Web</span>
                    <span className="value">{formatLimit(plan.websites_limit)}</span>
                  </div>
                  <div className="limit-item">
                    <span className="label">Item Menu</span>
                    <span className="value">{formatLimit(plan.menu_items_limit)}</span>
                  </div>
                  <div className="limit-item">
                    <span className="label">AI Hero/bulan</span>
                    <span className="value">{formatLimit(plan.ai_hero_limit)}</span>
                  </div>
                  <div className="limit-item">
                    <span className="label">Imej AI/bulan</span>
                    <span className="value">{formatLimit(plan.ai_images_limit)}</span>
                  </div>
                  <div className="limit-item">
                    <span className="label">Zon Penghantaran</span>
                    <span className="value">{formatLimit(plan.delivery_zones_limit)}</span>
                  </div>
                  <div className="limit-item">
                    <span className="label">Rider</span>
                    <span className="value">{formatLimit(plan.riders_limit)}</span>
                  </div>
                </div>

                <ul className="plan-features">
                  {plan.feature_list?.map((feature, i) => (
                    <li key={i}>
                      <span className="check">&#x2713;</span>
                      {feature}
                    </li>
                  ))}
                </ul>

                <div className="plan-action">
                  {isCurrentPlan ? (
                    <div className="current-plan-badge">Pelan Semasa</div>
                  ) : canUpgrade ? (
                    <button
                      className="upgrade-btn"
                      onClick={() => handleUpgrade(plan.plan_name)}
                      disabled={processing}
                    >
                      {processing ? 'Memproses...' : 'Naik Taraf'}
                    </button>
                  ) : (
                    <button className="upgrade-btn disabled" disabled>
                      Tidak Tersedia
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Addons Tab */}
      {activeTab === 'addons' && (
        <div className="addons-section">
          <p className="addons-intro">
            Tambah kredit tambahan apabila anda mencapai had pelan anda.
            Kredit addon tidak akan tamat tempoh.
          </p>
          <div className="addons-grid">
            {addons.map((addon) => (
              <div key={addon.type} className="addon-card">
                <div className="addon-info">
                  <h4>{addon.name}</h4>
                  <p className="addon-description">{addon.description}</p>
                  <p className="addon-price">RM {addon.price.toFixed(2)}</p>
                </div>
                <button
                  className="buy-addon-btn"
                  onClick={() => handleBuyAddon(addon.type)}
                  disabled={processing}
                >
                  {processing ? '...' : 'Beli'}
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Usage Widget Sidebar */}
      <div className="billing-sidebar">
        <UsageWidget
          onUpgradeClick={() => setActiveTab('plans')}
          onRenewClick={handleRenew}
          compact={true}
        />
      </div>
    </div>
  );
}
