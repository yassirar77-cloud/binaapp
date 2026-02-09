'use client'

import React from 'react'

interface HealthScoreCardProps {
  overallScore: number
  designScore: number
  performanceScore: number
  contentScore: number
  mobileScore: number
  totalIssues: number
  lastScan?: string
  websiteName?: string
  onClick?: () => void
}

function getScoreColor(score: number): string {
  if (score >= 80) return '#22c55e'
  if (score >= 50) return '#eab308'
  return '#ef4444'
}

function getScoreBg(score: number): string {
  if (score >= 80) return 'bg-green-50 border-green-200'
  if (score >= 50) return 'bg-yellow-50 border-yellow-200'
  return 'bg-red-50 border-red-200'
}

function getScoreLabel(score: number): string {
  if (score >= 80) return 'Baik'
  if (score >= 50) return 'Sederhana'
  return 'Perlu Perhatian'
}

export default function HealthScoreCard({
  overallScore,
  designScore,
  performanceScore,
  contentScore,
  mobileScore,
  totalIssues,
  lastScan,
  websiteName,
  onClick,
}: HealthScoreCardProps) {
  const color = getScoreColor(overallScore)
  const radius = 40
  const circumference = 2 * Math.PI * radius
  const strokeDashoffset = circumference - (overallScore / 100) * circumference

  const categories = [
    { label: 'Reka Bentuk', score: designScore },
    { label: 'Prestasi', score: performanceScore },
    { label: 'Kandungan', score: contentScore },
    { label: 'Mudah Alih', score: mobileScore },
  ]

  return (
    <div
      className={`border rounded-xl p-5 cursor-pointer transition-all hover:shadow-md ${getScoreBg(overallScore)}`}
      onClick={onClick}
    >
      {websiteName && (
        <h3 className="font-semibold text-gray-800 mb-3 truncate">{websiteName}</h3>
      )}

      <div className="flex items-center gap-5">
        {/* Circular progress */}
        <div className="relative flex-shrink-0">
          <svg width="100" height="100" viewBox="0 0 100 100">
            <circle
              cx="50"
              cy="50"
              r={radius}
              fill="none"
              stroke="#e5e7eb"
              strokeWidth="8"
            />
            <circle
              cx="50"
              cy="50"
              r={radius}
              fill="none"
              stroke={color}
              strokeWidth="8"
              strokeLinecap="round"
              strokeDasharray={circumference}
              strokeDashoffset={strokeDashoffset}
              transform="rotate(-90 50 50)"
              style={{ transition: 'stroke-dashoffset 0.5s ease' }}
            />
          </svg>
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span className="text-2xl font-bold" style={{ color }}>{overallScore}</span>
            <span className="text-[10px] text-gray-500">{getScoreLabel(overallScore)}</span>
          </div>
        </div>

        {/* Category bars */}
        <div className="flex-1 space-y-2">
          {categories.map((cat) => (
            <div key={cat.label}>
              <div className="flex justify-between text-xs text-gray-600 mb-0.5">
                <span>{cat.label}</span>
                <span>{cat.score}%</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-1.5">
                <div
                  className="h-1.5 rounded-full transition-all"
                  style={{
                    width: `${cat.score}%`,
                    backgroundColor: getScoreColor(cat.score),
                  }}
                />
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Footer */}
      <div className="flex items-center justify-between mt-3 pt-3 border-t border-gray-200">
        {totalIssues > 0 ? (
          <span className="text-xs font-medium text-red-600 bg-red-100 px-2 py-0.5 rounded-full">
            {totalIssues} isu ditemui
          </span>
        ) : (
          <span className="text-xs font-medium text-green-600 bg-green-100 px-2 py-0.5 rounded-full">
            Tiada isu
          </span>
        )}
        {lastScan && (
          <span className="text-xs text-gray-400">
            {new Date(lastScan).toLocaleDateString('ms-MY', {
              day: 'numeric',
              month: 'short',
              hour: '2-digit',
              minute: '2-digit',
            })}
          </span>
        )}
      </div>
    </div>
  )
}
