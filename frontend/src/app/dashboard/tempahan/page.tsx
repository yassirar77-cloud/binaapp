import type { Metadata } from 'next'

import TempahanClient from './TempahanClient'

export const metadata: Metadata = {
  title: 'Tempahan | BinaApp',
}

export default function TempahanPage() {
  return <TempahanClient />
}
