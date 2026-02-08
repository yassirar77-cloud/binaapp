import { NextResponse } from 'next/server'
import { supabaseAdmin } from '@/lib/supabase-admin'

export const dynamic = 'force-dynamic'

export async function GET() {
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

    // Run all queries in parallel
    const [
      usersRes,
      weekUsersRes,
      revenueRes,
      weekRevenueRes,
      websitesRes,
      failedWebsitesRes,
      errorsRes,
    ] = await Promise.all([
      // Total users
      supabaseAdmin.from('profiles').select('id', { count: 'exact', head: true }),
      // Users this week
      supabaseAdmin.from('profiles').select('id', { count: 'exact', head: true })
        .gte('created_at', startOfWeek),
      // Revenue this month (from transactions)
      supabaseAdmin.from('transactions').select('amount')
        .eq('payment_status', 'success')
        .gte('created_at', startOfMonth),
      // Revenue this week
      supabaseAdmin.from('transactions').select('amount')
        .eq('payment_status', 'success')
        .gte('created_at', startOfWeek),
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

    const totalUsers = usersRes.count ?? 0
    const weekUsers = weekUsersRes.count ?? 0

    const revenueMTD = (revenueRes.data ?? []).reduce((sum, t) => sum + (t.amount || 0), 0)
    const revenueWeek = (weekRevenueRes.data ?? []).reduce((sum, t) => sum + (t.amount || 0), 0)

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
    console.error('Stats API error:', error)
    return NextResponse.json({ error: 'Failed to fetch stats' }, { status: 500 })
  }
}
