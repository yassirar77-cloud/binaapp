'use client';

import { useState, useEffect } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { supabase, getCurrentUser, getStoredToken } from '@/lib/supabase';
import Link from 'next/link';
import AnalyticsDashboard from '@/components/AnalyticsDashboard';

// Backend API URL
const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'https://binaapp-backend.onrender.com';

interface Website {
  id: string;
  name: string;
  subdomain: string | null;
  user_id: string;
}

export default function AnalyticsPage() {
  const params = useParams();
  const id = params.id as string;
  const router = useRouter();

  const [loading, setLoading] = useState(true);
  const [website, setWebsite] = useState<Website | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadWebsite();
  }, [id]);

  async function loadWebsite() {
    try {
      setLoading(true);

      // First check for custom BinaApp token
      const customToken = getStoredToken();
      const customUser = await getCurrentUser();

      if (customToken && customUser) {
        console.log('[Analytics] ✅ Using custom BinaApp auth');

        // Fetch website using backend API
        const response = await fetch(`${API_BASE}/api/v1/websites/${id}`, {
          headers: {
            'Authorization': `Bearer ${customToken}`,
            'Content-Type': 'application/json'
          }
        });

        if (response.status === 401) {
          router.push('/login');
          return;
        }

        if (response.ok) {
          const data = await response.json();
          setWebsite(data);
        } else {
          setError('Website tidak dijumpai');
          setTimeout(() => router.push('/my-projects'), 2000);
        }
        return;
      }

      // Fallback to Supabase session
      if (!supabase) {
        setError('Sila log masuk');
        router.push('/login');
        return;
      }

      const { data: { session } } = await supabase.auth.getSession();
      if (!session) {
        router.push('/login');
        return;
      }

      // Fetch website data using Supabase
      const { data, error } = await supabase
        .from('websites')
        .select('*')
        .eq('id', id)
        .eq('user_id', session.user.id)
        .single();

      if (error || !data) {
        setError('Website tidak dijumpai');
        setTimeout(() => router.push('/my-projects'), 2000);
        return;
      }

      setWebsite(data);
    } catch (e) {
      console.error('Error loading website:', e);
      setError('Ralat memuatkan website');
    } finally {
      setLoading(false);
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="animate-spin h-12 w-12 border-4 border-blue-500 border-t-transparent rounded-full mx-auto mb-4"></div>
          <p className="text-gray-600">Loading analytics...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="text-6xl mb-4">⚠️</div>
          <h1 className="text-2xl font-bold text-gray-800 mb-2">{error}</h1>
          <p className="text-gray-500 mb-4">Redirecting to projects...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b sticky top-0 z-40">
        <nav className="container mx-auto px-4 h-16 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2">
            <span className="text-2xl">✨</span>
            <span className="text-xl font-bold">BinaApp</span>
          </Link>
          <div className="flex items-center gap-4">
            <Link href="/my-projects" className="text-sm text-gray-600 hover:text-gray-900">
              My Projects
            </Link>
            <Link href="/create" className="text-sm text-gray-600 hover:text-gray-900">
              Create Website
            </Link>
          </div>
        </nav>
      </header>

      <div className="py-8">
        <div className="max-w-7xl mx-auto px-4">
          {/* Page Header */}
          <div className="mb-6">
            <Link
              href="/my-projects"
              className="inline-flex items-center text-blue-500 hover:text-blue-600 mb-4"
            >
              <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
              Back to Projects
            </Link>
            <h1 className="text-3xl font-bold text-gray-900 mb-1">
              {website?.name || 'Analytics'}
            </h1>
            {website?.subdomain && (
              <p className="text-gray-500">
                <a
                  href={`https://${website.subdomain}.binaapp.my`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="hover:underline"
                >
                  {website.subdomain}.binaapp.my ↗
                </a>
              </p>
            )}
          </div>

          {/* Analytics Dashboard */}
          {website && (
            <AnalyticsDashboard projectId={website.id} />
          )}
        </div>
      </div>
    </div>
  );
}
