'use client';

// ItemList — order items + totals + payment-method pill.

import { Banknote, CreditCard } from 'lucide-react';

import type { RiderOrder } from '../lib/types';

interface ItemListProps {
  order: RiderOrder;
}

function isFree(amount: string | undefined | null): boolean {
  const n = Number.parseFloat(amount || '0');
  return Number.isFinite(n) && n <= 0;
}

export default function ItemList({ order }: ItemListProps) {
  const isCod = order.payment_method === 'cod';

  return (
    <section className="mx-4 mt-3 rounded-2xl bg-[var(--rider-surface)] border border-[var(--rider-border)] p-4">
      <h3 className="text-[13px] font-semibold text-[var(--rider-text-2)] uppercase tracking-wide">
        Item Pesanan
      </h3>

      <ul className="mt-3 space-y-2">
        {(order.items?.length ?? 0) === 0 ? (
          <li className="text-[12px] text-[var(--rider-muted)]">
            Tiada perincian item.
          </li>
        ) : (
          order.items!.map((it, idx) => (
            <li
              key={`${idx}-${it.name}`}
              className="flex items-baseline gap-2 text-[13px]"
            >
              <span className="font-mono text-[var(--rider-text-2)] shrink-0">
                {it.qty}×
              </span>
              <span className="flex-1 text-white truncate">{it.name}</span>
              <span className="font-mono text-[var(--rider-text-2)] shrink-0">
                RM{it.price}
              </span>
            </li>
          ))
        )}
      </ul>

      <div className="mt-4 pt-3 border-t border-[var(--rider-border)] space-y-1.5 text-[13px]">
        <div className="flex items-center justify-between text-[var(--rider-text-2)]">
          <span>Subtotal</span>
          <span className="font-mono">RM{order.subtotal}</span>
        </div>
        <div className="flex items-center justify-between text-[var(--rider-text-2)]">
          <span>Penghantaran</span>
          <span className="font-mono">
            {isFree(order.delivery_fee) ? 'Percuma' : `RM${order.delivery_fee}`}
          </span>
        </div>
        <div className="flex items-center justify-between pt-1.5">
          <span className="text-white font-semibold">Jumlah</span>
          <span className="font-mono text-[18px] font-bold text-[var(--rider-lime)]">
            RM{order.total}
          </span>
        </div>
      </div>

      <div
        className={`mt-4 inline-flex items-center gap-2 px-3 py-1.5 rounded-full border text-[12px] font-semibold ${
          isCod
            ? 'text-[var(--rider-amber)] bg-[rgba(255,176,32,0.10)] border-[rgba(255,176,32,0.30)]'
            : 'text-[var(--rider-lime)] bg-[rgba(199,255,61,0.10)] border-[rgba(199,255,61,0.30)]'
        }`}
      >
        {isCod ? (
          <>
            <Banknote className="w-3.5 h-3.5" />
            Tunai (COD)
          </>
        ) : (
          <>
            <CreditCard className="w-3.5 h-3.5" />
            Online
          </>
        )}
      </div>
    </section>
  );
}
