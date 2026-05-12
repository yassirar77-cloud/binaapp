// Penghantar Live — polygon helpers.
// Duplicated from penghantaran/lib/polygon.ts to avoid cross-feature coupling.
//
// Coordinate convention:
//   GeoJSON: [lng, lat]  (RFC 7946)
//   Leaflet: [lat, lng]
// All conversions go through these helpers — never inline a swap elsewhere.

import type { GeoJSONPolygon } from './types';

/**
 * Convert a GeoJSON Polygon's outer ring to Leaflet [lat, lng] pairs.
 * Drops the closing duplicate vertex (Leaflet auto-closes).
 */
export function geoJSONToLatLngs(p: GeoJSONPolygon): [number, number][] {
  const ring = p?.coordinates?.[0];
  if (!Array.isArray(ring) || ring.length === 0) return [];
  const last = ring.length - 1;
  const closed =
    ring.length >= 2 &&
    ring[0][0] === ring[last][0] &&
    ring[0][1] === ring[last][1];
  const usable = closed ? ring.slice(0, -1) : ring;
  return usable.map(([lng, lat]) => [lat, lng] as [number, number]);
}
