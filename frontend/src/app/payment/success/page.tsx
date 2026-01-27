'use client';

import React, { useEffect, useState, Suspense } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
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
    const userId = localStorage.getItem('user_id');
    const token = localStorage.getItem('token');

    // Check if this is an addon payment
    const pendingAddonType = localStorage.getItem('pending_addon_type');
    const pendingAddonQty = localStorage.getItem('pending_addon_quantity');
    const isAddonPayment = !!pendingAddonType;

    // Use billcode from URL or localStorage
    const effectiveBillCode = billcode || pendingBillCode;

    // If status_id is missing but we have billcode, verify via API
    if (!statusId && effectiveBillCode) {
      console.log('Status ID missing, verifying via API...');
      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'https://binaapp-backend.onrender.com';
        const verifyResponse = await fetch(`${apiUrl}/api/v1/payments/toyyibpay/verify/${effectiveBillCode}`);
        const verifyData = await verifyResponse.json();

        console.log('API verification result:', verifyData);

        if (verifyData.success && verifyData.status === 'paid') {
          setStatus('success');
          setMessage(isAddonPayment ? 'Kredit Addon Berjaya Ditambah!' : 'Pembayaran Berjaya!');

          // Clear all pending data
          localStorage.removeItem('pending_tier');
          localStorage.removeItem('pending_payment_id');
          localStorage.removeItem('pending_bill_code');
          localStorage.removeItem('pending_addon_type');
          localStorage.removeItem('pending_addon_quantity');

          // Redirect after 3 seconds - to /create for website addon, otherwise dashboard
          setTimeout(() => {
            if (isAddonPayment && pendingAddonType === 'website') {
              router.push('/create');
            } else {
              router.push('/dashboard');
            }
          }, 3000);
          return;
        }
      } catch (error) {
        console.error('API verification error:', error);
      }
    }

    // Check payment status from URL parameter
    if (statusId === '1') {
      // Payment successful
      setStatus('success');
      setMessage(isAddonPayment ? 'Kredit Addon Berjaya Ditambah!' : 'Pembayaran Berjaya!');

      // Update subscription if it was a subscription payment (not addon)
      if (!isAddonPayment && tier && paymentId) {
        try {
          const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'https://binaapp-backend.onrender.com';
          await fetch(`${apiUrl}/api/v1/payments/subscriptions/upgrade/${tier}`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({
              user_id: userId,
              payment_id: paymentId
            })
          });
        } catch (error) {
          console.error('Upgrade error:', error);
        }
      }

      // Clear all pending data
      localStorage.removeItem('pending_tier');
      localStorage.removeItem('pending_payment_id');
      localStorage.removeItem('pending_bill_code');
      localStorage.removeItem('pending_addon_type');
      localStorage.removeItem('pending_addon_quantity');

      // Redirect after 3 seconds - to /create for website addon, otherwise dashboard
      setTimeout(() => {
        if (isAddonPayment && pendingAddonType === 'website') {
          router.push('/create');
        } else {
          router.push('/dashboard');
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
      // Unknown status - try to verify via API if we have billcode
      if (effectiveBillCode) {
        try {
          const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'https://binaapp-backend.onrender.com';
          const verifyResponse = await fetch(`${apiUrl}/api/v1/payments/toyyibpay/verify/${effectiveBillCode}`);
          const verifyData = await verifyResponse.json();

          if (verifyData.success && verifyData.status === 'paid') {
            setStatus('success');
            setMessage(isAddonPayment ? 'Kredit Addon Berjaya Ditambah!' : 'Pembayaran Berjaya!');
            localStorage.removeItem('pending_tier');
            localStorage.removeItem('pending_payment_id');
            localStorage.removeItem('pending_bill_code');
            localStorage.removeItem('pending_addon_type');
            localStorage.removeItem('pending_addon_quantity');
            setTimeout(() => {
              if (isAddonPayment && pendingAddonType === 'website') {
                router.push('/create');
              } else {
                router.push('/dashboard');
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
