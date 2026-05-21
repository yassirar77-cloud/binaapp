'use client';

import { useEffect, useRef, useState } from 'react';

const PILLS = [
  { id: 'sec-bil', label: 'Bil & Langganan' },
  { id: 'sec-penggunaan', label: 'Penggunaan' },
  { id: 'sec-sejarah', label: 'Sejarah' },
  { id: 'sec-kaedah', label: 'Kaedah bayar' },
] as const;

export default function BillingSubnav() {
  const [active, setActive] = useState<string>(PILLS[0].id);
  const observerRef = useRef<IntersectionObserver | null>(null);

  useEffect(() => {
    const visible = new Set<string>();

    observerRef.current = new IntersectionObserver(
      (entries) => {
        for (const e of entries) {
          if (e.isIntersecting) visible.add(e.target.id);
          else visible.delete(e.target.id);
        }
        const topmost = PILLS.find((p) => visible.has(p.id))?.id;
        if (topmost) setActive(topmost);
      },
      { rootMargin: '-40% 0px -55% 0px', threshold: 0 }
    );

    PILLS.forEach((p) => {
      const el = document.getElementById(p.id);
      if (el) observerRef.current?.observe(el);
    });

    return () => observerRef.current?.disconnect();
  }, []);

  const scrollTo = (id: string) => {
    document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };

  return (
    <nav
      aria-label="Bahagian Bil & Langganan"
      className="sticky top-14 z-20 -mt-2 bg-white/85 backdrop-blur-md border-b border-ink-200"
    >
      <div className="flex gap-1.5 overflow-x-auto py-2.5">
        {PILLS.map((p) => {
          const isActive = active === p.id;
          return (
            <button
              key={p.id}
              type="button"
              onClick={() => scrollTo(p.id)}
              aria-current={isActive ? 'true' : undefined}
              className={`whitespace-nowrap rounded-full px-3 py-1.5 text-[12.5px] font-medium tracking-[-0.005em] transition-colors ${
                isActive
                  ? 'bg-ink-900 text-white'
                  : 'border border-ink-200 text-ink-500 hover:text-ink-700'
              }`}
            >
              {p.label}
            </button>
          );
        })}
      </div>
    </nav>
  );
}
