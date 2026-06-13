'use client';

import React, { useCallback, useEffect, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { backupAuthState, getStoredToken } from '@/lib/supabase';
import { appToast } from '@/components/ui';
import DashboardHeader from '@/components/dashboard-new/DashboardHeader';
import AddonsGrid from './components/AddonsGrid';
import BillingSubnav from './components/BillingSubnav';
import CurrentPlanBanner from './components/CurrentPlanBanner';
import PaymentHistoryPreview from './components/PaymentHistoryPreview';
import PaymentMethodPanel from './components/PaymentMethodPanel';
import PlanCards from './components/PlanCards';
import SupportFooter from './components/SupportFooter';
import UsageHeroCards from './components/UsageHeroCards';
import type { Addon, Plan, SubscriptionStatus, Transaction, UsageResponse } from './types';

const API_URL = process.env.NEXT_PUBLIC_API_URL || '';

export default function BillingPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [loading, setLoading] = useState(true);
  const [plans, setPlans] = useState<Plan[]>([]);
  const [addons, setAddons] = useState<Addon[]>([]);
  const [subscription, setSubscription] = useState<SubscriptionStatus | null>(null);
  const [usage, setUsage] = useState<UsageResponse | null>(null);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
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
      const [plansRes, statusRes, addonsRes, usageRes, txRes] = await Promise.all([
        fetch(`${API_URL}/api/v1/subscription/plans`),
        fetch(`${API_URL}/api/v1/subscription/status`, { headers: authHeaders }),
        fetch(`${API_URL}/api/v1/subscription/addons/available`),
        fetch(`${API_URL}/api/v1/subscription/usage`, { headers: authHeaders }),
        fetch(`${API_URL}/api/v1/subscription/transactions?limit=8`, { headers: authHeaders }),
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
      if (txRes.ok) {
        const data = await txRes.json();
        setTransactions(data.transactions || []);
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
          appToast.error('Ralat: ' + (data.detail?.message || data.detail || 'Gagal memproses'));
        }
      } catch (error) {
        console.error('Upgrade error:', error);
        appToast.error('Ralat semasa memproses naik taraf');
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
        appToast.error('Ralat: ' + (data.detail || 'Gagal memproses'));
      }
    } catch (error) {
      console.error('Renew error:', error);
      appToast.error('Ralat semasa memproses pembaharuan');
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
          appToast.error('Ralat: ' + (data.detail || 'Gagal memproses'));
        }
      } catch (error) {
        console.error('Addon purchase error:', error);
        appToast.error('Ralat semasa memproses pembelian');
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

          <section id="sec-tambahan" className="scroll-mt-32">
            <AddonsGrid
              addons={addons}
              usage={usage}
              processing={processing}
              onBuy={handleBuyAddon}
            />
          </section>

          <section id="sec-sejarah" className="scroll-mt-32">
            <PaymentHistoryPreview transactions={transactions} />
          </section>

          <section id="sec-kaedah" className="scroll-mt-32">
            <PaymentMethodPanel />
          </section>

          <SupportFooter />
        </div>
      </main>
    </>
  );
}
