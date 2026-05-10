'use client';

import { useEffect, useState } from 'react';
import { X } from 'lucide-react';
import {
  DAY_LABELS,
  DEFAULT_SCHEDULE,
  SWATCHES,
} from '../lib/constants';
import { polygonHasSelfIntersection } from '../lib/polygon';
import type {
  GeoJSONPolygon,
  ScheduleJson,
  Zone,
  ZoneInput,
} from '../lib/types';

type Tab = 'umum' | 'jadual' | 'lanjutan';

export interface ZoneDraft {
  /** existing zone id, if editing */
  id?: string;
  name: string;
  color: string;
  fee_cents: number;
  min_order_cents: number;
  polygon: GeoJSONPolygon;
  schedule_json: ScheduleJson;
  estimated_delivery_min: number;
  max_simultaneous_orders: number;
  customer_notes: string;
  active: boolean;
}

export function makeDraftFromZone(z: Zone): ZoneDraft {
  return {
    id: z.id,
    name: z.name,
    color: z.color,
    fee_cents: z.fee_cents,
    min_order_cents: z.min_order_cents,
    polygon: z.polygon,
    schedule_json: z.schedule_json,
    estimated_delivery_min: z.estimated_delivery_min ?? 30,
    max_simultaneous_orders: z.max_simultaneous_orders ?? 10,
    customer_notes: z.customer_notes ?? '',
    active: z.active,
  };
}

export function makeDraftForNew(polygon: GeoJSONPolygon): ZoneDraft {
  return {
    name: 'Zon Baru',
    color: SWATCHES[0],
    fee_cents: 500,
    min_order_cents: 2000,
    polygon,
    schedule_json: DEFAULT_SCHEDULE,
    estimated_delivery_min: 30,
    max_simultaneous_orders: 10,
    customer_notes: '',
    active: true,
  };
}

export default function ZoneSettingsModal({
  draft: initial,
  onClose,
  onSave,
  saving,
}: {
  draft: ZoneDraft;
  onClose: () => void;
  onSave: (draft: ZoneInput, id?: string) => Promise<void>;
  saving: boolean;
}) {
  const [tab, setTab] = useState<Tab>('umum');
  const [draft, setDraft] = useState<ZoneDraft>(initial);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);

  const update = <K extends keyof ZoneDraft>(key: K, value: ZoneDraft[K]) => {
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

  const handleSave = async () => {
    setError(null);
    if (!draft.name.trim()) {
      setError('Nama zon diperlukan.');
      setTab('umum');
      return;
    }
    if (polygonHasSelfIntersection(draft.polygon)) {
      setError('Sempadan zon tidak boleh bersilang.');
      return;
    }
    const noActiveDay = !Object.values(draft.schedule_json).some(
      (d) => d.active,
    );
    if (noActiveDay) {
      // Warn but allow save (per prompt)
      const ok = window.confirm(
        'Zon ini tiada hari aktif — pelanggan tidak akan boleh order. Teruskan?',
      );
      if (!ok) {
        setTab('jadual');
        return;
      }
    }
    const payload: ZoneInput = {
      name: draft.name.trim(),
      color: draft.color,
      fee_cents: draft.fee_cents,
      min_order_cents: draft.min_order_cents,
      polygon: draft.polygon,
      schedule_json: draft.schedule_json,
      estimated_delivery_min: draft.estimated_delivery_min,
      max_simultaneous_orders: draft.max_simultaneous_orders,
      customer_notes: draft.customer_notes.trim() || null,
      active: draft.active,
    };
    try {
      await onSave(payload, draft.id);
    } catch (e: any) {
      setError(e?.message || 'Gagal menyimpan zon.');
    }
  };

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
              {draft.id ? 'Edit Zon' : 'Zon Baru'}
            </div>
            <div className="font-geist font-semibold text-base text-white">
              Tetapan Zon
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
          {(
            [
              { key: 'umum' as Tab, label: 'Umum' },
              { key: 'jadual' as Tab, label: 'Jadual' },
              { key: 'lanjutan' as Tab, label: 'Lanjutan' },
            ]
          ).map((t) => (
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
          {tab === 'umum' && (
            <>
              <Field label="Nama Zon">
                <input
                  type="text"
                  value={draft.name}
                  onChange={(e) => update('name', e.target.value)}
                  placeholder="Cth: Shah Alam Tengah"
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
                    Pelanggan boleh order ke zon ini
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
              {(Object.keys(DAY_LABELS) as Array<keyof ScheduleJson>).map(
                (day) => {
                  const d = draft.schedule_json[day];
                  return (
                    <div
                      key={day}
                      className="flex items-center gap-3 px-3 py-2 rounded-lg bg-white/[0.04] border border-white/[0.08]"
                    >
                      <input
                        type="checkbox"
                        checked={d.active}
                        onChange={(e) =>
                          updateDay(day, { active: e.target.checked })
                        }
                        className="h-4 w-4 accent-[#C7FF3D]"
                        aria-label={DAY_LABELS[day]}
                      />
                      <div className="flex-1 font-geist text-sm text-white">
                        {DAY_LABELS[day]}
                      </div>
                      <input
                        type="time"
                        value={d.open}
                        onChange={(e) =>
                          updateDay(day, { open: e.target.value })
                        }
                        disabled={!d.active}
                        className="modal-input modal-input-sm font-mono"
                      />
                      <span className="text-white/40">–</span>
                      <input
                        type="time"
                        value={d.close}
                        onChange={(e) =>
                          updateDay(day, { close: e.target.value })
                        }
                        disabled={!d.active}
                        className="modal-input modal-input-sm font-mono"
                      />
                    </div>
                  );
                },
              )}
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
                      update(
                        'estimated_delivery_min',
                        Math.max(0, Number(e.target.value)),
                      )
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
                      update(
                        'max_simultaneous_orders',
                        Math.max(0, Number(e.target.value)),
                      )
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
            disabled={saving}
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
