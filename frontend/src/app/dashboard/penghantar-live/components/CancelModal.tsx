'use client';

// CancelModal — confirm + reason. Calls POST /live/orders/{id}/cancel.
// Reason is required at 10+ chars after strip (matches RPC and Pydantic).

import { useState } from 'react';
import { AlertTriangle } from 'lucide-react';
import toast from 'react-hot-toast';
import { Modal } from '@/components/ui/popups';
import { cancelOrder } from '../lib/api';
import type { ActiveOrder } from '../lib/types';

interface Props {
  order: ActiveOrder;
  onClose: () => void;
  onSuccess: () => void;
}

const MIN_REASON = 10;
const MAX_REASON = 500;

export default function CancelModal({ order, onClose, onSuccess }: Props) {
  const [reason, setReason] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const trimmedLen = reason.trim().length;
  const valid = trimmedLen >= MIN_REASON && trimmedLen <= MAX_REASON;
  const riderHasOrder =
    order.status === 'picked_up' || order.status === 'delivering';

  const submit = async () => {
    if (!valid) return;
    setSubmitting(true);
    try {
      await cancelOrder(order.id, reason.trim());
      toast.success('Pesanan dibatalkan');
      onSuccess();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'Gagal membatalkan pesanan');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Modal
      open
      onClose={onClose}
      title={`Batalkan pesanan ${order.order_number}?`}
      className="sm:max-w-[460px]"
      footer={
        <>
          <button
            type="button"
            onClick={onClose}
            disabled={submitting}
            className="h-11 px-4 rounded-lg text-sm font-geist text-white/70 hover:text-white hover:bg-white/[0.06] transition disabled:opacity-50"
          >
            Tidak jadi
          </button>
          <button
            type="button"
            onClick={submit}
            disabled={!valid || submitting}
            className="h-11 px-4 rounded-lg text-sm font-geist font-medium bg-red-400/15 text-red-300 hover:bg-red-400/20 ring-1 ring-red-400/30 transition disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {submitting ? 'Membatalkan…' : 'Batalkan pesanan'}
          </button>
        </>
      }
    >
      <div className="space-y-3">
          <WarningBox tone="amber">
            <strong className="font-geist font-semibold">
              Pembayaran TIDAK akan dikembalikan secara automatik.
            </strong>{' '}
            Anda perlu uruskan refund secara manual dari halaman Pesanan.
          </WarningBox>

          {riderHasOrder && (
            <WarningBox tone="red">
              Rider mungkin sudah ambil makanan. Hubungi rider terlebih dahulu
              sebelum batalkan.
            </WarningBox>
          )}

          <div>
            <label className="font-mono text-[10px] uppercase tracking-wider text-white/50">
              Sebab pembatalan
              <span className="text-red-300 ml-0.5">*</span>
            </label>
            <textarea
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              maxLength={MAX_REASON + 20 /* small buffer; strip-then-check at submit */}
              rows={4}
              placeholder="Contoh: Pelanggan minta cancel, kedai tutup, dll."
              className="mt-1.5 w-full rounded-lg bg-white/[0.04] border border-white/[0.08] focus:border-white/[0.20] outline-none px-3 py-2.5 text-sm font-geist text-white placeholder:text-white/30 resize-y"
            />
            <div className="mt-1 flex items-center justify-between text-[11px] font-mono">
              <span
                className={
                  trimmedLen < MIN_REASON ? 'text-red-300' : 'text-white/40'
                }
              >
                {trimmedLen < MIN_REASON
                  ? `Minimum ${MIN_REASON} aksara`
                  : 'OK'}
              </span>
              <span className="text-white/40">{trimmedLen}/{MAX_REASON}</span>
            </div>
          </div>
      </div>
    </Modal>
  );
}

function WarningBox({
  tone,
  children,
}: {
  tone: 'amber' | 'red';
  children: React.ReactNode;
}) {
  const classes =
    tone === 'red'
      ? 'bg-red-400/10 text-red-300 ring-red-400/20'
      : 'bg-amber-400/10 text-amber-200 ring-amber-400/20';
  return (
    <div
      className={`flex items-start gap-2 rounded-lg ring-1 px-3 py-2.5 text-[13px] font-geist ${classes}`}
    >
      <AlertTriangle size={14} strokeWidth={1.5} className="shrink-0 mt-0.5" />
      <div>{children}</div>
    </div>
  );
}
