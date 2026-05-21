'use client';

import { ArrowRight, Check } from 'lucide-react';
import type { Plan, SubscriptionStatus } from '../types';
import SectionHeader from './SectionHeader';

// Mirrors backend ordering in subscription.py:199.
// An unknown plan_name resolves to 0, matching backend's `.get(p, 0)`.
const PLAN_ORDER: Record<string, number> = { starter: 1, basic: 2, pro: 3 };

interface Props {
  plans: Plan[];
  subscription: SubscriptionStatus | null;
  processing: boolean;
  onUpgrade: (planName: string) => void;
}

function formatRM(n: number): string {
  return 'RM ' + n.toLocaleString('en-MY', { minimumFractionDigits: 0, maximumFractionDigits: 0 });
}

function formatLimit(limit: number | null): string {
  if (limit === null) return 'Tanpa had';
  if (limit === 0) return 'Tidak tersedia';
  return limit.toString();
}

const LIMIT_ROWS: { label: string; key: keyof Plan }[] = [
  { label: 'Laman Web', key: 'websites_limit' },
  { label: 'Item Menu', key: 'menu_items_limit' },
  { label: 'AI Hero/bulan', key: 'ai_hero_limit' },
  { label: 'Imej AI/bulan', key: 'ai_images_limit' },
  { label: 'Zon Penghantaran', key: 'delivery_zones_limit' },
  { label: 'Rider', key: 'riders_limit' },
];

interface CardState {
  // Badge precedence (highest to lowest):
  //   1. Current plan → "PELAN ANDA" + volt glow ring (always wins)
  //   2. Basic non-current → "PALING POPULAR" + indigo treatment
  //   3. Pro non-current → dark-card treatment, no badge
  //   4. Otherwise → plain card, no badge
  variant: 'current' | 'popular' | 'dark' | 'plain';
  // Button state — exactly one applies per card:
  //   - currentPlan: disabled, "Pelan Semasa"
  //   - canUpgrade: enabled, "Naik taraf ke {name}"
  //   - lowerTier: disabled, "Hubungi sokongan" (backend rejects downgrade)
  //   - unknown: disabled, "Tidak tersedia" (plan_name not in PLAN_ORDER)
  cta: 'currentPlan' | 'canUpgrade' | 'lowerTier' | 'unknown';
}

function resolveCardState(plan: Plan, subscription: SubscriptionStatus | null): CardState {
  const isCurrent = subscription?.plan_name === plan.plan_name;

  let variant: CardState['variant'];
  if (isCurrent) variant = 'current';
  else if (plan.plan_name === 'basic') variant = 'popular';
  else if (plan.plan_name === 'pro') variant = 'dark';
  else variant = 'plain';

  let cta: CardState['cta'];
  if (isCurrent) {
    cta = 'currentPlan';
  } else {
    const planRank = PLAN_ORDER[plan.plan_name] ?? 0;
    const currentRank = subscription ? (PLAN_ORDER[subscription.plan_name] ?? 0) : 0;
    if (planRank === 0) cta = 'unknown';
    else if (planRank > currentRank) cta = 'canUpgrade';
    else cta = 'lowerTier';
  }

  return { variant, cta };
}

function PlanCardView({
  plan,
  state,
  processing,
  onUpgrade,
}: {
  plan: Plan;
  state: CardState;
  processing: boolean;
  onUpgrade: (name: string) => void;
}) {
  const isDark = state.variant === 'dark';
  const fg = isDark ? 'text-[#F5F5FA]' : 'text-ink-900';
  const muted = isDark ? 'text-ink-300' : 'text-ink-500';
  const codeColor =
    isDark ? 'text-volt-400' : state.variant === 'popular' ? 'text-brand-500' : 'text-ink-400';

  const features = plan.feature_list ?? [];
  const useLimitsFallback = features.length === 0;

  // Border + shadow per variant. `current` always wins via the volt ring.
  const ringClass =
    state.variant === 'current'
      ? 'border-2 border-volt-400 shadow-[0_20px_50px_rgba(199,255,61,0.22),0_0_0_6px_rgba(199,255,61,0.08)]'
      : state.variant === 'popular'
        ? 'border-2 border-brand-500 shadow-[0_20px_50px_rgba(79,61,255,0.18)]'
        : isDark
          ? 'border border-white/[0.08]'
          : 'border border-ink-200';

  const bgClass = isDark ? 'bg-ink-900' : 'bg-white';
  const checkBg =
    isDark
      ? 'bg-volt-400/15 text-volt-400'
      : state.variant === 'popular'
        ? 'bg-brand-500/10 text-brand-500'
        : 'bg-ok-400/15 text-ok-500';

  return (
    <div className={`relative flex flex-col rounded-[24px] px-6 pb-6 pt-7 ${bgClass} ${ringClass}`}>
      {state.variant === 'current' && (
        <span className="absolute -top-3 left-6 flex items-center gap-1.5 rounded-full bg-volt-400 px-3 py-[5px] font-geist-mono text-[10.5px] font-bold tracking-[0.1em] text-ink-900 shadow-[0_6px_16px_rgba(199,255,61,0.4)]">
          <Check size={11} strokeWidth={3} />
          PELAN ANDA
        </span>
      )}
      {state.variant === 'popular' && (
        <span className="absolute -top-3 left-6 rounded-full bg-brand-500 px-3 py-[5px] font-geist-mono text-[10.5px] font-bold tracking-[0.1em] text-white shadow-[0_6px_16px_rgba(79,61,255,0.4)]">
          PALING POPULAR
        </span>
      )}

      <div className={`mb-2.5 font-geist-mono text-[11px] font-semibold uppercase tracking-[0.14em] ${codeColor}`}>
        {plan.plan_name.toUpperCase()}
      </div>

      <div className="mb-1 flex items-baseline gap-1">
        <span className={`text-[58px] font-extrabold leading-none tracking-[-0.045em] tabular-nums ${fg}`}>
          {formatRM(plan.price)}
        </span>
        <span className={`text-[15px] font-medium ${muted}`}>/bln</span>
      </div>
      <div className={`text-[13px] ${muted}`}>{plan.display_name}</div>

      <div className={`my-5 h-px ${isDark ? 'bg-white/[0.08]' : 'bg-ink-100'}`} />

      <ul className="m-0 flex flex-1 list-none flex-col gap-2.5 p-0">
        {useLimitsFallback
          ? LIMIT_ROWS.map((row) => (
              <li
                key={row.key}
                className={`flex items-start justify-between text-[13.5px] leading-snug ${fg}`}
              >
                <span className={muted}>{row.label}</span>
                <span className="font-medium tabular-nums">
                  {formatLimit(plan[row.key] as number | null)}
                </span>
              </li>
            ))
          : features.map((f, i) => (
              <li
                key={`${f}-${i}`}
                className={`flex items-start gap-2.5 text-[13.5px] leading-snug tracking-[-0.005em] ${fg}`}
              >
                <span
                  className={`mt-[1px] grid h-[18px] w-[18px] flex-shrink-0 place-items-center rounded-[5px] ${checkBg}`}
                >
                  <Check size={11} strokeWidth={3} />
                </span>
                {f}
              </li>
            ))}
      </ul>

      <CTA state={state} plan={plan} processing={processing} onUpgrade={onUpgrade} />
    </div>
  );
}

