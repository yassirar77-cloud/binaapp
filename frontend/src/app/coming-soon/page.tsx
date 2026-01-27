'use client'

import { useState, FormEvent } from 'react'

export default function ComingSoonPage() {
  const [email, setEmail] = useState('')
  const [isSubmitted, setIsSubmitted] = useState(false)
  const [isLoading, setIsLoading] = useState(false)

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    setIsLoading(true)

    // For now, just log the email (no backend yet)
    console.log('Email submitted for notification:', email)

    // Simulate a brief delay
    await new Promise((resolve) => setTimeout(resolve, 500))

    setIsSubmitted(true)
    setIsLoading(false)
  }

  const features = [
    'Complete website builder for restaurants',
    'Real-time order management system',
    'GPS rider tracking & chat support',
    'AI-powered menu generation',
    'Integrated payment via ToyyibPay',
    '100% PDPA compliant & secure',
  ]

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-900 via-indigo-900 to-purple-800 flex flex-col items-center justify-center px-4 py-8 sm:py-12 relative overflow-hidden">
      {/* Background decorative elements */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-40 -right-40 w-80 h-80 bg-purple-500 rounded-full mix-blend-multiply filter blur-3xl opacity-20 animate-pulse" />
        <div className="absolute -bottom-40 -left-40 w-80 h-80 bg-indigo-500 rounded-full mix-blend-multiply filter blur-3xl opacity-20 animate-pulse" />
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-96 h-96 bg-purple-400 rounded-full mix-blend-multiply filter blur-3xl opacity-10" />
      </div>

      {/* Main content */}
      <div className="relative z-10 max-w-2xl w-full text-center">
        {/* Logo */}
        <div className="mb-6 sm:mb-8">
          <span className="text-6xl sm:text-7xl">&#127869;</span>
        </div>

        {/* Title */}
        <h1 className="text-3xl sm:text-4xl md:text-5xl font-bold text-white mb-4 leading-tight">
          BinaApp
        </h1>
        <p className="text-lg sm:text-xl text-purple-200 mb-6 sm:mb-8 px-4">
          Malaysia&apos;s Most Powerful Restaurant Delivery Platform
        </p>

        {/* Status Badge */}
        <div className="inline-flex items-center px-4 py-2 rounded-full bg-white/10 backdrop-blur-sm border border-white/20 mb-8 sm:mb-10">
          <span className="w-2 h-2 bg-green-400 rounded-full mr-2 animate-pulse" />
          <span className="text-sm sm:text-base text-white font-medium">
            Currently in Development - Launching Q1 2025
          </span>
        </div>

        {/* Email Signup Form */}
        <div className="mb-10 sm:mb-12 px-4">
          {!isSubmitted ? (
            <form onSubmit={handleSubmit} className="flex flex-col sm:flex-row gap-3 max-w-md mx-auto">
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="Enter your email"
                required
                className="flex-1 px-4 py-3 rounded-lg bg-white/10 backdrop-blur-sm border border-white/20 text-white placeholder-purple-300 focus:outline-none focus:ring-2 focus:ring-purple-400 focus:border-transparent transition-all"
              />
              <button
                type="submit"
                disabled={isLoading}
                className="px-6 py-3 bg-gradient-to-r from-purple-500 to-indigo-500 text-white font-semibold rounded-lg hover:from-purple-600 hover:to-indigo-600 focus:outline-none focus:ring-2 focus:ring-purple-400 focus:ring-offset-2 focus:ring-offset-purple-900 transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-lg shadow-purple-500/25"
              >
                {isLoading ? (
                  <span className="flex items-center justify-center">
                    <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    Sending...
                  </span>
                ) : (
                  'Notify Me'
                )}
              </button>
            </form>
          ) : (
            <div className="bg-green-500/20 backdrop-blur-sm border border-green-400/30 rounded-lg px-6 py-4 max-w-md mx-auto">
              <p className="text-green-300 font-medium flex items-center justify-center gap-2">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
                Thank you! We&apos;ll notify you when we launch.
              </p>
            </div>
          )}
        </div>

        {/* Features List */}
        <div className="bg-white/5 backdrop-blur-sm rounded-2xl border border-white/10 p-6 sm:p-8 mx-4 sm:mx-0">
          <h2 className="text-lg sm:text-xl font-semibold text-white mb-6">
            What&apos;s Coming
          </h2>
          <ul className="space-y-3 sm:space-y-4 text-left">
            {features.map((feature, index) => (
              <li key={index} className="flex items-start gap-3">
                <span className="flex-shrink-0 w-5 h-5 bg-gradient-to-r from-green-400 to-emerald-400 rounded-full flex items-center justify-center mt-0.5">
                  <svg className="w-3 h-3 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                  </svg>
                </span>
                <span className="text-purple-100 text-sm sm:text-base">{feature}</span>
              </li>
            ))}
          </ul>
        </div>

        {/* Footer */}
        <p className="mt-10 sm:mt-12 text-purple-300 text-sm">
          Built with <span className="text-red-400">&#10084;</span> in Malaysia
        </p>
      </div>

      {/* Hidden founder login link - bottom right corner */}
      <a
        href="/founder-login"
        className="absolute bottom-4 right-4 w-12 h-12 cursor-pointer opacity-0 hover:opacity-5 transition-opacity"
        aria-label="Founder access"
        title=""
      >
        <span className="sr-only">Founder Login</span>
      </a>
    </div>
  )
}
