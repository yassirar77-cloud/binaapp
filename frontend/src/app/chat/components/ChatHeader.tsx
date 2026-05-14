'use client';

// New chat panel header that visually replaces BinaChat's internal header
// (gated by hideHeader prop in Phase 8). Hierarchy:
//   - Mobile back arrow (only <md)
//   - Avatar
//   - Name + presence pill (active=Online, closed=Ditutup)
//   - Phone + copy button
//   - Order# badge (if order_id) — last 4 chars as "#…XXXX"
//   - Lihat Pesanan link (if order_id)
//   - More menu (3 dots): Tutup Chat, Salin No Telefon

import { useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import {
  ArrowLeft,
  Copy,
  ExternalLink,
  MoreVertical,
  Package,
  Phone,
  X,
} from 'lucide-react';
import type { Conversation } from '../lib/types';
import ConvAvatar from './ConvAvatar';

interface Props {
  conv: Conversation;
  isMobile: boolean;
  onBack: () => void;
  onCopyPhone: (phone: string) => void;
  onCloseConversation: (id: string) => void;
}

function shortOrderId(id: string): string {
  if (!id) return '';
  const clean = id.replace(/-/g, '');
  return clean.slice(-4).toUpperCase();
}

export default function ChatHeader({
  conv,
  isMobile,
  onBack,
  onCopyPhone,
  onCloseConversation,
}: Props) {
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement | null>(null);

  // Close menu on outside click + Escape.
  useEffect(() => {
    if (!menuOpen) return;
    const onDocMouseDown = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuOpen(false);
      }
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setMenuOpen(false);
    };
    document.addEventListener('mousedown', onDocMouseDown);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onDocMouseDown);
      document.removeEventListener('keydown', onKey);
    };
  }, [menuOpen]);

  const isClosed = conv.status === 'closed';
  const phone = (conv.customer_phone || '').trim();
  const hasOrder = !!conv.order_id;

  return (
    <div className="relative z-20 bg-[#161623] border-b border-white/[0.08]">
      <div className="flex items-center gap-3 px-3 sm:px-4 py-2.5">
        {isMobile && (
          <button
            type="button"
            onClick={onBack}
            aria-label="Kembali ke senarai"
            className="inline-flex items-center justify-center w-8 h-8 rounded-lg bg-white/[0.04] border border-white/[0.08] text-white/70 hover:text-white hover:bg-white/[0.08] transition-colors"
          >
            <ArrowLeft size={14} strokeWidth={1.5} />
          </button>
        )}

        <ConvAvatar conv={conv} />

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="font-geist text-sm sm:text-base font-semibold text-white truncate">
              {conv.customer_name || 'Pelanggan'}
            </span>
            <PresencePill isClosed={isClosed} />
          </div>
          <div className="mt-0.5 flex items-center gap-2 flex-wrap">
            {phone && (
              <button
                type="button"
                onClick={() => onCopyPhone(phone)}
                aria-label="Salin nombor telefon"
                className="group inline-flex items-center gap-1 font-mono text-[11px] text-white/55 hover:text-white/85 transition-colors"
              >
                <Phone size={11} strokeWidth={1.5} />
                <span className="truncate">{phone}</span>
                <Copy
                  size={10}
                  strokeWidth={1.5}
                  className="opacity-0 group-hover:opacity-80 transition-opacity"
                />
              </button>
            )}
            {hasOrder && (
              <span className="inline-flex items-center gap-1 h-5 px-1.5 rounded-md bg-indigo-500/10 ring-1 ring-indigo-400/20 font-mono text-[10px] text-indigo-300">
                <Package size={10} strokeWidth={1.5} />#…{shortOrderId(conv.order_id!)}
              </span>
            )}
          </div>
        </div>

        <div className="flex items-center gap-1.5 shrink-0">
          {hasOrder && (
            <Link
              href={`/pesanan?highlight=${conv.order_id}`}
              className="hidden sm:inline-flex items-center gap-1 h-8 px-3 rounded-lg bg-white/[0.04] border border-white/[0.08] text-white/80 hover:text-white hover:bg-white/[0.08] font-geist text-xs transition-colors"
            >
              <ExternalLink size={12} strokeWidth={1.5} />
              Lihat Pesanan
            </Link>
          )}

          <div className="relative" ref={menuRef}>
            <button
              type="button"
              onClick={() => setMenuOpen((v) => !v)}
              aria-label="Menu lanjutan"
              aria-haspopup="menu"
              aria-expanded={menuOpen}
              className="inline-flex items-center justify-center w-8 h-8 rounded-lg bg-white/[0.04] border border-white/[0.08] text-white/70 hover:text-white hover:bg-white/[0.08] transition-colors"
            >
              <MoreVertical size={14} strokeWidth={1.5} />
            </button>

            {menuOpen && (
              <div
                role="menu"
                className="absolute right-0 top-full mt-1.5 z-50 w-48 max-w-[calc(100vw-1.5rem)] rounded-lg border border-white/[0.08] bg-[#161623] shadow-xl chat-fade-in"
              >
                {hasOrder && (
                  <Link
                    href={`/pesanan?highlight=${conv.order_id}`}
                    onClick={() => setMenuOpen(false)}
                    className="sm:hidden flex items-center gap-2 px-3 py-2 font-geist text-xs text-white/80 hover:bg-white/[0.04]"
                    role="menuitem"
                  >
                    <ExternalLink size={12} strokeWidth={1.5} />
                    Lihat Pesanan
                  </Link>
                )}
                {phone && (
                  <button
                    type="button"
                    onClick={() => {
                      onCopyPhone(phone);
                      setMenuOpen(false);
                    }}
                    className="w-full flex items-center gap-2 px-3 py-2 font-geist text-xs text-white/80 hover:bg-white/[0.04] text-left"
                    role="menuitem"
                  >
                    <Copy size={12} strokeWidth={1.5} />
                    Salin No Telefon
                  </button>
                )}
                {!isClosed && (
                  <button
                    type="button"
                    onClick={() => {
                      onCloseConversation(conv.id);
                      setMenuOpen(false);
                    }}
                    className="w-full flex items-center gap-2 px-3 py-2 font-geist text-xs text-red-300 hover:bg-red-500/10 text-left border-t border-white/[0.06]"
                    role="menuitem"
                  >
                    <X size={12} strokeWidth={1.5} />
                    Tutup Chat
                  </button>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function PresencePill({ isClosed }: { isClosed: boolean }) {
  if (isClosed) {
    return (
      <span className="inline-flex items-center gap-1 h-5 px-1.5 rounded-full bg-red-500/10 ring-1 ring-red-500/20 font-mono text-[10px] text-red-300">
        <span className="h-1.5 w-1.5 rounded-full bg-red-400" />
        Ditutup
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 h-5 px-1.5 rounded-full bg-emerald-400/10 ring-1 ring-emerald-400/20 font-mono text-[10px] text-emerald-300">
      <span className="chat-live-dot h-1.5 w-1.5 rounded-full bg-emerald-400" />
      Aktif
    </span>
  );
}
