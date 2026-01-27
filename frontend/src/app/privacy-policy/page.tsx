'use client';

export default function PrivacyPolicyPage() {
  return (
    <div className="min-h-screen bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-3xl mx-auto">
        <div className="bg-white shadow-lg rounded-lg p-8 sm:p-12">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">Privacy Policy</h1>
          <p className="text-sm text-gray-500 mb-8">Last updated: January 2025</p>

          <div className="space-y-8 text-gray-700">
            <section>
              <h2 className="text-xl font-semibold text-gray-900 mb-3">What We Collect</h2>
              <p className="mb-3">
                BinaApp collects the following information to provide our restaurant delivery services:
              </p>
              <ul className="list-disc list-inside space-y-2 ml-4">
                <li><strong>Account Information:</strong> Email address, password, and phone number</li>
                <li><strong>Location Data:</strong> GPS coordinates for delivery tracking and restaurant discovery</li>
                <li><strong>Restaurant Information:</strong> Menu items, pricing, operating hours, and business details</li>
                <li><strong>Payment Information:</strong> Transaction data processed through ToyyibPay</li>
              </ul>
            </section>

            <section>
              <h2 className="text-xl font-semibold text-gray-900 mb-3">How We Use It</h2>
              <p className="mb-3">Your information is used to:</p>
              <ul className="list-disc list-inside space-y-2 ml-4">
                <li>Facilitate delivery services between restaurants and customers</li>
                <li>Process and track orders in real-time</li>
                <li>Improve our platform and user experience</li>
                <li>Communicate important updates about your orders and account</li>
              </ul>
            </section>

            <section>
              <h2 className="text-xl font-semibold text-gray-900 mb-3">How We Protect It</h2>
              <p className="mb-3">We take data security seriously:</p>
              <ul className="list-disc list-inside space-y-2 ml-4">
                <li><strong>Database Security:</strong> All data is encrypted using Supabase's enterprise-grade security</li>
                <li><strong>Payment Security:</strong> Payments are securely processed through ToyyibPay with industry-standard encryption</li>
                <li><strong>GPS Data Retention:</strong> Location data is retained for 30 days for order history, then automatically deleted</li>
              </ul>
            </section>

            <section>
              <h2 className="text-xl font-semibold text-gray-900 mb-3">Your Rights (PDPA)</h2>
              <p className="mb-3">
                Under Malaysia's Personal Data Protection Act (PDPA), you have the right to:
              </p>
              <ul className="list-disc list-inside space-y-2 ml-4">
                <li><strong>Access:</strong> Request a copy of your personal data we hold</li>
                <li><strong>Correction:</strong> Update or correct inaccurate information</li>
                <li><strong>Deletion:</strong> Request deletion of your personal data</li>
              </ul>
            </section>

            <section>
              <h2 className="text-xl font-semibold text-gray-900 mb-3">AI Features</h2>
              <p>
                BinaApp may use AI-powered features to enhance your experience. Please note that
                AI-generated content may not always be accurate. We recommend verifying important
                information independently.
              </p>
            </section>

            <section>
              <h2 className="text-xl font-semibold text-gray-900 mb-3">Contact Us</h2>
              <p>
                If you have questions about this Privacy Policy or wish to exercise your data rights,
                please contact us at{' '}
                <a
                  href="mailto:support@binaapp.my"
                  className="text-blue-600 hover:text-blue-800 underline"
                >
                  support@binaapp.my
                </a>
              </p>
            </section>
          </div>
        </div>
      </div>
    </div>
  );
}
