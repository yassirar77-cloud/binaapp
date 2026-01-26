/**
 * Landing Page
 */

'use client'

import { useState, useEffect, Suspense } from 'react'
import Link from 'next/link'
import { useRouter, useSearchParams } from 'next/navigation'
import { Sparkles, Zap, Globe, Smartphone } from 'lucide-react'
import { signOut, getCurrentUser, getStoredToken } from '@/lib/supabase'
import { UpgradeModal } from '@/components/UpgradeModal'

function LandingPageContent() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const [user, setUser] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [showUpgradeModal, setShowUpgradeModal] = useState(false)
  const [targetTier, setTargetTier] = useState<'starter' | 'basic' | 'pro'>('basic')

  useEffect(() => {
    checkUser()
  }, [])

  // Handle tier parameter from redirect after login
  useEffect(() => {
    if (!loading && user) {
      const tier = searchParams.get('tier') as 'starter' | 'basic' | 'pro' | null
      if (tier && ['starter', 'basic', 'pro'].includes(tier)) {
        // Clear the URL parameter
        router.replace('/', { scroll: false })
        // Open the upgrade modal or redirect
        handleSelectPlan(tier)
      }
    }
  }, [loading, user, searchParams])

  async function checkUser() {
    try {
      // Check for stored auth token first (custom backend auth)
      const token = getStoredToken()
      if (token) {
        const currentUser = await getCurrentUser()
        setUser(currentUser)
      } else {
        setUser(null)
      }
    } catch (error) {
      console.error('Error checking user:', error)
      setUser(null)
    } finally {
      setLoading(false)
    }
  }

  async function handleLogout() {
    try {
      await signOut()
      setUser(null)
      router.refresh()
    } catch (error) {
      console.error('Error logging out:', error)
    }
  }

  function handleSelectPlan(tier: 'starter' | 'basic' | 'pro') {
    if (!user) {
      // Not logged in - redirect to login with return URL
      router.push(`/login?redirect=/?tier=${tier}`)
      return
    }

    // User is logged in
    if (tier === 'starter') {
      // If selecting Starter, just redirect to create website
      router.push('/create')
    } else {
      // Show upgrade modal for Basic or Pro
      setTargetTier(tier)
      setShowUpgradeModal(true)
    }
  }

  return (
    <div className="min-h-screen">
      {/* Header */}
      <header className="border-b bg-white/80 backdrop-blur-sm fixed w-full z-50">
        <nav className="container mx-auto px-4 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Sparkles className="w-6 h-6 text-primary-600" />
            <span className="text-xl font-bold">BinaApp</span>
          </div>
          <div className="flex items-center gap-4">
            {!loading && (
              user ? (
                <>
                  <Link href="/profile" className="text-gray-600 hover:text-gray-900">
                    Profil
                  </Link>
                  <Link href="/my-projects" className="text-gray-600 hover:text-gray-900">
                    Website Saya
                  </Link>
                  <button
                    onClick={handleLogout}
                    className="text-red-500 hover:text-red-600"
                  >
                    Log Keluar
                  </button>
                </>
              ) : (
                <>
                  <Link href="/login" className="text-gray-600 hover:text-gray-900">
                    Log Masuk
                  </Link>
                  <Link href="/register" className="btn btn-primary">
                    Daftar
                  </Link>
                </>
              )
            )}
          </div>
        </nav>
      </header>

      {/* Hero Section */}
      <section className="pt-32 pb-20 bg-gradient-to-b from-primary-50 to-white">
        <div className="container mx-auto px-4 text-center">
          <h1 className="text-5xl md:text-6xl font-bold text-gray-900 mb-6 animate-fade-in">
            Cipta Website Perniagaan<br />
            <span className="text-primary-600">Dalam Masa Minit</span>
          </h1>
          <p className="text-xl text-gray-600 mb-8 max-w-2xl mx-auto animate-slide-up">
            Hanya beritahu kami tentang perniagaan anda dalam Bahasa Malaysia atau English.
            AI kami akan jana website lengkap dengan WhatsApp, shopping cart, dan banyak lagi!
          </p>
          <div className="flex gap-4 justify-center animate-slide-up">
            <Link href="/create" className="btn btn-primary text-lg px-8 py-3">
              Mula Sekarang
            </Link>
            <Link href="/dashboard" className="btn btn-outline text-lg px-8 py-3">
              Lihat Projects
            </Link>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="py-20">
        <div className="container mx-auto px-4">
          <h2 className="text-3xl font-bold text-center mb-12">
            Kenapa Pilih BinaApp?
          </h2>
          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-8">
            <FeatureCard
              icon={<Sparkles className="w-8 h-8 text-primary-600" />}
              title="AI Powered"
              description="Hanya terangkan perniagaan anda, AI akan buat website"
            />
            <FeatureCard
              icon={<Zap className="w-8 h-8 text-primary-600" />}
              title="Siap Dalam Minit"
              description="Dari idea ke website live dalam masa kurang 5 minit"
            />
            <FeatureCard
              icon={<Globe className="w-8 h-8 text-primary-600" />}
              title="Domain Percuma"
              description="Dapat subdomain .binaapp.my secara percuma"
            />
            <FeatureCard
              icon={<Smartphone className="w-8 h-8 text-primary-600" />}
              title="Mobile Friendly"
              description="Responsive untuk semua peranti mobile dan desktop"
            />
          </div>
        </div>
      </section>

      {/* Auto Integrations */}
      <section className="py-20 bg-gray-50">
        <div className="container mx-auto px-4">
          <h2 className="text-3xl font-bold text-center mb-4">
            Semua Integrasi Sudah Termasuk
          </h2>
          <p className="text-center text-gray-600 mb-12 max-w-2xl mx-auto">
            Setiap website datang dengan features yang perniagaan anda perlukan
          </p>
          <div className="grid md:grid-cols-3 gap-6">
            <IntegrationCard
              emoji="📱"
              title="WhatsApp Ordering"
              description="Button WhatsApp + checkout flow automatik"
            />
            <IntegrationCard
              emoji="🛒"
              title="Shopping Cart"
              description="Sistem cart lengkap untuk e-commerce"
            />
            <IntegrationCard
              emoji="🗺️"
              title="Google Maps"
              description="Map lokasi perniagaan anda"
            />
            <IntegrationCard
              emoji="📧"
              title="Contact Form"
              description="Borang hubungi dengan email notification"
            />
            <IntegrationCard
              emoji="📱"
              title="QR Code"
              description="QR code untuk share website"
            />
            <IntegrationCard
              emoji="🔗"
              title="Social Sharing"
              description="Share ke Facebook, WhatsApp, Twitter"
            />
          </div>
        </div>
      </section>

      {/* Pricing */}
      <section className="py-20">
        <div className="container mx-auto px-4">
          <h2 className="text-3xl font-bold text-center mb-12">
            Harga Berpatutan Untuk Semua
          </h2>
          <div className="grid md:grid-cols-3 gap-8 max-w-5xl mx-auto">
            <PricingCard
              name="Starter"
              price="RM 5"
              period="/bulan"
              tier="starter"
              features={[
                '1 website',
                'Subdomain percuma',
                'AI generation',
                'Semua integrasi',
                'Support email'
              ]}
              cta="Mula Sekarang"
              onSelect={() => handleSelectPlan('starter')}
            />
            <PricingCard
              name="Basic"
              price="RM 29"
              period="/bulan"
              tier="basic"
              features={[
                '5 websites',
                'Custom subdomain',
                'Priority AI',
                'Analytics',
                'Priority support'
              ]}
              cta="Pilih Basic"
              onSelect={() => handleSelectPlan('basic')}
              highlighted
            />
            <PricingCard
              name="Pro"
              price="RM 49"
              period="/bulan"
              tier="pro"
              features={[
                'Unlimited websites',
                'Unlimited AI',
                'Unlimited zones',
                'Rider GPS (10)',
                'Priority support'
              ]}
              cta="Pilih Pro"
              onSelect={() => handleSelectPlan('pro')}
            />
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20 bg-primary-600 text-white">
        <div className="container mx-auto px-4 text-center">
          <h2 className="text-4xl font-bold mb-6">
            Sedia Untuk Mulakan?
          </h2>
          <p className="text-xl mb-8 text-primary-100">
            Cipta website pertama anda sekarang. Bermula dari RM5/bulan sahaja.
          </p>
          <Link href="/register" className="btn bg-white text-primary-600 hover:bg-gray-100 text-lg px-8 py-3">
            Daftar Sekarang
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-12 bg-gray-900 text-gray-400">
        <div className="container mx-auto px-4 text-center">
          <div className="flex items-center justify-center gap-2 mb-4">
            <Sparkles className="w-5 h-5" />
            <span className="text-lg font-bold text-white">BinaApp</span>
          </div>
          <p className="mb-4">AI-Powered Website Builder untuk SME Malaysia</p>
          <p className="text-sm">&copy; 2024 BinaApp. Semua hak cipta terpelihara.</p>
        </div>
      </footer>

      {/* Upgrade Modal */}
      {user && (
        <UpgradeModal
          show={showUpgradeModal}
          onClose={() => setShowUpgradeModal(false)}
          currentTier="starter"
          targetTier={targetTier}
        />
      )}
    </div>
  )
}

