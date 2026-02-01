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
  const [targetTier, setTargetTier] = useState<'starter' | 'basic' | 'pro'>('starter')

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

    // User is logged in - show upgrade/subscribe modal for ALL plans
    // Users must pay before they can create websites
    setTargetTier(tier)
    setShowUpgradeModal(true)
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
            <button
              onClick={() => handleSelectPlan('starter')}
              className="btn btn-primary text-lg px-8 py-3"
            >
              Mula Sekarang - RM5/bulan
            </button>
            {user && (
              <Link href="/my-projects" className="btn btn-outline text-lg px-8 py-3">
                Website Saya
              </Link>
            )}
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

      {/* Subscription Packages & Limits (Detailed) */}
      <section className="py-20 bg-gray-50">
        <div className="container mx-auto px-4">
          <h2 className="text-3xl font-bold text-center mb-4">
            Subscription Packages & Limits
          </h2>
          <p className="text-center text-gray-600 mb-12 max-w-3xl mx-auto">
            Bandingkan had penggunaan mengikut pelan. Had AI adalah bulanan (reset setiap bulan).
          </p>

          <div className="overflow-x-auto bg-white rounded-2xl shadow-sm border">
            <table className="min-w-[900px] w-full text-sm">
              <thead className="bg-gray-100">
                <tr>
                  <th className="text-left p-4 font-bold">Resource</th>
                  <th className="text-left p-4 font-bold">Starter (RM 5/mo)</th>
                  <th className="text-left p-4 font-bold">Basic (RM 29/mo)</th>
                  <th className="text-left p-4 font-bold">Pro (RM 49/mo)</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                <tr>
                  <td className="p-4 font-medium">Websites</td>
                  <td className="p-4">1</td>
                  <td className="p-4">5</td>
                  <td className="p-4">Unlimited</td>
                </tr>
                <tr>
                  <td className="p-4 font-medium">Menu Items</td>
                  <td className="p-4">20</td>
                  <td className="p-4">Unlimited</td>
                  <td className="p-4">Unlimited</td>
                </tr>
                <tr>
                  <td className="p-4 font-medium">AI Hero Generations</td>
                  <td className="p-4">1 / month</td>
                  <td className="p-4">10 / month</td>
                  <td className="p-4">Unlimited</td>
                </tr>
                <tr>
                  <td className="p-4 font-medium">AI Images</td>
                  <td className="p-4">5 / month</td>
                  <td className="p-4">30 / month</td>
                  <td className="p-4">Unlimited</td>
                </tr>
                <tr>
                  <td className="p-4 font-medium">Delivery Zones</td>
                  <td className="p-4">1</td>
                  <td className="p-4">5</td>
                  <td className="p-4">Unlimited</td>
                </tr>
                <tr>
                  <td className="p-4 font-medium">Riders (GPS)</td>
                  <td className="p-4">0</td>
                  <td className="p-4">0</td>
                  <td className="p-4">10</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </section>

      {/* Features By Plan */}
      <section className="py-20">
        <div className="container mx-auto px-4">
          <h2 className="text-3xl font-bold text-center mb-4">
            ⭐ Features by Plan
          </h2>
          <p className="text-center text-gray-600 mb-12 max-w-3xl mx-auto">
            Akses ciri bergantung pada pelan langganan anda.
          </p>

          <div className="overflow-x-auto bg-white rounded-2xl shadow-sm border">
            <table className="min-w-[900px] w-full text-sm">
              <thead className="bg-gray-100">
                <tr>
                  <th className="text-left p-4 font-bold">Feature</th>
                  <th className="text-left p-4 font-bold">Starter</th>
                  <th className="text-left p-4 font-bold">Basic</th>
                  <th className="text-left p-4 font-bold">Pro</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                <tr>
                  <td className="p-4 font-medium">Subdomain</td>
                  <td className="p-4">✅</td>
                  <td className="p-4">✅ Custom</td>
                  <td className="p-4">✅</td>
                </tr>
                <tr>
                  <td className="p-4 font-medium">All Integrations</td>
                  <td className="p-4">✅</td>
                  <td className="p-4">✅</td>
                  <td className="p-4">✅</td>
                </tr>
                <tr>
                  <td className="p-4 font-medium">Email Support</td>
                  <td className="p-4">✅</td>
                  <td className="p-4">✅</td>
                  <td className="p-4">✅</td>
                </tr>
                <tr>
                  <td className="p-4 font-medium">Priority Support</td>
                  <td className="p-4">❌</td>
                  <td className="p-4">✅</td>
                  <td className="p-4">✅</td>
                </tr>
                <tr>
                  <td className="p-4 font-medium">Priority AI</td>
                  <td className="p-4">❌</td>
                  <td className="p-4">✅</td>
                  <td className="p-4">✅</td>
                </tr>
                <tr>
                  <td className="p-4 font-medium">Advanced AI</td>
                  <td className="p-4">❌</td>
                  <td className="p-4">❌</td>
                  <td className="p-4">✅</td>
                </tr>
                <tr>
                  <td className="p-4 font-medium">Analytics</td>
                  <td className="p-4">❌</td>
                  <td className="p-4">✅</td>
                  <td className="p-4">✅</td>
                </tr>
                <tr>
                  <td className="p-4 font-medium">QR Payment</td>
                  <td className="p-4">❌</td>
                  <td className="p-4">✅</td>
                  <td className="p-4">✅</td>
                </tr>
                <tr>
                  <td className="p-4 font-medium">Contact Form</td>
                  <td className="p-4">❌</td>
                  <td className="p-4">✅</td>
                  <td className="p-4">✅</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </section>

      {/* Addon Pricing */}
      <section className="py-20 bg-gray-50">
        <div className="container mx-auto px-4">
          <h2 className="text-3xl font-bold text-center mb-4">
            🛒 Addon Pricing (Buy Extra Credits)
          </h2>
          <p className="text-center text-gray-600 mb-12 max-w-3xl mx-auto">
            Bila capai had, anda boleh beli kredit addon (auto-deduct bila digunakan).
          </p>

          <div className="grid md:grid-cols-2 lg:grid-cols-5 gap-4 max-w-6xl mx-auto">
            {[
              { name: 'AI Image', price: 'RM 1.00' },
              { name: 'AI Hero', price: 'RM 2.00' },
              { name: 'Website', price: 'RM 5.00' },
              { name: 'Rider', price: 'RM 3.00' },
              { name: 'Delivery Zone', price: 'RM 2.00' },
            ].map((a) => (
              <div key={a.name} className="card text-center">
                <div className="text-sm text-gray-500 mb-2">{a.name}</div>
                <div className="text-2xl font-bold text-gray-900">{a.price}</div>
                <div className="text-xs text-gray-500 mt-2">per credit</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Subscription Monitoring Features */}
      <section className="py-20">
        <div className="container mx-auto px-4">
          <h2 className="text-3xl font-bold text-center mb-4">
            📊 Subscription Monitoring Features
          </h2>
          <p className="text-center text-gray-600 mb-10 max-w-3xl mx-auto">
            Sistem memantau penggunaan, enforce had secara real-time, dan simpan rekod transaksi.
          </p>

          <div className="grid md:grid-cols-2 gap-6 max-w-5xl mx-auto">
            <div className="card">
              <h3 className="font-bold mb-2">1) Usage Tracking</h3>
              <p className="text-sm text-gray-600">
                Monthly usage counters (reset each month): websites, menu items, AI hero, AI images, zones, riders.
              </p>
            </div>
            <div className="card">
              <h3 className="font-bold mb-2">2) Limit Enforcement</h3>
              <p className="text-sm text-gray-600">
                Real-time limit checking before actions, auto-block when exceeded, suggests addon purchase, auto-deduct addon credits.
              </p>
            </div>
            <div className="card">
              <h3 className="font-bold mb-2">3) Expiry Reminders</h3>
              <p className="text-sm text-gray-600">
                Email notifications at 7/3/1 day before expiry + on-expiry, with auto-suspension of expired subscriptions.
              </p>
            </div>
            <div className="card">
              <h3 className="font-bold mb-2">4) API Endpoints</h3>
              <p className="text-sm text-gray-600">
                Status, usage, check-limit, plans, transactions, and addon credits endpoints for full visibility.
              </p>
            </div>
            <div className="card">
              <h3 className="font-bold mb-2">5) Transaction Tracking</h3>
              <p className="text-sm text-gray-600">
                Complete audit trail with invoice numbers (INV-YYYYMMDD-XXXX) and ToyyibPay integration.
              </p>
            </div>
            <div className="card">
              <h3 className="font-bold mb-2">6) Feature Access Control</h3>
              <p className="text-sm text-gray-600">
                Middleware guards for feature-based access and per-plan feature restrictions.
              </p>
            </div>
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
          <div className="flex flex-wrap justify-center gap-4 mb-4 text-sm">
            <Link href="/privacy-policy" className="hover:text-white transition-colors">
              Privacy Policy
            </Link>
            <span>|</span>
            <Link href="/terms-of-service" className="hover:text-white transition-colors">
              Terms of Service
            </Link>
            <span>|</span>
            <a href="mailto:support.team@binaapp.my" className="hover:text-white transition-colors">
              Contact
            </a>
          </div>
          <p className="text-sm">&copy; 2025 BinaApp. All rights reserved.</p>
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
