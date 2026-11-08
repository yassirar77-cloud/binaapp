import { describe, it, expect } from 'vitest'
import {
  firstLineOf, gatePreviewFromStatus, gatePreviewLine, generateBlockedReason, looksLikeMenuPaste, portraitPoster,
  posterWarning, suggestSubdomain,
} from './createGuards'

describe('looksLikeMenuPaste', () => {
  it('a menu with prices on several lines is a menu', () => {
    expect(looksLikeMenuPaste('Nasi Lemak 5.50\nTeh Tarik RM2.50\nRoti Canai 1.50')).toBe(true)
    expect(looksLikeMenuPaste('Set Ayam: Set A – Ayam Gepuk 12.50 | Set B 13.50\nMinuman: Teh O Ice 3.00')).toBe(true)
  })
  it('a long unpriced list is a menu too', () => {
    expect(looksLikeMenuPaste('Nasi Lemak\nMee Goreng\nRoti Canai\nTeh Tarik')).toBe(true)
  })
  it('a single line, or a two-line name and tagline, is not', () => {
    expect(looksLikeMenuPaste('Ayam Gepuk Panglima')).toBe(false)
    expect(looksLikeMenuPaste('Ayam Gepuk Panglima\nSedap dan pedas')).toBe(false)
    expect(looksLikeMenuPaste('')).toBe(false)
  })
  it('firstLineOf gives the name', () => {
    expect(firstLineOf('  Ayam Gepuk Panglima \nSedap')).toBe('Ayam Gepuk Panglima')
    expect(firstLineOf('')).toBe('')
  })
})

describe('suggestSubdomain', () => {
  it('slugifies the business name with hyphens', () => {
    expect(suggestSubdomain('Ayam Gepuk Panglima')).toBe('ayam-gepuk-panglima')
    expect(suggestSubdomain("Kek Mak Teh's Bakery!")).toBe('kek-mak-teh-s-bakery')
    expect(suggestSubdomain('  Restoran   Bismillah Maju ')).toBe('restoran-bismillah-maju')
  })
  it('caps at 30 characters on a word boundary and never ends with a hyphen', () => {
    const s = suggestSubdomain('Restoran Nasi Kandar Daging Crystal Pelangi Indah')
    expect(s.length).toBeLessThanOrEqual(30)
    expect(s).toBe('restoran-nasi-kandar-daging')
    expect(s.endsWith('-')).toBe(false)
  })
  it('is empty for names too short to be a subdomain', () => {
    expect(suggestSubdomain('AB')).toBe('')
    expect(suggestSubdomain('')).toBe('')
  })
})

describe('poster guard', () => {
  it('a portrait upload is a poster', () => {
    expect(portraitPoster(800, 1400)).toBe(true)
    expect(portraitPoster(1600, 900)).toBe(false)
    expect(portraitPoster(0, 0)).toBe(false)
  })
  it('explains the right thing', () => {
    expect(posterWarning({ poster: false, portrait: false, text_heavy: false })).toBeNull()
    expect(posterWarning({ poster: true, portrait: true, text_heavy: false })).toMatch(/menegak/)
    expect(posterWarning({ poster: true, portrait: false, text_heavy: true })).toMatch(/papan menu/)
  })
})

describe('generateBlockedReason', () => {
  it('blocks a restaurant with no menu items', () => {
    expect(generateBlockedReason(0, 'food', 'Restoran kami')).toMatch(/sekurang-kurangnya satu item/)
    expect(generateBlockedReason(0, 'bakery', '')).not.toBeNull()
    expect(generateBlockedReason(0, 'auto', 'Kedai makan nasi ayam di Klang')).not.toBeNull()
  })
  it('lets a salon, a shop, or a restaurant with items through', () => {
    expect(generateBlockedReason(0, 'salon', 'Salon rambut')).toBeNull()
    expect(generateBlockedReason(0, 'auto', 'Kedai telefon dan aksesori')).toBeNull()
    expect(generateBlockedReason(3, 'food', 'Restoran')).toBeNull()
  })
})

describe('gate preview', () => {
  it('reads the status response', () => {
    const p = gatePreviewFromStatus({ preview_mobile_url: 'https://res.cloudinary.com/x/job-1-mobile.png', visual_gate: { passed: true, summary: 'pass', fixes: ['contrast_guard'], failed_checks: [] } })
    expect(p?.url).toMatch(/mobile\.png$/)
    expect(p?.passed).toBe(true)
    expect(gatePreviewLine(p)).toMatch(/lulus selepas pembetulan/)
    expect(gatePreviewLine(gatePreviewFromStatus({ visual_gate: { passed: false, summary: 'FAIL contrast_aa(2)', failed_checks: ['contrast_aa'], fixes: [] } }))).toMatch(/contrast_aa/)
  })
  it('is null when the job carried no gate', () => {
    expect(gatePreviewFromStatus({ status: 'completed' })).toBeNull()
    expect(gatePreviewFromStatus(null)).toBeNull()
    expect(gatePreviewLine(null)).toMatch(/tidak dijalankan/)
  })
})
