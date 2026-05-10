// Penghantaran (Delivery Zone Management) — constants

import type { DayKey, ScheduleJson } from './types';

// ----- Map -----

/** KL city center fallback when website has no lat/lng set. [lat, lng] for Leaflet. */
export const DEFAULT_CENTER: [number, number] = [3.139, 101.687];

export const DEFAULT_ZOOM = 13;

/** CartoDB Positron — light tiles for visual contrast against dark UI. */
export const TILE_URL =
  'https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png';

export const TILE_ATTRIBUTION =
  '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>';

// ----- Schedule -----

export const DAY_KEYS: readonly DayKey[] = [
  'mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun',
] as const;

export const DAY_LABELS: Record<DayKey, string> = {
  mon: 'Isn',
  tue: 'Sel',
  wed: 'Rab',
  thu: 'Kha',
  fri: 'Jum',
  sat: 'Sab',
  sun: 'Ahd',
};

export const DEFAULT_SCHEDULE: ScheduleJson = {
  mon: { open: '10:00', close: '22:00', active: true },
  tue: { open: '10:00', close: '22:00', active: true },
  wed: { open: '10:00', close: '22:00', active: true },
  thu: { open: '10:00', close: '22:00', active: true },
  fri: { open: '10:00', close: '22:00', active: true },
  sat: { open: '10:00', close: '22:00', active: true },
  sun: { open: '10:00', close: '22:00', active: true },
};

// ----- Color swatches (8 zones, equal saturation) -----

export const SWATCHES: readonly string[] = [
  '#C7FF3D', // lime (default)
  '#F97316', // orange
  '#3B82F6', // blue
  '#A855F7', // purple
  '#EC4899', // pink
  '#14B8A6', // teal
  '#EF4444', // red
  '#EAB308', // yellow
] as const;
