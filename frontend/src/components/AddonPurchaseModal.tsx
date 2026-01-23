'use client';

import React, { useState } from 'react';
import { getCurrentUser, getStoredToken } from '@/lib/supabase';
import './AddonPurchaseModal.css';

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
        alert('Sila log masuk semula untuk meneruskan pembayaran.');
        setLoading(false);
        return;
      }

      if (!token) {
        alert('Sesi anda telah tamat. Sila log masuk semula.');
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
        localStorage.setItem('pending_payment_id', data.payment_id);
        localStorage.setItem('pending_addon_id', data.addon_id);

        // Redirect to ToyyibPay
        window.location.href = data.payment_url;
      } else {
        alert('Error: ' + (data.detail || 'Failed to create payment'));
        setLoading(false);
      }
    } catch (error) {
      alert('Error: ' + (error instanceof Error ? error.message : 'Unknown error'));
      setLoading(false);
    }
  };

  if (!show || !addon) return null;

  const total = addon.price * quantity;

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

        {['ai_image', 'ai_hero'].includes(addon.type) && (
          <div className="quantity-selector">
            <label>Kuantiti:</label>
            <select value={quantity} onChange={(e) => setQuantity(parseInt(e.target.value))}>
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
