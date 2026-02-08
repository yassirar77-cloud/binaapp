import { NextResponse } from 'next/server'
import { supabaseAdmin } from '@/lib/supabase-admin'

export const dynamic = 'force-dynamic'

export async function GET() {
  try {
    const thirtyDaysAgo = new Date()
    thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30)
    const since = thirtyDaysAgo.toISOString()

    const [usersRes, transactionsRes] = await Promise.all([
      supabaseAdmin.from('profiles').select('created_at')
        .gte('created_at', since)
        .order('created_at', { ascending: true }),
      supabaseAdmin.from('transactions').select('amount, created_at')
        .eq('payment_status', 'success')
        .gte('created_at', since)
        .order('created_at', { ascending: true }),
    ])

    // Group users by day
    const usersByDay: Record<string, number> = {}
    for (const u of usersRes.data ?? []) {
      const day = u.created_at.split('T')[0]
      usersByDay[day] = (usersByDay[day] || 0) + 1
    }

    // Group revenue by day
    const revenueByDay: Record<string, number> = {}
    for (const t of transactionsRes.data ?? []) {
      const day = t.created_at.split('T')[0]
      revenueByDay[day] = (revenueByDay[day] || 0) + (t.amount || 0)
    }

    // Generate full 30 day range
    const days: string[] = []
    for (let i = 29; i >= 0; i--) {
      const d = new Date()
      d.setDate(d.getDate() - i)
      days.push(d.toISOString().split('T')[0])
    }

    const signupChart = days.map(day => ({
      date: day,
      label: new Date(day).toLocaleDateString('en-MY', { day: 'numeric', month: 'short' }),
      count: usersByDay[day] || 0,
    }))

    const revenueChart = days.map(day => ({
      date: day,
      label: new Date(day).toLocaleDateString('en-MY', { day: 'numeric', month: 'short' }),
      amount: revenueByDay[day] || 0,
    }))

    return NextResponse.json({ signupChart, revenueChart })
  } catch (error) {
    console.error('Charts API error:', error)
    return NextResponse.json({ error: 'Failed to fetch chart data' }, { status: 500 })
  }
}
