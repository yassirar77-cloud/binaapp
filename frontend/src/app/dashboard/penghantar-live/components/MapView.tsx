'use client';

// MapView — Leaflet integration for /dashboard/penghantar-live.
//
// Renders:
//   - Outlet pin (lime pulse, reused .rest-pin-* styles)
//   - Rider DivIcons colored by presence (online / stale-GPS / offline)
//   - Delivery route dotted polylines from rider → delivery address
//   - Zone polygon overlays at 15% fill opacity
//
// Hover/select sync with the left panels is handled via the hoveredOrderId /
// hoveredRiderId / selectedOrderId / selectedRiderId props.
//
// Zones are passed in as a prop; PenghantarLiveClient owns the fetch and
// re-fetches once per outlet change.
// TODO v2: refetch zones on owner edit signal (websocket or focus listener).

import { useEffect, useRef, useState } from 'react';
import type {
  Map as LeafletMap,
  Marker,
  Polygon,
  Polyline,
} from 'leaflet';
import { geoJSONToLatLngs } from '../lib/polygon';
import {
  DEFAULT_CENTER,
  DEFAULT_ZOOM,
  TILE_ATTRIBUTION,
  TILE_URL,
} from '../lib/constants';
import type {
  ActiveOrder,
  LiteZone,
  LiveRider,
  Outlet,
} from '../lib/types';
import { computeRiderPresence } from '../lib/types';

interface Props {
  outlet: Outlet | null;
  orders: ActiveOrder[];
  riders: LiveRider[];
  zones: LiteZone[];
  showZones: boolean;
  showOfflineRiders: boolean;
  selectedOrderId: string | null;
  selectedRiderId: string | null;
  hoveredOrderId: string | null;
  hoveredRiderId: string | null;
  onOrderSelect: (orderId: string) => void;
  onRiderSelect: (riderId: string) => void;
}

// ---- DivIcon HTML for riders ----

function riderIconHtml(presence: ReturnType<typeof computeRiderPresence>, stale: boolean): string {
  const color =
    presence === 'online' ? '#34D399' :
    presence === 'online_stale_gps' ? '#FBBF24' : '#71717A';
  const opacity = presence === 'offline' || stale ? 0.6 : 1;
  // Lucide bike icon rendered inline; matches lucide-react Bike at strokeWidth 1.5
  return `
    <span class="phl-rider-pin" style="--phl-rider-color:${color};opacity:${opacity}">
      <span class="phl-rider-dot"></span>
      <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="#0a0e1a" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <circle cx="18.5" cy="17.5" r="3.5"/>
        <circle cx="5.5" cy="17.5" r="3.5"/>
        <circle cx="15" cy="5" r="1"/>
        <path d="M12 17.5V14l-3-3 4-3 2 3h2"/>
      </svg>
    </span>
  `;
}

