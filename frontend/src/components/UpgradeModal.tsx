'use client';

import React, { useState, useEffect } from 'react';
import toast from 'react-hot-toast';
import { Check, MailCheck, Rocket } from 'lucide-react';
import { Modal } from '@/components/ui/popups';
import {
  getCurrentUser,
  getStoredToken,
  verifyEmail,
  resendVerification,
} from '@/lib/supabase';

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

// `basic` was retired from sale (backend rejects new basic purchases) but
// stays here so a stale targetTier never renders an empty modal.
const features: Record<string, string[]> = {
  starter: [
    '1 website',
    '20 menu items',
    'Imej AI percuma',
    'WhatsApp + troli',
    '1 delivery zone'
  ],
  basic: [
    '5 websites',
    'Unlimited menu',
    'Imej AI percuma',
    '5 delivery zones',
    'QR Payment',
    'Borang Hubungi'
  ],
  pro: [
    'Unlimited websites & menu',
    'Imej AI percuma',
    'Unlimited zones',
    'Rider GPS (10 riders)',
    'Order dashboard & chat',
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

  const tierPrice = prices[targetTier] || 0;
  const tierFeatures = features[targetTier] || [];
  const isFreeToStarter = (currentTier || '').toLowerCase() === 'free' && targetTier === 'starter';

  const primaryBtn =
    'inline-flex h-11 w-full items-center justify-center rounded-xl bg-volt-400 px-4 text-sm font-semibold text-ink-900 transition-colors hover:bg-volt-300 active:bg-volt-500 disabled:cursor-not-allowed disabled:opacity-60';

  return (
    <Modal open={show && !!targetTier} onClose={onClose} size="sm">
      {needsVerification ? (
        <>
          <div
            className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-2xl bg-info-400/15 text-info-400"
            aria-hidden="true"
          >
            <MailCheck className="h-6 w-6" />
          </div>
          <h2 className="text-center font-geist text-lg font-bold tracking-tight text-ink-050">
            Sahkan e-mel sekarang / Verify email now
          </h2>
          <p className="mx-auto mt-2 max-w-sm text-center text-sm leading-relaxed text-ink-300">
            Kami telah menghantar kod 6 digit
            {userEmail ? ` ke ${userEmail}` : ' ke e-mel anda'}. Sahkan untuk
            teruskan ke pembayaran.
            <br />
            We sent a 6-digit code{userEmail ? ` to ${userEmail}` : ' to your email'}.
            Verify to continue to payment.
          </p>

          <form className="mt-5" onSubmit={handleVerifyAndContinue}>
            <input
              inputMode="numeric"
              autoComplete="one-time-code"
              placeholder="cth. 123456"
              value={code}
              onChange={(e) => setCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
              data-autofocus
              className="w-full rounded-xl bg-white/[0.04] px-3 py-3 text-center font-geist-mono text-xl font-semibold tracking-[0.35em] text-ink-050 ring-1 ring-white/[0.08] placeholder:tracking-normal placeholder:text-ink-500 focus:outline-none focus:ring-2 focus:ring-volt-400/60"
            />
            <button
              type="submit"
              className={`mt-4 ${primaryBtn}`}
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
            className="mt-4 w-full text-center text-sm font-medium text-volt-400 transition-colors hover:text-volt-300 disabled:cursor-not-allowed disabled:text-ink-500"
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
          <div
            className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-2xl bg-volt-400/15 text-volt-400"
            aria-hidden="true"
          >
            <Rocket className="h-6 w-6" />
          </div>

          {isFreeToStarter ? (
            <>
              <h2 className="text-center font-geist text-lg font-bold tracking-tight text-ink-050">
                Your site looks amazing! 🚀
              </h2>
              <p className="mx-auto mt-2 max-w-sm text-center text-sm leading-relaxed text-ink-300">
                Upgrade to Starter (RM5/month) to publish at{' '}
                <strong className="text-ink-100">yourname.binaapp.my</strong>.
              </p>
            </>
          ) : (
            <h2 className="text-center font-geist text-lg font-bold tracking-tight text-ink-050">
              Upgrade ke {targetTier.toUpperCase()}
            </h2>
          )}

          <div className="mt-4 flex items-baseline justify-center gap-1 rounded-2xl bg-white/[0.04] py-4 ring-1 ring-volt-400/40">
            <span className="font-geist text-3xl font-bold text-volt-400">RM {tierPrice}</span>
            <span className="text-sm text-ink-400">/bulan</span>
          </div>

          <div className="mt-5">
            <h3 className="text-sm font-semibold text-ink-100">Anda akan dapat:</h3>
            <ul className="mt-3 space-y-2.5">
              {tierFeatures.map((feature, i) => (
                <li key={i} className="flex items-start gap-2.5 text-sm text-ink-200">
                  <Check className="mt-0.5 h-4 w-4 shrink-0 text-volt-400" aria-hidden="true" />
                  {feature}
                </li>
              ))}
            </ul>
          </div>

          <button
            type="button"
            className={`mt-6 ${primaryBtn}`}
            onClick={handleUpgrade}
            disabled={loading}
          >
            {loading ? 'Memproses...' : `Upgrade Sekarang - RM${tierPrice}`}
          </button>

          <p className="mt-3 text-center text-xs text-ink-400">
            Anda akan diarahkan ke ToyyibPay untuk pembayaran selamat.
          </p>
        </>
      )}
    </Modal>
  );
}

export default UpgradeModal;
