'use client';
import { useEffect, useState, useRef } from 'react';
import { useParams } from 'next/navigation';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'https://binaapp-backend.onrender.com';
const WIDGET_URL = `${API_URL}/static/widgets/delivery-widget.js`;
const WIDGET_SCRIPT_ID = 'binaapp-delivery-widget-script';

/**
 * =============================================================================
 * DELIVERY PAGE - WIDGET HOST ONLY
 * =============================================================================
 * 
 * @deprecated PREVIOUS IMPLEMENTATION REMOVED
 * 
 * This page previously contained full delivery ordering logic including:
 * - Cart state management (cart, CartItem, addToCart, updateQty)
 * - Zone selection (zones, selectedZone, DeliveryZone)
 * - Customer info form (customerInfo state)
 * - Checkout flow (checkout function, WhatsApp integration)
 * - Menu display with category filtering
 * - Price calculations (subtotal, deliveryFee, total)
 * 
 * ALL OF THE ABOVE HAS BEEN REMOVED AND IS NOW DEPRECATED.
 * 
 * =============================================================================
 * DO NOT ADD CART, ZONE, OR CHECKOUT LOGIC TO THIS PAGE
 * =============================================================================
 * 
 * The BinaApp Delivery Widget is now the SINGLE SOURCE OF TRUTH for:
 * - Cart management
 * - Zone selection  
 * - Checkout flow
 * - Order submission
 * 
 * This page is now a minimal host that only:
 * 1. Injects the delivery widget script
 * 2. Initializes the widget with websiteId
 * 3. Provides fallback UI for errors/noscript
 * 
 * @see /frontend/public/widgets/delivery-widget.js - Widget source
 * @see /backend/static/widgets/delivery-widget.js - Backend widget copy
 * @see /WIDGET_INTEGRATION.md - Widget integration documentation
 * 
 * TODO: For widget customization or new features, modify the Delivery Widget
 *       directly. Do NOT re-implement ordering logic in this page.
 * 
 * TODO: See WIDGET_INTEGRATION.md for widget API documentation:
 *       - BinaAppDelivery.init(config)
 *       - Widget configuration options
 *       - Styling customization
 * 
 * =============================================================================
 */
