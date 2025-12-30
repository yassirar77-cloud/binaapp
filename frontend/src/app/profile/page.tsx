'use client';

import { useState, useEffect } from 'react';
import { createClientComponentClient } from '@supabase/auth-helpers-nextjs';
import { useRouter } from 'next/navigation';
import { apiFetch } from '@/lib/api';
import { DeliveryOrder, OrderStatus } from '@/types';

// Status badge colors and labels
const statusConfig: Record<OrderStatus, { bg: string; text: string; label: string }> = {
  pending: { bg: 'bg-yellow-100', text: 'text-yellow-800', label: 'Menunggu' },
  confirmed: { bg: 'bg-blue-100', text: 'text-blue-800', label: 'Disahkan' },
  preparing: { bg: 'bg-purple-100', text: 'text-purple-800', label: 'Sedang Disediakan' },
  ready: { bg: 'bg-green-100', text: 'text-green-800', label: 'Sedia' },
  picked_up: { bg: 'bg-indigo-100', text: 'text-indigo-800', label: 'Diambil' },
  delivering: { bg: 'bg-cyan-100', text: 'text-cyan-800', label: 'Dalam Penghantaran' },
  delivered: { bg: 'bg-emerald-100', text: 'text-emerald-800', label: 'Dihantar' },
  completed: { bg: 'bg-gray-100', text: 'text-gray-800', label: 'Selesai' },
  cancelled: { bg: 'bg-red-100', text: 'text-red-800', label: 'Dibatalkan' },
  rejected: { bg: 'bg-red-100', text: 'text-red-800', label: 'Ditolak' },
};

// Get next status in workflow
function getNextStatus(current: OrderStatus): OrderStatus | null {
  const workflow: Record<string, OrderStatus> = {
    pending: 'confirmed',
    confirmed: 'preparing',
    preparing: 'ready',
    ready: 'delivered',
  };
  return workflow[current] || null;
}

// Get button label for next action
function getActionLabel(current: OrderStatus): string {
  const labels: Record<string, string> = {
    pending: 'Sahkan',
    confirmed: 'Mula Sediakan',
    preparing: 'Sedia Diambil',
    ready: 'Telah Dihantar',
  };
  return labels[current] || '';
}

