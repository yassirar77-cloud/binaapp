'use client';

import type { ReactNode } from 'react';
import { Globe, Sparkles, Utensils } from 'lucide-react';
import type { UsageData, UsageResponse } from '../types';

interface NormalizedUsage {
  used: number;
  unlimited: boolean;
  totalLimit: number;
  addonCredits: number;
  percentage: number;
}

function normalizeOne(u: UsageData): NormalizedUsage {
  const unlimited = u.unlimited || u.limit === null;
  if (unlimited) {
    return { used: u.used, unlimited: true, totalLimit: 0, addonCredits: 0, percentage: 0 };
  }
  const base = u.limit ?? 0;
  const addonCredits = u.addon_credits ?? 0;
  const totalLimit = base + addonCredits;
  return {
    used: u.used,
    unlimited: false,
    totalLimit,
    addonCredits,
    percentage: totalLimit === 0 ? 0 : Math.min(100, (u.used / totalLimit) * 100),
  };
}

function combineTwo(a: UsageData, b: UsageData): NormalizedUsage {
  const unlimited = a.unlimited || b.unlimited || a.limit === null || b.limit === null;
  const usedTotal = a.used + b.used;
  if (unlimited) {
    return { used: usedTotal, unlimited: true, totalLimit: 0, addonCredits: 0, percentage: 0 };
  }
  const baseTotal = (a.limit ?? 0) + (b.limit ?? 0);
  const addonCredits = (a.addon_credits ?? 0) + (b.addon_credits ?? 0);
  const totalLimit = baseTotal + addonCredits;
  return {
    used: usedTotal,
    unlimited: false,
    totalLimit,
    addonCredits,
    percentage: totalLimit === 0 ? 0 : Math.min(100, (usedTotal / totalLimit) * 100),
  };
}

function partLabel(name: string, u: UsageData): string {
  if (u.unlimited || u.limit === null) return `${name}: ${u.used}/∞`;
  const total = (u.limit ?? 0) + (u.addon_credits ?? 0);
  return `${name}: ${u.used}/${total}`;
}

interface UsageCardProps {
  icon: ReactNode;
  label: string;
  color: string;
  data: NormalizedUsage;
  breakdown?: string;
  highlight?: boolean;
  badge?: string;
}

function UsageCard({ icon, label, color, data, breakdown, highlight = false, badge }: UsageCardProps) {
  const showBar = !data.unlimited;
  const hasAddons = data.addonCredits > 0;

  return (
    <div
      className={`relative overflow-hidden rounded-[20px] px-6 py-5 ${
        highlight
          ? 'bg-ink-900 border border-volt-400/30 shadow-[0_12px_32px_rgba(199,255,61,0.10)]'
          : 'bg-white border border-ink-200 shadow-soft'
      }`}
    >
      {highlight && (
        <svg
          aria-hidden="true"
          className="pointer-events-none absolute -right-10 -top-10 opacity-[0.08]"
          width="180"
          height="180"
          viewBox="0 0 180 180"
        >
          <circle cx="90" cy="90" r="80" fill="none" stroke="#C7FF3D" strokeWidth="1" />
          <circle cx="90" cy="90" r="56" fill="none" stroke="#C7FF3D" strokeWidth="1" />
          <circle cx="90" cy="90" r="32" fill="none" stroke="#C7FF3D" strokeWidth="1" />
        </svg>
      )}

      <div className="relative mb-3.5 flex items-start justify-between">
        <div
          className="grid h-[38px] w-[38px] place-items-center rounded-[10px]"
          style={{
            background: highlight ? 'rgba(199,255,61,0.14)' : `${color}14`,
            color: highlight ? '#C7FF3D' : color,
          }}
        >
          {icon}
        </div>
        {(data.unlimited || badge) && (
          <span
            className={`font-geist-mono text-[9.5px] font-semibold uppercase tracking-[0.1em] rounded-full px-2 py-[3px] ${
              highlight
                ? 'bg-volt-400 text-ink-900'
                : data.unlimited
                  ? 'bg-ok-400/15 text-ok-500'
                  : 'bg-brand-50 text-brand-500'
            }`}
          >
            {data.unlimited ? 'TANPA HAD' : badge}
          </span>
        )}
      </div>

      <div
        className={`relative mb-1.5 font-geist-mono text-[10px] font-medium uppercase tracking-[0.12em] ${
          highlight ? 'text-brand-300' : 'text-ink-400'
        }`}
      >
        {label}
      </div>

      <div className="relative flex items-baseline gap-2">
        <div
          className={`text-[38px] font-extrabold leading-none tracking-[-0.045em] tabular-nums ${
            highlight ? 'text-white' : 'text-ink-900'
          }`}
        >
          {data.used.toLocaleString('en-MY')}
        </div>
        {!data.unlimited && (
          <div className={`text-[14px] font-medium ${highlight ? 'text-ink-300' : 'text-ink-400'}`}>
            / {data.totalLimit.toLocaleString('en-MY')}
          </div>
        )}
      </div>

      {breakdown && (
        <div
          className={`relative mt-1.5 text-[11.5px] ${highlight ? 'text-ink-300' : 'text-ink-500'}`}
        >
          {breakdown}
        </div>
      )}

      {showBar && (
        <div className="relative mt-4">
          <div
            className="h-1.5 overflow-hidden rounded-full"
            style={{ background: highlight ? 'rgba(255,255,255,0.08)' : '#F0F0F5' }}
          >
            <div
              className="h-full rounded-full transition-[width] duration-500 ease-out"
              style={{
                width: `${data.percentage}%`,
                background: highlight ? '#C7FF3D' : color,
              }}
            />
          </div>
          <div
            className={`mt-1.5 flex justify-between font-geist-mono text-[10.5px] ${
              highlight ? 'text-ink-400' : 'text-ink-400'
            }`}
          >
            <span>{data.used.toLocaleString('en-MY')} digunakan</span>
            <span>
              {data.totalLimit.toLocaleString('en-MY')} had
              {hasAddons && ` (+${data.addonCredits} tambahan)`}
            </span>
          </div>
        </div>
      )}
    </div>
  );
}

