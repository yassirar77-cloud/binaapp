'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import dynamic from 'next/dynamic';
import toast from 'react-hot-toast';
import {
  createZone,
  deleteZone,
  geocodePostcode,
  listZones,
  testPoint,
  updateZone,
} from './lib/api';
import type {
  GeoJSONPolygon,
  Outlet,
  PostcodeTestResult,
  Zone,
  ZoneInput,
} from './lib/types';
import LeftColumn from './components/LeftColumn';
import TopBar from './components/TopBar';
import ZoneSettingsModal, {
  makeDraftForNew,
  makeDraftFromZone,
  type ZoneDraft,
} from './components/ZoneSettingsModal';
import './penghantaran.css';

// Map is heavy + uses window — load client-only
const MapPanel = dynamic(() => import('./components/MapPanel'), {
  ssr: false,
  loading: () => (
    <div className="h-full w-full bg-[#0f1424] flex items-center justify-center text-white/40 text-sm">
      Memuatkan peta…
    </div>
  ),
});

export default function PenghantaranClient({
  outlets,
}: {
  outlets: Outlet[];
}) {
  const [selectedOutletId, setSelectedOutletId] = useState<string | null>(
    outlets[0]?.id ?? null,
  );
  const [zones, setZones] = useState<Zone[]>([]);
  const [zonesLoading, setZonesLoading] = useState(false);
  const [hoveredZoneId, setHoveredZoneId] = useState<string | null>(null);
  const [draft, setDraft] = useState<ZoneDraft | null>(null);
  const [saving, setSaving] = useState(false);
  const [isDrawing, setIsDrawing] = useState(false);
  const [postcodeState, setPostcodeState] = useState<{
    postcode: string;
    result?: PostcodeTestResult;
    notFound?: boolean;
    error?: string;
  }>({ postcode: '' });
  const [postcodeLoading, setPostcodeLoading] = useState(false);
  const [postcodePin, setPostcodePin] = useState<{ lat: number; lng: number } | null>(null);

  const selectedOutlet = useMemo(
    () => outlets.find((o) => o.id === selectedOutletId) ?? null,
    [outlets, selectedOutletId],
  );

  // Load zones whenever outlet changes
  useEffect(() => {
    if (!selectedOutletId) {
      setZones([]);
      return;
    }
    let cancelled = false;
    (async () => {
      setZonesLoading(true);
      try {
        const data = await listZones(selectedOutletId);
        if (cancelled) return;
        setZones(data);
      } catch (e: any) {
        if (!cancelled) {
          toast.error(`Gagal memuatkan zon: ${e?.message ?? 'ralat'}`);
          setZones([]);
        }
      } finally {
        if (!cancelled) setZonesLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [selectedOutletId]);

  // Outlet missing lat/lng warning (one-shot)
  useEffect(() => {
    if (selectedOutlet && !selectedOutlet.lat) {
      const id = setTimeout(() => {
        toast(
          'Set lokasi outlet di Tetapan dahulu untuk memusatkan peta.',
          { icon: 'ℹ️' },
        );
      }, 600);
      return () => clearTimeout(id);
    }
  }, [selectedOutlet]);

  // Auto-clear postcode pin after 30s
  useEffect(() => {
    if (!postcodePin) return;
    const t = setTimeout(() => setPostcodePin(null), 30000);
    return () => clearTimeout(t);
  }, [postcodePin]);

  const handleAddZone = useCallback(() => {
    if (!selectedOutletId) {
      toast.error('Pilih outlet dahulu');
      return;
    }
    if (typeof window !== 'undefined' && window.innerWidth < 768) {
      toast('Lukis zon di komputer untuk pengalaman terbaik', { icon: '💻' });
      return;
    }
    setIsDrawing(true);
  }, [selectedOutletId]);

  const handleDrawComplete = useCallback((polygon: GeoJSONPolygon) => {
    setIsDrawing(false);
    setDraft(makeDraftForNew(polygon));
  }, []);

  const handleDrawCancel = useCallback(() => {
    setIsDrawing(false);
  }, []);

  const handleEditZone = useCallback((zone: Zone) => {
    setDraft(makeDraftFromZone(zone));
  }, []);

  const handleDeleteZone = useCallback(async (zone: Zone) => {
    if (!window.confirm(`Padam zon "${zone.name}"?`)) return;
    try {
      await deleteZone(zone.id);
      setZones((zs) => zs.filter((z) => z.id !== zone.id));
      toast.success('Zon dipadam');
    } catch (e: any) {
      toast.error(`Gagal padam: ${e?.message ?? 'ralat'}`);
    }
  }, []);

  const handleToggleActive = useCallback(
    async (zone: Zone, active: boolean) => {
      const prev = zones;
      setZones((zs) => zs.map((z) => (z.id === zone.id ? { ...z, active } : z)));
      try {
        await updateZone(zone.id, { active });
      } catch (e: any) {
        setZones(prev);
        toast.error(`Gagal kemaskini: ${e?.message ?? 'ralat'}`);
      }
    },
    [zones],
  );

  const handleSaveZone = useCallback(
    async (payload: ZoneInput, id?: string) => {
      if (!selectedOutletId) return;
      setSaving(true);
      try {
        if (id) {
          const updated = await updateZone(id, payload);
          setZones((zs) => zs.map((z) => (z.id === id ? updated : z)));
          toast.success('Zon dikemaskini');
        } else {
          const created = await createZone(selectedOutletId, payload);
          setZones((zs) => [...zs, created]);
          toast.success('Zon ditambah');
        }
        setDraft(null);
      } finally {
        setSaving(false);
      }
    },
    [selectedOutletId],
  );

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
      } catch (e: any) {
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

  // No outlets at all
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
        zones={zones}
      />

      <div className="flex-1 grid grid-cols-1 md:grid-cols-[40%_60%] overflow-hidden">
        <div className="order-2 md:order-1 h-full overflow-hidden border-t md:border-t-0 md:border-r border-white/[0.08]">
          <LeftColumn
            zones={zones}
            loading={zonesLoading}
            isDrawing={isDrawing}
            onAddZone={handleAddZone}
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
            outlet={selectedOutlet}
            zones={zones}
            hoveredZoneId={hoveredZoneId}
            isDrawing={isDrawing}
            onDrawComplete={handleDrawComplete}
            onDrawCancel={handleDrawCancel}
            postcodePin={postcodePin}
          />
        </div>
      </div>

      {draft && (
        <ZoneSettingsModal
          draft={draft}
          onClose={() => {
            if (!saving) setDraft(null);
          }}
          onSave={handleSaveZone}
          saving={saving}
        />
      )}
    </div>
  );
}
