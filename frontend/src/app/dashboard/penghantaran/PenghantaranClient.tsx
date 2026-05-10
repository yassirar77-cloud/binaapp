'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import dynamic from 'next/dynamic';
import toast from 'react-hot-toast';
import {
  createZone,
  deleteZone,
  geocodeAddress,
  geocodePostcode,
  getOutletInfo,
  listZones,
  setOutletLocation,
  testPoint,
  updateZone,
} from './lib/api';
import { ringToPolygon } from './lib/polygon';
import type {
  Outlet,
  PostcodeTestResult,
  Zone,
} from './lib/types';
import LeftColumn from './components/LeftColumn';
import TopBar from './components/TopBar';
import RingSettingsModal, {
  makeDraftForNewRing,
  makeDraftFromZone,
  type RingDraft,
} from './components/RingSettingsModal';
import './penghantaran.css';

const MapPanel = dynamic(() => import('./components/MapPanel'), {
  ssr: false,
  loading: () => (
    <div className="h-full w-full bg-[#0f1424] flex items-center justify-center text-white/40 text-sm">
      Memuatkan peta…
    </div>
  ),
});

const DEFAULT_FIRST_RING_M = 3_000;
const RING_GAP_M = 2_000;

/** Sort zones by outer radius ascending (smallest ring first). */
function sortRings(zones: Zone[]): Zone[] {
  return [...zones].sort(
    (a, b) => (a.outer_radius_m ?? 0) - (b.outer_radius_m ?? 0),
  );
}

