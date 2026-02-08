import { NextResponse } from 'next/server'
import { supabaseAdmin } from '@/lib/supabase-admin'

export const dynamic = 'force-dynamic'

export async function GET() {
  try {
    const thirtyDaysAgo = new Date()
    thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30)
    const since = thirtyDaysAgo.toISOString()

    const [usersRes, paymentsRes, addonRes] = await Promise.all([
      supabaseAdmin.from('profiles').select('created_at')
        .gte('created_at', since)
        .order('created_at', { ascending: true }),
      // Use payments table instead of transactions
      supabaseAdmin.from('payments').select('amount, created_at')
        .eq('status', 'paid')
        .gte('created_at', since)
        .order('created_at', { ascending: true }),
      // Also include addon_purchases for complete revenue picture
      supabaseAdmin.from('addon_purchases').select('amount, created_at')
        .eq('status', 'paid')
        .gte('created_at', since)
        .order('created_at', { ascending: true }),
    ])

    // Log query results for debugging
    console.log('[Charts] profiles rows:', usersRes.data?.length, 'error:', usersRes.error?.message)
    console.log('[Charts] payments rows:', paymentsRes.data?.length, 'error:', paymentsRes.error?.message)
    console.log('[Charts] addon_purchases rows:', addonRes.data?.length, 'error:', addonRes.error?.message)

    // Group users by day
    const usersByDay: Record<string, number> = {}
    for (const u of usersRes.data ?? []) {
      const day = u.created_at.split('T')[0]
      usersByDay[day] = (usersByDay[day] || 0) + 1
    }

    // Group revenue by day (combine payments + addon_purchases)
    const revenueByDay: Record<string, number> = {}
    for (const t of paymentsRes.data ?? []) {
      const day = t.created_at.split('T')[0]
      revenueByDay[day] = (revenueByDay[day] || 0) + (Number(t.amount) || 0)
    }
    for (const t of addonRes.data ?? []) {
      const day = t.created_at.split('T')[0]
      revenueByDay[day] = (revenueByDay[day] || 0) + (Number(t.amount) || 0)
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
    console.error('[Charts] API error:', error)
    return NextResponse.json({ error: 'Failed to fetch chart data' }, { status: 500 })
  }
}
