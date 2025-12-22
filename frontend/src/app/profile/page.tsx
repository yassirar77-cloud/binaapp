'use client';

import { useState, useEffect, Suspense } from 'react';
import { useRouter } from 'next/navigation';
import dynamic from 'next/dynamic';

// Force no prerendering
export const runtime = 'edge';

function ProfilePageContent() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [user, setUser] = useState<any>(null);
  const [profile, setProfile] = useState({
    full_name: '',
    business_name: '',
    phone: '',
    address: '',
    city: '',
    state: '',
  });
  const [message, setMessage] = useState({ type: '', text: '' });

  useEffect(() => {
    getProfile();
  }, []);

  async function getProfile() {
    try {
      setLoading(true);

      const { createClientComponentClient } = await import('@supabase/auth-helpers-nextjs');
      const supabase = createClientComponentClient();

      // Use getSession() for more reliable auth check
      const { data: { session } } = await supabase.auth.getSession();

      if (!session) {
        console.log('No session found, redirecting to login');
        router.push('/login');
        return;
      }

      const user = session.user;
      setUser(user);

      const { data, error } = await supabase
        .from('profiles')
        .select('*')
        .eq('id', user.id)
        .single();

      if (data) {
        setProfile({
          full_name: data.full_name || '',
          business_name: data.business_name || '',
          phone: data.phone || '',
          address: data.address || '',
          city: data.city || '',
          state: data.state || '',
        });
      }
    } catch (error) {
      console.error('Error:', error);
      router.push('/login');
    } finally {
      setLoading(false);
    }
  }

  async function updateProfile(e: React.FormEvent) {
    e.preventDefault();

    try {
      setSaving(true);
      setMessage({ type: '', text: '' });

      const { createClientComponentClient } = await import('@supabase/auth-helpers-nextjs');
      const supabase = createClientComponentClient();

      const { error } = await supabase
        .from('profiles')
        .upsert({
          id: user.id,
          email: user.email,
          ...profile,
          updated_at: new Date().toISOString(),
        });

      if (error) throw error;

      setMessage({ type: 'success', text: 'Profil berjaya dikemaskini!' });
    } catch (error) {
      console.error('Error:', error);
      setMessage({ type: 'error', text: 'Ralat mengemaskini profil.' });
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 py-12">
      <div className="max-w-2xl mx-auto px-4">
        <div className="bg-white rounded-xl shadow-lg p-8">
          <h1 className="text-2xl font-bold text-gray-800 mb-6">Profil Saya</h1>

          {message.text && (
            <div className={`p-4 rounded-lg mb-6 ${message.type === 'success' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
              {message.text}
            </div>
          )}

          <form onSubmit={updateProfile} className="space-y-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Email</label>
              <input type="email" value={user?.email || ''} disabled className="w-full px-4 py-3 border rounded-lg bg-gray-50" />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Nama Penuh</label>
              <input type="text" value={profile.full_name} onChange={(e) => setProfile({ ...profile, full_name: e.target.value })} className="w-full px-4 py-3 border rounded-lg" />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Nama Perniagaan</label>
              <input type="text" value={profile.business_name} onChange={(e) => setProfile({ ...profile, business_name: e.target.value })} className="w-full px-4 py-3 border rounded-lg" />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Telefon</label>
              <input type="tel" value={profile.phone} onChange={(e) => setProfile({ ...profile, phone: e.target.value })} className="w-full px-4 py-3 border rounded-lg" />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Alamat</label>
              <textarea value={profile.address} onChange={(e) => setProfile({ ...profile, address: e.target.value })} rows={3} className="w-full px-4 py-3 border rounded-lg" />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Bandar</label>
                <input type="text" value={profile.city} onChange={(e) => setProfile({ ...profile, city: e.target.value })} className="w-full px-4 py-3 border rounded-lg" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Negeri</label>
                <select value={profile.state} onChange={(e) => setProfile({ ...profile, state: e.target.value })} className="w-full px-4 py-3 border rounded-lg">
                  <option value="">Pilih</option>
                  <option value="Selangor">Selangor</option>
                  <option value="Kuala Lumpur">Kuala Lumpur</option>
                  <option value="Johor">Johor</option>
                  <option value="Pulau Pinang">Pulau Pinang</option>
                  <option value="Perak">Perak</option>
                  <option value="Kedah">Kedah</option>
                  <option value="Kelantan">Kelantan</option>
                  <option value="Melaka">Melaka</option>
                  <option value="Pahang">Pahang</option>
                  <option value="Sabah">Sabah</option>
                  <option value="Sarawak">Sarawak</option>
                  <option value="Terengganu">Terengganu</option>
                  <option value="Negeri Sembilan">Negeri Sembilan</option>
                  <option value="Perlis">Perlis</option>
                </select>
              </div>
            </div>

            <button type="submit" disabled={saving} className="w-full bg-blue-500 hover:bg-blue-600 text-white font-semibold py-3 rounded-lg disabled:opacity-50">
              {saving ? 'Menyimpan...' : 'Simpan Profil'}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}

export default function ProfilePage() {
  return (
    <Suspense fallback={<div className="min-h-screen flex items-center justify-center"><div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div></div>}>
      <ProfilePageContent />
    </Suspense>
  );
}
