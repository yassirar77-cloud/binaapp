'use client';

import { useEffect, useState, useRef } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

// Fix Leaflet default marker icons
if (typeof window !== 'undefined') {
  delete (L.Icon.Default.prototype as any)._getIconUrl;
  L.Icon.Default.mergeOptions({
    iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png',
    iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png',
    shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
  });
}

interface RiderTrackingMapProps {
  riderLat: number;
  riderLng: number;
  customerLat: number;
  customerLng: number;
  riderName?: string;
  lastUpdate?: string;
}

export default function RiderTrackingMap({
  riderLat,
  riderLng,
  customerLat,
  customerLng,
  riderName = 'Rider',
  lastUpdate
}: RiderTrackingMapProps) {
  const mapRef = useRef<L.Map | null>(null);
  const riderMarkerRef = useRef<L.Marker | null>(null);
  const customerMarkerRef = useRef<L.Marker | null>(null);
  const routeLineRef = useRef<L.Polyline | null>(null);
  const [distance, setDistance] = useState<number>(0);
  const [eta, setEta] = useState<number>(0);

  useEffect(() => {
    // Initialize map only once
    if (!mapRef.current) {
      const map = L.map('rider-map').setView([riderLat, riderLng], 14);

      // Add OpenStreetMap tiles (FREE!)
      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
        maxZoom: 19,
      }).addTo(map);

      mapRef.current = map;
    }

    return () => {
      if (mapRef.current) {
        mapRef.current.remove();
        mapRef.current = null;
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!mapRef.current) return;

    const map = mapRef.current;

    // Custom rider icon (motorcycle)
    const riderIcon = L.divIcon({
      html: `
        <div style="
          width: 50px;
          height: 50px;
          background: linear-gradient(135deg, #ea580c 0%, #fb923c 100%);
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          box-shadow: 0 4px 12px rgba(234, 88, 12, 0.4);
          border: 4px solid white;
          font-size: 24px;
        ">
          🛵
        </div>
      `,
      className: 'rider-marker',
      iconSize: [50, 50],
      iconAnchor: [25, 25],
      popupAnchor: [0, -25]
    });

    // Custom customer icon (location pin)
    const customerIcon = L.divIcon({
      html: `
        <div style="
          width: 40px;
          height: 40px;
          background: linear-gradient(135deg, #dc2626 0%, #ef4444 100%);
          border-radius: 50% 50% 50% 0;
          transform: rotate(-45deg);
          display: flex;
          align-items: center;
          justify-content: center;
          box-shadow: 0 4px 12px rgba(220, 38, 38, 0.4);
          border: 3px solid white;
        ">
          <span style="
            transform: rotate(45deg);
            font-size: 18px;
          ">📍</span>
        </div>
      `,
      className: 'customer-marker',
      iconSize: [40, 40],
      iconAnchor: [20, 40],
      popupAnchor: [0, -40]
    });

    // Update or create rider marker
    if (riderMarkerRef.current) {
      riderMarkerRef.current.setLatLng([riderLat, riderLng]);
    } else {
      riderMarkerRef.current = L.marker([riderLat, riderLng], { icon: riderIcon })
        .addTo(map)
        .bindPopup(`
          <div style="text-align: center; font-family: system-ui;">
            <strong style="font-size: 16px;">🛵 ${riderName}</strong><br>
            <span style="font-size: 12px; color: #666;">
              Rider sedang dalam perjalanan
            </span>
          </div>
        `);
    }

    // Update or create customer marker
    if (customerMarkerRef.current) {
      customerMarkerRef.current.setLatLng([customerLat, customerLng]);
    } else {
      customerMarkerRef.current = L.marker([customerLat, customerLng], { icon: customerIcon })
        .addTo(map)
        .bindPopup(`
          <div style="text-align: center; font-family: system-ui;">
            <strong style="font-size: 16px;">📍 Destinasi Anda</strong><br>
            <span style="font-size: 12px; color: #666;">
              Lokasi penghantaran
            </span>
          </div>
        `);
    }

    // Draw route line between rider and customer
    if (routeLineRef.current) {
      map.removeLayer(routeLineRef.current);
    }
    routeLineRef.current = L.polyline(
      [
        [riderLat, riderLng],
        [customerLat, customerLng]
      ],
      {
        color: '#ea580c',
        weight: 4,
        opacity: 0.7,
        dashArray: '10, 10',
        lineCap: 'round'
      }
    ).addTo(map);

    // Calculate distance (Haversine formula)
    const R = 6371; // Earth's radius in km
    const dLat = (customerLat - riderLat) * Math.PI / 180;
    const dLng = (customerLng - riderLng) * Math.PI / 180;
    const a =
      Math.sin(dLat/2) * Math.sin(dLat/2) +
      Math.cos(riderLat * Math.PI / 180) * Math.cos(customerLat * Math.PI / 180) *
      Math.sin(dLng/2) * Math.sin(dLng/2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
    const dist = R * c;
    setDistance(dist);

    // Estimate ETA (assuming 30 km/h average speed for motorcycle in city)
    const avgSpeed = 30; // km/h
    const etaMinutes = Math.ceil((dist / avgSpeed) * 60);
    setEta(etaMinutes);

    // Auto-zoom to fit both markers
    const bounds = L.latLngBounds([
      [riderLat, riderLng],
      [customerLat, customerLng]
    ]);
    map.fitBounds(bounds, { padding: [50, 50] });

  }, [riderLat, riderLng, customerLat, customerLng, riderName]);

  return (
    <div className="relative">
      {/* Map Container */}
      <div
        id="rider-map"
        style={{
          height: '500px',
          width: '100%',
          borderRadius: '16px',
          overflow: 'hidden',
          boxShadow: '0 4px 12px rgba(0, 0, 0, 0.1)'
        }}
      />

      {/* Info Overlay */}
      <div className="absolute top-4 left-4 bg-white rounded-lg shadow-lg p-4 z-[1000]">
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <span className="text-2xl">🛵</span>
            <div>
              <p className="font-semibold text-gray-900">{riderName}</p>
              <p className="text-xs text-gray-600">Rider anda</p>
            </div>
          </div>

          <div className="border-t pt-2 space-y-1 text-sm">
            <div className="flex items-center gap-2 text-gray-700">
              <span>📏</span>
              <span><strong>{distance.toFixed(1)} km</strong> lagi</span>
            </div>

            <div className="flex items-center gap-2 text-gray-700">
              <span>⏱️</span>
              <span>
                <strong>{eta} minit</strong> anggaran tiba
              </span>
            </div>

            {lastUpdate && (
              <div className="flex items-center gap-2 text-xs text-gray-500 pt-2 border-t">
                <span>🔄</span>
                <span>Dikemaskini: {new Date(lastUpdate).toLocaleTimeString('ms-MY')}</span>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Live Indicator */}
      <div className="absolute top-4 right-4 bg-white rounded-full px-4 py-2 shadow-lg z-[1000]">
        <div className="flex items-center gap-2">
          <span className="relative flex h-3 w-3">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-3 w-3 bg-green-500"></span>
          </span>
          <span className="text-sm font-semibold text-gray-900">LIVE</span>
        </div>
      </div>
    </div>
  );
}
