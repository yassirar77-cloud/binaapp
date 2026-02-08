import { NextResponse } from 'next/server'
import { supabaseAdmin } from '@/lib/supabase-admin'

export const dynamic = 'force-dynamic'

export async function GET() {
  try {
    const now = new Date()
    const startOfDay = now.toISOString().split('T')[0] + 'T00:00:00.000Z'
    const startOfWeek = (() => {
      const d = new Date()
      const day = d.getDay()
      const diff = d.getDate() - day + (day === 0 ? -6 : 1)
      return new Date(d.setDate(diff)).toISOString().split('T')[0] + 'T00:00:00.000Z'
    })()
    const startOfMonth = new Date(now.getFullYear(), now.getMonth(), 1).toISOString()

    // Query payments table (replaces non-existent transactions table)
    // Also query addon_purchases for complete revenue
    const [allPayRes, todayPayRes, weekPayRes, monthPayRes, recentPayRes, allAddonRes, todayAddonRes, weekAddonRes, monthAddonRes, recentAddonRes] = await Promise.all([
      // All time payments
      supabaseAdmin.from('payments').select('amount, tier, type')
        .eq('status', 'paid'),
      // Today payments
      supabaseAdmin.from('payments').select('amount')
        .eq('status', 'paid')
        .gte('created_at', startOfDay),
      // This week payments
      supabaseAdmin.from('payments').select('amount')
        .eq('status', 'paid')
        .gte('created_at', startOfWeek),
      // This month payments
      supabaseAdmin.from('payments').select('amount')
        .eq('status', 'paid')
        .gte('created_at', startOfMonth),
      // Recent payments with details
      supabaseAdmin.from('payments').select('id, transaction_id, amount, tier, type, status, created_at, user_id')
        .order('created_at', { ascending: false })
        .limit(40),
      // All time addon purchases
      supabaseAdmin.from('addon_purchases').select('amount, addon_type')
        .eq('status', 'paid'),
      // Today addon purchases
      supabaseAdmin.from('addon_purchases').select('amount')
        .eq('status', 'paid')
        .gte('created_at', startOfDay),
      // This week addon purchases
      supabaseAdmin.from('addon_purchases').select('amount')
        .eq('status', 'paid')
        .gte('created_at', startOfWeek),
      // This month addon purchases
      supabaseAdmin.from('addon_purchases').select('amount')
        .eq('status', 'paid')
        .gte('created_at', startOfMonth),
      // Recent addon purchases with details
      supabaseAdmin.from('addon_purchases').select('id, transaction_id, amount, addon_type, status, created_at, user_id')
        .order('created_at', { ascending: false })
        .limit(10),
    ])

    // Log query results for debugging
    console.log('[Revenue] payments all:', allPayRes.data?.length, 'error:', allPayRes.error?.message)
    console.log('[Revenue] payments today:', todayPayRes.data?.length, 'error:', todayPayRes.error?.message)
    console.log('[Revenue] payments week:', weekPayRes.data?.length, 'error:', weekPayRes.error?.message)
    console.log('[Revenue] payments month:', monthPayRes.data?.length, 'error:', monthPayRes.error?.message)
    console.log('[Revenue] payments recent:', recentPayRes.data?.length, 'error:', recentPayRes.error?.message)
    console.log('[Revenue] addons all:', allAddonRes.data?.length, 'error:', allAddonRes.error?.message)
    console.log('[Revenue] addons recent:', recentAddonRes.data?.length, 'error:', recentAddonRes.error?.message)

    const sum = (data: { amount: number }[] | null) =>
      (data ?? []).reduce((s, t) => s + (Number(t.amount) || 0), 0)

    // Combine recent payments and addon purchases for the transaction list
    const allRecent = [
      ...(recentPayRes.data ?? []).map(p => ({
        ...p,
        source: 'payment' as const,
        description: p.tier ? `${p.tier} subscription` : (p.type || 'Subscription'),
      })),
      ...(recentAddonRes.data ?? []).map(a => ({
        ...a,
        source: 'addon' as const,
        description: `Add-on: ${a.addon_type || 'Unknown'}`,
      })),
    ].sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())

    // Get user names for recent transactions
    const userIds = [...new Set(allRecent.map(t => t.user_id).filter(Boolean))]
    let profileMap: Record<string, { full_name: string; business_name: string }> = {}

    if (userIds.length > 0) {
      const { data: profiles, error: profilesError } = await supabaseAdmin
        .from('profiles')
        .select('id, full_name, business_name')
        .in('id', userIds)

      console.log('[Revenue] profiles for users:', profiles?.length, 'error:', profilesError?.message)

      for (const p of profiles ?? []) {
        profileMap[p.id] = { full_name: p.full_name, business_name: p.business_name }
      }
    }

    // Revenue by plan type (from payments.tier column)
    const byPlan: Record<string, number> = {}
    for (const t of allPayRes.data ?? []) {
      const tier = t.tier?.toLowerCase() || 'other'
      let plan = 'other'
      if (tier.includes('starter')) plan = 'starter'
      else if (tier.includes('basic')) plan = 'basic'
      else if (tier.includes('pro')) plan = 'pro'
      else if (tier !== 'other') plan = tier
      byPlan[plan] = (byPlan[plan] || 0) + (Number(t.amount) || 0)
    }
    // Add addon revenue
    const addonTotal = sum(allAddonRes.data)
    if (addonTotal > 0) {
      byPlan['addon'] = addonTotal
    }

    const transactions = allRecent.slice(0, 50).map(t => ({
      id: t.transaction_id || t.id,
      amount: t.amount,
      description: t.description,
      type: t.source,
      status: t.status,
      created_at: t.created_at,
      user_name: profileMap[t.user_id]?.full_name || profileMap[t.user_id]?.business_name || 'Unknown',
    }))

    return NextResponse.json({
      today: sum(todayPayRes.data) + sum(todayAddonRes.data),
      week: sum(weekPayRes.data) + sum(weekAddonRes.data),
      month: sum(monthPayRes.data) + sum(monthAddonRes.data),
      allTime: sum(allPayRes.data) + sum(allAddonRes.data),
      byPlan,
      transactions,
    })
  } catch (error) {
    console.error('[Revenue] API error:', error)
    return NextResponse.json({ error: 'Failed to fetch revenue' }, { status: 500 })
  }
}
