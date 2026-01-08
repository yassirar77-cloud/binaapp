'use client';

import React, { useState, useEffect, useRef, useCallback } from 'react';

// Type declarations for Leaflet
declare global {
    interface Window {
        L: any;
    }
}

// =====================================================
// TYPES
// =====================================================

interface Message {
    id: string;
    conversation_id: string;
    sender_type: 'customer' | 'owner' | 'rider' | 'system';
    sender_id?: string;
    sender_name?: string;
    message_type: 'text' | 'image' | 'location' | 'payment' | 'status' | 'voice';
    content: string;
    media_url?: string;
    metadata?: Record<string, any>;
    created_at: string;
    is_read: boolean;
}

interface Conversation {
    id: string;
    order_id?: string;
    website_id: string;
    customer_id: string;
    customer_name?: string;
    customer_phone?: string;
    status: 'active' | 'closed' | 'archived';
    unread_owner: number;
    unread_customer: number;
    unread_rider: number;
    created_at: string;
    updated_at: string;
}

interface Participant {
    id: string;
    conversation_id: string;
    user_type: 'customer' | 'owner' | 'rider';
    user_id?: string;
    user_name?: string;
    is_online: boolean;
    last_seen?: string;
}

interface RiderLocation {
    latitude: number;
    longitude: number;
    heading?: number;
    speed?: number;
    timestamp: string;
}

interface BinaChatProps {
    conversationId: string;
    userType: 'customer' | 'owner' | 'rider';
    userId: string;
    userName: string;
    orderId?: string;
    showMap?: boolean;
    onClose?: () => void;
    className?: string;
}

// =====================================================
// COMPONENT
// =====================================================

