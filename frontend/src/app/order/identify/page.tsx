import type { Metadata } from 'next'
import { IdentifyForm } from '@/components/order/identify/IdentifyForm'

export const metadata: Metadata = {
  title: 'Selamat datang · BinaApp',
  description: 'Masukkan nombor telefon untuk mula tempah.',
}

export default function IdentifyPage() {
  return (
    <div className="phone-page">
      <IdentifyForm />
    </div>
  )
}
