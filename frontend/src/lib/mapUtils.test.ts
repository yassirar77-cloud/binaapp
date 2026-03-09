import { describe, it, expect } from 'vitest'
import {
  calculateDistance,
  calculateDeliveryFee,
  formatDistance,
  formatDeliveryFee,
} from './mapUtils'

describe('calculateDistance (Haversine)', () => {
  it('returns 0 for same point', () => {
    expect(calculateDistance(3.1578, 101.7123, 3.1578, 101.7123)).toBe(0)
  })

  it('calculates KLCC to Bukit Bintang (~1.2km)', () => {
    const distance = calculateDistance(3.1578, 101.7123, 3.1478, 101.7056)
    expect(distance).toBeGreaterThan(0.5)
    expect(distance).toBeLessThan(2.0)
  })

  it('calculates KL to Penang (~300km)', () => {
    const distance = calculateDistance(3.1390, 101.6869, 5.4164, 100.3327)
    expect(distance).toBeGreaterThan(250)
    expect(distance).toBeLessThan(350)
  })

  it('returns positive value regardless of direction', () => {
    const d1 = calculateDistance(3.0, 101.0, 4.0, 102.0)
    const d2 = calculateDistance(4.0, 102.0, 3.0, 101.0)
    expect(d1).toBe(d2)
  })
})

describe('calculateDeliveryFee', () => {
  it('base fee only for <= 3km', () => {
    expect(calculateDeliveryFee(0)).toBe(3.0)
    expect(calculateDeliveryFee(1)).toBe(3.0)
    expect(calculateDeliveryFee(3)).toBe(3.0)
  })

  it('RM 1.00/km for 3-5km range', () => {
    // 4km = base 3.00 + (4-3)*1.00 = 4.00
    expect(calculateDeliveryFee(4)).toBe(4.0)
    // 5km = base 3.00 + 2*1.00 = 5.00
    expect(calculateDeliveryFee(5)).toBe(5.0)
  })

  it('RM 1.50/km for 5-10km range', () => {
    // 7km = base 3.00 + 2*1.00 + (7-5)*1.50 = 3 + 2 + 3 = 8.00
    expect(calculateDeliveryFee(7)).toBe(8.0)
    // 10km = base 3.00 + 2*1.00 + 5*1.50 = 3 + 2 + 7.5 = 12.50
    expect(calculateDeliveryFee(10)).toBe(12.5)
  })

  it('RM 2.00/km for 10km+ range', () => {
    // 12km = 3.00 + 2*1.00 + 5*1.50 + (12-10)*2.00 = 3 + 2 + 7.5 + 4 = 16.50
    expect(calculateDeliveryFee(12)).toBe(16.5)
  })

  it('handles zero distance', () => {
    expect(calculateDeliveryFee(0)).toBe(3.0)
  })
})

describe('formatDistance', () => {
  it('formats sub-kilometer as meters', () => {
    expect(formatDistance(0.5)).toBe('500 m')
    expect(formatDistance(0.1)).toBe('100 m')
  })

  it('formats kilometers with one decimal', () => {
    expect(formatDistance(1.0)).toBe('1.0 km')
    expect(formatDistance(5.5)).toBe('5.5 km')
    expect(formatDistance(12.34)).toBe('12.3 km')
  })
})

describe('formatDeliveryFee', () => {
  it('formats with RM prefix and 2 decimals', () => {
    expect(formatDeliveryFee(3)).toBe('RM 3.00')
    expect(formatDeliveryFee(12.5)).toBe('RM 12.50')
    expect(formatDeliveryFee(0)).toBe('RM 0.00')
  })
})
