'use client';

import React, { useState } from 'react';
import toast from 'react-hot-toast';
import { getCurrentUser, getStoredToken } from '@/lib/supabase';
import { AppModal } from '@/components/ui/AppModal';

interface LimitReachedModalProps {
  show: boolean;
  onClose: () => void;
  resourceType: 'website' | 'menu_item' | 'ai_hero' | 'ai_image' | 'zone' | 'rider';
  currentUsage: number;
  limit: number | null;
  canBuyAddon: boolean;
  addonPrice?: number;
  onUpgrade?: (tier: string) => void;
  onBuyAddon?: (type: string, quantity: number) => void;
}

const resourceLabels: Record<string, { name: string; nameMalay: string; icon: string }> = {
  website: { name: 'Website', nameMalay: 'Laman Web', icon: '' },
  menu_item: { name: 'Menu Item', nameMalay: 'Item Menu', icon: '' },
  ai_hero: { name: 'AI Hero Generation', nameMalay: 'Penjanaan AI Hero', icon: '' },
  ai_image: { name: 'AI Image', nameMalay: 'Imej AI', icon: '' },
  zone: { name: 'Delivery Zone', nameMalay: 'Zon Penghantaran', icon: '' },
  rider: { name: 'Rider', nameMalay: 'Rider', icon: '' }
};

const addonTypes: Record<string, string> = {
  website: 'website',
  ai_hero: 'ai_hero',
  ai_image: 'ai_image',
  zone: 'zone',
  rider: 'rider'
};

const upgradePlans = [
  {
    tier: 'basic',
    name: 'Basic',
    price: 29,
    features: [
      '5 laman web',
      'Item menu tanpa had',
      '10 AI hero/bulan',
      '30 imej AI/bulan',
      '5 zon penghantaran'
    ]
  },
  {
    tier: 'pro',
    name: 'Pro',
    price: 49,
    features: [
      'Laman web tanpa had',
      'AI tanpa had',
      'Zon tanpa had',
      '10 rider dengan GPS',
      'Sokongan keutamaan'
    ]
  }
];

