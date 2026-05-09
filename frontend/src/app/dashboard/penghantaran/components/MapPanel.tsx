'use client';

import { useEffect, useRef, useState } from 'react';
import type { Map as LeafletMap, Marker, Polygon, Polyline, CircleMarker } from 'leaflet';
import {
  DEFAULT_CENTER,
  DEFAULT_ZOOM,
  TILE_ATTRIBUTION,
  TILE_URL,
} from '../lib/constants';
import { geoJSONToLatLngs, latLngsToGeoJSON } from '../lib/polygon';
import type { GeoJSONPolygon, Outlet, Zone } from '../lib/types';

export interface MapPanelProps {
  outlet: Outlet | null;
  zones: Zone[];
  hoveredZoneId: string | null;
  isDrawing: boolean;
  onDrawComplete: (polygon: GeoJSONPolygon) => void;
  onDrawCancel: () => void;
  postcodePin: { lat: number; lng: number } | null;
}

export default function MapPanel({
  outlet,
  zones,
  hoveredZoneId,
  isDrawing,
  onDrawComplete,
  onDrawCancel,
  postcodePin,
}: MapPanelProps) {
  const mapRef = useRef<LeafletMap | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const polygonsRef = useRef<Map<string, Polygon>>(new Map());
  const outletPinRef = useRef<Marker | null>(null);
  const postcodePinRef = useRef<Marker | null>(null);

  // Drawing state
  const drawVerticesRef = useRef<[number, number][]>([]);
  const drawPolylineRef = useRef<Polyline | null>(null);
  const drawDotsRef = useRef<CircleMarker[]>([]);

  const [LRef, setLRef] = useState<typeof import('leaflet') | null>(null);

  // Init Leaflet (client-side only)
  useEffect(() => {
    let cancelled = false;
    (async () => {
      const L = (await import('leaflet')).default;
      // CSS — only inject once
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

  // Render zones
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
      poly.bindTooltip(z.name, { sticky: true, direction: 'top' });
      next.set(z.id, poly);
    }
    polygonsRef.current = next;
  }, [LRef, zones]);

  // Hover sync
  useEffect(() => {
    polygonsRef.current.forEach((poly, id) => {
      const el = (poly as any).getElement?.() as SVGElement | null;
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

  // ---------------------------------------------------------------
  // Drawing flow
  // ---------------------------------------------------------------
  useEffect(() => {
    if (!LRef || !mapRef.current) return;
    const L = LRef;
    const map = mapRef.current;
    if (!isDrawing) {
      // cleanup any in-progress drawing
      drawVerticesRef.current = [];
      drawPolylineRef.current?.remove();
      drawPolylineRef.current = null;
      drawDotsRef.current.forEach((d) => d.remove());
      drawDotsRef.current = [];
      if (containerRef.current) {
        containerRef.current.classList.remove('drawing');
      }
      map.doubleClickZoom.enable();
      return;
    }

    if (containerRef.current) {
      containerRef.current.classList.add('drawing');
    }
    map.doubleClickZoom.disable();

    const redrawPolyline = () => {
      drawPolylineRef.current?.remove();
      if (drawVerticesRef.current.length >= 2) {
        drawPolylineRef.current = L.polyline(drawVerticesRef.current, {
          color: '#C7FF3D',
          weight: 2,
          dashArray: '4,4',
        }).addTo(map);
      }
    };

    const handleClick = (e: any) => {
      const pt: [number, number] = [e.latlng.lat, e.latlng.lng];
      drawVerticesRef.current = [...drawVerticesRef.current, pt];
      const dot = L.circleMarker(pt, {
        radius: 5,
        color: '#C7FF3D',
        fillColor: '#0a0e1a',
        fillOpacity: 1,
        weight: 2,
      }).addTo(map);
      drawDotsRef.current.push(dot);
      redrawPolyline();
    };

    const handleDoubleClick = () => {
      const v = drawVerticesRef.current;
      if (v.length < 3) return;
      const polygon = latLngsToGeoJSON(v);
      onDrawComplete(polygon);
    };

    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onDrawCancel();
      }
    };

    map.on('click', handleClick);
    map.on('dblclick', handleDoubleClick);
    window.addEventListener('keydown', handleKey);

    return () => {
      map.off('click', handleClick);
      map.off('dblclick', handleDoubleClick);
      window.removeEventListener('keydown', handleKey);
    };
  }, [LRef, isDrawing, onDrawComplete, onDrawCancel]);

  return (
    <div className="relative h-full w-full">
      <div
        ref={containerRef}
        className="h-full w-full bg-[#0f1424]"
        aria-label="Peta zon penghantaran"
      />
      {isDrawing && (
        <div className="absolute top-4 left-1/2 -translate-x-1/2 z-[1000] px-4 py-2.5 rounded-lg bg-[#0a0e1a]/95 border border-white/[0.16] shadow-xl">
          <div className="font-geist text-xs text-white">
            Klik untuk lukis sempadan ·{' '}
            <span className="font-mono text-[#C7FF3D]">double-click</span> untuk
            selesai ·{' '}
            <span className="font-mono text-white/70">ESC</span> untuk batal
          </div>
        </div>
      )}
    </div>
  );
}
