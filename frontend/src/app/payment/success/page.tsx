'use client';

import React, { useEffect, useState, Suspense } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { getStoredToken, getApiAuthToken, supabase } from '@/lib/supabase';
import './PaymentSuccess.css';

function PaymentSuccessContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const [status, setStatus] = useState('checking');
  const [message, setMessage] = useState('Memeriksa pembayaran...');

  useEffect(() => {
    verifyPayment();
  }, []);

  const verifyPayment = async () => {
    const statusId = searchParams.get('status_id');
    const billcode = searchParams.get('billcode');
    const orderNo = searchParams.get('order_id');
    const transactionId = searchParams.get('transaction_id');

    console.log('Payment callback params:', { statusId, billcode, orderNo, transactionId });

    // Get stored payment info
    const tier = localStorage.getItem('pending_tier');
    const paymentId = localStorage.getItem('pending_payment_id');
    const pendingBillCode = localStorage.getItem('pending_bill_code');

    // Check if this is an addon payment
    const pendingAddonType = localStorage.getItem('pending_addon_type');
    const pendingAddonQty = localStorage.getItem('pending_addon_quantity');
    const isAddonPayment = !!pendingAddonType;

    // Use billcode from URL or localStorage
    const effectiveBillCode = billcode || pendingBillCode;

    // =========================================================================
    // SESSION RECOVERY - Try to restore session after external redirect
    // =========================================================================
    let authToken = getStoredToken();

    // If no stored token, try to get from Supabase session
    if (!authToken && supabase) {
      try {
        console.log('No stored token, attempting Supabase session recovery...');
        const { data: { session } } = await supabase.auth.getSession();

        if (session?.access_token) {
          authToken = session.access_token;
          console.log('Session recovered from Supabase');
        } else {
          // Try to refresh the session
          console.log('No session, attempting refresh...');
          const { data: { session: refreshedSession } } = await supabase.auth.refreshSession();

          if (refreshedSession?.access_token) {
            authToken = refreshedSession.access_token;
            console.log('Session refreshed successfully');
          }
        }
      } catch (error) {
        console.error('Session recovery error:', error);
      }
    }

    // If still no auth token, store pending payment and redirect to login
    if (!authToken) {
      console.log('No session found, storing pending payment for later verification');

      // Store pending payment verification data
      if (effectiveBillCode) {
        localStorage.setItem('pendingPaymentVerification', JSON.stringify({
          billCode: effectiveBillCode,
          statusId: statusId,
          tier: tier,
          isAddonPayment: isAddonPayment,
          addonType: pendingAddonType,
          addonQuantity: pendingAddonQty,
          timestamp: Date.now()
        }));
      }

      setStatus('redirect');
      setMessage('Sesi tamat. Mengalih ke halaman log masuk...');

      setTimeout(() => {
        router.push('/login?redirect=/dashboard&payment=pending');
      }, 2000);
      return;
    }

    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'https://binaapp-backend.onrender.com';

    // =========================================================================
    // VERIFY PAYMENT - Call backend to verify and process payment
    // =========================================================================

    // If we have billcode, verify with backend
    if (effectiveBillCode) {
      try {
        console.log('Verifying payment with backend...', { billCode: effectiveBillCode, statusId });

        const verifyResponse = await fetch(`${apiUrl}/api/v1/subscription/verify-payment`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${authToken}`
          },
          body: JSON.stringify({
            bill_code: effectiveBillCode,
            status_id: statusId
          })
        });

        const verifyData = await verifyResponse.json();
        console.log('Backend verification result:', verifyData);

        if (verifyData.success && verifyData.payment_status === 'paid') {
          setStatus('success');
          setMessage(isAddonPayment ? 'Kredit Addon Berjaya Ditambah!' : 'Pembayaran Berjaya!');

          // Clear all pending data
          clearPendingPaymentData();

          // Redirect after 3 seconds - to /create for website addon, otherwise dashboard
          setTimeout(() => {
            if (isAddonPayment && pendingAddonType === 'website') {
              router.push('/create?payment=success');
            } else {
              router.push('/dashboard?payment=success');
            }
          }, 3000);
          return;
        } else if (verifyData.payment_status === 'pending') {
          setStatus('pending');
          setMessage('Pembayaran dalam proses...');
          return;
        } else if (verifyData.payment_status === 'failed') {
          setStatus('failed');
          setMessage('Pembayaran Gagal');
          return;
        }
      } catch (error) {
        console.error('Backend verification error:', error);
        // Fall through to status_id check
      }
    }

    // =========================================================================
    // FALLBACK - Check payment status from URL parameter
    // =========================================================================
    if (statusId === '1') {
      // Payment successful
      setStatus('success');
      setMessage(isAddonPayment ? 'Kredit Addon Berjaya Ditambah!' : 'Pembayaran Berjaya!');

      // Update subscription if it was a subscription payment (not addon)
      if (!isAddonPayment && tier && paymentId) {
        try {
          await fetch(`${apiUrl}/api/v1/payments/subscriptions/upgrade/${tier}`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'Authorization': `Bearer ${authToken}`
            },
            body: JSON.stringify({
              payment_id: paymentId
            })
          });
        } catch (error) {
          console.error('Upgrade error:', error);
        }
      }

      // Clear all pending data
      clearPendingPaymentData();

      // Redirect after 3 seconds - to /create for website addon, otherwise dashboard
      setTimeout(() => {
        if (isAddonPayment && pendingAddonType === 'website') {
          router.push('/create?payment=success');
        } else {
          router.push('/dashboard?payment=success');
        }
      }, 3000);

    } else if (statusId === '3') {
      // Payment failed
      setStatus('failed');
      setMessage('Pembayaran Gagal');

    } else if (statusId === '2') {
      // Pending
      setStatus('pending');
      setMessage('Pembayaran dalam proses...');

    } else {
      // Unknown status - try to verify via legacy API if we have billcode
      if (effectiveBillCode) {
        try {
          const verifyResponse = await fetch(`${apiUrl}/api/v1/payments/toyyibpay/verify/${effectiveBillCode}`);
          const verifyData = await verifyResponse.json();

          if (verifyData.success && verifyData.status === 'paid') {
            setStatus('success');
            setMessage(isAddonPayment ? 'Kredit Addon Berjaya Ditambah!' : 'Pembayaran Berjaya!');
            clearPendingPaymentData();
            setTimeout(() => {
              if (isAddonPayment && pendingAddonType === 'website') {
                router.push('/create?payment=success');
              } else {
                router.push('/dashboard?payment=success');
              }
            }, 3000);
            return;
          } else if (verifyData.status === 'pending') {
            setStatus('pending');
            setMessage('Pembayaran dalam proses...');
            return;
          }
        } catch (error) {
          console.error('API verification error:', error);
        }
      }

      // Default to pending if we can't determine status
      setStatus('pending');
      setMessage('Sila tunggu pengesahan pembayaran...');
    }
  };

  // Helper function to clear all pending payment data
  const clearPendingPaymentData = () => {
    localStorage.removeItem('pending_tier');
    localStorage.removeItem('pending_payment_id');
    localStorage.removeItem('pending_bill_code');
    localStorage.removeItem('pending_addon_type');
    localStorage.removeItem('pending_addon_quantity');
    localStorage.removeItem('pendingPaymentVerification');
  };

  return (
    <div className="payment-result">
      {status === 'checking' && (
        <div className="checking">
          <div className="spinner"></div>
          <h2>{message}</h2>
        </div>
      )}

      {status === 'success' && (
        <div className="success">
          <div className="checkmark">✓</div>
          <h2>{message}</h2>
          <p>Terima kasih atas pembayaran anda.</p>
          <p>Mengalih...</p>
        </div>
      )}

      {status === 'failed' && (
        <div className="failed">
          <div className="cross">✗</div>
          <h2>Pembayaran Gagal</h2>
          <p>Sila cuba lagi.</p>
          <button onClick={() => router.push('/dashboard')}>Kembali</button>
        </div>
      )}

      {status === 'pending' && (
        <div className="pending">
          <div className="spinner"></div>
          <h2>{message}</h2>
          <p>Sila tunggu...</p>
        </div>
      )}

      {status === 'redirect' && (
        <div className="pending">
          <div className="spinner"></div>
          <h2>{message}</h2>
          <p>Pembayaran akan disahkan selepas log masuk.</p>
        </div>
      )}
    </div>
  );
}

export default function PaymentSuccess() {
  return (
    <Suspense fallback={
      <div className="payment-result">
        <div className="checking">
          <div className="spinner"></div>
          <h2>Memuatkan...</h2>
        </div>
      </div>
    }>
      <PaymentSuccessContent />
    </Suspense>
  );
}
