// /rider — GPS hook.
//
// Replaces the inline watchPosition logic from the pre-redesign page.tsx.
// Fixes a stale-closure bug in the previous backup interval: the original
// code (page.tsx:586) did
//
//   gpsIntervalRef.current = setInterval(() => {
//     if (currentLocation) sendLocationToAPI(currentLocation.lat, ...)
//   }, 15000);
//
// `currentLocation` was captured by closure when startGPSTracking() ran (at
// login, when it was still null), so the interval kept reading null forever
// and never sent a backup fix. We fix this by holding the latest fix in a
// ref and reading from the ref inside the interval callback.

import { useCallback, useEffect, useRef, useState } from 'react';

import type { GpsStatus } from './types';

interface UseGeolocationArgs {
  enabled: boolean;
  intervalMs: number;
  onLocation: (lat: number, lng: number) => void;
}

interface UseGeolocationResult {
  status: GpsStatus;
  currentLocation: { lat: number; lng: number } | null;
  lastUpdate: Date | null;
  permissionDenied: boolean;
}

export function useGeolocation(
  args: UseGeolocationArgs,
): UseGeolocationResult {
  const { enabled, intervalMs } = args;

  const [status, setStatus] = useState<GpsStatus>('inactive');
  const [currentLocation, setCurrentLocation] = useState<
    { lat: number; lng: number } | null
  >(null);
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);

  // Refs that avoid stale closures inside the long-lived watchPosition /
  // setInterval callbacks.
  const onLocationRef = useRef(args.onLocation);
  const currentLocationRef = useRef<{ lat: number; lng: number } | null>(null);
  const lastSentRef = useRef<number>(0);

  // Keep the callback ref in sync without retriggering watch setup.
  useEffect(() => {
    onLocationRef.current = args.onLocation;
  }, [args.onLocation]);

  const emit = useCallback(
    (lat: number, lng: number) => {
      onLocationRef.current(lat, lng);
      setLastUpdate(new Date());
      lastSentRef.current = Date.now();
    },
    [],
  );

  useEffect(() => {
    if (!enabled) {
      setStatus('inactive');
      return;
    }
    if (typeof navigator === 'undefined' || !navigator.geolocation) {
      setStatus('error');
      return;
    }

    const watchId = navigator.geolocation.watchPosition(
      (position) => {
        const { latitude, longitude } = position.coords;
        const loc = { lat: latitude, lng: longitude };
        currentLocationRef.current = loc;
        setCurrentLocation(loc);
        setStatus('active');

        // Throttle uploads: only emit if intervalMs has elapsed since the
        // last successful upload.
        if (Date.now() - lastSentRef.current >= intervalMs) {
          emit(latitude, longitude);
        }
      },
      (error) => {
        if (error.code === error.PERMISSION_DENIED) {
          setStatus('permission_denied');
        } else {
          setStatus('error');
        }
      },
      { enableHighAccuracy: true, timeout: 10000, maximumAge: 5000 },
    );

    // Send an immediate one-shot fix so we don't wait for the first
    // watchPosition callback (which can take 5–10s on cold start).
    navigator.geolocation.getCurrentPosition(
      (position) => {
        const { latitude, longitude } = position.coords;
        const loc = { lat: latitude, lng: longitude };
        currentLocationRef.current = loc;
        setCurrentLocation(loc);
        setStatus('active');
        emit(latitude, longitude);
      },
      () => {
        /* swallow — watchPosition will surface a status */
      },
      { enableHighAccuracy: true, timeout: 10000 },
    );

    // Backup interval: even when watchPosition is quiet (rider standing
    // still, no fresh fixes), re-upload the most recent known fix so the
    // backend keeps seeing the rider as online. Reads from the ref, NOT
    // from the closed-over state value — that was the bug.
    const backupId = setInterval(() => {
      const loc = currentLocationRef.current;
      if (loc) emit(loc.lat, loc.lng);
    }, intervalMs);

    return () => {
      navigator.geolocation.clearWatch(watchId);
      clearInterval(backupId);
      setStatus('inactive');
    };
  }, [enabled, intervalMs, emit]);

  return {
    status,
    currentLocation,
    lastUpdate,
    permissionDenied: status === 'permission_denied',
  };
}
