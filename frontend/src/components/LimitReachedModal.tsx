'use client';

import React, { useState } from 'react';
import toast from 'react-hot-toast';
import { AlertTriangle, Check, Minus, Plus } from 'lucide-react';
import { Modal } from '@/components/ui/popups';
import { cn } from '@/lib/utils';
import { getCurrentUser, getStoredToken } from '@/lib/supabase';

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
  /** Which tab opens first. Pass 'addon' to surface the per-slot add-on
   *  (e.g. rider RM3) directly instead of the upgrade plans. */
  defaultOption?: 'upgrade' | 'addon';
}

const resourceLabels: Record<string, { name: string; nameMalay: string }> = {
  website: { name: 'Website', nameMalay: 'Laman Web' },
  menu_item: { name: 'Menu Item', nameMalay: 'Item Menu' },
  ai_hero: { name: 'AI Hero Generation', nameMalay: 'Penjanaan AI Hero' },
  ai_image: { name: 'AI Image', nameMalay: 'Imej AI' },
  zone: { name: 'Delivery Zone', nameMalay: 'Zon Penghantaran' },
  rider: { name: 'Rider', nameMalay: 'Rider' }
};

const addonTypes: Record<string, string> = {
  website: 'website',
  ai_hero: 'ai_hero',
  ai_image: 'ai_image',
  zone: 'zone',
  rider: 'rider'
};

