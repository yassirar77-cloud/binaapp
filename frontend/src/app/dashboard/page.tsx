/**
 * Dashboard Page - Project Management
 */

'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import { Sparkles, Plus, Eye, Edit2, Trash2, ExternalLink, Calendar, Globe } from 'lucide-react'
import { API_BASE_URL } from '@/lib/env'

interface Project {
  id: string
  name: string
  subdomain: string
  url: string
  created_at: string
  published_at?: string
}

export default function DashboardPage() {
  const [projects, setProjects] = useState<Project[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null)
  const [deleting, setDeleting] = useState<string | null>(null)

  const userId = 'demo-user' // In production, get from auth

  useEffect(() => {
    loadProjects()
  }, [])

  const loadProjects = async () => {
    setLoading(true)
    setError('')

    try {
      const response = await fetch(`${API_BASE_URL}/api/projects/${userId}`)

      if (!response.ok) {
        throw new Error('Failed to load projects')
      }

      const data = await response.json()
      setProjects(data)
    } catch (err: any) {
      setError(err.message || 'Failed to load projects')
    } finally {
      setLoading(false)
    }
  }

  const handleDelete = async (projectId: string) => {
    setDeleting(projectId)
    setError('')

    try {
      const response = await fetch(
        `${API_BASE_URL}/api/projects/${userId}/${projectId}`,
        { method: 'DELETE' }
      )

      if (!response.ok) {
        throw new Error('Failed to delete project')
      }

      // Remove from list
      setProjects(projects.filter(p => p.id !== projectId))
      setDeleteConfirm(null)
    } catch (err: any) {
      setError(err.message || 'Failed to delete project')
    } finally {
      setDeleting(null)
    }
  }

  const formatDate = (dateString: string) => {
    try {
      const date = new Date(dateString)
      return date.toLocaleDateString('en-MY', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
      })
    } catch {
      return 'Unknown'
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b sticky top-0 z-40">
        <nav className="container mx-auto px-4 h-16 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2">
            <Sparkles className="w-6 h-6 text-primary-600" />
            <span className="text-xl font-bold">BinaApp</span>
          </Link>
          <div className="flex items-center gap-4">
            <Link href="/create" className="btn btn-primary">
              <Plus className="w-4 h-4 mr-2" />
              Create New Website
            </Link>
          </div>
        </nav>
      </header>

      <div className="container mx-auto px-4 py-8">
        {/* Title & Stats */}
        <div className="mb-8">
          <h1 className="text-4xl font-bold mb-2">My Projects</h1>
          <p className="text-gray-600">Manage and view all your websites</p>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-6">
            <div className="bg-white rounded-lg p-6 shadow-sm border border-gray-200">
              <div className="text-3xl font-bold text-primary-600 mb-1">
                {projects.length}
              </div>
              <div className="text-gray-600 text-sm">Total Websites</div>
            </div>
            <div className="bg-white rounded-lg p-6 shadow-sm border border-gray-200">
              <div className="text-3xl font-bold text-green-600 mb-1">
                {projects.filter(p => p.published_at).length}
              </div>
              <div className="text-gray-600 text-sm">Published</div>
            </div>
            <div className="bg-white rounded-lg p-6 shadow-sm border border-gray-200">
              <div className="text-3xl font-bold text-blue-600 mb-1">-</div>
              <div className="text-gray-600 text-sm">Total Views (Coming Soon)</div>
            </div>
          </div>
        </div>

        {/* Error Message */}
        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700">
            {error}
          </div>
        )}

        {/* Loading State */}
        {loading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {[1, 2, 3].map(i => (
              <div key={i} className="bg-white rounded-lg p-6 shadow-sm border border-gray-200 animate-pulse">
                <div className="h-32 bg-gray-200 rounded mb-4"></div>
                <div className="h-6 bg-gray-200 rounded mb-2"></div>
                <div className="h-4 bg-gray-200 rounded w-2/3"></div>
              </div>
            ))}
          </div>
        ) : projects.length === 0 ? (
          /* Empty State */
          <div className="text-center py-20">
            <div className="text-6xl mb-4">📄</div>
            <h2 className="text-2xl font-bold mb-2">No websites yet</h2>
            <p className="text-gray-600 mb-6">Create your first AI-powered website now!</p>
            <Link href="/create" className="btn btn-primary">
              <Plus className="w-4 h-4 mr-2" />
              Create Your First Website
            </Link>
          </div>
        ) : (
          /* Projects Grid */
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {projects.map(project => (
              <div
                key={project.id}
                className="bg-white rounded-lg shadow-sm border border-gray-200 hover:shadow-lg transition-shadow overflow-hidden"
              >
                {/* Preview Thumbnail */}
                <div className="relative h-48 bg-gradient-to-br from-primary-100 to-primary-200 flex items-center justify-center">
                  <Globe className="w-16 h-16 text-primary-600 opacity-50" />
                  <div className="absolute top-3 right-3">
                    <a
                      href={project.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="bg-white rounded-full p-2 shadow-md hover:shadow-lg transition-shadow"
                      title="View Live"
                    >
                      <ExternalLink className="w-4 h-4 text-gray-700" />
                    </a>
                  </div>
                </div>

                {/* Content */}
                <div className="p-6">
                  <h3 className="text-xl font-bold mb-2 truncate" title={project.name}>
                    {project.name}
                  </h3>

                  <div className="flex items-center gap-2 text-sm text-gray-600 mb-1">
                    <Globe className="w-4 h-4" />
                    <span className="truncate">{project.subdomain}.binaapp.my</span>
                  </div>

                  <div className="flex items-center gap-2 text-sm text-gray-500 mb-4">
                    <Calendar className="w-4 h-4" />
                    <span>Created {formatDate(project.created_at)}</span>
                  </div>

                  {/* Actions */}
                  <div className="flex gap-2">
                    <a
                      href={project.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex-1 btn btn-outline btn-sm"
                    >
                      <Eye className="w-4 h-4 mr-1" />
                      View
                    </a>
                    <Link
                      href={`/edit/${project.id}`}
                      className="flex-1 btn btn-outline btn-sm"
                    >
                      <Edit2 className="w-4 h-4 mr-1" />
                      Edit
                    </Link>
                    {deleteConfirm === project.id ? (
                      <button
                        onClick={() => handleDelete(project.id)}
                        disabled={deleting === project.id}
                        className="flex-1 btn bg-red-600 hover:bg-red-700 text-white btn-sm"
                      >
                        {deleting === project.id ? '...' : 'Confirm?'}
                      </button>
                    ) : (
                      <button
                        onClick={() => setDeleteConfirm(project.id)}
                        className="btn btn-outline btn-sm text-red-600 hover:bg-red-50"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    )}
                  </div>

                  {deleteConfirm === project.id && (
                    <button
                      onClick={() => setDeleteConfirm(null)}
                      className="w-full mt-2 text-xs text-gray-500 hover:text-gray-700"
                    >
                      Cancel
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Create New Button (Mobile FAB) */}
        <Link
          href="/create"
          className="fixed bottom-6 right-6 md:hidden btn btn-primary rounded-full w-14 h-14 flex items-center justify-center shadow-lg"
        >
          <Plus className="w-6 h-6" />
        </Link>
      </div>
    </div>
  )
}
