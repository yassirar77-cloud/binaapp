'use client';
import { useCallback, useMemo, useRef, useState, useEffect } from 'react';
import { useParams } from 'next/navigation';

const API_URL = 'https://binaapp-backend.onrender.com';

type DeliveryZone = {
    id: string;
    zone_name: string;
    delivery_fee: number;
    estimated_time_min?: number;
    estimated_time_max?: number;
};

type DeliverySettings = {
    minimum_order?: number;
    delivery_hours?: string;
    whatsapp_number?: string;
};

type MenuCategory = {
    id: string;
    name: string;
    is_active?: boolean;
    sort_order?: number;
};

type MenuItem = {
    id: string;
    name: string;
    description?: string | null;
    price: number;
    image_url?: string | null;
    category_id?: string | null;
};

type MenuResponse = {
    categories?: MenuCategory[];
    items?: MenuItem[];
};

type CartItem = MenuItem & { qty: number };

export default function DeliveryPage() {
    const { websiteId } = useParams();
    const [loading, setLoading] = useState(true);
    const [menu, setMenu] = useState<MenuResponse>({ categories: [], items: [] });
    const [zones, setZones] = useState<DeliveryZone[]>([]);
    const [settings, setSettings] = useState<DeliverySettings | null>(null);
    const [cart, setCart] = useState<CartItem[]>([]);
    const [selectedZone, setSelectedZone] = useState<DeliveryZone | null>(null);
    const [customerInfo, setCustomerInfo] = useState({ name: '', phone: '', address: '', notes: '' });
    const [selectedCategoryId, setSelectedCategoryId] = useState<string>('all');
    const [isCartOpen, setIsCartOpen] = useState(false);
    const [isLocationDropdownOpen, setIsLocationDropdownOpen] = useState(false);
    const [flashItemId, setFlashItemId] = useState<string | null>(null);
    const menuTopRef = useRef<HTMLDivElement | null>(null);
    const locationDropdownRef = useRef<HTMLDivElement | null>(null);

    const storageKey = useMemo(() => `pesanan:selectedZone:${websiteId ?? 'unknown'}`, [websiteId]);

    const loadData = useCallback(async () => {
        try {
            const [menuRes, zonesRes] = await Promise.all([
                fetch(`${API_URL}/v1/delivery/menu/${websiteId}`),
                fetch(`${API_URL}/v1/delivery/zones/${websiteId}`)
            ]);
            const menuData = await menuRes.json();
            const zonesData = await zonesRes.json();
            setMenu(menuData);
            setZones(zonesData.zones || []);
            setSettings(zonesData.settings || {});
        } catch (err) {
            console.error('Failed to load:', err);
        }
        setLoading(false);
    }, [websiteId]);

    useEffect(() => {
        loadData();
    }, [loadData]);

    useEffect(() => {
        // Restore selected zone from localStorage
        if (typeof window === 'undefined') return;
        try {
            const raw = window.localStorage.getItem(storageKey);
            if (!raw) return;
            const parsed = JSON.parse(raw) as DeliveryZone;
            if (parsed?.id && parsed?.zone_name) {
                setSelectedZone(parsed);
            }
        } catch {
            // ignore
        }
    }, [storageKey]);

    useEffect(() => {
        // Prevent background scroll when mobile cart drawer is open
        if (typeof document === 'undefined') return;
        const prev = document.body.style.overflow;
        if (isCartOpen) document.body.style.overflow = 'hidden';
        return () => {
            document.body.style.overflow = prev;
        };
    }, [isCartOpen]);

    // Close location dropdown when clicking outside
    useEffect(() => {
        function handleClickOutside(event: MouseEvent) {
            if (locationDropdownRef.current && !locationDropdownRef.current.contains(event.target as Node)) {
                setIsLocationDropdownOpen(false);
            }
        }
        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    function onSelectZone(zone: DeliveryZone) {
        setSelectedZone(zone);
        setIsLocationDropdownOpen(false);
        if (typeof window !== 'undefined') {
            try {
                window.localStorage.setItem(storageKey, JSON.stringify(zone));
            } catch {
                // ignore
            }
        }
    }

    function addToCart(item: MenuItem) {
        const existing = cart.find((c) => c.id === item.id);
        if (existing) {
            setCart(cart.map((c) => (c.id === item.id ? { ...c, qty: c.qty + 1 } : c)));
        } else {
            setCart([...cart, { ...item, qty: 1 }]);
        }
        setFlashItemId(item.id);
        window.setTimeout(() => setFlashItemId((prev) => (prev === item.id ? null : prev)), 350);
    }

    function updateQty(id: string, delta: number) {
        setCart(
            cart
                .map((c) => {
                    if (c.id === id) {
                        const newQty = c.qty + delta;
                        return newQty > 0 ? { ...c, qty: newQty } : null;
                    }
                    return c;
                })
                .filter(Boolean) as CartItem[]
        );
    }

    const itemCount = cart.reduce((sum, i) => sum + i.qty, 0);
    const subtotal = cart.reduce((sum, item) => sum + item.price * item.qty, 0);
    const deliveryFee = selectedZone?.delivery_fee || 0;
    const total = subtotal + deliveryFee;
    const minOrder = settings?.minimum_order || 0;

    const categories = useMemo(() => {
        const raw = (menu.categories || []) as MenuCategory[];
        return raw.filter((c) => c && c.id && c.name);
    }, [menu.categories]);

    const filteredItems = useMemo(() => {
        const items = (menu.items || []) as MenuItem[];
        if (selectedCategoryId === 'all') return items;
        return items.filter((i) => i.category_id === selectedCategoryId);
    }, [menu.items, selectedCategoryId]);

    function checkout() {
        if (!selectedZone) return alert('Sila pilih kawasan delivery');
        if (subtotal < minOrder) return alert(`Minimum order: RM${minOrder}`);
        if (!customerInfo.name || !customerInfo.phone || !customerInfo.address) {
            return alert('Sila isi maklumat penghantaran');
        }

        let msg = `🛵 *PESANAN DELIVERY*\n\n`;
        msg += `👤 *Pelanggan:* ${customerInfo.name}\n`;
        msg += `📱 *Telefon:* ${customerInfo.phone}\n`;
        msg += `📍 *Alamat:* ${customerInfo.address}\n`;
        if (customerInfo.notes) msg += `📝 *Nota:* ${customerInfo.notes}\n`;
        msg += `\n📦 *Pesanan:*\n`;
        cart.forEach(item => {
            msg += `• ${item.name} x${item.qty} - RM${(item.price * item.qty).toFixed(2)}\n`;
        });
        msg += `\n💰 Subtotal: RM${subtotal.toFixed(2)}`;
        msg += `\n🚗 Delivery (${selectedZone.zone_name}): RM${deliveryFee.toFixed(2)}`;
        msg += `\n\n*JUMLAH: RM${total.toFixed(2)}*`;

        const whatsapp = settings?.whatsapp_number || '60123456789';
        window.open(`https://wa.me/${whatsapp.replace(/[^0-9]/g, '')}?text=${encodeURIComponent(msg)}`, '_blank');
    }

    if (loading) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-gray-50">
                <div className="text-center">
                    <div className="w-16 h-16 border-4 border-orange-500 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
                    <p className="text-gray-600">Memuatkan menu...</p>
                </div>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-gray-100">
            {/* ============ HEADER WITH LOCATION SELECTOR ============ */}
            <header className="bg-gradient-to-r from-orange-500 to-orange-600 text-white sticky top-0 z-50 shadow-lg">
                <div className="max-w-3xl mx-auto px-4 py-3">
                    <div className="flex items-center justify-between">
                        {/* Left: Brand */}
                        <div className="flex items-center gap-2">
                            <span className="text-2xl">🛵</span>
                            <span className="font-bold text-lg hidden sm:inline">Pesan Delivery</span>
                        </div>
                        
                        {/* Center/Right: Location Selector */}
                        <div className="relative" ref={locationDropdownRef}>
                            <button
                                onClick={() => setIsLocationDropdownOpen(!isLocationDropdownOpen)}
                                className="flex items-center gap-2 bg-white/20 hover:bg-white/30 px-3 py-2 rounded-full transition-all duration-200 text-sm font-medium"
                            >
                                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
                                </svg>
                                <span className="max-w-[150px] truncate">
                                    {selectedZone ? selectedZone.zone_name : 'Pilih Lokasi'}
                                </span>
                                <svg className={`w-4 h-4 transition-transform duration-200 ${isLocationDropdownOpen ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                                </svg>
                            </button>
                            
                            {/* Location Dropdown */}
                            {isLocationDropdownOpen && (
                                <div className="absolute right-0 mt-2 w-72 bg-white rounded-xl shadow-2xl overflow-hidden animate-fadeIn z-50">
                                    <div className="p-3 bg-gray-50 border-b">
                                        <p className="text-gray-700 font-semibold text-sm">📍 Pilih Kawasan Delivery</p>
                                    </div>
                                    <div className="max-h-64 overflow-y-auto">
                                        {zones.map(zone => (
                                            <button
                                                key={zone.id}
                                                onClick={() => onSelectZone(zone)}
                                                className={`w-full px-4 py-3 text-left hover:bg-orange-50 transition-colors flex justify-between items-center border-b border-gray-100 last:border-0 ${
                                                    selectedZone?.id === zone.id ? 'bg-orange-50' : ''
                                                }`}
                                            >
                                                <div>
                                                    <div className={`font-medium ${selectedZone?.id === zone.id ? 'text-orange-600' : 'text-gray-800'}`}>
                                                        {selectedZone?.id === zone.id && <span className="mr-1">✓</span>}
                                                        {zone.zone_name}
                                                    </div>
                                                    {zone.estimated_time_min && zone.estimated_time_max && (
                                                        <div className="text-xs text-gray-500 mt-0.5">
                                                            {zone.estimated_time_min}-{zone.estimated_time_max} min
                                                        </div>
                                                    )}
                                                </div>
                                                <span className="text-orange-600 font-bold text-sm">
                                                    RM{zone.delivery_fee}
                                                </span>
                                            </button>
                                        ))}
                                    </div>
                                </div>
                            )}
                        </div>
                    </div>
                    
                    {/* Sub info row */}
                    <div className="flex items-center justify-between mt-2 text-xs text-white/80">
                        <span>Min. order: RM{minOrder}</span>
                        <span>{settings?.delivery_hours || '11am-10pm'}</span>
                    </div>
                </div>
            </header>

            {/* ============ STICKY CATEGORY NAVIGATION ============ */}
            {categories.length > 0 && (
                <div className="sticky top-[76px] z-40 bg-white shadow-sm">
                    <div className="max-w-3xl mx-auto">
                        <div className="overflow-x-auto scrollbar-hide">
                            <div className="flex gap-2 p-3 min-w-max">
                                <button
                                    onClick={() => setSelectedCategoryId('all')}
                                    className={`px-4 py-2 rounded-full text-sm font-medium transition-all duration-200 whitespace-nowrap
                                        ${selectedCategoryId === 'all' 
                                            ? 'bg-orange-500 text-white shadow-md' 
                                            : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                                        }`}
                                >
                                    Semua
                                </button>
                                {categories.map(cat => (
                                    <button
                                        key={cat.id}
                                        onClick={() => setSelectedCategoryId(cat.id)}
                                        className={`px-4 py-2 rounded-full text-sm font-medium transition-all duration-200 whitespace-nowrap
                                            ${selectedCategoryId === cat.id 
                                                ? 'bg-orange-500 text-white shadow-md' 
                                                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                                            }`}
                                    >
                                        {cat.name}
                                    </button>
                                ))}
                            </div>
                        </div>
                    </div>
                </div>
            )}

            {/* ============ MAIN CONTENT ============ */}
            <main className={`max-w-3xl mx-auto px-4 py-4 ${cart.length > 0 ? 'pb-28' : 'pb-8'}`}>
                <div ref={menuTopRef} className="scroll-mt-32" />
                
                {/* No Zone Selected Banner */}
                {!selectedZone && (
                    <div className="mb-4 bg-amber-50 border border-amber-200 rounded-xl p-4 flex items-center gap-3">
                        <span className="text-2xl">📍</span>
                        <div className="flex-1">
                            <p className="font-medium text-amber-800">Pilih kawasan delivery anda</p>
                            <p className="text-sm text-amber-600">Tekan butang lokasi di atas untuk memilih</p>
                        </div>
                        <button
                            onClick={() => setIsLocationDropdownOpen(true)}
                            className="bg-amber-500 hover:bg-amber-600 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors"
                        >
                            Pilih
                        </button>
                    </div>
                )}

                {/* ============ MENU ITEMS GRID ============ */}
                <div className="space-y-3">
                    {filteredItems?.map(item => {
                        const inCart = cart.find(c => c.id === item.id);
                        const justAdded = flashItemId === item.id;
                        return (
                            <div 
                                key={item.id} 
                                className={`bg-white rounded-xl overflow-hidden transition-all duration-200 
                                    ${justAdded ? 'ring-2 ring-green-400 shadow-lg shadow-green-100' : 'shadow-sm hover:shadow-md'}`}
                                style={{ borderRadius: '12px' }}
                            >
                                <div className="flex p-3 gap-3">
                                    {/* Item Image */}
                                    {item.image_url ? (
                                        <img 
                                            src={item.image_url} 
                                            alt={item.name} 
                                            className="w-24 h-24 rounded-lg object-cover flex-shrink-0" 
                                            style={{ borderRadius: '10px' }}
                                        />
                                    ) : (
                                        <div 
                                            className="w-24 h-24 rounded-lg bg-gradient-to-br from-orange-100 to-orange-200 flex-shrink-0 flex items-center justify-center"
                                            style={{ borderRadius: '10px' }}
                                        >
                                            <span className="text-3xl">🍽️</span>
                                        </div>
                                    )}
                                    
                                    {/* Item Details */}
                                    <div className="flex-1 min-w-0 flex flex-col">
                                        <h3 className="font-semibold text-gray-900 text-base leading-tight">{item.name}</h3>
                                        {item.description && (
                                            <p className="text-sm text-gray-500 line-clamp-2 mt-1 flex-1">{item.description}</p>
                                        )}
                                        <div className="flex justify-between items-end mt-2">
                                            <span className="font-bold text-orange-600 text-lg">
                                                RM{Number(item.price ?? 0).toFixed(2)}
                                            </span>
                                            {inCart ? (
                                                <div className="flex items-center gap-2 bg-gray-100 rounded-full p-1">
                                                    <button 
                                                        onClick={() => updateQty(item.id, -1)} 
                                                        className="w-8 h-8 bg-white hover:bg-gray-50 rounded-full flex items-center justify-center transition-colors shadow-sm font-bold text-gray-600"
                                                        aria-label={`Kurangkan ${item.name}`}
                                                    >
                                                        −
                                                    </button>
                                                    <span className="font-bold w-6 text-center text-gray-800">{inCart.qty}</span>
                                                    <button 
                                                        onClick={() => addToCart(item)} 
                                                        className="w-8 h-8 bg-orange-500 hover:bg-orange-600 text-white rounded-full flex items-center justify-center transition-colors shadow-sm font-bold"
                                                        aria-label={`Tambah ${item.name}`}
                                                    >
                                                        +
                                                    </button>
                                                </div>
                                            ) : (
                                                <button 
                                                    onClick={() => addToCart(item)} 
                                                    className="bg-orange-500 hover:bg-orange-600 text-white px-5 py-2 rounded-full text-sm font-bold transition-all duration-200 active:scale-95 shadow-sm"
                                                >
                                                    + Add
                                                </button>
                                            )}
                                        </div>
                                    </div>
                                </div>
                            </div>
                        );
                    })}
                </div>

                {filteredItems?.length === 0 && (
                    <div className="text-center py-12 text-gray-500">
                        <span className="text-5xl block mb-3">🍽️</span>
                        <p className="font-medium">Tiada item dalam kategori ini</p>
                    </div>
                )}
            </main>

            {/* ============ STICKY BOTTOM CART BAR ============ */}
            {cart.length > 0 && (
                <div className="fixed bottom-0 left-0 right-0 z-50 animate-slideUp">
                    <div className="max-w-3xl mx-auto px-4 pb-4">
                        <button
                            onClick={() => setIsCartOpen(true)}
                            className="w-full bg-orange-500 hover:bg-orange-600 text-white font-bold py-4 px-5 rounded-2xl transition-all duration-200 active:scale-[0.98] shadow-xl flex items-center justify-between"
                            style={{ 
                                boxShadow: '0 -4px 20px rgba(234, 88, 12, 0.3), 0 4px 20px rgba(0, 0, 0, 0.15)'
                            }}
                        >
                            <div className="flex items-center gap-3">
                                <span className="bg-white text-orange-500 w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold shadow-inner">
                                    {itemCount}
                                </span>
                                <span className="text-base">Lihat Bakul</span>
                            </div>
                            <span className="text-lg">RM{total.toFixed(2)}</span>
                        </button>
                    </div>
                </div>
            )}

            {/* ============ CART DRAWER (BOTTOM SHEET) ============ */}
            {isCartOpen && (
                <div className="fixed inset-0 z-[60]" role="dialog" aria-modal="true">
                    {/* Backdrop */}
                    <button
                        className="absolute inset-0 bg-black/60 animate-fadeIn"
                        onClick={() => setIsCartOpen(false)}
                        aria-label="Tutup bakul"
                    />
                    
                    {/* Drawer */}
                    <div className="absolute left-0 right-0 bottom-0 bg-white rounded-t-3xl shadow-2xl max-h-[90vh] flex flex-col animate-slideUp">
                        {/* Handle */}
                        <div className="flex justify-center pt-3 pb-2 flex-shrink-0">
                            <div className="w-10 h-1 bg-gray-300 rounded-full" />
                        </div>
                        
                        {/* Header */}
                        <div className="flex items-center justify-between px-5 pb-4 border-b flex-shrink-0">
                            <div>
                                <h2 className="text-xl font-bold text-gray-900">Bakul Anda</h2>
                                <p className="text-sm text-gray-500">{itemCount} item</p>
                            </div>
                            <button 
                                onClick={() => setIsCartOpen(false)}
                                className="w-10 h-10 bg-gray-100 hover:bg-gray-200 rounded-full flex items-center justify-center transition-colors"
                            >
                                <svg className="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                                </svg>
                            </button>
                        </div>
                        
                        {/* Scrollable Content */}
                        <div className="flex-1 overflow-y-auto">
                            {/* Cart Items */}
                            <div className="px-5 py-4">
                                {cart.map(item => (
                                    <div key={item.id} className="flex gap-3 items-center py-4 border-b border-gray-100 last:border-0">
                                        <div className="flex-1 min-w-0">
                                            <div className="font-medium text-gray-900">{item.name}</div>
                                            <div className="text-orange-600 font-semibold mt-0.5">
                                                RM{(item.price * item.qty).toFixed(2)}
                                            </div>
                                        </div>
                                        <div className="flex items-center gap-2 bg-gray-100 rounded-full p-1">
                                            <button 
                                                onClick={() => updateQty(item.id, -1)}
                                                className="w-9 h-9 bg-white hover:bg-gray-50 rounded-full font-bold transition-colors shadow-sm flex items-center justify-center"
                                            >
                                                −
                                            </button>
                                            <span className="w-6 text-center font-bold">{item.qty}</span>
                                            <button 
                                                onClick={() => updateQty(item.id, 1)}
                                                className="w-9 h-9 bg-orange-500 hover:bg-orange-600 text-white rounded-full font-bold transition-colors shadow-sm flex items-center justify-center"
                                            >
                                                +
                                            </button>
                                        </div>
                                    </div>
                                ))}
                            </div>

                            {/* Delivery Zone Selection in Cart */}
                            <div className="px-5 py-4 bg-gray-50 border-y">
                                <div className="flex items-center justify-between">
                                    <div className="flex items-center gap-2">
                                        <span className="text-lg">📍</span>
                                        <div>
                                            <p className="text-sm text-gray-600">Delivery ke</p>
                                            <p className="font-semibold text-gray-900">
                                                {selectedZone ? selectedZone.zone_name : 'Belum dipilih'}
                                            </p>
                                        </div>
                                    </div>
                                    <button
                                        onClick={() => {
                                            setIsCartOpen(false);
                                            setTimeout(() => setIsLocationDropdownOpen(true), 200);
                                        }}
                                        className="text-orange-600 font-medium text-sm hover:text-orange-700"
                                    >
                                        Tukar
                                    </button>
                                </div>
                            </div>
                            
                            {/* Summary */}
                            <div className="px-5 py-4 space-y-2">
                                <div className="flex justify-between text-gray-600">
                                    <span>Subtotal</span>
                                    <span>RM{subtotal.toFixed(2)}</span>
                                </div>
                                <div className="flex justify-between text-gray-600">
                                    <span>Delivery Fee</span>
                                    <span>{selectedZone ? `RM${deliveryFee.toFixed(2)}` : '-'}</span>
                                </div>
                                <div className="flex justify-between font-bold text-lg pt-3 border-t border-gray-200">
                                    <span>Total</span>
                                    <span className="text-orange-600">RM{total.toFixed(2)}</span>
                                </div>
                                {subtotal < minOrder && (
                                    <p className="text-red-500 text-sm bg-red-50 px-3 py-2 rounded-lg">
                                        ⚠️ Minimum order: RM{minOrder}. Tambah RM{(minOrder - subtotal).toFixed(2)} lagi.
                                    </p>
                                )}
                            </div>

                            {/* Customer Info Form */}
                            <div className="px-5 py-4 border-t space-y-3">
                                <h4 className="font-bold text-gray-900">Maklumat Penghantaran</h4>
                                <input
                                    type="text"
                                    placeholder="Nama penuh"
                                    value={customerInfo.name}
                                    onChange={e => setCustomerInfo({...customerInfo, name: e.target.value})}
                                    className="w-full p-3.5 border border-gray-200 rounded-xl focus:border-orange-500 focus:ring-2 focus:ring-orange-100 transition-all outline-none text-gray-900"
                                />
                                <input
                                    type="tel"
                                    placeholder="Nombor telefon"
                                    value={customerInfo.phone}
                                    onChange={e => setCustomerInfo({...customerInfo, phone: e.target.value})}
                                    className="w-full p-3.5 border border-gray-200 rounded-xl focus:border-orange-500 focus:ring-2 focus:ring-orange-100 transition-all outline-none text-gray-900"
                                />
                                <textarea
                                    placeholder="Alamat penuh"
                                    value={customerInfo.address}
                                    onChange={e => setCustomerInfo({...customerInfo, address: e.target.value})}
                                    className="w-full p-3.5 border border-gray-200 rounded-xl focus:border-orange-500 focus:ring-2 focus:ring-orange-100 transition-all outline-none resize-none text-gray-900"
                                    rows={2}
                                />
                                <input
                                    type="text"
                                    placeholder="Nota tambahan (optional)"
                                    value={customerInfo.notes}
                                    onChange={e => setCustomerInfo({...customerInfo, notes: e.target.value})}
                                    className="w-full p-3.5 border border-gray-200 rounded-xl focus:border-orange-500 focus:ring-2 focus:ring-orange-100 transition-all outline-none text-gray-900"
                                />
                            </div>
                        </div>

                        {/* Fixed Checkout Button */}
                        <div className="px-5 py-4 border-t bg-white flex-shrink-0">
                            <button
                                onClick={checkout}
                                disabled={subtotal < minOrder || !selectedZone}
                                className="w-full bg-green-500 hover:bg-green-600 disabled:bg-gray-300 disabled:cursor-not-allowed text-white font-bold py-4 rounded-xl transition-all duration-200 active:scale-[0.98] flex items-center justify-center gap-2 text-lg shadow-lg"
                            >
                                <svg className="w-6 h-6" fill="currentColor" viewBox="0 0 24 24">
                                    <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z"/>
                                </svg>
                                Pesan via WhatsApp
                            </button>
                            {!selectedZone && (
                                <p className="text-center text-amber-600 text-sm mt-2">
                                    Sila pilih kawasan delivery dahulu
                                </p>
                            )}
                        </div>
                    </div>
                </div>
            )}

            {/* ============ CSS ANIMATIONS ============ */}
            <style jsx global>{`
                @keyframes fadeIn {
                    from { opacity: 0; }
                    to { opacity: 1; }
                }
                
                @keyframes slideUp {
                    from { transform: translateY(100%); }
                    to { transform: translateY(0); }
                }
                
                .animate-fadeIn {
                    animation: fadeIn 0.2s ease-out;
                }
                
                .animate-slideUp {
                    animation: slideUp 0.3s cubic-bezier(0.32, 0.72, 0, 1);
                }
                
                .scrollbar-hide {
                    -ms-overflow-style: none;
                    scrollbar-width: none;
                }
                
                .scrollbar-hide::-webkit-scrollbar {
                    display: none;
                }
                
                .line-clamp-2 {
                    display: -webkit-box;
                    -webkit-line-clamp: 2;
                    -webkit-box-orient: vertical;
                    overflow: hidden;
                }
                
                /* Smooth transitions for all interactive elements */
                button, a {
                    -webkit-tap-highlight-color: transparent;
                }
                
                /* Better mobile scrolling */
                * {
                    -webkit-overflow-scrolling: touch;
                }
            `}</style>
        </div>
    );
}
