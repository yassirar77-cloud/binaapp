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
    const [flashItemId, setFlashItemId] = useState<string | null>(null);
    const menuTopRef = useRef<HTMLDivElement | null>(null);

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
                requestAnimationFrame(() => {
                    menuTopRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
                });
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

    function onSelectZone(zone: DeliveryZone) {
        setSelectedZone(zone);
        setIsCartOpen(false);
        if (typeof window !== 'undefined') {
            try {
                window.localStorage.setItem(storageKey, JSON.stringify(zone));
            } catch {
                // ignore
            }
        }
        requestAnimationFrame(() => {
            menuTopRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
        });
    }

    function clearZone() {
        setSelectedZone(null);
        if (typeof window !== 'undefined') {
            try {
                window.localStorage.removeItem(storageKey);
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
        <div className="min-h-screen bg-gray-50">
            {/* Header */}
            <header className="bg-gradient-to-r from-orange-500 to-red-500 text-white py-4 px-4 sticky top-0 z-40 shadow-lg">
                <div className="max-w-6xl mx-auto">
                    <h1 className="text-xl md:text-2xl font-bold flex items-center gap-2">
                        <span className="text-2xl">🛵</span> Pesan Delivery
                    </h1>
                    <p className="text-white/80 text-xs md:text-sm mt-1">
                        Min. order: RM{minOrder} • {settings?.delivery_hours || '11am-10pm'}
                    </p>
                </div>
            </header>

            {/* Main Content - Responsive Layout */}
            <div className={`max-w-6xl mx-auto p-4 ${cart.length > 0 ? 'pb-28 lg:pb-8' : 'pb-8'}`}>
                {/* Zone Selection - Always visible when no zone selected */}
                {!selectedZone && (
                    <section className="bg-white rounded-2xl p-4 md:p-6 shadow-sm mb-4">
                        <h2 className="text-lg md:text-xl font-bold mb-4 flex items-center gap-2">
                            <span>📍</span> Pilih Kawasan Delivery
                        </h2>
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                            {zones.map(zone => (
                                <button
                                    key={zone.id}
                                    onClick={() => onSelectZone(zone)}
                                    className="p-4 border-2 border-gray-200 rounded-xl text-left hover:border-orange-500 hover:bg-orange-50 transition-all duration-200 active:scale-[0.98]"
                                >
                                    <div className="flex justify-between items-start">
                                        <div>
                                            <div className="font-semibold text-gray-800">{zone.zone_name}</div>
                                            {zone.estimated_time_min && zone.estimated_time_max && (
                                                <div className="text-sm text-gray-500 mt-1">
                                                    🕐 {zone.estimated_time_min}-{zone.estimated_time_max} min
                                                </div>
                                            )}
                                        </div>
                                        <div className="text-orange-600 font-bold text-lg">
                                            RM{zone.delivery_fee}
                                        </div>
                                    </div>
                                </button>
                            ))}
                        </div>
                    </section>
                )}

                {/* Two-column layout for desktop when zone is selected */}
                {selectedZone && (
                    <div className="lg:flex lg:gap-6">
                        {/* Left Column - Menu (Mobile: full width, Desktop: 70%) */}
                        <div className="lg:w-[70%]">
                            {/* Selected Zone Display */}
                            <section className="bg-white rounded-2xl p-4 md:p-6 shadow-sm mb-4">
                                <div className="flex items-center justify-between flex-wrap gap-2">
                                    <div className="flex items-center gap-2">
                                        <span className="text-green-600 text-xl">✅</span>
                                        <div>
                                            <span className="font-semibold text-green-800">Kawasan dipilih:</span>
                                            <span className="ml-2 text-green-700 font-bold">{selectedZone.zone_name}</span>
                                        </div>
                                    </div>
                                    <div className="flex items-center gap-3">
                                        <span className="text-sm text-green-600">RM{selectedZone.delivery_fee} delivery</span>
                                        <button 
                                            onClick={clearZone}
                                            className="text-sm text-orange-600 hover:text-orange-700 underline transition-colors"
                                        >
                                            Tukar
                                        </button>
                                    </div>
                                </div>
                            </section>

                            {/* Menu Section */}
                            <section className="bg-white rounded-2xl p-4 md:p-6 shadow-sm mb-4">
                                <div ref={menuTopRef} className="scroll-mt-28" />
                                <h2 className="text-lg md:text-xl font-bold mb-4 flex items-center gap-2">
                                    <span>🍽️</span> Menu
                                </h2>

                                {/* Category Filter */}
                                {categories.length > 0 && (
                                    <div className="mb-4 overflow-x-auto pb-2 -mx-4 px-4 scrollbar-hide">
                                        <div className="flex gap-2 min-w-max">
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
                                )}

                                {/* Menu Items Grid */}
                                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 md:gap-4">
                                    {filteredItems?.map(item => {
                                        const inCart = cart.find(c => c.id === item.id);
                                        const justAdded = flashItemId === item.id;
                                        return (
                                            <div 
                                                key={item.id} 
                                                className={`flex gap-3 p-3 bg-gray-50 rounded-xl transition-all duration-200 
                                                    ${justAdded ? 'ring-2 ring-green-400 bg-green-50' : 'hover:bg-gray-100'}`}
                                            >
                                                {item.image_url ? (
                                                    <img 
                                                        src={item.image_url} 
                                                        alt={item.name} 
                                                        className="w-20 h-20 md:w-24 md:h-24 rounded-lg object-cover flex-shrink-0" 
                                                    />
                                                ) : (
                                                    <div className="w-20 h-20 md:w-24 md:h-24 rounded-lg bg-gradient-to-br from-orange-100 to-red-100 flex-shrink-0" />
                                                )}
                                                <div className="flex-1 min-w-0">
                                                    <h3 className="font-semibold text-gray-800 text-sm md:text-base truncate">{item.name}</h3>
                                                    {item.description && (
                                                        <p className="text-xs md:text-sm text-gray-500 line-clamp-2 mt-0.5">{item.description}</p>
                                                    )}
                                                    <div className="flex justify-between items-center mt-2">
                                                        <span className="font-bold text-orange-600">RM{Number(item.price ?? 0).toFixed(2)}</span>
                                                        {inCart ? (
                                                            <div className="flex items-center gap-1.5">
                                                                <button 
                                                                    onClick={() => updateQty(item.id, -1)} 
                                                                    className="w-8 h-8 bg-gray-200 hover:bg-gray-300 rounded-full flex items-center justify-center transition-colors active:scale-95 font-bold"
                                                                    aria-label={`Kurangkan ${item.name}`}
                                                                >
                                                                    −
                                                                </button>
                                                                <span className="font-bold w-6 text-center">{inCart.qty}</span>
                                                                <button 
                                                                    onClick={() => addToCart(item)} 
                                                                    className="w-8 h-8 bg-orange-500 hover:bg-orange-600 text-white rounded-full flex items-center justify-center transition-colors active:scale-95 font-bold"
                                                                    aria-label={`Tambah ${item.name}`}
                                                                >
                                                                    +
                                                                </button>
                                                            </div>
                                                        ) : (
                                                            <button 
                                                                onClick={() => addToCart(item)} 
                                                                className="bg-orange-500 hover:bg-orange-600 text-white px-3 py-1.5 rounded-full text-sm font-medium transition-all duration-200 active:scale-95 flex items-center gap-1"
                                                            >
                                                                <span className="text-lg leading-none">+</span> Tambah
                                                            </button>
                                                        )}
                                                    </div>
                                                </div>
                                            </div>
                                        );
                                    })}
                                </div>

                                {filteredItems?.length === 0 && (
                                    <div className="text-center py-8 text-gray-500">
                                        Tiada item dalam kategori ini
                                    </div>
                                )}
                            </section>
                        </div>

                        {/* Right Column - Desktop Cart Sidebar (Hidden on Mobile) */}
                        <aside className="hidden lg:block lg:w-[30%] lg:max-w-[320px]">
                            <div className="sticky top-24">
                                <div className="bg-white rounded-2xl shadow-sm overflow-hidden border border-gray-100">
                                    <div className="p-4 bg-gradient-to-r from-orange-500 to-red-500 text-white">
                                        <div className="flex items-center justify-between">
                                            <h2 className="text-lg font-bold flex items-center gap-2">
                                                <span>🛒</span> Bakul Pesanan
                                            </h2>
                                            <span className="text-sm opacity-80">{itemCount} item</span>
                                        </div>
                                    </div>
                                    
                                    <div className="p-4 max-h-[40vh] overflow-y-auto">
                                        {cart.length === 0 ? (
                                            <div className="text-center py-8 text-gray-400">
                                                <div className="text-4xl mb-2">🛒</div>
                                                <p>Bakul kosong</p>
                                                <p className="text-sm">Tambah item dari menu</p>
                                            </div>
                                        ) : (
                                            <div className="space-y-3">
                                                {cart.map(item => (
                                                    <div key={item.id} className="flex gap-3 items-start pb-3 border-b border-gray-100 last:border-0">
                                                        <div className="flex-1 min-w-0">
                                                            <div className="font-medium text-sm truncate">{item.name}</div>
                                                            <div className="text-orange-600 text-sm">RM{(item.price * item.qty).toFixed(2)}</div>
                                                        </div>
                                                        <div className="flex items-center gap-1">
                                                            <button 
                                                                onClick={() => updateQty(item.id, -1)}
                                                                className="w-6 h-6 bg-gray-100 hover:bg-gray-200 rounded-full text-sm font-bold transition-colors"
                                                                aria-label={`Kurangkan ${item.name}`}
                                                            >
                                                                −
                                                            </button>
                                                            <span className="w-5 text-center text-sm font-medium">{item.qty}</span>
                                                            <button 
                                                                onClick={() => updateQty(item.id, 1)}
                                                                className="w-6 h-6 bg-orange-100 hover:bg-orange-200 text-orange-600 rounded-full text-sm font-bold transition-colors"
                                                                aria-label={`Tambah ${item.name}`}
                                                            >
                                                                +
                                                            </button>
                                                        </div>
                                                    </div>
                                                ))}
                                            </div>
                                        )}
                                    </div>

                                    {cart.length > 0 && (
                                        <>
                                            {/* Order Summary */}
                                            <div className="p-4 bg-gray-50 border-t space-y-2 text-sm">
                                                <div className="flex justify-between text-gray-600">
                                                    <span>Subtotal</span>
                                                    <span>RM{subtotal.toFixed(2)}</span>
                                                </div>
                                                <div className="flex justify-between text-gray-600">
                                                    <span>Delivery</span>
                                                    <span>RM{deliveryFee.toFixed(2)}</span>
                                                </div>
                                                <div className="flex justify-between font-bold text-base pt-2 border-t border-gray-200">
                                                    <span>Jumlah</span>
                                                    <span className="text-orange-600">RM{total.toFixed(2)}</span>
                                                </div>
                                                {subtotal < minOrder && (
                                                    <p className="text-red-500 text-xs mt-1">
                                                        ⚠️ Minimum order: RM{minOrder}
                                                    </p>
                                                )}
                                            </div>

                                            {/* Checkout Form - Desktop */}
                                            <div className="p-4 border-t space-y-3">
                                                <h3 className="font-semibold text-sm text-gray-700">📝 Maklumat Penghantaran</h3>
                                                <input
                                                    type="text"
                                                    placeholder="Nama penuh"
                                                    value={customerInfo.name}
                                                    onChange={e => setCustomerInfo({...customerInfo, name: e.target.value})}
                                                    className="w-full p-2.5 text-sm border border-gray-200 rounded-lg focus:border-orange-500 focus:ring-1 focus:ring-orange-200 transition-all outline-none"
                                                />
                                                <input
                                                    type="tel"
                                                    placeholder="Nombor telefon"
                                                    value={customerInfo.phone}
                                                    onChange={e => setCustomerInfo({...customerInfo, phone: e.target.value})}
                                                    className="w-full p-2.5 text-sm border border-gray-200 rounded-lg focus:border-orange-500 focus:ring-1 focus:ring-orange-200 transition-all outline-none"
                                                />
                                                <textarea
                                                    placeholder="Alamat penuh"
                                                    value={customerInfo.address}
                                                    onChange={e => setCustomerInfo({...customerInfo, address: e.target.value})}
                                                    className="w-full p-2.5 text-sm border border-gray-200 rounded-lg focus:border-orange-500 focus:ring-1 focus:ring-orange-200 transition-all outline-none resize-none"
                                                    rows={2}
                                                />
                                                <input
                                                    type="text"
                                                    placeholder="Nota (optional)"
                                                    value={customerInfo.notes}
                                                    onChange={e => setCustomerInfo({...customerInfo, notes: e.target.value})}
                                                    className="w-full p-2.5 text-sm border border-gray-200 rounded-lg focus:border-orange-500 focus:ring-1 focus:ring-orange-200 transition-all outline-none"
                                                />
                                                <button
                                                    onClick={checkout}
                                                    disabled={subtotal < minOrder}
                                                    className="w-full bg-green-600 hover:bg-green-700 disabled:bg-gray-300 disabled:cursor-not-allowed text-white font-bold py-3 rounded-xl transition-all duration-200 active:scale-[0.98] flex items-center justify-center gap-2"
                                                >
                                                    <span>📱</span> WhatsApp Pesanan
                                                </button>
                                            </div>
                                        </>
                                    )}
                                </div>
                            </div>
                        </aside>
                    </div>
                )}
            </div>

            {/* MOBILE: Sticky bottom cart bar (only when items exist) */}
            {cart.length > 0 && (
                <div className="fixed bottom-0 left-0 right-0 bg-white border-t border-gray-200 shadow-2xl p-3 z-50 lg:hidden">
                    <button
                        onClick={() => setIsCartOpen(true)}
                        className="w-full bg-orange-500 hover:bg-orange-600 text-white font-bold py-3.5 px-4 rounded-xl transition-all duration-200 active:scale-[0.98] flex items-center justify-between"
                        aria-label="Buka bakul pesanan"
                    >
                        <div className="flex items-center gap-2">
                            <span className="bg-white text-orange-500 w-6 h-6 rounded-full flex items-center justify-center text-sm font-bold">
                                {itemCount}
                            </span>
                            <span>Lihat Bakul</span>
                        </div>
                        <span className="font-bold">RM{total.toFixed(2)}</span>
                    </button>
                </div>
            )}

            {/* MOBILE: Bottom drawer cart */}
            {isCartOpen && (
                <div className="fixed inset-0 z-[60] lg:hidden" role="dialog" aria-modal="true">
                    <button
                        className="absolute inset-0 bg-black/50 animate-fadeIn"
                        onClick={() => setIsCartOpen(false)}
                        aria-label="Tutup bakul"
                    />
                    <div className="absolute left-0 right-0 bottom-0 bg-white rounded-t-3xl shadow-2xl max-h-[85vh] overflow-hidden animate-slideUp">
                        {/* Handle */}
                        <div className="flex justify-center pt-3 pb-2">
                            <div className="w-12 h-1.5 bg-gray-300 rounded-full" />
                        </div>
                        
                        {/* Header */}
                        <div className="flex items-center justify-between px-4 pb-3 border-b">
                            <div>
                                <h2 className="text-lg font-bold flex items-center gap-2">
                                    <span>🛒</span> Bakul Pesanan
                                </h2>
                                {selectedZone?.zone_name && (
                                    <div className="text-sm text-green-700">✅ Kawasan: {selectedZone.zone_name}</div>
                                )}
                            </div>
                            <button 
                                onClick={() => setIsCartOpen(false)}
                                className="px-3 py-2 text-gray-600 hover:bg-gray-100 rounded-full transition-colors"
                            >
                                Tutup
                            </button>
                        </div>
                        
                        {/* Cart Items */}
                        <div className="px-4 py-3 max-h-[35vh] overflow-y-auto">
                            {cart.map(item => (
                                <div key={item.id} className="flex gap-3 items-center py-3 border-b border-gray-100 last:border-0">
                                    <div className="flex-1 min-w-0">
                                        <div className="font-medium truncate">{item.name}</div>
                                        <div className="text-orange-600 text-sm">RM{(item.price * item.qty).toFixed(2)}</div>
                                    </div>
                                    <div className="flex items-center gap-2">
                                        <button 
                                            onClick={() => updateQty(item.id, -1)}
                                            className="w-9 h-9 bg-gray-100 hover:bg-gray-200 rounded-full font-bold transition-colors"
                                            aria-label={`Kurangkan ${item.name}`}
                                        >
                                            −
                                        </button>
                                        <span className="w-6 text-center font-medium">{item.qty}</span>
                                        <button 
                                            onClick={() => updateQty(item.id, 1)}
                                            className="w-9 h-9 bg-orange-500 hover:bg-orange-600 text-white rounded-full font-bold transition-colors"
                                            aria-label={`Tambah ${item.name}`}
                                        >
                                            +
                                        </button>
                                    </div>
                                </div>
                            ))}
                        </div>
                        
                        {/* Summary & Checkout */}
                        <div className="px-4 py-4 bg-gray-50 border-t space-y-3 max-h-[45vh] overflow-y-auto">
                            <div className="flex justify-between text-gray-600">
                                <span>Subtotal</span>
                                <span>RM{subtotal.toFixed(2)}</span>
                            </div>
                            <div className="flex justify-between text-gray-600">
                                <span>Delivery</span>
                                <span>RM{deliveryFee.toFixed(2)}</span>
                            </div>
                            <div className="flex justify-between font-bold text-lg pt-2 border-t border-gray-200">
                                <span>Jumlah</span>
                                <span className="text-orange-600">RM{total.toFixed(2)}</span>
                            </div>
                            {subtotal < minOrder && (
                                <p className="text-red-500 text-sm">⚠️ Minimum order: RM{minOrder}</p>
                            )}
                            {!selectedZone && (
                                <p className="text-amber-600 text-sm">⚠️ Sila pilih kawasan delivery dahulu</p>
                            )}

                            {/* Customer Info */}
                            <div className="pt-3 border-t border-gray-200 space-y-3">
                                <h4 className="font-bold text-sm">📝 Maklumat Penghantaran</h4>
                                <input
                                    type="text"
                                    placeholder="Nama penuh"
                                    value={customerInfo.name}
                                    onChange={e => setCustomerInfo({...customerInfo, name: e.target.value})}
                                    className="w-full p-3 border border-gray-200 rounded-xl focus:border-orange-500 focus:ring-2 focus:ring-orange-200 transition-all outline-none"
                                />
                                <input
                                    type="tel"
                                    placeholder="Nombor telefon"
                                    value={customerInfo.phone}
                                    onChange={e => setCustomerInfo({...customerInfo, phone: e.target.value})}
                                    className="w-full p-3 border border-gray-200 rounded-xl focus:border-orange-500 focus:ring-2 focus:ring-orange-200 transition-all outline-none"
                                />
                                <textarea
                                    placeholder="Alamat penuh"
                                    value={customerInfo.address}
                                    onChange={e => setCustomerInfo({...customerInfo, address: e.target.value})}
                                    className="w-full p-3 border border-gray-200 rounded-xl focus:border-orange-500 focus:ring-2 focus:ring-orange-200 transition-all outline-none resize-none"
                                    rows={2}
                                />
                                <input
                                    type="text"
                                    placeholder="Nota tambahan (optional)"
                                    value={customerInfo.notes}
                                    onChange={e => setCustomerInfo({...customerInfo, notes: e.target.value})}
                                    className="w-full p-3 border border-gray-200 rounded-xl focus:border-orange-500 focus:ring-2 focus:ring-orange-200 transition-all outline-none"
                                />
                            </div>

                            <button
                                onClick={checkout}
                                disabled={subtotal < minOrder || !selectedZone}
                                className="w-full bg-green-600 hover:bg-green-700 disabled:bg-gray-300 disabled:cursor-not-allowed text-white font-bold py-4 rounded-xl transition-all duration-200 active:scale-[0.98] flex items-center justify-center gap-2"
                            >
                                <span>📱</span> WhatsApp Pesanan
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* CSS Animations */}
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
                    animation: slideUp 0.3s ease-out;
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
            `}</style>
        </div>
    );
}
