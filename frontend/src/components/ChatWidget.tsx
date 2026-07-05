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

    // Auto scroll to bottom - MUST be before any conditional returns
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    useEffect(() => {
        if (!isOpen) return;
        const onKey = (e: KeyboardEvent) => {
            if (e.key === 'Escape') setIsOpen(false);
        };
        document.addEventListener('keydown', onKey);
        return () => document.removeEventListener('keydown', onKey);
    }, [isOpen]);

    // Early return AFTER all hooks
    if (shouldHide) {
        return null;
    }

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
                className="fixed bottom-4 right-4 z-50 rounded-full bg-ink-800 p-3 text-volt-400 shadow-2xl shadow-black/50 ring-1 ring-white/[0.12] transition-all duration-300 hover:bg-ink-700 hover:ring-volt-400/40 md:p-4"
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
                    bg-ink-800 rounded-2xl shadow-2xl shadow-black/50 flex flex-col overflow-hidden ring-1 ring-white/[0.08] animate-scale-in origin-bottom-right">

                    {/* Header - Smaller on mobile */}
                    <div className="border-b border-white/[0.08] bg-ink-900 text-white p-3 md:p-4 flex items-center gap-2 md:gap-3">
                        <div className="w-8 h-8 md:w-10 md:h-10 bg-volt-400/15 ring-1 ring-volt-400/30 rounded-full flex items-center justify-center text-sm md:text-base">
                            🤖
                        </div>
                        <div>
                            <h3 className="font-bold text-sm md:text-base">BinaBot</h3>
                            <p className="text-[10px] md:text-xs text-ink-300">Sokongan Pelanggan</p>
                        </div>
                        {/* Close button for mobile */}
                        <button
                            onClick={() => setIsOpen(false)}
                            className="ml-auto md:hidden p-1 text-ink-300 hover:text-white transition-colors"
                        >
                            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                            </svg>
                        </button>
                    </div>

                    {/* Messages - Smaller text on mobile */}
                    <div className="flex-1 overflow-y-auto p-3 md:p-4 space-y-3 bg-ink-900/60">
                        {messages.map((msg, i) => (
                            <div
                                key={i}
                                className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                            >
                                <div
                                    className={`max-w-[85%] p-2 md:p-3 rounded-2xl ${
                                        msg.role === 'user'
                                            ? 'bg-volt-400 text-ink-900 rounded-br-md'
                                            : 'bg-white/[0.06] text-ink-100 rounded-bl-md ring-1 ring-white/[0.08]'
                                    }`}
                                >
                                    <p className="text-xs md:text-sm whitespace-pre-wrap">{msg.content}</p>
                                </div>
                            </div>
                        ))}

                        {loading && (
                            <div className="flex justify-start">
                                <div className="bg-white/[0.06] p-2 md:p-3 rounded-2xl rounded-bl-md ring-1 ring-white/[0.08]">
                                    <div className="flex gap-1">
                                        <span className="w-2 h-2 bg-ink-400 rounded-full animate-bounce"></span>
                                        <span className="w-2 h-2 bg-ink-400 rounded-full animate-bounce" style={{animationDelay: '0.1s'}}></span>
                                        <span className="w-2 h-2 bg-ink-400 rounded-full animate-bounce" style={{animationDelay: '0.2s'}}></span>
                                    </div>
                                </div>
                            </div>
                        )}

                        <div ref={messagesEndRef} />
                    </div>

                    {/* Input - Smaller on mobile */}
                    <div className="p-2 md:p-3 bg-ink-800 border-t border-white/[0.08]">
                        <div className="flex gap-2">
                            <input
                                type="text"
                                value={input}
                                onChange={(e) => setInput(e.target.value)}
                                onKeyPress={(e) => e.key === 'Enter' && sendMessage()}
                                placeholder="Taip soalan..."
                                className="flex-1 px-3 py-2 bg-white/[0.04] ring-1 ring-white/[0.08] text-ink-050 placeholder:text-ink-500 rounded-full focus:outline-none focus:ring-2 focus:ring-volt-400/60 text-xs md:text-sm"
                                disabled={loading}
                            />
                            <button
                                onClick={sendMessage}
                                disabled={loading || !input.trim()}
                                className="bg-volt-400 hover:bg-volt-300 disabled:bg-white/[0.08] disabled:text-ink-500 text-ink-900 p-2 rounded-full transition-colors"
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
