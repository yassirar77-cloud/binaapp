'use client';

import { useEffect, useMemo, useState } from 'react';
import { X } from 'lucide-react';
import {
  DAY_LABELS,
  DEFAULT_SCHEDULE,
  SWATCHES,
} from '../lib/constants';
import { formatDistance } from '../lib/polygon';
import type { ScheduleJson, Zone } from '../lib/types';

type Tab = 'asas' | 'jadual' | 'lanjutan';

const MIN_RADIUS_M = 500;     // 0.5 km
const MAX_RADIUS_M = 15_000;  // 15 km
const RADIUS_STEP_M = 500;    // 0.5 km
const DEFAULT_RADIUS_M = 3_000;

export interface RingDraft {
  /** existing zone id, if editing */
  id?: string;
  name: string;
  color: string;
  fee_cents: number;
  min_order_cents: number;
  outer_radius_m: number;
  schedule_json: ScheduleJson;
  estimated_delivery_min: number;
  max_simultaneous_orders: number;
  customer_notes: string;
  active: boolean;
}

export function makeDraftForNewRing(suggestedOuterM: number): RingDraft {
  return {
    name: 'Ring Baru',
    color: SWATCHES[0],
    fee_cents: 500,
    min_order_cents: 2000,
    outer_radius_m: suggestedOuterM,
    schedule_json: DEFAULT_SCHEDULE,
    estimated_delivery_min: 30,
    max_simultaneous_orders: 10,
    customer_notes: '',
    active: true,
  };
}

export function makeDraftFromZone(z: Zone): RingDraft {
  return {
    id: z.id,
    name: z.name,
    color: z.color,
    fee_cents: z.fee_cents,
    min_order_cents: z.min_order_cents,
    outer_radius_m: z.outer_radius_m ?? DEFAULT_RADIUS_M,
    schedule_json: z.schedule_json,
    estimated_delivery_min: z.estimated_delivery_min ?? 30,
    max_simultaneous_orders: z.max_simultaneous_orders ?? 10,
    customer_notes: z.customer_notes ?? '',
    active: z.active,
  };
}

