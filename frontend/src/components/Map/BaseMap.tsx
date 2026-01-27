'use client';

import React, { useEffect, useRef } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

// Fix for default marker icons in Leaflet with Next.js
delete (L.Icon.Default.prototype as any)._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
});

// =====================================================
// TYPES
// =====================================================

export interface MapProps {
  center?: [number, number];
  zoom?: number;
  height?: string;
  className?: string;
  onMapReady?: (map: L.Map) => void;
  children?: React.ReactNode;
}

// =====================================================
// BASE MAP COMPONENT
// =====================================================

export default function BaseMap({
  center = [3.1390, 101.6869], // Default: Kuala Lumpur
  zoom = 13,
  height = '400px',
  className = '',
  onMapReady,
  children
}: MapProps) {
  const mapRef = useRef<L.Map | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    // Initialize map
    const map = L.map(containerRef.current, {
      center,
      zoom,
      zoomControl: true,
      attributionControl: true,
    });

    // Add OpenStreetMap tile layer
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
      maxZoom: 19,
    }).addTo(map);

    mapRef.current = map;

    // Notify parent that map is ready
    if (onMapReady) {
      onMapReady(map);
    }

    // Cleanup on unmount
    return () => {
      if (mapRef.current) {
        mapRef.current.remove();
        mapRef.current = null;
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // Run once on mount

  // Update map center when prop changes
  useEffect(() => {
    if (mapRef.current && center) {
      mapRef.current.setView(center, zoom);
    }
  }, [center, zoom]);

  return (
    <div className={className}>
      <div ref={containerRef} style={{ height, width: '100%' }} />
    </div>
  );
}
