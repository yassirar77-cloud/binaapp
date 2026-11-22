import type { Metadata } from 'next'

import MascotVideoClient from './MascotVideoClient'

export const metadata: Metadata = {
  title: 'Video Maskot | BinaApp',
}

export default function MascotVideoPage() {
  return <MascotVideoClient />
}
