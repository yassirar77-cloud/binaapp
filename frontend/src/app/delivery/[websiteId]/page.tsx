'use client';
import { useState, useEffect, useRef, useCallback } from 'react';
import { useParams } from 'next/navigation';

const API_URL = 'https://binaapp-backend.onrender.com';

// Types
interface CartItem {
    id: string;
    name: string;
    price: number;
    qty: number;
    image_url?: string;
}

interface Zone {
    id: string;
    zone_name: string;
    delivery_fee: number;
    estimated_time_min?: number;
    estimated_time_max?: number;
}

interface MenuItem {
    id: string;
    name: string;
    description?: string;
    price: number;
    image_url?: string;
    category?: string;
}

interface Settings {
    minimum_order?: number;
    delivery_hours?: string;
    whatsapp_number?: string;
}

export default function DeliveryPage() {
    const { websiteId } = useParams();
    const [loading, setLoading] = useState(true);
    const [menu, setMenu] = useState<{ categories: string[]; items: MenuItem[] }>({ categories: [], items: [] });
    const [zones, setZones] = useState<Zone[]>([]);
    const [settings, setSettings] = useState<Settings | null>(null);
    const [cart, setCart] = useState<CartItem[]>([]);
    const [selectedZone, setSelectedZone] = useState<Zone | null>(null);
    const [customerInfo, setCustomerInfo] = useState({ name: '', phone: '', address: '', notes: '' });
    const [selectedCategory, setSelectedCategory] = useState<string>('all');
    const [isCartDrawerOpen, setIsCartDrawerOpen] = useState(false);
    const [addedItemId, setAddedItemId] = useState<string | null>(null);
    const menuRef = useRef<HTMLDivElement>(null);

    // Load zone from localStorage on mount
    useEffect(() => {
        const savedZoneId = localStorage.getItem(`delivery_zone_${websiteId}`);
        if (savedZoneId && zones.length > 0) {
            const savedZone = zones.find(z => z.id === savedZoneId);
            if (savedZone) {
                setSelectedZone(savedZone);
            }
        }
    }, [zones, websiteId]);

    // Save zone to localStorage when changed
    useEffect(() => {
        if (selectedZone) {
            localStorage.setItem(`delivery_zone_${websiteId}`, selectedZone.id);
        }
    }, [selectedZone, websiteId]);

    useEffect(() => {
        loadData();
    }, [websiteId]);

    async function loadData() {
        try {
            const [menuRes, zonesRes] = await Promise.all([
                fetch(`${API_URL}/v1/delivery/menu/${websiteId}`),
                fetch(`${API_URL}/v1/delivery/zones/${websiteId}`)
            ]);
            const menuData = await menuRes.json();
            const zonesData = await zonesRes.json();
            
            // Extract unique categories from items
            const categories = [...new Set(menuData.items?.map((item: MenuItem) => item.category).filter(Boolean))] as string[];
            
            setMenu({ categories, items: menuData.items || [] });
            setZones(zonesData.zones || []);
            setSettings(zonesData.settings || {});
        } catch (err) {
            console.error('Failed to load:', err);
        }
        setLoading(false);
    }

    const addToCart = useCallback((item: MenuItem) => {
        setCart(prevCart => {
            const existing = prevCart.find(c => c.id === item.id);
            if (existing) {
                return prevCart.map(c => c.id === item.id ? { ...c, qty: c.qty + 1 } : c);
            } else {
                return [...prevCart, { ...item, qty: 1 }];
            }
        });
        
        // Visual feedback
        setAddedItemId(item.id);
        setTimeout(() => setAddedItemId(null), 600);
    }, []);

    const updateQty = useCallback((id: string, delta: number) => {
        setCart(prevCart => prevCart.map(c => {
            if (c.id === id) {
                const newQty = c.qty + delta;
                return newQty > 0 ? { ...c, qty: newQty } : null;
            }
            return c;
        }).filter(Boolean) as CartItem[]);
    }, []);

    const removeFromCart = useCallback((id: string) => {
        setCart(prevCart => prevCart.filter(c => c.id !== id));
    }, []);

    const handleZoneSelect = useCallback((zone: Zone) => {
        setSelectedZone(zone);
        // Auto-scroll to menu after selection
        setTimeout(() => {
            menuRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }, 100);
    }, []);

    const subtotal = cart.reduce((sum, item) => sum + (item.price * item.qty), 0);
    const deliveryFee = selectedZone?.delivery_fee || 0;
    const total = subtotal + deliveryFee;
    const minOrder = settings?.minimum_order || 0;
    const cartItemCount = cart.reduce((sum, i) => sum + i.qty, 0);

    // Filter items by category
    const filteredItems = selectedCategory === 'all' 
        ? menu.items 
        : menu.items.filter(item => item.category === selectedCategory);

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
            {/* Header - Responsive */}
            <header className="bg-gradient-to-r from-orange-500 to-red-500 text-white py-4 md:py-6 px-4 sticky top-0 z-40 shadow-lg">
                <div className="max-w-7xl mx-auto">
                    <div className="flex items-center justify-between">
                        <div>
                            <h1 className="text-xl md:text-2xl font-bold flex items-center gap-2">
                                <span>🛵</span> Pesan Delivery
                            </h1>
                            <p className="text-white/80 text-xs md:text-sm mt-1">
                                Min. order: RM{minOrder} • {settings?.delivery_hours || '11am-10pm'}
                            </p>
                        </div>
                        {/* Desktop cart indicator */}
                        <div className="hidden lg:flex items-center gap-2 bg-white/20 px-4 py-2 rounded-full">
                            <span>🛒</span>
                            <span className="font-semibold">{cartItemCount} item</span>
                        </div>
                    </div>
                </div>
            </header>

            {/* Main Content - Two Column on Desktop */}
            <div className="max-w-7xl mx-auto px-4 py-4 md:py-6">
                <div className="lg:flex lg:gap-6">
                    {/* Left Column - Menu (70% on desktop) */}
                    <div className="lg:w-[70%] space-y-4 md:space-y-6">
                        
                        {/* Area Selection */}
                        <section className="bg-white rounded-2xl p-4 md:p-6 shadow-sm">
                            <h2 className="text-lg md:text-xl font-bold mb-4 flex items-center gap-2">
                                <span className="text-2xl">📍</span> Pilih Kawasan Delivery
                            </h2>
                            
                            {/* Selected Zone Display */}
                            {selectedZone && (
                                <div className="mb-4 p-3 md:p-4 bg-green-50 border-2 border-green-200 rounded-xl animate-fade-in">
                                    <div className="flex items-center justify-between">
                                        <div className="flex items-center gap-2">
                                            <span className="text-green-600 text-xl">✅</span>
                                            <div>
                                                <p className="font-semibold text-green-800">Kawasan dipilih:</p>
                                                <p className="text-green-700 text-lg">{selectedZone.zone_name}</p>
                                            </div>
                                        </div>
                                        <div className="text-right">
                                            <p className="text-sm text-green-600">Delivery</p>
                                            <p className="font-bold text-green-700">RM{selectedZone.delivery_fee.toFixed(2)}</p>
                                        </div>
                                    </div>
                                </div>
                            )}

                            {/* Zone Grid */}
                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                                {zones.map(zone => (
                                    <button
                                        key={zone.id}
                                        onClick={() => handleZoneSelect(zone)}
                                        className={`p-4 border-2 rounded-xl text-left transition-all duration-200 transform hover:scale-[1.02] active:scale-[0.98] ${
                                            selectedZone?.id === zone.id
                                                ? 'border-orange-500 bg-orange-50 shadow-md'
                                                : 'border-gray-200 hover:border-orange-300 hover:bg-orange-50/50'
                                        }`}
                                    >
                                        <div className="flex justify-between items-center">
                                            <div>
                                                <div className="font-semibold text-gray-800">{zone.zone_name}</div>
                                                {zone.estimated_time_min && (
                                                    <div className="text-sm text-gray-500 mt-1">
                                                        🕐 {zone.estimated_time_min}-{zone.estimated_time_max} min
                                                    </div>
                                                )}
                                            </div>
                                            <div className="text-orange-600 font-bold text-lg">
                                                RM{zone.delivery_fee.toFixed(2)}
                                            </div>
                                        </div>
                                    </button>
                                ))}
                            </div>
                        </section>

                        {/* Menu Section */}
                        <section ref={menuRef} className="bg-white rounded-2xl p-4 md:p-6 shadow-sm">
                            <h2 className="text-lg md:text-xl font-bold mb-4 flex items-center gap-2">
                                <span className="text-2xl">🍽️</span> Menu
                            </h2>

                            {/* Category Filter - Horizontal Scroll on Mobile */}
                            {menu.categories.length > 0 && (
                                <div className="mb-4 -mx-4 px-4 md:mx-0 md:px-0">
                                    <div className="flex gap-2 overflow-x-auto pb-2 scrollbar-hide">
                                        <button
                                            onClick={() => setSelectedCategory('all')}
                                            className={`px-4 py-2 rounded-full text-sm font-medium whitespace-nowrap transition-all ${
                                                selectedCategory === 'all'
                                                    ? 'bg-orange-500 text-white shadow-md'
                                                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                                            }`}
                                        >
                                            Semua
                                        </button>
                                        {menu.categories.map(cat => (
                                            <button
                                                key={cat}
                                                onClick={() => setSelectedCategory(cat)}
                                                className={`px-4 py-2 rounded-full text-sm font-medium whitespace-nowrap transition-all ${
                                                    selectedCategory === cat
                                                        ? 'bg-orange-500 text-white shadow-md'
                                                        : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                                                }`}
                                            >
                                                {cat}
                                            </button>
                                        ))}
                                    </div>
                                </div>
                            )}

                            {/* Food Cards Grid - Responsive */}
                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 md:gap-4">
                                {filteredItems.map(item => {
                                    const inCart = cart.find(c => c.id === item.id);
                                    const justAdded = addedItemId === item.id;
                                    
                                    return (
                                        <div 
                                            key={item.id} 
                                            className={`bg-gray-50 rounded-xl overflow-hidden transition-all duration-300 ${
                                                justAdded ? 'ring-2 ring-green-500 scale-[1.02]' : ''
                                            }`}
                                        >
                                            <div className="flex gap-3 p-3">
                                                {/* Image */}
                                                {item.image_url ? (
                                                    <img 
                                                        src={item.image_url} 
                                                        alt={item.name} 
                                                        className="w-20 h-20 md:w-24 md:h-24 rounded-lg object-cover flex-shrink-0"
                                                    />
                                                ) : (
                                                    <div className="w-20 h-20 md:w-24 md:h-24 rounded-lg bg-gray-200 flex items-center justify-center flex-shrink-0">
                                                        <span className="text-3xl">🍽️</span>
                                                    </div>
                                                )}
                                                
                                                {/* Content */}
                                                <div className="flex-1 min-w-0">
                                                    <h3 className="font-semibold text-gray-800 text-sm md:text-base truncate">
                                                        {item.name}
                                                    </h3>
                                                    {item.description && (
                                                        <p className="text-xs md:text-sm text-gray-500 line-clamp-2 mt-1">
                                                            {item.description}
                                                        </p>
                                                    )}
                                                    
                                                    <div className="flex justify-between items-center mt-2 md:mt-3">
                                                        <span className="font-bold text-orange-600 text-base md:text-lg">
                                                            RM{item.price?.toFixed(2)}
                                                        </span>
                                                        
                                                        {/* Add/Qty Controls */}
                                                        {inCart ? (
                                                            <div className="flex items-center gap-1 md:gap-2">
                                                                <button 
                                                                    onClick={() => updateQty(item.id, -1)}
                                                                    className="w-8 h-8 bg-gray-200 hover:bg-gray-300 rounded-full flex items-center justify-center font-bold text-gray-700 transition-colors active:scale-95"
                                                                >
                                                                    -
                                                                </button>
                                                                <span className="w-6 text-center font-bold">{inCart.qty}</span>
                                                                <button 
                                                                    onClick={() => addToCart(item)}
                                                                    className="w-8 h-8 bg-orange-500 hover:bg-orange-600 text-white rounded-full flex items-center justify-center font-bold transition-colors active:scale-95"
                                                                >
                                                                    +
                                                                </button>
                                                            </div>
                                                        ) : (
                                                            <button 
                                                                onClick={() => addToCart(item)}
                                                                className="px-3 md:px-4 py-1.5 md:py-2 bg-orange-500 hover:bg-orange-600 text-white rounded-full text-sm font-semibold transition-all active:scale-95 flex items-center gap-1"
                                                            >
                                                                <span className="text-lg">+</span> Tambah
                                                            </button>
                                                        )}
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                    );
                                })}
                            </div>

                            {filteredItems.length === 0 && (
                                <div className="text-center py-8 text-gray-500">
                                    <span className="text-4xl">🍽️</span>
                                    <p className="mt-2">Tiada item dalam kategori ini</p>
                                </div>
                            )}
                        </section>

                        {/* Customer Info Section - Always Visible */}
                        <section className="bg-white rounded-2xl p-4 md:p-6 shadow-sm">
                            <h2 className="text-lg md:text-xl font-bold mb-4 flex items-center gap-2">
                                <span className="text-2xl">📝</span> Maklumat Penghantaran
                            </h2>
                            <div className="space-y-3 md:space-y-4">
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-1">Nama penuh *</label>
                                    <input
                                        type="text"
                                        placeholder="Masukkan nama"
                                        value={customerInfo.name}
                                        onChange={e => setCustomerInfo({ ...customerInfo, name: e.target.value })}
                                        className="w-full p-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-orange-500 focus:border-orange-500 transition-all"
                                    />
                                </div>
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-1">Nombor telefon *</label>
                                    <input
                                        type="tel"
                                        placeholder="Cth: 0123456789"
                                        value={customerInfo.phone}
                                        onChange={e => setCustomerInfo({ ...customerInfo, phone: e.target.value })}
                                        className="w-full p-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-orange-500 focus:border-orange-500 transition-all"
                                    />
                                </div>
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-1">Alamat penuh *</label>
                                    <textarea
                                        placeholder="Masukkan alamat lengkap"
                                        value={customerInfo.address}
                                        onChange={e => setCustomerInfo({ ...customerInfo, address: e.target.value })}
                                        className="w-full p-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-orange-500 focus:border-orange-500 transition-all resize-none"
                                        rows={2}
                                    />
                                </div>
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-1">Nota tambahan</label>
                                    <input
                                        type="text"
                                        placeholder="Cth: Tingkat 2, Unit A"
                                        value={customerInfo.notes}
                                        onChange={e => setCustomerInfo({ ...customerInfo, notes: e.target.value })}
                                        className="w-full p-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-orange-500 focus:border-orange-500 transition-all"
                                    />
                                </div>
                            </div>
                        </section>

                        {/* Spacer for mobile bottom bar */}
                        <div className="h-24 lg:hidden"></div>
                    </div>

                    {/* Right Column - Desktop Cart Sidebar (30%) */}
                    <aside className="hidden lg:block lg:w-[30%]">
                        <div className="sticky top-24 max-w-[320px] ml-auto">
                            <div className="bg-white rounded-2xl shadow-sm overflow-hidden">
                                <div className="bg-gradient-to-r from-orange-500 to-red-500 p-4 text-white">
                                    <h3 className="font-bold text-lg flex items-center gap-2">
                                        <span>🛒</span> Bakul Pesanan
                                    </h3>
                                    <p className="text-white/80 text-sm">{cartItemCount} item</p>
                                </div>

                                <div className="p-4 max-h-[400px] overflow-y-auto">
                                    {cart.length === 0 ? (
                                        <div className="text-center py-8 text-gray-400">
                                            <span className="text-4xl">🛒</span>
                                            <p className="mt-2">Bakul kosong</p>
                                            <p className="text-sm">Tambah item dari menu</p>
                                        </div>
                                    ) : (
                                        <div className="space-y-3">
                                            {cart.map(item => (
                                                <div key={item.id} className="flex items-center gap-3 p-2 bg-gray-50 rounded-lg">
                                                    <div className="flex-1 min-w-0">
                                                        <p className="font-medium text-sm truncate">{item.name}</p>
                                                        <p className="text-orange-600 font-semibold text-sm">
                                                            RM{(item.price * item.qty).toFixed(2)}
                                                        </p>
                                                    </div>
                                                    <div className="flex items-center gap-1">
                                                        <button
                                                            onClick={() => updateQty(item.id, -1)}
                                                            className="w-7 h-7 bg-gray-200 hover:bg-gray-300 rounded-full text-sm font-bold transition-colors"
                                                        >
                                                            -
                                                        </button>
                                                        <span className="w-6 text-center text-sm font-semibold">{item.qty}</span>
                                                        <button
                                                            onClick={() => updateQty(item.id, 1)}
                                                            className="w-7 h-7 bg-orange-500 hover:bg-orange-600 text-white rounded-full text-sm font-bold transition-colors"
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
                                    <div className="border-t p-4 space-y-3">
                                        <div className="space-y-2 text-sm">
                                            <div className="flex justify-between">
                                                <span className="text-gray-600">Subtotal</span>
                                                <span>RM{subtotal.toFixed(2)}</span>
                                            </div>
                                            <div className="flex justify-between">
                                                <span className="text-gray-600">Delivery</span>
                                                <span>{selectedZone ? `RM${deliveryFee.toFixed(2)}` : '-'}</span>
                                            </div>
                                            <div className="flex justify-between font-bold text-lg pt-2 border-t">
                                                <span>Jumlah</span>
                                                <span className="text-orange-600">RM{total.toFixed(2)}</span>
                                            </div>
                                        </div>

                                        {subtotal < minOrder && (
                                            <div className="text-sm text-red-500 bg-red-50 p-2 rounded-lg text-center">
                                                Min. order: RM{minOrder} (kurang RM{(minOrder - subtotal).toFixed(2)})
                                            </div>
                                        )}

                                        <button
                                            onClick={checkout}
                                            disabled={subtotal < minOrder || !selectedZone}
                                            className="w-full bg-green-600 hover:bg-green-700 disabled:bg-gray-300 disabled:cursor-not-allowed text-white font-bold py-3 rounded-xl transition-all flex items-center justify-center gap-2"
                                        >
                                            <span>📱</span> WhatsApp Pesanan
                                        </button>
                                    </div>
                                )}
                            </div>
                        </div>
                    </aside>
                </div>
            </div>

            {/* Mobile Bottom Cart Bar - Only shows when cart has items */}
            {cart.length > 0 && (
                <div className="lg:hidden fixed bottom-0 left-0 right-0 bg-white border-t-2 border-gray-200 shadow-2xl z-50 animate-slide-up">
                    <div className="p-3 safe-area-pb">
                        <div className="flex items-center justify-between mb-2">
                            <button
                                onClick={() => setIsCartDrawerOpen(true)}
                                className="flex items-center gap-2 text-left"
                            >
                                <div className="relative">
                                    <span className="text-2xl">🛒</span>
                                    <span className="absolute -top-1 -right-1 bg-orange-500 text-white text-xs w-5 h-5 rounded-full flex items-center justify-center font-bold">
                                        {cartItemCount}
                                    </span>
                                </div>
                                <div>
                                    <p className="font-semibold text-gray-800">Lihat Bakul</p>
                                    <p className="text-xs text-gray-500">{cartItemCount} item • RM{total.toFixed(2)}</p>
                                </div>
                            </button>
                            
                            <button
                                onClick={checkout}
                                disabled={subtotal < minOrder || !selectedZone}
                                className="bg-green-600 hover:bg-green-700 disabled:bg-gray-300 text-white font-bold py-3 px-6 rounded-xl transition-all flex items-center gap-2"
                            >
                                <span>📱</span> Pesan
                            </button>
                        </div>
                        {subtotal < minOrder && (
                            <p className="text-xs text-red-500 text-center">
                                Min. order: RM{minOrder} (kurang RM{(minOrder - subtotal).toFixed(2)})
                            </p>
                        )}
                    </div>
                </div>
            )}

            {/* Mobile Cart Drawer/Modal */}
            {isCartDrawerOpen && (
                <>
                    {/* Backdrop */}
                    <div 
                        className="lg:hidden fixed inset-0 bg-black/50 z-50 animate-fade-in"
                        onClick={() => setIsCartDrawerOpen(false)}
                    />
                    
                    {/* Drawer */}
                    <div className="lg:hidden fixed bottom-0 left-0 right-0 bg-white rounded-t-3xl z-50 max-h-[85vh] overflow-hidden animate-slide-up">
                        {/* Handle */}
                        <div className="flex justify-center pt-3 pb-2">
                            <div className="w-12 h-1.5 bg-gray-300 rounded-full"></div>
                        </div>
                        
                        {/* Header */}
                        <div className="flex items-center justify-between px-4 pb-3 border-b">
                            <h3 className="font-bold text-lg flex items-center gap-2">
                                <span>🛒</span> Bakul Pesanan
                            </h3>
                            <button 
                                onClick={() => setIsCartDrawerOpen(false)}
                                className="w-8 h-8 bg-gray-100 rounded-full flex items-center justify-center text-gray-600 hover:bg-gray-200"
                            >
                                ✕
                            </button>
                        </div>

                        {/* Cart Items */}
                        <div className="p-4 overflow-y-auto max-h-[50vh]">
                            {cart.length === 0 ? (
                                <div className="text-center py-8 text-gray-400">
                                    <span className="text-4xl">🛒</span>
                                    <p className="mt-2">Bakul kosong</p>
                                </div>
                            ) : (
                                <div className="space-y-3">
                                    {cart.map(item => (
                                        <div key={item.id} className="flex items-center gap-3 p-3 bg-gray-50 rounded-xl">
                                            <div className="flex-1 min-w-0">
                                                <p className="font-medium truncate">{item.name}</p>
                                                <p className="text-orange-600 font-semibold">
                                                    RM{(item.price * item.qty).toFixed(2)}
                                                </p>
                                            </div>
                                            <div className="flex items-center gap-2">
                                                <button
                                                    onClick={() => updateQty(item.id, -1)}
                                                    className="w-8 h-8 bg-gray-200 hover:bg-gray-300 rounded-full font-bold transition-colors"
                                                >
                                                    -
                                                </button>
                                                <span className="w-6 text-center font-semibold">{item.qty}</span>
                                                <button
                                                    onClick={() => updateQty(item.id, 1)}
                                                    className="w-8 h-8 bg-orange-500 hover:bg-orange-600 text-white rounded-full font-bold transition-colors"
                                                >
                                                    +
                                                </button>
                                                <button
                                                    onClick={() => removeFromCart(item.id)}
                                                    className="w-8 h-8 bg-red-100 hover:bg-red-200 text-red-600 rounded-full text-sm transition-colors ml-1"
                                                >
                                                    🗑️
                                                </button>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>

                        {/* Summary & Checkout */}
                        {cart.length > 0 && (
                            <div className="border-t p-4 bg-gray-50 safe-area-pb">
                                <div className="space-y-2 text-sm mb-4">
                                    <div className="flex justify-between">
                                        <span className="text-gray-600">Subtotal</span>
                                        <span>RM{subtotal.toFixed(2)}</span>
                                    </div>
                                    <div className="flex justify-between">
                                        <span className="text-gray-600">Delivery</span>
                                        <span>{selectedZone ? `RM${deliveryFee.toFixed(2)}` : 'Pilih kawasan'}</span>
                                    </div>
                                    <div className="flex justify-between font-bold text-lg pt-2 border-t">
                                        <span>Jumlah</span>
                                        <span className="text-orange-600">RM{total.toFixed(2)}</span>
                                    </div>
                                </div>

                                {subtotal < minOrder && (
                                    <div className="text-sm text-red-500 bg-red-50 p-2 rounded-lg text-center mb-3">
                                        Min. order: RM{minOrder} (kurang RM{(minOrder - subtotal).toFixed(2)})
                                    </div>
                                )}

                                <button
                                    onClick={() => {
                                        setIsCartDrawerOpen(false);
                                        checkout();
                                    }}
                                    disabled={subtotal < minOrder || !selectedZone}
                                    className="w-full bg-green-600 hover:bg-green-700 disabled:bg-gray-300 disabled:cursor-not-allowed text-white font-bold py-4 rounded-xl transition-all flex items-center justify-center gap-2 text-lg"
                                >
                                    <span>📱</span> WhatsApp Pesanan
                                </button>
                            </div>
                        )}
                    </div>
                </>
            )}
        </div>
    );
}
