import { NextRequest, NextResponse } from 'next/server'
import { supabaseAdmin } from '@/lib/supabase-admin'
import { requireFounder } from '@/lib/require-founder'
import { getRevenueRows, sumRows } from '@/lib/revenue-rows'

export const dynamic = 'force-dynamic'

export async function GET(request: NextRequest) {
  const denied = await requireFounder(request)
  if (denied) return denied

  try {
    const now = new Date()
    const startOfMonth = new Date(now.getFullYear(), now.getMonth(), 1).toISOString()
    const startOfWeek = (() => {
      const d = new Date()
      const day = d.getDay()
      const diff = d.getDate() - day + (day === 0 ? -6 : 1)
      return new Date(d.setDate(diff)).toISOString().split('T')[0] + 'T00:00:00.000Z'
    })()
    const startOfDay = now.toISOString().split('T')[0] + 'T00:00:00.000Z'
    // Week may start before the month (e.g. month starts mid-week)
    const revenueSince = startOfWeek < startOfMonth ? startOfWeek : startOfMonth

    // Run all queries in parallel
    const [
      usersRes,
      weekUsersRes,
      revenueRows,
      websitesRes,
      failedWebsitesRes,
      errorsRes,
    ] = await Promise.all([
      // Total users
      supabaseAdmin.from('profiles').select('id', { count: 'exact', head: true }),
      // Users this week
      supabaseAdmin.from('profiles').select('id', { count: 'exact', head: true })
        .gte('created_at', startOfWeek),
      // Paid revenue rows (payments + transactions + addon_purchases)
      getRevenueRows({ since: revenueSince }),
      // Total websites
      supabaseAdmin.from('websites').select('id', { count: 'exact', head: true }),
      // Failed websites
      supabaseAdmin.from('websites').select('id', { count: 'exact', head: true })
        .eq('status', 'failed'),
      // Errors today (from generation_jobs)
      supabaseAdmin.from('generation_jobs').select('id, error', { count: 'exact' })
        .eq('status', 'failed')
        .gte('created_at', startOfDay),
    ])

    // Log each query result for debugging
    console.log('[Stats] profiles count:', usersRes.count, 'error:', usersRes.error?.message)
    console.log('[Stats] week profiles count:', weekUsersRes.count, 'error:', weekUsersRes.error?.message)
    console.log('[Stats] revenue rows:', revenueRows.length)
    console.log('[Stats] websites count:', websitesRes.count, 'error:', websitesRes.error?.message)
    console.log('[Stats] failed websites count:', failedWebsitesRes.count, 'error:', failedWebsitesRes.error?.message)
    console.log('[Stats] errors count:', errorsRes.count, 'error:', errorsRes.error?.message)

    const totalUsers = usersRes.count ?? 0
    const weekUsers = weekUsersRes.count ?? 0

    const revenueMTD = sumRows(revenueRows.filter(r => r.created_at >= startOfMonth))
    const revenueWeek = sumRows(revenueRows.filter(r => r.created_at >= startOfWeek))

    const totalWebsites = websitesRes.count ?? 0
    const failedWebsites = failedWebsitesRes.count ?? 0
    const successRate = totalWebsites > 0
      ? (((totalWebsites - failedWebsites) / totalWebsites) * 100).toFixed(1)
      : '0'

    const errorsToday = errorsRes.count ?? 0

    // Parse error types from generation_jobs errors
    const errorData = errorsRes.data ?? []
    const deepseekFails = errorData.filter(e => e.error?.toLowerCase().includes('deepseek')).length
    const qwenFails = errorData.filter(e => e.error?.toLowerCase().includes('qwen')).length

    return NextResponse.json({
      totalUsers,
      weekUsers,
      revenueMTD,
      revenueWeek,
      totalWebsites,
      successRate,
      errorsToday,
      deepseekFails,
      qwenFails,
    })
  } catch (error) {
    console.error('[Stats] API error:', error)
    return NextResponse.json({ error: 'Failed to fetch stats' }, { status: 500 })
  }
}
