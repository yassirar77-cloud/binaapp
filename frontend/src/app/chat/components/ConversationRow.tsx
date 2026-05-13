'use client';

// Single conversation card in the list. Visual hierarchy:
//   row 1: customer name (truncated)        last-message time
//   row 2: outlet pill + status pill (if any)
//   row 3: last-message preview (truncated, prefixed "Anda:" when owner-sent)
//   right: unread count badge when unread_owner > 0
// Selected state: lime left edge + soft surface lift.

import { Store, Package } from 'lucide-react';
import type { Conversation } from '../lib/types';
import { relTime } from '../lib/relTime';
import ConvAvatar from './ConvAvatar';

interface Props {
  conv: Conversation;
  websiteLabel: string;
  selected: boolean;
  onSelect: (id: string) => void;
}

function previewText(c: Conversation): string {
  const last = c.chat_messages?.[c.chat_messages.length - 1];
  if (!last) return 'Tiada mesej';
  const text =
    last.message_text ||
    (last as any).content ||
    (last as any).message ||
    '';
  if (text) return text;
  if (last.message_type === 'image') return '[gambar]';
  if (last.message_type === 'payment') return '[bukti pembayaran]';
  if (last.message_type === 'location') return '[lokasi]';
  if (last.message_type === 'voice') return '[mesej suara]';
  return 'Tiada mesej';
}

function isOwnerLast(c: Conversation): boolean {
  const last = c.chat_messages?.[c.chat_messages.length - 1];
  return last?.sender_type === 'owner';
}

export default function ConversationRow({
  conv,
  websiteLabel,
  selected,
  onSelect,
}: Props) {
  const unread = conv.unread_owner ?? 0;
  const hasUnread = unread > 0;
  const preview = previewText(conv);
  const ownerLast = isOwnerLast(conv);

  return (
    <button
      type="button"
      onClick={() => onSelect(conv.id)}
      className={[
        'group w-full text-left flex items-stretch gap-0',
        'transition-colors',
        selected
          ? 'bg-white/[0.04]'
          : 'hover:bg-white/[0.025]',
      ].join(' ')}
    >
      {/* Selected: lime left edge accent. Always-present transparent strip so
          unselected rows don't shift width on selection. */}
      <span
        aria-hidden="true"
        className={[
          'w-[3px] shrink-0',
          selected ? 'bg-[#C7FF3D]' : 'bg-transparent',
        ].join(' ')}
      />

      <div className="flex-1 min-w-0 flex items-start gap-3 px-3 py-3 border-b border-white/[0.05]">
        <ConvAvatar conv={conv} />

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-0.5">
            <div className="flex-1 min-w-0 font-geist text-sm font-medium text-white truncate">
              {conv.customer_name || 'Pelanggan'}
            </div>
            <div className="shrink-0 font-mono text-[10px] text-white/40">
              {relTime(conv.updated_at)}
            </div>
          </div>

          <div className="flex items-center gap-1.5 flex-wrap mb-1">
            <span className="inline-flex items-center gap-1 h-5 px-1.5 rounded-md bg-white/[0.04] ring-1 ring-white/[0.08] font-mono text-[10px] text-white/55">
              <Store size={10} strokeWidth={1.5} />
              <span className="truncate max-w-[120px]">{websiteLabel}</span>
            </span>
            {conv.order_id && (
              <span className="inline-flex items-center gap-1 h-5 px-1.5 rounded-md bg-indigo-500/10 ring-1 ring-indigo-400/20 font-mono text-[10px] text-indigo-300">
                <Package size={10} strokeWidth={1.5} />
                Pesanan
              </span>
            )}
            {conv.status === 'closed' && (
              <span className="inline-flex items-center h-5 px-1.5 rounded-md bg-red-500/10 ring-1 ring-red-500/20 font-mono text-[10px] text-red-300">
                Ditutup
              </span>
            )}
          </div>

          <div
            className={[
              'font-geist text-xs truncate',
              hasUnread && !ownerLast ? 'text-white/80' : 'text-white/40',
            ].join(' ')}
          >
            {ownerLast && <span className="text-white/30">Anda: </span>}
            {preview}
          </div>
        </div>

        {hasUnread && (
          <span className="self-center inline-flex items-center justify-center min-w-[20px] h-5 px-1.5 rounded-full bg-[#C7FF3D] text-[#0a0e1a] font-mono text-[10px] font-semibold">
            {unread > 9 ? '9+' : unread}
          </span>
        )}
      </div>
    </button>
  );
}
