import { describe, it, expect } from 'vitest'

import {
  buildHeatmapGrid,
  clampDaysForTier,
  deltaBadge,
  formatDayLabel,
  formatRM,
  heatmapOpacity,
  maxDaysForTier,
  requiredTierForDays,
} from './analytics'

describe('tier windows', () => {
  it('mirrors the backend clamp', () => {
    expect(maxDaysForTier('free')).toBe(7)
    expect(maxDaysForTier('starter')).toBe(7)
    expect(maxDaysForTier('basic')).toBe(30)
    expect(maxDaysForTier('pro')).toBe(90)
  })

  it('defaults unknown tiers to the smallest window', () => {
    expect(maxDaysForTier(undefined)).toBe(7)
    expect(maxDaysForTier(null)).toBe(7)
    expect(maxDaysForTier('mystery')).toBe(7)
  })

  it('clamps requested days', () => {
    expect(clampDaysForTier(90, 'starter')).toBe(7)
    expect(clampDaysForTier(90, 'basic')).toBe(30)
    expect(clampDaysForTier(90, 'pro')).toBe(90)
    expect(clampDaysForTier(0, 'pro')).toBe(1)
  })

  it('maps ranges to the plan that unlocks them', () => {
    expect(requiredTierForDays(7)).toBeNull()
    expect(requiredTierForDays(30)).toBe('basic')
    expect(requiredTierForDays(90)).toBe('pro')
  })
})

describe('formatting', () => {
  it('formats ringgit with two decimals', () => {
    expect(formatRM(0)).toContain('RM')
    expect(formatRM(1234.5)).toMatch(/1[,.]?234\.50/)
  })

  it('builds delta badges with direction + colour', () => {
    expect(deltaBadge(18)).toEqual({ text: '+18%', color: '#C7FF3D', icon: 'up' })
    expect(deltaBadge(-9.5)).toEqual({ text: '-9.5%', color: '#FF5A5F', icon: 'down' })
    expect(deltaBadge(0)?.icon).toBe('up')
  })

  it('returns no badge when there is no baseline', () => {
    expect(deltaBadge(null)).toBeUndefined()
    expect(deltaBadge(undefined)).toBeUndefined()
  })

  it('formats day labels without crashing on garbage', () => {
    expect(formatDayLabel('2026-07-03')).toBeTruthy()
    expect(formatDayLabel('garbage')).toBe('garbage')
  })
})

describe('heatmap shaping', () => {
  it('builds a 7x24 grid and tracks the max', () => {
    const grid = buildHeatmapGrid([
      { dow: 0, hour: 12, count: 5 },
      { dow: 6, hour: 23, count: 2 },
    ])
    expect(grid.rows).toHaveLength(7)
    expect(grid.rows[0]).toHaveLength(24)
    expect(grid.rows[0][12]).toBe(5)
    expect(grid.rows[6][23]).toBe(2)
    expect(grid.max).toBe(5)
  })

  it('ignores out-of-range cells', () => {
    const grid = buildHeatmapGrid([
      { dow: 9, hour: 12, count: 5 },
      { dow: 0, hour: 30, count: 5 },
    ])
    expect(grid.max).toBe(0)
  })

  it('handles empty input', () => {
    const grid = buildHeatmapGrid([])
    expect(grid.max).toBe(0)
    expect(grid.rows[3][3]).toBe(0)
  })

  it('keeps zero cells visually off and scales the rest', () => {
    expect(heatmapOpacity(0, 10)).toBe(0)
    expect(heatmapOpacity(10, 10)).toBe(1)
    expect(heatmapOpacity(5, 10)).toBeGreaterThan(0.15)
    expect(heatmapOpacity(5, 10)).toBeLessThan(1)
    expect(heatmapOpacity(3, 0)).toBe(0)
  })
})
