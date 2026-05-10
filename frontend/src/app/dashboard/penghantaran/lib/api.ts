// Penghantaran — API client
// Reuses the central auth/fetch helpers from frontend/src/lib/api.ts so we
// inherit token refresh, 401 redirect, and the API_BASE convention.

import { supabase, ensureValidToken } from '@/lib/supabase';
import type {
  GeoJSONPolygon,
  PostcodeTestResult,
  Zone,
  ZoneInput,
} from './types';

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || 'https://binaapp-backend.onrender.com';

// ----- Internal -----

async function getToken(): Promise<string> {
  // Same chain used everywhere else in the app: backend token first,
  // Supabase session as fallback.
  const validToken = await ensureValidToken();
  if (validToken) return validToken;
  if (supabase) {
    const { data } = await supabase.auth.getSession();
    if (data.session?.access_token) return data.session.access_token;
  }
  throw new Error('Tidak log masuk');
}

interface FetchOptions extends RequestInit {
  /** If true, returns null on 404 instead of throwing. */
  allow404?: boolean;
}

async function authFetch<T>(path: string, opts: FetchOptions = {}): Promise<T> {
  const token = await getToken();
  const url = `${API_BASE}${path}`;
  const res = await fetch(url, {
    ...opts,
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
      ...(opts.headers || {}),
    },
  });

  if (res.status === 204) {
    // No content
    return null as unknown as T;
  }

  if (!res.ok) {
    if (res.status === 404 && opts.allow404) {
      return null as unknown as T;
    }
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body?.detail || detail;
    } catch {
      /* ignore */
    }
    throw new Error(detail || `HTTP ${res.status}`);
  }

  return (await res.json()) as T;
}

// ----- Public API -----

export function listZones(websiteId: string): Promise<Zone[]> {
  return authFetch<Zone[]>(`/api/v1/zones/website/${websiteId}`);
}

export function createZone(websiteId: string, input: ZoneInput): Promise<Zone> {
  return authFetch<Zone>(`/api/v1/zones/website/${websiteId}`, {
    method: 'POST',
    body: JSON.stringify(input),
  });
}

export function updateZone(
  zoneId: string,
  patch: Partial<ZoneInput>,
): Promise<Zone> {
  return authFetch<Zone>(`/api/v1/zones/${zoneId}`, {
    method: 'PATCH',
    body: JSON.stringify(patch),
  });
}

export async function deleteZone(zoneId: string): Promise<void> {
  await authFetch<null>(`/api/v1/zones/${zoneId}`, { method: 'DELETE' });
}

export function testPoint(
  websiteId: string,
  lat: number,
  lng: number,
): Promise<PostcodeTestResult> {
  const params = new URLSearchParams({
    lat: String(lat),
    lng: String(lng),
  });
  return authFetch<PostcodeTestResult>(
    `/api/v1/zones/website/${websiteId}/test?${params.toString()}`,
  );
}

export interface GeocodeHit {
  found: true;
  lat: number;
  lng: number;
  display_name: string | null;
}
export interface GeocodeMiss {
  found: false;
}

export async function geocodePostcode(
  postcode: string,
  country = 'MY',
): Promise<GeocodeHit | GeocodeMiss> {
  const params = new URLSearchParams({
    postcode: postcode.trim(),
    country,
  });
  const res = await authFetch<{
    found: boolean;
    lat: number | null;
    lng: number | null;
    display_name: string | null;
  }>(`/api/v1/zones/geocode?${params.toString()}`);
  if (!res.found || res.lat == null || res.lng == null) {
    return { found: false };
  }
  return {
    found: true,
    lat: res.lat,
    lng: res.lng,
    display_name: res.display_name,
  };
}

// ----- Utility for building ZoneInput from a GeoJSON polygon + form draft -----

export function buildZoneInput(
  draft: Omit<ZoneInput, 'polygon'>,
  polygon: GeoJSONPolygon,
): ZoneInput {
  return { ...draft, polygon };
}
