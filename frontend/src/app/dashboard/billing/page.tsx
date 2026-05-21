'use client';

import React, { useCallback, useEffect, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { backupAuthState, getStoredToken } from '@/lib/supabase';
import DashboardHeader from '@/components/dashboard-new/DashboardHeader';
import BillingSubnav from './components/BillingSubnav';
import CurrentPlanBanner from './components/CurrentPlanBanner';
import PlanCards from './components/PlanCards';
import UsageHeroCards from './components/UsageHeroCards';
import type { Addon, Plan, SubscriptionStatus, UsageResponse } from './types';

const API_URL = process.env.NEXT_PUBLIC_API_URL || '';

export default function BillingPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [loading, setLoading] = useState(true);
  const [plans, setPlans] = useState<Plan[]>([]);
  const [addons, setAddons] = useState<Addon[]>([]);
  const [subscription, setSubscription] = useState<SubscriptionStatus | null>(null);
  const [usage, setUsage] = useState<UsageResponse | null>(null);
  const [processing, setProcessing] = useState(false);
  const [paymentMessage, setPaymentMessage] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      const token = getStoredToken();
      if (!token) {
        router.push('/login');
        return;
      }

      const authHeaders = { Authorization: `Bearer ${token}` };
      const [plansRes, statusRes, addonsRes, usageRes] = await Promise.all([
        fetch(`${API_URL}/api/v1/subscription/plans`),
        fetch(`${API_URL}/api/v1/subscription/status`, { headers: authHeaders }),
        fetch(`${API_URL}/api/v1/subscription/addons/available`),
        fetch(`${API_URL}/api/v1/subscription/usage`, { headers: authHeaders }),
      ]);

      if (plansRes.ok) {
        const data = await plansRes.json();
        setPlans(data.plans || []);
      }
      if (statusRes.ok) {
        setSubscription(await statusRes.json());
      }
      if (addonsRes.ok) {
        const data = await addonsRes.json();
        setAddons(data.addons || []);
      }
      if (usageRes.ok) {
        setUsage(await usageRes.json());
      }
    } catch (error) {
      console.error('Error fetching billing data:', error);
    } finally {
      setLoading(false);
    }
  }, [router]);

  useEffect(() => {
    fetchData();

    if (searchParams.get('payment') === 'success') {
      setPaymentMessage('Pembayaran berjaya! Data telah dikemaskini.');
      window.history.replaceState({}, '', window.location.pathname);
      const t = setTimeout(() => setPaymentMessage(null), 5000);
      return () => clearTimeout(t);
    }
  }, [fetchData, searchParams]);

  const handleUpgrade = useCallback(
    async (tier: string) => {
      if (processing) return;
      setProcessing(true);
      try {
        const token = getStoredToken();
        const res = await fetch(`${API_URL}/api/v1/subscription/upgrade`, {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ new_plan: tier, prorate: false }),
        });
        const data = await res.json();
        if (data.success && data.payment_url) {
          localStorage.setItem('pending_tier', tier);
          localStorage.setItem('pending_bill_code', data.bill_code);
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
    },
    [processing]
  );

  const handleRenew = useCallback(async () => {
    if (processing) return;
    setProcessing(true);
    try {
      const token = getStoredToken();
      const res = await fetch(`${API_URL}/api/v1/subscription/renew`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });
      const data = await res.json();
      if (data.success && data.auto_confirmed) {
        setPaymentMessage(data.message || 'Pembaharuan percuma berjaya!');
        fetchData();
        setTimeout(() => setPaymentMessage(null), 5000);
      } else if (data.success && data.payment_url) {
        localStorage.setItem('pending_renewal', 'true');
        localStorage.setItem('pending_bill_code', data.bill_code);
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
  }, [processing, fetchData]);

  const handleBuyAddon = useCallback(
    async (addonType: string, quantity = 1) => {
      if (processing) return;
      setProcessing(true);
      try {
        const token = getStoredToken();
        const res = await fetch(`${API_URL}/api/v1/subscription/addons/purchase`, {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ addon_type: addonType, quantity }),
        });
        const data = await res.json();
        if (data.success && data.payment_url) {
          localStorage.setItem('pending_addon_type', addonType);
          localStorage.setItem('pending_bill_code', data.bill_code);
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
    },
    [processing]
  );

  const handleLogout = useCallback(() => {
    if (typeof window !== 'undefined') {
      localStorage.removeItem('binaapp_token');
      localStorage.removeItem('binaapp_user');
    }
    router.push('/');
  }, [router]);

  if (loading) {
    return (
      <>
        <DashboardHeader onLogout={handleLogout} />
        <main className="min-h-screen bg-ink-050 flex items-center justify-center">
          <div className="font-geist-mono text-xs uppercase tracking-[0.14em] text-ink-400">
            Memuatkan…
          </div>
        </main>
      </>
    );
  }

  const placeholderSections: { id: string; title: string; commit: string }[] = [
    { id: 'sec-tambahan', title: 'Tambahan À la carte', commit: 'commit 6' },
    { id: 'sec-sejarah', title: 'Sejarah pembayaran', commit: 'commit 7' },
    { id: 'sec-kaedah', title: 'Kaedah pembayaran', commit: 'commit 8' },
  ];

  return (
    <>
      <DashboardHeader onLogout={handleLogout} />
      <main className="min-h-screen bg-ink-050 font-geist text-ink-900">
        <div className="mx-auto max-w-[1440px] px-4 py-8 sm:px-7 sm:py-10 flex flex-col gap-9">
          {paymentMessage && (
            <div
              role="status"
              className="rounded-xl2 bg-ok-500 text-white px-5 py-4 text-sm font-medium shadow-card"
            >
              ✓ {paymentMessage}
            </div>
          )}

          <header>
            <div className="font-geist-mono text-[10px] uppercase tracking-[0.14em] text-ink-400">
              Akaun <span className="text-ink-300">/</span> Bil &amp; Langganan
            </div>
            <h1 className="mt-1 text-[26px] font-bold tracking-[-0.035em] leading-tight text-ink-900">
              Bil &amp; Langganan
            </h1>
            <p className="mt-1 text-[13px] text-ink-500">
              Uruskan pelan, lihat penggunaan, dan muat turun resit dari sini.
            </p>
          </header>

          <BillingSubnav />

          {subscription && (
            <section id="sec-bil" className="scroll-mt-32">
              <CurrentPlanBanner subscription={subscription} plans={plans} />
            </section>
          )}

          <section id="sec-penggunaan" className="scroll-mt-32">
            <UsageHeroCards usage={usage} />
          </section>

          <section id="sec-pelan" className="scroll-mt-32">
            <PlanCards
              plans={plans}
              subscription={subscription}
              processing={processing}
              onUpgrade={handleUpgrade}
            />
          </section>

          {/* Remaining section placeholders — each filled by a subsequent commit. */}
          {placeholderSections.map((s) => (
            <section key={s.id} id={s.id} className="scroll-mt-32">
              <div className="rounded-[20px] border border-dashed border-ink-200 bg-white px-6 py-10 text-center">
                <div className="font-geist-mono text-[10px] uppercase tracking-[0.14em] text-ink-400">
                  {s.commit}
                </div>
                <div className="mt-2 text-[15px] font-semibold text-ink-600">{s.title}</div>
              </div>
            </section>
          ))}
        </div>
      </main>
    </>
  );
}
