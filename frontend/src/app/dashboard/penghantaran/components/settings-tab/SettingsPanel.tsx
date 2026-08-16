'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { AlertTriangle } from 'lucide-react';
import toast from 'react-hot-toast';
import { getDeliverySettings, updateDeliverySettings } from '../../lib/api';
import type {
  DeliverySettings,
  DeliverySettingsUpdate,
} from '../../lib/types';

// ----- Form model (numbers kept as strings for friendly editing) -----

interface SettingsForm {
  delivery_enabled: boolean;
  default_delivery_fee: string;
  minimum_order: string;
  max_delivery_distance: string;
  pickup_enabled: boolean;
  pickup_address: string;
  accept_cod: boolean;
  accept_online: boolean;
  accept_ewallet: boolean;
  notify_whatsapp: boolean;
  whatsapp_number: string;
  notify_email: boolean;
  notify_sound: boolean;
}

/** API numeric values may arrive as number or decimal string. */
function numToInput(v: number | string | null | undefined): string {
  if (v == null || v === '') return '';
  const n = Number(v);
  return Number.isFinite(n) ? String(n) : '';
}

function normalize(s: DeliverySettings): SettingsForm {
  return {
    delivery_enabled: !!s.delivery_enabled,
    default_delivery_fee: numToInput(s.default_delivery_fee),
    minimum_order: numToInput(s.minimum_order),
    max_delivery_distance: numToInput(s.max_delivery_distance),
    pickup_enabled: !!s.pickup_enabled,
    pickup_address: s.pickup_address ?? '',
    accept_cod: !!s.accept_cod,
    accept_online: !!s.accept_online,
    accept_ewallet: !!s.accept_ewallet,
    notify_whatsapp: !!s.notify_whatsapp,
    whatsapp_number: s.whatsapp_number ?? '',
    notify_email: !!s.notify_email,
    notify_sound: !!s.notify_sound,
  };
}

const BOOL_KEYS = [
  'delivery_enabled',
  'pickup_enabled',
  'accept_cod',
  'accept_online',
  'accept_ewallet',
  'notify_whatsapp',
  'notify_email',
  'notify_sound',
] as const;

const NUMERIC_KEYS = [
  'default_delivery_fee',
  'minimum_order',
  'max_delivery_distance',
] as const;

const NUMERIC_LABELS: Record<(typeof NUMERIC_KEYS)[number], string> = {
  default_delivery_fee: 'Yuran penghantaran',
  minimum_order: 'Pesanan minimum',
  max_delivery_distance: 'Jarak maksimum',
};

const STRING_KEYS = ['pickup_address', 'whatsapp_number'] as const;

/**
 * Build a partial update containing only modified keys.
 * Returns an error message (Malay) if a changed numeric value is invalid.
 */
function buildPatch(
  initial: SettingsForm,
  form: SettingsForm,
): { patch: DeliverySettingsUpdate } | { error: string } {
  const patch: DeliverySettingsUpdate = {};
  for (const k of BOOL_KEYS) {
    if (form[k] !== initial[k]) patch[k] = form[k];
  }
  for (const k of NUMERIC_KEYS) {
    if (form[k] !== initial[k]) {
      const n = Number(form[k]);
      if (form[k].trim() === '' || !Number.isFinite(n) || n < 0) {
        return {
          error: `${NUMERIC_LABELS[k]}: sila masukkan nombor yang sah.`,
        };
      }
      patch[k] = n;
    }
  }
  for (const k of STRING_KEYS) {
    if (form[k] !== initial[k]) patch[k] = form[k].trim();
  }
  return { patch };
}

// ----- Component -----

