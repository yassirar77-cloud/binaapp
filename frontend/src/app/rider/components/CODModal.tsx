'use client';

// CODModal — cash-collection confirmation modal.
//
// Trigger: when a `delivering` + COD order taps the "Selesai Hantar" CTA,
// RiderApp opens this modal instead of advancing directly. The two
// buttons threading `payment_received` (true / false) through to
// advanceStatus capture whether the rider actually got the cash — see
// Phase-4 backend column delivery_orders.payment_received.

import { Banknote, Loader2, X } from 'lucide-react';

import type { RiderOrder } from '../lib/types';

interface CODModalProps {
  order: RiderOrder;
  pending: boolean;
  onConfirm: (received: boolean) => void;
  onClose: () => void;
}

export default function CODModal({
  order,
  pending,
  onConfirm,
  onClose,
}: CODModalProps) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-end sm:items-center justify-center rider-fade-in"
      role="dialog"
      aria-modal="true"
      aria-labelledby="cod-modal-title"
    >
      {/* Backdrop — taps outside close the modal unless we're mid-request */}
      <button
        type="button"
        aria-label="Tutup"
        onClick={pending ? undefined : onClose}
        className="absolute inset-0 bg-black/65 backdrop-blur-sm"
      />

      <div className="relative w-full sm:max-w-md sm:mx-4 bg-[var(--rider-surface)] rounded-t-3xl sm:rounded-3xl border border-[var(--rider-border)] p-5 rider-modal-in">
        {/* Close (top-right, hidden while pending) */}
        {!pending && (
          <button
            type="button"
            onClick={onClose}
            aria-label="Tutup"
            className="absolute top-4 right-4 w-9 h-9 rounded-full flex items-center justify-center text-[var(--rider-text-2)] hover:text-white hover:bg-[var(--rider-surface-2)] transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        )}

        <div className="flex flex-col items-center text-center">
          <div className="w-14 h-14 rounded-2xl bg-[rgba(255,176,32,0.12)] border border-[rgba(255,176,32,0.30)] flex items-center justify-center mb-3">
            <Banknote
              className="w-7 h-7 text-[var(--rider-amber)]"
              strokeWidth={2.25}
            />
          </div>
          <h2
            id="cod-modal-title"
            className="text-[20px] font-semibold text-white"
          >
            Pesanan dah selesai dihantar?
          </h2>
          <p className="mt-1.5 text-[13px] text-[var(--rider-text-2)]">
            Sahkan kutipan tunai untuk pesanan ini.
          </p>
        </div>

        {/* Summary */}
        <dl className="mt-5 rounded-2xl bg-[var(--rider-surface-2)] border border-[var(--rider-border)] divide-y divide-[var(--rider-border)] text-[13px]">
          <div className="flex items-center justify-between px-4 py-3">
            <dt className="text-[var(--rider-text-2)]">Jumlah</dt>
            <dd className="font-mono text-[18px] font-bold text-[var(--rider-lime)]">
              RM{order.total}
            </dd>
          </div>
          <div className="flex items-center justify-between px-4 py-2.5">
            <dt className="text-[var(--rider-text-2)]">Pesanan</dt>
            <dd className="font-mono text-white">#{order.order_number}</dd>
          </div>
          <div className="flex items-center justify-between px-4 py-2.5">
            <dt className="text-[var(--rider-text-2)]">Pelanggan</dt>
            <dd className="text-white truncate max-w-[60%] text-right">
              {order.customer_name}
            </dd>
          </div>
          <div className="flex items-start justify-between px-4 py-2.5 gap-3">
            <dt className="text-[var(--rider-text-2)] shrink-0">Alamat</dt>
            <dd className="text-white text-right text-[12px] leading-relaxed">
              {order.delivery_address}
            </dd>
          </div>
        </dl>

        {/* Actions */}
        <div className="mt-5 space-y-2">
          <button
            type="button"
            onClick={() => onConfirm(true)}
            disabled={pending}
            className="w-full h-14 rounded-2xl bg-[var(--rider-lime)] hover:bg-[var(--rider-lime-2)] text-black font-semibold text-[15px] flex items-center justify-center gap-2 disabled:opacity-60 disabled:cursor-not-allowed transition-colors"
          >
            {pending ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : (
              <Banknote className="w-5 h-5" strokeWidth={2.25} />
            )}
            Tunai RM{order.total} diterima
          </button>
          <button
            type="button"
            onClick={() => onConfirm(false)}
            disabled={pending}
            className="w-full h-12 rounded-2xl bg-[var(--rider-surface-2)] border border-[var(--rider-border)] text-[var(--rider-text-2)] hover:text-white text-[14px] font-medium disabled:opacity-60 disabled:cursor-not-allowed transition-colors"
          >
            Tunai belum diterima
          </button>
        </div>

        <p className="mt-3 text-center text-[11px] text-[var(--rider-muted)]">
          Pilihan anda akan direkodkan untuk pengesahan pemilik kedai.
        </p>
      </div>
    </div>
  );
}
