'use client';

import { useEffect, useState } from 'react';
import { Eye, EyeOff, X } from 'lucide-react';
import type { Rider, RiderCreateInput, RiderUpdateInput } from '../../lib/types';
import { VEHICLE_TYPE_OPTIONS } from './vehicle';

export interface RiderFormValues {
  name: string;
  phone: string;
  email: string;
  password: string;
  vehicle_type: string;
  vehicle_plate: string;
  vehicle_model: string;
  is_active: boolean;
}

export function makeFormForNewRider(): RiderFormValues {
  return {
    name: '',
    phone: '',
    email: '',
    password: '',
    vehicle_type: 'motorcycle',
    vehicle_plate: '',
    vehicle_model: '',
    is_active: true,
  };
}

export function makeFormFromRider(r: Rider): RiderFormValues {
  return {
    name: r.name ?? '',
    phone: r.phone ?? '',
    email: r.email ?? '',
    password: '',
    vehicle_type: r.vehicle_type || 'motorcycle',
    vehicle_plate: r.vehicle_plate ?? '',
    vehicle_model: r.vehicle_model ?? '',
    is_active: r.is_active,
  };
}

/** Build the POST payload from a validated form. */
export function toCreateInput(v: RiderFormValues): RiderCreateInput {
  return {
    name: v.name.trim(),
    phone: v.phone.trim(),
    ...(v.email.trim() ? { email: v.email.trim() } : {}),
    vehicle_type: v.vehicle_type,
    ...(v.vehicle_plate.trim() ? { vehicle_plate: v.vehicle_plate.trim() } : {}),
    ...(v.vehicle_model.trim() ? { vehicle_model: v.vehicle_model.trim() } : {}),
    is_active: v.is_active,
    password: v.password,
  };
}

/** Build the PUT payload from a validated form (password only when set). */
export function toUpdateInput(v: RiderFormValues): RiderUpdateInput {
  return {
    name: v.name.trim(),
    phone: v.phone.trim(),
    email: v.email.trim(),
    vehicle_type: v.vehicle_type,
    vehicle_plate: v.vehicle_plate.trim(),
    vehicle_model: v.vehicle_model.trim(),
    is_active: v.is_active,
    ...(v.password ? { password: v.password } : {}),
  };
}

