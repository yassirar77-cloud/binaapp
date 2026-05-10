'use client';

import { useState } from 'react';
import { MapPin, Search } from 'lucide-react';
import type { PostcodeTestResult } from '../lib/types';

export interface PostcodeTestState {
  postcode: string;
  result?: PostcodeTestResult;
  notFound?: boolean;
  error?: string;
}

export default function PostcodeTest({
  onSubmit,
  state,
  loading,
}: {
  onSubmit: (postcode: string) => void;
  state: PostcodeTestState;
  loading: boolean;
}) {
  const [value, setValue] = useState(state.postcode);

  return (
    <div className="rounded-xl bg-[#161623] border border-white/[0.08] p-4">
      <div className="flex items-center gap-2 mb-2.5">
        <MapPin size={14} strokeWidth={1.5} className="text-[#C7FF3D]" />
        <span className="font-mono text-[10px] tracking-wider uppercase text-white/60">
          Uji Poskod
        </span>
      </div>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          if (value.trim().length >= 4) onSubmit(value.trim());
        }}
        className="flex gap-2"
      >
        <input
          type="text"
          inputMode="numeric"
          maxLength={5}
          value={value}
          onChange={(e) => setValue(e.target.value.replace(/\D/g, ''))}
          placeholder="Cth: 40000"
          className="flex-1 min-w-0 h-10 px-3 rounded-lg bg-white/[0.04] border border-white/[0.08] text-sm text-white font-mono placeholder:text-white/30 focus:outline-none focus:border-[#C7FF3D]/60"
        />
        <button
          type="submit"
          disabled={loading || value.length < 4}
          className="inline-flex items-center justify-center h-10 px-3 rounded-lg bg-white/[0.06] hover:bg-white/[0.1] text-white font-geist font-medium text-sm disabled:opacity-50 disabled:cursor-not-allowed transition"
          aria-label="Cari poskod"
        >
          <Search size={15} strokeWidth={1.5} />
        </button>
      </form>

      {loading && (
        <div className="mt-3 text-xs text-white/50">Mencari poskod…</div>
      )}

      {!loading && state.error && (
        <div className="mt-3 text-xs text-red-400">{state.error}</div>
      )}

      {!loading && state.notFound && (
        <div className="mt-3 text-xs text-white/60">
          Tiada zon meliputi alamat ini.
        </div>
      )}

      {!loading && state.result?.covered && (
        <div className="mt-3 px-3 py-2.5 rounded-lg bg-white/[0.04] border border-white/[0.08]">
          <div className="flex items-center gap-2">
            <span
              aria-hidden
              className="inline-block h-2.5 w-2.5 rounded-sm"
              style={{ backgroundColor: state.result.color ?? '#C7FF3D' }}
            />
            <span className="font-geist text-sm text-white">
              Diliputi oleh:{' '}
              <strong className="font-semibold">{state.result.name}</strong>
            </span>
          </div>
          <div className="mt-1 text-[11px] text-white/50 font-mono">
            RM {((state.result.fee_cents ?? 0) / 100).toFixed(2)} · min RM{' '}
            {((state.result.min_order_cents ?? 0) / 100).toFixed(0)}
          </div>
        </div>
      )}
    </div>
  );
}
