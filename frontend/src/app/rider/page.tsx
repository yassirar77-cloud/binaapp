'use client';

import { useState, useEffect, useRef } from 'react';
import { apiFetch } from '@/lib/api';

interface RiderOrder {
  id: string;
  order_number: string;
  customer_name: string;
  customer_phone: string;
  delivery_address: string;
  delivery_latitude: number | null;
  delivery_longitude: number | null;
  total_amount: number;
  status: string;
  created_at: string;
}

interface Rider {
  id: string;
  name: string;
  phone: string;
  vehicle_type: string;
  vehicle_plate: string;
}

export default function RiderApp() {
  // Authentication
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [phone, setPhone] = useState('');
  const [password, setPassword] = useState('');
  const [rider, setRider] = useState<Rider | null>(null);
  const [loginError, setLoginError] = useState('');

  // GPS Tracking
  const [gpsActive, setGpsActive] = useState(false);
  const [currentLocation, setCurrentLocation] = useState<{ lat: number; lng: number } | null>(null);
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);
  const watchIdRef = useRef<number | null>(null);
  const lastGpsSentRef = useRef<number>(0); // Throttle GPS updates to every 15 seconds

  // Orders
  const [orders, setOrders] = useState<RiderOrder[]>([]);
  const [activeOrder, setActiveOrder] = useState<RiderOrder | null>(null);
  const [loadingOrders, setLoadingOrders] = useState(false);

  // Status updates
  const [updatingStatus, setUpdatingStatus] = useState(false);

  // Check for saved rider credentials on mount
  useEffect(() => {
    const savedRider = localStorage.getItem('rider_data');
    if (savedRider) {
      try {
        const riderData = JSON.parse(savedRider);
        setRider(riderData);
        setIsLoggedIn(true);
      } catch (error) {
        console.error('Failed to parse saved rider data:', error);
        localStorage.removeItem('rider_data');
      }
    }
  }, []);

  // Start GPS tracking when logged in
  useEffect(() => {
    if (isLoggedIn && rider) {
      startGPSTracking();
    }
    return () => {
      stopGPSTracking();
    };
  }, [isLoggedIn, rider]);

  // Fetch orders periodically
  useEffect(() => {
    if (isLoggedIn && rider) {
      fetchOrders();
      const interval = setInterval(fetchOrders, 30000); // Every 30 seconds
      return () => clearInterval(interval);
    }
  }, [isLoggedIn, rider]);

  // Handle login
  const handleLogin = async () => {
    if (!phone.trim() || !password.trim()) {
      setLoginError('Sila masukkan nombor telefon dan kata laluan');
      return;
    }

    try {
      const response = await apiFetch('/v1/delivery/riders/login', {
        method: 'POST',
        body: JSON.stringify({
          phone: phone,
          password: password
        })
      });

      if (response.success && response.rider) {
        setRider(response.rider);
        setIsLoggedIn(true);
        localStorage.setItem('rider_data', JSON.stringify(response.rider));
        setLoginError('');
        console.log('✅ Login successful:', response.rider.name);
      }
    } catch (error: any) {
      console.error('Login error:', error);
      setLoginError(error.message || 'Nombor telefon atau kata laluan salah');
    }
  };

  // Handle logout
  const handleLogout = () => {
    stopGPSTracking();
    setIsLoggedIn(false);
    setRider(null);
    setPhone('');
    setPassword('');
    setOrders([]);
    setActiveOrder(null);
    localStorage.removeItem('rider_data');
  };

  // Start GPS tracking
  const startGPSTracking = () => {
    if (!navigator.geolocation) {
      alert('GPS tidak disokong oleh pelayar anda');
      return;
    }

    // Request permission and start watching position
    const options = {
      enableHighAccuracy: true,
      timeout: 10000,
      maximumAge: 5000 // Allow cached position up to 5 seconds old
    };

    watchIdRef.current = navigator.geolocation.watchPosition(
      (position) => {
        const { latitude, longitude } = position.coords;
        setCurrentLocation({ lat: latitude, lng: longitude });
        setGpsActive(true);

        // Throttle GPS updates to every 15 seconds to prevent API overload
        const now = Date.now();
        if (now - lastGpsSentRef.current >= 15000) {
          sendLocationToAPI(latitude, longitude);
          lastGpsSentRef.current = now;
        }
      },
      (error) => {
        console.error('GPS error:', error);
        setGpsActive(false);

        if (error.code === error.PERMISSION_DENIED) {
          alert('Sila benarkan akses GPS untuk menggunakan app ini');
        }
      },
      options
    );

    // Send initial GPS immediately
    navigator.geolocation.getCurrentPosition(
      (position) => {
        const { latitude, longitude } = position.coords;
        setCurrentLocation({ lat: latitude, lng: longitude });
        setGpsActive(true);
        sendLocationToAPI(latitude, longitude);
        lastGpsSentRef.current = Date.now();
        console.log('✅ Initial GPS sent');
      },
      (error) => {
        console.error('Initial GPS error:', error);
      },
      { enableHighAccuracy: true, timeout: 10000 }
    );

    console.log('✅ GPS tracking started');
  };

  // Stop GPS tracking
  const stopGPSTracking = () => {
    if (watchIdRef.current !== null) {
      navigator.geolocation.clearWatch(watchIdRef.current);
      watchIdRef.current = null;
      setGpsActive(false);
      console.log('🛑 GPS tracking stopped');
    }
  };

  // Send location to API
  const sendLocationToAPI = async (lat: number, lng: number) => {
    if (!rider) return;

    try {
      await apiFetch(`/v1/delivery/riders/${rider.id}/location`, {
        method: 'PUT',
        body: JSON.stringify({
          latitude: lat,
          longitude: lng
        })
      });

      setLastUpdate(new Date());
      console.log(`📍 GPS sent: ${lat.toFixed(6)}, ${lng.toFixed(6)}`);
    } catch (error) {
      console.error('Failed to send GPS:', error);
    }
  };

  // Fetch rider's assigned orders
  const fetchOrders = async () => {
    if (!rider) return;

    setLoadingOrders(true);
    try {
      // Get orders assigned to this rider
      const response = await apiFetch(`/v1/delivery/riders/${rider.id}/orders`);

      const fetchedOrders: RiderOrder[] = response.orders || [];
      setOrders(fetchedOrders);

      // Set active order (first ready/picked_up/delivering order)
      const active = fetchedOrders.find(o =>
        ['ready', 'picked_up', 'delivering'].includes(o.status)
      );
      setActiveOrder(active || null);

      console.log(`📦 Fetched ${fetchedOrders.length} orders`);
    } catch (error) {
      console.error('Failed to fetch orders:', error);
      setOrders([]);
      setActiveOrder(null);
    } finally {
      setLoadingOrders(false);
    }
  };

  // Update order status
  const updateOrderStatus = async (orderId: string, newStatus: string) => {
    if (!rider) return;

    setUpdatingStatus(true);
    try {
      await apiFetch(`/v1/delivery/riders/${rider.id}/orders/${orderId}/status`, {
        method: 'PUT',
        body: JSON.stringify({
          status: newStatus,
          notes: `Updated by rider ${rider.name}`
        })
      });

      // Refresh orders
      await fetchOrders();

      alert('✅ Status dikemas kini!');
    } catch (error) {
      console.error('Failed to update status:', error);
      alert('❌ Gagal mengemas kini status');
    } finally {
      setUpdatingStatus(false);
    }
  };

  // Status flow
  const getNextStatus = (currentStatus: string): string | null => {
    const flow: Record<string, string> = {
      'ready': 'picked_up',
      'picked_up': 'delivering',
      'delivering': 'delivered'
    };
    return flow[currentStatus] || null;
  };

  const getStatusLabel = (status: string): string => {
    const labels: Record<string, string> = {
      'ready': 'Siap Diambil',
      'picked_up': 'Diambil',
      'delivering': 'Dalam Penghantaran',
      'delivered': 'Dihantar',
      'completed': 'Selesai'
    };
    return labels[status] || status;
  };

  const getStatusColor = (status: string): string => {
    const colors: Record<string, string> = {
      'ready': 'bg-green-100 text-green-800',
      'picked_up': 'bg-purple-100 text-purple-800',
      'delivering': 'bg-blue-100 text-blue-800',
      'delivered': 'bg-emerald-100 text-emerald-800',
      'completed': 'bg-gray-100 text-gray-800'
    };
    return colors[status] || 'bg-gray-100 text-gray-800';
  };

  // Install PWA prompt
  useEffect(() => {
    let deferredPrompt: any;

    const handleBeforeInstallPrompt = (e: Event) => {
      e.preventDefault();
      deferredPrompt = e;

      // Show install button (optional)
      console.log('PWA install prompt available');
    };

    window.addEventListener('beforeinstallprompt', handleBeforeInstallPrompt);

    return () => {
      window.removeEventListener('beforeinstallprompt', handleBeforeInstallPrompt);
    };
  }, []);

  // Render Login Screen
  if (!isLoggedIn) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-green-400 to-green-600 flex items-center justify-center px-4">
        <div className="bg-white rounded-3xl shadow-2xl p-8 w-full max-w-md">
          <div className="text-center mb-8">
            <div className="text-6xl mb-4">🛵</div>
            <h1 className="text-3xl font-bold text-gray-800 mb-2">BinaApp Rider</h1>
            <p className="text-gray-600">Sistem Penghantaran Real-Time</p>
          </div>

          <form onSubmit={(e) => { e.preventDefault(); handleLogin(); }} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Nombor Telefon
              </label>
              <input
                type="tel"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                placeholder="Contoh: 0123456789"
                className="w-full p-4 border-2 border-gray-300 rounded-xl focus:border-green-500 focus:outline-none text-lg"
                autoFocus
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Kata Laluan
              </label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Masukkan kata laluan"
                className="w-full p-4 border-2 border-gray-300 rounded-xl focus:border-green-500 focus:outline-none text-lg"
              />
            </div>

            {loginError && (
              <div className="p-3 bg-red-50 border border-red-200 text-red-700 rounded-xl text-sm">
                {loginError}
              </div>
            )}

            <button
              type="submit"
              className="w-full py-4 bg-gradient-to-r from-green-500 to-green-600 text-white rounded-xl font-bold text-lg hover:from-green-600 hover:to-green-700 transition-all shadow-lg"
            >
              Log Masuk
            </button>
          </form>

          <div className="mt-6 p-4 bg-blue-50 border border-blue-200 rounded-xl">
            <p className="text-xs text-blue-800 text-center">
              💡 <strong>Tip:</strong> Simpan app ke skrin utama untuk akses mudah!
            </p>
          </div>
        </div>
      </div>
    );
  }

  // Render Main App Screen
  return (
    <div className="min-h-screen bg-gray-100">
      {/* Header */}
      <div className="bg-gradient-to-r from-green-500 to-green-600 text-white p-4 shadow-lg">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold">🛵 {rider?.name || 'Rider'}</h1>
            <div className="flex items-center gap-2 text-sm mt-1">
              <span className={`w-2 h-2 rounded-full ${gpsActive ? 'bg-green-300 animate-pulse' : 'bg-red-300'}`} />
              <span>{gpsActive ? 'GPS Aktif' : 'GPS Tidak Aktif'}</span>
            </div>
          </div>
          <button
            onClick={handleLogout}
            className="px-4 py-2 bg-white/20 hover:bg-white/30 rounded-lg transition-colors text-sm font-medium"
          >
            Log Keluar
          </button>
        </div>

        {lastUpdate && (
          <div className="mt-2 text-xs opacity-80">
            Kemas kini terakhir: {lastUpdate.toLocaleTimeString('ms-MY')}
          </div>
        )}
      </div>

      {/* Active Order */}
      {activeOrder ? (
        <div className="p-4">
          <div className="bg-white rounded-2xl shadow-lg overflow-hidden">
            {/* Order Header */}
            <div className="bg-gradient-to-r from-blue-500 to-blue-600 text-white p-4">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium">Pesanan Aktif</span>
                <span className={`px-3 py-1 rounded-full text-xs font-bold ${getStatusColor(activeOrder.status)} text-gray-800`}>
                  {getStatusLabel(activeOrder.status)}
                </span>
              </div>
              <h2 className="text-2xl font-bold">#{activeOrder.order_number}</h2>
              <p className="text-xl font-bold mt-1">RM {activeOrder.total_amount.toFixed(2)}</p>
            </div>

            {/* Customer Info */}
            <div className="p-4 space-y-3">
              <div className="flex items-start gap-3">
                <span className="text-2xl">👤</span>
                <div className="flex-1">
                  <p className="font-bold text-gray-800">{activeOrder.customer_name}</p>
                  <p className="text-gray-600 text-sm">{activeOrder.customer_phone}</p>
                </div>
              </div>

              <div className="flex items-start gap-3">
                <span className="text-2xl">📍</span>
                <div className="flex-1">
                  <p className="font-medium text-gray-800">{activeOrder.delivery_address}</p>
                </div>
              </div>
            </div>

            {/* Action Buttons */}
            <div className="p-4 border-t space-y-2">
              {/* Status Update Button */}
              {getNextStatus(activeOrder.status) && (
                <button
                  onClick={() => updateOrderStatus(activeOrder.id, getNextStatus(activeOrder.status)!)}
                  disabled={updatingStatus}
                  className="w-full py-3 bg-gradient-to-r from-green-500 to-green-600 text-white rounded-xl font-bold hover:from-green-600 hover:to-green-700 transition-all disabled:opacity-50"
                >
                  {updatingStatus ? '...' : `✓ ${getStatusLabel(getNextStatus(activeOrder.status)!)}`}
                </button>
              )}

              {/* Communication Buttons */}
              <div className="grid grid-cols-2 gap-2">
                <a
                  href={`tel:${activeOrder.customer_phone}`}
                  className="py-3 bg-blue-500 text-white rounded-xl font-medium text-center hover:bg-blue-600 transition-colors"
                >
                  📞 Hubungi
                </a>
                <a
                  href={`https://wa.me/${activeOrder.customer_phone.replace(/[^0-9]/g, '')}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="py-3 bg-green-500 text-white rounded-xl font-medium text-center hover:bg-green-600 transition-colors"
                >
                  💬 WhatsApp
                </a>
              </div>

              {/* Navigate Button */}
              {activeOrder.delivery_latitude && activeOrder.delivery_longitude && (
                <a
                  href={`https://www.google.com/maps/dir/?api=1&destination=${activeOrder.delivery_latitude},${activeOrder.delivery_longitude}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="block w-full py-3 bg-purple-500 text-white rounded-xl font-medium text-center hover:bg-purple-600 transition-colors"
                >
                  🗺️ Navigasi ke Lokasi
                </a>
              )}
            </div>
          </div>
        </div>
      ) : (
        <div className="p-4">
          <div className="bg-white rounded-2xl shadow-lg p-8 text-center">
            <div className="text-6xl mb-4">📦</div>
            <h3 className="text-xl font-bold text-gray-800 mb-2">Tiada Pesanan Aktif</h3>
            <p className="text-gray-600">Pesanan baru akan muncul di sini</p>
            {loadingOrders && (
              <div className="mt-4">
                <div className="animate-spin h-8 w-8 border-4 border-green-500 border-t-transparent rounded-full mx-auto" />
              </div>
            )}
          </div>
        </div>
      )}

      {/* GPS Info */}
      {currentLocation && (
        <div className="p-4">
          <div className="bg-white rounded-xl shadow p-4">
            <h3 className="font-bold text-gray-800 mb-2">📍 Lokasi Semasa</h3>
            <p className="text-sm text-gray-600">
              Lat: {currentLocation.lat.toFixed(6)}<br />
              Lng: {currentLocation.lng.toFixed(6)}
            </p>
          </div>
        </div>
      )}

      {/* Install Prompt (shows on first visit) */}
      {!window.matchMedia('(display-mode: standalone)').matches && (
        <div className="p-4">
          <div className="bg-blue-50 border border-blue-200 rounded-xl p-4">
            <p className="text-sm text-blue-800 text-center">
              💡 <strong>Install app</strong> untuk pengalaman lebih baik!<br />
              Tap menu <strong>⋮</strong> &gt; <strong>Add to Home Screen</strong>
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