export function LimitReachedModal({
  show,
  onClose,
  resourceType,
  currentUsage,
  limit,
  canBuyAddon,
  addonPrice,
  onUpgrade,
  onBuyAddon
}: LimitReachedModalProps) {
  const [selectedOption, setSelectedOption] = useState<'upgrade' | 'addon'>('upgrade');
  const [addonQuantity, setAddonQuantity] = useState(1);
  const [loading, setLoading] = useState(false);

  const resource = resourceLabels[resourceType];
  const addonType = addonTypes[resourceType];

  const handleUpgrade = async (tier: string) => {
    setLoading(true);
    try {
      const user = await getCurrentUser();
      const token = getStoredToken();

      if (!user?.id || !token) {
        toast.error('Sila log masuk semula');
        setLoading(false);
        return;
      }

      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || ''}/api/v1/subscription/upgrade`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
          },
          body: JSON.stringify({
            new_plan: tier,
            prorate: false
          })
        }
      );

      const data = await response.json();

      if (data.success && data.payment_url) {
        localStorage.setItem('pending_upgrade_tier', tier);
        window.location.href = data.payment_url;
      } else {
        toast.error('Ralat: ' + (data.detail?.message || data.detail || 'Gagal mencipta pembayaran'));
      }
    } catch (error) {
      console.error('Upgrade error:', error);
      toast.error('Ralat semasa memproses naik taraf');
    } finally {
      setLoading(false);
    }
  };

  const handleBuyAddon = async () => {
    if (!addonType || !canBuyAddon) return;

    setLoading(true);
    try {
      const user = await getCurrentUser();
      const token = getStoredToken();

      if (!user?.id || !token) {
        toast.error('Sila log masuk semula');
        setLoading(false);
        return;
      }

      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || ''}/api/v1/subscription/addons/purchase`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
          },
          body: JSON.stringify({
            addon_type: addonType,
            quantity: addonQuantity
          })
        }
      );

      const data = await response.json();

      if (data.success && data.payment_url) {
        localStorage.setItem('pending_addon_type', addonType);
        localStorage.setItem('pending_addon_quantity', String(addonQuantity));
        window.location.href = data.payment_url;
      } else {
        toast.error('Ralat: ' + (data.detail?.message || data.detail || 'Gagal mencipta pembayaran'));
      }
    } catch (error) {
      console.error('Addon purchase error:', error);
      toast.error('Ralat semasa memproses pembelian');
    } finally {
      setLoading(false);
    }
  };

  const totalAddonPrice = (addonPrice || 0) * addonQuantity;

  return (
    <AppModal
      open={show}
      onClose={onClose}
      variant="limit-reached"
      size="lg"
      title="Had Tercapai"
      description={
        <>
          Anda telah mencapai had {resource?.nameMalay} pelan anda{' '}
          <span className="font-semibold text-volt-400">
            ({currentUsage}/{limit ?? 'tanpa had'})
          </span>
        </>
      }
    >
      {/* Option toggle */}
      <div className="inline-flex w-full rounded-xl bg-white/[0.04] border border-white/[0.08] p-1">
        <button
          className={`flex-1 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
            selectedOption === 'upgrade'
              ? 'bg-volt-400 text-ink-900'
              : 'text-white/60 hover:text-white'
          }`}
          onClick={() => setSelectedOption('upgrade')}
        >
          Naik Taraf Pelan
        </button>
        {canBuyAddon && addonPrice && (
          <button
            className={`flex-1 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
              selectedOption === 'addon'
                ? 'bg-volt-400 text-ink-900'
                : 'text-white/60 hover:text-white'
            }`}
            onClick={() => setSelectedOption('addon')}
          >
            Beli Addon
          </button>
        )}
      </div>

      {/* Upgrade options */}
      {selectedOption === 'upgrade' && (
        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          {upgradePlans.map((plan) => (
            <div
              key={plan.tier}
              className={`rounded-2xl border p-4 ${
                plan.tier === 'pro'
                  ? 'border-volt-400/25 bg-white/[0.04] shadow-[0_0_0_1px_rgba(199,255,61,0.06)]'
                  : 'border-white/[0.08] bg-white/[0.02]'
              }`}
            >
              <div className="flex items-baseline justify-between">
                <h3 className="text-base font-semibold text-white">{plan.name}</h3>
                <div className="flex items-baseline gap-1">
                  <span className="text-xs text-white/50">RM</span>
                  <span className="text-2xl font-bold text-white">{plan.price}</span>
                  <span className="text-xs text-white/50">/bulan</span>
                </div>
              </div>
              <ul className="mt-3 space-y-1.5">
                {plan.features.map((feature, i) => (
                  <li key={i} className="flex items-center gap-2 text-sm text-white/70">
                    <span className="text-volt-400">&#x2713;</span>
                    {feature}
                  </li>
                ))}
              </ul>
              <button
                className="mt-4 inline-flex h-10 w-full items-center justify-center rounded-xl bg-volt-400 px-4 text-sm font-semibold text-ink-900 transition-all hover:bg-volt-300 active:scale-[0.98] disabled:opacity-60"
                onClick={() => handleUpgrade(plan.tier)}
                disabled={loading}
              >
                {loading ? 'Memproses...' : `Naik Taraf ke ${plan.name}`}
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Addon options */}
      {selectedOption === 'addon' && canBuyAddon && addonPrice && (
        <div className="mt-4">
          <div className="rounded-2xl border border-white/[0.08] bg-white/[0.02] p-4">
            <div className="flex items-baseline justify-between">
              <h3 className="text-base font-semibold text-white">{resource?.nameMalay} Tambahan</h3>
              <p className="text-sm text-white/60">RM {addonPrice.toFixed(2)} / unit</p>
            </div>

            <div className="mt-4 flex items-center justify-between">
              <label className="text-sm text-white/70">Kuantiti:</label>
              <div className="flex items-center gap-3">
                <button
                  className="flex h-8 w-8 items-center justify-center rounded-lg border border-white/[0.12] bg-white/[0.04] text-white disabled:opacity-40"
                  onClick={() => setAddonQuantity(Math.max(1, addonQuantity - 1))}
                  disabled={addonQuantity <= 1}
                >
                  -
                </button>
                <span className="min-w-6 text-center text-sm font-semibold text-white">{addonQuantity}</span>
                <button
                  className="flex h-8 w-8 items-center justify-center rounded-lg border border-white/[0.12] bg-white/[0.04] text-white"
                  onClick={() => setAddonQuantity(addonQuantity + 1)}
                >
                  +
                </button>
              </div>
            </div>

            <div className="mt-4 flex items-center justify-between border-t border-white/[0.06] pt-4">
              <span className="text-sm text-white/70">Jumlah:</span>
              <span className="text-lg font-bold text-volt-400">RM {totalAddonPrice.toFixed(2)}</span>
            </div>

            <button
              className="mt-4 inline-flex h-11 w-full items-center justify-center rounded-xl bg-volt-400 px-4 text-sm font-semibold text-ink-900 transition-all hover:bg-volt-300 active:scale-[0.98] disabled:opacity-60"
              onClick={handleBuyAddon}
              disabled={loading}
            >
              {loading ? 'Memproses...' : `Beli Sekarang - RM ${totalAddonPrice.toFixed(2)}`}
            </button>

            <p className="mt-3 text-center text-xs text-white/40">
              Kredit addon boleh digunakan bila-bila masa dan tidak akan tamat tempoh.
            </p>
          </div>
        </div>
      )}

      <p className="mt-5 text-center text-xs text-white/40">
        Anda akan diarahkan ke ToyyibPay untuk pembayaran selamat.
      </p>
    </AppModal>
  );
}

export default LimitReachedModal;
