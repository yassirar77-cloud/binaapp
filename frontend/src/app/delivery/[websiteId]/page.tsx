'use client';
import { useState, useEffect } from 'react';
import { useParams } from 'next/navigation';

const API_URL = 'https://binaapp-backend.onrender.com';

export default function DeliveryPage() {
    const { websiteId } = useParams();
    const [loading, setLoading] = useState(true);
    const [menu, setMenu] = useState({ categories: [], items: [] });
    const [zones, setZones] = useState([]);
    const [settings, setSettings] = useState(null);
    const [cart, setCart] = useState([]);
    const [selectedZone, setSelectedZone] = useState(null);
    const [step, setStep] = useState(1); // 1=zone, 2=menu, 3=checkout
    const [customerInfo, setCustomerInfo] = useState({ name: '', phone: '', address: '', notes: '' });

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

    if (loading) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-gray-100">
                <div className="text-center">
                    <div className="w-16 h-16 border-4 border-orange-500 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
                    <p className="text-gray-600">Memuatkan menu...</p>
                </div>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-gray-100">
            {/* Header */}
            <div className="bg-gradient-to-r from-orange-500 to-red-500 text-white py-6 px-4 sticky top-0 z-40">
                <div className="max-w-4xl mx-auto">
                    <h1 className="text-2xl font-bold">🛵 Pesan Delivery</h1>
                    <p className="text-white/80 text-sm">Min. order: RM{minOrder} • Delivery: {settings?.delivery_hours || '11am-10pm'}</p>
                </div>
            </div>

            <div className="max-w-4xl mx-auto p-4">
                {/* Step 1: Select Zone */}
                {step === 1 && (
                    <div className="bg-white rounded-2xl p-6 shadow-lg mb-6">
                        <h2 className="text-xl font-bold mb-4">📍 Pilih Kawasan Delivery</h2>
                        <div className="grid gap-3">
                            {zones.map(zone => (
                                <button
                                    key={zone.id}
                                    onClick={() => { setSelectedZone(zone); setStep(2); }}
                                    className="p-4 border-2 rounded-xl text-left hover:border-orange-500 hover:bg-orange-50 transition"
                                >
                                    <div className="flex justify-between items-center">
                                        <div>
                                            <div className="font-semibold">{zone.zone_name}</div>
                                            <div className="text-sm text-gray-500">{zone.estimated_time_min}-{zone.estimated_time_max} min</div>
                                        </div>
                                        <div className="text-orange-600 font-bold">RM{zone.delivery_fee}</div>
                                    </div>
                                </button>
                            ))}
                        </div>
                    </div>
                )}

                {/* Step 2: Menu */}
                {step >= 2 && (
                    <div className="bg-white rounded-2xl p-6 shadow-lg mb-6">
                        <div className="flex justify-between items-center mb-4">
                            <h2 className="text-xl font-bold">🍽️ Menu</h2>
                            <button onClick={() => setStep(1)} className="text-orange-600 text-sm">← Tukar kawasan</button>
                        </div>
                        <p className="text-sm text-green-600 mb-4">✓ {selectedZone?.zone_name} - RM{selectedZone?.delivery_fee} delivery</p>

                        <div className="grid gap-4">
                            {menu.items?.map(item => {
                                const inCart = cart.find(c => c.id === item.id);
                                return (
                                    <div key={item.id} className="flex gap-4 p-3 bg-gray-50 rounded-xl">
                                        {item.image_url && (
                                            <img src={item.image_url} alt={item.name} className="w-20 h-20 rounded-lg object-cover" />
                                        )}
                                        <div className="flex-1">
                                            <h3 className="font-semibold">{item.name}</h3>
                                            <p className="text-sm text-gray-500">{item.description}</p>
                                            <div className="flex justify-between items-center mt-2">
                                                <span className="font-bold text-orange-600">RM{item.price?.toFixed(2)}</span>
                                                {inCart ? (
                                                    <div className="flex items-center gap-2">
                                                        <button onClick={() => updateQty(item.id, -1)} className="w-8 h-8 bg-gray-200 rounded-full">-</button>
                                                        <span className="font-bold">{inCart.qty}</span>
                                                        <button onClick={() => updateQty(item.id, 1)} className="w-8 h-8 bg-orange-500 text-white rounded-full">+</button>
                                                    </div>
                                                ) : (
                                                    <button onClick={() => addToCart(item)} className="bg-orange-500 text-white px-4 py-2 rounded-full text-sm">+ Tambah</button>
                                                )}
                                            </div>
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    </div>
                )}

                {/* Step 3: Checkout */}
                {step >= 2 && cart.length > 0 && (
                    <div className="bg-white rounded-2xl p-6 shadow-lg mb-6">
                        <h2 className="text-xl font-bold mb-4">📝 Maklumat Penghantaran</h2>
                        <div className="space-y-4">
                            <input
                                type="text"
                                placeholder="Nama penuh"
                                value={customerInfo.name}
                                onChange={e => setCustomerInfo({...customerInfo, name: e.target.value})}
                                className="w-full p-3 border rounded-xl"
                            />
                            <input
                                type="tel"
                                placeholder="Nombor telefon"
                                value={customerInfo.phone}
                                onChange={e => setCustomerInfo({...customerInfo, phone: e.target.value})}
                                className="w-full p-3 border rounded-xl"
                            />
                            <textarea
                                placeholder="Alamat penuh"
                                value={customerInfo.address}
                                onChange={e => setCustomerInfo({...customerInfo, address: e.target.value})}
                                className="w-full p-3 border rounded-xl"
                                rows={2}
                            />
                            <input
                                type="text"
                                placeholder="Nota tambahan (optional)"
                                value={customerInfo.notes}
                                onChange={e => setCustomerInfo({...customerInfo, notes: e.target.value})}
                                className="w-full p-3 border rounded-xl"
                            />
                        </div>
                    </div>
                )}
            </div>

            {/* Floating Cart */}
            {cart.length > 0 && (
                <div className="fixed bottom-0 left-0 right-0 bg-white border-t shadow-2xl p-4 z-50">
                    <div className="max-w-4xl mx-auto">
                        <div className="flex justify-between items-center mb-3">
                            <div>
                                <span className="text-gray-600">{cart.reduce((sum, i) => sum + i.qty, 0)} item</span>
                                <span className="font-bold text-lg ml-2">RM{total.toFixed(2)}</span>
                            </div>
                            <div className="text-sm text-gray-500">
                                {subtotal < minOrder && <span className="text-red-500">Min. RM{minOrder}</span>}
                            </div>
                        </div>
                        <button
                            onClick={checkout}
                            disabled={subtotal < minOrder}
                            className="w-full bg-green-600 hover:bg-green-700 disabled:bg-gray-300 text-white font-bold py-4 rounded-xl flex items-center justify-center gap-2"
                        >
                            <span>📱</span> WhatsApp Pesanan
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
}
