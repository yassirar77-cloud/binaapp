import { NextResponse } from 'next/server'
import { supabaseAdmin } from '@/lib/supabase-admin'

export const dynamic = 'force-dynamic'

type ActivityItem = {
  id: string
  type: 'user' | 'website' | 'error' | 'payment' | 'generation'
  message: string
  detail: string
  created_at: string
  severity?: 'info' | 'success' | 'warning' | 'error'
}

export async function GET() {
  try {
    const oneHourAgo = new Date(Date.now() - 60 * 60 * 1000).toISOString()

    const [usersRes, websitesRes, jobsRes, transactionsRes] = await Promise.all([
      // Recent user registrations
      supabaseAdmin.from('profiles')
        .select('id, full_name, created_at')
        .gte('created_at', oneHourAgo)
        .order('created_at', { ascending: false })
        .limit(20),
      // Recent website changes
      supabaseAdmin.from('websites')
        .select('id, business_name, subdomain, status, created_at, updated_at, user_id, profiles!left(full_name)')
        .gte('updated_at', oneHourAgo)
        .order('updated_at', { ascending: false })
        .limit(20),
      // Recent generation jobs
      supabaseAdmin.from('generation_jobs')
        .select('id, job_id, status, error, user_id, description, created_at, updated_at')
        .gte('created_at', oneHourAgo)
        .order('created_at', { ascending: false })
        .limit(20),
      // Recent transactions
      supabaseAdmin.from('transactions')
        .select('transaction_id, amount, item_description, payment_status, created_at, user_id')
        .gte('created_at', oneHourAgo)
        .order('created_at', { ascending: false })
        .limit(20),
    ])

    // Get user names
    const allUserIds = [
      ...(jobsRes.data ?? []).map(j => j.user_id),
      ...(transactionsRes.data ?? []).map(t => t.user_id),
    ].filter(Boolean)
    const uniqueIds = [...new Set(allUserIds)]

    const { data: profiles } = await supabaseAdmin
      .from('profiles')
      .select('id, full_name')
      .in('id', uniqueIds.length > 0 ? uniqueIds : ['none'])

    const nameMap: Record<string, string> = {}
    for (const p of profiles ?? []) {
      nameMap[p.id] = p.full_name || 'Unknown'
    }

    const activities: ActivityItem[] = []

    // User registrations
    for (const u of usersRes.data ?? []) {
      activities.push({
        id: `user-${u.id}`,
        type: 'user',
        message: 'New user registered',
        detail: u.full_name || 'Unknown user',
        created_at: u.created_at,
        severity: 'success',
      })
    }

    // Website changes
    for (const w of websitesRes.data ?? []) {
      const profile = Array.isArray(w.profiles) ? w.profiles[0] : w.profiles
      const owner = profile?.full_name || 'Unknown'

      if (w.status === 'published') {
        activities.push({
          id: `web-${w.id}`,
          type: 'website',
          message: 'Website published',
          detail: `${w.subdomain}.binaapp.my by ${owner}`,
          created_at: w.updated_at || w.created_at,
          severity: 'success',
        })
      } else if (w.status === 'generating') {
        activities.push({
          id: `web-gen-${w.id}`,
          type: 'generation',
          message: 'Website generating...',
          detail: `For ${owner} (${w.business_name || w.subdomain})`,
          created_at: w.updated_at || w.created_at,
          severity: 'info',
        })
      } else if (w.status === 'failed') {
        activities.push({
          id: `web-fail-${w.id}`,
          type: 'error',
          message: 'Website generation failed',
          detail: `${w.business_name || w.subdomain} by ${owner}`,
          created_at: w.updated_at || w.created_at,
          severity: 'error',
        })
      }
    }

    // Generation jobs
    for (const j of jobsRes.data ?? []) {
      if (j.status === 'failed') {
        activities.push({
          id: `job-${j.id}`,
          type: 'error',
          message: 'Generation failed',
          detail: `${j.error?.substring(0, 80) || 'Unknown error'} (Job: ${j.job_id?.substring(0, 8)})`,
          created_at: j.updated_at || j.created_at,
          severity: 'error',
        })
      }
    }

    // Transactions
    for (const t of transactionsRes.data ?? []) {
      if (t.payment_status === 'success') {
        activities.push({
          id: `pay-${t.transaction_id}`,
          type: 'payment',
          message: 'Payment received',
          detail: `RM ${t.amount} - ${t.item_description || 'Subscription'} by ${nameMap[t.user_id] || 'Unknown'}`,
          created_at: t.created_at,
          severity: 'success',
        })
      } else if (t.payment_status === 'failed') {
        activities.push({
          id: `pay-fail-${t.transaction_id}`,
          type: 'payment',
          message: 'Payment failed',
          detail: `RM ${t.amount} by ${nameMap[t.user_id] || 'Unknown'}`,
          created_at: t.created_at,
          severity: 'error',
        })
      }
    }

    // Sort by time, newest first
    activities.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())

    return NextResponse.json({ activities: activities.slice(0, 50) })
  } catch (error) {
    console.error('Activity API error:', error)
    return NextResponse.json({ error: 'Failed to fetch activity' }, { status: 500 })
  }
}
