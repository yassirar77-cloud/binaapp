'use client';

// RouteMap — collapsible Leaflet map showing the rider's position and the
// customer pin connected by a straight dashed line.
//
// TODO: Replace the straight polyline with real road routing via
// OpenRouteService or Mapbox Directions in a followup PR.
//
// Leaflet is imported dynamically so the rider PWA's first paint stays
// small; the CSS is also lazy-imported here so it doesn't leak into
// other routes.

import { useEffect, useRef, useState } from 'react';
import { Maximize2, Minimize2 } from 'lucide-react';

interface RouteMapProps {
  riderLocation: { lat: number; lng: number } | null;
  customerLat: number | null;
  customerLng: number | null;
}

const RIDER_ICON_HTML = `
<div style="
  width: 36px; height: 36px;
  background: #C7FF3D;
  border: 3px solid #0a0e1a;
  border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  box-shadow: 0 4px 12px rgba(199,255,61,0.4);
">
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#0a0e1a" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
    <path d="M14 18V6a2 2 0 0 0-2-2H4a2 2 0 0 0-2 2v11a1 1 0 0 0 1 1h2"/>
    <path d="M15 18H9"/>
    <path d="M19 18h2a1 1 0 0 0 1-1v-3.65a1 1 0 0 0-.22-.624l-3.48-4.35A1 1 0 0 0 17.52 8H14"/>
    <circle cx="17" cy="18" r="2"/>
    <circle cx="7" cy="18" r="2"/>
  </svg>
</div>`;

const CUSTOMER_ICON_HTML = `
<div style="
  width: 36px; height: 36px;
  background: #FF5A5F;
  border: 3px solid #0a0e1a;
  border-radius: 50% 50% 50% 0;
  transform: rotate(-45deg);
  display: flex; align-items: center; justify-content: center;
  box-shadow: 0 4px 12px rgba(255,90,95,0.4);
">
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="transform: rotate(45deg);">
    <path d="M20 10c0 4.993-5.539 10.193-7.399 11.799a1 1 0 0 1-1.202 0C9.539 20.193 4 14.993 4 10a8 8 0 0 1 16 0"/>
    <circle cx="12" cy="10" r="3"/>
  </svg>
</div>`;

export default function RouteMap({
  riderLocation,
  customerLat,
  customerLng,
}: RouteMapProps) {
  const [expanded, setExpanded] = useState(false);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<unknown>(null);
  const riderMarkerRef = useRef<unknown>(null);
  const customerMarkerRef = useRef<unknown>(null);
  const lineRef = useRef<unknown>(null);

  // (Re)build the map when the container resizes (expand/collapse) or
  // when either endpoint changes. Cleanup tears down the Leaflet
  // instance to avoid leaks across detail screens.
  useEffect(() => {
    if (typeof window === 'undefined') return;
    if (!containerRef.current) return;
    if (customerLat == null || customerLng == null) return;

    let cancelled = false;

    (async () => {
      const L = (await import('leaflet')).default;
      await import('leaflet/dist/leaflet.css');
      if (cancelled || !containerRef.current) return;

      // Tear down any prior instance so toggling expanded doesn't double
      // up tiles on the same DOM node.
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const prior = mapRef.current as any;
      if (prior?.remove) prior.remove();

      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const map = (L as any).map(containerRef.current, {
        zoomControl: false,
        attributionControl: false,
      });

      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      (L as any)
        .tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
          maxZoom: 19,
        })
        .addTo(map);

      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const riderIcon = (L as any).divIcon({
        html: RIDER_ICON_HTML,
        className: 'rider-marker',
        iconSize: [36, 36],
        iconAnchor: [18, 18],
      });
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const customerIcon = (L as any).divIcon({
        html: CUSTOMER_ICON_HTML,
        className: 'customer-marker',
        iconSize: [36, 36],
        iconAnchor: [18, 36],
      });

      const customerLatLng: [number, number] = [customerLat, customerLng];
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const customerMarker = (L as any)
        .marker(customerLatLng, { icon: customerIcon })
        .addTo(map);

      let bounds: [number, number][] = [customerLatLng];

      if (riderLocation) {
        const riderLatLng: [number, number] = [
          riderLocation.lat,
          riderLocation.lng,
        ];
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const riderMarker = (L as any)
          .marker(riderLatLng, { icon: riderIcon })
          .addTo(map);
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const line = (L as any)
          .polyline([riderLatLng, customerLatLng], {
            color: '#C7FF3D',
            weight: 3,
            opacity: 0.8,
            dashArray: '8 8',
          })
          .addTo(map);
        riderMarkerRef.current = riderMarker;
        lineRef.current = line;
        bounds = [riderLatLng, customerLatLng];
      }

      customerMarkerRef.current = customerMarker;
      mapRef.current = map;

      if (bounds.length > 1) {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        (map as any).fitBounds(bounds, { padding: [30, 30] });
      } else {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        (map as any).setView(customerLatLng, 15);
      }
    })();

    return () => {
      cancelled = true;
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const m = mapRef.current as any;
      if (m?.remove) m.remove();
      mapRef.current = null;
      riderMarkerRef.current = null;
      customerMarkerRef.current = null;
      lineRef.current = null;
    };
  }, [expanded, riderLocation, customerLat, customerLng]);

  if (customerLat == null || customerLng == null) {
    return (
      <section className="mx-4 mt-3 rounded-2xl bg-[var(--rider-surface)] border border-[var(--rider-border)] p-4 text-[12px] text-[var(--rider-text-2)]">
        Lokasi GPS pelanggan tidak tersedia. Gunakan Waze atau Google Maps
        untuk navigasi.
      </section>
    );
  }

  const height = expanded ? 'h-80' : 'h-24';

  return (
    <section className="mx-4 mt-3 relative rounded-2xl overflow-hidden border border-[var(--rider-border)]">
      <div
        ref={containerRef}
        className={`${height} w-full bg-[var(--rider-surface)] transition-[height] duration-300`}
      />
      <button
        type="button"
        onClick={() => setExpanded((s) => !s)}
        className="absolute top-2 right-2 h-9 px-3 rounded-full bg-[var(--rider-bg)]/90 backdrop-blur border border-[var(--rider-border)] text-[12px] font-medium text-white flex items-center gap-1.5 hover:bg-[var(--rider-bg)] transition-colors"
      >
        {expanded ? (
          <>
            <Minimize2 className="w-3.5 h-3.5" />
            Tutup
          </>
        ) : (
          <>
            <Maximize2 className="w-3.5 h-3.5" />
            Besarkan
          </>
        )}
      </button>
    </section>
  );
}
