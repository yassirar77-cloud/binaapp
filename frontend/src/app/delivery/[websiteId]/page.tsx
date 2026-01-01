'use client';
import { useState, useEffect, useRef } from 'react';
import { useParams } from 'next/navigation';
import { ShoppingBag, ChevronDown, Check, MapPin, Plus, Minus, X, Info, Search } from 'lucide-react';

const API_URL = 'https://binaapp-backend.onrender.com';

export default function DeliveryPage() {
    const { websiteId } = useParams();
    const [loading, setLoading] = useState(true);
    const [menu, setMenu] = useState({ categories: [], items: [] });
    const [zones, setZones] = useState([]);
    const [settings, setSettings] = useState(null);
    const [cart, setCart] = useState([]);
    const [selectedZone, setSelectedZone] = useState(null);
    const [step, setStep] = useState(1); // 1=zone, 2=menu
    const [customerInfo, setCustomerInfo] = useState({ name: '', phone: '', address: '', notes: '' });
    const [selectedCategory, setSelectedCategory] = useState('all');
    const [isCartOpen, setIsCartOpen] = useState(false); // Mobile cart modal
    
    // Refs for scrolling
    const menuRef = useRef(null);

    useEffect(() => {
        loadData();
        // Load saved zone
        const savedZone = localStorage.getItem(`zone_${websiteId}`);
        if (savedZone) {
            setSelectedZone(JSON.parse(savedZone));
            setStep(2);
        }
    }, [websiteId]);

    useEffect(() => {
        if (selectedZone) {
            localStorage.setItem(`zone_${websiteId}`, JSON.stringify(selectedZone));
            if (step === 2) {
                // Auto scroll to menu on mobile/desktop
                setTimeout(() => {
                    menuRef.current?.scrollIntoView({ behavior: 'smooth' });
                }, 100);
            }
        }
    }, [selectedZone, step, websiteId]);

    async function loadData() {
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
    }

    function addToCart(item) {
        const existing = cart.find(c => c.id === item.id);
        if (existing) {
            setCart(cart.map(c => c.id === item.id ? {...c, qty: c.qty + 1} : c));
        } else {
            setCart([...cart, {...item, qty: 1}]);
        }
    }

    function updateQty(id, delta) {
        setCart(cart.map(c => {
            if (c.id === id) {
                const newQty = c.qty + delta;
                return newQty > 0 ? {...c, qty: newQty} : null;
            }
            return c;
        }).filter(Boolean));
    }

    const subtotal = cart.reduce((sum, item) => sum + (item.price * item.qty), 0);
    const deliveryFee = selectedZone?.delivery_fee || 0;
    const total = subtotal + deliveryFee;
    const minOrder = settings?.minimum_order || 0;

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

    // Filter items
    const filteredItems = selectedCategory === 'all' 
        ? menu.items 
        : menu.items?.filter(item => item.category_id === selectedCategory || item.category === selectedCategory);

    // Get unique categories if not provided in menu.categories
    const categories = menu.categories?.length > 0 
        ? menu.categories 
        : [...new Set(menu.items?.map(i => i.category || 'Lain-lain'))].map((c, i) => ({ id: c, name: c }));

    const CartContent = () => (
        <div className="flex flex-col h-full">
            <div className="p-4 border-b bg-gray-50 flex justify-between items-center">
                <h3 className="font-bold flex items-center gap-2">
                    <ShoppingBag className="w-5 h-5" />
                    Bakul Pesanan
                </h3>
                {/* Mobile Close Button */}
                <button onClick={() => setIsCartOpen(false)} className="lg:hidden p-2 hover:bg-gray-200 rounded-full">
                    <X className="w-5 h-5" />
                </button>
            </div>

            <div className="flex-1 overflow-y-auto p-4 space-y-4">
                {cart.length === 0 ? (
                    <div className="text-center py-10 text-gray-500">
                        <ShoppingBag className="w-12 h-12 mx-auto mb-3 opacity-20" />
                        <p>Bakul masih kosong</p>
                    </div>
                ) : (
                    <>
                        <div className="space-y-3">
                            {cart.map(item => (
                                <div key={item.id} className="flex gap-3 bg-white p-3 rounded-lg border shadow-sm">
                                    {item.image_url && <img src={item.image_url} className="w-16 h-16 rounded object-cover bg-gray-100" />}
                                    <div className="flex-1">
                                        <div className="font-medium text-sm line-clamp-1">{item.name}</div>
                                        <div className="text-orange-600 font-bold text-sm">RM{(item.price * item.qty).toFixed(2)}</div>
                                    </div>
                                    <div className="flex flex-col items-center gap-1">
                                        <button onClick={() => updateQty(item.id, 1)} className="w-6 h-6 bg-orange-100 text-orange-600 rounded flex items-center justify-center text-xs hover:bg-orange-200">+</button>
                                        <span className="text-xs font-bold">{item.qty}</span>
                                        <button onClick={() => updateQty(item.id, -1)} className="w-6 h-6 bg-gray-100 text-gray-600 rounded flex items-center justify-center text-xs hover:bg-gray-200">-</button>
                                    </div>
                                </div>
                            ))}
                        </div>

                        {/* Bill Summary */}
                        <div className="border-t pt-4 space-y-2 text-sm">
                            <div className="flex justify-between">
                                <span className="text-gray-600">Subtotal</span>
                                <span>RM{subtotal.toFixed(2)}</span>
                            </div>
                            <div className="flex justify-between">
                                <span className="text-gray-600">Delivery ({selectedZone?.zone_name})</span>
                                <span>RM{deliveryFee.toFixed(2)}</span>
                            </div>
                            <div className="flex justify-between font-bold text-lg pt-2 border-t">
                                <span>Jumlah</span>
                                <span className="text-orange-600">RM{total.toFixed(2)}</span>
                            </div>
                        </div>

                        {/* Checkout Form */}
                        <div className="pt-4 space-y-3">
                            <h4 className="font-bold text-sm text-gray-700">Maklumat Penghantaran</h4>
                            <input
                                type="text"
                                placeholder="Nama penuh"
                                value={customerInfo.name}
                                onChange={e => setCustomerInfo({...customerInfo, name: e.target.value})}
                                className="w-full p-2 border rounded-lg text-sm"
                            />
                            <input
                                type="tel"
                                placeholder="No. Telefon (WhatsApp)"
                                value={customerInfo.phone}
                                onChange={e => setCustomerInfo({...customerInfo, phone: e.target.value})}
                                className="w-full p-2 border rounded-lg text-sm"
                            />
                            <textarea
                                placeholder="Alamat penuh delivery"
                                value={customerInfo.address}
                                onChange={e => setCustomerInfo({...customerInfo, address: e.target.value})}
                                className="w-full p-2 border rounded-lg text-sm"
                                rows={2}
                            />
                            <textarea
                                placeholder="Nota (cth: jangan pedas)"
                                value={customerInfo.notes}
                                onChange={e => setCustomerInfo({...customerInfo, notes: e.target.value})}
                                className="w-full p-2 border rounded-lg text-sm"
                                rows={1}
                            />
                        </div>
                    </>
                )}
            </div>

            <div className="p-4 border-t bg-white">
                {subtotal < minOrder && (
                    <div className="mb-2 text-center text-xs text-red-500 bg-red-50 p-2 rounded">
                        Min. order RM{minOrder} (Kurang RM{(minOrder - subtotal).toFixed(2)})
                    </div>
                )}
                <button
                    onClick={checkout}
                    disabled={subtotal < minOrder || cart.length === 0}
                    className="w-full bg-green-600 hover:bg-green-700 disabled:bg-gray-300 disabled:cursor-not-allowed text-white font-bold py-3 rounded-xl flex items-center justify-center gap-2 transition-colors"
                >
                    <span>📱</span> WhatsApp Pesanan
                </button>
            </div>
        </div>
    );

    if (loading) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-gray-50">
                <div className="animate-pulse flex flex-col items-center">
                    <div className="w-12 h-12 bg-gray-200 rounded-full mb-3"></div>
                    <div className="h-4 w-32 bg-gray-200 rounded"></div>
                </div>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-gray-100 font-sans pb-24 lg:pb-0">
            {/* Mobile Header */}
            <header className="bg-white shadow-sm sticky top-0 z-30">
                <div className="max-w-7xl mx-auto px-4 py-4 flex justify-between items-center">
                    <div>
                        <h1 className="font-bold text-lg leading-tight">Delivery</h1>
                        <p className="text-xs text-gray-500">
                            {settings?.delivery_hours || '11am-10pm'}
                        </p>
                    </div>
                    {selectedZone && (
                        <button 
                            onClick={() => setStep(1)}
                            className="text-xs bg-orange-50 text-orange-600 px-3 py-1 rounded-full border border-orange-100 flex items-center gap-1"
                        >
                            <MapPin className="w-3 h-3" />
                            {selectedZone.zone_name}
                        </button>
                    )}
                </div>
            </header>

            <main className="max-w-7xl mx-auto p-4 lg:p-8">
                {step === 1 ? (
                    <div className="max-w-md mx-auto mt-10">
                        <div className="text-center mb-8">
                            <h2 className="text-2xl font-bold mb-2">📍 Pilih Kawasan</h2>
                            <p className="text-gray-500">Sila pilih kawasan penghantaran anda untuk melihat menu</p>
                        </div>
                        <div className="grid gap-3">
                            {zones.map(zone => (
                                <button
                                    key={zone.id}
                                    onClick={() => { setSelectedZone(zone); setStep(2); }}
                                    className="group relative overflow-hidden p-4 bg-white border-2 border-transparent hover:border-orange-500 rounded-xl shadow-sm hover:shadow-md transition-all text-left"
                                >
                                    <div className="flex justify-between items-center relative z-10">
                                        <div>
                                            <div className="font-bold text-gray-800">{zone.zone_name}</div>
                                            <div className="text-xs text-gray-500 mt-1 flex items-center gap-2">
                                                <span>⏱ {zone.estimated_time_min}-{zone.estimated_time_max} min</span>
                                            </div>
                                        </div>
                                        <div className="text-right">
                                            <div className="font-bold text-orange-600">RM{zone.delivery_fee}</div>
                                            <div className="text-[10px] text-gray-400">Delivery</div>
                                        </div>
                                    </div>
                                </button>
                            ))}
                        </div>
                    </div>
                ) : (
                    <div className="lg:grid lg:grid-cols-[1fr_320px] lg:gap-8 items-start">
                        {/* Left Column: Menu */}
                        <div ref={menuRef}>
                            {/* Area Selection Feedback */}
                            <div className="mb-6 bg-green-50 border border-green-100 p-3 rounded-lg flex justify-between items-center animate-in fade-in slide-in-from-top-2">
                                <div className="flex items-center gap-2 text-green-700 text-sm font-medium">
                                    <Check className="w-4 h-4" />
                                    Kawasan dipilih: {selectedZone.zone_name}
                                </div>
                                <button onClick={() => setStep(1)} className="text-xs text-green-600 underline">Tukar</button>
                            </div>

                            {/* Category Filter */}
                            <div className="sticky top-[72px] z-20 bg-gray-100/95 backdrop-blur py-2 mb-6 -mx-4 px-4 lg:mx-0 lg:px-0 overflow-x-auto no-scrollbar">
                                <div className="flex gap-2">
                                    <button
                                        onClick={() => setSelectedCategory('all')}
                                        className={`px-4 py-2 rounded-full text-sm font-medium whitespace-nowrap transition-colors ${
                                            selectedCategory === 'all' 
                                            ? 'bg-orange-600 text-white shadow-md' 
                                            : 'bg-white text-gray-600 hover:bg-gray-50 border'
                                        }`}
                                    >
                                        Semua
                                    </button>
                                    {categories.map(cat => (
                                        <button
                                            key={cat.id}
                                            onClick={() => setSelectedCategory(cat.id)}
                                            className={`px-4 py-2 rounded-full text-sm font-medium whitespace-nowrap transition-colors ${
                                                selectedCategory === cat.id 
                                                ? 'bg-orange-600 text-white shadow-md' 
                                                : 'bg-white text-gray-600 hover:bg-gray-50 border'
                                            }`}
                                        >
                                            {cat.name}
                                        </button>
                                    ))}
                                </div>
                            </div>

                            {/* Menu Grid */}
                            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-2 xl:grid-cols-3 gap-4">
                                {filteredItems?.map(item => {
                                    const inCart = cart.find(c => c.id === item.id);
                                    return (
                                        <div key={item.id} className="bg-white rounded-xl shadow-sm border overflow-hidden hover:shadow-md transition-shadow flex flex-col">
                                            {item.image_url && (
                                                <div className="aspect-video w-full overflow-hidden bg-gray-100 relative">
                                                    <img src={item.image_url} alt={item.name} className="w-full h-full object-cover" />
                                                </div>
                                            )}
                                            <div className="p-4 flex-1 flex flex-col">
                                                <div className="flex-1">
                                                    <h3 className="font-bold text-gray-800 line-clamp-2">{item.name}</h3>
                                                    <p className="text-xs text-gray-500 mt-1 line-clamp-2">{item.description}</p>
                                                </div>
                                                <div className="mt-4 flex justify-between items-center pt-3 border-t">
                                                    <span className="font-bold text-lg text-orange-600">RM{item.price?.toFixed(2)}</span>
                                                    {inCart ? (
                                                        <div className="flex items-center gap-3 bg-orange-50 rounded-full px-1 py-1">
                                                            <button onClick={() => updateQty(item.id, -1)} className="w-8 h-8 flex items-center justify-center bg-white rounded-full shadow-sm text-orange-600 hover:bg-gray-50">
                                                                <Minus className="w-4 h-4" />
                                                            </button>
                                                            <span className="font-bold text-sm w-4 text-center">{inCart.qty}</span>
                                                            <button onClick={() => updateQty(item.id, 1)} className="w-8 h-8 flex items-center justify-center bg-orange-500 rounded-full shadow-sm text-white hover:bg-orange-600">
                                                                <Plus className="w-4 h-4" />
                                                            </button>
                                                        </div>
                                                    ) : (
                                                        <button 
                                                            onClick={() => addToCart(item)}
                                                            className="bg-gray-900 text-white px-4 py-2 rounded-full text-sm font-medium hover:bg-black transition-colors flex items-center gap-2"
                                                        >
                                                            <Plus className="w-4 h-4" /> Tambah
                                                        </button>
                                                    )}
                                                </div>
                                            </div>
                                        </div>
                                    );
                                })}
                            </div>
                        </div>

                        {/* Desktop Cart Sidebar */}
                        <div className="hidden lg:block sticky top-24 h-[calc(100vh-8rem)]">
                            <div className="bg-white rounded-2xl shadow-lg border overflow-hidden h-full">
                                <CartContent />
                            </div>
                        </div>
                    </div>
                )}
            </main>

            {/* Mobile Bottom Cart Bar */}
            {step === 2 && cart.length > 0 && (
                <div className="fixed bottom-0 left-0 right-0 bg-white border-t shadow-[0_-4px_6px_-1px_rgba(0,0,0,0.1)] p-4 z-40 lg:hidden safe-area-bottom">
                    <button 
                        onClick={() => setIsCartOpen(true)}
                        className="w-full bg-gray-900 text-white p-4 rounded-xl flex justify-between items-center shadow-lg hover:bg-black transition-all active:scale-[0.98]"
                    >
                        <div className="flex items-center gap-3">
                            <div className="bg-orange-500 w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold">
                                {cart.reduce((sum, i) => sum + i.qty, 0)}
                            </div>
                            <span className="font-medium">Lihat Bakul</span>
                        </div>
                        <span className="font-bold text-lg">RM{total.toFixed(2)}</span>
                    </button>
                </div>
            )}

            {/* Mobile Cart Modal/Drawer */}
            {isCartOpen && (
                <div className="fixed inset-0 z-50 lg:hidden">
                    <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" onClick={() => setIsCartOpen(false)}></div>
                    <div className="absolute bottom-0 left-0 right-0 bg-white rounded-t-3xl h-[85vh] shadow-2xl animate-in slide-in-from-bottom duration-200">
                        <div className="w-12 h-1.5 bg-gray-300 rounded-full mx-auto my-3"></div>
                        <CartContent />
                    </div>
                </div>
            )}
        </div>
    );
}
