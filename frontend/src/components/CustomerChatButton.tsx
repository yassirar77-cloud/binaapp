'use client';

import React, { useState, useEffect } from 'react';
import BinaChat from './BinaChat';

// =====================================================
// TYPES
// =====================================================

interface CustomerChatButtonProps {
    orderId: string;
    websiteId: string;
    customerName: string;
    customerPhone: string;
}

// =====================================================
// COMPONENT
// =====================================================

export default function CustomerChatButton({
    orderId,
    websiteId,
    customerName,
    customerPhone
}: CustomerChatButtonProps) {
    const [isOpen, setIsOpen] = useState(false);
    const [conversationId, setConversationId] = useState<string | null>(null);
    const [customerId, setCustomerId] = useState<string | null>(null);
    const [isCreating, setIsCreating] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const API_URL = process.env.NEXT_PUBLIC_API_URL || 'https://binaapp-backend.onrender.com';

    // =====================================================
    // CHECK OR CREATE CONVERSATION
    // =====================================================

    const initConversation = async () => {
        if (conversationId) {
            setIsOpen(true);
            return;
        }

        try {
            setIsCreating(true);
            setError(null);

            // First check if conversation exists for this order
            const checkRes = await fetch(`${API_URL}/api/v1/chat/conversations/order/${orderId}`);
            const checkData = await checkRes.json();

            if (checkData.exists && checkData.conversation) {
                const existingConversation = checkData.conversation;
                const derivedCustomerId =
                    existingConversation.customer_id ||
                    (existingConversation.customer_phone
                        ? `customer_${existingConversation.customer_phone}`
                        : `customer_${customerPhone}`);
                setConversationId(existingConversation.id);
                setCustomerId(derivedCustomerId);
                setIsOpen(true);
                return;
            }

            // Create new conversation
            const createRes = await fetch(`${API_URL}/api/v1/chat/conversations/create`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    order_id: orderId,
                    website_id: websiteId,
                    customer_name: customerName,
                    customer_phone: customerPhone
                })
            });

            if (!createRes.ok) throw new Error('Failed to create conversation');

            const createData = await createRes.json();
            setConversationId(createData.conversation_id);
            setCustomerId(createData.customer_id || `customer_${customerPhone}`);
            setIsOpen(true);

        } catch (err) {
            console.error('[CustomerChat] Failed to init conversation:', err);
            setError('Gagal memulakan chat. Sila cuba lagi.');
        } finally {
            setIsCreating(false);
        }
    };

    // =====================================================
    // RENDER
    // =====================================================

    return (
        <>
            {/* Chat Button */}
            <button
                onClick={initConversation}
                disabled={isCreating}
                className="fixed bottom-4 right-4 z-40 bg-gradient-to-r from-orange-500 to-orange-600 hover:from-orange-600 hover:to-orange-700 disabled:from-gray-400 disabled:to-gray-500 text-white p-4 rounded-full shadow-xl transition-all duration-300 flex items-center gap-2"
            >
                {isCreating ? (
                    <div className="animate-spin w-6 h-6 border-2 border-white border-t-transparent rounded-full" />
                ) : (
                    <>
                        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                        </svg>
                        <span className="hidden md:inline font-medium">Chat Penjual</span>
                    </>
                )}
            </button>

            {/* Error Toast */}
            {error && (
                <div className="fixed bottom-20 right-4 z-50 bg-red-500 text-white px-4 py-2 rounded-lg shadow-lg flex items-center gap-2">
                    <span>{error}</span>
                    <button onClick={() => setError(null)} className="text-white/80 hover:text-white">
                        &times;
                    </button>
                </div>
            )}

            {/* Chat Modal */}
            {isOpen && conversationId && customerId && (
                <div className="fixed inset-0 z-50 flex items-end md:items-center justify-center bg-black/50">
                    <div className="w-full md:w-[420px] h-[85vh] md:h-[600px] md:max-h-[80vh] bg-white md:rounded-xl overflow-hidden shadow-2xl animate-slide-up">
                        <BinaChat
                            conversationId={conversationId}
                            userType="customer"
                            userId={customerId}
                            userName={customerName}
                            orderId={orderId}
                            showMap={true}
                            onClose={() => setIsOpen(false)}
                            className="h-full"
                        />
                    </div>
                </div>
            )}

            {/* Animation styles */}
            <style jsx global>{`
                @keyframes slide-up {
                    from {
                        transform: translateY(100%);
                        opacity: 0;
                    }
                    to {
                        transform: translateY(0);
                        opacity: 1;
                    }
                }
                .animate-slide-up {
                    animation: slide-up 0.3s ease-out;
                }
            `}</style>
        </>
    );
}
