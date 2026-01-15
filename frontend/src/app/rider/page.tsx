'use client';

import { useState, useEffect, useRef, useCallback } from 'react';

// API base URL
const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'https://binaapp-backend.onrender.com';

interface OrderItem {
  name: string;
  quantity: number;
  price: number;
  options?: string[];
}

interface RiderOrder {
  id: string;
  order_number: string;
  customer_name: string;
  customer_phone: string;
  customer_email?: string;
  delivery_address: string;
  delivery_latitude: number | null;
  delivery_longitude: number | null;
  total_amount: number;
  subtotal: number;
  delivery_fee: number;
  status: string;
  payment_method: string;
  payment_status: string;
  created_at: string;
  restaurant_name?: string;
  items?: OrderItem[];
  notes?: string;
}

interface Rider {
  id: string;
  name: string;
  phone: string;
  vehicle_type: string;
  vehicle_plate: string;
  website_id?: string;
}

type GpsStatus = 'inactive' | 'active' | 'error' | 'permission_denied';

export default function RiderApp() {
  // Authentication
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [phone, setPhone] = useState('');
  const [password, setPassword] = useState('');
  const [rememberMe, setRememberMe] = useState(true);
  const [rider, setRider] = useState<Rider | null>(null);
  const [loginError, setLoginError] = useState('');
  const [loginLoading, setLoginLoading] = useState(false);

  // GPS Tracking
  const [gpsStatus, setGpsStatus] = useState<GpsStatus>('inactive');
  const [currentLocation, setCurrentLocation] = useState<{ lat: number; lng: number } | null>(null);
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);
  const watchIdRef = useRef<number | null>(null);
  const lastGpsSentRef = useRef<number>(0);
  const gpsIntervalRef = useRef<NodeJS.Timeout | null>(null);

  // Orders
  const [orders, setOrders] = useState<RiderOrder[]>([]);
  const [selectedOrder, setSelectedOrder] = useState<RiderOrder | null>(null);
  const [loadingOrders, setLoadingOrders] = useState(false);
  const [isOffline, setIsOffline] = useState(false);

  // Status updates
  const [updatingStatus, setUpdatingStatus] = useState(false);

  // PWA Install
  const [installPrompt, setInstallPrompt] = useState<any>(null);
  const [showInstallBanner, setShowInstallBanner] = useState(false);
  const [isPWA, setIsPWA] = useState(false);

  // Pull to refresh
  const [refreshing, setRefreshing] = useState(false);
  const [pullDistance, setPullDistance] = useState(0);
  const touchStartY = useRef(0);

  // Check if running as PWA
  useEffect(() => {
    if (typeof window !== 'undefined') {
      setIsPWA(window.matchMedia('(display-mode: standalone)').matches);
    }
  }, []);

  // Check for saved rider credentials on mount
  useEffect(() => {
    const savedRider = localStorage.getItem('rider_data');
    const savedPhone = localStorage.getItem('rider_phone');

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

    if (savedPhone) {
      setPhone(savedPhone);
    }

    // Load cached orders
    const cachedOrders = localStorage.getItem('rider_cached_orders');
    if (cachedOrders) {
      try {
        setOrders(JSON.parse(cachedOrders));
      } catch (e) {
        console.error('Failed to load cached orders:', e);
      }
    }
  }, []);

  // Online/Offline detection
  useEffect(() => {
    const handleOnline = () => setIsOffline(false);
    const handleOffline = () => setIsOffline(true);

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);
    setIsOffline(!navigator.onLine);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
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

  // PWA Install prompt
  useEffect(() => {
    console.log('[Rider PWA] Setting up install prompt listener...');

    const handleBeforeInstallPrompt = (e: Event) => {
      console.log('[Rider PWA] ✅ Install prompt event captured!');
      e.preventDefault();
      setInstallPrompt(e);
      setShowInstallBanner(true);
    };

    window.addEventListener('beforeinstallprompt', handleBeforeInstallPrompt);

    // Check if already installed
    if (window.matchMedia('(display-mode: standalone)').matches) {
      console.log('[Rider PWA] ℹ️ App is already installed');
    } else {
      console.log('[Rider PWA] ⏳ Waiting for install prompt...');
    }

    return () => {
      window.removeEventListener('beforeinstallprompt', handleBeforeInstallPrompt);
    };
  }, []);

  // Register service worker for rider app
  useEffect(() => {
    if ('serviceWorker' in navigator && typeof window !== 'undefined') {
      console.log('[Rider PWA] Attempting to register service worker...');

      navigator.serviceWorker.register('/sw-rider.js', { scope: '/' })
        .then((registration) => {
          console.log('[Rider PWA] ✅ Service Worker registered successfully');
          console.log('[Rider PWA] Scope:', registration.scope);
          console.log('[Rider PWA] State:', registration.active?.state || 'installing');

          // Check for updates
          registration.addEventListener('updatefound', () => {
            console.log('[Rider PWA] Service Worker update found');
          });
        })
        .catch((err) => {
          console.error('[Rider PWA] ❌ Service worker registration failed:', err);
        });
    } else {
      console.warn('[Rider PWA] Service Worker not supported in this browser');
    }
  }, []);

  // API fetch helper (without Supabase auth for rider)
  const riderApiFetch = async (path: string, options?: RequestInit) => {
    const res = await fetch(`${API_BASE}${path}`, {
      headers: {
        'Content-Type': 'application/json',
      },
      ...options,
    });

    if (!res.ok) {
      const text = await res.text();
      throw new Error(text || 'API request failed');
    }

    return res.json();
  };

  // Handle login
  const handleLogin = async () => {
    if (!phone.trim() || !password.trim()) {
      setLoginError('Sila masukkan nombor telefon dan kata laluan');
      return;
    }

    setLoginLoading(true);
    setLoginError('');

    try {
      const response = await riderApiFetch('/api/v1/delivery/riders/login', {
        method: 'POST',
        body: JSON.stringify({
          phone: phone.replace(/\s/g, ''),
          password: password
        })
      });

      if (response.success && response.rider) {
        setRider(response.rider);
        setIsLoggedIn(true);
        localStorage.setItem('rider_data', JSON.stringify(response.rider));

        if (rememberMe) {
          localStorage.setItem('rider_phone', phone);
        } else {
          localStorage.removeItem('rider_phone');
        }

        setLoginError('');
        console.log('Login successful:', response.rider.name);
      } else {
        setLoginError('Login gagal. Sila cuba lagi.');
      }
    } catch (error: any) {
      console.error('Login error:', error);
      setLoginError(error.message || 'Nombor telefon atau kata laluan salah');
    } finally {
      setLoginLoading(false);
    }
  };

  // Handle logout
  const handleLogout = () => {
    stopGPSTracking();
    setIsLoggedIn(false);
    setRider(null);
    setPassword('');
    setOrders([]);
    setSelectedOrder(null);
    localStorage.removeItem('rider_data');
    localStorage.removeItem('rider_cached_orders');
  };

  // Start GPS tracking
  const startGPSTracking = () => {
    if (!navigator.geolocation) {
      alert('GPS tidak disokong oleh pelayar anda');
      setGpsStatus('error');
      return;
    }

    const options = {
      enableHighAccuracy: true,
      timeout: 10000,
      maximumAge: 5000
    };

    // Watch position continuously
    watchIdRef.current = navigator.geolocation.watchPosition(
      (position) => {
        const { latitude, longitude } = position.coords;
        setCurrentLocation({ lat: latitude, lng: longitude });
        setGpsStatus('active');

        // Throttle GPS updates to every 15 seconds
        const now = Date.now();
        if (now - lastGpsSentRef.current >= 15000) {
          sendLocationToAPI(latitude, longitude);
          lastGpsSentRef.current = now;
        }
      },
      (error) => {
        console.error('GPS error:', error);
        if (error.code === error.PERMISSION_DENIED) {
          setGpsStatus('permission_denied');
          alert('Sila benarkan akses GPS untuk menggunakan app ini');
        } else {
          setGpsStatus('error');
        }
      },
      options
    );

    // Send initial GPS immediately
    navigator.geolocation.getCurrentPosition(
      (position) => {
        const { latitude, longitude } = position.coords;
        setCurrentLocation({ lat: latitude, lng: longitude });
        setGpsStatus('active');
        sendLocationToAPI(latitude, longitude);
        lastGpsSentRef.current = Date.now();
      },
      (error) => {
        console.error('Initial GPS error:', error);
      },
      { enableHighAccuracy: true, timeout: 10000 }
    );

    // Backup interval to ensure GPS is sent even if watchPosition events are slow
    gpsIntervalRef.current = setInterval(() => {
      if (currentLocation) {
        sendLocationToAPI(currentLocation.lat, currentLocation.lng);
      }
    }, 15000);

    console.log('GPS tracking started');
  };

  // Stop GPS tracking
  const stopGPSTracking = () => {
    if (watchIdRef.current !== null) {
      navigator.geolocation.clearWatch(watchIdRef.current);
      watchIdRef.current = null;
    }
    if (gpsIntervalRef.current) {
      clearInterval(gpsIntervalRef.current);
      gpsIntervalRef.current = null;
    }
    setGpsStatus('inactive');
    console.log('GPS tracking stopped');
  };

  // Send location to API
  const sendLocationToAPI = async (lat: number, lng: number) => {
    if (!rider || isOffline) return;

    try {
      await riderApiFetch(`/api/v1/delivery/riders/${rider.id}/location`, {
        method: 'PUT',
        body: JSON.stringify({
          latitude: lat,
          longitude: lng,
          timestamp: new Date().toISOString()
        })
      });

      setLastUpdate(new Date());
      console.log(`GPS sent: ${lat.toFixed(6)}, ${lng.toFixed(6)}`);
    } catch (error) {
      console.error('Failed to send GPS:', error);
    }
  };

  // Fetch rider's assigned orders
  const fetchOrders = useCallback(async () => {
    if (!rider) return;

    setLoadingOrders(true);
    try {
      const response = await riderApiFetch(`/api/v1/delivery/riders/${rider.id}/orders`);

      const fetchedOrders: RiderOrder[] = response.orders || [];
      setOrders(fetchedOrders);

      // Cache orders for offline use
      localStorage.setItem('rider_cached_orders', JSON.stringify(fetchedOrders));

      console.log(`Fetched ${fetchedOrders.length} orders`);
    } catch (error) {
      console.error('Failed to fetch orders:', error);
      // Keep existing orders (from cache) if fetch fails
    } finally {
      setLoadingOrders(false);
      setRefreshing(false);
    }
  }, [rider]);

  // Update order status
  const updateOrderStatus = async (orderId: string, newStatus: string) => {
    if (!rider || isOffline) {
      alert('Anda dalam mod offline. Sila sambung ke internet.');
      return;
    }

    setUpdatingStatus(true);
    try {
      await riderApiFetch(`/api/v1/delivery/riders/${rider.id}/orders/${orderId}/status`, {
        method: 'PUT',
        body: JSON.stringify({
          status: newStatus,
          notes: `Updated by rider ${rider.name}`
        })
      });

      // Refresh orders
      await fetchOrders();

      // Close order detail if completed
      if (newStatus === 'delivered') {
        setSelectedOrder(null);
      }

      alert('Status dikemas kini!');
    } catch (error: any) {
      console.error('Failed to update status:', error);
      alert('Gagal mengemas kini status. ' + (error.message || ''));
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

  const getNextStatusLabel = (currentStatus: string): string => {
    const labels: Record<string, string> = {
      'ready': 'Ambil Pesanan',
      'picked_up': 'Mula Hantar',
      'delivering': 'Selesai Hantar'
    };
    return labels[currentStatus] || 'Kemas Kini';
  };

  const getStatusLabel = (status: string): string => {
    const labels: Record<string, string> = {
      'pending': 'Menunggu',
      'confirmed': 'Disahkan',
      'preparing': 'Sedang Disediakan',
      'ready': 'Siap Diambil',
      'picked_up': 'Diambil',
      'delivering': 'Dalam Penghantaran',
      'delivered': 'Dihantar',
      'completed': 'Selesai',
      'cancelled': 'Dibatalkan'
    };
    return labels[status] || status;
  };

  const getStatusColor = (status: string): string => {
    const colors: Record<string, string> = {
      'pending': 'bg-gray-100 text-gray-800',
      'confirmed': 'bg-yellow-100 text-yellow-800',
      'preparing': 'bg-blue-100 text-blue-800',
      'ready': 'bg-green-100 text-green-800',
      'picked_up': 'bg-purple-100 text-purple-800',
      'delivering': 'bg-orange-100 text-orange-800',
      'delivered': 'bg-emerald-100 text-emerald-800',
      'completed': 'bg-gray-100 text-gray-800',
      'cancelled': 'bg-red-100 text-red-800'
    };
    return colors[status] || 'bg-gray-100 text-gray-800';
  };

  // Open WhatsApp with pre-filled message
  const openWhatsApp = (order: RiderOrder) => {
    const phone = order.customer_phone.replace(/^0/, '60').replace(/[^0-9]/g, '');
    const message = encodeURIComponent(
      `Salam! Saya ${rider?.name || 'rider'} dari BinaApp. ` +
      `Pesanan anda #${order.order_number} sedang dalam perjalanan. ` +
      `Anggaran tiba dalam 15-20 minit. Terima kasih!`
    );
    window.open(`https://wa.me/${phone}?text=${message}`, '_blank');
  };

  // Open navigation (Waze preferred, fallback to Google Maps)
  const openNavigation = (order: RiderOrder) => {
    if (order.delivery_latitude && order.delivery_longitude) {
      // Try Waze first (popular in Malaysia)
      const wazeUrl = `https://waze.com/ul?ll=${order.delivery_latitude},${order.delivery_longitude}&navigate=yes`;
      window.open(wazeUrl, '_blank');
    } else {
      // Use address string
      const encoded = encodeURIComponent(order.delivery_address);
      window.open(`https://www.google.com/maps/search/?api=1&query=${encoded}`, '_blank');
    }
  };

  // Open Google Maps
  const openGoogleMaps = (order: RiderOrder) => {
    if (order.delivery_latitude && order.delivery_longitude) {
      const googleUrl = `https://www.google.com/maps/dir/?api=1&destination=${order.delivery_latitude},${order.delivery_longitude}`;
      window.open(googleUrl, '_blank');
    } else {
      const encoded = encodeURIComponent(order.delivery_address);
      window.open(`https://www.google.com/maps/search/?api=1&query=${encoded}`, '_blank');
    }
  };

  // Install PWA
  const handleInstallPWA = async () => {
    console.log('[Rider PWA] Install button clicked');

    if (!installPrompt) {
      console.warn('[Rider PWA] No install prompt available');
      alert('Install prompt tidak tersedia. Sila install manual:\n\nAndroid: Menu (⋮) → Add to Home Screen\niPhone: Share (⬆️) → Add to Home Screen');
      return;
    }

    console.log('[Rider PWA] Showing install prompt...');
    installPrompt.prompt();

    const { outcome } = await installPrompt.userChoice;
    console.log(`[Rider PWA] Install outcome: ${outcome}`);

    if (outcome === 'accepted') {
      console.log('[Rider PWA] ✅ User accepted install');
      setShowInstallBanner(false);
    } else {
      console.log('[Rider PWA] ❌ User declined install');
    }

    setInstallPrompt(null);
  };

  // Pull to refresh handlers
  const handleTouchStart = (e: React.TouchEvent) => {
    touchStartY.current = e.touches[0].clientY;
  };

  const handleTouchMove = (e: React.TouchEvent) => {
    const currentY = e.touches[0].clientY;
    const diff = currentY - touchStartY.current;

    if (diff > 0 && window.scrollY === 0) {
      setPullDistance(Math.min(diff, 100));
    }
  };

  const handleTouchEnd = () => {
    if (pullDistance > 60) {
      setRefreshing(true);
      fetchOrders();
    }
    setPullDistance(0);
  };

  // Get active orders count
  const activeOrdersCount = orders.filter(o =>
    ['ready', 'picked_up', 'delivering'].includes(o.status)
  ).length;

  // GPS Status indicator
  const getGpsStatusInfo = () => {
    switch (gpsStatus) {
      case 'active':
        return { color: 'bg-green-400', text: 'GPS Aktif', pulse: true };
      case 'error':
        return { color: 'bg-yellow-400', text: 'GPS Error', pulse: false };
      case 'permission_denied':
        return { color: 'bg-red-400', text: 'GPS Dinafikan', pulse: false };
      default:
        return { color: 'bg-gray-400', text: 'GPS Tidak Aktif', pulse: false };
    }
  };

  const gpsInfo = getGpsStatusInfo();

  // Render Login Screen
  if (!isLoggedIn) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-orange-500 to-orange-600 flex items-center justify-center px-4">
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
                className="w-full p-4 border-2 border-gray-300 rounded-xl focus:border-orange-500 focus:outline-none text-lg"
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
                className="w-full p-4 border-2 border-gray-300 rounded-xl focus:border-orange-500 focus:outline-none text-lg"
              />
            </div>

            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="rememberMe"
                checked={rememberMe}
                onChange={(e) => setRememberMe(e.target.checked)}
                className="w-5 h-5 text-orange-500 rounded border-gray-300 focus:ring-orange-500"
              />
              <label htmlFor="rememberMe" className="text-sm text-gray-700">
                Ingat nombor telefon saya
              </label>
            </div>

            {loginError && (
              <div className="p-3 bg-red-50 border border-red-200 text-red-700 rounded-xl text-sm">
                {loginError}
              </div>
            )}

            <button
              type="submit"
              disabled={loginLoading}
              className="w-full py-4 bg-gradient-to-r from-orange-500 to-orange-600 text-white rounded-xl font-bold text-lg hover:from-orange-600 hover:to-orange-700 transition-all shadow-lg disabled:opacity-50"
            >
              {loginLoading ? (
                <span className="flex items-center justify-center gap-2">
                  <span className="animate-spin h-5 w-5 border-2 border-white border-t-transparent rounded-full"></span>
                  Log Masuk...
                </span>
              ) : (
                'Log Masuk'
              )}
            </button>
          </form>

          <div className="mt-6 p-4 bg-gradient-to-r from-orange-50 to-orange-100 border-2 border-orange-200 rounded-xl">
            <div className="flex items-start gap-3">
              <div className="text-2xl">📲</div>
              <div className="flex-1">
                <p className="text-sm font-bold text-orange-900 mb-1">
                  Install App untuk Pengalaman Terbaik!
                </p>
                <p className="text-xs text-orange-800 mb-2">
                  Simpan BinaApp Rider ke skrin utama telefon anda:
                </p>
                <div className="text-xs text-orange-700 space-y-1">
                  <p>📱 <strong>Android:</strong> Tap menu ⋮ → Add to Home Screen</p>
                  <p>🍎 <strong>iPhone:</strong> Tap <span className="inline-flex items-center justify-center w-4 h-4 bg-orange-200 rounded">+</span> → Add to Home Screen</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Render Order Detail
  if (selectedOrder) {
    return (
      <div className="min-h-screen bg-gray-100">
        {/* Header */}
        <div className="bg-gradient-to-r from-orange-500 to-orange-600 text-white p-4 shadow-lg sticky top-0 z-50">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setSelectedOrder(null)}
              className="p-2 hover:bg-white/20 rounded-lg transition-colors"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
            </button>
            <div className="flex-1">
              <h1 className="text-lg font-bold">#{selectedOrder.order_number}</h1>
              <span className={`inline-block mt-1 px-2 py-0.5 rounded-full text-xs font-bold ${getStatusColor(selectedOrder.status)}`}>
                {getStatusLabel(selectedOrder.status)}
              </span>
            </div>
          </div>
        </div>

        <div className="p-4 space-y-4 pb-32">
          {/* Amount Card */}
          <div className="bg-white rounded-2xl shadow-lg p-4">
            <div className="text-center">
              <p className="text-gray-600 text-sm">Jumlah Bayaran</p>
              <p className="text-3xl font-bold text-orange-600">RM {selectedOrder.total_amount.toFixed(2)}</p>
              <p className="text-sm text-gray-500 mt-1">
                {selectedOrder.payment_method === 'cod' ? 'Bayar Tunai (COD)' :
                 selectedOrder.payment_status === 'paid' ? 'Telah Dibayar' : 'Belum Dibayar'}
              </p>
            </div>
          </div>

          {/* Customer Info */}
          <div className="bg-white rounded-2xl shadow-lg p-4">
            <h3 className="font-bold text-gray-800 mb-3 flex items-center gap-2">
              <span className="text-xl">👤</span> Pelanggan
            </h3>
            <div className="space-y-2">
              <p className="font-medium text-gray-800">{selectedOrder.customer_name}</p>
              <p className="text-gray-600">{selectedOrder.customer_phone}</p>
            </div>
          </div>

          {/* Delivery Address */}
          <div className="bg-white rounded-2xl shadow-lg p-4">
            <h3 className="font-bold text-gray-800 mb-3 flex items-center gap-2">
              <span className="text-xl">📍</span> Alamat Penghantaran
            </h3>
            <p className="text-gray-700">{selectedOrder.delivery_address}</p>
          </div>

          {/* Order Items */}
          {selectedOrder.items && selectedOrder.items.length > 0 && (
            <div className="bg-white rounded-2xl shadow-lg p-4">
              <h3 className="font-bold text-gray-800 mb-3 flex items-center gap-2">
                <span className="text-xl">🍽️</span> Item Pesanan
              </h3>
              <div className="space-y-2">
                {selectedOrder.items.map((item, index) => (
                  <div key={index} className="flex justify-between items-center py-2 border-b last:border-0">
                    <div>
                      <p className="font-medium text-gray-800">{item.quantity}x {item.name}</p>
                      {item.options && item.options.length > 0 && (
                        <p className="text-sm text-gray-500">{item.options.join(', ')}</p>
                      )}
                    </div>
                    <p className="text-gray-600">RM {item.price.toFixed(2)}</p>
                  </div>
                ))}
              </div>
              <div className="mt-3 pt-3 border-t space-y-1">
                <div className="flex justify-between text-sm text-gray-600">
                  <span>Subtotal</span>
                  <span>RM {selectedOrder.subtotal.toFixed(2)}</span>
                </div>
                <div className="flex justify-between text-sm text-gray-600">
                  <span>Penghantaran</span>
                  <span>RM {selectedOrder.delivery_fee.toFixed(2)}</span>
                </div>
                <div className="flex justify-between font-bold text-gray-800 pt-1">
                  <span>Jumlah</span>
                  <span>RM {selectedOrder.total_amount.toFixed(2)}</span>
                </div>
              </div>
            </div>
          )}

          {/* Notes */}
          {selectedOrder.notes && (
            <div className="bg-yellow-50 border border-yellow-200 rounded-2xl p-4">
              <h3 className="font-bold text-yellow-800 mb-2 flex items-center gap-2">
                <span className="text-xl">📝</span> Nota
              </h3>
              <p className="text-yellow-900">{selectedOrder.notes}</p>
            </div>
          )}
        </div>

        {/* Fixed Bottom Actions */}
        <div className="fixed bottom-0 left-0 right-0 bg-white border-t shadow-lg p-4 space-y-3 safe-area-pb">
          {/* Status Update Button */}
          {getNextStatus(selectedOrder.status) && (
            <button
              onClick={() => updateOrderStatus(selectedOrder.id, getNextStatus(selectedOrder.status)!)}
              disabled={updatingStatus || isOffline}
              className="w-full py-4 bg-gradient-to-r from-green-500 to-green-600 text-white rounded-xl font-bold text-lg hover:from-green-600 hover:to-green-700 transition-all disabled:opacity-50 shadow-lg"
            >
              {updatingStatus ? (
                <span className="flex items-center justify-center gap-2">
                  <span className="animate-spin h-5 w-5 border-2 border-white border-t-transparent rounded-full"></span>
                  Mengemas kini...
                </span>
              ) : (
                `✓ ${getNextStatusLabel(selectedOrder.status)}`
              )}
            </button>
          )}

          {/* Communication & Navigation Buttons */}
          <div className="grid grid-cols-2 gap-2">
            <a
              href={`tel:${selectedOrder.customer_phone}`}
              className="py-3 bg-blue-500 text-white rounded-xl font-medium text-center hover:bg-blue-600 transition-colors flex items-center justify-center gap-2"
            >
              <span>📞</span> Hubungi
            </a>
            <button
              onClick={() => openWhatsApp(selectedOrder)}
              className="py-3 bg-green-500 text-white rounded-xl font-medium hover:bg-green-600 transition-colors flex items-center justify-center gap-2"
            >
              <span>💬</span> WhatsApp
            </button>
          </div>

          <div className="grid grid-cols-2 gap-2">
            <button
              onClick={() => openNavigation(selectedOrder)}
              className="py-3 bg-purple-500 text-white rounded-xl font-medium hover:bg-purple-600 transition-colors flex items-center justify-center gap-2"
            >
              <span>🗺️</span> Waze
            </button>
            <button
              onClick={() => openGoogleMaps(selectedOrder)}
              className="py-3 bg-red-500 text-white rounded-xl font-medium hover:bg-red-600 transition-colors flex items-center justify-center gap-2"
            >
              <span>📍</span> Google Maps
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Render Main App Screen (Dashboard)
  return (
    <div
      className="min-h-screen bg-gray-100"
      onTouchStart={handleTouchStart}
      onTouchMove={handleTouchMove}
      onTouchEnd={handleTouchEnd}
    >
      {/* Pull to Refresh Indicator */}
      {pullDistance > 0 && (
        <div
          className="fixed top-0 left-0 right-0 flex justify-center z-40 bg-orange-500 transition-all"
          style={{ height: pullDistance }}
        >
          <div className="flex items-center justify-center text-white">
            {pullDistance > 60 ? 'Lepaskan untuk muat semula' : 'Tarik ke bawah untuk muat semula'}
          </div>
        </div>
      )}

      {/* Header */}
      <div className="bg-gradient-to-r from-orange-500 to-orange-600 text-white p-4 shadow-lg sticky top-0 z-50">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold">🛵 {rider?.name || 'Rider'}</h1>
            <div className="flex items-center gap-2 text-sm mt-1">
              <span className={`w-2 h-2 rounded-full ${gpsInfo.color} ${gpsInfo.pulse ? 'animate-pulse' : ''}`} />
              <span>{gpsInfo.text}</span>
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
            GPS kemas kini: {lastUpdate.toLocaleTimeString('ms-MY')}
          </div>
        )}
      </div>

      {/* Offline Banner */}
      {isOffline && (
        <div className="bg-yellow-500 text-white px-4 py-2 text-center text-sm font-medium">
          📶 Mod Offline - Data mungkin tidak terkini
        </div>
      )}

      {/* PWA Install Banner - Enhanced Design */}
      {showInstallBanner && !isPWA && (
        <div className="fixed bottom-20 left-4 right-4 z-50 animate-slide-up">
          <div className="bg-gradient-to-r from-orange-500 to-orange-600 text-white rounded-2xl shadow-2xl p-4 border-2 border-white/20">
            <button
              onClick={() => setShowInstallBanner(false)}
              className="absolute -top-2 -right-2 w-8 h-8 bg-white text-orange-600 rounded-full shadow-lg font-bold hover:scale-110 transition-transform"
            >
              ×
            </button>
            <div className="flex items-start gap-3">
              <div className="text-4xl">🛵</div>
              <div className="flex-1">
                <p className="font-bold text-lg mb-1">Install BinaApp Rider</p>
                <p className="text-sm opacity-90 mb-3">
                  Simpan ke skrin utama untuk akses mudah & cepat!
                </p>
                <ul className="text-xs space-y-1 mb-3 opacity-90">
                  <li>✓ Buka terus dari home screen</li>
                  <li>✓ Kerja tanpa browser</li>
                  <li>✓ Akses lebih cepat</li>
                </ul>
                <button
                  onClick={handleInstallPWA}
                  className="w-full py-3 bg-white text-orange-600 rounded-xl font-bold text-base hover:bg-orange-50 transition-all shadow-lg"
                >
                  📲 Install Sekarang
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* iOS Install Hint - For Safari users */}
      {!isPWA && typeof window !== 'undefined' && /iPhone|iPad|iPod/.test(navigator.userAgent) && !/CriOS|FxiOS|EdgiOS/.test(navigator.userAgent) && (
        <div className="bg-blue-500 text-white px-4 py-3 text-center text-sm">
          💡 <strong>iPhone users:</strong> Tap <span className="inline-block mx-1">
            <svg className="inline w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
              <path d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z"/>
            </svg>
          </span> then &quot;Add to Home Screen&quot;
        </div>
      )}

      {/* Content */}
      <div className="p-4 space-y-4">
        {/* Active Orders Summary */}
        <div className="bg-white rounded-2xl shadow-lg p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-gray-600 text-sm">Pesanan Aktif</p>
              <p className="text-3xl font-bold text-orange-600">{activeOrdersCount}</p>
            </div>
            <button
              onClick={() => fetchOrders()}
              disabled={loadingOrders || refreshing}
              className="p-3 bg-orange-100 text-orange-600 rounded-xl hover:bg-orange-200 transition-colors disabled:opacity-50"
            >
              {loadingOrders || refreshing ? (
                <span className="animate-spin inline-block h-5 w-5 border-2 border-orange-600 border-t-transparent rounded-full"></span>
              ) : (
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
              )}
            </button>
          </div>
        </div>

        {/* GPS Info Card */}
        {currentLocation && (
          <div className="bg-white rounded-xl shadow p-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="font-bold text-gray-800 flex items-center gap-2">
                  <span className={`w-3 h-3 rounded-full ${gpsInfo.color} ${gpsInfo.pulse ? 'animate-pulse' : ''}`}></span>
                  Lokasi Semasa
                </h3>
                <p className="text-xs text-gray-500 mt-1">
                  {currentLocation.lat.toFixed(6)}, {currentLocation.lng.toFixed(6)}
                </p>
              </div>
              <button
                onClick={() => window.open(`https://www.google.com/maps?q=${currentLocation.lat},${currentLocation.lng}`, '_blank')}
                className="px-3 py-1.5 bg-gray-100 text-gray-700 rounded-lg text-sm hover:bg-gray-200 transition-colors"
              >
                Lihat Peta
              </button>
            </div>
          </div>
        )}

        {/* Orders List */}
        <div>
          <h2 className="text-lg font-bold text-gray-800 mb-3">Senarai Pesanan</h2>

          {orders.length === 0 ? (
            <div className="bg-white rounded-2xl shadow-lg p-8 text-center">
              <div className="text-6xl mb-4">📦</div>
              <h3 className="text-xl font-bold text-gray-800 mb-2">Tiada Pesanan</h3>
              <p className="text-gray-600">Pesanan baru akan muncul di sini</p>
              {loadingOrders && (
                <div className="mt-4">
                  <div className="animate-spin h-8 w-8 border-4 border-orange-500 border-t-transparent rounded-full mx-auto" />
                </div>
              )}
            </div>
          ) : (
            <div className="space-y-3">
              {orders.map((order) => (
                <button
                  key={order.id}
                  onClick={() => setSelectedOrder(order)}
                  className="w-full bg-white rounded-2xl shadow-lg p-4 text-left hover:shadow-xl transition-all"
                >
                  <div className="flex items-start justify-between mb-2">
                    <div>
                      <p className="font-bold text-gray-800">#{order.order_number}</p>
                      <p className="text-sm text-gray-600">{order.customer_name}</p>
                    </div>
                    <span className={`px-2 py-1 rounded-full text-xs font-bold ${getStatusColor(order.status)}`}>
                      {getStatusLabel(order.status)}
                    </span>
                  </div>

                  <div className="flex items-center gap-2 text-sm text-gray-600 mb-2">
                    <span>📍</span>
                    <span className="truncate">{order.delivery_address}</span>
                  </div>

                  <div className="flex items-center justify-between">
                    <p className="text-lg font-bold text-orange-600">RM {order.total_amount.toFixed(2)}</p>
                    <span className="text-xs text-gray-500">
                      {new Date(order.created_at).toLocaleTimeString('ms-MY', { hour: '2-digit', minute: '2-digit' })}
                    </span>
                  </div>

                  {/* Quick action for active orders */}
                  {['ready', 'picked_up', 'delivering'].includes(order.status) && (
                    <div className="mt-3 pt-3 border-t">
                      <div className="flex items-center justify-between text-sm">
                        <span className="text-gray-600">Tindakan seterusnya:</span>
                        <span className="font-medium text-green-600">{getNextStatusLabel(order.status)}</span>
                      </div>
                    </div>
                  )}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Bottom Safe Area Padding */}
      <div className="h-8 safe-area-pb"></div>
    </div>
  );
}