export default function BinaChat({
    conversationId,
    userType,
    userId,
    userName,
    orderId,
    showMap = true,
    onClose,
    className = ''
}: BinaChatProps) {
    // State
    const [messages, setMessages] = useState<Message[]>([]);
    const [inputText, setInputText] = useState('');
    const [isTyping, setIsTyping] = useState<Record<string, boolean>>({});
    const [riderLocation, setRiderLocation] = useState<RiderLocation | null>(null);
    const [isConnected, setIsConnected] = useState(false);
    const [isLoading, setIsLoading] = useState(true);
    const [showAttachments, setShowAttachments] = useState(false);
    const [participants, setParticipants] = useState<Participant[]>([]);
    const [error, setError] = useState<string | null>(null);
    const [mapExpanded, setMapExpanded] = useState(false);

    // Refs
    const wsRef = useRef<WebSocket | null>(null);
    const messagesEndRef = useRef<HTMLDivElement>(null);
    const mapRef = useRef<any>(null);
    const mapContainerRef = useRef<HTMLDivElement>(null);
    const riderMarkerRef = useRef<any>(null);
    const fileInputRef = useRef<HTMLInputElement>(null);
    const paymentInputRef = useRef<HTMLInputElement>(null);
    const typingTimeoutRef = useRef<NodeJS.Timeout | null>(null);
    const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);

    // API URL
    const API_URL = process.env.NEXT_PUBLIC_API_URL || 'https://binaapp-backend.onrender.com';
    const WS_URL = API_URL.replace('https://', 'wss://').replace('http://', 'ws://');

    // =====================================================
    // LOAD INITIAL DATA
    // =====================================================

    const loadMessages = useCallback(async () => {
        try {
            setIsLoading(true);
            const res = await fetch(`${API_URL}/v1/chat/conversations/${conversationId}`);
            if (!res.ok) throw new Error('Failed to load messages');

            const data = await res.json();
            setMessages(data.messages || []);
            setParticipants(data.participants || []);
            setError(null);
        } catch (err) {
            console.error('[BinaChat] Failed to load messages:', err);
            setError('Gagal memuatkan mesej. Sila cuba lagi.');
        } finally {
            setIsLoading(false);
        }
    }, [API_URL, conversationId]);

    // =====================================================
    // WEBSOCKET CONNECTION
    // =====================================================

    const connectWebSocket = useCallback(() => {
        if (wsRef.current?.readyState === WebSocket.OPEN) return;

        const ws = new WebSocket(`${WS_URL}/v1/chat/ws/${conversationId}/${userType}/${userId}`);

        ws.onopen = () => {
            console.log('[BinaChat] Connected');
            setIsConnected(true);
            setError(null);
        };

        ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);

                switch (data.type) {
                    case 'new_message':
                        setMessages(prev => [...prev, data.message]);
                        // Mark as read if we're receiving
                        if (data.message.sender_type !== userType) {
                            ws.send(JSON.stringify({ type: 'read' }));
                        }
                        break;

                    case 'typing':
                        setIsTyping(prev => ({
                            ...prev,
                            [data.user_type]: data.is_typing
                        }));
                        break;

                    case 'rider_location':
                        setRiderLocation({
                            latitude: data.data.latitude,
                            longitude: data.data.longitude,
                            heading: data.data.heading,
                            speed: data.data.speed,
                            timestamp: data.data.timestamp
                        });
                        break;

                    case 'messages_read':
                        setMessages(prev => prev.map(m => ({
                            ...m,
                            is_read: m.sender_type === userType ? true : m.is_read
                        })));
                        break;

                    case 'user_joined':
                    case 'user_left':
                        // Could update participants here
                        break;

                    case 'rider_assigned':
                        // Reload participants
                        loadMessages();
                        break;

                    case 'pong':
                        // Keep-alive response
                        break;
                }
            } catch (err) {
                console.error('[BinaChat] Failed to parse message:', err);
            }
        };

        ws.onclose = () => {
            console.log('[BinaChat] Disconnected');
            setIsConnected(false);

            // Reconnect after 3 seconds
            reconnectTimeoutRef.current = setTimeout(() => {
                console.log('[BinaChat] Reconnecting...');
                connectWebSocket();
            }, 3000);
        };

        ws.onerror = (err) => {
            console.error('[BinaChat] WebSocket error:', err);
        };

        wsRef.current = ws;
    }, [WS_URL, conversationId, userType, userId, loadMessages]);

    // =====================================================
    // MAP INITIALIZATION
    // =====================================================

    const initMap = useCallback(async () => {
        if (!showMap || !mapContainerRef.current) return;

        // Load Leaflet if not already loaded
        if (!window.L) {
            // Load CSS
            const link = document.createElement('link');
            link.rel = 'stylesheet';
            link.href = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css';
            document.head.appendChild(link);

            // Load JS
            await new Promise<void>((resolve) => {
                const script = document.createElement('script');
                script.src = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js';
                script.onload = () => resolve();
                document.head.appendChild(script);
            });
        }

        // Wait a bit for Leaflet to initialize
        await new Promise(resolve => setTimeout(resolve, 100));

        if (mapRef.current) {
            mapRef.current.remove();
        }

        // Initialize map (centered on Penang by default)
        mapRef.current = window.L.map(mapContainerRef.current).setView([5.4164, 100.3327], 14);

        window.L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '&copy; OpenStreetMap'
        }).addTo(mapRef.current);
    }, [showMap]);

    // =====================================================
    // UPDATE RIDER MARKER
    // =====================================================

    const updateRiderMarker = useCallback((lat: number, lng: number) => {
        if (!mapRef.current || !window.L) return;

        if (riderMarkerRef.current) {
            riderMarkerRef.current.setLatLng([lat, lng]);
        } else {
            const riderIcon = window.L.divIcon({
                html: `<div style="
                    background: linear-gradient(135deg, #ea580c 0%, #f97316 100%);
                    width: 40px;
                    height: 40px;
                    border-radius: 50%;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    color: white;
                    font-size: 20px;
                    border: 3px solid white;
                    box-shadow: 0 4px 15px rgba(234, 88, 12, 0.4);
                ">
                    <span style="filter: drop-shadow(0 1px 2px rgba(0,0,0,0.3));">&#128757;</span>
                </div>`,
                iconSize: [40, 40],
                iconAnchor: [20, 20],
                className: 'rider-marker'
            });

            riderMarkerRef.current = window.L.marker([lat, lng], { icon: riderIcon }).addTo(mapRef.current);
        }

        mapRef.current.setView([lat, lng], 15);
    }, []);

    // =====================================================
    // EFFECTS
    // =====================================================

    useEffect(() => {
        loadMessages();
        connectWebSocket();

        return () => {
            if (wsRef.current) {
                wsRef.current.close();
            }
            if (reconnectTimeoutRef.current) {
                clearTimeout(reconnectTimeoutRef.current);
            }
            if (typingTimeoutRef.current) {
                clearTimeout(typingTimeoutRef.current);
            }
        };
    }, [loadMessages, connectWebSocket]);

    useEffect(() => {
        if (showMap) {
            initMap();
        }
        return () => {
            if (mapRef.current) {
                mapRef.current.remove();
                mapRef.current = null;
            }
        };
    }, [showMap, initMap]);

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    useEffect(() => {
        if (riderLocation && mapRef.current) {
            updateRiderMarker(riderLocation.latitude, riderLocation.longitude);
        }
    }, [riderLocation, updateRiderMarker]);

    // Keep-alive ping every 30 seconds
    useEffect(() => {
        const pingInterval = setInterval(() => {
            if (wsRef.current?.readyState === WebSocket.OPEN) {
                wsRef.current.send(JSON.stringify({ type: 'ping' }));
            }
        }, 30000);

        return () => clearInterval(pingInterval);
    }, []);

    // =====================================================
    // SEND MESSAGE
    // =====================================================

    const sendMessage = (type: string = 'text', content: string, mediaUrl?: string, metadata?: Record<string, any>) => {
        if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
            setError('Tidak disambungkan. Sila tunggu...');
            return;
        }

        if (!content.trim() && !mediaUrl) return;

        wsRef.current.send(JSON.stringify({
            type: 'message',
            sender_name: userName,
            message_type: type,
            content: content,
            media_url: mediaUrl,
            metadata: metadata
        }));

        setInputText('');
        handleTyping(false);
    };

    // =====================================================
    // TYPING INDICATOR
    // =====================================================

    const handleTyping = (typing: boolean) => {
        if (wsRef.current?.readyState === WebSocket.OPEN) {
            wsRef.current.send(JSON.stringify({
                type: 'typing',
                is_typing: typing
            }));
        }
    };

    const onInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        setInputText(e.target.value);

        // Debounce typing indicator
        handleTyping(true);

        if (typingTimeoutRef.current) {
            clearTimeout(typingTimeoutRef.current);
        }

        typingTimeoutRef.current = setTimeout(() => {
            handleTyping(false);
        }, 2000);
    };

    // =====================================================
    // FILE UPLOAD
    // =====================================================

    const uploadImage = async (file: File, isPayment: boolean = false) => {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('conversation_id', conversationId);
        formData.append('sender_type', userType);
        formData.append('sender_id', userId);
        formData.append('sender_name', userName);

        if (isPayment && orderId) {
            formData.append('order_id', orderId);
            formData.append('amount', '0');
        }

        const endpoint = isPayment
            ? '/v1/chat/messages/upload-payment'
            : '/v1/chat/messages/upload-image';

        try {
            const res = await fetch(`${API_URL}${endpoint}`, {
                method: 'POST',
                body: formData
            });

            if (!res.ok) throw new Error('Upload failed');

            setShowAttachments(false);
        } catch (err) {
            console.error('[BinaChat] Upload failed:', err);
            setError('Gagal memuat naik. Sila cuba lagi.');
        }
    };

    const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>, isPayment: boolean) => {
        const file = e.target.files?.[0];
        if (file) {
            uploadImage(file, isPayment);
        }
        e.target.value = ''; // Reset input
    };

    // =====================================================
    // RENDER MESSAGE
    // =====================================================

    const renderMessage = (msg: Message) => {
        const isOwn = msg.sender_type === userType;
        const isSystem = msg.sender_type === 'system';

        if (isSystem) {
            return (
                <div key={msg.id} className="text-center my-3">
                    <span className="bg-gray-200 text-gray-600 text-xs px-4 py-1.5 rounded-full inline-block">
                        {msg.content}
                    </span>
                </div>
            );
        }

        const senderIcon = msg.sender_type === 'rider' ? '&#128757;' : msg.sender_type === 'owner' ? '&#127978;' : '&#128100;';

        return (
            <div key={msg.id} className={`flex ${isOwn ? 'justify-end' : 'justify-start'} mb-3`}>
                <div className={`max-w-[80%] ${isOwn ? 'order-2' : ''}`}>
                    {!isOwn && (
                        <div className="text-xs text-gray-500 mb-1 ml-2 flex items-center gap-1">
                            <span dangerouslySetInnerHTML={{ __html: senderIcon }} />
                            {msg.sender_name}
                        </div>
                    )}
                    <div className={`rounded-2xl px-4 py-2.5 ${
                        isOwn
                            ? 'bg-orange-500 text-white rounded-br-sm'
                            : 'bg-white text-gray-800 rounded-bl-sm shadow-sm border border-gray-100'
                    }`}>
                        {/* Image message */}
                        {msg.message_type === 'image' && msg.media_url && (
                            <img
                                src={msg.media_url}
                                alt="Gambar"
                                className="rounded-lg max-w-full mb-2 cursor-pointer hover:opacity-90 transition-opacity"
                                onClick={() => window.open(msg.media_url, '_blank')}
                            />
                        )}

                        {/* Payment proof */}
                        {msg.message_type === 'payment' && (
                            <div className={`border-2 rounded-lg p-2 mb-2 ${
                                msg.metadata?.status === 'verified'
                                    ? 'border-green-400 bg-green-50'
                                    : 'border-yellow-400 bg-yellow-50'
                            }`}>
                                <div className={`text-xs font-bold mb-1 ${
                                    msg.metadata?.status === 'verified' ? 'text-green-600' : 'text-yellow-700'
                                }`}>
                                    &#128179; Bukti Pembayaran
                                </div>
                                {msg.media_url && (
                                    <img
                                        src={msg.media_url}
                                        alt="Bukti Pembayaran"
                                        className="rounded-lg max-w-full cursor-pointer"
                                        onClick={() => window.open(msg.media_url, '_blank')}
                                    />
                                )}
                                {msg.metadata?.status === 'pending_verification' && (
                                    <div className="text-xs text-yellow-700 mt-2 flex items-center gap-1">
                                        <span className="animate-pulse">&#9202;</span> Menunggu pengesahan
                                    </div>
                                )}
                                {msg.metadata?.status === 'verified' && (
                                    <div className="text-xs text-green-600 mt-2">&#9989; Disahkan</div>
                                )}
                            </div>
                        )}

                        {/* Location message */}
                        {msg.message_type === 'location' && msg.metadata && (
                            <div
                                className="bg-blue-50 rounded-lg p-3 mb-2 cursor-pointer hover:bg-blue-100 transition-colors"
                                onClick={() => {
                                    if (mapRef.current) {
                                        mapRef.current.setView([msg.metadata.lat, msg.metadata.lng], 16);
                                        setMapExpanded(true);
                                    }
                                }}
                            >
                                <div className="text-sm font-semibold text-blue-600">&#128205; Lokasi Dikongsi</div>
                                <div className="text-xs text-gray-500">Tap untuk lihat di peta</div>
                            </div>
                        )}

                        {/* Text content */}
                        {msg.content && msg.message_type !== 'payment' && (
                            <div className="text-sm whitespace-pre-wrap">{msg.content}</div>
                        )}
                    </div>

                    <div className={`text-[10px] text-gray-400 mt-1 ${isOwn ? 'text-right mr-2' : 'ml-2'}`}>
                        {new Date(msg.created_at).toLocaleTimeString('ms-MY', {
                            hour: '2-digit',
                            minute: '2-digit'
                        })}
                        {isOwn && msg.is_read && (
                            <span className="ml-1 text-blue-500">&#10003;&#10003;</span>
                        )}
                    </div>
                </div>
            </div>
        );
    };

    // =====================================================
    // RENDER TYPING INDICATOR
    // =====================================================

    const renderTypingIndicator = () => {
        const typingUsers = Object.entries(isTyping).filter(([type, typing]) => typing && type !== userType);
        if (typingUsers.length === 0) return null;

        return (
            <div className="flex items-center text-gray-500 text-sm mb-2 ml-2">
                <div className="flex space-x-1 mr-2">
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                </div>
                Sedang menaip...
            </div>
        );
    };

    // =====================================================
    // RENDER
    // =====================================================

    return (
        <div className={`flex flex-col h-full bg-gray-100 ${className}`}>
            {/* Header */}
            <div className="bg-gradient-to-r from-orange-500 to-orange-600 text-white px-4 py-3 flex items-center justify-between shadow-sm">
                <div className="flex items-center gap-3">
                    <div className="w-10 h-10 bg-white/20 rounded-full flex items-center justify-center text-xl">
                        &#128172;
                    </div>
                    <div>
                        <div className="font-bold text-sm">BinaApp Chat</div>
                        <div className="text-xs opacity-80 flex items-center gap-1">
                            {isConnected ? (
                                <>
                                    <span className="w-2 h-2 bg-green-400 rounded-full" />
                                    Dalam talian
                                </>
                            ) : (
                                <>
                                    <span className="w-2 h-2 bg-red-400 rounded-full animate-pulse" />
                                    Menyambung...
                                </>
                            )}
                        </div>
                    </div>
                </div>
                <div className="flex items-center gap-2">
                    {orderId && (
                        <div className="text-xs bg-white/20 px-2 py-1 rounded">
                            #{orderId.slice(-6)}
                        </div>
                    )}
                    {onClose && (
                        <button
                            onClick={onClose}
                            className="p-1 hover:bg-white/20 rounded transition-colors"
                        >
                            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                            </svg>
                        </button>
                    )}
                </div>
            </div>

            {/* Map (collapsible) */}
            {showMap && (
                <div className={`bg-white border-b transition-all duration-300 ${mapExpanded ? 'h-64' : 'h-32'}`}>
                    <div
                        ref={mapContainerRef}
                        className="w-full h-full"
                        style={{ minHeight: mapExpanded ? '256px' : '128px' }}
                    />
                    <div className="absolute bottom-2 left-2 right-2 flex justify-between items-center px-2">
                        {riderLocation && (
                            <div className="text-xs text-gray-600 bg-white/90 px-2 py-1 rounded shadow">
                                &#128757; Rider sedang dalam perjalanan
                            </div>
                        )}
                        <button
                            onClick={() => setMapExpanded(!mapExpanded)}
                            className="text-xs text-orange-600 bg-white/90 px-2 py-1 rounded shadow"
                        >
                            {mapExpanded ? 'Kecilkan' : 'Besarkan'}
                        </button>
                    </div>
                </div>
            )}

            {/* Error Banner */}
            {error && (
                <div className="bg-red-100 text-red-700 text-sm px-4 py-2 flex items-center justify-between">
                    <span>{error}</span>
                    <button onClick={() => setError(null)} className="text-red-500 hover:text-red-700">
                        &times;
                    </button>
                </div>
            )}

            {/* Messages */}
            <div className="flex-1 overflow-y-auto p-4">
                {isLoading ? (
                    <div className="flex items-center justify-center h-full">
                        <div className="text-center text-gray-500">
                            <div className="animate-spin w-8 h-8 border-4 border-orange-500 border-t-transparent rounded-full mx-auto mb-2" />
                            <div className="text-sm">Memuatkan mesej...</div>
                        </div>
                    </div>
                ) : messages.length === 0 ? (
                    <div className="flex items-center justify-center h-full">
                        <div className="text-center text-gray-500">
                            <div className="text-4xl mb-2">&#128172;</div>
                            <div className="text-sm">Tiada mesej lagi. Mulakan perbualan!</div>
                        </div>
                    </div>
                ) : (
                    <>
                        {messages.map(renderMessage)}
                        {renderTypingIndicator()}
                    </>
                )}
                <div ref={messagesEndRef} />
            </div>

            {/* Input area */}
            <div className="bg-white border-t p-3 safe-area-bottom">
                {/* Attachment options */}
                {showAttachments && (
                    <div className="flex space-x-2 mb-3">
                        <label className="flex-1 bg-blue-50 text-blue-600 py-2.5 px-4 rounded-xl text-center cursor-pointer hover:bg-blue-100 transition-colors text-sm font-medium">
                            &#128247; Gambar
                            <input
                                ref={fileInputRef}
                                type="file"
                                accept="image/*"
                                className="hidden"
                                onChange={(e) => handleFileSelect(e, false)}
                            />
                        </label>
                        {userType === 'customer' && (
                            <label className="flex-1 bg-green-50 text-green-600 py-2.5 px-4 rounded-xl text-center cursor-pointer hover:bg-green-100 transition-colors text-sm font-medium">
                                &#128179; Bukti Bayar
                                <input
                                    ref={paymentInputRef}
                                    type="file"
                                    accept="image/*"
                                    className="hidden"
                                    onChange={(e) => handleFileSelect(e, true)}
                                />
                            </label>
                        )}
                        <button
                            className="px-3 text-gray-400 hover:text-gray-600 transition-colors"
                            onClick={() => setShowAttachments(false)}
                        >
                            &times;
                        </button>
                    </div>
                )}

                <div className="flex items-center space-x-2">
                    <button
                        className="text-xl text-gray-400 hover:text-orange-500 transition-colors p-2"
                        onClick={() => setShowAttachments(!showAttachments)}
                    >
                        &#128206;
                    </button>

                    <input
                        type="text"
                        value={inputText}
                        onChange={onInputChange}
                        onKeyPress={(e) => {
                            if (e.key === 'Enter' && !e.shiftKey) {
                                e.preventDefault();
                                sendMessage('text', inputText);
                            }
                        }}
                        placeholder="Taip mesej..."
                        className="flex-1 bg-gray-100 rounded-full px-4 py-2.5 focus:outline-none focus:ring-2 focus:ring-orange-300 text-sm"
                    />

                    <button
                        onClick={() => sendMessage('text', inputText)}
                        disabled={!inputText.trim() || !isConnected}
                        className="bg-orange-500 hover:bg-orange-600 disabled:bg-gray-300 disabled:cursor-not-allowed text-white rounded-full w-10 h-10 flex items-center justify-center transition-colors shadow-sm"
                    >
                        <svg className="w-5 h-5 transform rotate-90" fill="currentColor" viewBox="0 0 24 24">
                            <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z" />
                        </svg>
                    </button>
                </div>
            </div>
        </div>
    );
}
