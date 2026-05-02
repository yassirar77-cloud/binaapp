export type ProgressMax = number | 'unlimited'

interface ProgressBarProps {
  value: number
  max: ProgressMax
  color: string
}

export function ProgressBar({ value, max, color }: ProgressBarProps) {
  const pct =
    max === 'unlimited'
      ? Math.min(100, value)
      : max === 0
        ? 0
        : (value / max) * 100
  return (
    <div
      style={{
        height: 3,
        width: '100%',
        background: '#eeeff2',
        borderRadius: 'var(--r-pill)',
        overflow: 'hidden',
      }}
    >
      <div
        style={{
          height: '100%',
          width: `${Math.max(2, pct)}%`,
          background: color,
          borderRadius: 'var(--r-pill)',
          transition: 'width 420ms cubic-bezier(.25,1,.5,1)',
        }}
      />
    </div>
  )
}
