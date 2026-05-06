import type { HTMLAttributes } from 'react'
import { cn } from '@/lib/utils'

export type SpinnerProps = HTMLAttributes<HTMLSpanElement>

export function Spinner({ className, ...rest }: SpinnerProps) {
  return (
    <span
      role="status"
      aria-label="Memuatkan"
      className={cn('spinner', className)}
      {...rest}
    />
  )
}