export default function SettingsPanel({
  websiteId,
}: {
  websiteId: string | null;
}) {
  const [initial, setInitial] = useState<SettingsForm | null>(null);
  const [form, setForm] = useState<SettingsForm | null>(null);
  const [loading, setLoading] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    if (!websiteId) {
      setInitial(null);
      setForm(null);
      return;
    }
    setLoading(true);
    setLoadError(null);
    try {
      const settings = await getDeliverySettings(websiteId);
      const normalized = normalize(settings);
      setInitial(normalized);
      setForm(normalized);
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'ralat';
      setLoadError(msg);
      setInitial(null);
      setForm(null);
    } finally {
      setLoading(false);
    }
  }, [websiteId]);

  useEffect(() => {
    void load();
  }, [load]);

  const update = useCallback(
    <K extends keyof SettingsForm>(key: K, value: SettingsForm[K]) => {
      setForm((f) => (f ? { ...f, [key]: value } : f));
    },
    [],
  );

  const dirty = useMemo(() => {
    if (!initial || !form) return false;
    return (Object.keys(form) as Array<keyof SettingsForm>).some(
      (k) => form[k] !== initial[k],
    );
  }, [initial, form]);

  const handleSave = useCallback(async () => {
    if (!websiteId || !initial || !form || saving) return;
    const built = buildPatch(initial, form);
    if ('error' in built) {
      toast.error(built.error);
      return;
    }
    if (Object.keys(built.patch).length === 0) return;
    setSaving(true);
    try {
      const updated = await updateDeliverySettings(websiteId, built.patch);
      const normalized = normalize(updated);
      setInitial(normalized);
      setForm(normalized);
      toast.success('Tetapan disimpan');
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'ralat';
      toast.error(`Gagal menyimpan: ${msg}`);
    } finally {
      setSaving(false);
    }
  }, [websiteId, initial, form, saving]);

  // ----- Loading / error states -----

  if (loading || (!form && !loadError)) {
    return (
      <div className="space-y-4">
        {[0, 1, 2, 3].map((i) => (
          <div
            key={i}
            className="h-[120px] rounded-xl bg-white/[0.04] animate-pulse"
          />
        ))}
      </div>
    );
  }

  if (loadError || !form) {
    return (
      <div className="flex flex-col items-center justify-center text-center px-6 py-10 rounded-xl bg-white/[0.02] border border-white/[0.06]">
        <p className="text-sm text-red-400">
          Gagal memuatkan tetapan: {loadError ?? 'ralat'}
        </p>
        <button
          type="button"
          onClick={() => void load()}
          className="mt-4 h-9 px-4 rounded-lg bg-white/[0.06] text-white font-geist text-sm font-medium hover:bg-white/[0.1] transition"
        >
          Cuba Semula
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* 1. Penghantaran */}
      <SectionCard eyebrow="Penghantaran">
        <ToggleRow
          title="Terima pesanan penghantaran"
          description="Matikan untuk menjeda semua pesanan delivery serta-merta."
          checked={form.delivery_enabled}
          onChange={(v) => update('delivery_enabled', v)}
          prominent
        />
        {!form.delivery_enabled && (
          <div className="flex items-start gap-2.5 px-3 py-2.5 rounded-lg bg-amber-500/10 border border-amber-500/20">
            <AlertTriangle
              size={15}
              strokeWidth={1.5}
              className="text-amber-400 mt-0.5 shrink-0"
            />
            <div className="text-[12px] leading-relaxed text-amber-300">
              Penghantaran dijeda — pelanggan tidak boleh membuat pesanan
              delivery.
            </div>
          </div>
        )}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <Field label="Yuran Penghantaran (RM)">
            <input
              type="number"
              min={0}
              step={0.5}
              value={form.default_delivery_fee}
              onChange={(e) => update('default_delivery_fee', e.target.value)}
              className="modal-input font-mono"
            />
          </Field>
          <Field label="Pesanan Minimum (RM)">
            <input
              type="number"
              min={0}
              step={1}
              value={form.minimum_order}
              onChange={(e) => update('minimum_order', e.target.value)}
              className="modal-input font-mono"
            />
          </Field>
          <Field label="Jarak Maksimum (KM)">
            <input
              type="number"
              min={0}
              step={0.5}
              value={form.max_delivery_distance}
              onChange={(e) => update('max_delivery_distance', e.target.value)}
              className="modal-input font-mono"
            />
          </Field>
        </div>
      </SectionCard>

      {/* 2. Pengambilan (Pickup) */}
      <SectionCard eyebrow="Pengambilan (Pickup)">
        <ToggleRow
          title="Benarkan pengambilan sendiri"
          description="Pelanggan boleh pilih ambil pesanan di kedai."
          checked={form.pickup_enabled}
          onChange={(v) => update('pickup_enabled', v)}
        />
        {form.pickup_enabled && (
          <Field label="Alamat Pengambilan">
            <textarea
              value={form.pickup_address}
              onChange={(e) => update('pickup_address', e.target.value)}
              rows={3}
              maxLength={400}
              placeholder="Cth: 12, Jalan Melur 3, Taman Sri Melur, 43000 Kajang"
              className="modal-input"
            />
          </Field>
        )}
      </SectionCard>

      {/* 3. Pembayaran */}
      <SectionCard eyebrow="Pembayaran">
        <ToggleRow
          title="Tunai semasa terima (COD)"
          description="Pelanggan bayar tunai kepada rider."
          checked={form.accept_cod}
          onChange={(v) => update('accept_cod', v)}
        />
        <ToggleRow
          title="Pembayaran online"
          description="FPX / kad melalui gerbang pembayaran."
          checked={form.accept_online}
          onChange={(v) => update('accept_online', v)}
        />
        <ToggleRow
          title="E-Wallet"
          description="Touch 'n Go, GrabPay dan lain-lain."
          checked={form.accept_ewallet}
          onChange={(v) => update('accept_ewallet', v)}
        />
      </SectionCard>

      {/* 4. Notifikasi */}
      <SectionCard eyebrow="Notifikasi">
        <ToggleRow
          title="Notifikasi WhatsApp"
          description="Terima makluman pesanan baru melalui WhatsApp."
          checked={form.notify_whatsapp}
          onChange={(v) => update('notify_whatsapp', v)}
        />
        {form.notify_whatsapp && (
          <Field label="Nombor WhatsApp">
            <input
              type="tel"
              value={form.whatsapp_number}
              onChange={(e) => update('whatsapp_number', e.target.value)}
              placeholder="Cth: 60123456789"
              className="modal-input font-mono"
              maxLength={20}
            />
          </Field>
        )}
        <ToggleRow
          title="Notifikasi emel"
          description="Terima makluman pesanan baru melalui emel."
          checked={form.notify_email}
          onChange={(v) => update('notify_email', v)}
        />
        <ToggleRow
          title="Bunyi notifikasi"
          description="Mainkan bunyi apabila pesanan baru masuk."
          checked={form.notify_sound}
          onChange={(v) => update('notify_sound', v)}
        />
      </SectionCard>

      {/* Sticky save bar */}
      <div className="sticky bottom-0 z-10 -mx-1 px-1 py-3 bg-[#0a0e1a]/95 backdrop-blur-sm border-t border-white/[0.08] flex items-center justify-end gap-3">
        {dirty && !saving && (
          <span className="text-[11px] text-white/50">
            Perubahan belum disimpan
          </span>
        )}
        <button
          type="button"
          onClick={handleSave}
          disabled={!dirty || saving}
          className="h-10 px-5 rounded-lg bg-[#C7FF3D] text-black hover:brightness-110 font-geist text-sm font-semibold transition disabled:opacity-40 disabled:cursor-not-allowed"
        >
          {saving ? 'Menyimpan…' : 'Simpan Tetapan'}
        </button>
      </div>
    </div>
  );
}

