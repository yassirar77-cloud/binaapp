'use client';

import { Shield } from 'lucide-react';
import SectionHeader from './SectionHeader';

// Confirmed supported subset of the 5 largest Malaysian retail banks ToyyibPay
// routes FPX through. ToyyibPay supports more banks at checkout — this list is
// a marketing display of the major recognisable brands, not exhaustive.
const BANKS: { name: string; bg: string; fg: string }[] = [
  { name: 'Maybank2u', bg: '#FFCC00', fg: '#000000' },
  { name: 'CIMB Clicks', bg: '#E60000', fg: '#FFFFFF' },
  { name: 'Public Bank', bg: '#0066B3', fg: '#FFFFFF' },
  { name: 'RHB', bg: '#005EB8', fg: '#FFFFFF' },
  { name: 'Hong Leong', bg: '#003E7E', fg: '#FFFFFF' },
];

function BankChip({ name, bg, fg }: (typeof BANKS)[number]) {
  return (
    <div
      className="inline-flex h-9 items-center justify-center rounded-lg border border-black/[0.08] px-3 font-geist text-[11.5px] font-bold tracking-[-0.01em]"
      style={{ background: bg, color: fg }}
    >
      {name}
    </div>
  );
}

export default function PaymentMethodPanel() {
  return (
    <div>
      <SectionHeader
        eyebrow="Kaedah Bayar"
        title="Kaedah pembayaran"
        sub="Bayaran diproses melalui ToyyibPay — gateway selamat untuk perniagaan Malaysia."
      />

      <div className="flex flex-col gap-4 rounded-[20px] border border-ink-200 bg-white px-6 py-[22px]">
        <div className="flex items-center gap-3">
          <div className="grid h-11 w-11 place-items-center rounded-[12px] border border-ink-200 bg-white shadow-[0_4px_10px_rgba(11,11,21,0.04)]">
            <svg width="26" height="26" viewBox="0 0 32 32" fill="none" aria-hidden="true">
              <path d="M4 8 L 16 4 L 28 8 L 28 18 C 28 24 22 28 16 30 C 10 28 4 24 4 18 Z" fill="#1E4FA0" />
              <path
                d="M11 14 L 14 17 L 21 11"
                stroke="#FFD700"
                strokeWidth="2.5"
                strokeLinecap="round"
                strokeLinejoin="round"
                fill="none"
              />
            </svg>
          </div>
          <div>
            <div className="text-[16px] font-bold tracking-[-0.02em] text-ink-900">toyyibPay</div>
            <div className="mt-0.5 font-geist-mono text-[10.5px] tracking-[0.06em] text-ink-400">
              BERLESEN BANK NEGARA · PCI-DSS
            </div>
          </div>
          <div className="ml-auto flex items-center gap-1 font-geist-mono text-[10.5px] font-semibold text-ok-500">
            <Shield size={11} strokeWidth={2.4} />
            SELAMAT
          </div>
        </div>

        <p className="text-[13px] leading-relaxed text-ink-500">
          Pembayaran melalui ToyyibPay (FPX). Pilih bank anda semasa checkout — RM 1.00 caj transaksi setiap bayaran, tiada caj tersembunyi.
        </p>

        <div>
          <div className="mb-2 font-geist-mono text-[9.5px] font-medium uppercase tracking-[0.12em] text-ink-400">
            Termasuk
          </div>
          <div className="flex flex-wrap gap-1.5">
            {BANKS.map((b) => (
              <BankChip key={b.name} {...b} />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
