'use client'

export default function PrivacyPolicy() {
  return (
    <div className="min-h-screen bg-gray-50 py-12 px-4">
      <div className="max-w-4xl mx-auto bg-white rounded-lg shadow-md p-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Privacy Policy</h1>
        <p className="text-sm text-gray-600 mb-8">Last updated: January 31, 2025</p>

        <div className="space-y-6 text-gray-700">

          {/* Business Model Clarification */}
          <div className="bg-blue-50 border-l-4 border-blue-500 p-6 mb-6 rounded">
            <h3 className="font-bold text-blue-900 mb-3 text-lg">
              📌 About BinaApp
            </h3>
            <p className="text-blue-800 mb-3">
              BinaApp is a <strong>Software as a Service (SaaS) platform</strong> that provides website 
              building and restaurant management tools. We charge subscription fees (RM5-RM49/month) 
              for access to our software.
            </p>
            <p className="text-blue-800 text-sm">
              We do NOT process customer payments for food orders, employ delivery riders, or operate 
              as a delivery service. Each restaurant manages their own operations independently.
            </p>
          </div>

          {/* Section 1: Introduction */}
          <section>
            <h2 className="text-xl font-semibold text-gray-900 mb-3">1. Introduction</h2>
            <p className="mb-3">
              Welcome to BinaApp. We are committed to protecting your personal information and your 
              right to privacy. This Privacy Policy explains how Ezy Work Asia Solution (SSM: 002944700-D) 
              collects, uses, stores, and protects your personal data in accordance with Malaysia's 
              Personal Data Protection Act 2010 (PDPA 2010).
            </p>
            <p>
              By using BinaApp, you agree to the collection and use of information in accordance with 
              this Privacy Policy.
            </p>
          </section>

          {/* Section 2: Information We Collect */}
          <section>
            <h2 className="text-xl font-semibold text-gray-900 mb-3">2. Information We Collect</h2>
            
            <h3 className="font-semibold text-gray-900 mt-4 mb-2">2.1 Information You Provide Directly</h3>
            <p className="mb-2">When you create an account or use our services, we collect:</p>
            <ul className="list-disc pl-6 space-y-2 mb-3">
              <li><strong>Account Information:</strong> Name, email address, phone number, password</li>
              <li><strong>Business Information (Restaurants):</strong> Restaurant name, SSM registration number, business address, logo</li>
              <li><strong>Payment Information:</strong> Subscription payment details (processed by ToyyibPay - we do NOT store credit card numbers)</li>
              <li><strong>Profile Information:</strong> Any additional information you choose to add to your profile</li>
            </ul>

            <h3 className="font-semibold text-gray-900 mt-4 mb-2">2.2 Information Collected Automatically</h3>
            <ul className="list-disc pl-6 space-y-2 mb-3">
              <li><strong>Usage Data:</strong> How you interact with our platform, features used, pages visited</li>
              <li><strong>Device Information:</strong> Device type, operating system, browser type, IP address</li>
              <li><strong>GPS Location Data:</strong> Only collected from delivery riders during active deliveries (with explicit consent)</li>
              <li><strong>Chat Messages:</strong> Communication between restaurants and customers through our chat feature</li>
              <li><strong>Order Information:</strong> Order details, timestamps, order history</li>
            </ul>

            <h3 className="font-semibold text-gray-900 mt-4 mb-2">2.3 Information from Third Parties</h3>
            <ul className="list-disc pl-6 space-y-2">
              <li><strong>Authentication Services:</strong> If you sign in with Google or other services</li>
              <li><strong>Payment Processors:</strong> Transaction confirmation from ToyyibPay</li>
            </ul>
          </section>

          {/* Section 3: How We Use Your Information */}
          <section>
            <h2 className="text-xl font-semibold text-gray-900 mb-3">3. How We Use Your Information</h2>
            
            <p className="mb-3">We use your personal information for the following purposes:</p>

            <h3 className="font-semibold text-gray-900 mt-4 mb-2">3.1 To Provide Our Services</h3>
            <ul className="list-disc pl-6 space-y-2 mb-3">
              <li>Create and manage your BinaApp account</li>
              <li>Generate and host your restaurant website</li>
              <li>Process subscription payments</li>
              <li>Enable order management features</li>
              <li>Facilitate GPS tracking for deliveries</li>
              <li>Enable chat communication between restaurants and customers</li>
            </ul>

            <h3 className="font-semibold text-gray-900 mt-4 mb-2">3.2 To Improve Our Services</h3>
            <ul className="list-disc pl-6 space-y-2 mb-3">
              <li>Analyze usage patterns to enhance user experience</li>
              <li>Identify and fix technical issues</li>
              <li>Develop new features based on user feedback</li>
              <li>Conduct research and analytics</li>
            </ul>

            <h3 className="font-semibold text-gray-900 mt-4 mb-2">3.3 To Communicate With You</h3>
            <ul className="list-disc pl-6 space-y-2 mb-3">
              <li>Send order notifications and receipts</li>
              <li>Provide customer support</li>
              <li>Send service announcements and updates</li>
              <li>Send subscription renewal reminders</li>
              <li>Respond to your inquiries</li>
            </ul>

            <h3 className="font-semibold text-gray-900 mt-4 mb-2">3.4 For Security and Legal Compliance</h3>
            <ul className="list-disc pl-6 space-y-2">
              <li>Prevent fraud and abuse</li>
              <li>Enforce our Terms of Service</li>
              <li>Comply with legal obligations (tax, accounting requirements)</li>
              <li>Protect the rights and safety of our users</li>
            </ul>
          </section>

          {/* Section 4: Data Retention */}
          <section>
            <h2 className="text-xl font-semibold text-gray-900 mb-3">4. Data Retention</h2>
            
            <p className="mb-3">We retain your personal data only as long as necessary for the purposes stated in this policy:</p>

            <table className="w-full text-sm border mb-4">
              <thead className="bg-gray-100">
                <tr>
                  <th className="border p-2 text-left">Data Type</th>
                  <th className="border p-2 text-left">Retention Period</th>
                  <th className="border p-2 text-left">Reason</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td className="border p-2">Account information</td>
                  <td className="border p-2">While account is active</td>
                  <td className="border p-2">Service provision</td>
                </tr>
                <tr>
                  <td className="border p-2">Order history</td>
                  <td className="border p-2">7 years</td>
                  <td className="border p-2">Tax and accounting compliance</td>
                </tr>
                <tr>
                  <td className="border p-2">Chat messages</td>
                  <td className="border p-2">90 days</td>
                  <td className="border p-2">Customer service and dispute resolution</td>
                </tr>
                <tr>
                  <td className="border p-2">GPS tracking data</td>
                  <td className="border p-2">30 days</td>
                  <td className="border p-2">Delivery tracking and dispute resolution</td>
                </tr>
                <tr>
                  <td className="border p-2">Payment records</td>
                  <td className="border p-2">7 years</td>
                  <td className="border p-2">Financial record-keeping requirements</td>
                </tr>
                <tr>
                  <td className="border p-2">Deleted account data</td>
                  <td className="border p-2">30 days (backup retention)</td>
                  <td className="border p-2">Account recovery period</td>
                </tr>
              </tbody>
            </table>

            <p className="text-sm text-gray-600">
              After the retention period, personal data is securely deleted or anonymized so it can no longer identify you.
            </p>
          </section>

          {/* Section 5: How We Share Your Information */}
          <section>
            <h2 className="text-xl font-semibold text-gray-900 mb-3">5. How We Share Your Information</h2>
            
            <div className="bg-yellow-50 border-l-4 border-yellow-400 p-4 mb-4">
              <p className="font-semibold text-yellow-900">⚠️ Important:</p>
              <p className="text-yellow-800">
                We do NOT sell, rent, or trade your personal information to third parties for marketing purposes.
              </p>
            </div>

            <p className="mb-3">We may share your information in the following limited circumstances:</p>

            <h3 className="font-semibold text-gray-900 mt-4 mb-2">5.1 With Your Consent</h3>
            <p className="mb-3">
              We will share your information with third parties only when you give us explicit permission to do so.
            </p>

            <h3 className="font-semibold text-gray-900 mt-4 mb-2">5.2 Service Providers</h3>
            <p className="mb-2">We share data with trusted service providers who help us operate BinaApp:</p>
            <ul className="list-disc pl-6 space-y-2 mb-3">
              <li><strong>Supabase:</strong> Database, authentication, and file storage</li>
              <li><strong>Vercel:</strong> Website hosting (frontend)</li>
              <li><strong>Render:</strong> Backend API hosting</li>
              <li><strong>ToyyibPay:</strong> Payment processing (they have their own privacy policy)</li>
            </ul>
            <p className="text-sm text-gray-600 mb-3">
              These providers are contractually obligated to protect your data and can only use it to provide services to BinaApp.
            </p>

            <h3 className="font-semibold text-gray-900 mt-4 mb-2">5.3 Between Platform Users</h3>
            <ul className="list-disc pl-6 space-y-2 mb-3">
              <li>Restaurant contact information is visible to customers placing orders</li>
              <li>Customer names and delivery addresses are shared with restaurants to fulfill orders</li>
              <li>Delivery rider location is shared with restaurants and customers during active deliveries</li>
            </ul>

            <h3 className="font-semibold text-gray-900 mt-4 mb-2">5.4 For Legal Reasons</h3>
            <p className="mb-2">We may disclose your information if required to:</p>
            <ul className="list-disc pl-6 space-y-2">
              <li>Comply with legal obligations, court orders, or government requests</li>
              <li>Enforce our Terms of Service</li>
              <li>Protect the rights, property, or safety of BinaApp, our users, or the public</li>
              <li>Prevent fraud or security threats</li>
            </ul>
          </section>

          {/* Section 6: Data Security */}
          <section>
            <h2 className="text-xl font-semibold text-gray-900 mb-3">6. How We Protect Your Information</h2>
            
            <p className="mb-3">We implement industry-standard security measures to protect your personal data:</p>

            <div className="grid md:grid-cols-2 gap-4 mb-4">
              <div className="bg-green-50 p-4 rounded">
                <p className="font-semibold text-green-900 mb-2">🔒 Technical Security</p>
                <ul className="text-sm space-y-1">
                  <li>• HTTPS encryption for all data transmission</li>
                  <li>• Encrypted data storage on Supabase</li>
                  <li>• Regular security audits</li>
                  <li>• Secure password hashing</li>
                </ul>
              </div>
              <div className="bg-green-50 p-4 rounded">
                <p className="font-semibold text-green-900 mb-2">👥 Administrative Security</p>
                <ul className="text-sm space-y-1">
                  <li>• Limited employee access to personal data</li>
                  <li>• Confidentiality agreements</li>
                  <li>• Regular security training</li>
                  <li>• Access logging and monitoring</li>
                </ul>
              </div>
            </div>

            <div className="bg-amber-50 border-l-4 border-amber-500 p-4">
              <p className="font-semibold text-amber-900">⚠️ Important Notice:</p>
              <p className="text-amber-800 text-sm">
                While we implement strong security measures, no system is 100% secure. You are responsible 
                for maintaining the confidentiality of your account password. Never share your password with anyone.
              </p>
            </div>
          </section>

          {/* Section 7: Your Rights Under PDPA */}
          <section className="bg-blue-50 p-6 rounded">
            <h2 className="text-xl font-semibold text-gray-900 mb-3">7. Your Rights Under Malaysian PDPA 2010</h2>
            
            <p className="mb-4">Under Malaysia's Personal Data Protection Act 2010, you have the following rights:</p>

            <div className="grid md:grid-cols-2 gap-4 mb-4">
              <div className="bg-white p-4 rounded">
                <h3 className="font-semibold text-blue-900 mb-2">✅ Right to Access</h3>
                <p className="text-sm">Request a copy of the personal data we hold about you</p>
              </div>
              <div className="bg-white p-4 rounded">
                <h3 className="font-semibold text-blue-900 mb-2">✏️ Right to Correction</h3>
                <p className="text-sm">Request correction of inaccurate or incomplete data</p>
              </div>
              <div className="bg-white p-4 rounded">
                <h3 className="font-semibold text-blue-900 mb-2">🗑️ Right to Deletion</h3>
                <p className="text-sm">Request deletion of your personal data</p>
              </div>
              <div className="bg-white p-4 rounded">
                <h3 className="font-semibold text-blue-900 mb-2">🚫 Right to Withdraw Consent</h3>
                <p className="text-sm">Withdraw consent for data processing at any time</p>
              </div>
              <div className="bg-white p-4 rounded">
                <h3 className="font-semibold text-blue-900 mb-2">📊 Right to Data Portability</h3>
                <p className="text-sm">Request your data in a portable format</p>
              </div>
              <div className="bg-white p-4 rounded">
                <h3 className="font-semibold text-blue-900 mb-2">⛔ Right to Limit Processing</h3>
                <p className="text-sm">Request limitation on how we process your data</p>
              </div>
            </div>

            <h3 className="font-semibold text-gray-900 mt-4 mb-2">How to Exercise Your Rights</h3>
            <div className="bg-white p-4 rounded">
              <p className="mb-2"><strong>Email:</strong> <a href="mailto:admin@binaapp.my" className="text-blue-600 underline">admin@binaapp.my</a></p>
              <p className="mb-2"><strong>Subject:</strong> &quot;PDPA Request - [Type of Request]&quot;</p>
              <p className="mb-2"><strong>Include:</strong></p>
              <ul className="list-disc pl-6 text-sm space-y-1">
                <li>Your full name and registered email</li>
                <li>Clear description of your request</li>
                <li>Proof of identity (to protect your privacy)</li>
              </ul>
              <p className="mt-3 text-sm text-gray-600">
                <strong>Response Time:</strong> We will respond within 21 days of receiving your request, 
                as required by PDPA 2010.
              </p>
            </div>
          </section>

          {/* Section 8: GPS Tracking Specific */}
          <section>
            <h2 className="text-xl font-semibold text-gray-900 mb-3">8. GPS Tracking & Location Data</h2>
            
            <div className="bg-orange-50 border-l-4 border-orange-400 p-4 mb-4">
              <p className="font-semibold text-orange-900 mb-2">📍 GPS Tracking Transparency</p>
              <p className="text-orange-800 text-sm">
                GPS tracking is ONLY used for delivery riders during active deliveries and requires explicit consent.
              </p>
            </div>

            <h3 className="font-semibold text-gray-900 mt-4 mb-2">8.1 What We Track</h3>
            <ul className="list-disc pl-6 space-y-2 mb-3">
              <li>Real-time location of delivery riders (only during active deliveries)</li>
              <li>Route taken for completed deliveries</li>
              <li>Timestamp and location of order pickup and delivery</li>
            </ul>

            <h3 className="font-semibold text-gray-900 mt-4 mb-2">8.2 Who Can See It</h3>
            <ul className="list-disc pl-6 space-y-2 mb-3">
              <li>The restaurant that assigned the delivery</li>
              <li>The customer waiting for their order</li>
              <li>BinaApp support (only for troubleshooting purposes)</li>
            </ul>

            <h3 className="font-semibold text-gray-900 mt-4 mb-2">8.3 How Long We Keep It</h3>
            <p className="mb-2">
              GPS tracking data is automatically deleted after <strong>30 days</strong>.
            </p>

            <h3 className="font-semibold text-gray-900 mt-4 mb-2">8.4 Your Control</h3>
            <ul className="list-disc pl-6 space-y-2">
              <li>Riders can disable GPS tracking in device settings (but this will prevent delivery tracking)</li>
              <li>GPS tracking automatically stops when delivery is marked as complete</li>
              <li>You can request deletion of your GPS history by contacting support</li>
            </ul>
          </section>

          {/* Section 9: Chat & Communications */}
          <section>
            <h2 className="text-xl font-semibold text-gray-900 mb-3">9. Chat & Communications</h2>
            
            <h3 className="font-semibold text-gray-900 mt-4 mb-2">9.1 Chat Messages</h3>
            <p className="mb-3">
              Our platform includes chat features for communication between customers and restaurants. 
              Please note:
            </p>
            <ul className="list-disc pl-6 space-y-2 mb-3">
              <li>Chat messages are stored for <strong>90 days</strong></li>
              <li>Messages are <strong>NOT end-to-end encrypted</strong></li>
              <li>BinaApp staff may review messages for quality assurance and dispute resolution</li>
              <li>Do NOT share sensitive information (passwords, credit card numbers) via chat</li>
            </ul>

            <h3 className="font-semibold text-gray-900 mt-4 mb-2">9.2 Email Communications</h3>
            <p className="mb-2">We may send you:</p>
            <ul className="list-disc pl-6 space-y-2">
              <li><strong>Transactional emails:</strong> Order confirmations, receipts, account notifications (you cannot opt-out)</li>
              <li><strong>Service updates:</strong> Important changes to BinaApp features or terms</li>
              <li><strong>Marketing emails:</strong> Promotional offers and news (you can opt-out anytime)</li>
            </ul>
          </section>

          {/* Section 10: Cookies */}
          <section>
            <h2 className="text-xl font-semibold text-gray-900 mb-3">10. Cookies & Tracking Technologies</h2>
            
            <p className="mb-3">
              BinaApp uses cookies and similar technologies to enhance your experience and analyze platform usage.
            </p>

            <h3 className="font-semibold text-gray-900 mt-4 mb-2">10.1 Types of Cookies We Use</h3>
            <table className="w-full text-sm border mb-4">
              <thead className="bg-gray-100">
                <tr>
                  <th className="border p-2 text-left">Cookie Type</th>
                  <th className="border p-2 text-left">Purpose</th>
                  <th className="border p-2 text-left">Can You Opt Out?</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td className="border p-2"><strong>Essential</strong></td>
                  <td className="border p-2">Login, security, basic functionality</td>
                  <td className="border p-2">No - required for service</td>
                </tr>
                <tr>
                  <td className="border p-2"><strong>Analytics</strong></td>
                  <td className="border p-2">Understand how users interact with BinaApp</td>
                  <td className="border p-2">Yes - via browser settings</td>
                </tr>
                <tr>
                  <td className="border p-2"><strong>Preferences</strong></td>
                  <td className="border p-2">Remember your settings and preferences</td>
                  <td className="border p-2">Yes - but may affect functionality</td>
                </tr>
              </tbody>
            </table>

            <h3 className="font-semibold text-gray-900 mt-4 mb-2">10.2 Managing Cookies</h3>
            <p className="mb-2">
              You can control cookies through your browser settings. However, disabling essential cookies 
              may prevent you from using certain features of BinaApp.
            </p>
          </section>

          {/* Section 11: Children's Privacy */}
          <section>
            <h2 className="text-xl font-semibold text-gray-900 mb-3">11. Children&apos;s Privacy</h2>
            
            <div className="bg-red-50 border-l-4 border-red-500 p-4">
              <p className="font-semibold text-red-900 mb-2">⚠️ Age Restriction</p>
              <p className="text-red-800 mb-3">
                BinaApp is not intended for use by anyone under 18 years old. We do not knowingly collect 
                personal information from children.
              </p>
              <p className="text-red-800 text-sm">
                If you believe we have inadvertently collected data from a child, please contact us immediately 
                at <a href="mailto:admin@binaapp.my" className="underline">admin@binaapp.my</a> and we will 
                promptly delete such information.
              </p>
            </div>
          </section>

          {/* Section 12: Third-Party Links */}
          <section>
            <h2 className="text-xl font-semibold text-gray-900 mb-3">12. Third-Party Links & Services</h2>
            
            <p className="mb-3">
              BinaApp may contain links to third-party websites or integrate with third-party services 
              (e.g., ToyyibPay for payments). This Privacy Policy does not apply to those external sites or services.
            </p>
            
            <p className="mb-2"><strong>Third-Party Services We Use:</strong></p>
            <ul className="list-disc pl-6 space-y-2 mb-3">
              <li><strong>ToyyibPay:</strong> Payment processing - <a href="https://toyyibpay.com/privacy-policy" className="text-blue-600 underline" target="_blank" rel="noopener noreferrer">View their privacy policy</a></li>
              <li><strong>Supabase:</strong> Data hosting - <a href="https://supabase.com/privacy" className="text-blue-600 underline" target="_blank" rel="noopener noreferrer">View their privacy policy</a></li>
            </ul>

            <p className="text-sm text-gray-600">
              We recommend reviewing the privacy policies of any third-party services you interact with.
            </p>
          </section>

          {/* Section 13: International Data Transfers */}
          <section>
            <h2 className="text-xl font-semibold text-gray-900 mb-3">13. International Data Transfers</h2>
            
            <p className="mb-3">
              Your data may be transferred to and stored on servers located outside Malaysia, including:
            </p>
            <ul className="list-disc pl-6 space-y-2 mb-3">
              <li><strong>Supabase:</strong> Data may be stored in Singapore or other regions</li>
              <li><strong>Vercel/Render:</strong> Hosting servers in various global locations</li>
            </ul>
            <p className="text-sm text-gray-600">
              We ensure that all data transfers comply with PDPA requirements and that adequate safeguards 
              are in place to protect your information.
            </p>
          </section>

          {/* Section 14: Changes to Privacy Policy */}
          <section>
            <h2 className="text-xl font-semibold text-gray-900 mb-3">14. Changes to This Privacy Policy</h2>
            
            <p className="mb-3">
              We may update this Privacy Policy from time to time to reflect changes in our practices or 
              for legal, operational, or regulatory reasons.
            </p>

            <h3 className="font-semibold text-gray-900 mt-4 mb-2">14.1 How We Notify You</h3>
            <ul className="list-disc pl-6 space-y-2 mb-3">
              <li>We will post the updated policy on this page with a new &quot;Last Updated&quot; date</li>
              <li>For significant changes, we will notify you via email</li>
              <li>Continued use of BinaApp after changes constitutes acceptance of the new policy</li>
            </ul>

            <p className="text-sm text-gray-600">
              We encourage you to review this Privacy Policy periodically to stay informed about how we 
              protect your information.
            </p>
          </section>

          {/* Section 15: Contact & Complaints */}
          <section className="bg-gray-50 p-6 rounded">
            <h2 className="text-xl font-semibold text-gray-900 mb-3">15. Contact Us & File Complaints</h2>
            
            <h3 className="font-semibold text-gray-900 mt-4 mb-2">15.1 Data Protection Officer</h3>
            <div className="bg-white p-4 rounded mb-4">
              <p className="mb-1"><strong>Company:</strong> Ezy Work Asia Solution</p>
              <p className="mb-1"><strong>SSM Registration:</strong> 002944700-D</p>
              <p className="mb-1"><strong>Email:</strong> <a href="mailto:admin@binaapp.my" className="text-blue-600 underline">admin@binaapp.my</a></p>
              <p className="mb-1"><strong>Subject for PDPA Requests:</strong> &quot;PDPA Request&quot;</p>
            </div>

            <h3 className="font-semibold text-gray-900 mt-4 mb-2">15.2 General Privacy Inquiries</h3>
            <p className="mb-1">Email: <a href="mailto:support.team@binaapp.my" className="text-blue-600 underline">support.team@binaapp.my</a></p>
            <p className="mb-4 text-sm text-gray-600">We aim to respond to all inquiries within 7 business days.</p>

            <h3 className="font-semibold text-gray-900 mt-4 mb-2">15.3 Filing a Complaint</h3>
            <p className="mb-2">
              If you are not satisfied with how we handle your personal data, you can file a complaint with:
            </p>
            <div className="bg-white p-4 rounded">
              <p className="font-semibold mb-2">Personal Data Protection Department</p>
              <p className="text-sm mb-1">Ministry of Communications and Digital</p>
              <p className="text-sm mb-1">Level 4-7, Menara MCMC, Off Persiaran Multimedia</p>
              <p className="text-sm mb-1">Cyber 6, 63000 Cyberjaya, Selangor</p>
              <p className="text-sm mb-1">Phone: 1-300-88-2400</p>
              <p className="text-sm">Website: <a href="http://www.pdp.gov.my" className="text-blue-600 underline" target="_blank" rel="noopener noreferrer">www.pdp.gov.my</a></p>
            </div>
          </section>

          {/* Section 16: Consent */}
          <section className="bg-green-50 border-2 border-green-600 p-6 rounded-lg">
            <h2 className="text-xl font-semibold text-green-900 mb-3">16. Your Consent</h2>
            
            <p className="mb-3">By using BinaApp, you acknowledge that:</p>
            <ul className="space-y-2">
              <li>✅ You have read and understood this Privacy Policy</li>
              <li>✅ You consent to the collection, use, and processing of your personal data as described</li>
              <li>✅ You understand your rights under Malaysian PDPA 2010</li>
              <li>✅ You can withdraw your consent at any time by contacting us</li>
            </ul>

            <p className="mt-4 text-sm text-green-800">
              <strong>Note:</strong> Withdrawing consent may limit your ability to use certain BinaApp features 
              or may result in account termination if essential data cannot be processed.
            </p>
          </section>

          {/* Footer */}
          <section className="text-center text-sm text-gray-600 pt-6 border-t">
            <p className="mb-1">Privacy Policy Version: 2.0</p>
            <p className="mb-1">Last Updated: January 31, 2025</p>
            <p className="mb-3">Effective Date: January 31, 2025</p>
            <p className="font-semibold">© 2025 Ezy Work Asia Solution. All rights reserved.</p>
            <p className="text-xs mt-1">BinaApp is a service of Ezy Work Asia Solution (SSM: 002944700-D)</p>
            <p className="text-xs mt-2">
              This Privacy Policy complies with the Personal Data Protection Act 2010 (Act 709) of Malaysia
            </p>
          </section>

        </div>
      </div>
    </div>
  )
}