function SectionHeader({ eyebrow, title, sub }: { eyebrow: string; title: string; sub?: string }) {
  return (
    <div className="mb-4">
      <div className="font-geist-mono text-[10.5px] font-semibold uppercase tracking-[0.14em] text-brand-500">
        — {eyebrow}
      </div>
      <h3 className="mt-1.5 text-[22px] font-bold tracking-[-0.03em] text-ink-900">{title}</h3>
      {sub && <p className="mt-1 text-[13px] text-ink-400">{sub}</p>}
    </div>
  );
}

export default function UsageHeroCards({ usage }: { usage: UsageResponse | null }) {
  if (!usage?.usage) {
    console.warn('[UsageHeroCards] No usage response — hiding section.');
    return null;
  }

  const { websites, menu_items, ai_hero, ai_images } = usage.usage;
  const monthLabel = new Date().toLocaleDateString('ms-MY', { month: 'long', year: 'numeric' });

  const cards: ReactNode[] = [];

  if (websites) {
    cards.push(
      <UsageCard
        key="websites"
        icon={<Globe size={20} strokeWidth={1.8} />}
        label="Website Aktif"
        color="#4F3DFF"
        data={normalizeOne(websites)}
      />
    );
  } else {
    console.warn('[UsageHeroCards] usage.websites missing — card hidden.');
  }

  if (menu_items) {
    cards.push(
      <UsageCard
        key="menu_items"
        icon={<Utensils size={20} strokeWidth={1.8} />}
        label="Item Menu"
        color="#3FB8FF"
        data={normalizeOne(menu_items)}
      />
    );
  } else {
    console.warn('[UsageHeroCards] usage.menu_items missing — card hidden.');
  }

  if (ai_hero && ai_images) {
    cards.push(
      <UsageCard
        key="ai_combined"
        icon={<Sparkles size={20} strokeWidth={1.8} />}
        label="AI Dijana Bulan Ini"
        color="#C7FF3D"
        highlight
        badge="BULAN INI"
        data={combineTwo(ai_hero, ai_images)}
        breakdown={`${partLabel('Hero', ai_hero)} · ${partLabel('Imej', ai_images)}`}
      />
    );
  } else {
    console.warn(
      '[UsageHeroCards] ai_hero or ai_images missing — combined AI card hidden.'
    );
  }

  if (cards.length === 0) return null;

  return (
    <div>
      <SectionHeader
        eyebrow="Penggunaan"
        title="Penggunaan bulan ini"
        sub={`Dikira semula setiap 1hb · ${monthLabel}`}
      />
      <div className="grid grid-cols-1 gap-3.5 md:grid-cols-3">{cards}</div>
    </div>
  );
}
