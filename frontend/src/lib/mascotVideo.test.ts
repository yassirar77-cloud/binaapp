import { describe, expect, it } from 'vitest'

import { clipProblem, isActive, MASCOT_PRESETS } from './mascotVideo'

const config = { min_clip_seconds: 2, max_clip_seconds: 10, max_clip_mb: 50 }
const mp4 = { type: 'video/mp4', size: 5 * 1024 * 1024 }

describe('clipProblem', () => {
  it('accepts a clip inside the limits', () => {
    expect(clipProblem(mp4, 8, config)).toBeNull()
    expect(clipProblem({ ...mp4, type: 'video/quicktime' }, 10.3, config)).toBeNull()
  })

  it('accepts a clip whose duration the browser could not read (the server checks)', () => {
    expect(clipProblem(mp4, null, config)).toBeNull()
  })

  it('refuses a clip over 10 seconds, too short, too big or the wrong format', () => {
    expect(clipProblem(mp4, 14, config)).toContain('terlalu panjang')
    expect(clipProblem(mp4, 1, config)).toContain('terlalu pendek')
    expect(clipProblem({ ...mp4, size: 51 * 1024 * 1024 }, 5, config)).toContain('terlalu besar')
    expect(clipProblem({ ...mp4, type: 'video/webm' }, 5, config)).toContain('MP4 atau MOV')
  })
})

describe('mascot video statuses', () => {
  it('polls only while a job is in flight', () => {
    expect(['queued', 'moderating', 'processing'].every((s) => isActive(s as any))).toBe(true)
    expect(['ready', 'rejected', 'failed'].some((s) => isActive(s as any))).toBe(false)
  })

  it('ships two preset mascots', () => {
    expect(MASCOT_PRESETS.map((m) => m.src)).toEqual([
      '/mascots/pakcik-teh-tarik.png',
      '/mascots/ayam-ceria.png',
    ])
  })
})
