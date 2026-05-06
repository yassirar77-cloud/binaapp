import type { HTMLAttributes, ReactNode } from 'react'
import { cn } from '@/lib/utils'

export interface EyebrowProps extends HTMLAttributes<HTMLDivElement> {
  children?: ReactNode
}

export function Eyebrow({ className, children, ...rest }: EyebrowProps) {
  return (
    <div className={cn('eyebrow', className)} {...rest}>
      {children}
    </div>
  )
}
