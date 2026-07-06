'use client'

import Link from 'next/link'
import { ArrowLeft } from 'lucide-react'

interface BackButtonProps {
  /** Destination to navigate back to. Defaults to the main dashboard. */
  href?: string
  /** Link label. Defaults to "Kembali ke Dashboard". */
  label?: string
  /** Extra classes appended to the default styling. */
  className?: string
}

/**
 * Standard "back" affordance used across dashboard sub-pages.
 *
 * Mirrors the existing pattern on /dashboard/create: an ArrowLeft icon
 * followed by "Kembali ke Dashboard", linking to /dashboard. The min-height
 * guarantees a comfortable tap target on mobile / tablet (Surface, phones).
 */
export default function BackButton({
  href = '/dashboard',
  label = 'Kembali ke Dashboard',
  className = '',
}: BackButtonProps) {
  return (
    <Link
      href={href}
      className={`inline-flex min-h-[44px] items-center gap-2 text-sm text-gray-600 transition-colors hover:text-gray-900 ${className}`}
    >
      <ArrowLeft className="h-5 w-5 shrink-0" />
      {label}
    </Link>
  )
}
