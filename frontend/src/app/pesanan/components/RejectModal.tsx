'use client';

// Reject (cancel) confirmation modal. Owns its own reason + submitting state;
// parent wires open/close + the actual API call via onConfirm.
//
// Validation: trim() then require length >= 10. The character counter shows
// the trimmed length so leading/trailing whitespace doesn't inflate the
// number a user sees.
//
// Loading: while onConfirm is in flight ESC and backdrop click are no-ops so
// the request can't be torn down mid-flight.

import { useEffect, useState } from 'react';
import { AlertTriangle, X } from 'lucide-react';
import type { Order } from '../lib/types';

const MIN_LEN = 10;
const MAX_LEN = 500;

const PAID_STATUSES: ReadonlySet<string> = new Set([
  'confirmed',
  'preparing',
  'ready',
  'picked_up',
  'delivering',
]);

interface Props {
  order: Order;
  onClose: () => void;
  /** Returns true on success (modal will unmount via parent), false on
   *  failure (modal stays open + clears submitting state for retry). */
  onConfirm: (order: Order, reason: string) => Promise<boolean>;
}

export default function RejectModal({ order, onClose, onConfirm }: Props) {
  const [reason, setReason] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const trimmed = reason.trim();
  const trimmedLen = trimmed.length;
  const valid = trimmedLen >= MIN_LEN && trimmedLen <= MAX_LEN;

  const showPaidWarning = PAID_STATUSES.has(order.status);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && !submitting) onClose();
    };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [onClose, submitting]);

  const handleSubmit = async () => {
    if (!valid || submitting) return;
    setSubmitting(true);
    const ok = await onConfirm(order, trimmed);
    if (!ok) setSubmitting(false);
    // Success: parent unmounts; no need to clear local state.
  };

  // Tone the counter red while too short, amber while OK but near max, white
  // otherwise.
  const counterClass =
    trimmedLen < MIN_LEN
      ? 'text-red-300'
      : trimmedLen > MAX_LEN - 50
        ? 'text-amber-300'
        : 'text-emerald-300';

  return (
    <div
      className="pesanan-fade-in fixed inset-0 z-[60] bg-black/55 backdrop-blur-sm flex items-center justify-center p-4"
      onMouseDown={() => {
        if (!submitting) onClose();
      }}
      role="presentation"
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="reject-modal-title"
        onMouseDown={(e) => e.stopPropagation()}
        className="pesanan-modal-in w-full max-w-[calc(100vw-2rem)] sm:max-w-[480px] rounded-xl bg-[#161623] ring-1 ring-white/[0.08] shadow-2xl shadow-black/50 overflow-hidden flex flex-col max-h-[calc(100vh-2rem)]"
      >
        {/* Header */}
        <div className="shrink-0 flex items-start justify-between gap-3 px-5 pt-5 pb-3">
          <div className="min-w-0">
            <h2
              id="reject-modal-title"
              className="font-geist font-semibold text-base text-white"
            >
              Tolak pesanan{' '}
              <span className="font-mono">#{order.order_number}</span>?
            </h2>
            <p className="mt-1 font-geist text-xs text-white/55">
              Tindakan ini tidak boleh dibatalkan.
            </p>
          </div>
          <button
            type="button"
            disabled={submitting}
            onClick={onClose}
            aria-label="Tutup"
            className="shrink-0 inline-flex items-center justify-center w-9 h-9 rounded-lg bg-white/[0.04] hover:bg-white/[0.08] text-white/60 hover:text-white ring-1 ring-white/[0.06] transition-colors disabled:opacity-40"
          >
            <X size={16} strokeWidth={1.5} />
          </button>
        </div>

        {/* Scrollable body */}
        <div className="flex-1 overflow-y-auto px-5 pb-4 space-y-3">
          {/* Standard customer-notify warning */}
          <div className="flex items-start gap-2.5 rounded-lg bg-amber-400/10 ring-1 ring-amber-400/30 border-l-[3px] border-amber-400 px-3 py-2.5">
            <AlertTriangle
              size={14}
              strokeWidth={1.8}
              className="text-amber-300 shrink-0 mt-0.5"
            />
            <div className="font-geist text-xs text-amber-100 leading-relaxed">
              Pelanggan akan dimaklumkan tentang penolakan.
            </div>
          </div>

          {/* Paid-already warning */}
          {showPaidWarning ? (
            <div className="flex items-start gap-2.5 rounded-lg bg-red-500/10 ring-1 ring-red-500/30 border-l-[3px] border-red-500 px-3 py-2.5">
              <AlertTriangle
                size={14}
                strokeWidth={1.8}
                className="text-red-300 shrink-0 mt-0.5"
              />
              <div className="font-geist text-xs text-red-100 leading-relaxed">
                Pelanggan mungkin sudah membayar. Anda perlu uruskan refund
                secara manual.
              </div>
            </div>
          ) : null}

          {/* Reason textarea */}
          <div>
            <label
              htmlFor="reject-reason"
              className="block font-mono text-[10px] uppercase tracking-wider text-white/45 mb-1.5"
            >
              Sebab Penolakan
            </label>
            <div className="relative">
              <textarea
                id="reject-reason"
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                rows={4}
                maxLength={MAX_LEN}
                disabled={submitting}
                placeholder={`Sebab tolak pesanan (sekurang-kurangnya ${MIN_LEN} aksara)...`}
                className="w-full resize-y rounded-lg bg-white/[0.04] ring-1 ring-white/[0.08] focus:ring-white/[0.18] focus:outline-none px-3 py-2.5 pb-7 font-geist text-sm text-white placeholder:text-white/30 disabled:opacity-60"
              />
              <div
                className={`absolute right-3 bottom-2 font-mono text-[10px] tracking-wide ${counterClass}`}
                aria-live="polite"
              >
                {trimmedLen}/{MAX_LEN}
              </div>
            </div>
            <p className="mt-1.5 font-geist text-[11px] text-white/40">
              Sebab ini akan disimpan dalam rekod pesanan.
            </p>
          </div>
        </div>

        {/* Footer actions */}
        <div className="shrink-0 grid grid-cols-2 gap-2 px-5 pt-3 pb-5 border-t border-white/[0.06]">
          <button
            type="button"
            disabled={submitting}
            onClick={onClose}
            className="inline-flex items-center justify-center h-11 px-3 rounded-lg bg-white/[0.04] hover:bg-white/[0.08] ring-1 ring-white/[0.08] text-white/80 font-geist text-sm font-medium transition-colors disabled:opacity-40"
          >
            Tidak jadi
          </button>
          <button
            type="button"
            disabled={!valid || submitting}
            onClick={handleSubmit}
            className="inline-flex items-center justify-center h-11 px-3 rounded-lg bg-red-500 hover:bg-red-400 active:bg-red-600 text-white font-geist text-sm font-semibold transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {submitting ? 'Memproses…' : 'Batalkan Pesanan'}
          </button>
        </div>
      </div>
    </div>
  );
}
