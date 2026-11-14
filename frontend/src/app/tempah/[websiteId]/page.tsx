import type { Metadata } from 'next'

import BookingClient from './BookingClient'

export const metadata: Metadata = {
  title: 'Tempah Slot',
  description: 'Tempah slot temujanji dalam talian.',
}

export default function TempahPage({ params }: { params: { websiteId: string } }) {
  return <BookingClient websiteId={params.websiteId} />
}
