'use client'

import { ReactElement } from 'react'

interface BarPoint {
  value: number
  label?: string
}

interface SparklineProps {
  points: BarPoint[]
  color?: string
  highlightColor?: string
  width?: number
  height?: number
}

export default function Sparkline({
  points,
  color = '#4F3DFF',
  highlightColor = '#C7FF3D',
  width = 140,
  height = 44,
}: SparklineProps): ReactElement {
  const max = Math.max(...points.map((p) => p.value))
  const barW = width / points.length - 2

  return (
    <svg width={width} height={height} className="block">
      {points.map((p, i) => {
        const bh = max > 0 ? (p.value / max) * height * 0.95 : 0
        const isLast = i === points.length - 1
        return (
          <rect
            key={i}
            x={i * (barW + 2)}
            y={height - bh}
            width={barW}
            height={bh}
            rx={2}
            fill={isLast ? highlightColor : color}
            opacity={isLast ? 1 : 0.55}
          />
        )
      })}
    </svg>
  )
}
