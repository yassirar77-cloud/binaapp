'use client';

import React, { useEffect, useRef, useState } from 'react';
import { List, X } from 'lucide-react';

export type TOCItem = {
  id: string;
  title: string;
};

type Props = {
  /** Items in the order they appear in the document. The hook tracks
   *  which one is currently in view as the user scrolls. */
  items: TOCItem[];
  /** Localized header label for the TOC, e.g. "Senarai kandungan"
   *  / "Table of contents". */
  label: string;
  /** Localized mobile drawer toggle aria-labels. */
  mobileLabels?: {
    open: string;
    close: string;
  };
};

const DEFAULT_MOBILE_LABELS = {
  open: 'Open table of contents',
  close: 'Close table of contents',
};

/**
 * Sticky sidebar table of contents with scroll spy.
 *
 * Desktop (lg+): renders in a sticky right column (parent is responsible
 * for the lg:grid-cols-[1fr_18rem] layout in LegalDocument).
 *
 * Mobile: collapses to a floating "List" button bottom-right that opens
 * a bottom-up drawer with the full TOC. Tapping any item closes the
 * drawer and scroll-snaps to the section.
 *
 * Scroll spy uses IntersectionObserver with a top-25% rootMargin so the
 * highlighted item changes when the section heading crosses roughly a
 * quarter of the viewport down — feels natural when scrolling at any
 * speed. Without this, very long sections cause the "active" item to
 * lag behind where the user is actually reading.
 */
export function LegalTOC({
  items,
  label,
  mobileLabels = DEFAULT_MOBILE_LABELS,
}: Props) {
  const [activeId, setActiveId] = useState<string | null>(items[0]?.id ?? null);
  const [mobileOpen, setMobileOpen] = useState(false);
  // Track items currently in view; we pick the topmost.
  const visibleRef = useRef<Set<string>>(new Set());

  useEffect(() => {
    if (typeof IntersectionObserver === 'undefined') return;

    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            visibleRef.current.add(entry.target.id);
          } else {
            visibleRef.current.delete(entry.target.id);
          }
        }
        // Pick the first item (in document order) that's currently visible.
        for (const item of items) {
          if (visibleRef.current.has(item.id)) {
            setActiveId(item.id);
            return;
          }
        }
      },
      {
        rootMargin: '-25% 0px -60% 0px',
        threshold: 0,
      },
    );

    for (const item of items) {
      const el = document.getElementById(item.id);
      if (el) observer.observe(el);
    }

    return () => observer.disconnect();
  }, [items]);

  // Lock body scroll when the mobile drawer is open
  useEffect(() => {
    if (mobileOpen) {
      const prev = document.body.style.overflow;
      document.body.style.overflow = 'hidden';
      return () => {
        document.body.style.overflow = prev;
      };
    }
  }, [mobileOpen]);

  const renderList = (onItemClick?: () => void) => (
    <ol className="space-y-1 text-sm">
      {items.map((item) => {
        const isActive = activeId === item.id;
        const baseFocus =
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-400 focus-visible:ring-offset-1';
        return (
          <li key={item.id}>
            <a
              href={`#${item.id}`}
              onClick={onItemClick}
              aria-current={isActive ? 'location' : undefined}
              className={
                isActive
                  ? `block rounded-md bg-brand-50 px-3 py-2 text-brand-700 font-medium border-l-2 border-brand-500 -ml-0.5 transition ${baseFocus}`
                  : `block rounded-md px-3 py-2 text-ink-600 hover:text-ink-900 hover:bg-ink-100 transition ${baseFocus}`
              }
            >
              {item.title}
            </a>
          </li>
        );
      })}
    </ol>
  );

  return (
    <>
      {/* Desktop sidebar */}
      <nav aria-label={label} className="hidden lg:block print:hidden">
        <div className="rounded-xl border border-ink-200 bg-white p-4 max-h-[calc(100vh-6rem)] overflow-y-auto">
          <h2 className="text-xs font-semibold uppercase tracking-wider text-ink-500 mb-3 px-3">
            {label}
          </h2>
          {renderList()}
        </div>
      </nav>

      {/* Mobile floating button + drawer */}
      <button
        type="button"
        onClick={() => setMobileOpen(true)}
        className="lg:hidden print:hidden fixed bottom-6 right-6 z-40 inline-flex items-center gap-2 rounded-full bg-brand-500 px-4 py-3 text-sm font-semibold text-white shadow-lift hover:bg-brand-600 transition focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-brand-300"
        aria-label={mobileLabels.open}
      >
        <List className="h-4 w-4" aria-hidden="true" />
        {label}
      </button>

      {mobileOpen && (
        <div className="lg:hidden fixed inset-0 z-50 flex flex-col" role="dialog" aria-modal="true" aria-label={label}>
          {/* Backdrop */}
          <div
            className="absolute inset-0 bg-ink-900/40"
            onClick={() => setMobileOpen(false)}
            aria-hidden="true"
          />
          {/* Drawer */}
          <div className="relative mt-auto w-full max-h-[85vh] bg-white rounded-t-2xl shadow-lift flex flex-col">
            <div className="flex items-center justify-between px-4 py-3 border-b border-ink-100">
              <h2 className="text-sm font-semibold text-ink-900">{label}</h2>
              <button
                type="button"
                onClick={() => setMobileOpen(false)}
                className="rounded-md p-1.5 text-ink-500 hover:text-ink-900 hover:bg-ink-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-400"
                aria-label={mobileLabels.close}
              >
                <X className="h-5 w-5" aria-hidden="true" />
              </button>
            </div>
            <div className="overflow-y-auto p-4">
              {renderList(() => setMobileOpen(false))}
            </div>
          </div>
        </div>
      )}
    </>
  );
}
