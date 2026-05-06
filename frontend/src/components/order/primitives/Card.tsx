import type { HTMLAttributes } from 'react'
import { cn } from '@/lib/utils'

export type CardProps = HTMLAttributes<HTMLDivElement>

export function Card({ className, ...rest }: CardProps) {
  return <div className={cn('card', className)} {...rest} />
}
