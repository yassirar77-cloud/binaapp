import { NextRequest, NextResponse } from 'next/server'
import { supabaseAdmin } from '@/lib/supabase-admin'

export const dynamic = 'force-dynamic'

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    const search = searchParams.get('search') || ''
    const status = searchParams.get('status') || ''
    const page = parseInt(searchParams.get('page') || '1')
    const limit = 50

    let query = supabaseAdmin
      .from('websites')
      .select(`
        id, business_name, business_type, subdomain, status,
        language, published_at, created_at, error_message, user_id,
        profiles!left(full_name, business_name)
      `)

    if (search) {
      query = query.or(`business_name.ilike.%${search}%,subdomain.ilike.%${search}%`)
    }

    if (status) {
      query = query.eq('status', status)
    }

    query = query
      .order('created_at', { ascending: false })
      .range((page - 1) * limit, page * limit - 1)

    const { data: websites, error } = await query
    if (error) throw error

    // Get counts by status
    const [totalRes, publishedRes, draftRes, failedRes] = await Promise.all([
      supabaseAdmin.from('websites').select('id', { count: 'exact', head: true }),
      supabaseAdmin.from('websites').select('id', { count: 'exact', head: true }).eq('status', 'published'),
      supabaseAdmin.from('websites').select('id', { count: 'exact', head: true }).eq('status', 'draft'),
      supabaseAdmin.from('websites').select('id', { count: 'exact', head: true }).eq('status', 'failed'),
    ])

    const result = (websites ?? []).map(w => {
      const profile = Array.isArray(w.profiles)
        ? w.profiles[0]
        : w.profiles
      return {
        id: w.id,
        business_name: w.business_name,
        business_type: w.business_type,
        subdomain: w.subdomain,
        status: w.status,
        language: w.language,
        published_at: w.published_at,
        created_at: w.created_at,
        error_message: w.error_message,
        owner_name: profile?.full_name || profile?.business_name || 'Unknown',
      }
    })

    return NextResponse.json({
      websites: result,
      counts: {
        total: totalRes.count ?? 0,
        published: publishedRes.count ?? 0,
        draft: draftRes.count ?? 0,
        failed: failedRes.count ?? 0,
      },
    })
  } catch (error) {
    console.error('Websites API error:', error)
    return NextResponse.json({ error: 'Failed to fetch websites' }, { status: 500 })
  }
}
