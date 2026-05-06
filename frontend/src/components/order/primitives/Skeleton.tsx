import type { HTMLAttributes } from 'react'
import { cn } from '@/lib/utils'

export type SkeletonProps = HTMLAttributes<HTMLDivElement>

export function Skeleton({ className, style, ...rest }: SkeletonProps) {
  return (
    <div
      role="status"
      aria-busy="true"
      aria-label="Memuatkan"
      className={cn('skel', className)}
      style={style}
      {...rest}
    />
  )
}
