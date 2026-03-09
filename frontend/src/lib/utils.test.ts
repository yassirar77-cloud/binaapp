import { describe, it, expect } from 'vitest'
import { cn, sleep } from './utils'

describe('cn (class name joiner)', () => {
  it('joins multiple class names', () => {
    expect(cn('foo', 'bar', 'baz')).toBe('foo bar baz')
  })

  it('filters out falsy values', () => {
    expect(cn('foo', false, undefined, 'bar')).toBe('foo bar')
  })

  it('returns empty string for all falsy', () => {
    expect(cn(false, undefined)).toBe('')
  })

  it('handles single class', () => {
    expect(cn('only')).toBe('only')
  })

  it('handles empty call', () => {
    expect(cn()).toBe('')
  })
})

describe('sleep', () => {
  it('returns a promise', () => {
    const result = sleep(0)
    expect(result).toBeInstanceOf(Promise)
  })

  it('resolves after timeout', async () => {
    const start = Date.now()
    await sleep(50)
    const elapsed = Date.now() - start
    expect(elapsed).toBeGreaterThanOrEqual(40) // Allow small variance
  })
})
