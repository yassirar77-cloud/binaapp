'use client'

export default function TermsOfService() {
  return (
    <div className="min-h-screen bg-gray-50 py-12 px-4">
      <div className="max-w-4xl mx-auto bg-white rounded-lg shadow-md p-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Terms of Service</h1>
        <p className="text-sm text-gray-600 mb-8">Last updated: January 31, 2025</p>

        <div className="space-y-6 text-gray-700">
          
          {/* BUSINESS MODEL CLARIFICATION - NEW */}
          <div className="bg-blue-50 border-l-4 border-blue-500 p-6 mb-6 rounded">
            <h3 className="font-bold text-blue-900 mb-3 text-lg">
              📌 Understanding BinaApp&apos;s Business Model
            </h3>
            <p className="text-blue-800 mb-3">
              BinaApp is a <strong>SaaS (Software as a Service) platform</strong> that provides website 
              building and restaurant management tools. We charge <strong>subscription fees only</strong> 
              (RM5-RM49 per month) for access to our software.
            </p>
            
            <div className="bg-white p-4 rounded mb-3">
              <p className="font-semibold text-blue-900 mb-2">✅ What We Provide:</p>
              <ul className="list-disc pl-6 text-blue-800 space-y-1 text-sm">
                <li>Website builder (yourrestaurant.binaapp.my)</li>
                <li>Order management software</li>
                <li>GPS tracking tools</li>
                <li>Customer chat features</li>
                <li>Payment integration via ToyyibPay</li>
                <li>Cloud hosting and storage</li>
              </ul>
            </div>

            <div className="bg-white p-4 rounded">
              <p className="font-semibold text-blue-900 mb-2">❌ What We Do NOT Do:</p>
              <ul className="list-disc pl-6 text-blue-800 space-y-1 text-sm">
                <li>Take commission or percentage from food orders</li>
                <li>Process customer payments (customers pay restaurants directly)</li>
                <li>Employ, hire, or manage delivery riders</li>
                <li>Control or supervise restaurant operations</li>
                <li>Handle money flow between customers and restaurants</li>
              </ul>
            </div>

            <p className="text-blue-800 mt-3 text-sm italic">
              💡 <strong>Simple Analogy:</strong> BinaApp is like renting an office space with tools. 
              You pay rent (subscription), we provide the space and tools, but you run your own 
              business your own way.
            </p>
          </div>
          
          {/* Section 1: Service Description */}
          <section>
            <h2 className="text-xl font-semibold text-gray-900 mb-3">1. Service Description</h2>
            <p className="mb-3">BinaApp is a restaurant delivery platform that provides website building, order management, GPS tracking, and payment integration services for restaurants in Malaysia.</p>
            <div className="bg-yellow-50 border-l-4 border-yellow-400 p-4">
              <p className="font-semibold">Platform Nature:</p>
              <p>BinaApp is a technology platform providing software tools. BinaApp does NOT operate as a delivery service provider, does not employ riders, and does not control restaurant operations.</p>
            </div>
          </section>

          {/* Section 2: Definitions */}
          <section>
            <h2 className="text-xl font-semibold text-gray-900 mb-3">2. Definitions</h2>
            <ul className="space-y-2">
              <li><strong>&quot;Platform&quot;</strong> means BinaApp&apos;s website, mobile applications, and related services.</li>
              <li><strong>&quot;Restaurant&quot;</strong> or <strong>&quot;Merchant&quot;</strong> means any food business using BinaApp to create websites and manage orders.</li>
              <li><strong>&quot;Customer&quot;</strong> means any person placing food orders through BinaApp-powered restaurant websites.</li>
              <li><strong>&quot;Rider&quot;</strong> or <strong>&quot;Delivery Partner&quot;</strong> means any person performing delivery services for restaurants using BinaApp&apos;s GPS tracking tools.</li>
              <li><strong>&quot;Services&quot;</strong> means all features provided by BinaApp including website builder, order management, GPS tracking, chat, and payment integration.</li>
            </ul>
          </section>

          {/* Section 3: Eligibility */}
          <section>
            <h2 className="text-xl font-semibold text-gray-900 mb-3">3. Eligibility & Account Requirements</h2>
            <h3 className="font-semibold text-gray-900 mt-4 mb-2">3.1 Minimum Age</h3>
            <p className="mb-3">You must be at least <strong>18 years old</strong> to create a BinaApp account, enter into this agreement, or use BinaApp services.</p>
            
            <h3 className="font-semibold text-gray-900 mt-4 mb-2">3.2 Account Credentials</h3>
            <p className="mb-2">You are responsible for:</p>
            <ul className="list-disc pl-6 space-y-2">
              <li>Keeping your password confidential and secure</li>
              <li>Using strong, unique passwords</li>
              <li>All activity that occurs under your account</li>
              <li>Notifying us immediately at support.team@binaapp.my of any unauthorized access</li>
              <li>Not sharing account credentials with others</li>
            </ul>
          </section>

          {/* Section 4: Subscription Plans */}
          <section>
            <h2 className="text-xl font-semibold text-gray-900 mb-3">4. Subscription Plans & Billing</h2>
            <h3 className="font-semibold text-gray-900 mt-4 mb-2">4.1 Available Plans</h3>
            <ul className="list-disc pl-6 space-y-2 mb-3">
              <li><strong>Starter:</strong> RM5 per month</li>
              <li><strong>Basic:</strong> RM29 per month</li>
              <li><strong>Pro:</strong> RM49 per month</li>
            </ul>
            <p className="mb-3">Payments are processed securely through ToyyibPay.</p>
            
            <h3 className="font-semibold text-gray-900 mt-4 mb-2">4.2 Auto-Renewal</h3>
            <div className="bg-amber-50 border-l-4 border-amber-500 p-4 mb-3">
              <p className="font-semibold mb-2">⚠️ Important Auto-Renewal Information:</p>
              <ul className="list-disc pl-6 space-y-1 text-sm">
                <li>Your subscription will automatically renew on your billing date</li>
                <li>You can cancel anytime before the next billing date</li>
                <li>Cancellation takes effect at the end of your current billing period</li>
                <li>No partial refunds for mid-cycle cancellations</li>
              </ul>
            </div>

            <h3 className="font-semibold text-gray-900 mt-4 mb-2">4.3 Payment Failures</h3>
            <p className="mb-2">If payment fails:</p>
            <ul className="list-disc pl-6 space-y-2">
              <li><strong>Day 1:</strong> We retry payment automatically</li>
              <li><strong>Day 3:</strong> Email reminder sent to update payment method</li>
              <li><strong>Day 7:</strong> Account suspended (view-only access, no new orders)</li>
              <li><strong>Day 30:</strong> Account and data permanently deleted</li>
            </ul>
          </section>

          {/* Section 5: User Responsibilities */}
          <section>
            <h2 className="text-xl font-semibold text-gray-900 mb-3">5. User Responsibilities</h2>
            <h3 className="font-semibold text-gray-900 mt-4 mb-2">5.1 General Obligations</h3>
            <p className="mb-2">All users must:</p>
            <ul className="list-disc pl-6 space-y-2 mb-3">
              <li>Provide accurate information when creating accounts</li>
              <li>Use the platform only for lawful purposes</li>
              <li>Keep account credentials secure</li>
              <li>Comply with all applicable Malaysian laws</li>
            </ul>

            <h3 className="font-semibold text-gray-900 mt-4 mb-2">5.2 Prohibited Activities</h3>
            <p className="mb-2">You must NOT:</p>
            <ul className="list-disc pl-6 space-y-2">
              <li>Violate any laws or regulations</li>
              <li>Infringe on intellectual property rights</li>
              <li>Transmit malware, viruses, or harmful code</li>
              <li>Attempt to gain unauthorized access to BinaApp systems</li>
              <li>Scrape, copy, or extract platform data without permission</li>
              <li>Use BinaApp to harass, threaten, or harm others</li>
            </ul>
          </section>

          {/* Section 6: Merchant Responsibilities */}
          <section>
            <h2 className="text-xl font-semibold text-gray-900 mb-3">6. Merchant Responsibilities</h2>
            <h3 className="font-semibold text-gray-900 mt-4 mb-2">6.1 Menu & Pricing</h3>
            <p className="mb-2">Restaurants must:</p>
            <ul className="list-disc pl-6 space-y-2 mb-3">
              <li>Ensure menu items and prices are accurate and up-to-date</li>
              <li>Update unavailable items promptly</li>
              <li>Display clear allergen information where applicable</li>
              <li>Comply with Malaysian food labeling requirements</li>
            </ul>

            <h3 className="font-semibold text-gray-900 mt-4 mb-2">6.2 Order Fulfillment</h3>
            <ul className="list-disc pl-6 space-y-2 mb-3">
              <li>Fulfill orders in a timely manner</li>
              <li>Maintain food quality and safety standards</li>
              <li>Respond promptly to customer inquiries</li>
              <li>Package food appropriately for delivery</li>
            </ul>

            <h3 className="font-semibold text-gray-900 mt-4 mb-2">6.3 Food Safety & Licensing</h3>
            <p className="mb-2">Restaurants are solely responsible for:</p>
            <ul className="list-disc pl-6 space-y-2">
              <li>Obtaining and maintaining all required licenses (business, food handling, etc.)</li>
              <li>Complying with Malaysian food safety regulations</li>
              <li>Food quality, hygiene, and safety</li>
              <li>Foodborne illness or contamination</li>
            </ul>
          </section>

          {/* Section 7: Customer Responsibilities */}
          <section>
            <h2 className="text-xl font-semibold text-gray-900 mb-3">7. Customer Responsibilities</h2>
            <h3 className="font-semibold text-gray-900 mt-4 mb-2">7.1 Accurate Information</h3>
            <p className="mb-2">Customers must:</p>
            <ul className="list-disc pl-6 space-y-2 mb-3">
              <li>Provide accurate delivery addresses</li>
              <li>Provide valid contact numbers</li>
              <li>Be available to receive deliveries</li>
              <li>Update contact information if changed</li>
            </ul>

            <h3 className="font-semibold text-gray-900 mt-4 mb-2">7.2 Age-Restricted Items</h3>
            <p className="mb-2">For orders containing alcohol or tobacco:</p>
            <ul className="list-disc pl-6 space-y-2 mb-3">
              <li>Customer must be 21+ years old</li>
              <li>Must present valid ID upon delivery</li>
              <li>Rider may refuse delivery without valid ID</li>
              <li>No refunds for refused age-restricted deliveries</li>
            </ul>
            <div className="bg-red-50 border-l-4 border-red-500 p-3">
              <p className="font-semibold text-red-800">Health Warning:</p>
              <p className="text-red-700">MEMINUM ARAK BOLEH MEMBAHAYAKAN KESIHATAN</p>
            </div>
          </section>

          {/* Section 8: Cancellation & Refunds */}
          <section>
            <h2 className="text-xl font-semibold text-gray-900 mb-3">8. Order Cancellation & Refund Policy</h2>
            
            <h3 className="font-semibold text-gray-900 mt-4 mb-2">8.1 Customer Cancellations</h3>
            <div className="space-y-2 mb-3">
              <p><strong>Before Restaurant Accepts:</strong></p>
              <ul className="list-disc pl-6 space-y-1">
                <li>Free cancellation within 2 minutes of order placement</li>
                <li>After 2 minutes: RM2 cancellation fee applies</li>
              </ul>
              <p className="mt-2"><strong>After Restaurant Accepts:</strong></p>
              <ul className="list-disc pl-6 space-y-1">
                <li>Customer liable for full order amount</li>
                <li>Refunds at restaurant&apos;s sole discretion</li>
                <li>BinaApp does not process refunds for accepted orders</li>
              </ul>
            </div>

            <h3 className="font-semibold text-gray-900 mt-4 mb-2">8.2 Refund Eligibility</h3>
            <div className="grid md:grid-cols-2 gap-4">
              <div className="bg-green-50 p-4 rounded">
                <p className="font-semibold text-green-800 mb-2">✅ Eligible for Refund:</p>
                <ul className="text-sm space-y-1">
                  <li>• Order not received</li>
                  <li>• Incorrect items delivered</li>
                  <li>• Food quality issues (with photo proof)</li>
                  <li>• Restaurant cancellation</li>
                </ul>
              </div>
              <div className="bg-red-50 p-4 rounded">
                <p className="font-semibold text-red-800 mb-2">❌ NOT Eligible:</p>
                <ul className="text-sm space-y-1">
                  <li>• Changed mind after acceptance</li>
                  <li>• Customer unavailable</li>
                  <li>• Incorrect address provided</li>
                  <li>• Subjective taste preferences</li>
                </ul>
              </div>
            </div>
          </section>

          {/* Section 9: Delivery Disclaimer - SIMPLIFIED */}
          <section className="bg-orange-50 border-2 border-orange-400 p-6 rounded-lg">
            <h2 className="text-xl font-semibold text-orange-900 mb-3">9. Delivery Operations Disclaimer</h2>
            
            <div className="bg-white p-4 rounded mb-3">
              <p className="font-semibold text-orange-900 mb-2">Software Tools Only:</p>
              <p className="text-gray-800">
                BinaApp provides <strong>software tools</strong> (GPS tracking, order management, chat features). 
                These are <strong>convenience tools</strong> that restaurants choose to use. BinaApp does NOT:
              </p>
              <ul className="list-disc pl-6 mt-2 space-y-1 text-sm">
                <li>Operate as a delivery service provider</li>
                <li>Employ, hire, or contract delivery riders</li>
                <li>Own or operate delivery vehicles</li>
                <li>Control, direct, or supervise delivery operations</li>
                <li>Verify rider qualifications, licenses, or insurance</li>
              </ul>
            </div>

            <div className="bg-white p-4 rounded">
              <p className="font-semibold text-orange-900 mb-2">Restaurant Responsibility:</p>
              <p className="text-gray-800">
                Each restaurant is <strong>solely responsible</strong> for:
              </p>
              <ul className="list-disc pl-6 mt-2 space-y-1 text-sm">
                <li>Hiring and managing their own delivery riders</li>
                <li>Ensuring riders have valid licenses and insurance</li>
                <li>All delivery-related liabilities, accidents, and damages</li>
                <li>Compliance with Malaysian delivery laws (GDL, etc.)</li>
              </ul>
            </div>

            <p className="text-sm text-gray-600 mt-3 italic">
              BinaApp&apos;s GPS tracking feature does NOT imply control, supervision, or employment. 
              It is a software tool provided &quot;as-is&quot; that may have technical limitations or inaccuracies.
            </p>
          </section>

          {/* Section 10: PDPA */}
          <section className="bg-blue-50 border-l-4 border-blue-500 p-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-3">10. Personal Data Protection & Privacy (PDPA)</h2>
            
            <div className="mb-4">
              <p className="font-semibold mb-2">🔒 BinaApp is committed to protecting your personal data under Malaysian PDPA 2010.</p>
            </div>

            <h3 className="font-semibold text-gray-900 mt-4 mb-2">10.1 Data We Collect</h3>
            <ul className="list-disc pl-6 space-y-2 mb-3">
              <li><strong>Account Info:</strong> Name, email, phone, IC number, SSM registration</li>
              <li><strong>Order Data:</strong> Customer names, addresses, order history</li>
              <li><strong>Location Data:</strong> GPS tracking during deliveries (retained 30 days)</li>
              <li><strong>Communications:</strong> Chat messages (retained 90 days)</li>
              <li><strong>Payment Info:</strong> Processed via ToyyibPay (not stored by BinaApp)</li>
            </ul>

            <h3 className="font-semibold text-gray-900 mt-4 mb-2">10.2 How We Use Your Data</h3>
            <ul className="list-disc pl-6 space-y-2 mb-3">
              <li>Provide and improve BinaApp services</li>
              <li>Process orders and payments</li>
              <li>Enable GPS tracking for deliveries</li>
              <li>Facilitate customer-restaurant communication</li>
              <li>Send service notifications and receipts</li>
              <li>Comply with legal obligations (tax, accounting)</li>
            </ul>

            <h3 className="font-semibold text-gray-900 mt-4 mb-2">10.3 Data Retention</h3>
            <table className="w-full text-sm border">
              <thead className="bg-gray-100">
                <tr>
                  <th className="border p-2 text-left">Data Type</th>
                  <th className="border p-2 text-left">Retention</th>
                </tr>
              </thead>
              <tbody>
                <tr><td className="border p-2">Order history</td><td className="border p-2">7 years</td></tr>
                <tr><td className="border p-2">Chat messages</td><td className="border p-2">90 days</td></tr>
                <tr><td className="border p-2">GPS tracking</td><td className="border p-2">30 days</td></tr>
                <tr><td className="border p-2">Active account</td><td className="border p-2">While active</td></tr>
              </tbody>
            </table>

            <h3 className="font-semibold text-gray-900 mt-4 mb-2">10.4 Your Rights Under PDPA</h3>
            <div className="grid md:grid-cols-2 gap-3">
              <div className="bg-white p-3 rounded">
                <p className="font-semibold">✅ Access</p>
                <p className="text-sm">Request copies of your data</p>
              </div>
              <div className="bg-white p-3 rounded">
                <p className="font-semibold">✏️ Correction</p>
                <p className="text-sm">Request correction of errors</p>
              </div>
              <div className="bg-white p-3 rounded">
                <p className="font-semibold">🗑️ Deletion</p>
                <p className="text-sm">Request data deletion</p>
              </div>
              <div className="bg-white p-3 rounded">
                <p className="font-semibold">🚫 Withdrawal</p>
                <p className="text-sm">Withdraw consent</p>
              </div>
            </div>

            <div className="mt-4 bg-white p-4 rounded">
              <p className="font-semibold mb-2">To Exercise Your Rights:</p>
              <p className="text-sm">Email: <a href="mailto:admin@binaapp.my" className="text-blue-600 underline">admin@binaapp.my</a></p>
              <p className="text-sm">Subject: &quot;PDPA Request&quot;</p>
              <p className="text-sm">Response Time: Within 21 days</p>
            </div>
          </section>

          {/* Section 11: Software Tools */}
          <section>
            <h2 className="text-xl font-semibold text-gray-900 mb-3">11. Software Tools & Features</h2>
            
            <h3 className="font-semibold text-gray-900 mt-4 mb-2">11.1 GPS Tracking Tool</h3>
            <p className="mb-2">BinaApp provides GPS tracking as a software feature:</p>
            <ul className="list-disc pl-6 space-y-2 mb-3">
              <li>Tracks rider location during active deliveries (with rider&apos;s permission)</li>
              <li>Shows real-time location to customers and restaurants</li>
              <li>Location data retained for 30 days, then deleted</li>
              <li>May be inaccurate due to technical limitations (GPS signal, weather, etc.)</li>
              <li>Does NOT create employment or agency relationships</li>
            </ul>

            <h3 className="font-semibold text-gray-900 mt-4 mb-2">11.2 Chat Feature</h3>
            <p className="mb-2">In-app chat for customer-restaurant communication:</p>
            <ul className="list-disc pl-6 space-y-2 mb-3">
              <li>For order-related inquiries only</li>
              <li>Messages retained for 90 days</li>
              <li>NOT end-to-end encrypted</li>
              <li>Do not share sensitive personal information (IC, passwords, cards)</li>
            </ul>

            <h3 className="font-semibold text-gray-900 mt-4 mb-2">11.3 Order Management Software</h3>
            <p>BinaApp provides software for managing orders. Restaurants are responsible for fulfilling orders accurately and on time.</p>
          </section>

          {/* Section 12: Intellectual Property */}
          <section>
            <h2 className="text-xl font-semibold text-gray-900 mb-3">12. Intellectual Property Rights</h2>
            
            <h3 className="font-semibold text-gray-900 mt-4 mb-2">12.1 BinaApp Owns</h3>
            <ul className="list-disc pl-6 space-y-2 mb-3">
              <li>BinaApp software, code, and algorithms</li>
              <li>Website builder templates and tools</li>
              <li>GPS tracking technology</li>
              <li>Platform design and user interface</li>
              <li>BinaApp logo, name, and trademarks</li>
            </ul>

            <h3 className="font-semibold text-gray-900 mt-4 mb-2">12.2 Restaurants Own</h3>
            <ul className="list-disc pl-6 space-y-2 mb-3">
              <li>Menu items, descriptions, and pricing</li>
              <li>Restaurant name, logo, and branding</li>
              <li>Food photographs uploaded</li>
              <li>Marketing materials</li>
            </ul>

            <h3 className="font-semibold text-gray-900 mt-4 mb-2">12.3 Subdomain License</h3>
            <p className="mb-2">Websites at <code className="bg-gray-100 px-2 py-1 rounded">[restaurantname].binaapp.my</code>:</p>
            <ul className="list-disc pl-6 space-y-2">
              <li>Are <strong>licensed for use</strong> during active subscription</li>
              <li>Cannot be transferred or sold to third parties</li>
              <li>Terminate upon subscription cancellation</li>
              <li>May be deleted 30 days after account closure</li>
            </ul>
          </section>

          {/* Section 13: Service Availability */}
          <section>
            <h2 className="text-xl font-semibold text-gray-900 mb-3">13. Service Availability & Support</h2>
            
            <p className="mb-3">BinaApp strives for <strong>99.9% uptime</strong> but does NOT guarantee uninterrupted service.</p>

            <h3 className="font-semibold text-gray-900 mt-4 mb-2">13.1 Customer Support</h3>
            <div className="bg-gray-50 p-4 rounded">
              <p className="mb-2"><strong>Email:</strong> support.team@binaapp.my</p>
              <p className="mb-2"><strong>Business Hours:</strong> Monday-Friday, 9 AM - 6 PM MYT</p>
              <p className="mb-2"><strong>Response Times:</strong></p>
              <ul className="list-disc pl-6 space-y-1 text-sm">
                <li>Starter: 48-72 hours</li>
                <li>Basic: 24-48 hours</li>
                <li>Pro: 12-24 hours</li>
              </ul>
            </div>
          </section>

          {/* Section 14: Account Termination */}
          <section>
            <h2 className="text-xl font-semibold text-gray-900 mb-3">14. Account Termination</h2>
            
            <h3 className="font-semibold text-gray-900 mt-4 mb-2">14.1 Cancelling Your Subscription</h3>
            <p className="mb-2">You may cancel anytime via:</p>
            <ul className="list-disc pl-6 space-y-2 mb-3">
              <li>Account dashboard settings</li>
              <li>Email to support.team@binaapp.my</li>
              <li>Effective at end of current billing period</li>
              <li>No partial refunds for unused time</li>
            </ul>

            <div className="bg-amber-50 border-l-4 border-amber-500 p-4">
              <p className="font-semibold">⚠️ Upon Termination:</p>
              <ul className="list-disc pl-6 space-y-1 text-sm mt-2">
                <li>Website becomes inaccessible immediately</li>
                <li>Data retained 30 days, then permanently deleted</li>
                <li><strong>Export your data before cancelling!</strong></li>
              </ul>
            </div>
          </section>

          {/* Section 15: Third-Party Services */}
          <section>
            <h2 className="text-xl font-semibold text-gray-900 mb-3">15. Third-Party Services</h2>
            
            <h3 className="font-semibold text-gray-900 mt-4 mb-2">15.1 Payment Processing</h3>
            <p className="mb-2">All payments processed through <strong>ToyyibPay</strong>:</p>
            <ul className="list-disc pl-6 space-y-2 mb-3">
              <li>BinaApp does NOT store credit card information</li>
              <li>BinaApp NOT responsible for ToyyibPay failures</li>
              <li>Payment disputes handled by ToyyibPay</li>
            </ul>

            <h3 className="font-semibold text-gray-900 mt-4 mb-2">15.2 Hosting Infrastructure</h3>
            <ul className="list-disc pl-6 space-y-2">
              <li><strong>Frontend:</strong> Vercel</li>
              <li><strong>Backend:</strong> Render</li>
              <li><strong>Database:</strong> Supabase</li>
              <li>BinaApp NOT liable for third-party service outages</li>
            </ul>
          </section>

          {/* Section 16: Limitation of Liability */}
          <section className="bg-gray-100 p-6 rounded">
            <h2 className="text-xl font-semibold text-gray-900 mb-3">16. Limitation of Liability</h2>
            
            <p className="font-bold mb-3">BinaApp provides software &quot;AS-IS&quot; and &quot;AS AVAILABLE&quot;</p>

            <h3 className="font-semibold text-gray-900 mt-4 mb-2">BinaApp is NOT liable for:</h3>
            <ul className="list-disc pl-6 space-y-2 mb-3">
              <li>Service interruptions or downtime</li>
              <li>Data loss (backup is your responsibility)</li>
              <li>Third-party service failures (ToyyibPay, Vercel, etc.)</li>
              <li>Restaurant operations (food quality, delivery, customer service)</li>
              <li>Lost profits or business opportunities</li>
              <li>GPS inaccuracies or technical limitations</li>
            </ul>

            <div className="bg-white p-4 rounded mt-4">
              <p className="font-bold text-lg">Liability Cap:</p>
              <p>BinaApp&apos;s total liability shall not exceed subscription fees paid in the preceding 12 months. For free accounts: limited to RM100.</p>
            </div>
          </section>

          {/* Section 17: Malaysian Law */}
          <section>
            <h2 className="text-xl font-semibold text-gray-900 mb-3">17. Governing Law & Disputes</h2>
            
            <p className="mb-3">These Terms governed by <strong>Malaysian law</strong>. Disputes resolved in Malaysian courts (Kuala Lumpur).</p>

            <h3 className="font-semibold text-gray-900 mt-4 mb-2">Informal Resolution First</h3>
            <p className="mb-2">Before legal action:</p>
            <ol className="list-decimal pl-6 space-y-1">
              <li>Contact support.team@binaapp.my</li>
              <li>Describe the dispute</li>
              <li>Allow 30 days for good-faith resolution</li>
            </ol>
          </section>

          {/* Section 18: Contact */}
          <section className="bg-gray-50 p-6 rounded">
            <h2 className="text-xl font-semibold text-gray-900 mb-3">18. Contact Information</h2>
            
            <div className="grid md:grid-cols-2 gap-4">
              <div>
                <p className="font-semibold">General Inquiries</p>
                <p className="text-sm">📧 <a href="mailto:info@binaapp.my" className="text-blue-600 underline">info@binaapp.my</a></p>
              </div>
              <div>
                <p className="font-semibold">Customer Support</p>
                <p className="text-sm">📧 <a href="mailto:support.team@binaapp.my" className="text-blue-600 underline">support.team@binaapp.my</a></p>
              </div>
              <div>
                <p className="font-semibold">Legal / Compliance</p>
                <p className="text-sm">📧 <a href="mailto:admin@binaapp.my" className="text-blue-600 underline">admin@binaapp.my</a></p>
              </div>
              <div>
                <p className="font-semibold">Data Protection (PDPA)</p>
                <p className="text-sm">📧 <a href="mailto:admin@binaapp.my" className="text-blue-600 underline">admin@binaapp.my</a></p>
                <p className="text-xs text-gray-600">Subject: &quot;PDPA Request&quot;</p>
              </div>
            </div>

            <div className="mt-6 pt-4 border-t">
              <p className="font-semibold">Business Name:</p>
              <p className="text-sm">Ezy Work Asia Solution</p>
              <p className="font-semibold mt-2">SSM Registration:</p>
              <p className="text-sm">002944700-D</p>
              <p className="font-semibold mt-2">Website:</p>
              <p className="text-sm"><a href="https://binaapp.my" className="text-blue-600 underline">https://binaapp.my</a></p>
            </div>
          </section>

          {/* Acceptance */}
          <section className="bg-green-50 border-2 border-green-600 p-6 rounded-lg">
            <h2 className="text-xl font-semibold text-green-900 mb-3">19. Acknowledgment & Acceptance</h2>
            
            <p className="mb-3 font-semibold">By creating an account or using BinaApp, you acknowledge:</p>
            <ul className="space-y-2">
              <li>✅ You have read and understood these Terms</li>
              <li>✅ You agree to be bound by these Terms</li>
              <li>✅ You have legal capacity to enter this agreement</li>
              <li>✅ You will comply with all applicable laws</li>
            </ul>

            <p className="mt-4 font-bold text-lg text-green-800">
              If you do not agree, you must NOT use BinaApp services.
            </p>
          </section>

          {/* Footer */}
          <section className="text-center text-sm text-gray-600 pt-6 border-t">
            <p className="mb-1">Last Updated: January 31, 2025</p>
            <p className="mb-1">Version: 2.0</p>
            <p className="mb-3">Effective Date: January 31, 2025</p>
            <p className="font-semibold">© 2025 Ezy Work Asia Solution. All rights reserved.</p>
            <p className="text-xs mt-1">BinaApp is a service of Ezy Work Asia Solution (SSM: 002944700-D)</p>
          </section>

        </div>
      </div>
    </div>
  )
}
