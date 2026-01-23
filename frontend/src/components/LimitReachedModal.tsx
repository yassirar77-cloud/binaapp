'use client';

import React, { useState } from 'react';
import { getCurrentUser, getStoredToken } from '@/lib/supabase';
import './LimitReachedModal.css';

interface LimitReachedModalProps {
  show: boolean;
  onClose: () => void;
  resourceType: 'website' | 'menu_item' | 'ai_hero' | 'ai_image' | 'zone' | 'rider';
  currentUsage: number;
  limit: number;
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
      '10 rider dengan GPS',
      'Domain tersuai',
      'Akses API'
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

  if (!show) return null;

  const resource = resourceLabels[resourceType];
  const addonType = addonTypes[resourceType];

  const handleUpgrade = async (tier: string) => {
    setLoading(true);
    try {
      const user = await getCurrentUser();
      const token = getStoredToken();

      if (!user?.id || !token) {
        alert('Sila log masuk semula');
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
        alert('Ralat: ' + (data.detail?.message || data.detail || 'Gagal mencipta pembayaran'));
      }
    } catch (error) {
      console.error('Upgrade error:', error);
      alert('Ralat semasa memproses naik taraf');
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
        alert('Sila log masuk semula');
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
        alert('Ralat: ' + (data.detail?.message || data.detail || 'Gagal mencipta pembayaran'));
      }
    } catch (error) {
      console.error('Addon purchase error:', error);
      alert('Ralat semasa memproses pembelian');
    } finally {
      setLoading(false);
    }
  };

  const totalAddonPrice = (addonPrice || 0) * addonQuantity;

  return (
    <div className="limit-modal-overlay" onClick={onClose}>
      <div className="limit-modal" onClick={(e) => e.stopPropagation()}>
        <button className="close-btn" onClick={onClose}>&times;</button>

        <div className="limit-modal-header">
          <div className="warning-icon">!</div>
          <h2>Had Tercapai</h2>
          <p>
            Anda telah mencapai had {resource.nameMalay} pelan anda
            <span className="usage-count">({currentUsage}/{limit})</span>
          </p>
        </div>

        <div className="limit-modal-options">
          {/* Option Toggle */}
          <div className="option-toggle">
            <button
              className={`toggle-btn ${selectedOption === 'upgrade' ? 'active' : ''}`}
              onClick={() => setSelectedOption('upgrade')}
            >
              Naik Taraf Pelan
            </button>
            {canBuyAddon && addonPrice && (
              <button
                className={`toggle-btn ${selectedOption === 'addon' ? 'active' : ''}`}
                onClick={() => setSelectedOption('addon')}
              >
                Beli Addon
              </button>
            )}
          </div>

          {/* Upgrade Options */}
          {selectedOption === 'upgrade' && (
            <div className="upgrade-options">
              {upgradePlans.map((plan) => (
                <div key={plan.tier} className={`plan-card ${plan.tier}`}>
                  <div className="plan-header">
                    <h3>{plan.name}</h3>
                    <div className="plan-price">
                      <span className="currency">RM</span>
                      <span className="amount">{plan.price}</span>
                      <span className="period">/bulan</span>
                    </div>
                  </div>
                  <ul className="plan-features">
                    {plan.features.map((feature, i) => (
                      <li key={i}>
                        <span className="check">&#x2713;</span>
                        {feature}
                      </li>
                    ))}
                  </ul>
                  <button
                    className="plan-btn"
                    onClick={() => handleUpgrade(plan.tier)}
                    disabled={loading}
                  >
                    {loading ? 'Memproses...' : `Naik Taraf ke ${plan.name}`}
                  </button>
                </div>
              ))}
            </div>
          )}

          {/* Addon Options */}
          {selectedOption === 'addon' && canBuyAddon && addonPrice && (
            <div className="addon-options">
              <div className="addon-card">
                <div className="addon-info">
                  <h3>{resource.nameMalay} Tambahan</h3>
                  <p className="addon-price">
                    RM {addonPrice.toFixed(2)} / unit
                  </p>
                </div>

                <div className="quantity-selector">
                  <label>Kuantiti:</label>
                  <div className="quantity-controls">
                    <button
                      onClick={() => setAddonQuantity(Math.max(1, addonQuantity - 1))}
                      disabled={addonQuantity <= 1}
                    >
                      -
                    </button>
                    <span>{addonQuantity}</span>
                    <button onClick={() => setAddonQuantity(addonQuantity + 1)}>
                      +
                    </button>
                  </div>
                </div>

                <div className="addon-total">
                  <span>Jumlah:</span>
                  <span className="total-price">RM {totalAddonPrice.toFixed(2)}</span>
                </div>

                <button
                  className="addon-btn"
                  onClick={handleBuyAddon}
                  disabled={loading}
                >
                  {loading ? 'Memproses...' : `Beli Sekarang - RM ${totalAddonPrice.toFixed(2)}`}
                </button>

                <p className="addon-note">
                  Kredit addon boleh digunakan bila-bila masa dan tidak akan tamat tempoh.
                </p>
              </div>
            </div>
          )}
        </div>

        <p className="modal-footer-note">
          Anda akan diarahkan ke ToyyibPay untuk pembayaran selamat.
        </p>
      </div>
    </div>
  );
}

export default LimitReachedModal;
