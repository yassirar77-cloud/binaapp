'use client';

import type { Plan, SubscriptionStatus } from '../types';

interface Props {
  subscription: SubscriptionStatus;
  plans: Plan[];
}

function rm(n: number) {
  return 'RM ' + n.toLocaleString('en-MY', { minimumFractionDigits: 0, maximumFractionDigits: 0 });
}

function formatMonthYearBM(iso: string) {
  return new Date(iso).toLocaleDateString('ms-MY', { month: 'short', year: 'numeric' });
}

function formatDateBM(iso: string) {
  return new Date(iso).toLocaleDateString('ms-MY', { day: 'numeric', month: 'long', year: 'numeric' });
}

function monthsSince(iso: string): string {
  const start = new Date(iso);
  const now = new Date();
  const months = (now.getFullYear() - start.getFullYear()) * 12 + (now.getMonth() - start.getMonth());
  if (months < 1) return 'kurang dari sebulan';
  if (months === 1) return '1 bulan';
  return `${months} bulan`;
}

export default function CurrentPlanBanner({ subscription, plans }: Props) {
  const currentPlan = plans.find((p) => p.plan_name === subscription.plan_name);

  if (!currentPlan) {
    console.warn(
      `[CurrentPlanBanner] No plan in plans[] matches subscription.plan_name="${subscription.plan_name}". Hiding price line.`
    );
  }

  const planLabel = currentPlan?.display_name ?? subscription.plan_name;
  const price = currentPlan?.price;
  const isExpired = subscription.is_expired;

  return (
    <div
      className="relative overflow-hidden rounded-[24px] border border-volt-400/20 px-7 py-7 text-white shadow-lift"
      style={{ background: 'linear-gradient(135deg, #1A1B3C 0%, #0B0B15 60%, #0B0B15 100%)' }}
    >
      <svg
        aria-hidden="true"
        className="pointer-events-none absolute -right-8 -top-8 opacity-[0.14]"
        width="280"
        height="220"
        viewBox="0 0 280 220"
      >
        <defs>
          <pattern id="cpb-grid" width="22" height="22" patternUnits="userSpaceOnUse">
            <path d="M22 0H0V22" fill="none" stroke="#C7FF3D" strokeWidth=".5" />
          </pattern>
        </defs>
        <rect width="280" height="220" fill="url(#cpb-grid)" />
      </svg>
      <div
        aria-hidden="true"
        className="pointer-events-none absolute right-7 top-7 h-[110px] w-[110px] rounded-full blur-lg"
        style={{ background: 'radial-gradient(circle, rgba(79,61,255,.55), transparent 70%)' }}
      />

      <div className="relative grid grid-cols-1 gap-8 md:grid-cols-[1fr_auto] md:items-center">
        <div>
          <div className="mb-3.5 flex items-center gap-2">
            <span className="font-geist-mono text-[10px] font-semibold tracking-[0.14em] text-volt-400">
              PELAN SEMASA
            </span>
            <span
              className={`inline-block h-1.5 w-1.5 rounded-full ${
                isExpired ? 'bg-err-400' : 'bg-ok-400 shadow-[0_0_10px_#22C08F]'
              }`}
              aria-hidden="true"
            />
            <span
              className={`font-geist-mono text-[10px] font-semibold tracking-[0.14em] ${
                isExpired ? 'text-err-400' : 'text-ok-400'
              }`}
            >
              {isExpired ? 'TAMAT' : 'AKTIF'}
            </span>
          </div>

          <div className="flex flex-wrap items-end gap-4">
            <h2 className="text-[56px] font-extrabold leading-none tracking-[-0.045em] text-white">
              {planLabel}
            </h2>
            {price !== undefined && (
              <div className="pb-2 text-[22px] font-semibold tracking-[-0.02em] text-white">
                {rm(price)}
                <span className="font-medium text-brand-300">/bulan</span>
              </div>
            )}
          </div>

          <div className="mt-6 flex flex-wrap gap-7">
            {subscription.end_date && (
              <BannerStat
                label={isExpired ? 'Tamat pada' : 'Bil seterusnya'}
                value={price !== undefined ? rm(price) : formatDateBM(subscription.end_date)}
                sub={price !== undefined ? formatDateBM(subscription.end_date) : undefined}
              />
            )}
            {subscription.start_date && (
              <BannerStat
                label="Aktif sejak"
                value={formatMonthYearBM(subscription.start_date)}
                sub={monthsSince(subscription.start_date)}
              />
            )}
            <BannerStat
              label="Status auto-renew"
              value={subscription.auto_renew ? 'Hidup' : 'Mati'}
              sub={subscription.auto_renew ? 'Boleh batal bila-bila' : 'Bil seterusnya manual'}
              volt={subscription.auto_renew}
            />
          </div>
        </div>

        <button
          type="button"
          onClick={() =>
            document.getElementById('sec-pelan')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
          }
          className="flex min-w-[180px] items-center justify-center gap-2 rounded-xl bg-volt-400 px-5 py-3.5 text-[14px] font-bold tracking-[-0.01em] text-ink-900 shadow-glow-volt transition-colors hover:bg-volt-300"
        >
          <svg
            width="14"
            height="14"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.5"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
          >
            <polyline points="17 11 12 6 7 11" />
            <polyline points="17 18 12 13 7 18" />
          </svg>
          Tukar pelan
        </button>
      </div>
    </div>
  );
}

function BannerStat({
  label,
  value,
  sub,
  volt = false,
}: {
  label: string;
  value: string;
  sub?: string;
  volt?: boolean;
}) {
  return (
    <div>
      <div className="mb-1 font-geist-mono text-[9.5px] font-medium uppercase tracking-[0.12em] text-ink-400">
        {label}
      </div>
      <div
        className={`text-[17px] font-semibold tracking-[-0.02em] tabular-nums ${
          volt ? 'text-volt-400' : 'text-white'
        }`}
      >
        {value}
      </div>
      {sub && <div className="mt-0.5 text-[11.5px] text-ink-400">{sub}</div>}
    </div>
  );
}
