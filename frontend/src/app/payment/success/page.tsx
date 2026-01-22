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

    // Check payment status
    if (statusId === '1') {
      // Payment successful
      setStatus('success');
      setMessage('Pembayaran Berjaya!');

      // Update subscription if it was a subscription payment
      const tier = localStorage.getItem('pending_tier');
      const paymentId = localStorage.getItem('pending_payment_id');
      const userId = localStorage.getItem('user_id');
      const token = localStorage.getItem('token');

      if (tier && paymentId) {
        try {
          await fetch(`${process.env.NEXT_PUBLIC_API_URL || ''}/api/subscriptions/upgrade/${tier}`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({
              user_id: userId ? parseInt(userId) : null,
              payment_id: parseInt(paymentId)
            })
          });

          // Clear pending data
          localStorage.removeItem('pending_tier');
          localStorage.removeItem('pending_payment_id');

        } catch (error) {
          console.error('Upgrade error:', error);
        }
      }

      // Redirect after 3 seconds
      setTimeout(() => {
        router.push('/dashboard');
      }, 3000);

    } else if (statusId === '3') {
      // Payment failed
      setStatus('failed');
      setMessage('Pembayaran Gagal');

    } else {
      // Pending or unknown
      setStatus('pending');
      setMessage('Pembayaran dalam proses...');
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
          <h2>Pembayaran Berjaya!</h2>
          <p>Terima kasih. Package anda telah dikemaskini.</p>
          <p>Mengalih ke dashboard...</p>
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
