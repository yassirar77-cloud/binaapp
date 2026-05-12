'use client';

// ReassignModal — pick an idle rider for an order.
// "Idle" = is_online AND no active_order_id. Calls PATCH /live/orders/{id}/rider.

import { useMemo, useState } from 'react';
import { Bike, X } from 'lucide-react';
import toast from 'react-hot-toast';
import { reassignRider } from '../lib/api';
import type { ActiveOrder, LiveRider } from '../lib/types';
import { computeRiderPresence } from '../lib/types';

interface Props {
  order: ActiveOrder;
  riders: LiveRider[];
  onClose: () => void;
  onSuccess: () => void;
}

function isIdle(r: LiveRider): boolean {
  return computeRiderPresence(r) !== 'offline' && !r.active_order_id;
}

export default function ReassignModal({ order, riders, onClose, onSuccess }: Props) {
  const idleRiders = useMemo(
    () => riders.filter((r) => isIdle(r) && r.id !== order.rider_id),
    [riders, order.rider_id],
  );

  const [pickedId, setPickedId] = useState<string | null>(
    idleRiders[0]?.id ?? null,
  );
  const [submitting, setSubmitting] = useState(false);

  const submit = async () => {
    if (!pickedId) return;
    setSubmitting(true);
    try {
      await reassignRider(order.id, pickedId);
      const picked = idleRiders.find((r) => r.id === pickedId);
      toast.success(`Pesanan ditukar kepada ${picked?.name ?? 'rider'}`);
      onSuccess();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'Gagal menukar rider');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <ModalShell onClose={onClose} title="Tukar rider">
      <p className="text-[13px] text-white/60 font-geist mb-3">
        Pilih rider yang idle untuk pesanan <span className="font-mono text-white/80">{order.order_number}</span>.
      </p>

      {idleRiders.length === 0 ? (
        <div className="rounded-lg bg-white/[0.04] border border-white/[0.06] px-3 py-4 text-center">
          <Bike size={18} strokeWidth={1.5} className="mx-auto text-white/40" />
          <p className="mt-2 text-sm text-white/60 font-geist">
            Tiada rider idle.
          </p>
          <p className="mt-1 text-[12px] text-white/40 font-geist">
            Tetapkan rider sebagai online di Penghantar dulu.
          </p>
        </div>
      ) : (
        <ul className="space-y-1.5 max-h-[300px] overflow-y-auto">
          {idleRiders.map((r) => (
            <li key={r.id}>
              <label
                className={`flex items-center justify-between gap-2 rounded-lg px-3 py-2.5 cursor-pointer border transition ${
                  pickedId === r.id
                    ? 'bg-white/[0.06] border-white/[0.16]'
                    : 'bg-[#161623] border-white/[0.06] hover:border-white/[0.12]'
                }`}
              >
                <span className="flex items-center gap-2 min-w-0">
                  <input
                    type="radio"
                    name="rider"
                    checked={pickedId === r.id}
                    onChange={() => setPickedId(r.id)}
                    className="accent-[#C7FF3D] w-4 h-4 shrink-0"
                  />
                  <span className="min-w-0">
                    <span className="block text-sm font-geist text-white truncate">
                      {r.name}
                    </span>
                    {r.vehicle_plate && (
                      <span className="block font-mono text-[11px] text-white/50">
                        {r.vehicle_plate}
                      </span>
                    )}
                  </span>
                </span>
                <span className="font-mono text-[11px] text-white/50">
                  {r.today_deliveries} hantaran
                </span>
              </label>
            </li>
          ))}
        </ul>
      )}

      <div className="mt-4 flex items-center justify-end gap-2">
        <button
          type="button"
          onClick={onClose}
          disabled={submitting}
          className="h-11 px-4 rounded-lg text-sm font-geist text-white/70 hover:text-white hover:bg-white/[0.06] transition disabled:opacity-50"
        >
          Batal
        </button>
        <button
          type="button"
          onClick={submit}
          disabled={!pickedId || submitting}
          className="h-11 px-4 rounded-lg text-sm font-geist font-medium bg-[#C7FF3D] text-[#0a0e1a] hover:bg-[#d2ff5a] transition disabled:opacity-40 disabled:cursor-not-allowed"
        >
          {submitting ? 'Menyimpan…' : 'Sahkan tukar rider'}
        </button>
      </div>
    </ModalShell>
  );
}

function ModalShell({
  onClose,
  title,
  children,
}: {
  onClose: () => void;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div
      className="fixed inset-0 z-[2000] flex items-end sm:items-center justify-center bg-black/50 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="w-full sm:w-[440px] sm:max-w-[90vw] bg-[#0a0e1a] border border-white/[0.08] rounded-t-2xl sm:rounded-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between gap-2 px-4 pt-4 pb-3 border-b border-white/[0.06]">
          <h3 className="text-base font-geist font-semibold text-white">{title}</h3>
          <button
            type="button"
            onClick={onClose}
            aria-label="Tutup"
            className="h-10 w-10 -mr-2 flex items-center justify-center rounded-lg text-white/60 hover:text-white hover:bg-white/[0.06] transition"
          >
            <X size={18} strokeWidth={1.5} />
          </button>
        </div>
        <div className="px-4 py-4">{children}</div>
      </div>
    </div>
  );
}
