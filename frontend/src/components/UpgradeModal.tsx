'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import toast from 'react-hot-toast';
import { getCurrentUser, getStoredToken } from '@/lib/supabase';
import { AppModal } from '@/components/ui/AppModal';

interface UpgradeModalProps {
  show: boolean;
  currentTier: string;
  targetTier: string;
  onClose: () => void;
}

const prices: Record<string, number> = {
  starter: 5,
  basic: 29,
  pro: 49
};

const features: Record<string, string[]> = {
  starter: [
    '1 website',
    '20 menu items',
    '1 AI generation',
    '5 AI images',
    '1 delivery zone'
  ],
  basic: [
    '5 websites',
    'Unlimited menu',
    '10 AI generations/month',
    '30 AI images/month',
    '5 delivery zones',
    'QR Payment',
    'Borang Hubungi'
  ],
  pro: [
    'Unlimited websites',
    'Unlimited menu',
    'Unlimited AI',
    'Unlimited zones',
    'Rider GPS (10 riders)',
    'Advanced analytics',
    'Priority support'
  ]
};

export function UpgradeModal({ show, currentTier, targetTier, onClose }: UpgradeModalProps) {
  const router = useRouter();
  const [loading, setLoading] = useState(false);

  const handleUpgrade = async () => {
    setLoading(true);

    try {
      // Get user and token from BinaApp auth system
      const user = await getCurrentUser();
      const token = getStoredToken();

      if (!user?.id) {
        toast.error('Sila log masuk semula untuk meneruskan pembayaran.');
        setLoading(false);
        return;
      }

      if (!token) {
        toast.error('Sesi anda telah tamat. Sila log masuk semula.');
        setLoading(false);
        return;
      }

      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || ''}/api/v1/payments/subscribe/${targetTier}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          user_id: user.id
        })
      });

      const data = await response.json();

      if (data.success) {
        // Save payment ID for verification later
        localStorage.setItem('pending_payment_id', data.payment_id);
        localStorage.setItem('pending_tier', targetTier);

        // Redirect to ToyyibPay
        window.location.href = data.payment_url;
      } else if (
        response.status === 403 &&
        response.headers.get('X-Email-Verification-Required') === 'true'
      ) {
        // Email verification gate: send the user straight to the code-entry
        // page (pre-filled with their email) instead of a blocking alert, then
        // back to billing once verified — no hunting for where to verify.
        toast.error(data.detail || 'Sila sahkan e-mel anda sebelum membuat pembayaran.');
        onClose();
        const params = new URLSearchParams();
        if (user.email) params.set('email', user.email);
        params.set('redirect', '/dashboard/billing');
        router.push(`/verify-email?${params.toString()}`);
      } else {
        toast.error(data.detail || 'Failed to create payment');
        setLoading(false);
      }
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Unknown error');
      setLoading(false);
    }
  };

  if (!targetTier) return null;

  const tierPrice = prices[targetTier] || 0;
  const tierFeatures = features[targetTier] || [];
  const isFreeToStarter = (currentTier || '').toLowerCase() === 'free' && targetTier === 'starter';

  return (
    <AppModal
      open={show}
      onClose={onClose}
      variant="limit-reached"
      title={isFreeToStarter ? 'Your site looks amazing! 🚀' : `Upgrade ke ${targetTier.toUpperCase()}`}
      description={
        isFreeToStarter ? (
          <>
            Upgrade to Starter (RM5/month) to publish at{' '}
            <strong className="text-white">yourname.binaapp.my</strong>.
          </>
        ) : undefined
      }
      primaryLabel={loading ? 'Memproses...' : `Upgrade Sekarang - RM${tierPrice}`}
      onPrimary={handleUpgrade}
      primaryLoading={loading}
    >
      {/* Price */}
      <div className="flex items-baseline justify-center gap-1 rounded-2xl border border-white/[0.08] bg-white/[0.02] py-5">
        <span className="text-3xl font-bold text-white">RM {tierPrice}</span>
        <span className="text-sm text-white/50">/bulan</span>
      </div>

      {/* Features */}
      <div className="mt-4">
        <h3 className="text-sm font-semibold text-white/80">Anda akan dapat:</h3>
        <div className="mt-2 space-y-1.5">
          {tierFeatures.map((feature, i) => (
            <div key={i} className="flex items-center gap-2 text-sm text-white/70">
              <span className="text-volt-400">✓</span> {feature}
            </div>
          ))}
        </div>
      </div>

      <p className="mt-4 text-center text-xs text-white/40">
        Anda akan diarahkan ke ToyyibPay untuk pembayaran selamat.
      </p>
    </AppModal>
  );
}

export default UpgradeModal;
