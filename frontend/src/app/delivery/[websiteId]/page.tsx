'use client';
import { useState, useEffect, useMemo } from 'react';
import { useParams } from 'next/navigation';
import { ShoppingBag, MapPin, X, Plus, Minus, ChevronRight, Check, Trash2 } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

const API_URL = 'https://binaapp-backend.onrender.com';

export default function DeliveryPage() {
    const { websiteId } = useParams();
    const [loading, setLoading] = useState(true);
    const [menu, setMenu] = useState<{ categories: any[], items: any[] }>({ categories: [], items: [] });
    const [zones, setZones] = useState<any[]>([]);
    const [settings, setSettings] = useState<any>(null);
    const [cart, setCart] = useState<any[]>([]);
    const [selectedZone, setSelectedZone] = useState<any>(null);
    const [customerInfo, setCustomerInfo] = useState({ name: '', phone: '', address: '', notes: '' });
    
    // UI States
    const [selectedCategory, setSelectedCategory] = useState('All');
    const [isMobileCartOpen, setIsMobileCartOpen] = useState(false);
    const [showZoneSelector, setShowZoneSelector] = useState(true);

    // Initial Load
    useEffect(() => {
        loadData();
        // Load persisted zone
        const savedZone = localStorage.getItem(`delivery_zone_${websiteId}`);
        if (savedZone) {
            setSelectedZone(JSON.parse(savedZone));
            setShowZoneSelector(false);
        }
    }, [websiteId]);

    // Persist Zone
    useEffect(() => {
        if (selectedZone) {
            localStorage.setItem(`delivery_zone_${websiteId}`, JSON.stringify(selectedZone));
        }
    }, [selectedZone, websiteId]);

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

    // Cart Operations
    function addToCart(item: any) {
        const existing = cart.find(c => c.id === item.id);
        if (existing) {
            setCart(cart.map(c => c.id === item.id ? {...c, qty: c.qty + 1} : c));
        } else {
            setCart([...cart, {...item, qty: 1}]);
        }
    }

    function updateQty(id: any, delta: number) {
        setCart(cart.map(c => {
            if (c.id === id) {
                const newQty = c.qty + delta;
                return newQty > 0 ? {...c, qty: newQty} : null;
            }
            return c;
        }).filter(Boolean));
    }

    function clearCart() {
        if (confirm('Kosongkan bakul pesanan?')) {
            setCart([]);
            setIsMobileCartOpen(false);
        }
    }

    const subtotal = cart.reduce((sum, item) => sum + (item.price * item.qty), 0);
    const deliveryFee = selectedZone?.delivery_fee || 0;
    const total = subtotal + deliveryFee;
    const minOrder = settings?.minimum_order || 0;

    // Derived Data
    const categories = useMemo(() => {
        // Use provided categories or extract from items if empty
        if (menu.categories?.length > 0) return ['All', ...menu.categories.map(c => c.name)];
        const uniqueCats = Array.from(new Set(menu.items.map(i => i.category || 'Other')));
        return ['All', ...uniqueCats];
    }, [menu]);

    const filteredItems = useMemo(() => {
        if (selectedCategory === 'All') return menu.items;
        // Check if categories are objects or just strings in items
        // Assuming items have category_id or category_name. 
        // If complex, we might need adjustments. Simplified assumption: item.category matches.
        return menu.items.filter(i => {
             // Handle case where category might be an object or ID
             if (menu.categories?.length > 0) {
                 const cat = menu.categories.find(c => c.name === selectedCategory);
                 return i.category_id === cat?.id; 
             }
             return i.category === selectedCategory;
        });
    }, [selectedCategory, menu]);

    function handleZoneSelect(zone: any) {
        setSelectedZone(zone);
        setShowZoneSelector(false);
        // Scroll to menu
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }

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

    // Render Components
    const CartContent = ({ isMobile = false }) => (
        <div className="flex flex-col h-full">
            <div className="p-4 border-b flex justify-between items-center bg-gray-50">
                <h3 className="font-bold text-lg flex items-center gap-2">
                    <ShoppingBag size={20} />
                    Bakul Pesanan
                </h3>
                {cart.length > 0 && (
                    <button onClick={clearCart} className="text-red-500 hover:bg-red-50 p-1 rounded transition">
                        <Trash2 size={18} />
                    </button>
                )}
            </div>
            
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
                {cart.length === 0 ? (
                    <div className="text-center text-gray-500 py-10">
                        <ShoppingBag size={48} className="mx-auto mb-2 opacity-20" />
                        <p>Bakul kosong</p>
                    </div>
                ) : (
                    cart.map(item => (
                        <div key={item.id} className="flex gap-3 items-start">
                            <div className="flex-1">
                                <div className="font-medium line-clamp-1">{item.name}</div>
                                <div className="text-sm text-gray-500">RM{item.price.toFixed(2)}</div>
                            </div>
                            <div className="flex items-center gap-2 bg-gray-100 rounded-lg p-1">
                                <button onClick={() => updateQty(item.id, -1)} className="w-6 h-6 flex items-center justify-center bg-white rounded shadow-sm hover:bg-gray-50">-</button>
                                <span className="text-sm font-medium w-4 text-center">{item.qty}</span>
                                <button onClick={() => updateQty(item.id, 1)} className="w-6 h-6 flex items-center justify-center bg-white rounded shadow-sm hover:bg-gray-50">+</button>
                            </div>
                        </div>
                    ))
                )}
            </div>

            <div className="p-4 bg-gray-50 border-t space-y-3">
                <div className="space-y-1 text-sm">
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

                {cart.length > 0 && (
                    <div className="pt-2 space-y-3">
                        {/* Simplified Checkout Form in Cart for Desktop, or make it a separate step?
                            The requirement implies checkout flow. 
                            Let's keep form here for compactness or reveal it.
                            For now, inputs inside cart container.
                        */}
                         <div className="space-y-2">
                            <input
                                placeholder="Nama"
                                value={customerInfo.name}
                                onChange={e => setCustomerInfo({...customerInfo, name: e.target.value})}
                                className="w-full p-2 text-sm border rounded-lg"
                            />
                            <input
                                placeholder="Telefon"
                                type="tel"
                                value={customerInfo.phone}
                                onChange={e => setCustomerInfo({...customerInfo, phone: e.target.value})}
                                className="w-full p-2 text-sm border rounded-lg"
                            />
                             <textarea
                                placeholder="Alamat penuh"
                                value={customerInfo.address}
                                onChange={e => setCustomerInfo({...customerInfo, address: e.target.value})}
                                className="w-full p-2 text-sm border rounded-lg resize-none"
                                rows={2}
                            />
                        </div>

                        <button
                            onClick={checkout}
                            disabled={subtotal < minOrder}
                            className="w-full bg-green-600 hover:bg-green-700 disabled:bg-gray-300 text-white font-bold py-3 rounded-xl flex items-center justify-center gap-2 transition"
                        >
                            <span>WhatsApp Pesanan</span>
                        </button>
                        {subtotal < minOrder && (
                            <div className="text-center text-xs text-red-500">
                                Min order: RM{minOrder}
                            </div>
                        )}
                    </div>
                )}
            </div>
        </div>
    );

    if (loading) return (
        <div className="min-h-screen flex items-center justify-center bg-gray-50">
            <div className="w-8 h-8 border-4 border-orange-500 border-t-transparent rounded-full animate-spin"></div>
        </div>
    );

    if (showZoneSelector) return (
        <div className="min-h-screen bg-gray-50 flex flex-col items-center justify-center p-4">
             <div className="w-full max-w-md bg-white rounded-2xl shadow-xl p-6">
                <div className="text-center mb-6">
                    <h1 className="text-2xl font-bold mb-2">📍 Pilih Kawasan</h1>
                    <p className="text-gray-500">Sila pilih kawasan penghantaran anda</p>
                </div>
                <div className="space-y-3">
                    {zones.map(zone => (
                        <button
                            key={zone.id}
                            onClick={() => handleZoneSelect(zone)}
                            className="w-full p-4 border-2 border-gray-100 hover:border-orange-500 hover:bg-orange-50 rounded-xl transition text-left group"
                        >
                            <div className="flex justify-between items-center">
                                <div>
                                    <div className="font-semibold text-gray-900 group-hover:text-orange-700">{zone.zone_name}</div>
                                    <div className="text-sm text-gray-500">{zone.estimated_time_min}-{zone.estimated_time_max} min</div>
                                </div>
                                <div className="text-orange-600 font-bold">RM{zone.delivery_fee}</div>
                            </div>
                        </button>
                    ))}
                </div>
            </div>
        </div>
    );

    return (
        <div className="min-h-screen bg-gray-50 pb-24 lg:pb-0">
            {/* Header */}
            <div className="bg-white shadow-sm sticky top-0 z-30">
                <div className="max-w-7xl mx-auto px-4 py-4">
                    <div className="flex justify-between items-center">
                        <h1 className="text-xl font-bold text-gray-900">🛵 Pesan Delivery</h1>
                        {/* Area Indicator */}
                        <div className="hidden md:flex items-center gap-2 bg-green-50 px-3 py-1.5 rounded-full border border-green-100">
                            <Check size={16} className="text-green-600" />
                            <span className="text-sm font-medium text-green-800">Kawasan: {selectedZone.zone_name}</span>
                            <button 
                                onClick={() => setShowZoneSelector(true)} 
                                className="text-xs text-green-600 hover:underline ml-1"
                            >
                                Tukar
                            </button>
                        </div>
                    </div>
                </div>
                
                {/* Mobile Area Indicator */}
                <div className="md:hidden px-4 pb-3 border-b">
                    <div className="flex items-center justify-between bg-green-50 px-3 py-2 rounded-lg border border-green-100">
                        <div className="flex items-center gap-2">
                             <Check size={16} className="text-green-600" />
                             <span className="text-sm font-medium text-green-800 truncate max-w-[200px]">{selectedZone.zone_name}</span>
                        </div>
                        <button 
                            onClick={() => setShowZoneSelector(true)} 
                            className="text-xs text-green-600 font-medium px-2 py-1 hover:bg-green-100 rounded"
                        >
                            Tukar
                        </button>
                    </div>
                </div>

                {/* Categories */}
                <div className="border-t px-4 py-2 overflow-x-auto no-scrollbar">
                    <div className="flex gap-2 max-w-7xl mx-auto">
                        {categories.map(cat => (
                            <button
                                key={cat}
                                onClick={() => setSelectedCategory(cat)}
                                className={`px-4 py-1.5 rounded-full text-sm font-medium whitespace-nowrap transition ${
                                    selectedCategory === cat 
                                    ? 'bg-orange-500 text-white shadow-sm' 
                                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                                }`}
                            >
                                {cat}
                            </button>
                        ))}
                    </div>
                </div>
            </div>

            <main className="max-w-7xl mx-auto px-4 py-6">
                <div className="lg:grid lg:grid-cols-[1fr_380px] gap-8 items-start">
                    {/* Menu Grid */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {filteredItems.map(item => {
                            const inCart = cart.find(c => c.id === item.id);
                            return (
                                <div key={item.id} className="bg-white p-3 rounded-xl shadow-sm border border-gray-100 flex gap-4 hover:shadow-md transition">
                                    {item.image_url && (
                                        <div className="w-24 h-24 shrink-0 bg-gray-100 rounded-lg overflow-hidden">
                                            <img src={item.image_url} alt={item.name} className="w-full h-full object-cover" />
                                        </div>
                                    )}
                                    <div className="flex-1 flex flex-col justify-between">
                                        <div>
                                            <h3 className="font-semibold text-gray-900 line-clamp-1">{item.name}</h3>
                                            <p className="text-xs text-gray-500 line-clamp-2 mt-1">{item.description}</p>
                                        </div>
                                        <div className="flex justify-between items-end mt-3">
                                            <span className="font-bold text-orange-600">RM{item.price?.toFixed(2)}</span>
                                            {inCart ? (
                                                <div className="flex items-center gap-3 bg-gray-50 rounded-lg p-1 border">
                                                    <button onClick={() => updateQty(item.id, -1)} className="w-7 h-7 flex items-center justify-center bg-white rounded shadow-sm hover:text-red-500 transition"><Minus size={14} /></button>
                                                    <span className="font-bold text-sm w-4 text-center">{inCart.qty}</span>
                                                    <button onClick={() => updateQty(item.id, 1)} className="w-7 h-7 flex items-center justify-center bg-orange-500 text-white rounded shadow-sm hover:bg-orange-600 transition"><Plus size={14} /></button>
                                                </div>
                                            ) : (
                                                <button 
                                                    onClick={() => addToCart(item)}
                                                    className="bg-gray-900 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-gray-800 transition active:scale-95"
                                                >
                                                    Add
                                                </button>
                                            )}
                                        </div>
                                    </div>
                                </div>
                            );
                        })}
                        {filteredItems.length === 0 && (
                            <div className="col-span-full text-center py-12 text-gray-500">
                                Tiada item dalam kategori ini.
                            </div>
                        )}
                    </div>

                    {/* Desktop Cart (Sticky) */}
                    <div className="hidden lg:block sticky top-36 h-[calc(100vh-160px)] bg-white rounded-2xl shadow-lg border border-gray-100 overflow-hidden">
                        <CartContent />
                    </div>
                </div>
            </main>

            {/* Mobile Bottom Bar - Only show if cart has items */}
            <AnimatePresence>
                {cart.length > 0 && !isMobileCartOpen && (
                    <motion.div 
                        initial={{ y: 100 }}
                        animate={{ y: 0 }}
                        exit={{ y: 100 }}
                        className="fixed bottom-0 left-0 right-0 bg-white border-t shadow-[0_-4px_6px_-1px_rgba(0,0,0,0.1)] p-4 z-40 lg:hidden"
                    >
                        <div className="max-w-md mx-auto flex gap-4 items-center">
                            <div className="flex-1" onClick={() => setIsMobileCartOpen(true)}>
                                <div className="text-xs text-gray-500">{cart.reduce((s, i) => s + i.qty, 0)} items</div>
                                <div className="font-bold text-lg">RM{total.toFixed(2)}</div>
                            </div>
                            <button 
                                onClick={() => setIsMobileCartOpen(true)}
                                className="bg-orange-500 text-white px-6 py-3 rounded-xl font-bold text-sm flex items-center gap-2 shadow-orange-200 shadow-lg"
                            >
                                <ShoppingBag size={18} />
                                Lihat Bakul
                            </button>
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>

            {/* Mobile Cart Drawer/Modal */}
            <AnimatePresence>
                {isMobileCartOpen && (
                    <>
                        <motion.div
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 0.5 }}
                            exit={{ opacity: 0 }}
                            onClick={() => setIsMobileCartOpen(false)}
                            className="fixed inset-0 bg-black z-50 lg:hidden"
                        />
                        <motion.div
                            initial={{ y: '100%' }}
                            animate={{ y: 0 }}
                            exit={{ y: '100%' }}
                            transition={{ type: "spring", damping: 25, stiffness: 300 }}
                            className="fixed bottom-0 left-0 right-0 bg-white z-50 rounded-t-2xl h-[85vh] lg:hidden flex flex-col"
                        >
                            <div className="flex justify-center p-2" onClick={() => setIsMobileCartOpen(false)}>
                                <div className="w-12 h-1.5 bg-gray-300 rounded-full" />
                            </div>
                            <div className="flex-1 overflow-hidden relative">
                                <button 
                                    onClick={() => setIsMobileCartOpen(false)}
                                    className="absolute top-2 right-4 p-2 bg-gray-100 rounded-full z-10"
                                >
                                    <X size={20} />
                                </button>
                                <CartContent isMobile={true} />
                            </div>
                        </motion.div>
                    </>
                )}
            </AnimatePresence>
        </div>
    );
}
