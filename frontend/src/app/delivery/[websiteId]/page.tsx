'use client';
import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'https://binaapp-backend.onrender.com';
const WIDGET_URL = `${API_URL}/static/widgets/delivery-widget.js`;

/**
 * Delivery Page
 * 
 * Minimal host for the BinaApp Delivery Widget.
 * The widget is the single source of truth for all ordering:
 * - Cart management
 * - Zone selection  
 * - Checkout flow
 */
export default function DeliveryPage() {
    const { websiteId } = useParams();
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        if (!websiteId) return;

        const script = document.createElement('script');
        script.src = WIDGET_URL;
        script.async = true;

        script.onload = () => {
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

        return () => {
            if (script.parentNode) {
                script.parentNode.removeChild(script);
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
                        className="px-4 py-2 bg-orange-500 text-white rounded-lg"
                    >
                        Cuba Semula
                    </button>
                </div>
            </div>
        );
    }

    // Minimal UI - widget handles everything
    return (
        <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
            <div className="text-center">
                <p className="text-gray-700 text-lg">
                    Pesan makanan melalui butang <strong>&apos;Pesan Sekarang&apos;</strong> di penjuru skrin
                </p>
            </div>
            {/* Widget injects floating button at bottom-right */}
        </div>
    );
}