function CTA({
  state,
  plan,
  processing,
  onUpgrade,
}: {
  state: CardState;
  plan: Plan;
  processing: boolean;
  onUpgrade: (name: string) => void;
}) {
  const isDark = state.variant === 'dark';
  const popular = state.variant === 'popular';

  if (state.cta === 'currentPlan') {
    return (
      <button
        type="button"
        disabled
        className={`mt-6 w-full rounded-xl border border-dashed px-5 py-3.5 text-[14px] font-bold tracking-[-0.005em] ${
          isDark ? 'border-white/[0.16] text-ink-400' : 'border-ink-200 text-ink-400'
        }`}
      >
        Pelan Semasa
      </button>
    );
  }

  if (state.cta === 'lowerTier' || state.cta === 'unknown') {
    const label = state.cta === 'lowerTier' ? 'Hubungi sokongan' : 'Tidak tersedia';
    const title =
      state.cta === 'lowerTier'
        ? 'Hubungi sokongan untuk turun pelan'
        : 'Pelan ini tidak boleh dipilih';
    return (
      <button
        type="button"
        disabled
        title={title}
        className={`mt-6 w-full cursor-not-allowed rounded-xl px-5 py-3.5 text-[14px] font-bold tracking-[-0.005em] ${
          isDark ? 'bg-white/[0.06] text-ink-400' : 'bg-ink-100 text-ink-400'
        }`}
      >
        {label}
      </button>
    );
  }

  // canUpgrade
  const bgBtn = popular
    ? 'bg-brand-500 hover:bg-brand-600 text-white shadow-[0_10px_24px_rgba(79,61,255,0.32)]'
    : isDark
      ? 'bg-volt-400 hover:bg-volt-300 text-ink-900 shadow-glow-volt'
      : 'bg-ink-900 hover:bg-ink-800 text-white';

  return (
    <button
      type="button"
      onClick={() => onUpgrade(plan.plan_name)}
      disabled={processing}
      className={`mt-6 flex w-full items-center justify-center gap-1.5 rounded-xl px-5 py-3.5 text-[14px] font-bold tracking-[-0.005em] transition-colors disabled:opacity-60 ${bgBtn}`}
    >
      {processing ? 'Memproses…' : `Naik taraf ke ${plan.display_name}`}
      {!processing && <ArrowRight size={13} strokeWidth={2.5} />}
    </button>
  );
}

export default function PlanCards({ plans, subscription, processing, onUpgrade }: Props) {
  const renderable = plans.filter((p) => {
    if (!p.plan_name || !p.display_name || p.price === null || p.price === undefined) {
      console.warn(
        `[PlanCards] Plan missing required field(s); hiding card. Got: ${JSON.stringify({
          plan_name: p.plan_name,
          display_name: p.display_name,
          price: p.price,
        })}`
      );
      return false;
    }
    return true;
  });

  if (renderable.length === 0) return null;

  // Sort by PLAN_ORDER so cards appear Starter → Basic → Pro regardless of API order.
  // Unknown plans fall to the end.
  const sorted = [...renderable].sort(
    (a, b) => (PLAN_ORDER[a.plan_name] ?? 99) - (PLAN_ORDER[b.plan_name] ?? 99)
  );

  return (
    <div>
      <SectionHeader
        eyebrow="Pilih pelan"
        title="Tukar pelan, bila-bila masa"
        sub="Naik taraf diproses serta-merta melalui ToyyibPay. Untuk turun pelan, sila hubungi sokongan."
      />
      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        {sorted.map((plan) => (
          <PlanCardView
            key={plan.plan_name}
            plan={plan}
            state={resolveCardState(plan, subscription)}
            processing={processing}
            onUpgrade={onUpgrade}
          />
        ))}
      </div>
    </div>
  );
}
