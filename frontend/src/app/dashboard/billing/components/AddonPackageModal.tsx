'use client';

import { X } from 'lucide-react';
import type { Addon, AddonPackage } from '../types';

interface Props {
  addon: Addon | null;
  packages: AddonPackage[];
  processing: boolean;
  onSelect: (packageId: string) => void;
  onClose: () => void;
}

function formatRM(n: number): string {
  return 'RM ' + n.toLocaleString('en-MY', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

/**
 * Bundle picker shown when an addon offers volume-discounted packages
 * (AI images / AI hero). Prices shown here are display-only — the backend
 * re-resolves the package by id and bills the server-side price.
 */
export default function AddonPackageModal({ addon, packages, processing, onSelect, onClose }: Props) {
  if (!addon) return null;

  const options = packages
    .filter((p) => p.addon_type === addon.type)
    .sort((a, b) => a.quantity - b.quantity);

  if (options.length === 0) return null;

  // Highlight the mid-range bundle (best mix of price and commitment):
  // the second-largest package, falling back to the largest.
  const popularId = options.length > 2 ? options[options.length - 2].package_id : options[options.length - 1].package_id;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-ink-900/50 px-4"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-label={`Pilih pakej ${addon.name}`}
    >
      <div
        className="w-full max-w-[420px] rounded-[20px] bg-white p-6 shadow-[0_24px_64px_rgba(11,11,21,0.18)]"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between">
          <div>
            <h3 className="m-0 text-[17px] font-semibold tracking-[-0.02em] text-ink-900">
              Pilih pakej {addon.name}
            </h3>
            <p className="mt-1 text-[12.5px] leading-snug text-ink-500">
              Beli pukal, jimat lebih. Kredit tidak akan tamat tempoh.
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Tutup"
            className="grid h-8 w-8 shrink-0 place-items-center rounded-[9px] text-ink-400 transition-colors hover:bg-ink-050 hover:text-ink-900"
          >
            <X size={16} strokeWidth={2.2} />
          </button>
        </div>

        <div className="mt-4 flex flex-col gap-2.5">
          {options.map((pkg) => {
            const popular = pkg.package_id === popularId && options.length > 1;
            return (
              <button
                key={pkg.package_id}
                type="button"
                disabled={processing}
                onClick={() => onSelect(pkg.package_id)}
                className={`flex items-center justify-between gap-3 rounded-[14px] border px-4 py-3 text-left transition-all disabled:opacity-60 ${
                  popular
                    ? 'border-ink-900 bg-ink-050'
                    : 'border-ink-200 bg-white hover:border-ink-300 hover:bg-ink-050/50'
                }`}
              >
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-[14.5px] font-semibold tabular-nums text-ink-900">
                      {pkg.quantity} kredit
                    </span>
                    {popular && (
                      <span className="rounded-full bg-ink-900 px-2 py-[2px] font-geist-mono text-[9px] font-semibold uppercase tracking-[0.1em] text-white">
                        Popular
                      </span>
                    )}
                  </div>
                  <div className="mt-[2px] text-[11.5px] text-ink-500">
                    {formatRM(pkg.unit_price)}/kredit
                    {pkg.savings_pct > 0 && (
                      <span className="ml-1.5 font-semibold text-ok-500">Jimat {pkg.savings_pct}%</span>
                    )}
                  </div>
                </div>
                <span className="text-[16px] font-bold tracking-[-0.02em] tabular-nums text-ink-900">
                  {formatRM(pkg.price)}
                </span>
              </button>
            );
          })}
        </div>

        <p className="mb-0 mt-4 text-center text-[11px] text-ink-400">
          Anda akan dibawa ke halaman pembayaran ToyyibPay.
        </p>
      </div>
    </div>
  );
}
