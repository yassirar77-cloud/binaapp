import type { Metadata } from 'next'

import PromosiClient from './PromosiClient'

export const metadata: Metadata = {
  title: 'Promosi | BinaApp',
}

export default function PromosiPage() {
  return <PromosiClient />
}
