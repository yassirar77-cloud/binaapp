'use client';

import React, { useState } from 'react';
import './UpgradeModal.css';

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
    'Custom domain',
    'API access'
  ]
};

export function UpgradeModal({ show, currentTier, targetTier, onClose }: UpgradeModalProps) {
  const [loading, setLoading] = useState(false);

  const handleUpgrade = async () => {
    setLoading(true);

    try {
      const userId = localStorage.getItem('user_id');
      const token = localStorage.getItem('token');

      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || ''}/api/payments/subscribe/${targetTier}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          user_id: userId ? parseInt(userId) : null
        })
      });

      const data = await response.json();

      if (data.success) {
        // Save payment ID for verification later
        localStorage.setItem('pending_payment_id', data.payment_id);
        localStorage.setItem('pending_tier', targetTier);

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

  if (!show || !targetTier) return null;

  const tierPrice = prices[targetTier] || 0;
  const tierFeatures = features[targetTier] || [];

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="upgrade-modal" onClick={(e) => e.stopPropagation()}>
        <button className="close-btn" onClick={onClose}>×</button>

        <h2>Upgrade ke {targetTier.toUpperCase()}</h2>

        <div className="price-box">
          <div className="price">RM {tierPrice}</div>
          <div className="period">/bulan</div>
        </div>

        <div className="features-list">
          <h3>Anda akan dapat:</h3>
          {tierFeatures.map((feature, i) => (
            <div key={i} className="feature-item">
              <span className="check">✓</span> {feature}
            </div>
          ))}
        </div>

        <button
          className="upgrade-btn"
          onClick={handleUpgrade}
          disabled={loading}
        >
          {loading ? 'Memproses...' : `Upgrade Sekarang - RM${tierPrice}`}
        </button>

        <p className="note">
          Anda akan diarahkan ke ToyyibPay untuk pembayaran selamat.
        </p>
      </div>
    </div>
  );
}

export default UpgradeModal;
