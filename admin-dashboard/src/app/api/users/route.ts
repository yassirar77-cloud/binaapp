import { NextRequest, NextResponse } from 'next/server'
import { supabaseAdmin } from '@/lib/supabase-admin'
import { requireFounder } from '@/lib/require-founder'

export const dynamic = 'force-dynamic'

export async function GET(request: NextRequest) {
  const denied = await requireFounder(request)
  if (denied) return denied

  try {
    const { searchParams } = new URL(request.url)
    // Strip PostgREST filter syntax characters so the .or() string cannot break
    const search = (searchParams.get('search') || '').replace(/[,().]/g, '').trim()
    const plan = searchParams.get('plan') || ''
    const sort = searchParams.get('sort') || 'newest'
    const page = parseInt(searchParams.get('page') || '1')
    const limit = 50

    // Resolve the plan filter BEFORE pagination (subscriptions has no FK to profiles)
    let planIds: string[] | null = null   // restrict to these ids
    let excludeIds: string[] = []         // 'free' = no subscription row, or tier 'free'
    if (plan === 'free') {
      const { data: paidSubs, error: paidErr } = await supabaseAdmin
        .from('subscriptions')
        .select('user_id')
        .neq('tier', 'free')
      console.log('[Users] non-free subscriptions:', paidSubs?.length, 'error:', paidErr?.message)
      excludeIds = (paidSubs ?? []).map(s => s.user_id)
    } else if (plan) {
      const { data: subs, error: subErr } = await supabaseAdmin
        .from('subscriptions')
        .select('user_id')
        .eq('tier', plan)
      console.log('[Users] plan subscriptions:', subs?.length, 'error:', subErr?.message)
      planIds = (subs ?? []).map(s => s.user_id)
      if (planIds.length === 0) {
        return NextResponse.json({ users: [], total: 0, page })
      }
    }

    // Query profiles directly (no embedded join with subscriptions
    // since there's no direct FK between profiles and subscriptions)
    let query = supabaseAdmin
      .from('profiles')
      .select('id, full_name, business_name, phone, created_at', { count: 'exact' })

    if (search) {
      query = query.or(`full_name.ilike.%${search}%,business_name.ilike.%${search}%`)
    }
    if (planIds) {
      query = query.in('id', planIds)
    }
    if (excludeIds.length > 0) {
      query = query.not('id', 'in', `(${excludeIds.join(',')})`)
    }

    if (sort === 'newest') {
      query = query.order('created_at', { ascending: false })
    } else {
      query = query.order('created_at', { ascending: true })
    }

    query = query.range((page - 1) * limit, page * limit - 1)

    const { data: users, error, count: totalCount } = await query

    console.log('[Users] profiles:', users?.length, 'total:', totalCount, 'error:', error?.message)

    if (error) throw error

    // Get subscription info separately for these users
    const userIds = (users ?? []).map(u => u.id)

    let subMap: Record<string, { tier: string; status: string }> = {}
    let countMap: Record<string, number> = {}

    if (userIds.length > 0) {
      // Query subscriptions separately (user_id column references auth.users)
      const { data: subscriptions, error: subError } = await supabaseAdmin
        .from('subscriptions')
        .select('user_id, tier, status')
        .in('user_id', userIds)

      console.log('[Users] subscriptions:', subscriptions?.length, 'error:', subError?.message)

      for (const s of subscriptions ?? []) {
        subMap[s.user_id] = { tier: s.tier, status: s.status }
      }

      // Get website counts for these users
      const { data: websiteCounts, error: wcError } = await supabaseAdmin
        .from('websites')
        .select('user_id')
        .in('user_id', userIds)

      console.log('[Users] website counts:', websiteCounts?.length, 'error:', wcError?.message)

      for (const w of websiteCounts ?? []) {
        countMap[w.user_id] = (countMap[w.user_id] || 0) + 1
      }
    }

    const result = (users ?? []).map(u => ({
      id: u.id,
      full_name: u.full_name || 'No name',
      business_name: u.business_name,
      phone: u.phone,
      created_at: u.created_at,
      plan: subMap[u.id]?.tier || 'free',
      status: subMap[u.id]?.status || 'inactive',
      website_count: countMap[u.id] || 0,
    }))

    return NextResponse.json({
      users: result,
      total: totalCount ?? 0,
      page,
    })
  } catch (error) {
    console.error('[Users] API error:', error)
    return NextResponse.json({ error: 'Failed to fetch users' }, { status: 500 })
  }
}
