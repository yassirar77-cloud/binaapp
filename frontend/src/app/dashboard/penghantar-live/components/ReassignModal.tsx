'use client';

// ReassignModal — pick an idle rider for an order.
// "Idle" = is_online AND no active_order_id. Calls PATCH /live/orders/{id}/rider.
// Riders are ranked by straight-line distance to the delivery point so the
// nearest sensible choice is pre-selected.

import { useMemo, useState } from 'react';
import { Bike } from 'lucide-react';
import toast from 'react-hot-toast';
import { Modal } from '@/components/ui/popups';
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

function haversineKm(
  lat1: number,
  lng1: number,
  lat2: number,
  lng2: number,
): number {
  const toRad = (d: number) => (d * Math.PI) / 180;
  const dLat = toRad(lat2 - lat1);
  const dLng = toRad(lng2 - lng1);
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLng / 2) ** 2;
  return 2 * 6371 * Math.asin(Math.sqrt(a));
}

type RankedRider = LiveRider & { distanceKm: number | null };

export default function ReassignModal({ order, riders, onClose, onSuccess }: Props) {
  const idleRiders = useMemo<RankedRider[]>(() => {
    const dest =
      order.delivery_latitude != null && order.delivery_longitude != null
        ? { lat: order.delivery_latitude, lng: order.delivery_longitude }
        : null;
    return riders
      .filter((r) => isIdle(r) && r.id !== order.rider_id)
      .map((r) => ({
        ...r,
        distanceKm:
          dest && r.current_latitude != null && r.current_longitude != null
            ? haversineKm(
                r.current_latitude,
                r.current_longitude,
                dest.lat,
                dest.lng,
              )
            : null,
      }))
      // Nearest first; riders without GPS sink to the bottom, then by workload.
      .sort((a, b) => {
        if (a.distanceKm != null && b.distanceKm != null) {
          return a.distanceKm - b.distanceKm;
        }
        if (a.distanceKm != null) return -1;
        if (b.distanceKm != null) return 1;
        return a.today_deliveries - b.today_deliveries;
      });
  }, [riders, order.rider_id, order.delivery_latitude, order.delivery_longitude]);

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
    <Modal open onClose={onClose} title="Tukar rider" className="sm:max-w-[440px]">
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
          {idleRiders.map((r, idx) => (
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
                    <span className="flex items-center gap-1.5 min-w-0">
                      <span className="text-sm font-geist text-white truncate">
                        {r.name}
                      </span>
                      {idx === 0 && r.distanceKm != null && (
                        <span className="shrink-0 h-4 px-1.5 rounded-full font-mono text-[9px] tracking-wider uppercase bg-[#C7FF3D]/15 text-[#C7FF3D] ring-1 ring-[#C7FF3D]/25">
                          Terdekat
                        </span>
                      )}
                    </span>
                    {r.vehicle_plate && (
                      <span className="block font-mono text-[11px] text-white/50">
                        {r.vehicle_plate}
                      </span>
                    )}
                  </span>
                </span>
                <span className="text-right shrink-0">
                  {r.distanceKm != null && (
                    <span className="block font-mono text-[11px] text-white/70">
                      {r.distanceKm < 10
                        ? `${r.distanceKm.toFixed(1)} km`
                        : `${Math.round(r.distanceKm)} km`}
                    </span>
                  )}
                  <span className="block font-mono text-[11px] text-white/50">
                    {r.today_deliveries} hantaran
                  </span>
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
    </Modal>
  );
}
