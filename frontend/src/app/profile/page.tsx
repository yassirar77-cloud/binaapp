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
  const [activeTab, setActiveTab] = useState<'profile' | 'orders' | 'menu'>('profile');

  // Orders state
  const [orders, setOrders] = useState<DeliveryOrder[]>([]);
  const [loadingOrders, setLoadingOrders] = useState(false);
  const [updatingOrder, setUpdatingOrder] = useState<string | null>(null);
  const [riders, setRiders] = useState<any[]>([]);
  const [loadingRiders, setLoadingRiders] = useState(false);
  const [ridersError, setRidersError] = useState<string>('');
  const [assigningRider, setAssigningRider] = useState<string | null>(null);
  const [deliverySettings, setDeliverySettings] = useState<any | null>(null);
  const [updatingSettings, setUpdatingSettings] = useState(false);
  const [settingsError, setSettingsError] = useState<string>('');
  const [newRider, setNewRider] = useState({
    name: '',
    phone: '',
    vehicle_type: 'motorcycle',
    vehicle_plate: '',
  });
  const [creatingRider, setCreatingRider] = useState(false);

  // Menu state
  const [menuItems, setMenuItems] = useState<any[]>([]);
  const [loadingMenu, setLoadingMenu] = useState(false);
  const [editingItem, setEditingItem] = useState<any | null>(null);
  const [showAddForm, setShowAddForm] = useState(false);
  const [websiteId, setWebsiteId] = useState<string | null>(null);
  const [businessType, setBusinessType] = useState<'food' | 'clothing' | 'services' | 'general'>('food');
  
  // Business type configurations for dynamic categories
  const businessCategories = {
    food: [
      { id: 'nasi', name: '🍚 Nasi', icon: '🍚' },
      { id: 'lauk', name: '🍗 Lauk', icon: '🍗' },
      { id: 'minuman', name: '🥤 Minuman', icon: '🥤' },
    ],
    clothing: [
      { id: 'baju', name: '👗 Baju', icon: '👗' },
      { id: 'tudung', name: '🧕 Tudung', icon: '🧕' },
      { id: 'aksesori', name: '👜 Aksesori', icon: '👜' },
    ],
    services: [
      { id: 'servis', name: '🔧 Perkhidmatan', icon: '🔧' },
      { id: 'pakej', name: '📦 Pakej', icon: '📦' },
    ],
    general: [
      { id: 'produk', name: '🛍️ Produk', icon: '🛍️' },
      { id: 'lain', name: '📦 Lain-lain', icon: '📦' },
    ],
  };

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

  // Fetch user's website_id
  useEffect(() => {
    const fetchWebsiteId = async () => {
      if (!user?.id) return;
      try {
        const { data } = await supabase
          .from('websites')
          .select('id')
          .eq('user_id', user.id)
          .order('created_at', { ascending: false })
          .limit(1)
          .maybeSingle();
        if (data) {
          setWebsiteId(data.id);
        }
      } catch (error) {
        console.error('Failed to fetch website_id:', error);
      }
    };
    if (user?.id) {
      fetchWebsiteId();
    }
  }, [user?.id, supabase]);

  // Fetch orders when orders tab is active
  useEffect(() => {
    if (activeTab === 'orders' && user?.id && websiteId) {
      fetchOrders();
      fetchRiders();
      fetchDeliverySettings();
    }
  }, [activeTab, user?.id, websiteId]);

  // Fetch menu items when menu tab is active
  useEffect(() => {
    if (activeTab === 'menu' && websiteId) {
      fetchMenuItems();
    }
  }, [activeTab, websiteId]);

  const fetchOrders = async () => {
    if (!user?.id) return;
    setLoadingOrders(true);
    try {
      const { data: { session } } = await supabase.auth.getSession();
      const token = session?.access_token;
      if (!token) throw new Error('Session not found');

      const data = await apiFetch(`/v1/delivery/admin/orders`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
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
      const { data: { session } } = await supabase.auth.getSession();
      const token = session?.access_token;
      if (!token) throw new Error('Session not found');

      await apiFetch(`/v1/delivery/admin/orders/${orderId}/status`, {
        method: 'PUT',
        body: JSON.stringify({ status: newStatus }),
        headers: {
          Authorization: `Bearer ${token}`,
        },
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

  const fetchRiders = async () => {
    if (!websiteId) return;
    setLoadingRiders(true);
    setRidersError('');
    try {
      const { data: { session } } = await supabase.auth.getSession();
      const token = session?.access_token;
      if (!token) throw new Error('Session not found');

      const data = await apiFetch(`/v1/delivery/admin/websites/${websiteId}/riders`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      setRiders(data || []);
    } catch (error) {
      console.error('Failed to fetch riders:', error);
      setRidersError(
        'Tak boleh load riders. Semak backend ENV: SUPABASE_URL + SUPABASE_ANON_KEY, dan Vercel NEXT_PUBLIC_API_URL betul.'
      );
    } finally {
      setLoadingRiders(false);
    }
  };

  const fetchDeliverySettings = async () => {
    if (!websiteId) return;
    setSettingsError('');
    try {
      const { data: { session } } = await supabase.auth.getSession();
      const token = session?.access_token;
      if (!token) throw new Error('Session not found');

      const data = await apiFetch(`/v1/delivery/admin/websites/${websiteId}/settings`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      setDeliverySettings(data);
    } catch (error) {
      console.error('Failed to fetch delivery settings:', error);
      setSettingsError(
        'Tak boleh load delivery settings. Semak backend ENV: SUPABASE_URL + SUPABASE_ANON_KEY.'
      );
    }
  };

  const updateUseOwnRiders = async (value: boolean) => {
    if (!websiteId) return;
    setUpdatingSettings(true);
    try {
      const { data: { session } } = await supabase.auth.getSession();
      const token = session?.access_token;
      if (!token) throw new Error('Session not found');

      const updated = await apiFetch(`/v1/delivery/admin/websites/${websiteId}/settings`, {
        method: 'PUT',
        body: JSON.stringify({ use_own_riders: value }),
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      setDeliverySettings(updated);
      // Refresh riders/orders UI
      await fetchRiders();
      await fetchOrders();
    } catch (error) {
      console.error('Failed to update delivery settings:', error);
      alert('Gagal mengemas kini tetapan rider');
    } finally {
      setUpdatingSettings(false);
    }
  };

  const assignRiderToOrder = async (orderId: string, riderId: string | null) => {
    setAssigningRider(orderId);
    try {
      const { data: { session } } = await supabase.auth.getSession();
      const token = session?.access_token;
      if (!token) throw new Error('Session not found');

      const response = await apiFetch(`/v1/delivery/admin/orders/${orderId}/assign-rider`, {
        method: 'PUT',
        body: JSON.stringify({ rider_id: riderId }),
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      await fetchOrders();

      // Show WhatsApp notification option if rider was assigned
      if (riderId && response.whatsapp_notification) {
        const { rider_name, whatsapp_link } = response.whatsapp_notification;
        const shouldNotify = confirm(
          `✅ Rider ${rider_name} telah di-assign!\n\n` +
          `Hantar notifikasi WhatsApp kepada rider sekarang?`
        );

        if (shouldNotify) {
          // Open WhatsApp in new tab
          window.open(whatsapp_link, '_blank');
        }
      }
    } catch (error) {
      console.error('Failed to assign rider:', error);
      alert('Gagal assign rider');
    } finally {
      setAssigningRider(null);
    }
  };

  const createRider = async () => {
    if (!websiteId) return;
    if (!newRider.name.trim() || !newRider.phone.trim()) {
      alert('Sila isi nama dan telefon rider');
      return;
    }

    setCreatingRider(true);
    try {
      const { data: { session } } = await supabase.auth.getSession();
      const token = session?.access_token;
      if (!token) throw new Error('Session not found');

      await apiFetch(`/v1/delivery/admin/websites/${websiteId}/riders`, {
        method: 'POST',
        body: JSON.stringify({
          name: newRider.name,
          phone: newRider.phone,
          vehicle_type: newRider.vehicle_type,
          vehicle_plate: newRider.vehicle_plate || null,
        }),
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      setNewRider({ name: '', phone: '', vehicle_type: 'motorcycle', vehicle_plate: '' });
      await fetchRiders();
    } catch (error) {
      console.error('Failed to create rider:', error);
      alert('Gagal tambah rider');
    } finally {
      setCreatingRider(false);
    }
  };

  const fetchMenuItems = async () => {
    if (!websiteId) return;
    setLoadingMenu(true);
    try {
      const data = await apiFetch(`/v1/menu/websites/${websiteId}/menu-items`);
      setMenuItems(data);
    } catch (error) {
      console.error('Failed to fetch menu items:', error);
    } finally {
      setLoadingMenu(false);
    }
  };

  const deleteMenuItem = async (itemId: string) => {
    if (!websiteId || !confirm('Pasti nak delete item ini?')) return;
    try {
      await apiFetch(`/v1/menu/websites/${websiteId}/menu-items/${itemId}`, {
        method: 'DELETE',
      });
      await fetchMenuItems();
    } catch (error) {
      console.error('Failed to delete menu item:', error);
      alert('Gagal delete item');
    }
  };

  const toggleAvailability = async (itemId: string, isAvailable: boolean) => {
    if (!websiteId) return;
    try {
      await apiFetch(`/v1/menu/websites/${websiteId}/menu-items/${itemId}/availability?is_available=${!isAvailable}`, {
        method: 'PATCH',
      });
      await fetchMenuItems();
    } catch (error) {
      console.error('Failed to toggle availability:', error);
      alert('Gagal toggle availability');
    }
  };

  const saveMenuItem = async (itemData: any) => {
    if (!websiteId) return;
    try {
      if (itemData.id) {
        // Update existing
        await apiFetch(`/v1/menu/websites/${websiteId}/menu-items/${itemData.id}`, {
          method: 'PUT',
          body: JSON.stringify(itemData),
        });
      } else {
        // Create new
        await apiFetch(`/v1/menu/websites/${websiteId}/menu-items`, {
          method: 'POST',
          body: JSON.stringify(itemData),
        });
      }
      await fetchMenuItems();
      setEditingItem(null);
      setShowAddForm(false);
    } catch (error) {
      console.error('Failed to save menu item:', error);
      alert('Gagal save item');
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
          <button
            onClick={() => setActiveTab('menu')}
            className={`flex-1 py-4 px-6 font-medium transition-colors ${
              activeTab === 'menu'
                ? 'bg-blue-500 text-white'
                : 'text-gray-600 hover:bg-gray-50'
            }`}
          >
            🍽️ Menu
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

            {/* Rider System Settings (Phase 1) */}
            {!websiteId ? (
              <div className="bg-white rounded-xl shadow p-4">
                <p className="text-gray-700">Anda perlu ada website untuk aktifkan sistem rider.</p>
              </div>
            ) : (
              <div className="bg-white rounded-xl shadow p-4">
                {settingsError && (
                  <div className="mb-3 p-3 bg-red-50 border border-red-200 rounded text-red-700 text-sm">
                    {settingsError}
                  </div>
                )}
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <h2 className="font-bold text-lg">🛵 Own Riders</h2>
                    <p className="text-sm text-gray-600">
                      Aktifkan untuk guna rider sendiri dan assign rider pada pesanan.
                    </p>
                  </div>
                  <label className="flex items-center gap-2 text-sm font-medium">
                    <input
                      type="checkbox"
                      checked={(deliverySettings?.use_own_riders ?? true) === true}
                      onChange={(e) => updateUseOwnRiders(e.target.checked)}
                      disabled={updatingSettings}
                      className="w-4 h-4"
                    />
                    {updatingSettings ? '...' : 'Enable'}
                  </label>
                </div>

                {(deliverySettings?.use_own_riders ?? true) && (
                  <div className="mt-4 border-t pt-4">
                    <h3 className="font-semibold mb-2">Riders</h3>

                    {ridersError && (
                      <div className="mb-3 p-3 bg-red-50 border border-red-200 rounded text-red-700 text-sm">
                        {ridersError}
                      </div>
                    )}

                    {/* Add Rider */}
                    <div className="grid grid-cols-1 sm:grid-cols-4 gap-2">
                      <input
                        value={newRider.name}
                        onChange={(e) => setNewRider({ ...newRider, name: e.target.value })}
                        placeholder="Nama rider"
                        className="p-2 border rounded-lg"
                      />
                      <input
                        value={newRider.phone}
                        onChange={(e) => setNewRider({ ...newRider, phone: e.target.value })}
                        placeholder="Telefon"
                        className="p-2 border rounded-lg"
                      />
                      <input
                        value={newRider.vehicle_plate}
                        onChange={(e) => setNewRider({ ...newRider, vehicle_plate: e.target.value })}
                        placeholder="Plate (optional)"
                        className="p-2 border rounded-lg"
                      />
                      <button
                        onClick={createRider}
                        disabled={creatingRider}
                        className="py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50"
                      >
                        {creatingRider ? '...' : '+ Tambah'}
                      </button>
                    </div>

                    {/* Riders List */}
                    <div className="mt-3 text-sm text-gray-700">
                      {loadingRiders ? (
                        <p>Memuat riders...</p>
                      ) : riders.length === 0 ? (
                        <p className="text-gray-500">Belum ada rider. Tambah rider untuk mula assign.</p>
                      ) : (
                        <ul className="space-y-1">
                          {riders.map((r) => (
                            <li key={r.id} className="flex items-center justify-between">
                              <span className="font-medium">{r.name}</span>
                              <span className="text-gray-500">{r.phone}</span>
                            </li>
                          ))}
                        </ul>
                      )}
                    </div>
                  </div>
                )}
              </div>
            )}

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

                    {/* Rider Assignment (Phase 1) */}
                    {(deliverySettings?.use_own_riders ?? true) && (
                      <div className="border-t pt-4 mb-4">
                        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
                          <div className="text-sm">
                            <span className="text-gray-500">Rider:</span>{' '}
                            <span className="font-medium">
                              {order.rider_id
                                ? (riders.find((r) => r.id === order.rider_id)?.name || '—')
                                : 'Belum assign'}
                            </span>
                          </div>
                          <select
                            value={order.rider_id || ''}
                            onChange={(e) => assignRiderToOrder(order.id, e.target.value ? e.target.value : null)}
                            disabled={assigningRider === order.id || loadingRiders}
                            className="p-2 border rounded-lg text-sm"
                          >
                            <option value="">-- Pilih rider --</option>
                            {riders.map((r) => (
                              <option key={r.id} value={r.id}>
                                {r.name} ({r.phone})
                              </option>
                            ))}
                          </select>
                        </div>
                        {assigningRider === order.id && (
                          <p className="text-xs text-gray-500 mt-2">Mengemas kini rider...</p>
                        )}

                        {/* Quick Action Buttons (Phase 2+) */}
                        {order.rider_id && riders.find((r) => r.id === order.rider_id) && (
                          <div className="mt-3 grid grid-cols-3 gap-2">
                            <a
                              href={`https://wa.me/${(riders.find((r) => r.id === order.rider_id)?.phone || '').replace(/[^0-9]/g, '')}?text=${encodeURIComponent(`Hi ${riders.find((r) => r.id === order.rider_id)?.name}, ada pesanan untuk anda!\n\nOrder: ${order.order_number}\nPelanggan: ${order.customer_name}\nAlamat: ${order.delivery_address}`)}`}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="flex items-center justify-center gap-1 px-3 py-2 bg-green-500 text-white rounded-lg text-xs font-medium hover:bg-green-600 transition-colors"
                            >
                              💬 WhatsApp
                            </a>
                            <a
                              href={`tel:${riders.find((r) => r.id === order.rider_id)?.phone || ''}`}
                              className="flex items-center justify-center gap-1 px-3 py-2 bg-blue-500 text-white rounded-lg text-xs font-medium hover:bg-blue-600 transition-colors"
                            >
                              📞 Call
                            </a>
                            <a
                              href={`/track?order=${order.order_number}`}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="flex items-center justify-center gap-1 px-3 py-2 bg-purple-500 text-white rounded-lg text-xs font-medium hover:bg-purple-600 transition-colors"
                            >
                              🗺️ Track
                            </a>
                          </div>
                        )}
                      </div>
                    )}

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

        {/* Menu Tab */}
        {activeTab === 'menu' && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h1 className="text-2xl font-bold">🛒 Menu / Produk</h1>
              <button
                onClick={() => setShowAddForm(true)}
                className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors"
              >
                + Tambah Item
              </button>
            </div>
            
            {/* Business Type Selector */}
            <div className="bg-white rounded-xl shadow p-4">
              <label className="block text-sm font-medium mb-2">Jenis Perniagaan:</label>
              <div className="flex flex-wrap gap-2">
                <button
                  onClick={() => setBusinessType('food')}
                  className={`px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                    businessType === 'food' 
                      ? 'bg-orange-500 text-white' 
                      : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }`}
                >
                  🍛 Makanan
                </button>
                <button
                  onClick={() => setBusinessType('clothing')}
                  className={`px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                    businessType === 'clothing' 
                      ? 'bg-pink-500 text-white' 
                      : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }`}
                >
                  👗 Pakaian
                </button>
                <button
                  onClick={() => setBusinessType('services')}
                  className={`px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                    businessType === 'services' 
                      ? 'bg-blue-500 text-white' 
                      : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }`}
                >
                  🔧 Servis
                </button>
                <button
                  onClick={() => setBusinessType('general')}
                  className={`px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                    businessType === 'general' 
                      ? 'bg-green-500 text-white' 
                      : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }`}
                >
                  🛒 Lain-lain
                </button>
              </div>
              <p className="text-xs text-gray-500 mt-2">
                Kategori tersedia: {businessCategories[businessType].map(c => c.name).join(', ')}
              </p>
            </div>

            {!websiteId ? (
              <div className="bg-white rounded-xl shadow p-8 text-center">
                <div className="text-5xl mb-4">📝</div>
                <h2 className="text-lg font-semibold mb-2">Tiada Website</h2>
                <p className="text-gray-600">Anda perlu create website dulu untuk manage menu.</p>
              </div>
            ) : loadingMenu && menuItems.length === 0 ? (
              <div className="bg-white rounded-xl shadow p-8 text-center">
                <div className="animate-spin h-8 w-8 border-4 border-blue-500 border-t-transparent rounded-full mx-auto" />
                <p className="mt-4 text-gray-600">Memuat menu...</p>
              </div>
            ) : showAddForm || editingItem ? (
              <MenuItemForm
                item={editingItem}
                onSave={saveMenuItem}
                onCancel={() => {
                  setEditingItem(null);
                  setShowAddForm(false);
                }}
                categories={businessCategories[businessType]}
              />
            ) : menuItems.length === 0 ? (
              <div className="bg-white rounded-xl shadow p-8 text-center">
                <div className="text-5xl mb-4">🍽️</div>
                <h2 className="text-lg font-semibold mb-2">Menu Kosong</h2>
                <p className="text-gray-600 mb-4">Belum ada item dalam menu. Klik &quot;Tambah Item&quot; untuk mulakan!</p>
              </div>
            ) : (
              <div className="space-y-3">
                {menuItems.map((item) => (
                  <div key={item.id} className="bg-white rounded-xl shadow p-4 flex items-center gap-4">
                    {/* Image */}
                    <div className="w-20 h-20 bg-gray-200 rounded-lg overflow-hidden flex-shrink-0">
                      {item.image_url ? (
                        <img src={item.image_url} alt={item.name} className="w-full h-full object-cover" />
                      ) : (
                        <div className="w-full h-full flex items-center justify-center text-3xl">
                          🍽️
                        </div>
                      )}
                    </div>

                    {/* Info */}
                    <div className="flex-1 min-w-0">
                      <h3 className="font-bold text-lg">{item.name}</h3>
                      <p className="text-sm text-gray-600 truncate">{item.description || 'Tiada description'}</p>
                      <div className="flex items-center gap-3 mt-1">
                        <span className="font-bold text-blue-600">RM {item.price?.toFixed(2) || '0.00'}</span>
                        <span className="text-xs px-2 py-1 bg-gray-100 rounded">
                          {item.category_id || 'Tiada kategori'}
                        </span>
                        <button
                          onClick={() => toggleAvailability(item.id, item.is_available)}
                          className={`text-xs px-2 py-1 rounded ${
                            item.is_available
                              ? 'bg-green-100 text-green-700'
                              : 'bg-red-100 text-red-700'
                          }`}
                        >
                          {item.is_available ? '✓ Available' : '✗ Unavailable'}
                        </button>
                      </div>
                    </div>

                    {/* Actions */}
                    <div className="flex gap-2">
                      <button
                        onClick={() => setEditingItem(item)}
                        className="p-2 text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                        title="Edit"
                      >
                        ✏️
                      </button>
                      <button
                        onClick={() => deleteMenuItem(item.id)}
                        className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                        title="Delete"
                      >
                        🗑️
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

// Menu Item Form Component - Now with dynamic categories
function MenuItemForm({ 
  item, 
  onSave, 
  onCancel, 
  categories 
}: { 
  item: any, 
  onSave: (data: any) => void, 
  onCancel: () => void,
  categories: { id: string, name: string, icon: string }[]
}) {
  // Get default category from the first category in the list
  const defaultCategory = categories.length > 0 ? categories[0].id : 'produk';
  
  const [formData, setFormData] = useState({
    id: item?.id || null,
    name: item?.name || '',
    price: item?.price || 0,
    description: item?.description || '',
    category_id: item?.category_id || defaultCategory,
    image_url: item?.image_url || '',
    is_available: item?.is_available ?? true,
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSave(formData);
  };

  return (
    <div className="bg-white rounded-xl shadow p-6">
      <h2 className="text-xl font-bold mb-4">{item ? 'Edit Item' : 'Tambah Item Baru'}</h2>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium mb-1">Nama Item</label>
          <input
            type="text"
            value={formData.name}
            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
            className="w-full p-3 border rounded-lg"
            placeholder="Nama produk anda"
            required
          />
        </div>

        <div>
          <label className="block text-sm font-medium mb-1">Harga (RM)</label>
          <input
            type="number"
            step="0.01"
            value={formData.price}
            onChange={(e) => setFormData({ ...formData, price: parseFloat(e.target.value) })}
            className="w-full p-3 border rounded-lg"
            placeholder="8.00"
            required
          />
        </div>

        <div>
          <label className="block text-sm font-medium mb-1">Kategori</label>
          <select
            value={formData.category_id}
            onChange={(e) => setFormData({ ...formData, category_id: e.target.value })}
            className="w-full p-3 border rounded-lg"
          >
            {categories.map((cat) => (
              <option key={cat.id} value={cat.id}>{cat.name}</option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium mb-1">Description</label>
          <textarea
            value={formData.description}
            onChange={(e) => setFormData({ ...formData, description: e.target.value })}
            className="w-full p-3 border rounded-lg"
            placeholder="Hidangan istimewa dari dapur kami"
            rows={3}
          />
        </div>

        <div>
          <label className="block text-sm font-medium mb-1">URL Gambar</label>
          <input
            type="url"
            value={formData.image_url}
            onChange={(e) => setFormData({ ...formData, image_url: e.target.value })}
            className="w-full p-3 border rounded-lg"
            placeholder="https://example.com/image.jpg"
          />
          <p className="text-xs text-gray-500 mt-1">Kosongkan untuk auto-generate gambar AI</p>
        </div>

        <div className="flex items-center gap-2">
          <input
            type="checkbox"
            id="is_available"
            checked={formData.is_available}
            onChange={(e) => setFormData({ ...formData, is_available: e.target.checked })}
            className="w-4 h-4"
          />
          <label htmlFor="is_available" className="text-sm font-medium">Available untuk order</label>
        </div>

        <div className="flex gap-3 pt-4">
          <button
            type="submit"
            className="flex-1 py-3 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors"
          >
            Simpan
          </button>
          <button
            type="button"
            onClick={onCancel}
            className="flex-1 py-3 border rounded-lg hover:bg-gray-50 transition-colors"
          >
            Batal
          </button>
        </div>
      </form>
    </div>
  );
}
