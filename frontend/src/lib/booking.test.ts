import { describe, it, expect, vi } from 'vitest'

// booking.ts imports apiFetch (auth, supabase) for the merchant half; the
// helpers under test are pure and never call it.
vi.mock('@/lib/api', () => ({ apiFetch: vi.fn() }))
vi.mock('@/lib/supabase', () => ({ ensureValidToken: vi.fn() }))

import {
  addDays,
  bookableDates,
  formatDateMs,
  formatDuration,
  formatPrice,
  formatTime12,
  groupByDate,
  hoursProblem,
  isPlausiblePhone,
  parseErrorBody,
  weekdayOf,
} from './booking'

describe('calendar helpers', () => {
  it('adds days across month and year ends', () => {
    expect(addDays('2026-11-30', 1)).toBe('2026-12-01')
    expect(addDays('2026-12-31', 1)).toBe('2027-01-01')
    expect(addDays('2028-02-28', 1)).toBe('2028-02-29')
  })

  it('knows the weekday of a date', () => {
    expect(weekdayOf('2026-11-16')).toBe('mon')
    expect(weekdayOf('2026-11-22')).toBe('sun')
  })
})

describe('bookableDates', () => {
  const info = {
    today: '2026-11-16',
    max_days_ahead: 7,
    open_weekdays: ['mon', 'tue', 'wed', 'thu', 'fri', 'sat'] as any,
    closed_dates: ['2026-11-18'],
  }

  it('covers today through max_days_ahead inclusive', () => {
    const dates = bookableDates(info)
    expect(dates).toHaveLength(8)
    expect(dates[0].date).toBe('2026-11-16')
    expect(dates[7].date).toBe('2026-11-23')
  })

  it('flags closed weekdays and closed dates', () => {
    const byDate = Object.fromEntries(bookableDates(info).map((d) => [d.date, d.closed]))
    expect(byDate['2026-11-16']).toBe(false)
    expect(byDate['2026-11-18']).toBe(true) // closed date
    expect(byDate['2026-11-22']).toBe(true) // Sunday
  })
})

describe('formatting', () => {
  it('formats dates in Malay', () => {
    expect(formatDateMs('2026-11-16')).toBe('Isnin, 16 Nov 2026')
    expect(formatDateMs('2026-03-01')).toBe('Ahad, 1 Mac 2026')
  })

  it('formats 12-hour times', () => {
    expect(formatTime12('09:00')).toBe('9:00 PG')
    expect(formatTime12('12:30')).toBe('12:30 PTG')
    expect(formatTime12('00:15')).toBe('12:15 PG')
    expect(formatTime12('14:05')).toBe('2:05 PTG')
    expect(formatTime12(null)).toBe('')
  })

  it('formats durations and prices', () => {
    expect(formatDuration(45)).toBe('45 minit')
    expect(formatDuration(60)).toBe('1 jam')
    expect(formatDuration(90)).toBe('1 jam 30 minit')
    expect(formatPrice(25)).toBe('RM25.00')
    expect(formatPrice(null)).toBe('')
  })
})

describe('validation', () => {
  it('accepts plausible phone numbers only', () => {
    expect(isPlausiblePhone('012-345 6789')).toBe(true)
    expect(isPlausiblePhone('+60 12 345 6789')).toBe(true)
    expect(isPlausiblePhone('12345')).toBe(false)
  })

  it('finds problems in opening hours', () => {
    expect(hoursProblem([{ open: '09:00', close: '18:00' }])).toBeNull()
    expect(hoursProblem([{ open: '18:00', close: '24:00' }])).toBeNull()
    expect(hoursProblem([{ open: '18:00', close: '09:00' }])).toMatch(/selepas/)
    expect(hoursProblem([{ open: '9', close: '18:00' }])).toMatch(/tidak sah/)
    expect(
      hoursProblem([
        { open: '14:00', close: '18:00' },
        { open: '09:00', close: '15:00' },
      ]),
    ).toMatch(/bertindih/)
  })
})

describe('groupByDate', () => {
  it('groups rows by date in ascending order', () => {
    const groups = groupByDate([
      { date: '2026-11-17', id: 'b' },
      { date: '2026-11-16', id: 'a' },
      { date: '2026-11-17', id: 'c' },
    ])
    expect(groups.map((g) => g.date)).toEqual(['2026-11-16', '2026-11-17'])
    expect(groups[1].rows.map((r) => r.id)).toEqual(['b', 'c'])
  })
})

describe('parseErrorBody', () => {
  it('reads the structured error the booking API sends', () => {
    expect(parseErrorBody({ detail: { error: 'SLOT_FULL', message: 'Penuh' } })).toEqual({
      message: 'Penuh',
      code: 'SLOT_FULL',
    })
  })

  it('handles plain strings, validation arrays and garbage', () => {
    expect(parseErrorBody({ detail: 'Bukan website anda' }).message).toBe('Bukan website anda')
    expect(parseErrorBody({ detail: [{ loc: ['body'] }] }).code).toBe('VALIDATION')
    expect(parseErrorBody(null).code).toBe('ERROR')
  })
})
