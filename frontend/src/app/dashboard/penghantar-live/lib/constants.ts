// Penghantar Live — map constants.
// Tile URL + KL fallback center mirror /dashboard/penghantaran/lib/constants
// so the two pages share the same visual basemap.

export const DEFAULT_CENTER: [number, number] = [3.139, 101.687];
export const DEFAULT_ZOOM = 13;

export const TILE_URL =
  'https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png';

export const TILE_ATTRIBUTION =
  '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>';
