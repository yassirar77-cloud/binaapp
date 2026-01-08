'use client';

import React, { useState, useEffect, useRef, useCallback } from 'react';
import BinaChat from './BinaChat';

// =====================================================
// TYPES
// =====================================================

interface RiderChatProps {
    orderId: string;
    riderId: string;
    riderName: string;
    onClose?: () => void;
}

// =====================================================
// COMPONENT
// =====================================================

export default function RiderChat({
    orderId,
    riderId,
    riderName,
    onClose
}: RiderChatProps) {
    const [conversationId, setConversationId] = useState<string | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [locationEnabled, setLocationEnabled] = useState(false);
    const [sharingLocation, setSharingLocation] = useState(false);

    const locationIntervalRef = useRef<NodeJS.Timeout | null>(null);
    const wsRef = useRef<WebSocket | null>(null);

    const API_URL = process.env.NEXT_PUBLIC_API_URL || 'https://binaapp-backend.onrender.com';
    const WS_URL = API_URL.replace('https://', 'wss://').replace('http://', 'ws://');

    // =====================================================
    // LOAD CONVERSATION
    // =====================================================

    useEffect(() => {
        const loadConversation = async () => {
            try {
                const res = await fetch(`${API_URL}/v1/chat/conversations/order/${orderId}`);
                const data = await res.json();

                if (data.exists && data.conversation) {
                    setConversationId(data.conversation.id);
                } else {
                    setError('Tiada chat untuk pesanan ini');
                }
            } catch (err) {
                console.error('[RiderChat] Failed to load conversation:', err);
                setError('Gagal memuatkan chat');
            } finally {
                setIsLoading(false);
            }
        };

        loadConversation();
    }, [API_URL, orderId]);

    // =====================================================
    // LOCATION SHARING
    // =====================================================

    const startLocationSharing = useCallback(() => {
        if (!conversationId) return;

        if (!navigator.geolocation) {
            setError('GPS tidak tersedia pada peranti ini');
            return;
        }

        setSharingLocation(true);

        // Send location every 10 seconds
        const sendLocation = () => {
            navigator.geolocation.getCurrentPosition(
                async (position) => {
                    const { latitude, longitude, accuracy, heading, speed } = position.coords;

                    try {
                        // Send to API
                        await fetch(`${API_URL}/v1/chat/rider/update-location`, {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({
                                rider_id: riderId,
                                order_id: orderId,
                                latitude,
                                longitude,
                                accuracy,
                                heading,
                                speed
                            })
                        });
                    } catch (err) {
                        console.error('[RiderChat] Failed to send location:', err);
                    }
                },
                (err) => {
                    console.error('[RiderChat] Geolocation error:', err);
                    if (err.code === 1) {
                        setError('Sila benarkan akses lokasi');
                        setSharingLocation(false);
                    }
                },
                {
                    enableHighAccuracy: true,
                    timeout: 5000,
                    maximumAge: 0
                }
            );
        };

        // Send immediately
        sendLocation();

        // Then every 10 seconds
        locationIntervalRef.current = setInterval(sendLocation, 10000);
    }, [API_URL, conversationId, orderId, riderId]);

    const stopLocationSharing = useCallback(() => {
        if (locationIntervalRef.current) {
            clearInterval(locationIntervalRef.current);
            locationIntervalRef.current = null;
        }
        setSharingLocation(false);
    }, []);

    // Check location permission on mount
    useEffect(() => {
        navigator.permissions?.query({ name: 'geolocation' }).then((result) => {
            setLocationEnabled(result.state === 'granted');
        });
    }, []);

    // Cleanup on unmount
    useEffect(() => {
        return () => {
            stopLocationSharing();
        };
    }, [stopLocationSharing]);

    // =====================================================
    // RENDER
    // =====================================================

    if (isLoading) {
        return (
            <div className="h-full flex items-center justify-center bg-gray-100">
                <div className="text-center">
                    <div className="animate-spin w-10 h-10 border-4 border-orange-500 border-t-transparent rounded-full mx-auto mb-4" />
                    <p className="text-gray-600">Memuatkan chat...</p>
                </div>
            </div>
        );
    }

    if (error || !conversationId) {
        return (
            <div className="h-full flex items-center justify-center bg-gray-100 p-4">
                <div className="bg-white rounded-xl shadow-lg p-6 text-center max-w-sm">
                    <div className="text-4xl mb-4">&#128533;</div>
                    <p className="text-gray-700 mb-4">{error || 'Chat tidak tersedia'}</p>
                    {onClose && (
                        <button
                            onClick={onClose}
                            className="bg-orange-500 text-white px-6 py-2 rounded-lg"
                        >
                            Kembali
                        </button>
                    )}
                </div>
            </div>
        );
    }

    return (
        <div className="h-full flex flex-col">
            {/* Location sharing bar */}
            <div className="bg-blue-600 text-white px-4 py-2 flex items-center justify-between">
                <div className="flex items-center gap-2 text-sm">
                    <span>&#128205;</span>
                    <span>Kongsi Lokasi:</span>
                </div>
                <button
                    onClick={sharingLocation ? stopLocationSharing : startLocationSharing}
                    className={`px-4 py-1.5 rounded-full text-sm font-medium transition-colors ${
                        sharingLocation
                            ? 'bg-red-500 hover:bg-red-600'
                            : 'bg-green-500 hover:bg-green-600'
                    }`}
                >
                    {sharingLocation ? (
                        <>
                            <span className="animate-pulse mr-1">&#9679;</span>
                            Berhenti
                        </>
                    ) : (
                        'Mula Kongsi'
                    )}
                </button>
            </div>

            {/* Chat component */}
            <div className="flex-1">
                <BinaChat
                    conversationId={conversationId}
                    userType="rider"
                    userId={riderId}
                    userName={riderName}
                    orderId={orderId}
                    showMap={true}
                    onClose={onClose}
                    className="h-full"
                />
            </div>
        </div>
    );
}