export default function MapView({
  outlet,
  orders,
  riders,
  zones,
  showZones,
  showOfflineRiders,
  selectedOrderId,
  selectedRiderId,
  hoveredOrderId,
  hoveredRiderId,
  onOrderSelect,
  onRiderSelect,
}: Props) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<LeafletMap | null>(null);
  const outletPinRef = useRef<Marker | null>(null);
  const zonePolysRef = useRef<Map<string, Polygon>>(new Map());
  const riderMarkersRef = useRef<Map<string, Marker>>(new Map());
  const routeLinesRef = useRef<Map<string, Polyline>>(new Map());
  const deliveryPinsRef = useRef<Map<string, Marker>>(new Map());

  const [LRef, setLRef] = useState<typeof import('leaflet') | null>(null);

  // Load Leaflet client-side only.
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

  // Create the map once.
  useEffect(() => {
    if (!LRef || !containerRef.current || mapRef.current) return;
    const L = LRef;
    const center: [number, number] =
      outlet?.lat && outlet?.lng ? [outlet.lat, outlet.lng] : DEFAULT_CENTER;
    const map = L.map(containerRef.current, {
      center,
      zoom: DEFAULT_ZOOM,
      zoomControl: false, // custom controls land in commit 5
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

  // Outlet pin.
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

  // Recenter on outlet change.
  useEffect(() => {
    if (!mapRef.current || !outlet?.lat || !outlet?.lng) return;
    mapRef.current.setView([outlet.lat, outlet.lng], DEFAULT_ZOOM, {
      animate: true,
    });
  }, [outlet?.lat, outlet?.lng]);

  // Zone overlays.
  useEffect(() => {
    if (!LRef || !mapRef.current) return;
    const L = LRef;
    const map = mapRef.current;
    zonePolysRef.current.forEach((p) => p.remove());
    zonePolysRef.current.clear();
    if (!showZones) return;

    for (const z of zones) {
      if (!z.active) continue;
      const ring = geoJSONToLatLngs(z.polygon);
      if (ring.length < 3) continue;
      const poly = L.polygon(ring, {
        color: z.color,
        fillColor: z.color,
        fillOpacity: 0.15,
        weight: 1.5,
        opacity: 0.6,
        interactive: false,
      }).addTo(map);
      zonePolysRef.current.set(z.id, poly);
    }
  }, [LRef, zones, showZones]);

  // Rider markers.
  useEffect(() => {
    if (!LRef || !mapRef.current) return;
    const L = LRef;
    const map = mapRef.current;
    riderMarkersRef.current.forEach((m) => m.remove());
    riderMarkersRef.current.clear();

    for (const r of riders) {
      const presence = computeRiderPresence(r);
      if (presence === 'offline' && !showOfflineRiders) continue;
      if (r.current_latitude == null || r.current_longitude == null) continue;
      const stale = presence === 'online_stale_gps';
      const icon = L.divIcon({
        className: 'phl-rider-marker',
        html: riderIconHtml(presence, stale),
        iconSize: [26, 26],
        iconAnchor: [13, 13],
      });
      const marker = L.marker([r.current_latitude, r.current_longitude], {
        icon,
      }).addTo(map);
      marker.on('click', () => onRiderSelect(r.id));
      marker.bindTooltip(r.name, { direction: 'top', offset: [0, -10] });
      riderMarkersRef.current.set(r.id, marker);
    }
  }, [LRef, riders, showOfflineRiders, onRiderSelect]);

  // Delivery routes + customer pins for orders that have an assigned rider
  // with known GPS and a known delivery address.
  useEffect(() => {
    if (!LRef || !mapRef.current) return;
    const L = LRef;
    const map = mapRef.current;
    routeLinesRef.current.forEach((p) => p.remove());
    routeLinesRef.current.clear();
    deliveryPinsRef.current.forEach((m) => m.remove());
    deliveryPinsRef.current.clear();

    for (const o of orders) {
      if (
        o.delivery_latitude == null ||
        o.delivery_longitude == null
      ) {
        continue;
      }
      // Delivery destination pin (small lime dot, distinct from outlet pulse)
      const destIcon = L.divIcon({
        className: 'phl-dest-pin',
        html: `<span class="phl-dest-dot" style="background:${o.zone_color || '#C7FF3D'}"></span>`,
        iconSize: [14, 14],
        iconAnchor: [7, 7],
      });
      const destMarker = L.marker(
        [o.delivery_latitude, o.delivery_longitude],
        { icon: destIcon, interactive: true },
      ).addTo(map);
      destMarker.on('click', () => onOrderSelect(o.id));
      destMarker.bindTooltip(o.order_number, { direction: 'top', offset: [0, -6] });
      deliveryPinsRef.current.set(o.id, destMarker);

      // Route line from rider → delivery (only if rider GPS known)
      if (
        o.rider_id &&
        o.rider_current_latitude != null &&
        o.rider_current_longitude != null
      ) {
        const line = L.polyline(
          [
            [o.rider_current_latitude, o.rider_current_longitude],
            [o.delivery_latitude, o.delivery_longitude],
          ],
          {
            color: o.zone_color || '#C7FF3D',
            weight: 2,
            opacity: 0.7,
            dashArray: '4,6',
            interactive: false,
          },
        ).addTo(map);
        routeLinesRef.current.set(o.id, line);
      }
    }
  }, [LRef, orders, onOrderSelect]);

  // Selection → fly to relevant bounds.
  useEffect(() => {
    if (!LRef || !mapRef.current) return;
    const L = LRef;
    const map = mapRef.current;

    // The detail panel mounts/unmounts simultaneously and shifts the map
    // container width. Refresh Leaflet's cached size after the slide-in
    // animation settles (CSS animation is 220ms).
    window.setTimeout(() => map.invalidateSize(), 240);

    if (selectedOrderId) {
      const o = orders.find((x) => x.id === selectedOrderId);
      if (!o) return;
      const pts: [number, number][] = [];
      if (o.delivery_latitude != null && o.delivery_longitude != null) {
        pts.push([o.delivery_latitude, o.delivery_longitude]);
      }
      if (o.rider_current_latitude != null && o.rider_current_longitude != null) {
        pts.push([o.rider_current_latitude, o.rider_current_longitude]);
      }
      if (outlet?.lat && outlet?.lng) pts.push([outlet.lat, outlet.lng]);
      if (pts.length === 1) {
        map.setView(pts[0], 16, { animate: true });
      } else if (pts.length >= 2) {
        map.fitBounds(L.latLngBounds(pts), { padding: [60, 60], maxZoom: 16 });
      }
      return;
    }
    if (selectedRiderId) {
      const r = riders.find((x) => x.id === selectedRiderId);
      if (!r || r.current_latitude == null || r.current_longitude == null) return;
      map.setView([r.current_latitude, r.current_longitude], 16, {
        animate: true,
      });
    }
  }, [LRef, selectedOrderId, selectedRiderId, orders, riders, outlet?.lat, outlet?.lng]);

  // Hover highlight — add CSS class to marker element.
  useEffect(() => {
    riderMarkersRef.current.forEach((m, id) => {
      const el = m.getElement();
      if (!el) return;
      el.classList.toggle('phl-hover', id === hoveredRiderId);
    });
  }, [hoveredRiderId]);

  useEffect(() => {
    deliveryPinsRef.current.forEach((m, id) => {
      const el = m.getElement();
      if (!el) return;
      el.classList.toggle('phl-hover', id === hoveredOrderId);
    });
    routeLinesRef.current.forEach((p, id) => {
      const el = (p as unknown as { getElement?: () => SVGElement | null }).getElement?.();
      if (!el) return;
      el.classList.toggle('phl-route-hover', id === hoveredOrderId);
    });
  }, [hoveredOrderId]);

  return (
    <div className="relative h-full w-full">
      <div
        ref={containerRef}
        className="h-full w-full bg-[#0f1424]"
        aria-label="Peta penghantar live"
      />
    </div>
  );
}