function FeatureCard({ icon, title, description }: { icon: React.ReactNode; title: string; description: string }) {
  return (
    <div className="card text-center hover:shadow-lg transition-shadow">
      <div className="flex justify-center mb-4">{icon}</div>
      <h3 className="text-xl font-bold mb-2">{title}</h3>
      <p className="text-gray-600">{description}</p>
    </div>
  )
}

function IntegrationCard({ emoji, title, description }: { emoji: string; title: string; description: string }) {
  return (
    <div className="card text-center hover:shadow-lg transition-shadow">
      <div className="text-4xl mb-3">{emoji}</div>
      <h3 className="font-bold mb-2">{title}</h3>
      <p className="text-sm text-gray-600">{description}</p>
    </div>
  )
}

function PricingCard({
  name,
  price,
  period,
  tier,
  features,
  cta,
  onSelect,
  highlighted
}: {
  name: string
  price: string
  period: string
  tier: 'starter' | 'basic' | 'pro'
  features: string[]
  cta: string
  onSelect: () => void
  highlighted?: boolean
}) {
  return (
    <div className={`card ${highlighted ? 'ring-2 ring-primary-600 shadow-xl' : ''}`}>
      {highlighted && (
        <div className="text-xs font-bold text-primary-600 text-center mb-2">PALING POPULAR</div>
      )}
      <h3 className="text-2xl font-bold text-center mb-2">{name}</h3>
      <div className="text-center mb-6">
        <span className="text-4xl font-bold">{price}</span>
        <span className="text-gray-600">{period}</span>
      </div>
      <ul className="space-y-3 mb-6">
        {features.map((feature, i) => (
          <li key={i} className="flex items-center gap-2">
            <span className="text-green-500">✓</span>
            <span className="text-sm">{feature}</span>
          </li>
        ))}
      </ul>
      <button onClick={onSelect} className={`btn w-full ${highlighted ? 'btn-primary' : 'btn-outline'}`}>
        {cta}
      </button>
    </div>
  )
}

export default function LandingPage() {
  return (
    <Suspense fallback={<div className="min-h-screen flex items-center justify-center">Loading...</div>}>
      <LandingPageContent />
    </Suspense>
  )
}
