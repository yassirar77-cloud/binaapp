import { supabaseAdmin } from './supabase-admin'

/**
 * Unified revenue rows across the three tables the backend writes money to:
 *  - payments        (legacy subscribe flow; status pending -> 'successful')
 *  - transactions    (subscription/upgrade/renewal flow; payment_status 'success')
 *  - addon_purchases (credits granted after payment; status 'active'/'depleted',
 *                     price in total_price, legacy rows in amount)
 *
 * De-duplication: a transaction whose toyyibpay_bill_code matches a payments
 * bill_code is dropped (same bill), and an addon_purchase linked (transaction_id)
 * to a successful transaction is dropped (the transaction is the money record).
 */

export const PAID_PAYMENT_STATUSES = ['paid', 'successful', 'success']
export const ACTIVE_ADDON_STATUSES = ['active', 'depleted']

export type RevenueRow = {
  id: string
  source: 'payment' | 'transaction' | 'addon'
  amount: number
  created_at: string
  user_id: string | null
  description: string
  plan: string
  status: string
  paid: boolean
}

function planFromTier(tier: string | null | undefined): string {
  const t = (tier || '').toLowerCase()
  if (!t) return 'other'
  if (t.includes('starter')) return 'starter'
  if (t.includes('basic')) return 'basic'
  if (t.includes('pro')) return 'pro'
  return t
}

export async function getRevenueRows(opts: { since?: string; paidOnly?: boolean } = {}): Promise<RevenueRow[]> {
  const { since, paidOnly = true } = opts

  let payQ = supabaseAdmin.from('payments')
    .select('id, bill_code, transaction_id, amount, tier, type, status, created_at, user_id')
  let txnQ = supabaseAdmin.from('transactions')
    .select('transaction_id, user_id, transaction_type, item_description, amount, toyyibpay_bill_code, payment_status, metadata, created_at')
  let addonQ = supabaseAdmin.from('addon_purchases')
    .select('id, transaction_id, amount, total_price, addon_type, status, created_at, user_id')

  if (paidOnly) {
    payQ = payQ.in('status', PAID_PAYMENT_STATUSES)
    txnQ = txnQ.eq('payment_status', 'success')
    addonQ = addonQ.in('status', ACTIVE_ADDON_STATUSES)
  }
  if (since) {
    payQ = payQ.gte('created_at', since)
    txnQ = txnQ.gte('created_at', since)
    addonQ = addonQ.gte('created_at', since)
  }

  const [payRes, txnRes, addonRes] = await Promise.all([payQ, txnQ, addonQ])

  if (payRes.error) console.log('[Revenue] payments error:', payRes.error.message)
  if (txnRes.error) console.log('[Revenue] transactions error:', txnRes.error.message)
  if (addonRes.error) console.log('[Revenue] addon_purchases error:', addonRes.error.message)

  const payments = payRes.data ?? []
  const transactions = txnRes.data ?? []
  const addons = addonRes.data ?? []

  const billCodes = new Set(payments.map(p => p.bill_code).filter(Boolean))
  const dedupedTxns = transactions.filter(t => !t.toyyibpay_bill_code || !billCodes.has(t.toyyibpay_bill_code))
  const successTxnIds = new Set(
    dedupedTxns.filter(t => t.payment_status === 'success').map(t => t.transaction_id)
  )
  const dedupedAddons = addons.filter(a => !a.transaction_id || !successTxnIds.has(a.transaction_id))

  const rows: RevenueRow[] = []

  for (const p of payments) {
    rows.push({
      id: `pay-${p.id}`,
      source: 'payment',
      amount: Number(p.amount) || 0,
      created_at: p.created_at,
      user_id: p.user_id,
      description: p.tier ? `${p.tier} subscription` : (p.type || 'Subscription'),
      plan: planFromTier(p.tier),
      status: p.status,
      paid: PAID_PAYMENT_STATUSES.includes(p.status),
    })
  }

  for (const t of dedupedTxns) {
    const meta = (t.metadata ?? {}) as Record<string, unknown>
    const isAddon = (t.transaction_type || '').toLowerCase().includes('addon')
    const planHint = typeof meta.plan === 'string' ? meta.plan : t.item_description
    rows.push({
      id: `txn-${t.transaction_id}`,
      source: 'transaction',
      amount: Number(t.amount) || 0,
      created_at: t.created_at,
      user_id: t.user_id,
      description: t.item_description || t.transaction_type || 'Transaction',
      plan: isAddon ? 'addon' : planFromTier(planHint),
      status: t.payment_status,
      paid: t.payment_status === 'success',
    })
  }

  for (const a of dedupedAddons) {
    rows.push({
      id: `addon-${a.id}`,
      source: 'addon',
      amount: Number(a.total_price ?? a.amount) || 0,
      created_at: a.created_at,
      user_id: a.user_id,
      description: `Add-on: ${a.addon_type || 'Unknown'}`,
      plan: 'addon',
      status: a.status,
      paid: ACTIVE_ADDON_STATUSES.includes(a.status),
    })
  }

  return rows
}

export const sumRows = (rows: RevenueRow[]) => rows.reduce((s, r) => s + r.amount, 0)
