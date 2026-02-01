'use client'

import { useState, useEffect, useRef } from 'react'
import Link from 'next/link'

interface UsageData {
  used: number
  limit: number | null
  percentage: number
  unlimited: boolean
  addon_credits: number
}

interface SubscriptionUsage {
  plan: {
    name: string
    status: string
    days_remaining: number
    end_date: string | null
    is_expired: boolean
  }
  usage: {
    websites: UsageData
    menu_items: UsageData
    ai_hero: UsageData
    ai_images: UsageData
    delivery_zones: UsageData
    riders: UsageData
  }
}

interface AnimatedUsageWidgetProps {
  subscription: SubscriptionUsage | null
  loading: boolean
  compact?: boolean
}

// Animated counter hook
function useAnimatedCounter(end: number, duration: number = 1000, start: number = 0) {
  const [count, setCount] = useState(start)
  const countRef = useRef(start)
  const frameRef = useRef<number>()

  useEffect(() => {
    const startTime = performance.now()
    const startValue = countRef.current

    const animate = (currentTime: number) => {
      const elapsed = currentTime - startTime
      const progress = Math.min(elapsed / duration, 1)

      // Easing function for smooth animation
      const easeOutQuart = 1 - Math.pow(1 - progress, 4)
      const current = Math.round(startValue + (end - startValue) * easeOutQuart)

      setCount(current)
      countRef.current = current

      if (progress < 1) {
        frameRef.current = requestAnimationFrame(animate)
      }
    }

    frameRef.current = requestAnimationFrame(animate)

    return () => {
      if (frameRef.current) {
        cancelAnimationFrame(frameRef.current)
      }
    }
  }, [end, duration])

  return count
}

// Single usage item with animated counter
function AnimatedUsageItem({
  icon,
  label,
  used,
  limit,
  unlimited,
  addon_credits,
  colorClass,
  gradientFrom,
  gradientTo
}: {
  icon: string
  label: string
  used: number
  limit: number | null
  unlimited: boolean
  addon_credits: number
  colorClass: string
  gradientFrom: string
  gradientTo: string
}) {
  const animatedUsed = useAnimatedCounter(used, 800)
  const total = unlimited ? null : (limit || 0) + addon_credits
  const percentage = total ? Math.min((used / total) * 100, 100) : 0
  const isOverLimit = total !== null && used > total
  const isNearLimit = total !== null && percentage >= 80 && !isOverLimit

  return (
    <div className="group">
      <div className="flex justify-between items-center mb-2">
        <div className="flex items-center gap-2">
          <span className="text-lg">{icon}</span>
          <span className="text-sm font-medium text-gray-700">{label}</span>
        </div>
        <div className="flex items-center gap-2">
          <span className={`text-sm font-bold ${
            isOverLimit ? 'text-red-500' : isNearLimit ? 'text-amber-500' : colorClass
          }`}>
            {animatedUsed}
            {!unlimited && <span className="text-gray-400 font-normal">/{total}</span>}
            {unlimited && <span className="text-gray-400 font-normal ml-1 text-xs">unlimited</span>}
          </span>
          {isOverLimit && <span className="text-red-500 animate-pulse">!</span>}
          {addon_credits > 0 && (
            <span className="text-xs bg-purple-100 text-purple-700 px-1.5 py-0.5 rounded-full">
              +{addon_credits}
            </span>
          )}
        </div>
      </div>

      {/* Animated progress bar */}
      <div className="relative h-2.5 bg-gray-100 rounded-full overflow-hidden">
        <div
          className={`absolute inset-y-0 left-0 rounded-full transition-all duration-1000 ease-out ${
            isOverLimit
              ? 'bg-gradient-to-r from-red-400 to-red-500'
              : isNearLimit
                ? 'bg-gradient-to-r from-amber-400 to-orange-500'
                : `bg-gradient-to-r ${gradientFrom} ${gradientTo}`
          }`}
          style={{
            width: unlimited ? '30%' : `${Math.min(percentage, 100)}%`,
            boxShadow: isOverLimit
              ? '0 0 8px rgba(239, 68, 68, 0.5)'
              : isNearLimit
                ? '0 0 8px rgba(245, 158, 11, 0.5)'
                : undefined
          }}
        />
        {/* Shimmer effect */}
        <div
          className="absolute inset-y-0 left-0 w-full bg-gradient-to-r from-transparent via-white/30 to-transparent animate-shimmer"
          style={{
            width: unlimited ? '30%' : `${Math.min(percentage, 100)}%`,
            animationDuration: '2s',
            animationIterationCount: 'infinite'
          }}
        />
      </div>
    </div>
  )
}