export default function ProfilePage() {
  const supabase = createClientComponentClient();
  const router = useRouter();
  const [state, setState] = useState<'loading' | 'auth' | 'noauth'>('loading');
  const [user, setUser] = useState<any>(null);
  const [profile, setProfile] = useState({ full_name: '', business_name: '', phone: '' });
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState('');

  // Tab state
  const [activeTab, setActiveTab] = useState<'profile' | 'orders'>('profile');

  // Orders state
  const [orders, setOrders] = useState<DeliveryOrder[]>([]);
  const [loadingOrders, setLoadingOrders] = useState(false);
  const [updatingOrder, setUpdatingOrder] = useState<string | null>(null);

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

  // Fetch orders when orders tab is active
  useEffect(() => {
    if (activeTab === 'orders' && user?.id) {
      fetchOrders();
    }
  }, [activeTab, user?.id]);

  const fetchOrders = async () => {
    if (!user?.id) return;
    setLoadingOrders(true);
    try {
      const data = await apiFetch(`/v1/delivery/orders/business/${user.id}`);
      setOrders(data);
    } catch (error) {
      console.error('Failed to fetch orders:', error);
    } finally {
      setLoadingOrders(false);
    }
  };

  const updateOrderStatus = async (orderId: string, newStatus: OrderStatus) => {
    setUpdatingOrder(orderId);
    try {
      await apiFetch(`/v1/delivery/orders/${orderId}/status`, {
        method: 'PUT',
        body: JSON.stringify({ status: newStatus }),
      });
      // Refresh orders
      await fetchOrders();
    } catch (error) {
      console.error('Failed to update order status:', error);
      alert('Gagal mengemas kini status pesanan');
    } finally {
      setUpdatingOrder(null);
    }
  };

  const save = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    await supabase.from('profiles').upsert({ id: user.id, email: user.email, ...profile, updated_at: new Date().toISOString() });
    setSaving(false);
    setMsg('Disimpan!');
    setTimeout(() => setMsg(''), 3000);
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleString('ms-MY', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const formatCurrency = (amount: number) => {
    return `RM ${amount.toFixed(2)}`;
  };

  if (state === 'loading') return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="animate-spin h-10 w-10 border-4 border-blue-500 border-t-transparent rounded-full" />
    </div>
  );

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
      <div className="max-w-2xl mx-auto">
        {/* Tabs */}
        <div className="flex mb-6 bg-white rounded-xl shadow overflow-hidden">
          <button
            onClick={() => setActiveTab('profile')}
            className={`flex-1 py-4 px-6 font-medium transition-colors ${
              activeTab === 'profile'
                ? 'bg-blue-500 text-white'
                : 'text-gray-600 hover:bg-gray-50'
            }`}
          >
            Profil
          </button>
          <button
            onClick={() => setActiveTab('orders')}
            className={`flex-1 py-4 px-6 font-medium transition-colors ${
              activeTab === 'orders'
                ? 'bg-blue-500 text-white'
                : 'text-gray-600 hover:bg-gray-50'
            }`}
          >
            Pesanan
          </button>
        </div>

        {/* Profile Tab */}
        {activeTab === 'profile' && (
          <div className="bg-white rounded-xl shadow p-6">
            <h1 className="text-2xl font-bold mb-6">Profil Saya</h1>
            {msg && <div className="p-3 bg-green-100 text-green-700 rounded mb-4">{msg}</div>}
            <form onSubmit={save} className="space-y-4">
              <input type="email" value={user?.email || ''} disabled className="w-full p-3 bg-gray-100 rounded-lg" />
              <input type="text" value={profile.full_name} onChange={e => setProfile({ ...profile, full_name: e.target.value })} placeholder="Nama" className="w-full p-3 border rounded-lg" />
              <input type="text" value={profile.business_name} onChange={e => setProfile({ ...profile, business_name: e.target.value })} placeholder="Perniagaan" className="w-full p-3 border rounded-lg" />
              <input type="tel" value={profile.phone} onChange={e => setProfile({ ...profile, phone: e.target.value })} placeholder="Telefon" className="w-full p-3 border rounded-lg" />
              <button type="submit" disabled={saving} className="w-full py-3 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors">
                {saving ? '...' : 'Simpan'}
              </button>
            </form>
            <button onClick={() => router.push('/my-projects')} className="w-full mt-4 py-3 border rounded-lg hover:bg-gray-50 transition-colors">
              Kembali
            </button>
            <button onClick={async () => { await supabase.auth.signOut(); router.push('/login'); }} className="w-full mt-2 py-3 text-red-500 hover:bg-red-50 rounded-lg transition-colors">
              Log Keluar
            </button>
          </div>
        )}

        {/* Orders Tab */}
        {activeTab === 'orders' && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h1 className="text-2xl font-bold">Pesanan Saya</h1>
              <button
                onClick={fetchOrders}
                disabled={loadingOrders}
                className="px-4 py-2 text-sm bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors"
              >
                {loadingOrders ? '...' : 'Muat Semula'}
              </button>
            </div>

            {loadingOrders && orders.length === 0 ? (
              <div className="bg-white rounded-xl shadow p-8 text-center">
                <div className="animate-spin h-8 w-8 border-4 border-blue-500 border-t-transparent rounded-full mx-auto" />
                <p className="mt-4 text-gray-600">Memuat pesanan...</p>
              </div>
            ) : orders.length === 0 ? (
              <div className="bg-white rounded-xl shadow p-8 text-center">
                <div className="text-5xl mb-4">📦</div>
                <h2 className="text-lg font-semibold mb-2">Tiada Pesanan</h2>
                <p className="text-gray-600">Anda belum mempunyai sebarang pesanan delivery.</p>
              </div>
            ) : (
              orders.map((order) => {
                const status = statusConfig[order.status] || statusConfig.pending;
                const nextStatus = getNextStatus(order.status);
                const actionLabel = getActionLabel(order.status);
                const isUpdating = updatingOrder === order.id;

                return (
                  <div key={order.id} className="bg-white rounded-xl shadow p-5">
                    {/* Order Header */}
                    <div className="flex items-start justify-between mb-4">
                      <div>
                        <div className="flex items-center gap-2 mb-1">
                          <span className="font-bold text-lg">{order.order_number}</span>
                          <span className={`px-2 py-1 text-xs font-medium rounded-full ${status.bg} ${status.text}`}>
                            {status.label}
                          </span>
                        </div>
                        <p className="text-sm text-gray-500">{formatDate(order.created_at)}</p>
                      </div>
                      <div className="text-right">
                        <p className="font-bold text-lg text-blue-600">{formatCurrency(order.total_amount)}</p>
                        <p className="text-xs text-gray-500">
                          {order.payment_method === 'cod' ? 'Tunai' : order.payment_method === 'ewallet' ? 'E-Wallet' : 'Online'}
                        </p>
                      </div>
                    </div>

                    {/* Customer Info */}
                    <div className="border-t pt-4 mb-4">
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm">
                        <div>
                          <span className="text-gray-500">Pelanggan:</span>
                          <p className="font-medium">{order.customer_name}</p>
                        </div>
                        <div>
                          <span className="text-gray-500">Telefon:</span>
                          <p className="font-medium">{order.customer_phone}</p>
                        </div>
                        <div className="sm:col-span-2">
                          <span className="text-gray-500">Alamat:</span>
                          <p className="font-medium">{order.delivery_address}</p>
                        </div>
                      </div>
                    </div>

                    {/* Action Buttons */}
                    {nextStatus && (
                      <div className="flex gap-2 pt-3 border-t">
                        <button
                          onClick={() => updateOrderStatus(order.id, nextStatus)}
                          disabled={isUpdating}
                          className="flex-1 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors disabled:opacity-50"
                        >
                          {isUpdating ? '...' : actionLabel}
                        </button>
                        {order.status === 'pending' && (
                          <button
                            onClick={() => updateOrderStatus(order.id, 'cancelled')}
                            disabled={isUpdating}
                            className="px-4 py-2 border border-red-300 text-red-600 rounded-lg hover:bg-red-50 transition-colors disabled:opacity-50"
                          >
                            Batal
                          </button>
                        )}
                      </div>
                    )}
                  </div>
                );
              })
            )}
          </div>
        )}
      </div>
    </div>
  );
}
