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
    const [step, setStep] = useState(1); // 1=zone, 2=menu, 3=checkout
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
        // Restore selected zone from localStorage (mobile-friendly persistence)
        if (typeof window === 'undefined') return;
        try {
            const raw = window.localStorage.getItem(storageKey);
            if (!raw) return;
            const parsed = JSON.parse(raw) as DeliveryZone;
            if (parsed?.id && parsed?.zone_name) {
                setSelectedZone(parsed);
                setStep(2);
                // Defer scroll until UI renders
                requestAnimationFrame(() => {
                    menuTopRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
                });
            }
        } catch {
            // ignore
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
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

    function onSelectZone(zone: DeliveryZone) {
        setSelectedZone(zone);
        setStep(2);
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
                <div className="max-w-6xl mx-auto">
                    <h1 className="text-2xl font-bold">🛵 Pesan Delivery</h1>
                    <p className="text-white/80 text-sm">Min. order: RM{minOrder} • Delivery: {settings?.delivery_hours || '11am-10pm'}</p>
                    {selectedZone?.zone_name && (
                        <div className="mt-2 text-sm">
                            <span className="font-semibold">✅ Kawasan dipilih:</span> {selectedZone.zone_name}
                        </div>
                    )}
                </div>
            </div>

            {/* Content */}
            <div
                className={[
                    'max-w-6xl mx-auto p-4',
                    cart.length > 0 ? 'pb-28 lg:pb-8' : 'pb-8',
                ].join(' ')}
            >
                {/* Step 1: Select Zone */}
                {step === 1 && (
                    <div className="bg-white rounded-2xl p-6 shadow-lg mb-6">
                        <h2 className="text-xl font-bold mb-4">📍 Pilih Kawasan Delivery</h2>
                        <div className="grid gap-3">
                            {zones.map((zone) => (
                                <button
                                    key={zone.id}
                                    onClick={() => onSelectZone(zone)}
                                    className="p-4 border-2 rounded-xl text-left hover:border-orange-500 hover:bg-orange-50 transition active:scale-[0.99]"
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
                    <div className="lg:grid lg:grid-cols-[minmax(0,1fr)_320px] lg:gap-6">
                        {/* Left: Menu */}
                        <div className="bg-white rounded-2xl p-6 shadow-lg mb-6 lg:mb-0">
                            <div ref={menuTopRef} className="scroll-mt-28" />
                            <div className="flex flex-col gap-3 mb-4">
                                <div className="flex justify-between items-center">
                                    <h2 className="text-xl font-bold">🍽️ Menu</h2>
                                    <button
                                        onClick={() => setStep(1)}
                                        className="text-orange-600 text-sm hover:underline"
                                    >
                                        ← Tukar kawasan
                                    </button>
                                </div>
                                <div className="text-sm text-green-700">
                                    <span className="font-semibold">✅ Kawasan dipilih:</span> {selectedZone?.zone_name}{' '}
                                    <span className="text-green-600">• RM{selectedZone?.delivery_fee ?? 0} delivery</span>
                                </div>
                            </div>

                            {/* Category filtering (works on all sizes) */}
                            {categories.length > 0 && (
                                <div className="mb-5">
                                    <div className="flex gap-2 overflow-x-auto pb-2 -mx-1 px-1">
                                        <button
                                            onClick={() => setSelectedCategoryId('all')}
                                            className={[
                                                'shrink-0 px-3 py-2 rounded-full text-sm border transition',
                                                selectedCategoryId === 'all'
                                                    ? 'bg-orange-500 text-white border-orange-500'
                                                    : 'bg-white text-gray-700 border-gray-200 hover:border-orange-300',
                                            ].join(' ')}
                                        >
                                            Semua
                                        </button>
                                        {categories.map((c) => (
                                            <button
                                                key={c.id}
                                                onClick={() => setSelectedCategoryId(c.id)}
                                                className={[
                                                    'shrink-0 px-3 py-2 rounded-full text-sm border transition',
                                                    selectedCategoryId === c.id
                                                        ? 'bg-orange-500 text-white border-orange-500'
                                                        : 'bg-white text-gray-700 border-gray-200 hover:border-orange-300',
                                                ].join(' ')}
                                            >
                                                {c.name}
                                            </button>
                                        ))}
                                    </div>
                                </div>
                            )}

                            {/* Responsive food cards */}
                            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                                {filteredItems?.map((item) => {
                                    const inCart = cart.find((c) => c.id === item.id);
                                    return (
                                        <div
                                            key={item.id}
                                            className={[
                                                'flex gap-4 p-4 bg-gray-50 rounded-2xl border border-gray-100 transition',
                                                flashItemId === item.id ? 'ring-2 ring-orange-300' : '',
                                            ].join(' ')}
                                        >
                                            {item.image_url ? (
                                                <img
                                                    src={item.image_url}
                                                    alt={item.name}
                                                    className="w-20 h-20 rounded-xl object-cover shrink-0"
                                                />
                                            ) : (
                                                <div className="w-20 h-20 rounded-xl bg-gradient-to-br from-orange-100 to-red-100 shrink-0" />
                                            )}
                                            <div className="flex-1 min-w-0">
                                                <h3 className="font-semibold leading-snug">{item.name}</h3>
                                                {item.description ? (
                                                    <p className="text-sm text-gray-500 line-clamp-2">{item.description}</p>
                                                ) : (
                                                    <p className="text-sm text-gray-400">—</p>
                                                )}
                                                <div className="flex justify-between items-center mt-3 gap-2">
                                                    <span className="font-bold text-orange-600">
                                                        RM{Number(item.price ?? 0).toFixed(2)}
                                                    </span>
                                                    {inCart ? (
                                                        <div className="flex items-center gap-2">
                                                            <button
                                                                onClick={() => updateQty(item.id, -1)}
                                                                className="w-9 h-9 bg-white border border-gray-200 rounded-full hover:border-orange-300 active:scale-[0.98]"
                                                                aria-label={`Kurangkan ${item.name}`}
                                                            >
                                                                −
                                                            </button>
                                                            <span className="font-bold w-6 text-center">{inCart.qty}</span>
                                                            <button
                                                                onClick={() => updateQty(item.id, 1)}
                                                                className="w-9 h-9 bg-orange-500 text-white rounded-full hover:bg-orange-600 active:scale-[0.98]"
                                                                aria-label={`Tambah ${item.name}`}
                                                            >
                                                                +
                                                            </button>
                                                        </div>
                                                    ) : (
                                                        <button
                                                            onClick={() => addToCart(item)}
                                                            className="bg-orange-500 text-white px-4 py-2 rounded-full text-sm font-semibold hover:bg-orange-600 active:scale-[0.99]"
                                                        >
                                                            + Tambah
                                                        </button>
                                                    )}
                                                </div>
                                            </div>
                                        </div>
                                    );
                                })}
                            </div>

                            {filteredItems?.length === 0 && (
                                <div className="text-center text-gray-500 py-10">Tiada item untuk kategori ini.</div>
                            )}
                        </div>

                        {/* Right: Desktop sticky cart (never overlaps menu) */}
                        <div className="hidden lg:block">
                            <div className="sticky top-28">
                                <div className="bg-white rounded-2xl shadow-lg border border-gray-100 overflow-hidden">
                                    <div className="p-5 border-b">
                                        <div className="flex items-center justify-between">
                                            <h3 className="text-lg font-bold">🧺 Bakul Pesanan</h3>
                                            <span className="text-sm text-gray-500">{itemCount} item</span>
                                        </div>
                                        {selectedZone?.zone_name && (
                                            <div className="mt-2 text-sm text-green-700">
                                                ✅ Kawasan dipilih: {selectedZone.zone_name}
                                            </div>
                                        )}
                                    </div>

                                    <div className="p-5 max-h-[calc(100vh-14rem)] overflow-y-auto">
                                        {cart.length === 0 ? (
                                            <div className="text-sm text-gray-500">Bakul kosong. Tambah item dari menu.</div>
                                        ) : (
                                            <div className="space-y-3">
                                                {cart.map((ci) => (
                                                    <div key={ci.id} className="flex items-start justify-between gap-3">
                                                        <div className="min-w-0">
                                                            <div className="font-semibold truncate">{ci.name}</div>
                                                            <div className="text-sm text-gray-500">
                                                                RM{Number(ci.price ?? 0).toFixed(2)}
                                                            </div>
                                                        </div>
                                                        <div className="flex items-center gap-2 shrink-0">
                                                            <button
                                                                onClick={() => updateQty(ci.id, -1)}
                                                                className="w-8 h-8 bg-gray-100 rounded-full hover:bg-gray-200"
                                                                aria-label={`Kurangkan ${ci.name}`}
                                                            >
                                                                −
                                                            </button>
                                                            <span className="font-bold w-6 text-center">{ci.qty}</span>
                                                            <button
                                                                onClick={() => updateQty(ci.id, 1)}
                                                                className="w-8 h-8 bg-orange-500 text-white rounded-full hover:bg-orange-600"
                                                                aria-label={`Tambah ${ci.name}`}
                                                            >
                                                                +
                                                            </button>
                                                        </div>
                                                    </div>
                                                ))}
                                            </div>
                                        )}

                                        {/* Totals */}
                                        <div className="mt-5 pt-4 border-t space-y-2 text-sm">
                                            <div className="flex justify-between">
                                                <span className="text-gray-600">Subtotal</span>
                                                <span className="font-semibold">RM{subtotal.toFixed(2)}</span>
                                            </div>
                                            <div className="flex justify-between">
                                                <span className="text-gray-600">Delivery</span>
                                                <span className="font-semibold">RM{deliveryFee.toFixed(2)}</span>
                                            </div>
                                            <div className="flex justify-between text-base">
                                                <span className="font-bold">Jumlah</span>
                                                <span className="font-bold">RM{total.toFixed(2)}</span>
                                            </div>
                                            {subtotal < minOrder && (
                                                <div className="text-red-600">
                                                    Minimum order: RM{Number(minOrder).toFixed(0)}
                                                </div>
                                            )}
                                        </div>

                                        {/* Customer info */}
                                        {cart.length > 0 && (
                                            <div className="mt-5 pt-4 border-t">
                                                <h4 className="font-bold mb-3">📝 Maklumat Penghantaran</h4>
                                                <div className="space-y-3">
                                                    <input
                                                        type="text"
                                                        placeholder="Nama penuh"
                                                        value={customerInfo.name}
                                                        onChange={(e) => setCustomerInfo({ ...customerInfo, name: e.target.value })}
                                                        className="w-full p-3 border rounded-xl"
                                                    />
                                                    <input
                                                        type="tel"
                                                        placeholder="Nombor telefon"
                                                        value={customerInfo.phone}
                                                        onChange={(e) => setCustomerInfo({ ...customerInfo, phone: e.target.value })}
                                                        className="w-full p-3 border rounded-xl"
                                                    />
                                                    <textarea
                                                        placeholder="Alamat penuh"
                                                        value={customerInfo.address}
                                                        onChange={(e) => setCustomerInfo({ ...customerInfo, address: e.target.value })}
                                                        className="w-full p-3 border rounded-xl"
                                                        rows={2}
                                                    />
                                                    <input
                                                        type="text"
                                                        placeholder="Nota tambahan (optional)"
                                                        value={customerInfo.notes}
                                                        onChange={(e) => setCustomerInfo({ ...customerInfo, notes: e.target.value })}
                                                        className="w-full p-3 border rounded-xl"
                                                    />
                                                </div>
                                                <button
                                                    onClick={checkout}
                                                    disabled={subtotal < minOrder}
                                                    className="mt-4 w-full bg-green-600 hover:bg-green-700 disabled:bg-gray-300 text-white font-bold py-3 rounded-xl flex items-center justify-center gap-2"
                                                >
                                                    <span>📱</span> WhatsApp Pesanan
                                                </button>
                                            </div>
                                        )}
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                )}

            </div>

            {/* MOBILE: Sticky bottom cart bar (only when items exist) */}
            {cart.length > 0 && (
                <div className="fixed bottom-0 left-0 right-0 bg-white border-t shadow-2xl p-4 z-50 lg:hidden">
                    <div className="max-w-6xl mx-auto">
                        <button
                            onClick={() => setIsCartOpen(true)}
                            className="w-full flex items-center justify-between gap-3"
                            aria-label="Buka bakul pesanan"
                        >
                            <div className="text-left">
                                <div className="font-bold">🧺 Bakul Pesanan</div>
                                <div className="text-sm text-gray-600">
                                    {itemCount} item • <span className="font-semibold">RM{total.toFixed(2)}</span>
                                    {subtotal < minOrder && (
                                        <span className="text-red-600"> • Min. RM{Number(minOrder).toFixed(0)}</span>
                                    )}
                                </div>
                            </div>
                            <div className="shrink-0 bg-orange-500 text-white px-4 py-2 rounded-full font-semibold">
                                Lihat
                            </div>
                        </button>
                    </div>
                </div>
            )}

            {/* MOBILE: Bottom drawer cart */}
            {isCartOpen && (
                <div className="fixed inset-0 z-[60] lg:hidden" role="dialog" aria-modal="true">
                    <button
                        className="absolute inset-0 bg-black/40"
                        onClick={() => setIsCartOpen(false)}
                        aria-label="Tutup bakul"
                    />
                    <div className="absolute left-0 right-0 bottom-0 bg-white rounded-t-3xl shadow-2xl max-h-[85vh] overflow-hidden">
                        <div className="p-5 border-b flex items-center justify-between">
                            <div>
                                <div className="text-lg font-bold">🧺 Bakul Pesanan</div>
                                {selectedZone?.zone_name && (
                                    <div className="text-sm text-green-700">✅ Kawasan dipilih: {selectedZone.zone_name}</div>
                                )}
                            </div>
                            <button
                                onClick={() => setIsCartOpen(false)}
                                className="text-gray-600 px-3 py-2 rounded-full hover:bg-gray-100"
                            >
                                Tutup
                            </button>
                        </div>

                        <div className="p-5 overflow-y-auto max-h-[calc(85vh-9rem)]">
                            <div className="space-y-3">
                                {cart.map((ci) => (
                                    <div key={ci.id} className="flex items-start justify-between gap-3">
                                        <div className="min-w-0">
                                            <div className="font-semibold truncate">{ci.name}</div>
                                            <div className="text-sm text-gray-500">RM{Number(ci.price ?? 0).toFixed(2)}</div>
                                        </div>
                                        <div className="flex items-center gap-2 shrink-0">
                                            <button
                                                onClick={() => updateQty(ci.id, -1)}
                                                className="w-9 h-9 bg-gray-100 rounded-full hover:bg-gray-200"
                                                aria-label={`Kurangkan ${ci.name}`}
                                            >
                                                −
                                            </button>
                                            <span className="font-bold w-6 text-center">{ci.qty}</span>
                                            <button
                                                onClick={() => updateQty(ci.id, 1)}
                                                className="w-9 h-9 bg-orange-500 text-white rounded-full hover:bg-orange-600"
                                                aria-label={`Tambah ${ci.name}`}
                                            >
                                                +
                                            </button>
                                        </div>
                                    </div>
                                ))}
                            </div>

                            <div className="mt-5 pt-4 border-t space-y-2 text-sm">
                                <div className="flex justify-between">
                                    <span className="text-gray-600">Subtotal</span>
                                    <span className="font-semibold">RM{subtotal.toFixed(2)}</span>
                                </div>
                                <div className="flex justify-between">
                                    <span className="text-gray-600">Delivery</span>
                                    <span className="font-semibold">RM{deliveryFee.toFixed(2)}</span>
                                </div>
                                <div className="flex justify-between text-base">
                                    <span className="font-bold">Jumlah</span>
                                    <span className="font-bold">RM{total.toFixed(2)}</span>
                                </div>
                                {subtotal < minOrder && (
                                    <div className="text-red-600">Minimum order: RM{Number(minOrder).toFixed(0)}</div>
                                )}
                            </div>

                            <div className="mt-5 pt-4 border-t">
                                <h4 className="font-bold mb-3">📝 Maklumat Penghantaran</h4>
                                <div className="space-y-3">
                                    <input
                                        type="text"
                                        placeholder="Nama penuh"
                                        value={customerInfo.name}
                                        onChange={(e) => setCustomerInfo({ ...customerInfo, name: e.target.value })}
                                        className="w-full p-3 border rounded-xl"
                                    />
                                    <input
                                        type="tel"
                                        placeholder="Nombor telefon"
                                        value={customerInfo.phone}
                                        onChange={(e) => setCustomerInfo({ ...customerInfo, phone: e.target.value })}
                                        className="w-full p-3 border rounded-xl"
                                    />
                                    <textarea
                                        placeholder="Alamat penuh"
                                        value={customerInfo.address}
                                        onChange={(e) => setCustomerInfo({ ...customerInfo, address: e.target.value })}
                                        className="w-full p-3 border rounded-xl"
                                        rows={2}
                                    />
                                    <input
                                        type="text"
                                        placeholder="Nota tambahan (optional)"
                                        value={customerInfo.notes}
                                        onChange={(e) => setCustomerInfo({ ...customerInfo, notes: e.target.value })}
                                        className="w-full p-3 border rounded-xl"
                                    />
                                </div>

                                <button
                                    onClick={checkout}
                                    disabled={subtotal < minOrder}
                                    className="mt-4 w-full bg-green-600 hover:bg-green-700 disabled:bg-gray-300 text-white font-bold py-4 rounded-xl flex items-center justify-center gap-2"
                                >
                                    <span>📱</span> WhatsApp Pesanan
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
