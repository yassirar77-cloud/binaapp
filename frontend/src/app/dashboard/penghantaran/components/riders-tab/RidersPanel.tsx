'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { Bike, Plus, Search, X } from 'lucide-react';
import toast from 'react-hot-toast';
import { confirmDialog } from '@/components/ui/popups';
import {
  ApiError,
  createRider,
  deleteRider,
  listRiders,
  updateRider,
} from '../../lib/api';
import type { Rider, RiderLimitDetail } from '../../lib/types';
import RiderCard from './RiderCard';
import RiderModal, {
  makeFormForNewRider,
  makeFormFromRider,
  toCreateInput,
  toUpdateInput,
  type RiderFormValues,
} from './RiderModal';

const RIDER_LIMIT_FALLBACK = 'Had rider dicapai untuk pelan anda';

function isLimitDetail(detail: unknown): detail is RiderLimitDetail {
  return (
    !!detail &&
    typeof detail === 'object' &&
    (detail as { error?: unknown }).error === 'limit_reached'
  );
}

type ModalState =
  | { mode: 'create' }
  | { mode: 'edit'; rider: Rider }
  | null;

export default function RidersPanel({
  websiteId,
}: {
  websiteId: string | null;
}) {
  const [riders, setRiders] = useState<Rider[]>([]);
  const [loading, setLoading] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [modal, setModal] = useState<ModalState>(null);
  const [saving, setSaving] = useState(false);
  const [handoverPhone, setHandoverPhone] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!websiteId) {
      setRiders([]);
      return;
    }
    setLoading(true);
    setLoadError(null);
    try {
      const list = await listRiders(websiteId);
      setRiders(list);
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'ralat';
      setLoadError(msg);
      setRiders([]);
    } finally {
      setLoading(false);
    }
  }, [websiteId]);

  useEffect(() => {
    setSearch('');
    setHandoverPhone(null);
    setModal(null);
    void load();
  }, [load]);

  const onlineCount = useMemo(
    () => riders.filter((r) => r.is_online).length,
    [riders],
  );

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return riders;
    return riders.filter(
      (r) =>
        r.name.toLowerCase().includes(q) ||
        (r.phone ?? '').toLowerCase().includes(q) ||
        (r.vehicle_plate ?? '').toLowerCase().includes(q),
    );
  }, [riders, search]);

  const handleSave = useCallback(
    async (values: RiderFormValues) => {
      if (!websiteId || !modal) return;
      setSaving(true);
      try {
        if (modal.mode === 'create') {
          const created = await createRider(websiteId, toCreateInput(values));
          setRiders((rs) => [...rs, created]);
          setModal(null);
          setHandoverPhone(created.phone || values.phone.trim());
          toast.success('Rider ditambah');
        } else {
          const updated = await updateRider(
            modal.rider.id,
            toUpdateInput(values),
          );
          setRiders((rs) =>
            rs.map((r) => (r.id === updated.id ? updated : r)),
          );
          setModal(null);
          toast.success('Rider dikemaskini');
        }
      } catch (e) {
        if (e instanceof ApiError && e.status === 403 && isLimitDetail(e.detail)) {
          const msg = e.detail.message || RIDER_LIMIT_FALLBACK;
          toast.error(msg);
          throw new Error(msg);
        }
        throw e;
      } finally {
        setSaving(false);
      }
    },
    [websiteId, modal],
  );

  const handleDelete = useCallback(async (rider: Rider) => {
    const ok = await confirmDialog({
      title: 'Padam rider?',
      message: `Padam rider "${rider.name}"? Tindakan ini tidak boleh dibuat asal.`,
      confirmText: 'Padam',
      cancelText: 'Batal',
      variant: 'danger',
    });
    if (!ok) return;
    try {
      await deleteRider(rider.id);
      setRiders((rs) => rs.filter((r) => r.id !== rider.id));
      toast.success('Rider dipadam');
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'ralat';
      toast.error(`Gagal padam: ${msg}`);
    }
  }, []);

  return (
    <div className="space-y-4">
      {/* Header row */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <div className="font-mono text-[10px] tracking-wider uppercase text-white/50">
            Rider Penghantaran
          </div>
          <div className="font-geist font-semibold text-base text-white">
            {riders.length} rider{' '}
            <span className="text-white/40 font-normal">·</span>{' '}
            <span className="text-emerald-400">{onlineCount} online</span>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <div className="relative flex-1 sm:flex-none">
            <Search
              size={14}
              strokeWidth={1.5}
              className="absolute left-3 top-1/2 -translate-y-1/2 text-white/40 pointer-events-none"
            />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Cari nama, telefon, plat…"
              className="h-9 w-full sm:w-56 pl-9 pr-3 rounded-lg bg-white/[0.04] border border-white/[0.08] text-sm text-white font-geist placeholder:text-white/30 focus:outline-none focus:border-white/[0.16]"
            />
          </div>
          <button
            type="button"
            onClick={() => setModal({ mode: 'create' })}
            disabled={!websiteId}
            className="inline-flex items-center gap-1.5 h-9 px-3 rounded-lg bg-[#C7FF3D] text-black font-geist font-semibold text-sm hover:brightness-110 disabled:opacity-40 disabled:cursor-not-allowed transition shrink-0"
          >
            <Plus size={14} strokeWidth={2} />
            Tambah Rider
          </button>
        </div>
      </div>

      {/* Post-create handover hint */}
      {handoverPhone && (
        <div className="flex items-start justify-between gap-3 px-4 py-3 rounded-xl bg-[#C7FF3D]/10 border border-[#C7FF3D]/30">
          <div className="text-[12px] leading-relaxed text-white/80">
            Berikan nombor telefon{' '}
            <span className="font-mono text-white">{handoverPhone}</span> &amp;
            kata laluan ini kepada rider untuk log masuk di{' '}
            <span className="font-mono text-white">/rider</span>.
          </div>
          <button
            type="button"
            onClick={() => setHandoverPhone(null)}
            className="p-1 rounded-md text-white/50 hover:text-white hover:bg-white/[0.06] transition shrink-0"
            aria-label="Tutup"
          >
            <X size={14} strokeWidth={1.5} />
          </button>
        </div>
      )}

      {/* List */}
      {loading ? (
        <div className="space-y-2.5">
          {[0, 1, 2].map((i) => (
            <div
              key={i}
              className="h-[74px] rounded-xl bg-white/[0.04] animate-pulse"
            />
          ))}
        </div>
      ) : loadError ? (
        <div className="flex flex-col items-center justify-center text-center px-6 py-10 rounded-xl bg-white/[0.02] border border-white/[0.06]">
          <p className="text-sm text-red-400">Gagal memuatkan rider: {loadError}</p>
          <button
            type="button"
            onClick={() => void load()}
            className="mt-4 h-9 px-4 rounded-lg bg-white/[0.06] text-white font-geist text-sm font-medium hover:bg-white/[0.1] transition"
          >
            Cuba Semula
          </button>
        </div>
      ) : riders.length === 0 ? (
        <div className="flex flex-col items-center justify-center text-center px-6 py-10 rounded-xl bg-white/[0.02] border border-white/[0.06]">
          <Bike size={28} strokeWidth={1.5} className="text-white/30 mb-2" />
          <h3 className="font-geist font-semibold text-base text-white">
            Tiada rider lagi
          </h3>
          <p className="mt-1 text-sm text-white/60 max-w-xs">
            Tambah rider pertama anda untuk mula menghantar pesanan sendiri.
          </p>
          <button
            type="button"
            onClick={() => setModal({ mode: 'create' })}
            disabled={!websiteId}
            className="mt-5 inline-flex items-center gap-1.5 px-4 py-2.5 rounded-lg bg-[#C7FF3D] text-black font-geist font-semibold text-sm hover:brightness-110 disabled:opacity-40 transition"
          >
            <Plus size={16} strokeWidth={2} />
            Tambah Rider
          </button>
        </div>
      ) : filtered.length === 0 ? (
        <div className="px-6 py-8 text-center text-sm text-white/50 rounded-xl bg-white/[0.02] border border-white/[0.06]">
          Tiada rider sepadan dengan &quot;{search.trim()}&quot;.
        </div>
      ) : (
        <div className="space-y-2.5">
          {filtered.map((r) => (
            <RiderCard
              key={r.id}
              rider={r}
              onEdit={(rider) => setModal({ mode: 'edit', rider })}
              onDelete={handleDelete}
            />
          ))}
        </div>
      )}

      {modal && (
        <RiderModal
          mode={modal.mode}
          initial={
            modal.mode === 'edit'
              ? makeFormFromRider(modal.rider)
              : makeFormForNewRider()
          }
          onClose={() => {
            if (!saving) setModal(null);
          }}
          onSave={handleSave}
          saving={saving}
        />
      )}
    </div>
  );
}
