'use client';

import { useState, useRef, useEffect } from 'react';
import { usePathname } from 'next/navigation';

interface Message {
    role: 'user' | 'assistant';
    content: string;
}

// Routes where BinaBot should NOT appear (customer-facing pages with their own chat)
const HIDDEN_ROUTES = ['/delivery'];

export default function ChatWidget() {
    const pathname = usePathname();
    const [isOpen, setIsOpen] = useState(false);
    const [messages, setMessages] = useState<Message[]>([
        {
            role: 'assistant',
            content: 'Hai! 👋 Saya BinaBot. Bagaimana saya boleh bantu anda hari ini?'
        }
    ]);
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);
    const messagesEndRef = useRef<HTMLDivElement>(null);

    // Don't render on customer-facing routes that have their own chat widget
    const shouldHide = HIDDEN_ROUTES.some(route => pathname?.startsWith(route));

    if (shouldHide) {
        return null;
    }

    // Auto scroll to bottom
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    const sendMessage = async () => {
        if (!input.trim() || loading) return;

        const userMessage = input.trim();
        setInput('');

        // Add user message
        setMessages(prev => [...prev, { role: 'user', content: userMessage }]);
        setLoading(true);

        try {
            const res = await fetch('/backend/api/chat/support', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    message: userMessage,
                    history: messages.slice(-10) // Last 10 messages
                })
            });

            const data = await res.json();

            setMessages(prev => [...prev, {
                role: 'assistant',
                content: data.reply || 'Maaf, saya tidak dapat memproses. Sila hubungi WhatsApp.'
            }]);
        } catch (error) {
            console.error('Chat error:', error);
            setMessages(prev => [...prev, {
                role: 'assistant',
                content: 'Maaf, berlaku ralat sambungan. Sila cuba lagi.'
            }]);
        }

        setLoading(false);
    };

    return (
        <>
            {/* Chat Button - Smaller on mobile */}
            <button
                onClick={() => setIsOpen(!isOpen)}
                className="fixed bottom-4 right-4 z-50 bg-blue-600 hover:bg-blue-700 text-white p-3 md:p-4 rounded-full shadow-xl transition-all duration-300"
                aria-label="Chat Support"
            >
                {isOpen ? (
                    <svg className="w-5 h-5 md:w-6 md:h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                ) : (
                    <svg className="w-5 h-5 md:w-6 md:h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                    </svg>
                )}
            </button>

            {/* Chat Window - RESPONSIVE SIZE */}
            {isOpen && (
                <div className="fixed bottom-16 right-2 md:bottom-24 md:right-6 z-50
                    w-[calc(100vw-16px)] max-w-[320px] md:max-w-[380px]
                    h-[60vh] max-h-[450px] md:max-h-[500px]
                    bg-white rounded-2xl shadow-2xl flex flex-col overflow-hidden border border-gray-200">

                    {/* Header - Smaller on mobile */}
                    <div className="bg-blue-600 text-white p-3 md:p-4 flex items-center gap-2 md:gap-3">
                        <div className="w-8 h-8 md:w-10 md:h-10 bg-white/20 rounded-full flex items-center justify-center text-sm md:text-base">
                            🤖
                        </div>
                        <div>
                            <h3 className="font-bold text-sm md:text-base">BinaBot</h3>
                            <p className="text-[10px] md:text-xs text-blue-100">Sokongan Pelanggan</p>
                        </div>
                        {/* Close button for mobile */}
                        <button
                            onClick={() => setIsOpen(false)}
                            className="ml-auto md:hidden p-1"
                        >
                            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                            </svg>
                        </button>
                    </div>

                    {/* Messages - Smaller text on mobile */}
                    <div className="flex-1 overflow-y-auto p-3 md:p-4 space-y-3 bg-gray-50">
                        {messages.map((msg, i) => (
                            <div
                                key={i}
                                className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                            >
                                <div
                                    className={`max-w-[85%] p-2 md:p-3 rounded-2xl ${
                                        msg.role === 'user'
                                            ? 'bg-blue-600 text-white rounded-br-md'
                                            : 'bg-white text-gray-800 rounded-bl-md shadow-sm border'
                                    }`}
                                >
                                    <p className="text-xs md:text-sm whitespace-pre-wrap">{msg.content}</p>
                                </div>
                            </div>
                        ))}

                        {loading && (
                            <div className="flex justify-start">
                                <div className="bg-white p-2 md:p-3 rounded-2xl rounded-bl-md shadow-sm border">
                                    <div className="flex gap-1">
                                        <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></span>
                                        <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{animationDelay: '0.1s'}}></span>
                                        <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{animationDelay: '0.2s'}}></span>
                                    </div>
                                </div>
                            </div>
                        )}

                        <div ref={messagesEndRef} />
                    </div>

                    {/* Input - Smaller on mobile */}
                    <div className="p-2 md:p-3 bg-white border-t">
                        <div className="flex gap-2">
                            <input
                                type="text"
                                value={input}
                                onChange={(e) => setInput(e.target.value)}
                                onKeyPress={(e) => e.key === 'Enter' && sendMessage()}
                                placeholder="Taip soalan..."
                                className="flex-1 px-3 py-2 border rounded-full focus:outline-none focus:ring-2 focus:ring-blue-500 text-xs md:text-sm"
                                disabled={loading}
                            />
                            <button
                                onClick={sendMessage}
                                disabled={loading || !input.trim()}
                                className="bg-blue-600 hover:bg-blue-700 disabled:bg-gray-300 text-white p-2 rounded-full transition-colors"
                            >
                                <svg className="w-4 h-4 md:w-5 md:h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                                </svg>
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </>
    );
}
