'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { getCurrentUser, getStoredToken, signOut } from '@/lib/supabase'
import {
  Button,
  Card,
  Badge,
  EmptyState,
  LoadingSpinner,
  Modal,
} from '@/components/ui'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'https://binaapp-backend.onrender.com'

interface Website {
  id: string
  business_name: string
  subdomain: string | null
  full_url: string | null
  status: string
  created_at: string
  published_at: string | null
}

interface User {
  id: string
  email: string
  full_name?: string
}

export default function MyProjectsPage() {
  const router = useRouter()
  const [loading, setLoading] = useState(true)
  const [websites, setWebsites] = useState<Website[]>([])
  const [user, setUser] = useState<User | null>(null)
  const [deleting, setDeleting] = useState<string | null>(null)
  const [confirmDelete, setConfirmDelete] = useState<Website | null>(null)

  useEffect(() => {
    checkAuthAndGetWebsites()
  }, [])

  async function checkAuthAndGetWebsites() {
    try {
      setLoading(true)
      const token = getStoredToken()
      const currentUser = await getCurrentUser()

      if (!token || !currentUser) {
        router.push('/login')
        return
      }

      setUser(currentUser as User)

      const response = await fetch(`${API_BASE}/api/v1/websites/`, {
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      })

      if (response.status === 401) {
        router.push('/login')
        return
      }

      if (response.ok) {
        const data = await response.json()
        setWebsites(data || [])
      } else {
        setWebsites([])
      }
    } catch (error) {
      console.error('Error:', error)
      setWebsites([])
    } finally {
      setLoading(false)
    }
  }

  async function deleteWebsite(site: Website) {
    try {
      setDeleting(site.id)
      const token = getStoredToken()
      if (!token) {
        router.push('/login')
        return
      }

      const response = await fetch(`${API_BASE}/api/v1/websites/${site.id}`, {
        method: 'DELETE',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }))
        throw new Error(errorData.detail || `HTTP ${response.status}`)
      }

      setWebsites((prev) => prev.filter((w) => w.id !== site.id))
      setConfirmDelete(null)
    } catch (error) {
      console.error('Error deleting website:', error)
      const errorMessage = error instanceof Error ? error.message : 'Unknown error'
      alert(`Ralat memadam website: ${errorMessage}`)
    } finally {
      setDeleting(null)
    }
  }

  async function handleLogout() {
    await signOut()
    router.push('/')
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-ink-050">
        <LoadingSpinner />
      </div>
    )
  }

  if (!user) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-ink-050">
        <div className="text-center">
          <h1 className="text-2xl font-semibold text-ink-900 mb-3 tracking-tight">Sila log masuk</h1>
          <Link href="/login">
            <Button variant="primary">Log masuk</Button>
          </Link>
        </div>
      </div>
    )
  }

  const publishedCount = websites.filter((w) => w.status === 'published').length
  const draftCount = websites.length - publishedCount

  return (
    <div className="min-h-screen bg-ink-050 font-geist text-ink-900">
      {/* Header */}
      <header className="bg-white/80 backdrop-blur-md border-b border-ink-200/80 sticky top-0 z-40">
        <nav className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2">
            <span className="inline-flex h-8 w-8 items-center justify-center rounded-lg bg-brand-500 text-white text-sm font-bold tracking-tight">
              B
            </span>
            <span className="text-base font-semibold tracking-tight">BinaApp</span>
          </Link>
          <div className="hidden md:flex items-center gap-1">
            <NavLink href="/my-projects" active>
              Projek
            </NavLink>
            <NavLink href="/create">Bina baharu</NavLink>
            <NavLink href="/dashboard/billing">Langganan</NavLink>
            <NavLink href="/profile">Profil</NavLink>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={handleLogout}
              className="text-sm text-ink-500 hover:text-ink-900 transition-colors"
            >
              Log keluar
            </button>
          </div>
        </nav>
      </header>

      <main className="max-w-6xl mx-auto px-6 py-10 md:py-14">
        {/* Page header */}
        <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-6 mb-10">
          <div>
            <h1 className="text-3xl md:text-4xl font-semibold tracking-tight text-ink-900">
              Projek saya
            </h1>
            <p className="text-ink-500 mt-2 text-sm">
              {websites.length === 0
                ? 'Tiada projek lagi — bina yang pertama anda di bawah.'
                : `${websites.length} projek · ${publishedCount} live · ${draftCount} draf`}
            </p>
          </div>
          {websites.length > 0 && (
            <Link href="/create">
              <Button
                variant="primary"
                size="md"
                leftIcon={
                  <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={2.2} viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
                  </svg>
                }
              >
                Bina projek baharu
              </Button>
            </Link>
          )}
        </div>

        {/* Stats row */}
        {websites.length > 0 && (
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-10">
            <StatCard label="Jumlah projek" value={websites.length} />
            <StatCard label="Live" value={publishedCount} accent="ok" />
            <StatCard label="Draf" value={draftCount} accent="warn" />
          </div>
        )}

        {/* Project list */}
        {websites.length === 0 ? (
          <EmptyState
            title="Mula bina projek pertama"
            description="Bina laman web profesional dalam minit, dengan AI. Pilih satu templat atau mula dari kosong."
            action={
              <Link href="/create">
                <Button variant="primary" size="lg">
                  Bina laman web
                </Button>
              </Link>
            }
          />
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {websites.map((website) => (
              <ProjectCard
                key={website.id}
                website={website}
                deleting={deleting === website.id}
                onDelete={() => setConfirmDelete(website)}
              />
            ))}
          </div>
        )}
      </main>

      {/* Delete confirmation */}
      <Modal
        open={!!confirmDelete}
        onClose={() => setConfirmDelete(null)}
        title="Padam projek?"
        description={
          confirmDelete
            ? `"${confirmDelete.business_name}" beserta semua kandungan, menu, dan data berkaitan akan dipadam secara kekal. Tindakan ini tidak boleh dibatalkan.`
            : ''
        }
        size="sm"
        footer={
          <>
            <Button variant="ghost" onClick={() => setConfirmDelete(null)}>
              Batal
            </Button>
            <Button
              variant="danger"
              loading={!!deleting}
              onClick={() => confirmDelete && deleteWebsite(confirmDelete)}
            >
              Padam projek
            </Button>
          </>
        }
      >
        <div className="text-sm text-ink-600">
          Untuk meneruskan, klik <span className="font-medium text-ink-900">Padam projek</span>. Anda
          tidak akan dapat memulihkan data ini.
        </div>
      </Modal>
    </div>
  )
}

