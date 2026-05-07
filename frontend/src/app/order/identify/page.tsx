import type { Metadata } from 'next'
import { IdentifyPageClient } from '@/components/order/identify/IdentifyPageClient'

export const metadata: Metadata = {
  title: 'Selamat datang · BinaApp',
  description: 'Masukkan nombor telefon untuk mula tempah.',
}

export default function IdentifyPage() {
  return <IdentifyPageClient />
}
