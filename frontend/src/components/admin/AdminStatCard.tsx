'use client'

import React from 'react'

interface AdminStatCardProps {
  label: string
  value: string | number
  trend?: 'up' | 'down' | 'neutral'
  trendValue?: string
  color?: 'blue' | 'green' | 'red' | 'yellow' | 'purple' | 'gray'
  icon?: React.ReactNode
}

const COLOR_MAP = {
  blue: 'bg-blue-50 border-blue-200 text-blue-700',
  green: 'bg-green-50 border-green-200 text-green-700',
  red: 'bg-red-50 border-red-200 text-red-700',
  yellow: 'bg-yellow-50 border-yellow-200 text-yellow-700',
  purple: 'bg-purple-50 border-purple-200 text-purple-700',
  gray: 'bg-gray-50 border-gray-200 text-gray-700',
}

const TREND_COLORS = {
  up: 'text-green-600',
  down: 'text-red-600',
  neutral: 'text-gray-500',
}

export default function AdminStatCard({
  label,
  value,
  trend,
  trendValue,
  color = 'blue',
  icon,
}: AdminStatCardProps) {
  return (
    <div className={`border rounded-xl p-4 ${COLOR_MAP[color]}`}>
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs font-medium opacity-70 uppercase tracking-wide">{label}</p>
          <p className="text-2xl font-bold mt-1">{value}</p>
          {trend && trendValue && (
            <div className={`flex items-center gap-1 mt-1 text-xs ${TREND_COLORS[trend]}`}>
              {trend === 'up' && (
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                  <path d="M7 17l5-5 5 5M7 7l5 5 5-5" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
              )}
              {trend === 'down' && (
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                  <path d="M7 7l5 5 5-5M7 17l5-5 5 5" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
              )}
              <span>{trendValue}</span>
            </div>
          )}
        </div>
        {icon && (
          <div className="opacity-50">{icon}</div>
        )}
      </div>
    </div>
  )
}
