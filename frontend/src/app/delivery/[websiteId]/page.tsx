'use client';
import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'https://binaapp-backend.onrender.com';
const WIDGET_URL = `${API_URL}/static/widgets/delivery-widget.js`;

/**
 * Delivery Page
 * 
 * This page serves as a host for the BinaApp Delivery Widget.
 * All cart, zone selection, and checkout logic is handled by the injected widget.
 * The widget is the single source of truth for delivery ordering.
 */
export default function DeliveryPage() {
    const { websiteId } = useParams();
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        if (!websiteId) return;

        // Inject the delivery widget script
        const script = document.createElement('script');
        script.src = WIDGET_URL;
        script.async = true;

        script.onload = () => {
            // Initialize the widget once the script is loaded
            if (typeof window !== 'undefined' && (window as any).BinaAppDelivery) {
                (window as any).BinaAppDelivery.init({
                    websiteId: websiteId,
                    apiUrl: `${API_URL}/v1`,
                    primaryColor: '#ea580c',
                    language: 'ms'
                });
                setLoading(false);
            } else {
                setError('Gagal memuatkan widget delivery');
                setLoading(false);
            }
        };

        script.onerror = () => {
            setError('Gagal memuatkan widget delivery');
            setLoading(false);
        };

        document.body.appendChild(script);

        // Cleanup on unmount
        return () => {
            // Remove the script
            if (script.parentNode) {
                script.parentNode.removeChild(script);
            }
            // Remove widget elements if they exist
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
                    <div className="w-16 h-16 border-4 border-orange-500 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
                    <p className="text-gray-600">Memuatkan delivery...</p>
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-gray-50">
                <div className="text-center">
                    <span className="text-5xl block mb-4">⚠️</span>
                    <p className="text-gray-800 font-medium">{error}</p>
                    <button 
                        onClick={() => window.location.reload()}
                        className="mt-4 px-6 py-2 bg-orange-500 text-white rounded-lg hover:bg-orange-600 transition-colors"
                    >
                        Cuba Semula
                    </button>
                </div>
            </div>
        );
    }

    // The page is now a minimal host - the widget handles everything
    return (
        <div className="min-h-screen bg-gray-100">
            {/* Header */}
            <header className="bg-gradient-to-r from-orange-500 to-orange-600 text-white py-6">
                <div className="max-w-3xl mx-auto px-4 text-center">
                    <span className="text-3xl mb-2 block">🛵</span>
                    <h1 className="text-2xl font-bold">Pesan Delivery</h1>
                    <p className="text-white/80 text-sm mt-1">
                        Klik butang &quot;Pesan Sekarang&quot; di bawah untuk mula
                    </p>
                </div>
            </header>

            {/* Instructions */}
            <main className="max-w-3xl mx-auto px-4 py-8">
                <div className="bg-white rounded-xl shadow-sm p-6 text-center">
                    <div className="text-6xl mb-4">🍽️</div>
                    <h2 className="text-xl font-semibold text-gray-800 mb-2">
                        Sedia untuk pesan?
                    </h2>
                    <p className="text-gray-600 mb-4">
                        Klik butang &quot;Pesan Sekarang&quot; di sudut kanan bawah untuk melihat menu dan membuat pesanan.
                    </p>
                    <div className="flex items-center justify-center gap-2 text-sm text-gray-500">
                        <span>👇</span>
                        <span>Butang order ada di bawah kanan</span>
                    </div>
                </div>

                {/* Features info */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-6">
                    <div className="bg-white rounded-xl p-4 text-center shadow-sm">
                        <span className="text-2xl block mb-2">📋</span>
                        <h3 className="font-medium text-gray-800">Menu Lengkap</h3>
                        <p className="text-sm text-gray-500">Lihat semua menu yang tersedia</p>
                    </div>
                    <div className="bg-white rounded-xl p-4 text-center shadow-sm">
                        <span className="text-2xl block mb-2">📍</span>
                        <h3 className="font-medium text-gray-800">Pilih Kawasan</h3>
                        <p className="text-sm text-gray-500">Pilih kawasan delivery anda</p>
                    </div>
                    <div className="bg-white rounded-xl p-4 text-center shadow-sm">
                        <span className="text-2xl block mb-2">✅</span>
                        <h3 className="font-medium text-gray-800">Checkout Mudah</h3>
                        <p className="text-sm text-gray-500">Proses pesanan yang cepat</p>
                    </div>
                </div>
            </main>

            {/* The BinaApp Delivery Widget will be injected here automatically */}
            {/* It provides the floating "Pesan Sekarang" button and handles all ordering */}
        </div>
    );
}
