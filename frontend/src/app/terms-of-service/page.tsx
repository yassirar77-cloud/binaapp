/**
 * Terms of Service Page
 */

import Link from 'next/link'
import { Sparkles, ArrowLeft } from 'lucide-react'

export const metadata = {
  title: 'Terms of Service - BinaApp',
  description: 'Terms of Service for BinaApp - AI Website Builder Malaysia',
}

export default function TermsOfServicePage() {
  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="border-b bg-white">
        <nav className="container mx-auto px-4 h-16 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2">
            <Sparkles className="w-6 h-6 text-primary-600" />
            <span className="text-xl font-bold">BinaApp</span>
          </Link>
          <Link href="/" className="flex items-center gap-2 text-gray-600 hover:text-gray-900">
            <ArrowLeft className="w-4 h-4" />
            <span>Back to Home</span>
          </Link>
        </nav>
      </header>

      {/* Content */}
      <main className="container mx-auto px-4 py-12 max-w-3xl">
        <h1 className="text-3xl font-bold mb-2">Terms of Service</h1>
        <p className="text-gray-500 mb-8">Last updated: January 2025</p>

        <div className="bg-white rounded-lg shadow-sm p-6 md:p-8 space-y-6">
          <section>
            <h2 className="text-xl font-semibold mb-3">1. Service Description</h2>
            <p className="text-gray-600">
              BinaApp provides an AI-powered website builder platform and restaurant delivery management
              system for Malaysian businesses. Our services include website creation, menu management,
              order processing, and delivery tracking.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold mb-3">2. User Responsibilities</h2>
            <ul className="list-disc list-inside text-gray-600 space-y-2">
              <li>Provide accurate and truthful information</li>
              <li>Keep your account credentials secure</li>
              <li>Use the platform for lawful purposes only</li>
              <li>Not upload harmful, offensive, or illegal content</li>
              <li>Comply with all applicable Malaysian laws</li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-semibold mb-3">3. Merchant Responsibilities</h2>
            <p className="text-gray-600 mb-2">If you use BinaApp as a merchant, you agree to:</p>
            <ul className="list-disc list-inside text-gray-600 space-y-2">
              <li>Maintain accurate menu information and pricing</li>
              <li>Fulfill orders in a timely manner</li>
              <li>Ensure food safety and quality standards</li>
              <li>Handle customer complaints professionally</li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-semibold mb-3">4. Subscription & Pricing</h2>
            <p className="text-gray-600 mb-2">Our current subscription plans:</p>
            <ul className="list-disc list-inside text-gray-600 space-y-2">
              <li><strong>Starter:</strong> RM5/month - 1 website</li>
              <li><strong>Basic:</strong> RM29/month - 5 websites with analytics</li>
              <li><strong>Pro:</strong> RM49/month - Unlimited websites with delivery features</li>
            </ul>
            <p className="text-gray-600 mt-2">
              Payments are processed securely via ToyyibPay. Subscriptions auto-renew unless cancelled.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold mb-3">5. Service Availability</h2>
            <p className="text-gray-600">
              BinaApp is provided &quot;as-is&quot;. While we strive for 99% uptime, we may experience
              occasional downtime for maintenance or unforeseen issues. We do not guarantee
              uninterrupted service.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold mb-3">6. Limitation of Liability</h2>
            <p className="text-gray-600">BinaApp is not responsible for:</p>
            <ul className="list-disc list-inside text-gray-600 space-y-2 mt-2">
              <li>Food quality or safety issues (merchant responsibility)</li>
              <li>Delivery delays beyond our reasonable control</li>
              <li>Accuracy of AI-generated content</li>
              <li>Third-party service disruptions (payment gateways, hosting)</li>
              <li>Indirect or consequential damages</li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-semibold mb-3">7. Account Termination</h2>
            <p className="text-gray-600">
              We reserve the right to suspend or terminate accounts that violate these terms,
              engage in fraudulent activity, or harm other users. You may cancel your account
              at any time through your profile settings.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold mb-3">8. Governing Law</h2>
            <p className="text-gray-600">
              These terms are governed by the laws of Malaysia. Any disputes shall be resolved
              in Malaysian courts.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold mb-3">9. Contact Us</h2>
            <p className="text-gray-600">
              Questions about these terms? Contact us at{' '}
              <a href="mailto:support@binaapp.my" className="text-primary-600 hover:underline">
                support@binaapp.my
              </a>
            </p>
          </section>
        </div>
      </main>

      {/* Footer */}
      <footer className="py-8 border-t bg-white mt-12">
        <div className="container mx-auto px-4 text-center text-sm text-gray-500">
          <div className="flex flex-wrap justify-center gap-4 mb-4">
            <Link href="/privacy-policy" className="hover:text-gray-700">Privacy Policy</Link>
            <span>|</span>
            <Link href="/terms-of-service" className="hover:text-gray-700">Terms of Service</Link>
            <span>|</span>
            <a href="mailto:support@binaapp.my" className="hover:text-gray-700">Contact</a>
          </div>
          <p>&copy; 2025 BinaApp. All rights reserved.</p>
        </div>
      </footer>
    </div>
  )
}
