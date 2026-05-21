'use client';

import { MessageCircle } from 'lucide-react';

const PREFILL = 'Hi BinaApp, saya ada soalan tentang bil saya.';

export default function SupportFooter() {
  const waNumber = process.env.NEXT_PUBLIC_SUPPORT_WHATSAPP;

  if (!waNumber) {
    if (process.env.NODE_ENV !== 'production') {
      console.warn(
        '[SupportFooter] NEXT_PUBLIC_SUPPORT_WHATSAPP is not set — footer hidden. Set the env var in Vercel (preview + prod) to enable.'
      );
    }
    return null;
  }

  const href = `https://wa.me/${waNumber}?text=${encodeURIComponent(PREFILL)}`;

  return (
    <div className="mt-3 flex flex-wrap items-center justify-between gap-4 rounded-2xl border border-ink-200 bg-white px-6 py-5">
      <div className="flex items-center gap-3.5">
        <div className="grid h-9 w-9 place-items-center rounded-[10px] bg-brand-50 text-brand-500">
          <MessageCircle size={18} strokeWidth={1.8} />
        </div>
        <div>
          <div className="text-[14px] font-semibold tracking-[-0.015em] text-ink-900">
            Ada soalan tentang bil?
          </div>
          <div className="text-[12.5px] text-ink-400">
            WhatsApp pasukan sokongan — biasa balas dalam 10 minit.
          </div>
        </div>
      </div>
      <a
        href={href}
        target="_blank"
        rel="noopener noreferrer"
        className="flex items-center gap-1.5 rounded-[10px] bg-whatsapp px-4 py-2.5 text-[13px] font-semibold text-white transition-colors hover:bg-[#1FB855]"
      >
        <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
          <path d="M17.5 14.4l-2.3-1.1a1 1 0 00-1.1.2l-.7.8a.6.6 0 01-.7.1c-1-.5-2.2-1.5-3-2.8a.6.6 0 01.1-.7l.7-.8a1 1 0 00.2-1l-.9-2.5a1 1 0 00-1.2-.6c-1 .3-2 1-2 2.4 0 3 3.4 6.6 6.4 7.5 1.4.4 2.6-.6 3-1.6.2-.5-.1-1.1-.5-1.3z" />
          <path d="M12 2a10 10 0 00-8.6 15l-1.4 5 5.2-1.4A10 10 0 1012 2zm0 18a8 8 0 01-4-1l-3 .8.8-2.9a8 8 0 1110.2-3.9 8 8 0 01-4 7z" />
        </svg>
        WhatsApp
      </a>
    </div>
  );
}
