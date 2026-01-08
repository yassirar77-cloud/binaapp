'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import ChatList from '@/components/ChatList';
import BinaChat from '@/components/BinaChat';

// =====================================================
// TYPES
// =====================================================

interface Website {
    id: string;
    business_name: string;
    subdomain: string;
}

// =====================================================
// CHAT DASHBOARD PAGE
// =====================================================

export default function ChatDashboardPage() {
    const router = useRouter();
    const [websites, setWebsites] = useState<Website[]>([]);
    const [selectedWebsiteId, setSelectedWebsiteId] = useState<string | null>(null);
    const [selectedConversationId, setSelectedConversationId] = useState<string | null>(null);
    const [selectedOrderId, setSelectedOrderId] = useState<string | undefined>(undefined);
    const [isLoading, setIsLoading] = useState(true);
    const [isMobileView, setIsMobileView] = useState(false);
    const [showChat, setShowChat] = useState(false);

    const API_URL = process.env.NEXT_PUBLIC_API_URL || 'https://binaapp-backend.onrender.com';

    // =====================================================
    // DETECT MOBILE VIEW
    // =====================================================

    useEffect(() => {
        const checkMobile = () => setIsMobileView(window.innerWidth < 768);
        checkMobile();
        window.addEventListener('resize', checkMobile);
        return () => window.removeEventListener('resize', checkMobile);
    }, []);

    // =====================================================
    // LOAD USER WEBSITES
    // =====================================================

    useEffect(() => {
        const loadWebsites = async () => {
            try {
                // Get user from localStorage or session
                const userStr = localStorage.getItem('binaapp_user');
                if (!userStr) {
                    router.push('/auth/login');
                    return;
                }

                const user = JSON.parse(userStr);
                const userId = user.id;

                // Fetch user's websites
                const res = await fetch(`${API_URL}/v1/websites/user/${userId}`);
                if (!res.ok) throw new Error('Failed to load websites');

                const data = await res.json();
                const websiteList = data.websites || [];

                setWebsites(websiteList);

                // Auto-select first website
                if (websiteList.length > 0 && !selectedWebsiteId) {
                    setSelectedWebsiteId(websiteList[0].id);
                }
            } catch (err) {
                console.error('[ChatDashboard] Failed to load websites:', err);
            } finally {
                setIsLoading(false);
            }
        };

        loadWebsites();
    }, [API_URL, router, selectedWebsiteId]);

    // =====================================================
    // HANDLERS
    // =====================================================

    const handleSelectConversation = (conversationId: string, orderId?: string) => {
        setSelectedConversationId(conversationId);
        setSelectedOrderId(orderId);
        if (isMobileView) {
            setShowChat(true);
        }
    };

    const handleBackToList = () => {
        setShowChat(false);
    };

    // =====================================================
    // RENDER LOADING STATE
    // =====================================================

    if (isLoading) {
        return (
            <div className="min-h-screen bg-gray-100 flex items-center justify-center">
                <div className="text-center">
                    <div className="animate-spin w-10 h-10 border-4 border-orange-500 border-t-transparent rounded-full mx-auto mb-4" />
                    <p className="text-gray-600">Memuatkan...</p>
                </div>
            </div>
        );
    }

    // =====================================================
    // RENDER NO WEBSITES STATE
    // =====================================================

    if (websites.length === 0) {
        return (
            <div className="min-h-screen bg-gray-100 flex items-center justify-center p-4">
                <div className="bg-white rounded-xl shadow-lg p-8 max-w-md text-center">
                    <div className="text-6xl mb-4">&#127978;</div>
                    <h2 className="text-xl font-bold text-gray-800 mb-2">Tiada Laman Web</h2>
                    <p className="text-gray-600 mb-6">
                        Anda perlu membuat laman web terlebih dahulu untuk menggunakan sistem chat.
                    </p>
                    <button
                        onClick={() => router.push('/dashboard')}
                        className="bg-orange-500 hover:bg-orange-600 text-white px-6 py-3 rounded-lg font-medium transition-colors"
                    >
                        Buat Laman Web
                    </button>
                </div>
            </div>
        );
    }

    // =====================================================
    // RENDER MOBILE VIEW
    // =====================================================

    if (isMobileView) {
        return (
            <div className="min-h-screen bg-gray-100">
                {/* Header */}
                <header className="bg-white border-b px-4 py-3 flex items-center justify-between sticky top-0 z-10">
                    {showChat ? (
                        <button
                            onClick={handleBackToList}
                            className="flex items-center gap-2 text-orange-600"
                        >
                            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                            </svg>
                            Kembali
                        </button>
                    ) : (
                        <h1 className="font-bold text-lg">Mesej</h1>
                    )}

                    {/* Website selector */}
                    {!showChat && websites.length > 1 && (
                        <select
                            value={selectedWebsiteId || ''}
                            onChange={(e) => {
                                setSelectedWebsiteId(e.target.value);
                                setSelectedConversationId(null);
                            }}
                            className="text-sm border rounded-lg px-2 py-1"
                        >
                            {websites.map(w => (
                                <option key={w.id} value={w.id}>
                                    {w.business_name}
                                </option>
                            ))}
                        </select>
                    )}
                </header>

                {/* Content */}
                <div className="h-[calc(100vh-57px)]">
                    {showChat && selectedConversationId && selectedWebsiteId ? (
                        <BinaChat
                            conversationId={selectedConversationId}
                            userType="owner"
                            userId={selectedWebsiteId}
                            userName="Pemilik Kedai"
                            orderId={selectedOrderId}
                            showMap={true}
                            className="h-full"
                        />
                    ) : selectedWebsiteId ? (
                        <ChatList
                            websiteId={selectedWebsiteId}
                            onSelectConversation={handleSelectConversation}
                            selectedConversationId={selectedConversationId || undefined}
                            className="h-full"
                        />
                    ) : null}
                </div>
            </div>
        );
    }

    // =====================================================
    // RENDER DESKTOP VIEW
    // =====================================================

    return (
        <div className="min-h-screen bg-gray-100">
            {/* Header */}
            <header className="bg-white border-b px-6 py-4 flex items-center justify-between">
                <div className="flex items-center gap-4">
                    <button
                        onClick={() => router.push('/dashboard')}
                        className="text-gray-500 hover:text-gray-700"
                    >
                        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                        </svg>
                    </button>
                    <h1 className="text-xl font-bold text-gray-800">Mesej Pelanggan</h1>
                </div>

                {/* Website selector */}
                {websites.length > 1 && (
                    <select
                        value={selectedWebsiteId || ''}
                        onChange={(e) => {
                            setSelectedWebsiteId(e.target.value);
                            setSelectedConversationId(null);
                        }}
                        className="border rounded-lg px-3 py-2"
                    >
                        {websites.map(w => (
                            <option key={w.id} value={w.id}>
                                {w.business_name}
                            </option>
                        ))}
                    </select>
                )}
            </header>

            {/* Main content */}
            <div className="flex h-[calc(100vh-73px)]">
                {/* Conversation list - left panel */}
                {selectedWebsiteId && (
                    <div className="w-80 border-r bg-white flex-shrink-0">
                        <ChatList
                            websiteId={selectedWebsiteId}
                            onSelectConversation={handleSelectConversation}
                            selectedConversationId={selectedConversationId || undefined}
                            className="h-full"
                        />
                    </div>
                )}

                {/* Chat area - right panel */}
                <div className="flex-1 bg-gray-50">
                    {selectedConversationId && selectedWebsiteId ? (
                        <BinaChat
                            conversationId={selectedConversationId}
                            userType="owner"
                            userId={selectedWebsiteId}
                            userName="Pemilik Kedai"
                            orderId={selectedOrderId}
                            showMap={true}
                            className="h-full"
                        />
                    ) : (
                        <div className="h-full flex items-center justify-center text-gray-500">
                            <div className="text-center">
                                <div className="text-6xl mb-4">&#128172;</div>
                                <p className="text-lg">Pilih perbualan untuk mula chat</p>
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