// Basic (RM29) was retired from sale — the backend rejects new basic
// purchases, so Pro is the only upgrade target offered here.
const upgradePlans = [
  {
    tier: 'pro',
    name: 'Bisnes',
    price: 49,
    features: [
      'Laman web & zon tanpa had',
      'Imej AI percuma',
      '10 rider sendiri + GPS tracking',
      'Dashboard order & chat pelanggan',
      'Analitik penuh & sokongan keutamaan'
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
  onBuyAddon,
  defaultOption = 'upgrade'
}: LimitReachedModalProps) {
  const [selectedOption, setSelectedOption] = useState<'upgrade' | 'addon'>(defaultOption);
  const [addonQuantity, setAddonQuantity] = useState(1);
  const [loading, setLoading] = useState(false);

  const resource = resourceLabels[resourceType] ?? resourceLabels.website;
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
  const showAddonTab = canBuyAddon && !!addonPrice;

  return (
    <Modal open={show} onClose={onClose} size="md">
      {/* Header */}
      <div className="text-center">
        <div
          className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-2xl bg-warn-400/15 text-warn-400"
          aria-hidden="true"
        >
          <AlertTriangle className="h-6 w-6" />
        </div>
        <h2 className="font-geist text-lg font-bold tracking-tight text-ink-050">
          Had Tercapai / Limit Reached
        </h2>
        <p className="mx-auto mt-2 max-w-sm text-sm leading-relaxed text-ink-300">
          Anda telah mencapai had {resource.nameMalay} pelan anda. / You&rsquo;ve
          reached your plan&rsquo;s {resource.name} limit.
        </p>
        <span className="mt-3 inline-flex items-center rounded-full bg-warn-400/15 px-3 py-1 font-geist-mono text-xs font-semibold text-warn-400">
          {currentUsage}/{limit ?? 'tanpa had'}
        </span>
      </div>

      {/* Option toggle */}
      {showAddonTab && (
        <div className="mt-5 flex gap-1 rounded-xl bg-white/[0.04] p-1 ring-1 ring-white/[0.06]">
          <button
            type="button"
            className={cn(
              'flex-1 rounded-lg px-3 py-2 text-sm font-semibold transition-colors',
              selectedOption === 'upgrade'
                ? 'bg-volt-400 text-ink-900'
                : 'text-ink-300 hover:bg-white/[0.06] hover:text-ink-100'
            )}
            onClick={() => setSelectedOption('upgrade')}
          >
            Naik Taraf / Upgrade
          </button>
          <button
            type="button"
            className={cn(
              'flex-1 rounded-lg px-3 py-2 text-sm font-semibold transition-colors',
              selectedOption === 'addon'
                ? 'bg-volt-400 text-ink-900'
                : 'text-ink-300 hover:bg-white/[0.06] hover:text-ink-100'
            )}
            onClick={() => setSelectedOption('addon')}
          >
            Beli Addon / Buy Add-on
          </button>
        </div>
      )}

      {/* Upgrade options */}
      {selectedOption === 'upgrade' && (
        <div className="mt-5 space-y-4">
          {upgradePlans.map((plan) => (
            <div
              key={plan.tier}
              className="rounded-2xl bg-white/[0.04] p-5 ring-1 ring-volt-400/40"
            >
              <div className="flex items-baseline justify-between">
                <h3 className="font-geist text-base font-bold tracking-tight text-ink-050">
                  {plan.name}
                </h3>
                <div className="flex items-baseline gap-1">
                  <span className="text-xs font-semibold text-ink-400">RM</span>
                  <span className="font-geist text-2xl font-bold text-volt-400">
                    {plan.price}
                  </span>
                  <span className="text-xs text-ink-400">/bulan</span>
                </div>
              </div>
              <ul className="mt-4 space-y-2.5">
                {plan.features.map((feature, i) => (
                  <li key={i} className="flex items-start gap-2.5 text-sm text-ink-200">
                    <Check className="mt-0.5 h-4 w-4 shrink-0 text-volt-400" aria-hidden="true" />
                    {feature}
                  </li>
                ))}
              </ul>
              <button
                type="button"
                className="mt-5 inline-flex h-11 w-full items-center justify-center rounded-xl bg-volt-400 px-4 text-sm font-semibold text-ink-900 transition-colors hover:bg-volt-300 active:bg-volt-500 disabled:cursor-not-allowed disabled:opacity-60"
                onClick={() => handleUpgrade(plan.tier)}
                disabled={loading}
              >
                {loading ? 'Memproses… / Processing…' : `Naik Taraf / Upgrade — ${plan.name}`}
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Addon options */}
      {selectedOption === 'addon' && showAddonTab && (
        <div className="mt-5 rounded-2xl bg-white/[0.04] p-5 ring-1 ring-white/[0.08]">
          <h3 className="font-geist text-base font-bold tracking-tight text-ink-050">
            {resource.nameMalay} Tambahan / Additional {resource.name}
          </h3>
          <p className="mt-1 text-sm font-semibold text-volt-400">
            RM {addonPrice!.toFixed(2)} / unit
          </p>

          <div className="mt-4 flex items-center justify-between">
            <span className="text-sm text-ink-300">Kuantiti / Quantity:</span>
            <div className="flex items-center gap-1 rounded-xl bg-white/[0.04] p-1 ring-1 ring-white/[0.08]">
              <button
                type="button"
                aria-label="Kurangkan kuantiti"
                className="flex h-8 w-8 items-center justify-center rounded-lg text-ink-200 transition-colors hover:bg-white/[0.08] disabled:cursor-not-allowed disabled:opacity-40"
                onClick={() => setAddonQuantity(Math.max(1, addonQuantity - 1))}
                disabled={addonQuantity <= 1}
              >
                <Minus className="h-4 w-4" />
              </button>
              <span className="w-8 text-center font-geist-mono text-sm font-semibold text-ink-050">
                {addonQuantity}
              </span>
              <button
                type="button"
                aria-label="Tambah kuantiti"
                className="flex h-8 w-8 items-center justify-center rounded-lg text-ink-200 transition-colors hover:bg-white/[0.08]"
                onClick={() => setAddonQuantity(addonQuantity + 1)}
              >
                <Plus className="h-4 w-4" />
              </button>
            </div>
          </div>

          <div className="mt-4 flex items-center justify-between border-t border-white/[0.08] pt-4">
            <span className="text-sm text-ink-300">Jumlah / Total:</span>
            <span className="font-geist text-lg font-bold text-volt-400">
              RM {totalAddonPrice.toFixed(2)}
            </span>
          </div>

          <button
            type="button"
            className="mt-5 inline-flex h-11 w-full items-center justify-center rounded-xl bg-volt-400 px-4 text-sm font-semibold text-ink-900 transition-colors hover:bg-volt-300 active:bg-volt-500 disabled:cursor-not-allowed disabled:opacity-60"
            onClick={handleBuyAddon}
            disabled={loading}
          >
            {loading
              ? 'Memproses… / Processing…'
              : `Beli Sekarang / Buy Now — RM ${totalAddonPrice.toFixed(2)}`}
          </button>

          <p className="mt-3 text-xs leading-relaxed text-ink-400">
            Kredit sah selama 365 hari dan ditolak apabila digunakan. / Credits
            are valid for 365 days and are deducted as you use them.
          </p>
        </div>
      )}

      <p className="mt-5 text-center text-xs text-ink-400">
        Anda akan diarahkan ke ToyyibPay untuk pembayaran selamat. / You&rsquo;ll be
        redirected to ToyyibPay for secure payment.
      </p>
    </Modal>
  );
}

export default LimitReachedModal;
