import type { Metadata } from 'next'
import type { ReactNode } from 'react'
import { OrderShell } from '@/components/order/OrderShell'
import './theme.css'

export const metadata: Metadata = {
  title: 'BinaApp Delivery',
  description: 'Tempah makanan dari restoran kegemaran anda.',
}

export default function OrderLayout({ children }: { children: ReactNode }) {
  return <OrderShell>{children}</OrderShell>
}
