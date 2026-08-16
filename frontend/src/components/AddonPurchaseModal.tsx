'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import toast from 'react-hot-toast';
import { PackagePlus } from 'lucide-react';
import { Modal } from '@/components/ui/popups';
import { getCurrentUser, getStoredToken, backupAuthState } from '@/lib/supabase';

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
  const quantity = addon?.quantity || 1;
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

  const total = (addon?.price ?? 0) * quantity;

  return (
    <Modal open={show && !!addon} onClose={onClose} size="sm">
      {addon && (
        <>
          <div
            className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-2xl bg-volt-400/15 text-volt-400"
            aria-hidden="true"
          >
            <PackagePlus className="h-6 w-6" />
          </div>

          <h2 className="text-center font-geist text-lg font-bold tracking-tight text-ink-050">
            Beli Addon
          </h2>

          <div className="mt-4 rounded-2xl bg-white/[0.04] p-5 text-center ring-1 ring-white/[0.08]">
            <h3 className="font-geist text-base font-semibold tracking-tight text-ink-050">
              {addon.label}
            </h3>
            <p className="mt-1 text-sm font-semibold text-volt-400">
              RM {addon.price} {addon.is_recurring ? '/bulan' : 'sekali'}
            </p>
          </div>

          {/* ai_image / ai_hero quantity options removed: AI images are free
              and those addons are no longer sold (backend rejects them). */}

          <div className="mt-4 flex items-center justify-between rounded-xl bg-white/[0.04] px-4 py-3 ring-1 ring-white/[0.06]">
            <span className="text-sm text-ink-300">Jumlah:</span>
            <span className="font-geist text-lg font-bold text-volt-400">
              RM {total.toFixed(2)}
            </span>
          </div>

          <button
            type="button"
            className="mt-5 inline-flex h-11 w-full items-center justify-center rounded-xl bg-volt-400 px-4 text-sm font-semibold text-ink-900 transition-colors hover:bg-volt-300 active:bg-volt-500 disabled:cursor-not-allowed disabled:opacity-60"
            onClick={handlePurchase}
            disabled={loading}
          >
            {loading ? 'Memproses...' : `Bayar RM${total.toFixed(2)}`}
          </button>

          <p className="mt-3 text-center text-xs text-ink-400">
            Anda akan diarahkan ke ToyyibPay untuk pembayaran selamat.
          </p>
        </>
      )}
    </Modal>
  );
}

export default AddonPurchaseModal;
