'use client';

import React, { useState, useEffect } from 'react';
import toast from 'react-hot-toast';
import {
  getCurrentUser,
  getStoredToken,
  verifyEmail,
  resendVerification,
} from '@/lib/supabase';
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

// Throttle resends so a signup/upgrade spike can't burn through the Zoho
// SMTP daily send cap by hammering the resend endpoint.
const RESEND_COOLDOWN_SECONDS = 30;

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
  const [loading, setLoading] = useState(false);

  // Inline email-verification state. When the pay gate reports the user is
  // not verified, we verify right here in the modal and continue straight to
  // payment, instead of navigating away (which lost the upgrade context).
  const [needsVerification, setNeedsVerification] = useState(false);
  const [userEmail, setUserEmail] = useState('');
  const [code, setCode] = useState('');
  const [verifying, setVerifying] = useState(false);
  const [resending, setResending] = useState(false);
  const [cooldown, setCooldown] = useState(0);

  useEffect(() => {
    if (cooldown <= 0) return;
    const t = setTimeout(() => setCooldown((c) => c - 1), 1000);
    return () => clearTimeout(t);
  }, [cooldown]);

  // Send (or resend) the 6-digit code. Respects the resend cooldown and the
  // backend SMTP send cap (resend returns verification_email_sent=false when
  // the send fails / cap is hit, even though the HTTP status is 200).
  const sendCode = async () => {
    if (cooldown > 0 || resending) return;
    setResending(true);
    try {
      const data = await resendVerification();
      if (data?.verification_email_sent === false) {
        toast.error(
          'Tak dapat hantar kod sekarang, cuba lagi sebentar. / ' +
            'Could not send a code right now, please try again shortly.'
        );
      } else {
        toast.success(
          'Kod 6 digit dihantar ke e-mel anda. / A 6-digit code was sent to your email.'
        );
      }
    } catch (error) {
      toast.error(
        error instanceof Error
          ? error.message
          : 'Gagal menghantar kod. / Failed to send code.'
      );
    } finally {
      // Throttle regardless of outcome to respect the SMTP send cap.
      setCooldown(RESEND_COOLDOWN_SECONDS);
      setResending(false);
    }
  };

  // Switch the modal into verification mode and auto-send a fresh code once.
  const enterVerification = (email?: string) => {
    setLoading(false);
    setUserEmail(email || '');
    setNeedsVerification(true);
    void sendCode();
  };

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
        // Email verification gate: verify inline and continue straight to
        // payment, instead of routing away to /verify-email (which dropped
        // the upgrade context and made the user re-navigate).
        enterVerification(user.email);
      } else {
        toast.error(data.detail || 'Failed to create payment');
        setLoading(false);
      }
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Unknown error');
      setLoading(false);
    }
  };

  // Verify the entered code, then continue straight to payment. The draft is
  // held server-side against the user, so nothing is lost across this step.
  const handleVerifyAndContinue = async (e: React.FormEvent) => {
    e.preventDefault();
    const cleaned = code.replace(/\D/g, '');
    if (cleaned.length !== 6) {
      toast.error('Sila masukkan kod 6 digit. / Please enter the 6-digit code.');
      return;
    }

    setVerifying(true);
    try {
      await verifyEmail(cleaned);
      toast.success('E-mel disahkan! / Email verified!');
      setNeedsVerification(false);
      setCode('');
      // Continue to ToyyibPay without navigating away or losing the draft.
      await handleUpgrade();
    } catch (error) {
      toast.error(
        error instanceof Error
          ? error.message
          : 'Kod pengesahan tidak sah. / Invalid verification code.'
      );
    } finally {
      setVerifying(false);
    }
  };

  if (!show || !targetTier) return null;

  const tierPrice = prices[targetTier] || 0;
  const tierFeatures = features[targetTier] || [];
  const isFreeToStarter = (currentTier || '').toLowerCase() === 'free' && targetTier === 'starter';

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="upgrade-modal" onClick={(e) => e.stopPropagation()}>
        <button className="close-btn" onClick={onClose}>×</button>

        {needsVerification ? (
          <>
            <h2>Sahkan e-mel sekarang / Verify email now</h2>
            <p style={{ marginTop: 8, marginBottom: 16, color: '#4b5563' }}>
              Kami telah menghantar kod 6 digit
              {userEmail ? ` ke ${userEmail}` : ' ke e-mel anda'}. Sahkan untuk
              teruskan ke pembayaran.
              <br />
              We sent a 6-digit code{userEmail ? ` to ${userEmail}` : ' to your email'}.
              Verify to continue to payment.
            </p>

            <form onSubmit={handleVerifyAndContinue}>
              <input
                inputMode="numeric"
                autoComplete="one-time-code"
                placeholder="cth. 123456"
                value={code}
                onChange={(e) => setCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                style={{
                  width: '100%',
                  padding: '12px 14px',
                  fontSize: 22,
                  letterSpacing: '0.35em',
                  textAlign: 'center',
                  border: '1px solid #d1d5db',
                  borderRadius: 10,
                  marginBottom: 12,
                  boxSizing: 'border-box',
                }}
              />
              <button
                type="submit"
                className="upgrade-btn"
                disabled={verifying || code.length !== 6}
              >
                {verifying
                  ? 'Mengesahkan... / Verifying...'
                  : 'Sahkan & Teruskan Bayar / Verify & Continue'}
              </button>
            </form>

            <button
              type="button"
              onClick={sendCode}
              disabled={resending || cooldown > 0}
              style={{
                background: 'none',
                border: 'none',
                color: '#4f46e5',
                cursor: resending || cooldown > 0 ? 'not-allowed' : 'pointer',
                fontSize: 14,
                marginTop: 14,
                width: '100%',
              }}
            >
              {cooldown > 0
                ? `Hantar semula kod (${cooldown}s) / Resend code (${cooldown}s)`
                : resending
                ? 'Menghantar... / Sending...'
                : 'Tidak menerima kod? Hantar semula / Resend code'}
            </button>
          </>
        ) : (
          <>
            {isFreeToStarter ? (
              <>
                <h2>Your site looks amazing! 🚀</h2>
                <p style={{ marginTop: 8, marginBottom: 16, color: '#4b5563' }}>
                  Upgrade to Starter (RM5/month) to publish at <strong>yourname.binaapp.my</strong>.
                </p>
              </>
            ) : (
              <h2>Upgrade ke {targetTier.toUpperCase()}</h2>
            )}

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
          </>
        )}
      </div>
    </div>
  );
}

export default UpgradeModal;
