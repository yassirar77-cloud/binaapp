/**
 * Privacy Policy Page
 */

import Link from 'next/link'
import { Sparkles, ArrowLeft } from 'lucide-react'

export const metadata = {
  title: 'Privacy Policy - BinaApp',
  description: 'Privacy Policy for BinaApp - AI Website Builder Malaysia',
}

export default function PrivacyPolicyPage() {
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
        <h1 className="text-3xl font-bold mb-2">Privacy Policy</h1>
        <p className="text-gray-500 mb-8">Last updated: January 2025</p>

        <div className="bg-white rounded-lg shadow-sm p-6 md:p-8 space-y-6">
          <section>
            <h2 className="text-xl font-semibold mb-3">Who We Are</h2>
            <p className="text-gray-600">
              BinaApp is a Malaysian company providing an AI-powered website builder and restaurant
              delivery platform. This policy explains how we collect, use, and protect your data.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold mb-3">Data We Collect</h2>
            <ul className="list-disc list-inside text-gray-600 space-y-2">
              <li><strong>Account Information:</strong> Email address, password (encrypted), full name</li>
              <li><strong>Contact Details:</strong> Phone number (optional, for business use)</li>
              <li><strong>Business Information:</strong> Restaurant details, menu items, pricing</li>
              <li><strong>Location Data:</strong> GPS coordinates (riders only, for delivery tracking)</li>
              <li><strong>Usage Data:</strong> How you interact with our platform</li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-semibold mb-3">How We Use Your Data</h2>
            <ul className="list-disc list-inside text-gray-600 space-y-2">
              <li>Provide our website builder and delivery platform services</li>
              <li>Process and fulfill customer orders</li>
              <li>Track deliveries in real-time (GPS for riders)</li>
              <li>Send service notifications and updates</li>
              <li>Improve our AI features and user experience</li>
              <li>Process subscription payments via ToyyibPay</li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-semibold mb-3">Data Protection</h2>
            <p className="text-gray-600">
              We take data security seriously:
            </p>
            <ul className="list-disc list-inside text-gray-600 space-y-2 mt-2">
              <li>All data is encrypted and stored securely on Supabase</li>
              <li>Passwords are hashed using industry-standard encryption</li>
              <li>Payment processing is handled by ToyyibPay (we never store card details)</li>
              <li>We use HTTPS for all data transmission</li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-semibold mb-3">Data Retention</h2>
            <ul className="list-disc list-inside text-gray-600 space-y-2">
              <li><strong>GPS/Location Data:</strong> Deleted after 30 days</li>
              <li><strong>Account Data:</strong> Kept until you request deletion</li>
              <li><strong>Transaction Records:</strong> Retained for 7 years (legal requirement)</li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-semibold mb-3">Your Rights (PDPA Malaysia)</h2>
            <p className="text-gray-600 mb-2">
              Under the Personal Data Protection Act 2010, you have the right to:
            </p>
            <ul className="list-disc list-inside text-gray-600 space-y-2">
              <li>Access your personal data</li>
              <li>Request correction of inaccurate data</li>
              <li>Request deletion of your data</li>
              <li>Withdraw consent for data processing</li>
            </ul>
            <p className="text-gray-600 mt-2">
              To exercise these rights, contact us at{' '}
              <a href="mailto:support@binaapp.my" className="text-primary-600 hover:underline">
                support@binaapp.my
              </a>
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold mb-3">AI Features Disclosure</h2>
            <p className="text-gray-600">
              BinaApp uses artificial intelligence to generate website content, images, and suggestions.
              AI-generated content may not always be accurate. You are responsible for reviewing and
              editing content before publishing.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold mb-3">Contact Us</h2>
            <p className="text-gray-600">
              For privacy-related questions or requests:
            </p>
            <p className="text-gray-600 mt-2">
              <strong>Email:</strong>{' '}
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
