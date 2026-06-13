'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import toast from 'react-hot-toast';
import { getCurrentUser, getStoredToken, backupAuthState } from '@/lib/supabase';
import { AppModal } from '@/components/ui/AppModal';

interface Addon {
  type: string;
  label: string;
  price: number;
  quantity?: number;
  is_recurring?: boolean;
}

interface AddonPurchaseModalProps {
  show: boolean;
  addon: Addon | null;
  onClose: () => void;
}

export function AddonPurchaseModal({ show, addon, onClose }: AddonPurchaseModalProps) {
  const router = useRouter();
  const [quantity, setQuantity] = useState(addon?.quantity || 1);
  const [loading, setLoading] = useState(false);

  const handlePurchase = async () => {
    if (!addon) return;

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

      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || ''}/api/v1/payments/addon/purchase`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          user_id: user.id,
          addon_type: addon.type,
          quantity: quantity
        })
      });

      const data = await response.json();

      if (data.success) {
        // Save addon info to localStorage so payment success page can handle it
        localStorage.setItem('pending_payment_id', data.payment_id);
        localStorage.setItem('pending_bill_code', data.bill_code);
        localStorage.setItem('pending_addon_type', addon.type);
        localStorage.setItem('pending_addon_quantity', String(quantity));
        // Clear subscription-related pending info to avoid confusion
        localStorage.removeItem('pending_tier');

        // CRITICAL: Backup auth state before external redirect
        // This helps restore the session if localStorage is cleared during redirect
        backupAuthState();

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

  if (!addon) return null;

  const total = addon.price * quantity;

  return (
    <AppModal
      open={show}
      onClose={onClose}
      variant="limit-reached"
      title="Beli Addon"
      primaryLabel={loading ? 'Memproses...' : `Bayar RM${total.toFixed(2)}`}
      onPrimary={handlePurchase}
      primaryLoading={loading}
    >
      <div className="rounded-2xl border border-white/[0.08] bg-white/[0.02] p-4">
        <h3 className="text-base font-semibold text-white">{addon.label}</h3>
        <p className="mt-1 text-sm text-white/60">
          RM {addon.price} {addon.is_recurring ? '/bulan' : 'sekali'}
        </p>
      </div>

      {['ai_image', 'ai_hero'].includes(addon.type) && (
        <div className="mt-4 flex items-center justify-between">
          <label className="text-sm text-white/70">Kuantiti:</label>
          <select
            value={quantity}
            onChange={(e) => setQuantity(parseInt(e.target.value))}
            className="rounded-xl border border-white/[0.12] bg-white/[0.04] px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-volt-400/40"
          >
            <option value="1">1 - RM{addon.price}</option>
            {addon.type === 'ai_image' && (
              <>
                <option value="10">10 - RM{addon.price * 10}</option>
                <option value="50">50 - RM{addon.price * 50}</option>
                <option value="100">100 - RM{addon.price * 100}</option>
              </>
            )}
            {addon.type === 'ai_hero' && (
              <>
                <option value="5">5 - RM{addon.price * 5}</option>
                <option value="10">10 - RM{addon.price * 10}</option>
              </>
            )}
          </select>
        </div>
      )}

      <div className="mt-4 flex items-center justify-between border-t border-white/[0.06] pt-4">
        <span className="text-sm text-white/70">Jumlah:</span>
        <span className="text-lg font-bold text-volt-400">RM {total.toFixed(2)}</span>
      </div>
    </AppModal>
  );
}

export default AddonPurchaseModal;