export default function AnimatedUsageWidget({
  subscription,
  loading,
  compact = false
}: AnimatedUsageWidgetProps) {
  const [isVisible, setIsVisible] = useState(false)
  const widgetRef = useRef<HTMLDivElement>(null)

  // Trigger animation when widget becomes visible
  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setIsVisible(true)
        }
      },
      { threshold: 0.1 }
    )

    if (widgetRef.current) {
      observer.observe(widgetRef.current)
    }

    return () => observer.disconnect()
  }, [])

  // Loading state
  if (loading) {
    return (
      <div className="bg-gradient-to-br from-gray-50 to-gray-100 rounded-xl border border-gray-200 p-6 animate-pulse">
        <div className="h-6 bg-gray-200 rounded w-1/3 mb-4"></div>
        <div className="space-y-4">
          {[1, 2, 3, 4].map(i => (
            <div key={i}>
              <div className="h-4 bg-gray-200 rounded w-full mb-2"></div>
              <div className="h-2 bg-gray-200 rounded w-full"></div>
            </div>
          ))}
        </div>
      </div>
    )
  }

  // No data state
  if (!subscription) {
    return (
      <div className="bg-gradient-to-br from-gray-50 to-gray-100 rounded-xl border border-gray-200 p-6 text-center">
        <span className="text-4xl mb-3 block">📊</span>
        <p className="text-gray-500 text-sm">Tidak dapat memuatkan data penggunaan</p>
        <button
          onClick={() => window.location.reload()}
          className="mt-3 text-blue-500 text-sm hover:underline"
        >
          Cuba semula
        </button>
      </div>
    )
  }

  const { plan, usage } = subscription
  const hasWarning = Object.values(usage).some(u => {
    const total = u.unlimited ? Infinity : (u.limit || 0) + u.addon_credits
    return u.used >= total
  })

  // Plan badge colors
  const planColors: Record<string, { bg: string, text: string, border: string }> = {
    starter: { bg: 'bg-blue-100', text: 'text-blue-700', border: 'border-blue-200' },
    basic: { bg: 'bg-emerald-100', text: 'text-emerald-700', border: 'border-emerald-200' },
    pro: { bg: 'bg-purple-100', text: 'text-purple-700', border: 'border-purple-200' },
    enterprise: { bg: 'bg-amber-100', text: 'text-amber-700', border: 'border-amber-200' }
  }
  const planStyle = planColors[plan.name.toLowerCase()] || planColors.starter

  return (
    <div
      ref={widgetRef}
      className={`bg-gradient-to-br from-slate-50 via-white to-blue-50 rounded-xl border border-gray-200 shadow-sm overflow-hidden transition-all duration-500 ${
        isVisible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'
      }`}
    >
      {/* Header */}
      <div className="px-6 py-4 bg-gradient-to-r from-slate-50 to-blue-50 border-b border-gray-100">
        <div className="flex justify-between items-center">
          <h3 className="text-lg font-semibold text-gray-800 flex items-center gap-2">
            <span className="text-xl">📊</span>
            Penggunaan
          </h3>
          <Link
            href="/dashboard/billing"
            className="text-blue-500 text-sm hover:text-blue-600 hover:underline transition-colors"
          >
            Urus Langganan →
          </Link>
        </div>
      </div>

      {/* Plan Badge */}
      <div className="px-6 pt-4 pb-2">
        <div className="flex items-center gap-3 flex-wrap">
          <span className={`px-4 py-1.5 ${planStyle.bg} ${planStyle.text} rounded-full font-bold text-sm border ${planStyle.border} shadow-sm`}>
            {plan.name.toUpperCase()}
          </span>
          <span className={`text-sm flex items-center gap-1 ${plan.is_expired ? 'text-red-500' : 'text-emerald-600'}`}>
            {plan.is_expired ? '❌' : '✅'}
            {plan.is_expired ? 'Tamat Tempoh' : 'Aktif'}
          </span>
          {!plan.is_expired && plan.days_remaining > 0 && plan.days_remaining <= 7 && (
            <span className="text-xs text-amber-600 bg-amber-50 px-2 py-1 rounded-full">
              {plan.days_remaining} hari lagi
            </span>
          )}
        </div>
      </div>

      {/* Usage Stats */}
      <div className="p-6 pt-4 space-y-4">
        <AnimatedUsageItem
          icon="🌐"
          label="Website"
          used={usage.websites.used}
          limit={usage.websites.limit}
          unlimited={usage.websites.unlimited}
          addon_credits={usage.websites.addon_credits}
          colorClass="text-blue-600"
          gradientFrom="from-blue-400"
          gradientTo="to-cyan-500"
        />

        <AnimatedUsageItem
          icon="📋"
          label="Menu Items"
          used={usage.menu_items.used}
          limit={usage.menu_items.limit}
          unlimited={usage.menu_items.unlimited}
          addon_credits={usage.menu_items.addon_credits}
          colorClass="text-emerald-600"
          gradientFrom="from-emerald-400"
          gradientTo="to-teal-500"
        />

        <AnimatedUsageItem
          icon="✨"
          label="AI Hero"
          used={usage.ai_hero.used}
          limit={usage.ai_hero.limit}
          unlimited={usage.ai_hero.unlimited}
          addon_credits={usage.ai_hero.addon_credits}
          colorClass="text-purple-600"
          gradientFrom="from-purple-400"
          gradientTo="to-pink-500"
        />

        <AnimatedUsageItem
          icon="🖼️"
          label="AI Images"
          used={usage.ai_images.used}
          limit={usage.ai_images.limit}
          unlimited={usage.ai_images.unlimited}
          addon_credits={usage.ai_images.addon_credits}
          colorClass="text-amber-600"
          gradientFrom="from-amber-400"
          gradientTo="to-orange-500"
        />

        {!compact && (
          <>
            <AnimatedUsageItem
              icon="📍"
              label="Zon Penghantaran"
              used={usage.delivery_zones.used}
              limit={usage.delivery_zones.limit}
              unlimited={usage.delivery_zones.unlimited}
              addon_credits={usage.delivery_zones.addon_credits}
              colorClass="text-rose-600"
              gradientFrom="from-rose-400"
              gradientTo="to-red-500"
            />

            <AnimatedUsageItem
              icon="🛵"
              label="Rider"
              used={usage.riders.used}
              limit={usage.riders.limit}
              unlimited={usage.riders.unlimited}
              addon_credits={usage.riders.addon_credits}
              colorClass="text-indigo-600"
              gradientFrom="from-indigo-400"
              gradientTo="to-violet-500"
            />
          </>
        )}
      </div>

      {/* Warning Banner */}
      {hasWarning && (
        <div className="mx-6 mb-4 p-3 bg-gradient-to-r from-red-50 to-amber-50 border border-red-200 rounded-lg">
          <p className="text-red-700 text-sm flex items-start gap-2">
            <span className="text-lg">⚠️</span>
            <span>Anda telah melebihi had penggunaan. Sila upgrade atau beli addon untuk terus menggunakan ciri-ciri ini.</span>
          </p>
        </div>
      )}

      {/* Action Buttons */}
      <div className="px-6 pb-6 flex gap-3">
        <Link
          href="/pricing"
          className="flex-1 py-2.5 bg-gradient-to-r from-blue-500 to-blue-600 text-white text-center rounded-lg text-sm font-semibold hover:from-blue-600 hover:to-blue-700 transition-all shadow-sm hover:shadow-md"
        >
          💎 Upgrade Plan
        </Link>
        <Link
          href="/dashboard/billing"
          className="flex-1 py-2.5 bg-white text-blue-600 text-center rounded-lg text-sm font-semibold border border-blue-200 hover:bg-blue-50 transition-all"
        >
          📄 Billing
        </Link>
      </div>

      {/* Shimmer animation styles */}
      <style jsx>{`
        @keyframes shimmer {
          0% { transform: translateX(-100%); }
          100% { transform: translateX(100%); }
        }
        .animate-shimmer {
          animation: shimmer 2s infinite;
        }
      `}</style>
    </div>
  )
}