// ----- Small building blocks -----

function SectionCard({
  eyebrow,
  children,
}: {
  eyebrow: string;
  children: React.ReactNode;
}) {
  return (
    <section className="rounded-xl bg-[#161623] border border-white/[0.08] px-4 sm:px-5 py-4 space-y-3.5">
      <div className="font-mono text-[10px] tracking-wider uppercase text-white/50">
        {eyebrow}
      </div>
      {children}
    </section>
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

function ToggleRow({
  title,
  description,
  checked,
  onChange,
  prominent = false,
}: {
  title: string;
  description?: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
  prominent?: boolean;
}) {
  return (
    <label
      className={`flex items-center justify-between gap-3 cursor-pointer rounded-lg transition ${
        prominent
          ? 'px-3 py-3 bg-white/[0.04] border border-white/[0.08]'
          : 'px-3 py-2.5 bg-white/[0.02] border border-white/[0.06] hover:border-white/[0.12]'
      }`}
    >
      <div className="min-w-0">
        <div
          className={`font-geist text-white ${
            prominent ? 'text-sm font-semibold' : 'text-sm'
          }`}
        >
          {title}
        </div>
        {description && (
          <div className="mt-0.5 text-[11px] text-white/50">{description}</div>
        )}
      </div>
      <span className="relative inline-flex items-center shrink-0">
        <input
          type="checkbox"
          className="sr-only peer"
          checked={checked}
          onChange={(e) => onChange(e.target.checked)}
        />
        <span className="block w-9 h-5 bg-white/10 rounded-full peer-checked:bg-[#C7FF3D] transition" />
        <span className="absolute left-0.5 top-0.5 w-4 h-4 bg-white rounded-full transition peer-checked:translate-x-4" />
      </span>
    </label>
  );
}
