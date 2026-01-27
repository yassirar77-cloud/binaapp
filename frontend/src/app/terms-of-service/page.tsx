'use client'

export default function TermsOfService() {
  return (
    <div className="min-h-screen bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-4xl mx-auto bg-white rounded-lg shadow-md p-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Terms of Service</h1>
        <p className="text-sm text-gray-600 mb-8">Last updated: January 2025</p>

        <div className="space-y-6 text-gray-700">
          <section>
            <h2 className="text-xl font-semibold text-gray-900 mb-3">Service Description</h2>
            <p>BinaApp is a restaurant delivery platform that provides website building, order management, GPS tracking, and payment integration services for restaurants in Malaysia.</p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-gray-900 mb-3">Subscription Plans</h2>
            <ul className="list-disc pl-6 space-y-2">
              <li><strong>Starter:</strong> RM5 per month</li>
              <li><strong>Basic:</strong> RM29 per month</li>
              <li><strong>Pro:</strong> RM49 per month</li>
            </ul>
            <p className="mt-3">Payments are processed securely through ToyyibPay.</p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-gray-900 mb-3">User Responsibilities</h2>
            <ul className="list-disc pl-6 space-y-2">
              <li>Provide accurate information when creating an account</li>
              <li>Use the platform only for lawful purposes</li>
              <li>Keep your account credentials secure</li>
              <li>Comply with all applicable Malaysian laws</li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-gray-900 mb-3">Merchant Responsibilities</h2>
            <ul className="list-disc pl-6 space-y-2">
              <li>Ensure menu items and prices are accurate</li>
              <li>Fulfill orders in a timely manner</li>
              <li>Maintain food quality and safety standards</li>
              <li>Respond promptly to customer inquiries</li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-gray-900 mb-3">Service Availability</h2>
            <p>BinaApp is provided &quot;as-is&quot; without warranties. We strive for 99.9% uptime but may experience occasional downtime for maintenance or unforeseen technical issues.</p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-gray-900 mb-3">Liability Limits</h2>
            <p className="mb-2">BinaApp is not responsible for:</p>
            <ul className="list-disc pl-6 space-y-2">
              <li>Food quality or safety (merchant responsibility)</li>
              <li>Delivery delays beyond our control</li>
              <li>Third-party service interruptions</li>
              <li>Loss of business or profits</li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-gray-900 mb-3">Account Termination</h2>
            <p>We reserve the right to suspend or terminate accounts that violate these terms, engage in fraudulent activity, or misuse the platform.</p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-gray-900 mb-3">Governing Law</h2>
            <p>These terms are governed by the laws of Malaysia. Any disputes will be resolved in Malaysian courts.</p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-gray-900 mb-3">Contact</h2>
            <p>For questions about these terms: <a href="mailto:support@binaapp.my" className="text-blue-600 hover:underline">support@binaapp.my</a></p>
          </section>
        </div>
      </div>
    </div>
  )
}
