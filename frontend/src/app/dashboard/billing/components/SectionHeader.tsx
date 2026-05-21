'use client';

export default function SectionHeader({
  eyebrow,
  title,
  sub,
}: {
  eyebrow: string;
  title: string;
  sub?: string;
}) {
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