export default function RiderModal({
  mode,
  initial,
  onClose,
  onSave,
  saving,
}: {
  mode: 'create' | 'edit';
  initial: RiderFormValues;
  onClose: () => void;
  onSave: (values: RiderFormValues) => Promise<void>;
  saving: boolean;
}) {
  const [form, setForm] = useState<RiderFormValues>(initial);
  const [error, setError] = useState<string | null>(null);
  const [showPassword, setShowPassword] = useState(false);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);

  const update = <K extends keyof RiderFormValues>(
    key: K,
    value: RiderFormValues[K],
  ) => {
    setForm((f) => ({ ...f, [key]: value }));
  };

  const validate = (): string | null => {
    if (!form.name.trim()) return 'Nama rider diperlukan.';
    if (!form.phone.trim()) return 'Nombor telefon diperlukan.';
    if (
      form.email.trim() &&
      !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email.trim())
    ) {
      return 'Format emel tidak sah.';
    }
    if (mode === 'create' && !form.password) {
      return 'Kata laluan diperlukan.';
    }
    if (form.password && form.password.length < 6) {
      return 'Kata laluan mesti sekurang-kurangnya 6 aksara.';
    }
    return null;
  };

  const handleSave = async () => {
    const err = validate();
    setError(err);
    if (err) return;
    try {
      await onSave(form);
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Gagal menyimpan rider.';
      setError(msg);
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
              {mode === 'create' ? 'Rider Baru' : 'Edit Rider'}
            </div>
            <div className="font-geist font-semibold text-base text-white">
              {mode === 'create' ? 'Tambah Rider' : 'Tetapan Rider'}
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

        <div className="flex-1 overflow-y-auto px-5 py-4 space-y-4">
          <Field label="Nama *">
            <input
              type="text"
              value={form.name}
              onChange={(e) => update('name', e.target.value)}
              placeholder="Cth: Ahmad Faiz"
              className="modal-input"
              maxLength={120}
            />
          </Field>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <Field label="No. Telefon *">
              <input
                type="tel"
                value={form.phone}
                onChange={(e) => update('phone', e.target.value)}
                placeholder="Cth: 0123456789"
                className="modal-input font-mono"
                maxLength={20}
              />
            </Field>
            <Field label="Emel">
              <input
                type="email"
                value={form.email}
                onChange={(e) => update('email', e.target.value)}
                placeholder="pilihan"
                className="modal-input"
                maxLength={120}
              />
            </Field>
          </div>

          <Field
            label={mode === 'create' ? 'Kata Laluan *' : 'Kata Laluan Baru'}
          >
            <div className="relative">
              <input
                type={showPassword ? 'text' : 'password'}
                value={form.password}
                onChange={(e) => update('password', e.target.value)}
                placeholder={
                  mode === 'create'
                    ? 'Min 6 aksara'
                    : 'Biar kosong jika tiada perubahan'
                }
                className="modal-input pr-10"
                maxLength={60}
                autoComplete="new-password"
              />
              <button
                type="button"
                onClick={() => setShowPassword((s) => !s)}
                className="absolute right-2 top-1/2 -translate-y-1/2 p-1.5 rounded-md text-white/50 hover:text-white transition"
                aria-label={
                  showPassword ? 'Sembunyi kata laluan' : 'Tunjuk kata laluan'
                }
              >
                {showPassword ? (
                  <EyeOff size={16} strokeWidth={1.5} />
                ) : (
                  <Eye size={16} strokeWidth={1.5} />
                )}
              </button>
            </div>
            {mode === 'edit' && (
              <div className="mt-1 text-[11px] text-white/50">
                Isi hanya untuk reset kata laluan rider (min 6 aksara).
              </div>
            )}
          </Field>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <Field label="Jenis Kenderaan">
              <select
                value={form.vehicle_type}
                onChange={(e) => update('vehicle_type', e.target.value)}
                className="modal-input appearance-none"
              >
                {VEHICLE_TYPE_OPTIONS.map((o) => (
                  <option key={o.value} value={o.value} className="bg-[#161623]">
                    {o.label}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="No. Plat">
              <input
                type="text"
                value={form.vehicle_plate}
                onChange={(e) =>
                  update('vehicle_plate', e.target.value.toUpperCase())
                }
                placeholder="Cth: WXY 1234"
                className="modal-input font-mono uppercase"
                maxLength={20}
              />
            </Field>
          </div>

          <Field label="Model Kenderaan">
            <input
              type="text"
              value={form.vehicle_model}
              onChange={(e) => update('vehicle_model', e.target.value)}
              placeholder="Cth: Yamaha LC135"
              className="modal-input"
              maxLength={80}
            />
          </Field>

          <label className="flex items-center justify-between gap-3 px-3 py-2.5 rounded-lg bg-white/[0.04] border border-white/[0.08] cursor-pointer">
            <div>
              <div className="font-geist text-sm text-white">Aktif</div>
              <div className="text-[11px] text-white/50">
                Rider boleh terima pesanan
              </div>
            </div>
            <input
              type="checkbox"
              checked={form.is_active}
              onChange={(e) => update('is_active', e.target.checked)}
              className="h-4 w-4 accent-[#C7FF3D]"
            />
          </label>

          {mode === 'create' && (
            <div className="px-3 py-2.5 rounded-lg bg-[#4F3DFF]/10 border border-[#4F3DFF]/30 text-[11px] leading-relaxed text-white/70">
              Rider akan log masuk menggunakan{' '}
              <span className="text-white">nombor telefon</span> dan{' '}
              <span className="text-white">kata laluan</span> di{' '}
              <span className="font-mono text-white">/rider</span>.
            </div>
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
            {saving
              ? 'Menyimpan…'
              : mode === 'create'
                ? 'Tambah Rider'
                : 'Simpan'}
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
