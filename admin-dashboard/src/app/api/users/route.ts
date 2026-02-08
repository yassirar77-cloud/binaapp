import { NextRequest, NextResponse } from 'next/server'
import { supabaseAdmin } from '@/lib/supabase-admin'

export const dynamic = 'force-dynamic'

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    const search = searchParams.get('search') || ''
    const plan = searchParams.get('plan') || ''
    const sort = searchParams.get('sort') || 'newest'
    const page = parseInt(searchParams.get('page') || '1')
    const limit = 50

    // Get users with subscription info
    let query = supabaseAdmin
      .from('profiles')
      .select(`
        id, full_name, business_name, phone, created_at,
        subscriptions!left(tier, status)
      `)

    if (search) {
      query = query.or(`full_name.ilike.%${search}%,business_name.ilike.%${search}%`)
    }

    if (sort === 'newest') {
      query = query.order('created_at', { ascending: false })
    } else {
      query = query.order('created_at', { ascending: true })
    }

    query = query.range((page - 1) * limit, page * limit - 1)

    const { data: users, error } = await query

    if (error) throw error

    // Get website counts for these users
    const userIds = (users ?? []).map(u => u.id)
    const { data: websiteCounts } = await supabaseAdmin
      .from('websites')
      .select('user_id')
      .in('user_id', userIds.length > 0 ? userIds : ['none'])

    const countMap: Record<string, number> = {}
    for (const w of websiteCounts ?? []) {
      countMap[w.user_id] = (countMap[w.user_id] || 0) + 1
    }

    // Get total count
    const { count: totalCount } = await supabaseAdmin
      .from('profiles')
      .select('id', { count: 'exact', head: true })

    const result = (users ?? []).map(u => {
      const sub = Array.isArray(u.subscriptions)
        ? u.subscriptions[0]
        : u.subscriptions
      return {
        id: u.id,
        full_name: u.full_name || 'No name',
        business_name: u.business_name,
        phone: u.phone,
        created_at: u.created_at,
        plan: sub?.tier || 'free',
        status: sub?.status || 'inactive',
        website_count: countMap[u.id] || 0,
      }
    })

    // Filter by plan client-side if needed (since tier is from joined table)
    const filtered = plan
      ? result.filter(u => u.plan === plan)
      : result

    return NextResponse.json({
      users: filtered,
      total: totalCount ?? 0,
      page,
    })
  } catch (error) {
    console.error('Users API error:', error)
    return NextResponse.json({ error: 'Failed to fetch users' }, { status: 500 })
  }
}
