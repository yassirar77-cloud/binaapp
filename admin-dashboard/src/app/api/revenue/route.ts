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

    const [allRes, todayRes, weekRes, monthRes, recentRes] = await Promise.all([
      // All time
      supabaseAdmin.from('transactions').select('amount')
        .eq('payment_status', 'success'),
      // Today
      supabaseAdmin.from('transactions').select('amount')
        .eq('payment_status', 'success')
        .gte('created_at', startOfDay),
      // This week
      supabaseAdmin.from('transactions').select('amount')
        .eq('payment_status', 'success')
        .gte('created_at', startOfWeek),
      // This month
      supabaseAdmin.from('transactions').select('amount')
        .eq('payment_status', 'success')
        .gte('created_at', startOfMonth),
      // Recent transactions with user info
      supabaseAdmin.from('transactions').select(`
        transaction_id, amount, item_description, transaction_type,
        payment_status, created_at, user_id
      `)
        .order('created_at', { ascending: false })
        .limit(50),
    ])

    const sum = (data: { amount: number }[] | null) =>
      (data ?? []).reduce((s, t) => s + (t.amount || 0), 0)

    // Get user names for recent transactions
    const userIds = [...new Set((recentRes.data ?? []).map(t => t.user_id).filter(Boolean))]
    const { data: profiles } = await supabaseAdmin
      .from('profiles')
      .select('id, full_name, business_name')
      .in('id', userIds.length > 0 ? userIds : ['none'])

    const profileMap: Record<string, { full_name: string; business_name: string }> = {}
    for (const p of profiles ?? []) {
      profileMap[p.id] = { full_name: p.full_name, business_name: p.business_name }
    }

    // Revenue by plan type
    const byPlan: Record<string, number> = {}
    for (const t of allRes.data ?? []) {
      // Determine plan from item_description
      const desc = (t as { item_description?: string }).item_description?.toLowerCase() || ''
      let plan = 'other'
      if (desc.includes('starter')) plan = 'starter'
      else if (desc.includes('basic')) plan = 'basic'
      else if (desc.includes('pro')) plan = 'pro'
      else if (desc.includes('addon') || desc.includes('add-on')) plan = 'addon'
      byPlan[plan] = (byPlan[plan] || 0) + (t.amount || 0)
    }

    const transactions = (recentRes.data ?? []).map(t => ({
      id: t.transaction_id,
      amount: t.amount,
      description: t.item_description,
      type: t.transaction_type,
      status: t.payment_status,
      created_at: t.created_at,
      user_name: profileMap[t.user_id]?.full_name || profileMap[t.user_id]?.business_name || 'Unknown',
    }))

    return NextResponse.json({
      today: sum(todayRes.data),
      week: sum(weekRes.data),
      month: sum(monthRes.data),
      allTime: sum(allRes.data),
      byPlan,
      transactions,
    })
  } catch (error) {
    console.error('Revenue API error:', error)
    return NextResponse.json({ error: 'Failed to fetch revenue' }, { status: 500 })
  }
}
