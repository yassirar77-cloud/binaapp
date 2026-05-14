'use client';

// Owner-side payment verification modal. Mirrors the RejectModal pattern from
// /pesanan: parent controls open/close (renders only when message != null) and
// supplies the actual API call via onConfirm. Local state covers the in-flight
// flag; success is signalled by the parent unmounting us, failure by onConfirm
// returning false (we clear submitting and let the user retry).

import { useEffect, useState } from 'react';
import { AlertTriangle, ShieldCheck, X } from 'lucide-react';
import type { Message } from '../lib/types';

interface Props {
  message: Message | null;
  onConfirm: (messageId: string) => Promise<boolean>;
  onClose: () => void;
}

export default function VerifyPaymentModal({ message, onConfirm, onClose }: Props) {
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!message) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && !submitting) onClose();
    };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [message, onClose, submitting]);

  if (!message) return null;

  const meta = message.metadata ?? {};
  const amount = typeof meta.amount === 'number' ? meta.amount : Number(meta.amount);
  const hasAmount = Number.isFinite(amount) && amount > 0;
  const orderIdRaw: string | undefined = meta.order_id;
  const orderTail = orderIdRaw ? orderIdRaw.slice(-8) : null;
  const reference: string | undefined = meta.reference || meta.payment_reference;
  const method: string | undefined = meta.method || meta.payment_method;

  const handleSubmit = async () => {
    if (submitting) return;
    setSubmitting(true);
    const ok = await onConfirm(message.id);
    if (!ok) setSubmitting(false);
  };

  return (
    <div
      className="chat-fade-in fixed inset-0 z-[60] bg-black/55 backdrop-blur-sm flex items-center justify-center p-4"
      onMouseDown={() => {
        if (!submitting) onClose();
      }}
      role="presentation"
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="verify-payment-title"
        onMouseDown={(e) => e.stopPropagation()}
        className="chat-modal-in w-full max-w-[calc(100vw-2rem)] sm:max-w-[480px] rounded-xl bg-[#161623] ring-1 ring-white/[0.08] shadow-2xl shadow-black/50 overflow-hidden flex flex-col max-h-[calc(100vh-2rem)]"
      >
        {/* Header */}
        <div className="shrink-0 flex items-start justify-between gap-3 px-5 pt-5 pb-3">
          <div className="flex items-start gap-3 min-w-0">
            <div className="shrink-0 w-9 h-9 rounded-lg bg-lime-400/15 ring-1 ring-lime-400/30 flex items-center justify-center">
              <ShieldCheck size={18} strokeWidth={1.8} className="text-lime-300" />
            </div>
            <div className="min-w-0">
              <h2
                id="verify-payment-title"
                className="font-geist font-semibold text-base text-white"
              >
                Sahkan Pembayaran?
              </h2>
              <p className="mt-1 font-geist text-xs text-white/55">
                Semak butiran sebelum mengesahkan.
              </p>
            </div>
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
          {/* Payment metadata */}
          <div className="rounded-lg bg-lime-400/[0.08] ring-1 ring-lime-400/20 p-3 space-y-2">
            {hasAmount ? (
              <div>
                <div className="font-mono text-[10px] uppercase tracking-wider text-lime-200/70 mb-0.5">
                  Jumlah
                </div>
                <div className="font-mono text-2xl font-semibold text-lime-300 leading-none">
                  RM {amount.toFixed(2)}
                </div>
              </div>
            ) : null}
            {orderTail ? (
              <div className="font-mono text-xs text-white/70">
                Pesanan: <span className="text-white/90">#{orderTail}</span>
              </div>
            ) : null}
            {reference ? (
              <div className="font-geist text-xs text-white/70">
                Rujukan: <span className="font-mono text-white/90">{reference}</span>
              </div>
            ) : null}
            {method ? (
              <div className="font-geist text-xs text-white/70">
                Kaedah: <span className="text-white/90">{method}</span>
              </div>
            ) : null}
          </div>

          {/* Warning */}
          <div className="flex items-start gap-2.5 rounded-lg bg-amber-500/10 ring-1 ring-amber-500/30 border-l-[3px] border-amber-500 px-3 py-2.5">
            <AlertTriangle
              size={14}
              strokeWidth={1.8}
              className="text-amber-300 shrink-0 mt-0.5"
            />
            <div className="font-geist text-xs text-amber-100 leading-relaxed">
              Sila pastikan bayaran benar-benar telah masuk ke akaun bank anda
              sebelum mengesahkan.
            </div>
          </div>

          {/* Helper */}
          <p className="font-geist text-[11px] text-white/50 leading-relaxed">
            Tindakan ini akan tandakan bayaran sebagai disahkan dan maklumkan
            pelanggan.
          </p>
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
            disabled={submitting}
            onClick={handleSubmit}
            className="inline-flex items-center justify-center gap-1.5 h-11 px-3 rounded-lg bg-lime-500 hover:bg-lime-400 active:bg-lime-600 text-black font-geist text-sm font-semibold transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {submitting ? (
              'Memproses…'
            ) : (
              <>
                <ShieldCheck size={15} strokeWidth={2} />
                Sahkan Pembayaran
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
