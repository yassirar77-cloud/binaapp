'use client';

// MapLegend — bottom-left color key for marker states.

const ITEMS: Array<{ color: string; label: string }> = [
  { color: '#C7FF3D', label: 'Outlet' },
  { color: '#34D399', label: 'Rider online' },
  { color: '#FBBF24', label: 'GPS lapuk' },
  { color: '#71717A', label: 'Offline' },
  { color: '#EF4444', label: 'Tersangkut' },
];

export default function MapLegend() {
  return (
    <div className="absolute bottom-4 left-4 z-[1000] rounded-lg bg-[#0a0e1a]/95 border border-white/[0.08] backdrop-blur-sm px-3 py-2.5">
      <div className="font-mono text-[9px] uppercase tracking-wider text-white/40 mb-1.5">
        Legenda
      </div>
      <ul className="space-y-1">
        {ITEMS.map((it) => (
          <li key={it.label} className="flex items-center gap-2 text-[11px] text-white/70 font-geist">
            <span
              className="h-2 w-2 rounded-full shrink-0"
              style={{ backgroundColor: it.color }}
              aria-hidden
            />
            {it.label}
          </li>
        ))}
      </ul>
    </div>
  );
}
