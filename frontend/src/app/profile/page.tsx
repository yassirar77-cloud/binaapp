'use client';

import { useState, useEffect } from 'react';
import { createClientComponentClient } from '@supabase/auth-helpers-nextjs';
import { useRouter } from 'next/navigation';

export default function ProfilePage() {
  const supabase = createClientComponentClient();
  const router = useRouter();
  const [state, setState] = useState<'loading'|'auth'|'noauth'>('loading');
  const [user, setUser] = useState<any>(null);
  const [profile, setProfile] = useState({ full_name: '', business_name: '', phone: '' });
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState('');

  useEffect(() => {
    const check = async () => {
      await new Promise(r => setTimeout(r, 100));
      const { data: { session } } = await supabase.auth.getSession();
      if (session?.user) {
        setUser(session.user);
        setState('auth');
        const { data } = await supabase.from('profiles').select('*').eq('id', session.user.id).maybeSingle();
        if (data) setProfile({ full_name: data.full_name || '', business_name: data.business_name || '', phone: data.phone || '' });
      } else {
        setState('noauth');
      }
    };
    check();
  }, [supabase]);

  const save = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    await supabase.from('profiles').upsert({ id: user.id, email: user.email, ...profile, updated_at: new Date().toISOString() });
    setSaving(false);
    setMsg('✅ Saved!');
    setTimeout(() => setMsg(''), 3000);
  };

  if (state === 'loading') return <div className="min-h-screen flex items-center justify-center"><div className="animate-spin h-10 w-10 border-4 border-blue-500 border-t-transparent rounded-full"/></div>;

  if (state === 'noauth') return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
      <div className="bg-white p-8 rounded-xl shadow text-center max-w-md w-full">
        <div className="text-5xl mb-4">🔐</div>
        <h1 className="text-xl font-bold mb-2">Sila Log Masuk</h1>
        <p className="text-gray-600 mb-6">Anda perlu log masuk untuk melihat profil</p>
        <button onClick={() => router.push('/login')} className="w-full py-3 bg-blue-500 text-white rounded-lg">Log Masuk</button>
      </div>
    </div>
  );

  return (
    <div className="min-h-screen bg-gray-50 py-8 px-4">
      <div className="max-w-md mx-auto bg-white rounded-xl shadow p-6">
        <h1 className="text-2xl font-bold mb-6">👤 Profil Saya</h1>
        {msg && <div className="p-3 bg-green-100 text-green-700 rounded mb-4">{msg}</div>}
        <form onSubmit={save} className="space-y-4">
          <input type="email" value={user?.email||''} disabled className="w-full p-3 bg-gray-100 rounded-lg"/>
          <input type="text" value={profile.full_name} onChange={e=>setProfile({...profile,full_name:e.target.value})} placeholder="Nama" className="w-full p-3 border rounded-lg"/>
          <input type="text" value={profile.business_name} onChange={e=>setProfile({...profile,business_name:e.target.value})} placeholder="Perniagaan" className="w-full p-3 border rounded-lg"/>
          <input type="tel" value={profile.phone} onChange={e=>setProfile({...profile,phone:e.target.value})} placeholder="Telefon" className="w-full p-3 border rounded-lg"/>
          <button type="submit" disabled={saving} className="w-full py-3 bg-blue-500 text-white rounded-lg">{saving?'...':'💾 Simpan'}</button>
        </form>
        <button onClick={()=>router.push('/my-projects')} className="w-full mt-4 py-3 border rounded-lg">← Kembali</button>
        <button onClick={async()=>{await supabase.auth.signOut();router.push('/login');}} className="w-full mt-2 py-3 text-red-500">🚪 Log Keluar</button>
      </div>
    </div>
  );
}
