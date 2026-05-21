'use client';

import Link from 'next/link';
import { ArrowRight } from 'lucide-react';
import type { Transaction } from '../types';
import SectionHeader from './SectionHeader';

interface Props {
  transactions: Transaction[];
}

// Backend emits these three values (subscription.py upgrade/renew/addon flows).
// An unrecognised value renders the raw string with a console.warn so a new
// backend status surfaces rather than masking as something else.
const STATUS_MAP: Record<
  string,
  { label: string; dotClass: string; pillClass: string }
> = {
  success: {
    label: 'Berjaya',
    dotClass: 'bg-ok-400',
    pillClass: 'bg-[#DCFCE7] text-ok-500',
  },
  pending: {
    label: 'Menunggu',
    dotClass: 'bg-warn-400',
    pillClass: 'bg-[#FFF4D9] text-[#A35F00]',
  },
  failed: {
    label: 'Gagal',
    dotClass: 'bg-err-400',
    pillClass: 'bg-[#FFE0E1] text-[#C02D32]',
  },
};

function StatusPill({ status }: { status: string }) {
  const mapped = STATUS_MAP[status];
  if (!mapped) {
    console.warn(
      `[PaymentHistoryPreview] Unknown payment_status="${status}". Rendering raw value; add an entry to STATUS_MAP.`
    );
  }
  const label = mapped?.label ?? status;
  const dotClass = mapped?.dotClass ?? 'bg-ink-400';
  const pillClass = mapped?.pillClass ?? 'bg-ink-100 text-ink-500';

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2 py-[3px] font-geist-mono text-[10.5px] font-semibold tracking-[0.04em] ${pillClass}`}
    >
      <span className={`inline-block h-1.5 w-1.5 rounded-full ${dotClass}`} />
      {label.toUpperCase()}
    </span>
  );
}

function formatRM(n: number): string {
  return 'RM ' + n.toLocaleString('en-MY', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function formatDateBM(iso: string): string {
  return new Date(iso).toLocaleDateString('ms-MY', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  });
}

export default function PaymentHistoryPreview({ transactions }: Props) {
  const renderable = transactions.filter((tx) => {
    if (!tx.transaction_id || !tx.created_at || tx.amount === null || tx.amount === undefined) {
      console.warn(
        `[PaymentHistoryPreview] Transaction missing required field(s); skipping row. Got: ${JSON.stringify(
          { transaction_id: tx.transaction_id, created_at: tx.created_at, amount: tx.amount }
        )}`
      );
      return false;
    }
    return true;
  });

  const seeAll = (
    <Link
      href="/dashboard/transactions"
      className="inline-flex items-center gap-1 text-[13px] font-semibold text-brand-500 hover:text-brand-600"
    >
      Lihat semua
      <ArrowRight size={12} strokeWidth={2.5} />
    </Link>
  );

  return (
    <div>
      <SectionHeader eyebrow="Sejarah" title="Sejarah pembayaran" right={seeAll} />

      {renderable.length === 0 ? (
        <div className="rounded-[18px] border border-ink-200 bg-white px-6 py-10 text-center">
          <p className="text-[14px] text-ink-500">Belum ada transaksi.</p>
        </div>
      ) : (
        <div className="overflow-hidden rounded-[18px] border border-ink-200 bg-white">
          {/* Column header — desktop only. The fixed grid columns sum to >340px
              which overflows ~360px viewports; below sm we render a stacked
              card per row instead. */}
          <div className="hidden sm:grid grid-cols-[110px_1fr_120px_110px] gap-3 border-b border-ink-200 bg-ink-050 px-5 py-2.5 font-geist-mono text-[10px] font-medium uppercase tracking-[0.1em] text-ink-400">
            <div>Tarikh</div>
            <div>Penerangan</div>
            <div className="text-right">Jumlah</div>
            <div>Status</div>
          </div>
          {renderable.map((tx, i) => {
            const isLast = i === renderable.length - 1;
            return (
              <div
                key={tx.transaction_id}
                className={`px-4 py-3.5 sm:px-5 ${isLast ? '' : 'border-b border-ink-100'} transition-colors hover:bg-[#FAFAFD]`}
              >
                {/* Mobile: 2-row stacked card. */}
                <div className="flex flex-col gap-2 sm:hidden">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0 flex-1">
                      <div className="text-[14px] font-medium tracking-[-0.005em] text-ink-900">
                        {tx.item_description || tx.transaction_type || 'Transaksi'}
                      </div>
                      {tx.invoice_number && (
                        <div className="mt-0.5 font-geist-mono text-[10.5px] text-ink-300">
                          {tx.invoice_number}
                        </div>
                      )}
                    </div>
                    <div className="flex-shrink-0 text-right text-[14px] font-semibold tabular-nums tracking-[-0.01em] text-ink-900">
                      {formatRM(tx.amount)}
                    </div>
                  </div>
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-geist-mono text-[11px] text-ink-500">
                      {formatDateBM(tx.created_at)}
                    </span>
                    <StatusPill status={tx.payment_status} />
                  </div>
                </div>

                {/* Desktop: 4-column grid. */}
                <div className="hidden sm:grid sm:grid-cols-[110px_1fr_120px_110px] sm:gap-3 sm:items-center">
                  <div className="font-geist-mono text-[12px] text-ink-500">
                    {formatDateBM(tx.created_at)}
                  </div>
                  <div className="min-w-0">
                    <div className="truncate text-[13.5px] font-medium tracking-[-0.005em] text-ink-900">
                      {tx.item_description || tx.transaction_type || 'Transaksi'}
                    </div>
                    {tx.invoice_number && (
                      <div className="mt-0.5 font-geist-mono text-[10.5px] text-ink-300">
                        {tx.invoice_number}
                      </div>
                    )}
                  </div>
                  <div className="text-right text-[14px] font-semibold tabular-nums tracking-[-0.01em] text-ink-900">
                    {formatRM(tx.amount)}
                  </div>
                  <div>
                    <StatusPill status={tx.payment_status} />
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
