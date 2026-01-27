'use client'

export default function PrivacyPolicy() {
  return (
    <div className="min-h-screen bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-4xl mx-auto bg-white rounded-lg shadow-md p-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Privacy Policy</h1>
        <p className="text-sm text-gray-600 mb-8">Last updated: January 2025</p>

        <div className="space-y-6 text-gray-700">
          <section>
            <h2 className="text-xl font-semibold text-gray-900 mb-3">What We Collect</h2>
            <ul className="list-disc pl-6 space-y-2">
              <li>Email and password for your account</li>
              <li>Phone number for order notifications</li>
              <li>Restaurant information if you're a merchant</li>
              <li>GPS location only for delivery riders during active deliveries</li>
              <li>Payment information processed securely by ToyyibPay</li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-gray-900 mb-3">How We Use It</h2>
            <ul className="list-disc pl-6 space-y-2">
              <li>To provide our restaurant delivery platform services</li>
              <li>To process orders and payments</li>
              <li>To track deliveries in real-time</li>
              <li>To send you important updates about your orders</li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-gray-900 mb-3">How We Protect It</h2>
            <ul className="list-disc pl-6 space-y-2">
              <li>Data is encrypted and stored securely on Supabase</li>
              <li>We never share your personal information without consent</li>
              <li>GPS data is deleted after 30 days</li>
              <li>Payment details are handled by ToyyibPay - we don't store card numbers</li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-gray-900 mb-3">Your Rights</h2>
            <p className="mb-3">Under Malaysia's Personal Data Protection Act (PDPA), you can:</p>
            <ul className="list-disc pl-6 space-y-2">
              <li>Request to see your data</li>
              <li>Request correction of your data</li>
              <li>Request deletion of your account</li>
              <li>Contact us at: support@binaapp.my</li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-gray-900 mb-3">AI Features</h2>
            <p>Some features use AI (artificial intelligence) to generate content. AI-generated content may not be accurate and is not copyrighted.</p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-gray-900 mb-3">Contact</h2>
            <p>For privacy questions: <a href="mailto:support@binaapp.my" className="text-blue-600 hover:underline">support@binaapp.my</a></p>
            <p className="mt-2">BinaApp is committed to protecting your privacy and complying with Malaysian law.</p>
          </section>
        </div>
      </div>
    </div>
  )
}
