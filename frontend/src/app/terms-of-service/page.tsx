'use client';

export default function TermsOfServicePage() {
  return (
    <div className="min-h-screen bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-3xl mx-auto">
        <div className="bg-white shadow-lg rounded-lg p-8 sm:p-12">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">Terms of Service</h1>
          <p className="text-sm text-gray-500 mb-8">Last updated: January 2025</p>

          <div className="space-y-8 text-gray-700">
            <section>
              <h2 className="text-xl font-semibold text-gray-900 mb-3">Service Description</h2>
              <p>
                BinaApp is a restaurant delivery platform that connects customers with local
                restaurants and delivery services. We provide the technology infrastructure
                to facilitate ordering, payment processing, and delivery coordination.
              </p>
            </section>

            <section>
              <h2 className="text-xl font-semibold text-gray-900 mb-3">Subscription Plans</h2>
              <p className="mb-3">BinaApp offers the following subscription plans for merchants:</p>
              <ul className="list-disc list-inside space-y-2 ml-4">
                <li><strong>Starter Plan:</strong> RM5/month - Basic features for small businesses</li>
                <li><strong>Basic Plan:</strong> RM29/month - Enhanced features with priority support</li>
                <li><strong>Pro Plan:</strong> RM49/month - Full access to all features and premium support</li>
              </ul>
            </section>

            <section>
              <h2 className="text-xl font-semibold text-gray-900 mb-3">User Responsibilities</h2>
              <p className="mb-3">As a user of BinaApp, you agree to:</p>
              <ul className="list-disc list-inside space-y-2 ml-4">
                <li>Provide accurate and complete information when creating an account</li>
                <li>Keep your account credentials secure and confidential</li>
                <li>Use the platform only for lawful purposes</li>
                <li>Not engage in fraudulent or deceptive activities</li>
              </ul>
            </section>

            <section>
              <h2 className="text-xl font-semibold text-gray-900 mb-3">Merchant Responsibilities</h2>
              <p className="mb-3">Merchants using BinaApp agree to:</p>
              <ul className="list-disc list-inside space-y-2 ml-4">
                <li>Maintain accurate and up-to-date menu information and pricing</li>
                <li>Ensure timely fulfillment of orders</li>
                <li>Comply with all applicable food safety and health regulations</li>
                <li>Respond promptly to customer inquiries and complaints</li>
              </ul>
            </section>

            <section>
              <h2 className="text-xl font-semibold text-gray-900 mb-3">Service Availability</h2>
              <p>
                BinaApp is provided on an "as-is" basis. While we strive to maintain high
                availability, the service may experience downtime for maintenance, updates,
                or due to circumstances beyond our control. We do not guarantee uninterrupted
                access to the platform.
              </p>
            </section>

            <section>
              <h2 className="text-xl font-semibold text-gray-900 mb-3">Liability Limits</h2>
              <p className="mb-3">BinaApp is not responsible for:</p>
              <ul className="list-disc list-inside space-y-2 ml-4">
                <li>Food quality, preparation, or safety issues from restaurant partners</li>
                <li>Delivery delays caused by traffic, weather, or other external factors</li>
                <li>Disputes between customers and merchants</li>
                <li>Accuracy of restaurant information provided by merchants</li>
              </ul>
            </section>

            <section>
              <h2 className="text-xl font-semibold text-gray-900 mb-3">Account Termination</h2>
              <p>
                BinaApp reserves the right to suspend or terminate accounts that violate these
                Terms of Service, engage in fraudulent activity, or otherwise abuse the platform.
                Users may also request account deletion at any time by contacting support.
              </p>
            </section>

            <section>
              <h2 className="text-xl font-semibold text-gray-900 mb-3">Governing Law</h2>
              <p>
                These Terms of Service are governed by and construed in accordance with the
                laws of Malaysia. Any disputes arising from the use of BinaApp shall be
                subject to the exclusive jurisdiction of Malaysian courts.
              </p>
            </section>

            <section>
              <h2 className="text-xl font-semibold text-gray-900 mb-3">Contact Us</h2>
              <p>
                If you have questions about these Terms of Service, please contact us at{' '}
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