export default function PenghantaranClient({
  outlets,
}: {
  outlets: Outlet[];
}) {
  const [selectedOutletId, setSelectedOutletId] = useState<string | null>(
    outlets[0]?.id ?? null,
  );
  // Local outlet record we can mutate after location updates without
  // reloading the page.
  const [outletInfo, setOutletInfo] = useState<Outlet | null>(null);
  const [outletLoading, setOutletLoading] = useState(false);

  const [zones, setZones] = useState<Zone[]>([]);
  const [zonesLoading, setZonesLoading] = useState(false);
  const [hoveredZoneId, setHoveredZoneId] = useState<string | null>(null);

  const [draft, setDraft] = useState<{
    ring: RingDraft;
    innerRadiusM: number;
    maxOuterRadiusM: number | null;
  } | null>(null);
  const [saving, setSaving] = useState(false);

  const [outletPickerMode, setOutletPickerMode] = useState(false);

  const [postcodeState, setPostcodeState] = useState<{
    postcode: string;
    result?: PostcodeTestResult;
    notFound?: boolean;
    error?: string;
  }>({ postcode: '' });
  const [postcodeLoading, setPostcodeLoading] = useState(false);
  const [postcodePin, setPostcodePin] = useState<{ lat: number; lng: number } | null>(null);

  const selectedOutletRow = useMemo(
    () => outlets.find((o) => o.id === selectedOutletId) ?? null,
    [outlets, selectedOutletId],
  );

  // The outlet object used by the map combines server info with the row data
  // so we always show the freshest lat/lng.
  const outlet = outletInfo ?? selectedOutletRow;

  const sortedZones = useMemo(() => sortRings(zones), [zones]);
  const hasOutletLocation = !!(outlet?.lat && outlet?.lng);

  // Load outlet info + zones when outlet changes
  useEffect(() => {
    if (!selectedOutletId) {
      setZones([]);
      setOutletInfo(null);
      return;
    }
    let cancelled = false;
    (async () => {
      setOutletLoading(true);
      setZonesLoading(true);
      try {
        const [info, zoneList] = await Promise.all([
          getOutletInfo(selectedOutletId),
          listZones(selectedOutletId),
        ]);
        if (cancelled) return;
        setZones(zoneList);
        const next: Outlet = {
          id: info.id,
          name: info.business_name || info.name || 'Outlet',
          subdomain: selectedOutletRow?.subdomain ?? '',
          lat: info.lat,
          lng: info.lng,
          location_address: info.location_address,
          business_name: info.business_name,
        };
        setOutletInfo(next);

        // Auto-geocode if we have an address but no pin yet.
        if (!info.lat && info.location_address) {
          try {
            const geo = await geocodeAddress(info.location_address);
            if (cancelled) return;
            if (geo.found) {
              await setOutletLocation(info.id, geo.lat, geo.lng);
              if (cancelled) return;
              setOutletInfo({ ...next, lat: geo.lat, lng: geo.lng });
              toast.success(
                'Lokasi kedai diset secara automatik dari alamat anda.',
              );
            }
          } catch {
            // Auto-geocode is best-effort. Owner can pin manually.
          }
        }
      } catch (e) {
        if (!cancelled) {
          const msg = e instanceof Error ? e.message : 'ralat';
          toast.error(`Gagal memuatkan: ${msg}`);
          setZones([]);
        }
      } finally {
        if (!cancelled) {
          setOutletLoading(false);
          setZonesLoading(false);
        }
      }
    })();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedOutletId]);

  // Auto-clear postcode pin after 30s
  useEffect(() => {
    if (!postcodePin) return;
    const t = setTimeout(() => setPostcodePin(null), 30000);
    return () => clearTimeout(t);
  }, [postcodePin]);

  // ---------------- Outlet picker ----------------
  const handleToggleOutletPicker = useCallback(() => {
    setOutletPickerMode((m) => !m);
  }, []);

  const handleOutletPick = useCallback(
    async (lat: number, lng: number) => {
      if (!selectedOutletId) return;
      setOutletPickerMode(false);
      try {
        await setOutletLocation(selectedOutletId, lat, lng);
        setOutletInfo((prev) =>
          prev ? { ...prev, lat, lng } : prev,
        );
        toast.success('Lokasi kedai dikemaskini');
      } catch (e) {
        const msg = e instanceof Error ? e.message : 'ralat';
        toast.error(`Gagal kemaskini lokasi: ${msg}`);
      }
    },
    [selectedOutletId],
  );

  // ---------------- Ring CRUD ----------------
  const handleAddRing = useCallback(() => {
    if (!hasOutletLocation) {
      toast.error('Tetapkan lokasi kedai dahulu');
      return;
    }
    const maxOuter = sortedZones.length
      ? sortedZones[sortedZones.length - 1].outer_radius_m ?? 0
      : 0;
    const suggested = maxOuter > 0 ? maxOuter + RING_GAP_M : DEFAULT_FIRST_RING_M;
    const innerRadiusM = maxOuter;
    setDraft({
      ring: makeDraftForNewRing(suggested),
      innerRadiusM,
      maxOuterRadiusM: null,
    });
  }, [hasOutletLocation, sortedZones]);

  const handleEditZone = useCallback(
    (zone: Zone) => {
      const idx = sortedZones.findIndex((z) => z.id === zone.id);
      const prev = idx > 0 ? sortedZones[idx - 1] : null;
      const next = idx < sortedZones.length - 1 ? sortedZones[idx + 1] : null;
      const innerRadiusM = prev?.outer_radius_m ?? 0;
      const maxOuterRadiusM = next?.outer_radius_m ?? null;
      setDraft({
        ring: makeDraftFromZone(zone),
        innerRadiusM,
        maxOuterRadiusM,
      });
    },
    [sortedZones],
  );

  const handleDeleteZone = useCallback(async (zone: Zone) => {
    if (!window.confirm(`Padam ring "${zone.name}"?`)) return;
    try {
      await deleteZone(zone.id);
      setZones((zs) => zs.filter((z) => z.id !== zone.id));
      toast.success('Ring dipadam');
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'ralat';
      toast.error(`Gagal padam: ${msg}`);
    }
  }, []);

  const handleToggleActive = useCallback(
    async (zone: Zone, active: boolean) => {
      const prev = zones;
      setZones((zs) => zs.map((z) => (z.id === zone.id ? { ...z, active } : z)));
      try {
        await updateZone(zone.id, { active });
      } catch (e) {
        setZones(prev);
        const msg = e instanceof Error ? e.message : 'ralat';
        toast.error(`Gagal kemaskini: ${msg}`);
      }
    },
    [zones],
  );

  const handleSaveRing = useCallback(
    async (next: RingDraft) => {
      if (!selectedOutletId || !outlet?.lat || !outlet?.lng) {
        toast.error('Lokasi kedai diperlukan');
        return;
      }
      const innerRadiusM = draft?.innerRadiusM ?? 0;
      const polygon = ringToPolygon(outlet.lat, outlet.lng, next.outer_radius_m);
      setSaving(true);
      try {
        if (next.id) {
          const updated = await updateZone(next.id, {
            name: next.name,
            color: next.color,
            fee_cents: next.fee_cents,
            min_order_cents: next.min_order_cents,
            polygon,
            schedule_json: next.schedule_json,
            estimated_delivery_min: next.estimated_delivery_min,
            max_simultaneous_orders: next.max_simultaneous_orders,
            customer_notes: next.customer_notes.trim() || null,
            active: next.active,
            inner_radius_m: innerRadiusM,
            outer_radius_m: next.outer_radius_m,
          });
          setZones((zs) => zs.map((z) => (z.id === next.id ? updated : z)));

          // If outer radius changed, the next ring's inner_radius_m metadata
          // is stale — push the cascade so the UI label matches reality.
          const sorted = sortRings(
            zones.map((z) => (z.id === next.id ? updated : z)),
          );
          const idx = sorted.findIndex((z) => z.id === next.id);
          const after = idx >= 0 && idx < sorted.length - 1 ? sorted[idx + 1] : null;
          if (after && (after.inner_radius_m ?? 0) !== next.outer_radius_m) {
            try {
              const cascadePolygon = ringToPolygon(
                outlet.lat,
                outlet.lng,
                after.outer_radius_m ?? 0,
              );
              const cascaded = await updateZone(after.id, {
                polygon: cascadePolygon,
                inner_radius_m: next.outer_radius_m,
                outer_radius_m: after.outer_radius_m ?? undefined,
              });
              setZones((zs) =>
                zs.map((z) => (z.id === after.id ? cascaded : z)),
              );
            } catch {
              // Non-fatal — UI label may temporarily lag.
            }
          }
          toast.success('Ring dikemaskini');
        } else {
          const created = await createZone(selectedOutletId, {
            name: next.name,
            color: next.color,
            fee_cents: next.fee_cents,
            min_order_cents: next.min_order_cents,
            polygon,
            schedule_json: next.schedule_json,
            estimated_delivery_min: next.estimated_delivery_min,
            max_simultaneous_orders: next.max_simultaneous_orders,
            customer_notes: next.customer_notes.trim() || null,
            active: next.active,
            inner_radius_m: innerRadiusM,
            outer_radius_m: next.outer_radius_m,
          });
          setZones((zs) => [...zs, created]);
          toast.success('Ring ditambah');
        }
        setDraft(null);
      } finally {
        setSaving(false);
      }
    },
    [selectedOutletId, outlet, draft, zones],
  );

  // ---------------- Postcode test ----------------
  const handlePostcodeSubmit = useCallback(
    async (postcode: string) => {
      if (!selectedOutletId) return;
      setPostcodeLoading(true);
      setPostcodeState({ postcode });
      setPostcodePin(null);
      try {
        const geo = await geocodePostcode(postcode);
        if (!geo.found || geo.lat == null || geo.lng == null) {
          setPostcodeState({
            postcode,
            error: 'Poskod tidak ditemui.',
          });
          return;
        }
        setPostcodePin({ lat: geo.lat, lng: geo.lng });
        const zone = await testPoint(selectedOutletId, geo.lat, geo.lng);
        setPostcodeState({
          postcode,
          result: zone,
          notFound: !zone.covered,
        });
      } catch {
        setPostcodeState({
          postcode,
          error: 'Tidak dapat mencari poskod, cuba lagi.',
        });
      } finally {
        setPostcodeLoading(false);
      }
    },
    [selectedOutletId],
  );

  // ---------------- No-outlets state ----------------
  if (outlets.length === 0) {
    return (
      <div className="penghantaran-root flex items-center justify-center px-6">
        <div className="text-center max-w-sm">
          <h2 className="font-geist font-semibold text-lg text-white">
            Tambah outlet pertama anda
          </h2>
          <p className="mt-2 text-sm text-white/60">
            Anda perlu sekurang-kurangnya satu website untuk menetapkan zon
            penghantaran.
          </p>
          <a
            href="/create"
            className="inline-block mt-5 px-4 py-2.5 rounded-lg bg-[#C7FF3D] text-black font-geist font-semibold text-sm hover:brightness-110 transition"
          >
            Cipta Website
          </a>
        </div>
      </div>
    );
  }

  return (
    <div className="penghantaran-root flex flex-col h-screen overflow-hidden">
      <TopBar
        outlets={outlets}
        selectedOutletId={selectedOutletId}
        onOutletChange={setSelectedOutletId}
        zones={sortedZones}
      />

      <div className="flex-1 grid grid-cols-1 md:grid-cols-[40%_60%] overflow-hidden">
        <div className="order-2 md:order-1 h-full overflow-hidden border-t md:border-t-0 md:border-r border-white/[0.08]">
          <LeftColumn
            zones={sortedZones}
            loading={zonesLoading || outletLoading}
            hasOutletLocation={hasOutletLocation}
            outletAddress={outlet?.location_address ?? null}
            outletPickerMode={outletPickerMode}
            onToggleOutletPicker={handleToggleOutletPicker}
            onAddRing={handleAddRing}
            onHoverZone={setHoveredZoneId}
            onEditZone={handleEditZone}
            onDeleteZone={handleDeleteZone}
            onToggleActive={handleToggleActive}
            postcodeState={postcodeState}
            postcodeLoading={postcodeLoading}
            onPostcodeSubmit={handlePostcodeSubmit}
          />
        </div>
        <div className="order-1 md:order-2 h-[40vh] md:h-full">
          <MapPanel
            outlet={outlet}
            zones={sortedZones}
            hoveredZoneId={hoveredZoneId}
            outletPickerMode={outletPickerMode}
            onOutletPick={handleOutletPick}
            postcodePin={postcodePin}
          />
        </div>
      </div>

      {draft && (
        <RingSettingsModal
          draft={draft.ring}
          innerRadiusM={draft.innerRadiusM}
          maxOuterRadiusM={draft.maxOuterRadiusM}
          onClose={() => {
            if (!saving) setDraft(null);
          }}
          onSave={handleSaveRing}
          saving={saving}
        />
      )}
    </div>
  );
}
