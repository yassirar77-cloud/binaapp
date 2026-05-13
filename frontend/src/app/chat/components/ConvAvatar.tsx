'use client';

// Conversation avatar paint. Status-driven so the row at a glance signals
// what the user should pay attention to. Priority (highest first):
//   closed  -> red (muted, deprioritised)
//   unread  -> lime (calls attention)
//   order   -> indigo (an active order conversation)
//   default -> gray (regular support thread)

import type { Conversation } from '../lib/types';

interface Props {
  conv: Conversation;
  size?: 'sm' | 'md';
}

type Paint = {
  bg: string;
  text: string;
  ring: string;
};

function paintFor(c: Conversation): Paint {
  if (c.status === 'closed') {
    return {
      bg: 'bg-red-500/15',
      text: 'text-red-300',
      ring: 'ring-red-500/30',
    };
  }
  if ((c.unread_owner ?? 0) > 0) {
    return {
      bg: 'bg-[#C7FF3D]',
      text: 'text-[#0a0e1a]',
      ring: 'ring-[#C7FF3D]/40',
    };
  }
  if (c.order_id) {
    return {
      bg: 'bg-indigo-500/15',
      text: 'text-indigo-300',
      ring: 'ring-indigo-400/30',
    };
  }
  return {
    bg: 'bg-white/[0.06]',
    text: 'text-white/60',
    ring: 'ring-white/[0.10]',
  };
}

function initialOf(name?: string): string {
  if (!name) return '?';
  const trimmed = name.trim();
  if (!trimmed) return '?';
  return trimmed.charAt(0).toUpperCase();
}

export default function ConvAvatar({ conv, size = 'md' }: Props) {
  const paint = paintFor(conv);
  const sizeCls =
    size === 'sm'
      ? 'w-8 h-8 text-xs'
      : 'w-10 h-10 text-sm';
  return (
    <div
      className={[
        'inline-flex items-center justify-center rounded-full',
        'font-geist font-semibold ring-1 shrink-0',
        sizeCls,
        paint.bg,
        paint.text,
        paint.ring,
      ].join(' ')}
      aria-hidden="true"
    >
      {initialOf(conv.customer_name)}
    </div>
  );
}
