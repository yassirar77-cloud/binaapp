// Penghantaran — polygon utilities
// Coordinate convention notes:
//   GeoJSON: [lng, lat]  (RFC 7946)
//   Leaflet: [lat, lng]
// All conversions go through these helpers — never inline a swap elsewhere.

import area from '@turf/area';
import kinks from '@turf/kinks';
import { polygon as turfPolygon } from '@turf/helpers';
import type { GeoJSONPolygon } from './types';

/**
 * Convert a GeoJSON Polygon's outer ring to Leaflet [lat, lng] pairs.
 * Drops the closing duplicate vertex (Leaflet auto-closes).
 */
export function geoJSONToLatLngs(p: GeoJSONPolygon): [number, number][] {
  const ring = p?.coordinates?.[0];
  if (!Array.isArray(ring) || ring.length === 0) return [];
  // GeoJSON closes by repeating first point; Leaflet doesn't want that.
  const last = ring.length - 1;
  const closed =
    ring.length >= 2 &&
    ring[0][0] === ring[last][0] &&
    ring[0][1] === ring[last][1];
  const usable = closed ? ring.slice(0, -1) : ring;
  return usable.map(([lng, lat]) => [lat, lng] as [number, number]);
}

/**
 * Convert Leaflet [lat, lng] vertices to a closed GeoJSON Polygon.
 * Adds the closing duplicate vertex automatically.
 */
export function latLngsToGeoJSON(latlngs: [number, number][]): GeoJSONPolygon {
  if (latlngs.length < 3) {
    throw new Error('Polygon needs at least 3 vertices');
  }
  const ring = latlngs.map(([lat, lng]) => [lng, lat]);
  // Close the ring
  const first = ring[0];
  const last = ring[ring.length - 1];
  if (first[0] !== last[0] || first[1] !== last[1]) {
    ring.push([first[0], first[1]]);
  }
  return {
    type: 'Polygon',
    coordinates: [ring],
  };
}

/** True if the polygon's outer ring self-intersects. */
export function polygonHasSelfIntersection(p: GeoJSONPolygon): boolean {
  try {
    const feat = turfPolygon(p.coordinates);
    const intersections = kinks(feat);
    return (intersections.features?.length ?? 0) > 0;
  } catch {
    // turf throws on degenerate input; treat as invalid (which is a kind of bad geometry)
    return true;
  }
}

/** Surface area in square meters (great-circle aware via turf). */
export function polygonAreaM2(p: GeoJSONPolygon): number {
  try {
    const feat = turfPolygon(p.coordinates);
    return area(feat);
  } catch {
    return 0;
  }
}

/** Format square meters as "X.X km²" or "X m²" for very small zones. */
export function formatKm2(m2: number | null | undefined): string {
  if (!m2 || m2 <= 0) return '0 km²';
  if (m2 < 10_000) return `${Math.round(m2)} m²`;
  const km2 = m2 / 1_000_000;
  if (km2 < 0.1) return `${km2.toFixed(2)} km²`;
  if (km2 < 10) return `${km2.toFixed(1)} km²`;
  return `${Math.round(km2)} km²`;
}
