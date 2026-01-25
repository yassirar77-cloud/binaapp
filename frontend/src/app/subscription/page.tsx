'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

/**
 * Subscription page - redirects to /dashboard/billing
 * This provides a cleaner URL for users while using the existing billing page
 */
export default function SubscriptionPage() {
  const router = useRouter();

  useEffect(() => {
    router.replace('/dashboard/billing');
  }, [router]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="text-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
        <p className="text-gray-600">Mengalihkan ke halaman langganan...</p>
      </div>
    </div>
  );
}
