'use client';

import { useState, useEffect, useCallback } from 'react';
import { createClientComponentClient } from '@supabase/auth-helpers-nextjs';
import { useRouter } from 'next/navigation';

export default function ProfilePage() {
  const supabase = createClientComponentClient();
  const router = useRouter();

  const [loading, setLoading] = useState(true);
  const [user, setUser] = useState<any>(null);
  const [profile, setProfile] = useState({ full_name: '', business_name: '', phone: '' });
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState('');

  const checkAuth = useCallback(async () => {
    try {
      // Method 1: Try getSession first
      const { data: { session }, error: sessionError } = await supabase.auth.getSession();

      if (session?.user) {
        console.log('Auth via getSession:', session.user.email);
        return session.user;
      }

      // Method 2: Try getUser as fallback
      const { data: { user }, error: userError } = await supabase.auth.getUser();

      if (user) {
        console.log('Auth via getUser:', user.email);
        return user;
      }

      // Method 3: Check for stored session
      const storedSession = localStorage.getItem('supabase.auth.token');
      if (storedSession) {
        const parsed = JSON.parse(storedSession);
        if (parsed?.currentSession?.user) {
          console.log('Auth via localStorage:', parsed.currentSession.user.email);
          return parsed.currentSession.user;
        }
      }

      console.log('No auth found');
      return null;
    } catch (err) {
      console.error('Auth check error:', err);
      return null;
    }
  }, [supabase]);

  useEffect(() => {
    let mounted = true;

    const init = async () => {
      // Wait a bit for auth to initialize
      await new Promise(resolve => setTimeout(resolve, 100));

      const authUser = await checkAuth();

      if (!mounted) return;

      if (!authUser) {
        console.log('No user found, redirecting to login');
        router.replace('/login');
        return;
      }

      setUser(authUser);

      // Load profile
      try {
        const { data, error } = await supabase
          .from('profiles')
          .select('*')
          .eq('id', authUser.id)
          .single();

        if (data && mounted) {
          setProfile({
            full_name: data.full_name || '',
            business_name: data.business_name || '',
            phone: data.phone || ''
          });
        }
      } catch (err) {
        console.error('Profile load error:', err);
      }

      if (mounted) setLoading(false);
    };

    init();

    // Listen for auth changes
    const { data: { subscription } } = supabase.auth.onAuthStateChange(async (event, session) => {
      console.log('Auth state changed:', event);

      if (event === 'SIGNED_OUT') {
        router.replace('/login');
      } else if (event === 'SIGNED_IN' && session?.user) {
        setUser(session.user);
        setLoading(false);
      }
    });

    return () => {
      mounted = false;
      subscription.unsubscribe();
    };
  }, [supabase, router, checkAuth]);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!user) return;

    setSaving(true);
    setMessage('');

    try {
      const { error } = await supabase
        .from('profiles')
        .upsert({
          id: user.id,
          email: user.email,
          full_name: profile.full_name,
          business_name: profile.business_name,
          phone: profile.phone,
          updated_at: new Date().toISOString()
        });

      if (error) throw error;

      setMessage('✅ Berjaya disimpan!');
    } catch (err: any) {
      console.error('Save error:', err);
      setMessage('❌ Ralat: ' + err.message);
    } finally {
      setSaving(false);
      setTimeout(() => setMessage(''), 3000);
    }
  };

  // Loading state
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="animate-spin h-12 w-12 border-4 border-blue-500 border-t-transparent rounded-full mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading profile...</p>
        </div>
      </div>
    );
  }

  // No user - this shouldn't show if redirect works
  if (!user) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <p className="text-gray-600 mb-4">Sila log masuk untuk melihat profil</p>
          <button
            onClick={() => router.push('/login')}
            className="px-6 py-2 bg-blue-500 text-white rounded-lg"
          >
            Log Masuk
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 py-8 px-4">
      <div className="max-w-md mx-auto bg-white rounded-xl shadow-lg p-6">
        <h1 className="text-2xl font-bold mb-6">👤 Profil Saya</h1>

        {message && (
          <div className={`p-3 rounded-lg mb-4 ${
            message.includes('❌') ? 'bg-red-100 text-red-700' : 'bg-green-100 text-green-700'
          }`}>
            {message}
          </div>
        )}

        <form onSubmit={handleSave} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
            <input
              type="email"
              value={user.email || ''}
              disabled
              className="w-full p-3 bg-gray-100 rounded-lg text-gray-600"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Nama Penuh</label>
            <input
              type="text"
              value={profile.full_name}
              onChange={(e) => setProfile({ ...profile, full_name: e.target.value })}
              className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder="Masukkan nama anda"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Nama Perniagaan</label>
            <input
              type="text"
              value={profile.business_name}
              onChange={(e) => setProfile({ ...profile, business_name: e.target.value })}
              className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder="Nama kedai / perniagaan"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">No. Telefon</label>
            <input
              type="tel"
              value={profile.phone}
              onChange={(e) => setProfile({ ...profile, phone: e.target.value })}
              className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder="012-345 6789"
            />
          </div>

          <button
            type="submit"
            disabled={saving}
            className="w-full py-3 bg-blue-500 hover:bg-blue-600 text-white font-medium rounded-lg disabled:opacity-50 transition-colors"
          >
            {saving ? (
              <span className="flex items-center justify-center gap-2">
                <div className="animate-spin h-4 w-4 border-2 border-white border-t-transparent rounded-full"></div>
                Menyimpan...
              </span>
            ) : (
              '💾 Simpan Profil'
            )}
          </button>
        </form>

        <button
          onClick={() => router.push('/my-projects')}
          className="w-full mt-4 py-3 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
        >
          ← Kembali ke Projek
        </button>

        <button
          onClick={async () => {
            await supabase.auth.signOut();
            router.replace('/login');
          }}
          className="w-full mt-2 py-3 text-red-500 hover:bg-red-50 rounded-lg transition-colors"
        >
          🚪 Log Keluar
        </button>
      </div>
    </div>
  );
}