/* ------------------------------------------------------------------ */

function NavLink({
  href,
  children,
  active,
}: {
  href: string
  children: React.ReactNode
  active?: boolean
}) {
  return (
    <Link
      href={href}
      className={
        'px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ' +
        (active
          ? 'text-ink-900 bg-ink-100'
          : 'text-ink-500 hover:text-ink-900 hover:bg-ink-050')
      }
    >
      {children}
    </Link>
  )
}

function StatCard({
  label,
  value,
  accent,
}: {
  label: string
  value: number | string
  accent?: 'ok' | 'warn'
}) {
  const accentClass =
    accent === 'ok'
      ? 'text-ok-500'
      : accent === 'warn'
        ? 'text-warn-500'
        : 'text-ink-900'
  return (
    <Card padding="md">
      <p className="text-xs uppercase tracking-wider text-ink-400 font-medium">{label}</p>
      <p className={`mt-2 text-3xl font-semibold tracking-tight ${accentClass}`}>{value}</p>
    </Card>
  )
}

function ProjectCard({
  website,
  deleting,
  onDelete,
}: {
  website: Website
  deleting: boolean
  onDelete: () => void
}) {
  const isLive = website.status === 'published'
  const liveUrl = website.full_url || (website.subdomain ? `https://${website.subdomain}.binaapp.my` : null)
  const initials = website.business_name
    .split(' ')
    .map((s) => s[0])
    .join('')
    .slice(0, 2)
    .toUpperCase()

  return (
    <Card padding="none" interactive className="overflow-hidden flex flex-col">
      {/* Preview */}
      <div className="relative h-36 bg-gradient-to-br from-ink-100 to-ink-050 border-b border-ink-200/80 flex items-center justify-center">
        <div className="absolute top-3 right-3">
          <Badge color={isLive ? 'green' : 'gray'}>
            <span className={`h-1.5 w-1.5 rounded-full ${isLive ? 'bg-ok-500' : 'bg-ink-400'}`} />
            {isLive ? 'Live' : 'Draf'}
          </Badge>
        </div>
        <span className="text-2xl font-semibold tracking-tight text-ink-400">{initials}</span>
      </div>

      {/* Body */}
      <div className="p-5 flex-1 flex flex-col">
        <h3 className="text-base font-semibold text-ink-900 tracking-tight truncate">
          {website.business_name}
        </h3>
        {website.subdomain ? (
          <a
            href={liveUrl || '#'}
            target="_blank"
            rel="noopener noreferrer"
            className="mt-1 text-xs text-brand-600 hover:text-brand-700 truncate block"
          >
            {website.subdomain}.binaapp.my
          </a>
        ) : (
          <p className="mt-1 text-xs text-ink-400">Belum diterbitkan</p>
        )}
        <p className="mt-2 text-xs text-ink-400">
          Dibuat {new Date(website.created_at).toLocaleDateString('ms-MY', {
            day: 'numeric',
            month: 'short',
            year: 'numeric',
          })}
        </p>

        <div className="mt-4 pt-4 border-t border-ink-100 flex items-center gap-2">
          <Link href={`/editor/${website.id}`} className="flex-1">
            <Button variant="secondary" size="sm" fullWidth>
              Edit
            </Button>
          </Link>
          {isLive && liveUrl && (
            <a href={liveUrl} target="_blank" rel="noopener noreferrer" className="flex-1">
              <Button variant="subtle" size="sm" fullWidth>
                Lihat live
              </Button>
            </a>
          )}
          <button
            onClick={(e) => {
              e.preventDefault()
              e.stopPropagation()
              onDelete()
            }}
            disabled={deleting}
            aria-label="Padam projek"
            className="h-8 w-8 inline-flex items-center justify-center rounded-lg text-ink-400 hover:text-err-500 hover:bg-err-500/10 transition-colors disabled:opacity-50"
          >
            <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={1.8} viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6M1 7h22M9 7V4a1 1 0 011-1h4a1 1 0 011 1v3"
              />
            </svg>
          </button>
        </div>
      </div>
    </Card>
  )
}
