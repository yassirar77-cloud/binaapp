import { NextRequest, NextResponse } from 'next/server'
import { supabaseAdmin } from '@/lib/supabase-admin'
import { requireFounder } from '@/lib/require-founder'
import { uniqueUuids } from '@/lib/uuid'

export const dynamic = 'force-dynamic'

export async function GET(request: NextRequest) {
  const denied = await requireFounder(request)
  if (denied) return denied

  try {
    const { searchParams } = new URL(request.url)
    // Strip PostgREST filter syntax characters so the .or() string cannot break
    const search = (searchParams.get('search') || '').replace(/[,().]/g, '').trim()
    const status = searchParams.get('status') || ''
    const page = parseInt(searchParams.get('page') || '1')
    const limit = 50

    // Query websites without embedded profile join (no direct FK between websites and profiles)
    let query = supabaseAdmin
      .from('websites')
      .select('id, business_name, business_type, subdomain, status, language, published_at, created_at, error_message, user_id', { count: 'exact' })

    if (search) {
      query = query.or(`business_name.ilike.%${search}%,subdomain.ilike.%${search}%`)
    }

    if (status) {
      query = query.eq('status', status)
    }

    query = query
      .order('created_at', { ascending: false })
      .range((page - 1) * limit, page * limit - 1)

    const { data: websites, error, count: filteredTotal } = await query

    console.log('[Websites] query:', websites?.length, 'total:', filteredTotal, 'error:', error?.message)

    if (error) throw error

    // Get owner names separately
    const userIds = uniqueUuids((websites ?? []).map(w => w.user_id))
    const profileMap: Record<string, { full_name: string; business_name: string }> = {}

    if (userIds.length > 0) {
      const { data: profiles, error: profilesError } = await supabaseAdmin
        .from('profiles')
        .select('id, full_name, business_name')
        .in('id', userIds)

      console.log('[Websites] profiles:', profiles?.length, 'error:', profilesError?.message)

      for (const p of profiles ?? []) {
        profileMap[p.id] = { full_name: p.full_name, business_name: p.business_name }
      }
    }

    // Get counts by status
    const [totalRes, publishedRes, draftRes, failedRes] = await Promise.all([
      supabaseAdmin.from('websites').select('id', { count: 'exact', head: true }),
      supabaseAdmin.from('websites').select('id', { count: 'exact', head: true }).eq('status', 'published'),
      supabaseAdmin.from('websites').select('id', { count: 'exact', head: true }).eq('status', 'draft'),
      supabaseAdmin.from('websites').select('id', { count: 'exact', head: true }).eq('status', 'failed'),
    ])

    console.log('[Websites] counts - total:', totalRes.count, 'published:', publishedRes.count, 'draft:', draftRes.count, 'failed:', failedRes.count)
    if (totalRes.error) console.log('[Websites] total count error:', totalRes.error.message)

    const result = (websites ?? []).map(w => ({
      id: w.id,
      business_name: w.business_name,
      business_type: w.business_type,
      subdomain: w.subdomain,
      status: w.status,
      language: w.language,
      published_at: w.published_at,
      created_at: w.created_at,
      error_message: w.error_message,
      owner_name: profileMap[w.user_id]?.full_name || profileMap[w.user_id]?.business_name || 'Unknown',
    }))

    return NextResponse.json({
      websites: result,
      total: filteredTotal ?? 0,
      page,
      counts: {
        total: totalRes.count ?? 0,
        published: publishedRes.count ?? 0,
        draft: draftRes.count ?? 0,
        failed: failedRes.count ?? 0,
      },
    })
  } catch (error) {
    console.error('[Websites] API error:', error)
    return NextResponse.json({ error: 'Failed to fetch websites' }, { status: 500 })
  }
}
