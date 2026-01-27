'use client';

import React, { useEffect, useState, useCallback } from 'react';
import L from 'leaflet';
import BaseMap from './BaseMap';
import { calculateDistance, calculateDeliveryFee } from '@/lib/mapUtils';

// =====================================================
// TYPES
// =====================================================

interface Location {
  latitude: number;
  longitude: number;
}

interface DeliveryZone {
  id: string;
  name: string;
  coordinates: [number, number][];
  fee: number;
  color?: string;
}

interface DeliveryMapProps {
  // Restaurant/Store location
  storeLocation: Location;

  // Customer delivery address
  deliveryAddress?: Location;

  // Rider location (real-time)
  riderLocation?: Location;

  // Delivery zones
  deliveryZones?: DeliveryZone[];

  // Map settings
  height?: string;
  className?: string;
  showDistance?: boolean;

  // Callbacks
  onDistanceCalculated?: (distance: number, fee: number) => void;
}

// =====================================================
// CUSTOM ICONS
// =====================================================

const storeIcon = L.icon({
  iconUrl: 'data:image/svg+xml;base64,' + btoa(`
    <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="rgb(249, 115, 22)" stroke-width="2">
      <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"></path>
      <polyline points="9 22 9 12 15 12 15 22"></polyline>
    </svg>
  `),
  iconSize: [32, 32],
  iconAnchor: [16, 32],
  popupAnchor: [0, -32],
});

const customerIcon = L.icon({
  iconUrl: 'data:image/svg+xml;base64,' + btoa(`
    <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="rgb(59, 130, 246)" stroke="white" stroke-width="2">
      <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"></path>
      <circle cx="12" cy="10" r="3" fill="white" stroke="rgb(59, 130, 246)"></circle>
    </svg>
  `),
  iconSize: [32, 32],
  iconAnchor: [16, 32],
  popupAnchor: [0, -32],
});

const riderIcon = L.icon({
  iconUrl: 'data:image/svg+xml;base64,' + btoa(`
    <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="rgb(34, 197, 94)" stroke="white" stroke-width="2">
      <circle cx="12" cy="12" r="10" fill="rgb(34, 197, 94)"></circle>
      <path d="M12 2v20M2 12h20" stroke="white" stroke-width="2"></path>
    </svg>
  `),
  iconSize: [32, 32],
  iconAnchor: [16, 16],
  popupAnchor: [0, -16],
});

// =====================================================
// DELIVERY MAP COMPONENT
// =====================================================

export default function DeliveryMap({
  storeLocation,
  deliveryAddress,
  riderLocation,
  deliveryZones = [],
  height = '400px',
  className = '',
  showDistance = true,
  onDistanceCalculated
}: DeliveryMapProps) {
  const [map, setMap] = useState<L.Map | null>(null);
  const [markers, setMarkers] = useState<{
    store?: L.Marker;
    customer?: L.Marker;
    rider?: L.Marker;
  }>({});
  const [zones, setZones] = useState<L.Polygon[]>([]);
  const [routeLine, setRouteLine] = useState<L.Polyline | null>(null);

  // Calculate map center based on available locations
  const getMapCenter = useCallback((): [number, number] => {
    if (deliveryAddress) {
      return [deliveryAddress.latitude, deliveryAddress.longitude];
    }
    if (riderLocation) {
      return [riderLocation.latitude, riderLocation.longitude];
    }
    return [storeLocation.latitude, storeLocation.longitude];
  }, [storeLocation, deliveryAddress, riderLocation]);

  // Handle map ready
  const handleMapReady = useCallback((mapInstance: L.Map) => {
    setMap(mapInstance);
  }, []);

  // Add or update store marker
  useEffect(() => {
    if (!map) return;

    // Remove old marker
    if (markers.store) {
      markers.store.remove();
    }

    // Add new marker
    const marker = L.marker(
      [storeLocation.latitude, storeLocation.longitude],
      { icon: storeIcon }
    ).addTo(map);

    marker.bindPopup('<b>Kedai</b><br>Lokasi penjual');

    setMarkers(prev => ({ ...prev, store: marker }));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [map, storeLocation]);

  // Add or update customer marker
  useEffect(() => {
    if (!map || !deliveryAddress) return;

    // Remove old marker
    if (markers.customer) {
      markers.customer.remove();
    }

    // Add new marker
    const marker = L.marker(
      [deliveryAddress.latitude, deliveryAddress.longitude],
      { icon: customerIcon }
    ).addTo(map);

    marker.bindPopup('<b>Alamat Penghantaran</b><br>Destinasi pelanggan');

    setMarkers(prev => ({ ...prev, customer: marker }));

    // Calculate distance and fee
    if (showDistance && onDistanceCalculated) {
      const distance = calculateDistance(
        storeLocation.latitude,
        storeLocation.longitude,
        deliveryAddress.latitude,
        deliveryAddress.longitude
      );
      const fee = calculateDeliveryFee(distance);
      onDistanceCalculated(distance, fee);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [map, deliveryAddress, storeLocation, showDistance, onDistanceCalculated]);

  // Add or update rider marker (real-time tracking)
  useEffect(() => {
    if (!map || !riderLocation) return;

    // Remove old marker
    if (markers.rider) {
      markers.rider.remove();
    }

    // Add new marker
    const marker = L.marker(
      [riderLocation.latitude, riderLocation.longitude],
      { icon: riderIcon }
    ).addTo(map);

    marker.bindPopup('<b>Rider</b><br>Lokasi rider sekarang');

    setMarkers(prev => ({ ...prev, rider: marker }));

    // Center map on rider if actively tracking
    map.setView([riderLocation.latitude, riderLocation.longitude], 15);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [map, riderLocation]);

  // Draw delivery zones
  useEffect(() => {
    if (!map || deliveryZones.length === 0) return;

    // Remove old zones
    zones.forEach(zone => zone.remove());

    // Draw new zones
    const newZones = deliveryZones.map(zone => {
      const polygon = L.polygon(zone.coordinates, {
        color: zone.color || '#3b82f6',
        fillColor: zone.color || '#3b82f6',
        fillOpacity: 0.1,
        weight: 2,
      }).addTo(map);

      polygon.bindPopup(`
        <b>${zone.name}</b><br>
        Bayaran: RM${zone.fee.toFixed(2)}
      `);

      return polygon;
    });

    setZones(newZones);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [map, deliveryZones]);

  // Draw route line from store to customer
  useEffect(() => {
    if (!map || !deliveryAddress) return;

    // Remove old route
    if (routeLine) {
      routeLine.remove();
    }

    // Draw route from store to customer
    const line = L.polyline(
      [
        [storeLocation.latitude, storeLocation.longitude],
        [deliveryAddress.latitude, deliveryAddress.longitude],
      ],
      {
        color: '#f97316',
        weight: 3,
        opacity: 0.7,
        dashArray: '10, 10',
      }
    ).addTo(map);

    setRouteLine(line);

    // Fit map to show all markers
    const bounds = L.latLngBounds([
      [storeLocation.latitude, storeLocation.longitude],
      [deliveryAddress.latitude, deliveryAddress.longitude],
    ]);

    if (riderLocation) {
      bounds.extend([riderLocation.latitude, riderLocation.longitude]);
    }

    map.fitBounds(bounds, { padding: [50, 50] });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [map, storeLocation, deliveryAddress, riderLocation]);

  return (
    <BaseMap
      center={getMapCenter()}
      zoom={13}
      height={height}
      className={className}
      onMapReady={handleMapReady}
    />
  );
}