export default function DeliveryPage() {
    const { websiteId } = useParams();
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const initAttempted = useRef(false);

    // =========================================================================
    // ⚠️  WARNING: DO NOT ADD STATE OR LOGIC BELOW THIS LINE
    // =========================================================================
    // 
    // The following are DEPRECATED and must NOT be re-added:
    // - const [cart, setCart] = useState([])           // ❌ DEPRECATED
    // - const [zones, setZones] = useState([])         // ❌ DEPRECATED  
    // - const [selectedZone, setSelectedZone] = ...    // ❌ DEPRECATED
    // - const [customerInfo, setCustomerInfo] = ...    // ❌ DEPRECATED
    // - const [menu, setMenu] = useState({})           // ❌ DEPRECATED
    // - function addToCart() {}                        // ❌ DEPRECATED
    // - function updateQty() {}                        // ❌ DEPRECATED
    // - function checkout() {}                         // ❌ DEPRECATED
    //
    // All ordering logic is handled by the Delivery Widget.
    // See file header comments for documentation.
    // =========================================================================

    useEffect(() => {
        if (!websiteId) return;

        // Prevent duplicate initialization
        if (initAttempted.current) {
            console.warn('[DeliveryPage] Widget initialization already attempted, skipping.');
            return;
        }
        initAttempted.current = true;

        // Check if script already exists (prevent duplicates)
        const existingScript = document.getElementById(WIDGET_SCRIPT_ID);
        if (existingScript) {
            console.warn('[DeliveryPage] Widget script already loaded, attempting re-init.');
            initializeWidget();
            return;
        }

        // Create and inject script
        const script = document.createElement('script');
        script.id = WIDGET_SCRIPT_ID;
        script.src = WIDGET_URL;
        script.async = true;

        script.onload = () => {
            console.log('[DeliveryPage] Widget script loaded successfully.');
            initializeWidget();
        };

        script.onerror = (e) => {
            console.error('[DeliveryPage] Failed to load widget script:', WIDGET_URL, e);
            setError('Gagal memuatkan widget delivery');
            setLoading(false);
        };

        document.body.appendChild(script);

        function initializeWidget() {
            try {
                // Safeguard: check if BinaAppDelivery exists
                if (typeof window === 'undefined') {
                    console.error('[DeliveryPage] Window is undefined (SSR context).');
                    setLoading(false);
                    return;
                }

                const BinaAppDelivery = (window as any).BinaAppDelivery;

                if (!BinaAppDelivery) {
                    console.error('[DeliveryPage] BinaAppDelivery is undefined. Widget failed to register.');
                    setError('Widget tidak tersedia');
                    setLoading(false);
                    return;
                }

                if (typeof BinaAppDelivery.init !== 'function') {
                    console.error('[DeliveryPage] BinaAppDelivery.init is not a function.');
                    setError('Widget tidak sah');
                    setLoading(false);
                    return;
                }

                // Initialize widget
                BinaAppDelivery.init({
                    websiteId: websiteId,
                    apiUrl: `${API_URL}/v1`,
                    primaryColor: '#ea580c',
                    language: 'ms'
                });

                console.log('[DeliveryPage] Widget initialized for websiteId:', websiteId);
                setLoading(false);

            } catch (err) {
                console.error('[DeliveryPage] Widget initialization error:', err);
                setError('Ralat semasa memulakan widget');
                setLoading(false);
            }
        }

        return () => {
            // Cleanup on unmount
            const scriptEl = document.getElementById(WIDGET_SCRIPT_ID);
            if (scriptEl?.parentNode) {
                scriptEl.parentNode.removeChild(scriptEl);
            }
            const widget = document.getElementById('binaapp-widget');
            const modal = document.getElementById('binaapp-modal');
            if (widget) widget.remove();
            if (modal) modal.remove();
        };
    }, [websiteId]);

    if (loading) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-gray-50">
                <div className="text-center">
                    <div className="w-12 h-12 border-4 border-orange-500 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
                    <p className="text-gray-600">Memuatkan...</p>
                </div>
                {/* noscript fallback */}
                <noscript>
                    <div className="fixed inset-0 bg-gray-50 flex items-center justify-center p-4 z-50">
                        <div className="bg-white rounded-xl shadow-lg p-6 max-w-sm text-center">
                            <span className="text-4xl block mb-4">📱</span>
                            <h2 className="text-lg font-bold mb-2">JavaScript Diperlukan</h2>
                            <p className="text-gray-600 mb-4">
                                Sila aktifkan JavaScript atau gunakan WhatsApp untuk memesan.
                            </p>
                            <a
                                href="https://wa.me/?text=Saya%20ingin%20membuat%20pesanan"
                                className="inline-block px-6 py-3 bg-green-500 text-white rounded-lg font-medium"
                            >
                                💬 Pesan via WhatsApp
                            </a>
                        </div>
                    </div>
                </noscript>
            </div>
        );
    }

    if (error) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-gray-50">
                <div className="text-center">
                    <p className="text-gray-800 mb-4">{error}</p>
                    <button 
                        onClick={() => window.location.reload()}
                        className="px-4 py-2 bg-orange-500 text-white rounded-lg mb-3"
                    >
                        Cuba Semula
                    </button>
                    <p className="text-sm text-gray-500">
                        Atau{' '}
                        <a 
                            href="https://wa.me/?text=Saya%20ingin%20membuat%20pesanan" 
                            className="text-green-600 underline"
                        >
                            pesan via WhatsApp
                        </a>
                    </p>
                </div>
            </div>
        );
    }

    // =========================================================================
    // MINIMAL UI ONLY - Widget handles all ordering functionality
    // =========================================================================
    // ⚠️  DO NOT ADD: menu grids, cart drawers, zone selectors, checkout forms
    //     All of these are provided by the injected Delivery Widget.
    // =========================================================================
    return (
        <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
            <div className="text-center">
                <p className="text-gray-700 text-lg">
                    Pesan makanan melalui butang <strong>&apos;Pesan Sekarang&apos;</strong> di penjuru skrin
                </p>
            </div>

            {/* noscript fallback for users without JavaScript */}
            <noscript>
                <div className="fixed inset-0 bg-gray-50 flex items-center justify-center p-4 z-50">
                    <div className="bg-white rounded-xl shadow-lg p-6 max-w-sm text-center">
                        <span className="text-4xl block mb-4">📱</span>
                        <h2 className="text-lg font-bold mb-2">JavaScript Diperlukan</h2>
                        <p className="text-gray-600 mb-4">
                            Sila aktifkan JavaScript atau gunakan WhatsApp untuk memesan.
                        </p>
                        <a
                            href="https://wa.me/?text=Saya%20ingin%20membuat%20pesanan"
                            className="inline-block px-6 py-3 bg-green-500 text-white rounded-lg font-medium"
                        >
                            💬 Pesan via WhatsApp
                        </a>
                    </div>
                </div>
            </noscript>

            {/* Widget injects floating button at bottom-right */}
        </div>
    );
}
