'use client'

import { useCallback, useEffect, useState } from 'react'

import {
  STATUS_ACTION_LABELS,
  STATUS_LABELS,
  addDays,
  fetchBookings,
  formatDateMs,
  formatDuration,
  formatPrice,
  formatTime12,
  groupByDate,
  setBookingStatus,
  type BookingStatus,
  type OwnerBooking,
} from '@/lib/booking'

import { Button, Notice, errorText, inputClass } from './ui'

const STATUS_TONES: Record<BookingStatus, string> = {
  pending: 'bg-[#FFB020]/15 text-[#FFC966]',
  confirmed: 'bg-[#C7FF3D]/15 text-[#C7FF3D]',
  cancelled: 'bg-white/[0.06] text-white/40',
  completed: 'bg-[#4F9DFF]/15 text-[#8FC0FF]',
  no_show: 'bg-[#FF5A5F]/15 text-[#FF9A9D]',
}

type Range = 'upcoming' | 'past'

/** Today in Malaysia as YYYY-MM-DD (the server's business day). */
function todayMy(): string {
  return new Intl.DateTimeFormat('en-CA', { timeZone: 'Asia/Kuala_Lumpur' }).format(new Date())
}

export default function BookingsTab({ websiteId }: { websiteId: string }) {
  const [range, setRange] = useState<Range>('upcoming')
  const [status, setStatus] = useState<BookingStatus | ''>('')
  const [bookings, setBookings] = useState<OwnerBooking[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [busyId, setBusyId] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    const today = todayMy()
    try {
      const rows = await fetchBookings(
        websiteId,
        range === 'upcoming'
          ? { dateFrom: today, dateTo: addDays(today, 180), status }
          : { dateFrom: addDays(today, -90), dateTo: addDays(today, -1), status },
      )
      setBookings(range === 'past' ? [...rows].reverse() : rows)
    } catch (err) {
      setError(errorText(err, 'Gagal memuatkan tempahan.'))
    } finally {
      setLoading(false)
    }
  }, [websiteId, range, status])

  useEffect(() => {
    load()
  }, [load])

  const act = async (booking: OwnerBooking, next: BookingStatus) => {
    if (next === 'cancelled' && !window.confirm(`Batalkan tempahan ${booking.reference}?`)) return
    setBusyId(booking.id)
    setError('')
    try {
      const updated = await setBookingStatus(websiteId, booking.id, next)
      setBookings((rows) => rows.map((r) => (r.id === updated.id ? updated : r)))
    } catch (err) {
      setError(errorText(err, 'Gagal mengemas kini tempahan.'))
      load()
    } finally {
      setBusyId(null)
    }
  }

  const groups = groupByDate(bookings)
  if (range === 'past') groups.reverse()

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        {(['upcoming', 'past'] as Range[]).map((r) => (
          <Button key={r} variant={range === r ? 'primary' : 'ghost'} onClick={() => setRange(r)}>
            {r === 'upcoming' ? 'Akan datang' : 'Lepas (90 hari)'}
          </Button>
        ))}
        <select
          aria-label="Tapis status"
          value={status}
          onChange={(e) => setStatus(e.target.value as BookingStatus | '')}
          className={`${inputClass} !w-auto !rounded-full !py-1.5 text-xs`}
        >
          <option value="" className="bg-[#161623]">Semua status</option>
          {(Object.keys(STATUS_LABELS) as BookingStatus[]).map((s) => (
            <option key={s} value={s} className="bg-[#161623]">
              {STATUS_LABELS[s]}
            </option>
          ))}
        </select>
        <Button onClick={load} disabled={loading} className="ml-auto">
          Muat semula
        </Button>
      </div>

      {error && <Notice tone="error">{error}</Notice>}

      {loading ? (
        <div className="flex justify-center py-16">
          <div className="h-7 w-7 animate-spin rounded-full border-2 border-white/20 border-t-[#C7FF3D]" />
        </div>
      ) : groups.length === 0 ? (
        <div className="dash-surface p-10 text-center">
          <p className="text-white font-medium">Tiada tempahan</p>
          <p className="text-[13px] text-white/40 mt-1">
            {range === 'upcoming'
              ? 'Kongsi pautan tempahan di atas kepada pelanggan anda.'
              : 'Tiada tempahan dalam 90 hari lepas.'}
          </p>
        </div>
      ) : (
        groups.map((group) => (
          <section key={group.date} className="dash-surface p-4">
            <h2 className="text-sm font-semibold text-white mb-3">
              {formatDateMs(group.date)}
              <span className="ml-2 text-xs font-normal text-white/40">{group.rows.length} tempahan</span>
            </h2>
            <ul className="divide-y divide-white/[0.06]">
              {group.rows.map((b) => (
                <li key={b.id} className="py-3 flex flex-wrap items-start gap-x-4 gap-y-2">
                  <div className="w-20 shrink-0">
                    <p className="text-sm font-semibold text-white dash-tnum">{formatTime12(b.time)}</p>
                    <p className="text-[11px] text-white/40">{formatDuration(b.duration_min)}</p>
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="text-sm text-white">
                      {b.customer_name}
                      <span className={`ml-2 rounded-full px-2 py-0.5 text-[11px] font-medium ${STATUS_TONES[b.status]}`}>
                        {STATUS_LABELS[b.status]}
                        {b.status === 'cancelled' && b.cancelled_by === 'customer' ? ' oleh pelanggan' : ''}
                      </span>
                    </p>
                    <p className="text-[13px] text-white/60">
                      {b.service_name}
                      {b.price !== null ? ` · ${formatPrice(b.price)}` : ''}
                    </p>
                    <p className="text-[12px] text-white/40">
                      <a href={`https://wa.me/${b.customer_phone}`} target="_blank" rel="noopener noreferrer" className="underline hover:text-white/70">
                        +{b.customer_phone}
                      </a>
                      {' · '}
                      <span className="dash-tnum">{b.reference}</span>
                    </p>
                    {b.notes && <p className="text-[12px] text-white/50 mt-1 whitespace-pre-wrap">“{b.notes}”</p>}
                  </div>
                  {b.next_statuses.length > 0 && (
                    <div className="flex flex-wrap gap-2">
                      {[
                        ...b.next_statuses.filter((x) => x !== 'cancelled'),
                        ...b.next_statuses.filter((x) => x === 'cancelled'),
                      ].map((next) => (
                          <Button
                            key={next}
                            variant={next === 'cancelled' || next === 'no_show' ? 'danger' : 'primary'}
                            disabled={busyId === b.id}
                            onClick={() => act(b, next)}
                          >
                            {STATUS_ACTION_LABELS[next]}
                          </Button>
                        ))}
                    </div>
                  )}
                </li>
              ))}
            </ul>
          </section>
        ))
      )}
    </div>
  )
}
