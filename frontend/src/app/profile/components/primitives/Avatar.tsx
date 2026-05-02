export type AvatarTone = 'purple' | 'teal' | 'amber'

interface AvatarProps {
  initials: string
  tone?: AvatarTone
  size?: number
}

const TONE_MAP: Record<AvatarTone, [string, string]> = {
  purple: ['var(--avatar-purple-bg)', 'var(--avatar-purple-fg)'],
  teal: ['var(--avatar-teal-bg)', 'var(--avatar-teal-fg)'],
  amber: ['var(--avatar-amber-bg)', 'var(--avatar-amber-fg)'],
}

export function Avatar({ initials, tone = 'purple', size = 38 }: AvatarProps) {
  const [bg, fg] = TONE_MAP[tone]
  return (
    <div
      style={{
        width: size,
        height: size,
        borderRadius: '50%',
        background: bg,
        color: fg,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        fontSize: size >= 56 ? 18 : 13,
        fontWeight: 500,
        letterSpacing: 0,
        flexShrink: 0,
        userSelect: 'none',
      }}
    >
      {initials}
    </div>
  )
}
