'use client';

import { useEffect, useRef, useState } from 'react';
import type { Map as LeafletMap, Marker, Polygon } from 'leaflet';
import {
  DEFAULT_CENTER,
  DEFAULT_ZOOM,
  TILE_ATTRIBUTION,
  TILE_URL,
} from '../lib/constants';
import { geoJSONToLatLngs } from '../lib/polygon';
import type { Outlet, Zone } from '../lib/types';

export interface MapPanelProps {
  outlet: Outlet | null;
  zones: Zone[];
  hoveredZoneId: string | null;
  outletPickerMode: boolean;
  onOutletPick: (lat: number, lng: number) => void;
  postcodePin: { lat: number; lng: number } | null;
}

export default function MapPanel({
  outlet,
  zones,
  hoveredZoneId,
  outletPickerMode,
  onOutletPick,
  postcodePin,
}: MapPanelProps) {
  const mapRef = useRef<LeafletMap | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const polygonsRef = useRef<Map<string, Polygon>>(new Map());
  const outletPinRef = useRef<Marker | null>(null);
  const postcodePinRef = useRef<Marker | null>(null);

  const [LRef, setLRef] = useState<typeof import('leaflet') | null>(null);

  // Init Leaflet (client-side only)
  useEffect(() => {
    let cancelled = false;
    (async () => {
      const L = (await import('leaflet')).default;
      if (typeof document !== 'undefined' && !document.getElementById('leaflet-css')) {
        const link = document.createElement('link');
        link.id = 'leaflet-css';
        link.rel = 'stylesheet';
        link.href = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css';
        document.head.appendChild(link);
      }
      if (cancelled) return;
      setLRef(() => L);
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  // Create map once Leaflet is loaded
  useEffect(() => {
    if (!LRef || !containerRef.current || mapRef.current) return;
    const L = LRef;
    const center: [number, number] =
      outlet?.lat && outlet?.lng ? [outlet.lat, outlet.lng] : DEFAULT_CENTER;
    const map = L.map(containerRef.current, {
      center,
      zoom: DEFAULT_ZOOM,
      zoomControl: true,
      attributionControl: true,
    });
    L.tileLayer(TILE_URL, {
      attribution: TILE_ATTRIBUTION,
      maxZoom: 19,
    }).addTo(map);
    mapRef.current = map;

    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, [LRef, outlet]);

  // Outlet pin
  useEffect(() => {
    if (!LRef || !mapRef.current) return;
    const L = LRef;
    if (outletPinRef.current) {
      outletPinRef.current.remove();
      outletPinRef.current = null;
    }
    if (!outlet?.lat || !outlet?.lng) return;
    const icon = L.divIcon({
      className: 'rest-pin-wrap',
      html: `<span class="rest-pin-pulse"></span><span class="rest-pin-dot"></span>`,
      iconSize: [22, 22],
      iconAnchor: [11, 11],
    });
    outletPinRef.current = L.marker([outlet.lat, outlet.lng], { icon }).addTo(
      mapRef.current,
    );
  }, [LRef, outlet]);

  // Render zones (each zone's polygon is already a 64-vertex ring approximation)
  useEffect(() => {
    if (!LRef || !mapRef.current) return;
    const L = LRef;
    const map = mapRef.current;
    const next = new Map<string, Polygon>();

    polygonsRef.current.forEach((poly) => poly.remove());
    polygonsRef.current.clear();

    for (const z of zones) {
      const ring = geoJSONToLatLngs(z.polygon);
      if (ring.length < 3) continue;
      const poly = L.polygon(ring, {
        color: z.color,
        fillColor: z.color,
        fillOpacity: z.active ? 0.3 : 0,
        weight: z.active ? 2 : 1.5,
        opacity: z.active ? 1 : 0.6,
        dashArray: z.active ? undefined : '6,4',
      }).addTo(map);
      const radiusLabel =
        z.outer_radius_m != null
          ? ` · ${(z.outer_radius_m / 1000).toFixed(1)} km`
          : '';
      poly.bindTooltip(`${z.name}${radiusLabel}`, {
        sticky: true,
        direction: 'top',
      });
      next.set(z.id, poly);
    }
    polygonsRef.current = next;
  }, [LRef, zones]);

  // Hover sync
  useEffect(() => {
    polygonsRef.current.forEach((poly, id) => {
      const el = (poly as unknown as { getElement?: () => SVGElement | null }).getElement?.();
      if (!el) return;
      if (id === hoveredZoneId) {
        el.classList.add('zone-pulse');
      } else {
        el.classList.remove('zone-pulse');
      }
    });
  }, [hoveredZoneId]);

  // Postcode pin
  useEffect(() => {
    if (!LRef || !mapRef.current) return;
    const L = LRef;
    if (postcodePinRef.current) {
      postcodePinRef.current.remove();
      postcodePinRef.current = null;
    }
    if (!postcodePin) return;
    const icon = L.divIcon({
      className: 'postcode-pin-wrap',
      html: `<svg width="22" height="28" viewBox="0 0 24 28" fill="none" stroke="#0a0e1a" stroke-width="1.5"><path d="M12 27s-9-9.5-9-15a9 9 0 1 1 18 0c0 5.5-9 15-9 15z" fill="#C7FF3D"/><circle cx="12" cy="11" r="3" fill="#0a0e1a"/></svg>`,
      iconSize: [22, 28],
      iconAnchor: [11, 28],
    });
    postcodePinRef.current = L.marker([postcodePin.lat, postcodePin.lng], {
      icon,
    }).addTo(mapRef.current);
    mapRef.current.setView([postcodePin.lat, postcodePin.lng], 14, {
      animate: true,
    });
  }, [LRef, postcodePin]);

  // Outlet picker — single click drops the pin via callback
  useEffect(() => {
    if (!LRef || !mapRef.current) return;
    const map = mapRef.current;
    if (containerRef.current) {
      containerRef.current.classList.toggle('outlet-picking', outletPickerMode);
    }
    if (!outletPickerMode) return;

    const handleClick = (e: { latlng: { lat: number; lng: number } }) => {
      onOutletPick(e.latlng.lat, e.latlng.lng);
    };
    map.on('click', handleClick);
    return () => {
      map.off('click', handleClick);
    };
  }, [LRef, outletPickerMode, onOutletPick]);

  // Recenter when outlet location changes (after a pick)
  useEffect(() => {
    if (!mapRef.current || !outlet?.lat || !outlet?.lng) return;
    mapRef.current.setView([outlet.lat, outlet.lng], DEFAULT_ZOOM, {
      animate: true,
    });
  }, [outlet?.lat, outlet?.lng]);

  return (
    <div className="relative h-full w-full">
      <div
        ref={containerRef}
        className="h-full w-full bg-[#0f1424]"
        aria-label="Peta zon penghantaran"
      />
      {outletPickerMode && (
        <div className="absolute top-4 left-1/2 -translate-x-1/2 z-[1000] px-4 py-2.5 rounded-lg bg-[#0a0e1a]/95 border border-white/[0.16] shadow-xl">
          <div className="font-geist text-xs text-white">
            Klik pada peta untuk tetapkan lokasi kedai
          </div>
        </div>
      )}
    </div>
  );
}
