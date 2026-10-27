'use client';

import { useState, useEffect } from 'react';
import { useParams, useRouter, useSearchParams } from 'next/navigation';
import BinaChat from '@/components/BinaChat';

/**
 * Customer Chat Page
 *
 * Allows customers to chat about their order
 * Accessed from delivery widget tracking view
 *
 * Route: /chat/[conversationId]?customer={customerId}&name={customerName}
 */
export default function CustomerChatPage() {
    const params = useParams();
    const router = useRouter();
    const searchParams = useSearchParams();

    const conversationId = params?.conversationId as string;
    const customerId = searchParams?.get('customer');
    const customerName = searchParams?.get('name') || 'Pelanggan';

    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        // Validate required parameters
        if (!conversationId) {
            setError('ID perbualan tidak sah');
            setIsLoading(false);
            return;
        }

        if (!customerId) {
            setError('ID pelanggan tidak sah');
            setIsLoading(false);
            return;
        }

        setIsLoading(false);
    }, [conversationId, customerId]);

    if (isLoading) {
        return (
            <div className="min-h-screen bg-gray-50 flex items-center justify-center">
                <div className="text-center">
                    <div className="animate-spin h-12 w-12 border-4 border-blue-500 border-t-transparent rounded-full mx-auto mb-4"></div>
                    <p className="text-gray-600">Memuatkan chat...</p>
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
                <div className="bg-white rounded-xl shadow-lg p-8 max-w-md w-full text-center">
                    <div className="text-5xl mb-4">❌</div>
                    <h1 className="text-xl font-bold mb-2">Ralat</h1>
                    <p className="text-gray-600">{error}</p>
                </div>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-gray-50">
            {/* Header */}
            <div className="bg-white shadow-sm border-b sticky top-0 z-10">
                <div className="max-w-4xl mx-auto px-4 py-3">
                    <div className="flex items-center gap-3">
                        <button
                            type="button"
                            onClick={() => {
                                // window.close() is ignored unless this tab was
                                // script-opened; fall back to navigating away.
                                window.close();
                                setTimeout(() => {
                                    if (window.closed) return;
                                    if (window.history.length > 1) router.back();
                                    else router.push('/');
                                }, 150);
                            }}
                            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
                            title="Tutup"
                        >
                            ✕
                        </button>
                        <div>
                            <h1 className="font-bold text-lg">💬 Chat BinaApp</h1>
                            <p className="text-xs text-gray-500">{customerName}</p>
                        </div>
                    </div>
                </div>
            </div>

            {/* Chat Component */}
            <div className="max-w-4xl mx-auto h-[calc(100vh-72px)]">
                <BinaChat
                    conversationId={conversationId}
                    userType="customer"
                    userId={customerId!}
                    userName={customerName}
                />
            </div>
        </div>
    );
}
