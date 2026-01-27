'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { getConversations, type Conversation } from '@/lib/chatApi';

// =====================================================
// TYPES
// =====================================================

interface ChatListProps {
    websiteId?: string; // Single website ID (deprecated - use websiteIds instead)
    websiteIds?: string[]; // Multiple website IDs for filtering
    onSelectConversation: (conversationId: string, orderId?: string) => void;
    selectedConversationId?: string;
    className?: string;
}

// =====================================================
// COMPONENT
// =====================================================

export default function ChatList({
    websiteId,
    websiteIds,
    onSelectConversation,
    selectedConversationId,
    className = ''
}: ChatListProps) {
    const [conversations, setConversations] = useState<Conversation[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [filter, setFilter] = useState<'all' | 'active' | 'closed'>('all');

    // =====================================================
    // LOAD CONVERSATIONS
    // =====================================================

    const loadConversations = useCallback(async () => {
        try {
            setIsLoading(true);

            // Determine which website IDs to filter by
            let idsToFilter: string[] = [];
            if (websiteIds && websiteIds.length > 0) {
                idsToFilter = websiteIds;
            } else if (websiteId) {
                idsToFilter = [websiteId];
            }

            console.log('[ChatList] Loading conversations for website IDs:', idsToFilter);

            // Use chatApi with proper token handling
            const data = await getConversations(idsToFilter.length > 0 ? idsToFilter : undefined);
            const conversationsData = data.conversations || [];
            setConversations(conversationsData);
            setError(null);
        } catch (err: any) {
            console.error('[ChatList] Failed to load:', err);
            if (err.message?.includes('Sesi tamat') || err.message?.includes('401')) {
                setError('Sesi tamat. Sila log masuk semula.');
            } else {
                setError('Gagal memuatkan perbualan');
            }
        } finally {
            setIsLoading(false);
        }
    }, [websiteId, websiteIds]);

    useEffect(() => {
        loadConversations();

        // Refresh every 30 seconds
        const interval = setInterval(loadConversations, 30000);
        return () => clearInterval(interval);
    }, [loadConversations]);

    // =====================================================
    // FILTER CONVERSATIONS
    // =====================================================

    const filteredConversations = conversations.filter(conv => {
        if (filter === 'all') return true;
        return conv.status === filter;
    });

    // =====================================================
    // FORMAT TIME
    // =====================================================

    const formatTime = (dateString: string) => {
        const date = new Date(dateString);
        const now = new Date();
        const diffMs = now.getTime() - date.getTime();
        const diffMins = Math.floor(diffMs / 60000);
        const diffHours = Math.floor(diffMs / 3600000);
        const diffDays = Math.floor(diffMs / 86400000);

        if (diffMins < 1) return 'Baru';
        if (diffMins < 60) return `${diffMins}m`;
        if (diffHours < 24) return `${diffHours}j`;
        if (diffDays < 7) return `${diffDays}h`;

        return date.toLocaleDateString('ms-MY', {
            day: 'numeric',
            month: 'short'
        });
    };

    // =====================================================
    // RENDER CONVERSATION ITEM
    // =====================================================

    const renderConversation = (conv: Conversation) => {
        const isSelected = conv.id === selectedConversationId;
        const lastMessage = conv.chat_messages?.[conv.chat_messages.length - 1];
        const hasUnread = conv.unread_owner > 0;
        const lastMessageText =
            lastMessage?.message_text || lastMessage?.content || lastMessage?.message || 'Tiada mesej';

        return (
            <div
                key={conv.id}
                onClick={() => onSelectConversation(conv.id, conv.order_id)}
                className={`p-3 border-b cursor-pointer transition-colors ${
                    isSelected
                        ? 'bg-orange-50 border-l-4 border-l-orange-500'
                        : 'hover:bg-gray-50 border-l-4 border-l-transparent'
                }`}
            >
                <div className="flex items-start gap-3">
                    {/* Avatar */}
                    <div className={`w-10 h-10 rounded-full flex items-center justify-center text-white font-semibold ${
                        hasUnread ? 'bg-orange-500' : 'bg-gray-400'
                    }`}>
                        {conv.customer_name?.charAt(0).toUpperCase() || '?'}
                    </div>

                    {/* Content */}
                    <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between mb-0.5">
                            <div className="font-medium text-sm truncate">
                                {conv.customer_name || 'Pelanggan'}
                            </div>
                            <div className="text-xs text-gray-400 flex-shrink-0 ml-2">
                                {formatTime(conv.updated_at)}
                            </div>
                        </div>

                        <div className="flex items-center justify-between">
                            <div className="text-xs text-gray-500 truncate flex-1">
                                {lastMessage ? (
                                    <>
                                        {lastMessage.sender_type === 'owner' && (
                                            <span className="text-gray-400">Anda: </span>
                                        )}
                                        {lastMessageText}
                                    </>
                                ) : (
                                    'Tiada mesej'
                                )}
                            </div>

                            {/* Badges */}
                            <div className="flex items-center gap-1.5 ml-2">
                                {hasUnread && (
                                    <span className="bg-orange-500 text-white text-[10px] font-bold w-5 h-5 rounded-full flex items-center justify-center">
                                        {conv.unread_owner > 9 ? '9+' : conv.unread_owner}
                                    </span>
                                )}
                                {conv.order_id && (
                                    <span className="bg-blue-100 text-blue-600 text-[10px] px-1.5 py-0.5 rounded">
                                        #{conv.order_id.slice(-4)}
                                    </span>
                                )}
                            </div>
                        </div>

                        {/* Status badge */}
                        {conv.status === 'closed' && (
                            <div className="mt-1">
                                <span className="text-[10px] bg-gray-100 text-gray-500 px-1.5 py-0.5 rounded">
                                    Ditutup
                                </span>
                            </div>
                        )}
                    </div>
                </div>
            </div>
        );
    };

    // =====================================================
    // RENDER
    // =====================================================

    return (
        <div className={`flex flex-col h-full bg-white ${className}`}>
            {/* Header */}
            <div className="p-4 border-b bg-gradient-to-r from-orange-500 to-orange-600 text-white">
                <div className="flex items-center justify-between mb-3">
                    <h2 className="font-bold text-lg">Mesej</h2>
                    <button
                        onClick={loadConversations}
                        className="p-1.5 hover:bg-white/20 rounded-full transition-colors"
                        title="Muat semula"
                    >
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                        </svg>
                    </button>
                </div>

                {/* Filter tabs */}
                <div className="flex gap-1 bg-white/20 rounded-lg p-1">
                    {(['all', 'active', 'closed'] as const).map(f => (
                        <button
                            key={f}
                            onClick={() => setFilter(f)}
                            className={`flex-1 py-1.5 px-3 rounded-md text-xs font-medium transition-colors ${
                                filter === f
                                    ? 'bg-white text-orange-600'
                                    : 'text-white/80 hover:text-white'
                            }`}
                        >
                            {f === 'all' ? 'Semua' : f === 'active' ? 'Aktif' : 'Ditutup'}
                        </button>
                    ))}
                </div>
            </div>

            {/* Conversations list */}
            <div className="flex-1 overflow-y-auto">
                {isLoading ? (
                    <div className="flex items-center justify-center h-32">
                        <div className="animate-spin w-6 h-6 border-3 border-orange-500 border-t-transparent rounded-full" />
                    </div>
                ) : error ? (
                    <div className="p-4 text-center text-red-500 text-sm">
                        {error}
                        <button
                            onClick={loadConversations}
                            className="block mx-auto mt-2 text-orange-500 underline"
                        >
                            Cuba lagi
                        </button>
                    </div>
                ) : filteredConversations.length === 0 ? (
                    <div className="p-8 text-center text-gray-500">
                        <div className="text-4xl mb-2">&#128172;</div>
                        <div className="text-sm font-medium">
                            {filter === 'all'
                                ? 'Tiada perbualan lagi'
                                : filter === 'active'
                                ? 'Tiada perbualan aktif'
                                : 'Tiada perbualan ditutup'}
                        </div>
                        {filter === 'all' && (
                            <div className="text-xs text-gray-400 mt-2">
                                Pelanggan boleh chat melalui butang di website anda
                            </div>
                        )}
                    </div>
                ) : (
                    filteredConversations.map(renderConversation)
                )}
            </div>

            {/* Summary footer */}
            <div className="p-3 border-t bg-gray-50 text-xs text-gray-500 flex items-center justify-between">
                <span>{filteredConversations.length} perbualan</span>
                <span>
                    {conversations.reduce((sum, c) => sum + c.unread_owner, 0)} belum dibaca
                </span>
            </div>
        </div>
    );
}
