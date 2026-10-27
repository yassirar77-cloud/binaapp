/**
 * Legacy /dashboard/create route.
 *
 * The form that used to live here posted to a backend endpoint that no
 * longer exists (POST /api/generate) and nothing links to this page any
 * more. The real website-creation flow lives at /create — forward old
 * bookmarks there and keep the route resolving.
 */

'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'

export default function CreateWebsitePage() {
  const router = useRouter()

  useEffect(() => {
    router.replace('/create')
  }, [router])

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <p className="text-sm text-gray-600">Membawa anda ke halaman cipta website…</p>
    </div>
  )
}
