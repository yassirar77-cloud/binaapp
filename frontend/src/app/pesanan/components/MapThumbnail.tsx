'use client';

// Abstract map preview SVG used inside the customer info card. Purely
// decorative — no real geocoded data is drawn here. If we ever wire up a real
// static-tile API (Mapbox/CARTO), swap this component out without touching
// callers since props stay empty.

interface Props {
  /** Optional override for the address shown in the corner badge. */
  addressLine?: string | null;
  className?: string;
}

export default function MapThumbnail({ addressLine, className = '' }: Props) {
  return (
    <div
      className={`relative w-full h-24 rounded-lg overflow-hidden ring-1 ring-white/[0.08] ${className}`}
    >
      <svg
        viewBox="0 0 320 96"
        preserveAspectRatio="xMidYMid slice"
        className="absolute inset-0 w-full h-full"
        aria-hidden
      >
        {/* Background gradient — soft dusk. */}
        <defs>
          <linearGradient id="map-bg" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor="#161826" />
            <stop offset="100%" stopColor="#1f2235" />
          </linearGradient>
        </defs>
        <rect width="320" height="96" fill="url(#map-bg)" />

        {/* Major roads — wide, slightly bright */}
        <g stroke="#3a3f56" strokeWidth="6" strokeLinecap="round" fill="none">
          <path d="M -10 60 Q 80 40 160 50 T 330 30" />
          <path d="M 50 -10 Q 70 40 90 110" />
          <path d="M 230 110 Q 220 60 260 -10" />
        </g>

        {/* Minor roads */}
        <g stroke="#2a2e44" strokeWidth="2" strokeLinecap="round" fill="none">
          <path d="M 0 30 L 320 30" />
          <path d="M 0 80 L 320 80" />
          <path d="M 130 0 L 130 96" />
          <path d="M 200 0 L 200 96" />
        </g>

        {/* Buildings — scattered blocks for texture */}
        <g fill="#2c3046" opacity="0.6">
          <rect x="20" y="14" width="22" height="10" rx="1.5" />
          <rect x="60" y="66" width="18" height="10" rx="1.5" />
          <rect x="100" y="14" width="16" height="10" rx="1.5" />
          <rect x="148" y="66" width="22" height="10" rx="1.5" />
          <rect x="186" y="14" width="10" height="10" rx="1.5" />
          <rect x="248" y="66" width="22" height="10" rx="1.5" />
          <rect x="282" y="14" width="16" height="10" rx="1.5" />
        </g>

        {/* Destination pin in the visual center. */}
        <g transform="translate(160 50)">
          <circle r="14" fill="#C7FF3D" opacity="0.15" />
          <circle r="6" fill="#C7FF3D" />
          <circle r="2" fill="#0B0B15" />
        </g>
      </svg>

      {addressLine ? (
        <div className="absolute left-2 bottom-2 right-2 truncate text-[10px] font-mono text-white/70 bg-black/40 backdrop-blur-[2px] rounded px-2 py-1 ring-1 ring-white/[0.06]">
          {addressLine}
        </div>
      ) : null}
    </div>
  );
}
