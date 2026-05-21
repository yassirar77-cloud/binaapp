'use client';

import type { ReactNode } from 'react';
import {
  Bike,
  HelpCircle,
  Map as MapIcon,
  Monitor,
  Plus,
  Sparkles,
  Wand2,
} from 'lucide-react';
import type { Addon, UsageResponse } from '../types';
import SectionHeader from './SectionHeader';

interface Props {
  addons: Addon[];
  usage: UsageResponse | null;
  processing: boolean;
  onBuy: (addonType: string) => void;
}

// Local icon + accent table. Unknown addon.type falls back to a neutral default
// and triggers a console.warn so a new backend addon doesn't silently render
// as a grey blob forever.
const ADDON_VISUAL: Record<string, { color: string; icon: ReactNode }> = {
  ai_image: { color: '#8F5AFF', icon: <Sparkles size={22} strokeWidth={1.8} /> },
  ai_hero: { color: '#4F3DFF', icon: <Wand2 size={22} strokeWidth={1.8} /> },
  website: { color: '#3FB8FF', icon: <Monitor size={22} strokeWidth={1.8} /> },
  rider: { color: '#22C08F', icon: <Bike size={22} strokeWidth={1.8} /> },
  zone: { color: '#FFB020', icon: <MapIcon size={22} strokeWidth={1.8} /> },
};

const NEUTRAL_VISUAL = { color: '#86869A', icon: <HelpCircle size={22} strokeWidth={1.8} /> };

// Maps an addon.type to the matching usage bucket key whose addon_credits
// represents the user's current balance for that addon.
const ADDON_TO_USAGE_KEY: Record<string, keyof NonNullable<UsageResponse['usage']>> = {
  ai_image: 'ai_images',
  ai_hero: 'ai_hero',
  website: 'websites',
  rider: 'riders',
  zone: 'delivery_zones',
};

function formatRM(n: number): string {
  return 'RM ' + n.toLocaleString('en-MY', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function ownedCredits(addonType: string, usage: UsageResponse | null): number {
  if (!usage?.usage) return 0;
  const key = ADDON_TO_USAGE_KEY[addonType];
  if (!key) return 0;
  return usage.usage[key]?.addon_credits ?? 0;
}

function AddonCard({
  addon,
  owned,
  processing,
  onBuy,
}: {
  addon: Addon;
  owned: number;
  processing: boolean;
  onBuy: (type: string) => void;
}) {
  const visual = ADDON_VISUAL[addon.type];
  if (!visual) {
    console.warn(
      `[AddonsGrid] No icon/color mapping for addon.type="${addon.type}" — rendering with neutral default. Add an entry to ADDON_VISUAL.`
    );
  }
  const { color, icon } = visual ?? NEUTRAL_VISUAL;

  return (
    <div className="group relative flex flex-col gap-3 rounded-[18px] border border-ink-200 bg-white px-5 pb-[18px] pt-5 transition-all hover:-translate-y-[2px] hover:border-ink-300 hover:shadow-[0_8px_24px_rgba(11,11,21,0.06)]">
      <div className="flex items-start justify-between">
        <div
          className="grid h-[42px] w-[42px] place-items-center rounded-[11px]"
          style={{ background: `${color}14`, color }}
        >
          {icon}
        </div>
        {owned > 0 && (
          <span className="flex items-center gap-1 rounded-full bg-[#DCFCE7] px-2 py-[3px] font-geist-mono text-[9.5px] font-semibold uppercase tracking-[0.1em] text-ok-500">
            <span className="inline-block h-[5px] w-[5px] rounded-full bg-ok-400" />
            DIMILIKI · {owned}
          </span>
        )}
      </div>

      <div>
        <h4 className="m-0 text-[15px] font-semibold tracking-[-0.02em] text-ink-900">
          {addon.name}
        </h4>
        <p className="mt-1 text-[12.5px] leading-snug text-ink-500">{addon.description}</p>
      </div>

      <div className="mt-1 flex items-center justify-between">
        <span className="text-[20px] font-bold tracking-[-0.03em] tabular-nums text-ink-900">
          {formatRM(addon.price)}
        </span>
        <button
          type="button"
          onClick={() => onBuy(addon.type)}
          disabled={processing}
          className="flex items-center gap-1.5 rounded-[9px] bg-ink-900 px-3.5 py-[7px] text-[12.5px] font-semibold text-white transition-colors hover:bg-ink-800 disabled:opacity-60"
        >
          <Plus size={12} strokeWidth={2.5} />
          {processing ? '…' : 'Beli'}
        </button>
      </div>
    </div>
  );
}

export default function AddonsGrid({ addons, usage, processing, onBuy }: Props) {
  const renderable = addons.filter((a) => {
    if (!a.type || !a.name || a.price === null || a.price === undefined) {
      console.warn(
        `[AddonsGrid] Addon missing required field(s); hiding card. Got: ${JSON.stringify({
          type: a.type,
          name: a.name,
          price: a.price,
        })}`
      );
      return false;
    }
    return true;
  });

  if (renderable.length === 0) return null;

  return (
    <div>
      <SectionHeader
        eyebrow="Tambahan"
        title="Tambahan À la carte"
        sub="Bayar sekali — kredit tidak akan tamat tempoh."
      />
      <div className="grid grid-cols-1 gap-3.5 sm:grid-cols-2 lg:grid-cols-3">
        {renderable.map((addon) => (
          <AddonCard
            key={addon.type}
            addon={addon}
            owned={ownedCredits(addon.type, usage)}
            processing={processing}
            onBuy={onBuy}
          />
        ))}
      </div>
    </div>
  );
}
