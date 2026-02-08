import { NextRequest, NextResponse } from 'next/server'
import { supabaseAdmin } from '@/lib/supabase-admin'

export const dynamic = 'force-dynamic'

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    const since = searchParams.get('since') || ''
    const countOnly = searchParams.get('count_only') === 'true'

    const startOfDay = new Date().toISOString().split('T')[0] + 'T00:00:00.000Z'

    if (countOnly) {
      // Quick count of today's errors
      const { count } = await supabaseAdmin
        .from('generation_jobs')
        .select('id', { count: 'exact', head: true })
        .eq('status', 'failed')
        .gte('created_at', since || startOfDay)

      return NextResponse.json({ count: count ?? 0 })
    }

    // Get failed generation jobs with details
    const { data: failedJobs } = await supabaseAdmin
      .from('generation_jobs')
      .select('id, job_id, status, error, user_id, created_at')
      .eq('status', 'failed')
      .order('created_at', { ascending: false })
      .limit(100)

    // Get error_logs if table exists
    let errorLogs: Array<Record<string, unknown>> = []
    try {
      const { data } = await supabaseAdmin
        .from('error_logs')
        .select('*')
        .order('created_at', { ascending: false })
        .limit(100)
      errorLogs = data ?? []
    } catch {
      // Table may not exist yet
    }

    // Count today's errors by type
    const todayErrors = (failedJobs ?? []).filter(
      j => j.created_at >= startOfDay
    )
    const deepseekFails = todayErrors.filter(
      e => e.error?.toLowerCase().includes('deepseek')
    ).length
    const qwenFails = todayErrors.filter(
      e => e.error?.toLowerCase().includes('qwen')
    ).length
    const stabilityFails = todayErrors.filter(
      e => e.error?.toLowerCase().includes('stability')
    ).length

    // Get user names
    const userIds = [...new Set(
      (failedJobs ?? []).map(j => j.user_id).filter(Boolean)
    )]
    const { data: profiles } = await supabaseAdmin
      .from('profiles')
      .select('id, full_name')
      .in('id', userIds.length > 0 ? userIds : ['none'])

    const profileMap: Record<string, string> = {}
    for (const p of profiles ?? []) {
      profileMap[p.id] = p.full_name
    }

    // Classify errors with severity
    const errors = (failedJobs ?? []).map(j => {
      let severity: 'critical' | 'error' | 'warning' | 'info' = 'error'
      let errorType = 'generation'
      const errorMsg = j.error?.toLowerCase() || ''

      if (errorMsg.includes('deepseek') && errorMsg.includes('qwen')) {
        severity = 'critical'
        errorType = 'deepseek+qwen'
      } else if (errorMsg.includes('deepseek')) {
        severity = 'error'
        errorType = 'deepseek'
      } else if (errorMsg.includes('qwen')) {
        severity = 'warning'
        errorType = 'qwen'
      } else if (errorMsg.includes('stability')) {
        severity = 'warning'
        errorType = 'stability'
      }

      return {
        id: j.id,
        job_id: j.job_id,
        error: j.error,
        user_id: j.user_id,
        user_name: profileMap[j.user_id] || j.user_id || 'Unknown',
        created_at: j.created_at,
        severity,
        error_type: errorType,
      }
    })

    return NextResponse.json({
      errors,
      errorLogs,
      todaySummary: {
        total: todayErrors.length,
        deepseek: deepseekFails,
        qwen: qwenFails,
        stability: stabilityFails,
      },
    })
  } catch (error) {
    console.error('Errors API error:', error)
    return NextResponse.json({ error: 'Failed to fetch errors' }, { status: 500 })
  }
}
