import { NextResponse } from 'next/server'
import { supabaseAdmin } from '@/lib/supabase-admin'
import { requireFounder } from '@/lib/require-founder'

export const dynamic = 'force-dynamic'

const WISH_DOMAIN = process.env.WISH_DOMAIN || 'mysyg.com'

// A wish counts as sold once payment cleared: everything after awaiting_payment
// except cancelled (see backend/app/services/wishes.py, LIVE_STATUSES).
const PAID = ['paid', 'generating', 'storing', 'ready', 'video_failed']

const COLUMNS = [
  'id', 'slug', 'status', 'occasion', 'package', 'video_seconds', 'amount_rm',
  'sender_name', 'recipient_name', 'message', 'photo_urls', 'video_url', 'poster_url',
  'video_direction', 'video_error', 'video_attempts',
  'payer_email', 'payer_phone', 'bill_code', 'paid_at', 'created_at',
  'unlock_at', 'opened_at', 'open_count', 'view_count',
  'reaction', 'reply_text', 'replied_at',
  'since_kind', 'since_date', 'secret_question', 'heart_count',
].join(', ')

const REACTIONS: Record<string, string> = { love: '❤️', touched: '😭', hug: '🤗', laugh: '😂', wow: '😍' }

type Row = Record<string, any>

function startOf(unit: 'day' | 'week' | 'month'): Date {
  // Malaysia time (UTC+8): "today" should mean the founder's today.
  const now = new Date(Date.now() + 8 * 3600_000)
  const d = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate()))
  if (unit === 'week') d.setUTCDate(d.getUTCDate() - ((d.getUTCDay() + 6) % 7))
  if (unit === 'month') d.setUTCDate(1)
  return new Date(d.getTime() - 8 * 3600_000)
}

export async function GET(request: Request) {
  const denied = await requireFounder(request)
  if (denied) return denied

  try {
    const { searchParams } = new URL(request.url)
    const search = (searchParams.get('search') || '').trim().toLowerCase()
    const filter = searchParams.get('status') || ''

    // The table is small (one row per gift); fetch it once and work in memory.
    const { data, error } = await supabaseAdmin
      .from('wishes')
      .select(COLUMNS)
      .order('created_at', { ascending: false })
      .limit(2000)
    if (error) throw error
    const rows = (data ?? []) as Row[]

    const isPaid = (r: Row) => PAID.includes(r.status)
    const paidAt = (r: Row) => new Date(r.paid_at || r.created_at)
    const money = (list: Row[]) => list.reduce((s, r) => s + (Number(r.amount_rm) || 0), 0)
    const paid = rows.filter(isPaid)
    const since = (d: Date) => paid.filter(r => paidAt(r) >= d)

    const byPackage: Record<string, { count: number; amount: number }> = {}
    const byOccasion: Record<string, number> = {}
    for (const r of paid) {
      const p = r.package || 'ringkas'
      byPackage[p] = byPackage[p] || { count: 0, amount: 0 }
      byPackage[p].count++
      byPackage[p].amount += Number(r.amount_rm) || 0
      byOccasion[r.occasion || 'birthday'] = (byOccasion[r.occasion || 'birthday'] || 0) + 1
    }

    const senders = new Set(paid.map(r => (r.payer_email || '').toLowerCase()).filter(Boolean))

    const summary = {
      revenue: {
        today: money(since(startOf('day'))),
        week: money(since(startOf('week'))),
        month: money(since(startOf('month'))),
        allTime: money(paid),
      },
      counts: {
        paid: paid.length,
        free: paid.filter(r => !Number(r.amount_rm)).length,
        ready: rows.filter(r => r.status === 'ready').length,
        making: rows.filter(r => ['paid', 'generating', 'storing'].includes(r.status)).length,
        failed: rows.filter(r => r.status === 'video_failed').length,
        unpaid: rows.filter(r => r.status === 'awaiting_payment').length,
        cancelled: rows.filter(r => r.status === 'cancelled').length,
        opened: paid.filter(r => r.opened_at).length,
        replied: paid.filter(r => r.replied_at).length,
        senders: senders.size,
        repeatSenders: [...senders].filter(e => paid.filter(r => (r.payer_email || '').toLowerCase() === e).length > 1).length,
        hearts: paid.reduce((s, r) => s + (Number(r.heart_count) || 0), 0),
      },
      byPackage,
      byOccasion,
    }

    let list = rows
    if (filter === 'paid') list = paid
    else if (filter === 'making') list = rows.filter(r => ['paid', 'generating', 'storing'].includes(r.status))
    else if (filter) list = rows.filter(r => r.status === filter)
    if (search) {
      list = list.filter(r =>
        [r.slug, r.sender_name, r.recipient_name, r.payer_email, r.payer_phone, r.bill_code]
          .some(v => String(v || '').toLowerCase().includes(search)),
      )
    }

    const wishes = list.slice(0, 300).map(r => ({
      id: r.id,
      slug: r.slug,
      url: `https://${r.slug}.${WISH_DOMAIN}`,
      status: r.status,
      occasion: r.occasion,
      package: r.package || 'ringkas',
      video_seconds: r.video_seconds,
      amount: Number(r.amount_rm) || 0,
      sender_name: r.sender_name,
      recipient_name: r.recipient_name,
      message: r.message,
      photo_urls: r.photo_urls || [],
      video_url: r.video_url,
      poster_url: r.poster_url,
      video_direction: r.video_direction,
      video_error: r.video_error,
      video_attempts: r.video_attempts || 0,
      payer_email: r.payer_email,
      payer_phone: r.payer_phone,
      bill_code: r.bill_code,
      paid_at: r.paid_at,
      created_at: r.created_at,
      unlock_at: r.unlock_at,
      opened_at: r.opened_at,
      open_count: r.open_count || 0,
      view_count: r.view_count || 0,
      reaction: r.reaction ? REACTIONS[r.reaction] || r.reaction : null,
      reply_text: r.reply_text,
      replied_at: r.replied_at,
      since: r.since_kind && r.since_date ? { kind: r.since_kind, date: r.since_date } : null,
      secret_question: r.secret_question,
      hearts: r.heart_count || 0,
    }))

    return NextResponse.json({ summary, wishes, total: list.length })
  } catch (error: any) {
    console.error('[Wishes] API error:', error)
    return NextResponse.json({ error: 'Failed to load mysyg wishes' }, { status: 500 })
  }
}