export default function RingSettingsModal({
  draft: initial,
  innerRadiusM,
  maxOuterRadiusM,
  onClose,
  onSave,
  saving,
}: {
  draft: RingDraft;
  /** Auto-derived inner radius (previous ring's outer, or 0). Display-only. */
  innerRadiusM: number;
  /** When editing, the next ring's outer radius — outer must stay strictly less than this. */
  maxOuterRadiusM: number | null;
  onClose: () => void;
  onSave: (draft: RingDraft) => Promise<void>;
  saving: boolean;
}) {
  const [tab, setTab] = useState<Tab>('asas');
  const [draft, setDraft] = useState<RingDraft>(initial);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);

  const update = <K extends keyof RingDraft>(key: K, value: RingDraft[K]) => {
    setDraft((d) => ({ ...d, [key]: value }));
  };

  const updateDay = (
    day: keyof ScheduleJson,
    patch: Partial<ScheduleJson[keyof ScheduleJson]>,
  ) => {
    setDraft((d) => ({
      ...d,
      schedule_json: {
        ...d.schedule_json,
        [day]: { ...d.schedule_json[day], ...patch },
      },
    }));
  };

  const minOuter = Math.max(innerRadiusM + RADIUS_STEP_M, MIN_RADIUS_M);
  const hardMax = maxOuterRadiusM != null
    ? Math.min(maxOuterRadiusM - RADIUS_STEP_M, MAX_RADIUS_M)
    : MAX_RADIUS_M;

  const radiusError = useMemo(() => {
    if (draft.outer_radius_m <= innerRadiusM) {
      return `Radius mesti melebihi ${formatDistance(innerRadiusM)} (ring sebelum)`;
    }
    if (maxOuterRadiusM != null && draft.outer_radius_m >= maxOuterRadiusM) {
      return `Radius mesti kurang daripada ${formatDistance(maxOuterRadiusM)} (ring selepas)`;
    }
    if (draft.outer_radius_m < MIN_RADIUS_M) {
      return `Radius minimum ${formatDistance(MIN_RADIUS_M)}`;
    }
    if (draft.outer_radius_m > MAX_RADIUS_M) {
      return `Radius maksimum ${formatDistance(MAX_RADIUS_M)}`;
    }
    return null;
  }, [draft.outer_radius_m, innerRadiusM, maxOuterRadiusM]);

  const handleSave = async () => {
    setError(null);
    if (!draft.name.trim()) {
      setError('Nama ring diperlukan.');
      setTab('asas');
      return;
    }
    if (radiusError) {
      setError(radiusError);
      setTab('asas');
      return;
    }
    const noActiveDay = !Object.values(draft.schedule_json).some((d) => d.active);
    if (noActiveDay) {
      const ok = window.confirm(
        'Ring ini tiada hari aktif — pelanggan tidak akan boleh order. Teruskan?',
      );
      if (!ok) {
        setTab('jadual');
        return;
      }
    }
    try {
      await onSave({ ...draft, name: draft.name.trim() });
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Gagal menyimpan ring.';
      setError(msg);
    }
  };

  const innerLabel = formatDistance(innerRadiusM);
  const outerLabel = formatDistance(draft.outer_radius_m);

  return (
    <div
      role="dialog"
      aria-modal="true"
      className="fixed inset-0 z-[1100] bg-black/60 backdrop-blur-sm flex items-stretch sm:items-center justify-center"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="w-full sm:max-w-lg sm:rounded-2xl bg-[#161623] border border-white/[0.08] flex flex-col max-h-[100dvh] sm:max-h-[90vh]">
        <div className="flex items-center justify-between px-5 py-4 border-b border-white/[0.08]">
          <div>
            <div className="font-mono text-[10px] tracking-wider uppercase text-white/50">
              {draft.id ? 'Edit Ring' : 'Ring Baru'}
            </div>
            <div className="font-geist font-semibold text-base text-white">
              Tetapan Ring
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-2 rounded-md text-white/60 hover:text-white hover:bg-white/[0.06] transition"
            aria-label="Tutup"
          >
            <X size={18} strokeWidth={1.5} />
          </button>
        </div>

        <div className="flex border-b border-white/[0.08] px-2">
          {([
            { key: 'asas' as Tab, label: 'Asas' },
            { key: 'jadual' as Tab, label: 'Jadual' },
            { key: 'lanjutan' as Tab, label: 'Lanjutan' },
          ]).map((t) => (
            <button
              key={t.key}
              type="button"
              onClick={() => setTab(t.key)}
              className={`px-4 py-3 font-geist font-medium text-sm transition border-b-2 -mb-px ${
                tab === t.key
                  ? 'text-white border-[#C7FF3D]'
                  : 'text-white/50 border-transparent hover:text-white/80'
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>

        <div className="flex-1 overflow-y-auto px-5 py-4 space-y-4">
          {tab === 'asas' && (
            <>
              <Field label="Nama Ring">
                <input
                  type="text"
                  value={draft.name}
                  onChange={(e) => update('name', e.target.value)}
                  placeholder="Cth: Ring Dekat"
                  className="modal-input"
                  maxLength={80}
                />
              </Field>

              <Field label="Warna">
                <div className="flex gap-2 flex-wrap">
                  {SWATCHES.map((c) => (
                    <button
                      key={c}
                      type="button"
                      onClick={() => update('color', c)}
                      className={`h-8 w-8 rounded-md transition ${
                        draft.color === c
                          ? 'ring-2 ring-white ring-offset-2 ring-offset-[#161623]'
                          : 'opacity-80 hover:opacity-100'
                      }`}
                      style={{ backgroundColor: c }}
                      aria-label={`Pilih warna ${c}`}
                    />
                  ))}
                </div>
              </Field>

              <Field
                label={`Radius Luar (${(draft.outer_radius_m / 1000).toFixed(1)} km)`}
              >
                <div className="flex items-center gap-3">
                  <input
                    type="number"
                    min={MIN_RADIUS_M / 1000}
                    max={MAX_RADIUS_M / 1000}
                    step={0.5}
                    value={(draft.outer_radius_m / 1000).toFixed(1)}
                    onChange={(e) => {
                      const km = Number(e.target.value);
                      if (!Number.isFinite(km)) return;
                      update('outer_radius_m', Math.round(km * 1000));
                    }}
                    className="modal-input font-mono w-28"
                  />
                  <input
                    type="range"
                    min={Math.max(MIN_RADIUS_M, minOuter)}
                    max={hardMax}
                    step={RADIUS_STEP_M}
                    value={Math.min(
                      Math.max(draft.outer_radius_m, MIN_RADIUS_M),
                      MAX_RADIUS_M,
                    )}
                    onChange={(e) => update('outer_radius_m', Number(e.target.value))}
                    className="flex-1 accent-[#C7FF3D]"
                    aria-label="Radius luar"
                  />
                </div>
                <div className="mt-2 text-[11px] text-white/50">
                  Ring ini akan liputi{' '}
                  <span className="font-mono text-white/80">{innerLabel}</span>{' '}
                  hingga{' '}
                  <span className="font-mono text-white/80">{outerLabel}</span>{' '}
                  dari kedai
                </div>
                {radiusError && (
                  <div className="mt-1 text-[11px] text-red-400">{radiusError}</div>
                )}
              </Field>

              <div className="grid grid-cols-2 gap-3">
                <Field label="Yuran Penghantaran (RM)">
                  <input
                    type="number"
                    min={0}
                    step={0.5}
                    value={(draft.fee_cents / 100).toString()}
                    onChange={(e) =>
                      update(
                        'fee_cents',
                        Math.max(0, Math.round(Number(e.target.value) * 100)),
                      )
                    }
                    className="modal-input font-mono"
                  />
                </Field>
                <Field label="Pesanan Minimum (RM)">
                  <input
                    type="number"
                    min={0}
                    step={1}
                    value={(draft.min_order_cents / 100).toString()}
                    onChange={(e) =>
                      update(
                        'min_order_cents',
                        Math.max(0, Math.round(Number(e.target.value) * 100)),
                      )
                    }
                    className="modal-input font-mono"
                  />
                </Field>
              </div>

              <label className="flex items-center justify-between gap-3 px-3 py-2.5 rounded-lg bg-white/[0.04] border border-white/[0.08]">
                <div>
                  <div className="font-geist text-sm text-white">Aktif</div>
                  <div className="text-[11px] text-white/50">
                    Pelanggan boleh order ke ring ini
                  </div>
                </div>
                <input
                  type="checkbox"
                  checked={draft.active}
                  onChange={(e) => update('active', e.target.checked)}
                  className="h-4 w-4 accent-[#C7FF3D]"
                />
              </label>
            </>
          )}

          {tab === 'jadual' && (
            <div className="space-y-2">
              {(Object.keys(DAY_LABELS) as Array<keyof ScheduleJson>).map((day) => {
                const d = draft.schedule_json[day];
                return (
                  <div
                    key={day}
                    className="flex items-center gap-3 px-3 py-2 rounded-lg bg-white/[0.04] border border-white/[0.08]"
                  >
                    <input
                      type="checkbox"
                      checked={d.active}
                      onChange={(e) => updateDay(day, { active: e.target.checked })}
                      className="h-4 w-4 accent-[#C7FF3D]"
                      aria-label={DAY_LABELS[day]}
                    />
                    <div className="flex-1 font-geist text-sm text-white">
                      {DAY_LABELS[day]}
                    </div>
                    <input
                      type="time"
                      value={d.open}
                      onChange={(e) => updateDay(day, { open: e.target.value })}
                      disabled={!d.active}
                      className="modal-input modal-input-sm font-mono"
                    />
                    <span className="text-white/40">–</span>
                    <input
                      type="time"
                      value={d.close}
                      onChange={(e) => updateDay(day, { close: e.target.value })}
                      disabled={!d.active}
                      className="modal-input modal-input-sm font-mono"
                    />
                  </div>
                );
              })}
            </div>
          )}

          {tab === 'lanjutan' && (
            <>
              <div className="grid grid-cols-2 gap-3">
                <Field label="Anggaran Masa (minit)">
                  <input
                    type="number"
                    min={5}
                    max={180}
                    value={draft.estimated_delivery_min}
                    onChange={(e) =>
                      update('estimated_delivery_min', Math.max(0, Number(e.target.value)))
                    }
                    className="modal-input font-mono"
                  />
                </Field>
                <Field label="Pesanan Serentak Maks">
                  <input
                    type="number"
                    min={1}
                    max={500}
                    value={draft.max_simultaneous_orders}
                    onChange={(e) =>
                      update('max_simultaneous_orders', Math.max(0, Number(e.target.value)))
                    }
                    className="modal-input font-mono"
                  />
                </Field>
              </div>
              <Field label="Nota untuk Pelanggan">
                <textarea
                  value={draft.customer_notes}
                  onChange={(e) => update('customer_notes', e.target.value)}
                  rows={3}
                  maxLength={300}
                  placeholder="Cth: Hanya delivery sebelum 9pm di kawasan ini."
                  className="modal-input"
                />
              </Field>
            </>
          )}
        </div>

        {error && (
          <div className="px-5 py-2.5 text-xs text-red-400 border-t border-white/[0.08]">
            {error}
          </div>
        )}

        <div className="flex items-center justify-end gap-2 px-5 py-4 border-t border-white/[0.08]">
          <button
            type="button"
            onClick={onClose}
            disabled={saving}
            className="h-10 px-4 rounded-lg text-white/70 hover:text-white hover:bg-white/[0.06] font-geist text-sm font-medium transition disabled:opacity-50"
          >
            Batal
          </button>
          <button
            type="button"
            onClick={handleSave}
            disabled={saving || !!radiusError}
            className="h-10 px-5 rounded-lg bg-[#C7FF3D] text-black hover:brightness-110 font-geist text-sm font-semibold transition disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {saving ? 'Menyimpan…' : 'Simpan'}
          </button>
        </div>
      </div>
    </div>
  );
}

function Field({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <label className="block">
      <div className="font-mono text-[10px] tracking-wider uppercase text-white/50 mb-1.5">
        {label}
      </div>
      {children}
    </label>
  );
}
