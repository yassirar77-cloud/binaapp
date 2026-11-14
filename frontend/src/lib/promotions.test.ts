import { describe, expect, it } from 'vitest'
import {
  EMPTY_VOUCHER_FORM,
  endOfDayMalaysia,
  errorMessage,
  loyaltySummary,
  normalizeVoucherCode,
  usageText,
  voucherFormProblem,
  voucherPayload,
  voucherState,
  type Voucher,
  type VoucherForm,
} from './promotions'

const form = (over: Partial<VoucherForm> = {}): VoucherForm => ({
  ...EMPTY_VOUCHER_FORM,
  code: 'RAYA15',
  discount_value: '15',
  ...over,
})

const voucher = (over: Partial<Voucher> = {}): Voucher => ({
  id: 'v1', website_id: 'w1', code: 'RAYA15', description: '', discount_type: 'percent',
  discount_value: 15, max_discount: null, min_order: 0, starts_at: null, expires_at: null,
  usage_limit: null, per_customer_limit: null, used_count: 0, is_active: true, summary: '',
  ...over,
})

describe('voucher form', () => {
  it('normalises codes the way the server does', () => {
    expect(normalizeVoucherCode(' raya-15 ')).toBe('RAYA15')
  })

  it('accepts a minimal valid voucher', () => {
    expect(voucherFormProblem(form())).toBeNull()
  })

  it.each([
    [{ code: 'A' }, /3–20/],
    [{ code: 'KOD PROMO!' }, /3–20/],
    [{ discount_value: '' }, /nilai diskaun/],
    [{ discount_value: '0' }, /nilai diskaun/],
    [{ discount_value: '150' }, /1 hingga 100/],
    [{ min_order: 'abc' }, /Pesanan minimum/],
    [{ usage_limit: '2.5' }, /nombor bulat/],
    [{ usage_limit: '0' }, /sekurang-kurangnya 1/],
  ])('rejects %j', (over, message) => {
    expect(voucherFormProblem(form(over as Partial<VoucherForm>))).toMatch(message)
  })

  it('allows more than RM100 off for a fixed voucher', () => {
    expect(voucherFormProblem(form({ discount_type: 'fixed', discount_value: '150' }))).toBeNull()
  })

  it('builds the request body, dropping a cap from a fixed voucher', () => {
    expect(
      voucherPayload(form({
        code: 'rm5-off', discount_type: 'fixed', discount_value: '5', max_discount: '3',
        min_order: '20', usage_limit: '50', once_per_customer: true,
      }))
    ).toEqual({
      code: 'RM5OFF', description: '', discount_type: 'fixed', discount_value: 5,
      max_discount: null, min_order: 20, expires_at: null, usage_limit: 50,
      per_customer_limit: 1,
    })
  })

  it('accepts a comma as the decimal separator', () => {
    expect(voucherPayload(form({ discount_value: '7,5' })).discount_value).toBe(7.5)
  })

  it('expires at the end of the chosen day in Malaysia, not UTC', () => {
    // 23:59:59 on 30 Nov in UTC+8 is 15:59:59 UTC the same day.
    expect(endOfDayMalaysia('2026-11-30')).toBe('2026-11-30T15:59:59.000Z')
    expect(voucherPayload(form({ expires_on: '2026-11-30' })).expires_at).toBe(
      '2026-11-30T15:59:59.000Z'
    )
  })
})

describe('voucher state', () => {
  const now = new Date('2026-11-14T04:00:00Z')

  it('reports why a voucher cannot be used', () => {
    expect(voucherState(voucher(), now)).toBe('active')
    expect(voucherState(voucher({ is_active: false }), now)).toBe('paused')
    expect(voucherState(voucher({ expires_at: '2026-11-14T03:59:59Z' }), now)).toBe('expired')
    expect(voucherState(voucher({ usage_limit: 5, used_count: 5 }), now)).toBe('used_up')
    expect(voucherState(voucher({ starts_at: '2026-12-01T00:00:00Z' }), now)).toBe('scheduled')
  })

  it('paused wins over everything: it is the one state the merchant chose', () => {
    expect(
      voucherState(voucher({ is_active: false, expires_at: '2020-01-01T00:00:00Z' }), now)
    ).toBe('paused')
  })

  it('describes usage with and without a limit', () => {
    expect(usageText(voucher({ used_count: 3, usage_limit: 50 }))).toBe('3 / 50 ditebus')
    expect(usageText(voucher({ used_count: 3 }))).toBe('3 ditebus')
  })
})

describe('loyalty summary', () => {
  it('says what a customer has to spend to earn a reward', () => {
    expect(
      loyaltySummary({ enabled: true, points_per_rm: 2, redeem_points: 100, redeem_value: 5 })
    ).toBe('Pelanggan dapat 2 mata bagi setiap RM1. 100 mata = RM5.00 diskaun (selepas belanja kira-kira RM50).')
  })
})

describe('API error text', () => {
  it('reads every shape FastAPI sends', () => {
    expect(errorMessage({ detail: 'Kod RAYA15 sudah wujud' }, 'x')).toBe('Kod RAYA15 sudah wujud')
    expect(errorMessage({ detail: [{ msg: 'Value error, Kod mesti 3–20 huruf' }] }, 'x')).toBe(
      'Kod mesti 3–20 huruf'
    )
    expect(errorMessage({ detail: { message: 'Bukan website anda' } }, 'x')).toBe('Bukan website anda')
    expect(errorMessage(null, 'Ralat')).toBe('Ralat')
  })
})
