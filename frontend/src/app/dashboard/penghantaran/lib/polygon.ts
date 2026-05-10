// Penghantaran — polygon utilities
// Coordinate convention notes:
//   GeoJSON: [lng, lat]  (RFC 7946)
//   Leaflet: [lat, lng]
// All conversions go through these helpers — never inline a swap elsewhere.

import circle from '@turf/circle';
import distance from '@turf/distance';
import { point } from '@turf/helpers';
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

// ---------- Concentric ring helpers ----------

/** 64-vertex GeoJSON polygon approximating a circle of given radius. */
export function ringToPolygon(
  centerLat: number,
  centerLng: number,
  radiusM: number,
): GeoJSONPolygon {
  const c = circle([centerLng, centerLat], radiusM / 1000, {
    steps: 64,
    units: 'kilometers',
  });
  return c.geometry as GeoJSONPolygon;
}

/** Great-circle distance in meters between two lat/lng points. */
export function distanceMeters(
  aLat: number,
  aLng: number,
  bLat: number,
  bLng: number,
): number {
  const a = point([aLng, aLat]);
  const b = point([bLng, bLat]);
  return distance(a, b, { units: 'meters' });
}

/** Format meters as "3 km" or "500 m" for ring labels. */
export function formatDistance(m: number): string {
  if (m < 1000) return `${Math.round(m)} m`;
  const km = m / 1000;
  return Number.isInteger(km) ? `${km} km` : `${km.toFixed(1)} km`;
}
