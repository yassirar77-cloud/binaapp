import { NextRequest, NextResponse } from 'next/server'
import { supabaseAdmin } from '@/lib/supabase-admin'
import { requireFounder } from '@/lib/require-founder'
import { getRevenueRows, sumRows } from '@/lib/revenue-rows'
import { uniqueUuids } from '@/lib/uuid'

export const dynamic = 'force-dynamic'

export async function GET(request: NextRequest) {
  const denied = await requireFounder(request)
  if (denied) return denied

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

    // All rows (any status) from payments + transactions + addon_purchases,
    // newest first. Totals only count paid rows; the history shows every status.
    const allRows = (await getRevenueRows({ paidOnly: false }))
      .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
    const paid = allRows.filter(r => r.paid)

    console.log('[Revenue] rows:', allRows.length, 'paid:', paid.length)

    const recent = allRows.slice(0, 50)

    // Get user names for recent transactions
    const userIds = uniqueUuids(recent.map(t => t.user_id))
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

    // Revenue by plan type
    const byPlan: Record<string, number> = {}
    for (const r of paid) {
      byPlan[r.plan] = (byPlan[r.plan] || 0) + r.amount
    }

    const transactions = recent.map(t => ({
      id: t.id,
      amount: t.amount,
      description: t.description,
      type: t.source,
      status: t.status,
      created_at: t.created_at,
      user_name: (t.user_id && (profileMap[t.user_id]?.full_name || profileMap[t.user_id]?.business_name)) || 'Unknown',
    }))

    return NextResponse.json({
      today: sumRows(paid.filter(r => r.created_at >= startOfDay)),
      week: sumRows(paid.filter(r => r.created_at >= startOfWeek)),
      month: sumRows(paid.filter(r => r.created_at >= startOfMonth)),
      allTime: sumRows(paid),
      byPlan,
      transactions,
    })
  } catch (error) {
    console.error('[Revenue] API error:', error)
    return NextResponse.json({ error: 'Failed to fetch revenue' }, { status: 500 })
  }
}
