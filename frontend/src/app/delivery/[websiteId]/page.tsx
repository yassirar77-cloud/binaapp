'use client';
import { useState, useEffect, useRef } from 'react';
import { useParams } from 'next/navigation';

const API_URL = 'https://binaapp-backend.onrender.com';

interface MenuItem {
    id: string;
    name: string;
    description: string;
    price: number;
    image_url?: string;
    category?: string;
}

interface CartItem extends MenuItem {
    qty: number;
}

interface Zone {
    id: string;
    zone_name: string;
    delivery_fee: number;
    estimated_time_min: number;
    estimated_time_max: number;
}

interface Settings {
    minimum_order?: number;
    delivery_hours?: string;
    whatsapp_number?: string;
}

export default function DeliveryPage() {
    const { websiteId } = useParams();
    const [loading, setLoading] = useState(true);
    const [menu, setMenu] = useState<{ categories: string[], items: MenuItem[] }>({ categories: [], items: [] });
    const [zones, setZones] = useState<Zone[]>([]);
    const [settings, setSettings] = useState<Settings | null>(null);
    const [cart, setCart] = useState<CartItem[]>([]);
    const [selectedZone, setSelectedZone] = useState<Zone | null>(null);
    const [customerInfo, setCustomerInfo] = useState({ name: '', phone: '', address: '', notes: '' });
    const [selectedCategory, setSelectedCategory] = useState<string>('all');
    const [cartDrawerOpen, setCartDrawerOpen] = useState(false);
    const [addedItemId, setAddedItemId] = useState<string | null>(null);
    const menuRef = useRef<HTMLDivElement>(null);
    const STORAGE_KEY = `delivery_zone_${websiteId}`;

    // Load zone from localStorage on mount
    useEffect(() => {
        const savedZone = localStorage.getItem(STORAGE_KEY);
        if (savedZone) {
            try {
                setSelectedZone(JSON.parse(savedZone));
            } catch (e) {
                localStorage.removeItem(STORAGE_KEY);
            }
        }
    }, [websiteId]);

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
            setMenu({ ...menuData, categories });
            setZones(zonesData.zones || []);
            setSettings(zonesData.settings || {});
        } catch (err) {
            console.error('Failed to load:', err);
        }
        setLoading(false);
    }

    function selectZone(zone: Zone) {
        setSelectedZone(zone);
        localStorage.setItem(STORAGE_KEY, JSON.stringify(zone));
        // Smooth scroll to menu
        setTimeout(() => {
            menuRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }, 100);
    }

    function addToCart(item: MenuItem) {
        const existing = cart.find(c => c.id === item.id);
        if (existing) {
            setCart(cart.map(c => c.id === item.id ? {...c, qty: c.qty + 1} : c));
        } else {
            setCart([...cart, {...item, qty: 1}]);
        }
        // Show visual feedback
        setAddedItemId(item.id);
        setTimeout(() => setAddedItemId(null), 600);
    }

    function updateQty(id: string, delta: number) {
        setCart(cart.map(c => {
            if (c.id === id) {
                const newQty = c.qty + delta;
                return newQty > 0 ? {...c, qty: newQty} : null;
            }
            return c;
        }).filter(Boolean) as CartItem[]);
    }

    function removeFromCart(id: string) {
        setCart(cart.filter(c => c.id !== id));
    }

    const subtotal = cart.reduce((sum, item) => sum + (item.price * item.qty), 0);
    const deliveryFee = selectedZone?.delivery_fee || 0;
    const total = subtotal + deliveryFee;
    const minOrder = settings?.minimum_order || 0;
    const totalItems = cart.reduce((sum, i) => sum + i.qty, 0);

    // Filter menu items by category
    const filteredItems = selectedCategory === 'all' 
        ? menu.items 
        : menu.items?.filter(item => item.category === selectedCategory);

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
            <div className="max-w-6xl mx-auto p-4">
                <div className="lg:flex lg:gap-6">
                    {/* Left Column - Menu (Mobile: full width, Desktop: 70%) */}
                    <div className="lg:w-[70%]">
                        {/* Zone Selection */}
                        <section className="bg-white rounded-2xl p-4 md:p-6 shadow-sm mb-4">
                            <h2 className="text-lg md:text-xl font-bold mb-4 flex items-center gap-2">
                                <span>📍</span> Kawasan Delivery
                            </h2>
                            
                            {/* Selected Zone Display */}
                            {selectedZone && (
                                <div className="mb-4 p-3 md:p-4 bg-green-50 border-2 border-green-200 rounded-xl animate-fadeIn">
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
                                                onClick={() => {
                                                    setSelectedZone(null);
                                                    localStorage.removeItem(STORAGE_KEY);
                                                }}
                                                className="text-sm text-orange-600 hover:text-orange-700 underline transition-colors"
                                            >
                                                Tukar
                                            </button>
                                        </div>
                                    </div>
                                </div>
                            )}

                            {/* Zone Selection Grid */}
                            {!selectedZone && (
                                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                                    {zones.map(zone => (
                                        <button
                                            key={zone.id}
                                            onClick={() => selectZone(zone)}
                                            className="p-4 border-2 border-gray-200 rounded-xl text-left hover:border-orange-500 hover:bg-orange-50 transition-all duration-200 active:scale-[0.98]"
                                        >
                                            <div className="flex justify-between items-start">
                                                <div>
                                                    <div className="font-semibold text-gray-800">{zone.zone_name}</div>
                                                    <div className="text-sm text-gray-500 mt-1">
                                                        🕐 {zone.estimated_time_min}-{zone.estimated_time_max} min
                                                    </div>
                                                </div>
                                                <div className="text-orange-600 font-bold text-lg">
                                                    RM{zone.delivery_fee}
                                                </div>
                                            </div>
                                        </button>
                                    ))}
                                </div>
                            )}
                        </section>

                        {/* Menu Section */}
                        <section ref={menuRef} className="bg-white rounded-2xl p-4 md:p-6 shadow-sm mb-4">
                            <h2 className="text-lg md:text-xl font-bold mb-4 flex items-center gap-2">
                                <span>🍽️</span> Menu
                            </h2>

                            {/* Category Filter */}
                            {menu.categories.length > 0 && (
                                <div className="mb-4 overflow-x-auto pb-2 -mx-4 px-4 scrollbar-hide">
                                    <div className="flex gap-2 min-w-max">
                                        <button
                                            onClick={() => setSelectedCategory('all')}
                                            className={`px-4 py-2 rounded-full text-sm font-medium transition-all duration-200 whitespace-nowrap
                                                ${selectedCategory === 'all' 
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
                                                className={`px-4 py-2 rounded-full text-sm font-medium transition-all duration-200 whitespace-nowrap
                                                    ${selectedCategory === cat 
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

                            {/* Menu Items Grid */}
                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 md:gap-4">
                                {filteredItems?.map(item => {
                                    const inCart = cart.find(c => c.id === item.id);
                                    const justAdded = addedItemId === item.id;
                                    return (
                                        <div 
                                            key={item.id} 
                                            className={`flex gap-3 p-3 bg-gray-50 rounded-xl transition-all duration-200 
                                                ${justAdded ? 'ring-2 ring-green-400 bg-green-50' : 'hover:bg-gray-100'}`}
                                        >
                                            {item.image_url && (
                                                <img 
                                                    src={item.image_url} 
                                                    alt={item.name} 
                                                    className="w-20 h-20 md:w-24 md:h-24 rounded-lg object-cover flex-shrink-0" 
                                                />
                                            )}
                                            <div className="flex-1 min-w-0">
                                                <h3 className="font-semibold text-gray-800 text-sm md:text-base truncate">{item.name}</h3>
                                                {item.description && (
                                                    <p className="text-xs md:text-sm text-gray-500 line-clamp-2 mt-0.5">{item.description}</p>
                                                )}
                                                <div className="flex justify-between items-center mt-2">
                                                    <span className="font-bold text-orange-600">RM{item.price?.toFixed(2)}</span>
                                                    {inCart ? (
                                                        <div className="flex items-center gap-1.5">
                                                            <button 
                                                                onClick={() => updateQty(item.id, -1)} 
                                                                className="w-8 h-8 bg-gray-200 hover:bg-gray-300 rounded-full flex items-center justify-center transition-colors active:scale-95 font-bold"
                                                            >
                                                                −
                                                            </button>
                                                            <span className="font-bold w-6 text-center">{inCart.qty}</span>
                                                            <button 
                                                                onClick={() => addToCart(item)} 
                                                                className="w-8 h-8 bg-orange-500 hover:bg-orange-600 text-white rounded-full flex items-center justify-center transition-colors active:scale-95 font-bold"
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

                        {/* Checkout Form - Mobile Only (appears after cart) */}
                        <section className="lg:hidden bg-white rounded-2xl p-4 shadow-sm mb-24">
                            <h2 className="text-lg font-bold mb-4 flex items-center gap-2">
                                <span>📝</span> Maklumat Penghantaran
                            </h2>
                            <div className="space-y-3">
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
                        </section>
                    </div>

                    {/* Right Column - Desktop Cart Sidebar (Hidden on Mobile) */}
                    <aside className="hidden lg:block lg:w-[30%] lg:max-w-[320px]">
                        <div className="sticky top-24">
                            <div className="bg-white rounded-2xl shadow-sm overflow-hidden">
                                <div className="p-4 bg-gradient-to-r from-orange-500 to-red-500 text-white">
                                    <h2 className="text-lg font-bold flex items-center gap-2">
                                        <span>🛒</span> Bakul Pesanan
                                    </h2>
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
                                                        >
                                                            −
                                                        </button>
                                                        <span className="w-5 text-center text-sm font-medium">{item.qty}</span>
                                                        <button 
                                                            onClick={() => updateQty(item.id, 1)}
                                                            className="w-6 h-6 bg-orange-100 hover:bg-orange-200 text-orange-600 rounded-full text-sm font-bold transition-colors"
                                                        >
                                                            +
                                                        </button>
                                                        <button 
                                                            onClick={() => removeFromCart(item.id)}
                                                            className="w-6 h-6 text-gray-400 hover:text-red-500 transition-colors ml-1"
                                                        >
                                                            ✕
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
                                                <span>{selectedZone ? `RM${deliveryFee.toFixed(2)}` : '—'}</span>
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
                                            <h3 className="font-semibold text-sm text-gray-700">Maklumat Penghantaran</h3>
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
                                                disabled={subtotal < minOrder || !selectedZone}
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
            </div>

            {/* Mobile Bottom Cart Bar - Only shows when cart has items */}
            {cart.length > 0 && (
                <div className="lg:hidden fixed bottom-0 left-0 right-0 bg-white border-t border-gray-200 shadow-2xl z-50 animate-slideUp">
                    <div className="p-3">
                        <button
                            onClick={() => setCartDrawerOpen(true)}
                            className="w-full bg-orange-500 hover:bg-orange-600 text-white font-bold py-3.5 px-4 rounded-xl transition-all duration-200 active:scale-[0.98] flex items-center justify-between"
                        >
                            <div className="flex items-center gap-2">
                                <span className="bg-white text-orange-500 w-6 h-6 rounded-full flex items-center justify-center text-sm font-bold">
                                    {totalItems}
                                </span>
                                <span>Lihat Bakul</span>
                            </div>
                            <span className="font-bold">RM{total.toFixed(2)}</span>
                        </button>
                    </div>
                </div>
            )}

            {/* Mobile Cart Drawer/Modal */}
            {cartDrawerOpen && (
                <>
                    {/* Backdrop */}
                    <div 
                        className="lg:hidden fixed inset-0 bg-black/50 z-50 animate-fadeIn"
                        onClick={() => setCartDrawerOpen(false)}
                    />
                    
                    {/* Drawer */}
                    <div className="lg:hidden fixed bottom-0 left-0 right-0 bg-white rounded-t-3xl z-50 max-h-[85vh] overflow-hidden animate-slideUp">
                        {/* Handle */}
                        <div className="flex justify-center pt-3 pb-2">
                            <div className="w-12 h-1.5 bg-gray-300 rounded-full" />
                        </div>
                        
                        {/* Header */}
                        <div className="flex items-center justify-between px-4 pb-3 border-b">
                            <h2 className="text-lg font-bold flex items-center gap-2">
                                <span>🛒</span> Bakul Pesanan
                            </h2>
                            <button 
                                onClick={() => setCartDrawerOpen(false)}
                                className="w-8 h-8 flex items-center justify-center text-gray-400 hover:text-gray-600"
                            >
                                ✕
                            </button>
                        </div>
                        
                        {/* Cart Items */}
                        <div className="px-4 py-3 max-h-[40vh] overflow-y-auto">
                            {cart.map(item => (
                                <div key={item.id} className="flex gap-3 items-center py-3 border-b border-gray-100 last:border-0">
                                    <div className="flex-1 min-w-0">
                                        <div className="font-medium truncate">{item.name}</div>
                                        <div className="text-orange-600 text-sm">RM{(item.price * item.qty).toFixed(2)}</div>
                                    </div>
                                    <div className="flex items-center gap-2">
                                        <button 
                                            onClick={() => updateQty(item.id, -1)}
                                            className="w-8 h-8 bg-gray-100 hover:bg-gray-200 rounded-full font-bold transition-colors"
                                        >
                                            −
                                        </button>
                                        <span className="w-6 text-center font-medium">{item.qty}</span>
                                        <button 
                                            onClick={() => updateQty(item.id, 1)}
                                            className="w-8 h-8 bg-orange-100 hover:bg-orange-200 text-orange-600 rounded-full font-bold transition-colors"
                                        >
                                            +
                                        </button>
                                        <button 
                                            onClick={() => removeFromCart(item.id)}
                                            className="w-8 h-8 text-gray-400 hover:text-red-500 transition-colors"
                                        >
                                            🗑️
                                        </button>
                                    </div>
                                </div>
                            ))}
                        </div>
                        
                        {/* Summary & Checkout */}
                        <div className="px-4 py-4 bg-gray-50 border-t space-y-3">
                            <div className="flex justify-between text-gray-600">
                                <span>Subtotal</span>
                                <span>RM{subtotal.toFixed(2)}</span>
                            </div>
                            <div className="flex justify-between text-gray-600">
                                <span>Delivery</span>
                                <span>{selectedZone ? `RM${deliveryFee.toFixed(2)}` : '—'}</span>
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
                            <button
                                onClick={() => {
                                    setCartDrawerOpen(false);
                                    if (selectedZone && subtotal >= minOrder) {
                                        // Scroll to checkout form
                                        setTimeout(() => {
                                            document.querySelector('input[placeholder="Nama penuh"]')?.scrollIntoView({ behavior: 'smooth', block: 'center' });
                                        }, 300);
                                    }
                                }}
                                disabled={subtotal < minOrder || !selectedZone}
                                className="w-full bg-green-600 hover:bg-green-700 disabled:bg-gray-300 disabled:cursor-not-allowed text-white font-bold py-4 rounded-xl transition-all duration-200 active:scale-[0.98] flex items-center justify-center gap-2"
                            >
                                <span>📝</span> Teruskan ke Checkout
                            </button>
                        </div>
                    </div>
                </>
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
