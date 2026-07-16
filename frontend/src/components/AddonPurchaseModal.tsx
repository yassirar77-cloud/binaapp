'use client';

import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import toast from 'react-hot-toast';
import { getCurrentUser, getStoredToken, backupAuthState } from '@/lib/supabase';
import './AddonPurchaseModal.css';

interface Addon {
  type: string;
  label: string;
  price: number;
  quantity?: number;
  is_recurring?: boolean;
}

interface AddonPackage {
  package_id: string;
  addon_type: string;
  quantity: number;
  price: number;
  unit_price: number;
  savings: number;
  savings_pct: number;
}

interface AddonPurchaseModalProps {
  show: boolean;
  addon: Addon | null;
  onClose: () => void;
}

export function AddonPurchaseModal({ show, addon, onClose }: AddonPurchaseModalProps) {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  // Bundle packages (AI images / AI hero) fetched from the server catalog.
  // Prices shown are display-only — the backend re-resolves the package by id
  // and bills the server-side price. If the fetch fails or the addon has no
  // packages, the modal falls back to a plain single-credit purchase.
  const [packages, setPackages] = useState<AddonPackage[]>([]);
  const [selectedPackageId, setSelectedPackageId] = useState<string | null>(null);

  useEffect(() => {
    if (!show || !addon) return;
    setPackages([]);
    setSelectedPackageId(null);

    let cancelled = false;
    (async () => {
      try {
        const res = await fetch(
          `${process.env.NEXT_PUBLIC_API_URL || ''}/api/v1/subscription/addons/packages?addon_type=${encodeURIComponent(addon.type)}`
        );
        if (!res.ok) return;
        const data = await res.json();
        const list: AddonPackage[] = (data.packages || []).sort(
          (a: AddonPackage, b: AddonPackage) => a.quantity - b.quantity
        );
        if (!cancelled && list.length > 0) {
          setPackages(list);
          setSelectedPackageId(list[0].package_id);
        }
      } catch {
        // Fall back to single-credit purchase silently.
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [show, addon]);

  const selectedPackage = packages.find((p) => p.package_id === selectedPackageId) || null;

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
          quantity: selectedPackage ? selectedPackage.quantity : 1,
          ...(selectedPackage ? { package_id: selectedPackage.package_id } : {})
        })
      });

      const data = await response.json();

      if (data.success) {
        // Save addon info to localStorage so payment success page can handle it
        localStorage.setItem('pending_payment_id', data.payment_id);
        localStorage.setItem('pending_bill_code', data.bill_code);
        localStorage.setItem('pending_addon_type', addon.type);
        localStorage.setItem('pending_addon_quantity', String(data.quantity ?? 1));
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

  if (!show || !addon) return null;

  const total = selectedPackage ? selectedPackage.price : addon.price;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="addon-modal" onClick={(e) => e.stopPropagation()}>
        <button className="close-btn" onClick={onClose}>×</button>

        <h2>Beli Addon</h2>

        <div className="addon-details">
          <h3>{addon.label}</h3>
          <p className="addon-price">
            RM {addon.price} {addon.is_recurring ? '/bulan' : 'sekali'}
          </p>
        </div>

        {packages.length > 0 && (
          <div className="quantity-selector">
            <label>Pakej:</label>
            <select
              value={selectedPackageId ?? ''}
              onChange={(e) => setSelectedPackageId(e.target.value)}
            >
              {packages.map((pkg) => (
                <option key={pkg.package_id} value={pkg.package_id}>
                  {pkg.quantity} kredit — RM{pkg.price.toFixed(2)}
                  {pkg.savings_pct > 0 ? ` (Jimat ${pkg.savings_pct}%)` : ''}
                </option>
              ))}
            </select>
          </div>
        )}

        <div className="total-price">
          <strong>Jumlah: RM {total.toFixed(2)}</strong>
        </div>

        <button
          className="purchase-btn"
          onClick={handlePurchase}
          disabled={loading}
        >
          {loading ? 'Memproses...' : `Bayar RM${total.toFixed(2)}`}
        </button>
      </div>
    </div>
  );
}

export default AddonPurchaseModal;
