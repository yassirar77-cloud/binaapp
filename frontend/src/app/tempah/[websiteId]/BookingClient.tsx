'use client'

/**
 * Customer booking page — /tempah/{websiteId}
 *
 * Service → date → time → details → confirmation, on one page. No login:
 * the customer keeps a reference code and proves a booking is theirs with
 * that code plus the phone number it was made with ("Semak tempahan").
 *
 * The server is the authority on what is bookable; this page only avoids
 * offering what it already knows cannot work, and when the server says a
 * slot has just gone (409) it reloads the slots and says so.
 */

import { useEffect, useMemo, useRef, useState } from 'react'

import {
  BookingApiError,
  STATUS_LABELS,
  WEEKDAY_LABELS,
  bookableDates,
  cancelBooking,
  createBooking,
  fetchPublicInfo,
  fetchSlots,
  formatDateMs,
  formatDuration,
  formatPrice,
  formatTime12,
  isPlausiblePhone,
  lookupBooking,
  type BookingService,
  type CustomerBooking,
  type PublicBookingInfo,
  type Slot,
} from '@/lib/booking'

type View = 'book' | 'done' | 'lookup'

const card = 'rounded-2xl border border-slate-200 bg-white p-5 shadow-sm'
const input =
  'w-full rounded-xl border border-slate-300 bg-white px-3.5 py-3 text-base text-slate-900 ' +
  'placeholder:text-slate-400 focus:border-slate-900 focus:outline-none focus:ring-2 focus:ring-slate-900/10'
const primaryBtn =
  'w-full rounded-xl bg-slate-900 px-4 py-3.5 text-base font-semibold text-white transition ' +
  'hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-40'

function StepTitle({ n, children }: { n: number; children: React.ReactNode }) {
  return (
    <h2 className="mb-3 flex items-center gap-2 text-base font-semibold text-slate-900">
      <span className="flex h-6 w-6 items-center justify-center rounded-full bg-slate-900 text-xs font-bold text-white">
        {n}
      </span>
      {children}
    </h2>
  )
}

function ErrorBox({ children }: { children: React.ReactNode }) {
  return (
    <div role="alert" className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
      {children}
    </div>
  )
}

function BookingSummary({ booking }: { booking: CustomerBooking }) {
  const rows: Array<[string, string]> = [
    ['Servis', booking.service_name],
    ['Tarikh', formatDateMs(booking.date)],
    ['Masa', `${formatTime12(booking.time)} (${formatDuration(booking.duration_min)})`],
    ['Nama', booking.customer_name],
    ['Telefon', booking.customer_phone_masked],
    ['Status', STATUS_LABELS[booking.status]],
  ]
  if (booking.price !== null) rows.splice(3, 0, ['Harga', formatPrice(booking.price)])
  return (
    <dl className="divide-y divide-slate-100 text-sm">
      {rows.map(([k, v]) => (
        <div key={k} className="flex justify-between gap-4 py-2">
          <dt className="text-slate-500">{k}</dt>
          <dd className="text-right font-medium text-slate-900">{v}</dd>
        </div>
      ))}
    </dl>
  )
}

export default function BookingClient({ websiteId }: { websiteId: string }) {
  const [info, setInfo] = useState<PublicBookingInfo | null>(null)
  const [loadError, setLoadError] = useState('')
  const [view, setView] = useState<View>('book')

  const [service, setService] = useState<BookingService | null>(null)
  const [date, setDate] = useState('')
  const [slots, setSlots] = useState<Slot[]>([])
  const [slotsMessage, setSlotsMessage] = useState('')
  const [slotsLoading, setSlotsLoading] = useState(false)
  const [time, setTime] = useState('')
  const [name, setName] = useState('')
  const [phone, setPhone] = useState('')
  const [notes, setNotes] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [formError, setFormError] = useState('')
  const [booking, setBooking] = useState<CustomerBooking | null>(null)

  const [lookupRef, setLookupRef] = useState('')
  const [lookupPhone, setLookupPhone] = useState('')
  const [lookupBusy, setLookupBusy] = useState(false)
  const [lookupError, setLookupError] = useState('')
  const [found, setFound] = useState<CustomerBooking | null>(null)

  const slotRequest = useRef(0)

  useEffect(() => {
    fetchPublicInfo(websiteId)
      .then((data) => {
        setInfo(data)
        if (data.services.length === 1) setService(data.services[0])
        if (data.business_name) document.title = `Tempah Slot — ${data.business_name}`
      })
      .catch((err: BookingApiError) =>
        setLoadError(err.status === 404 ? 'Halaman tempahan tidak dijumpai.' : err.message),
      )
  }, [websiteId])

  const dates = useMemo(() => (info ? bookableDates(info) : []), [info])

  const loadSlots = async (serviceId: string, day: string) => {
    const request = ++slotRequest.current
    setSlotsLoading(true)
    setSlotsMessage('')
    setTime('')
    try {
      const res = await fetchSlots(websiteId, serviceId, day)
      if (request !== slotRequest.current) return
      setSlots(res.slots)
      if (res.message) setSlotsMessage(res.message)
      else if (!res.slots.some((s) => s.available)) setSlotsMessage('Tiada slot kosong pada tarikh ini.')
    } catch (err) {
      if (request !== slotRequest.current) return
      setSlots([])
      setSlotsMessage((err as BookingApiError).message)
    } finally {
      if (request === slotRequest.current) setSlotsLoading(false)
    }
  }

  useEffect(() => {
    if (service && date) loadSlots(service.id, date)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [service?.id, date])

  const canSubmit = !!service && !!date && !!time && name.trim().length > 0 && isPlausiblePhone(phone)

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!service || !canSubmit || submitting) return
    setSubmitting(true)
    setFormError('')
    try {
      const created = await createBooking(websiteId, {
        service_id: service.id,
        date,
        time,
        customer_name: name.trim(),
        customer_phone: phone.trim(),
        notes: notes.trim(),
      })
      setBooking(created)
      setView('done')
      window.scrollTo({ top: 0 })
    } catch (err) {
      const apiErr = err as BookingApiError
      setFormError(apiErr.message)
      // The slot went while the customer was typing — show what is left.
      if (apiErr.status === 409 || apiErr.code === 'SLOT_INVALID') loadSlots(service.id, date)
    } finally {
      setSubmitting(false)
    }
  }

  const doLookup = async (e: React.FormEvent) => {
    e.preventDefault()
    setLookupBusy(true)
    setLookupError('')
    setFound(null)
    try {
      setFound(await lookupBooking(websiteId, lookupRef.trim(), lookupPhone.trim()))
    } catch (err) {
      setLookupError((err as BookingApiError).message)
    } finally {
      setLookupBusy(false)
    }
  }

  const doCancel = async () => {
    if (!found || !window.confirm('Batalkan tempahan ini?')) return
    setLookupBusy(true)
    setLookupError('')
    try {
      setFound(await cancelBooking(websiteId, found.reference, lookupPhone.trim()))
    } catch (err) {
      setLookupError((err as BookingApiError).message)
    } finally {
      setLookupBusy(false)
    }
  }

  const startOver = () => {
    setBooking(null)
    setTime('')
    setNotes('')
    setFormError('')
    setView('book')
    if (service && date) loadSlots(service.id, date)
  }

  // ── Render ────────────────────────────────────────────────────────────

  if (loadError) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-slate-50 px-4">
        <div className={`${card} max-w-sm text-center`}>
          <p className="font-semibold text-slate-900">Maaf</p>
          <p className="mt-1 text-sm text-slate-600">{loadError}</p>
        </div>
      </main>
    )
  }

  if (!info) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-slate-50">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-slate-300 border-t-slate-900" />
      </main>
    )
  }

  return (
    <main className="min-h-screen bg-slate-50 px-4 py-8 text-slate-900">
      <div className="mx-auto max-w-lg space-y-4">
        <header className="text-center">
          <p className="text-xs font-semibold uppercase tracking-widest text-slate-500">Tempah slot</p>
          <h1 className="mt-1 text-2xl font-bold" style={{ textWrap: 'balance' } as React.CSSProperties}>
            {info.business_name || 'Tempahan'}
          </h1>
        </header>

        {view === 'done' && booking ? (
          <section className={card} aria-live="polite">
            <div className="mb-4 text-center">
              <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-emerald-100 text-2xl text-emerald-700">
                ✓
              </div>
              <h2 className="text-lg font-bold">Tempahan diterima</h2>
              <p className="mt-1 text-sm text-slate-600">Simpan kod rujukan ini untuk menyemak atau membatalkan tempahan.</p>
              <p className="mt-3 inline-block rounded-xl bg-slate-900 px-4 py-2 font-mono text-xl font-bold tracking-widest text-white">
                {booking.reference}
              </p>
            </div>
            <BookingSummary booking={booking} />
            <button type="button" onClick={startOver} className="mt-4 w-full rounded-xl border border-slate-300 px-4 py-3 text-sm font-semibold hover:bg-slate-50">
              Buat tempahan lain
            </button>
          </section>
        ) : view === 'lookup' ? (
          <section className={`${card} space-y-4`}>
            <h2 className="text-base font-semibold">Semak tempahan</h2>
            <form onSubmit={doLookup} className="space-y-3">
              <label className="block text-sm font-medium text-slate-700">
                Kod rujukan
                <input
                  className={`${input} mt-1 font-mono uppercase`}
                  placeholder="TP-XXXXXX"
                  value={lookupRef}
                  onChange={(e) => setLookupRef(e.target.value)}
                  autoCapitalize="characters"
                  required
                />
              </label>
              <label className="block text-sm font-medium text-slate-700">
                Nombor telefon semasa menempah
                <input
                  className={`${input} mt-1`}
                  type="tel"
                  inputMode="tel"
                  placeholder="012-345 6789"
                  value={lookupPhone}
                  onChange={(e) => setLookupPhone(e.target.value)}
                  required
                />
              </label>
              {lookupError && <ErrorBox>{lookupError}</ErrorBox>}
              <button type="submit" className={primaryBtn} disabled={lookupBusy || !lookupRef.trim() || !isPlausiblePhone(lookupPhone)}>
                {lookupBusy ? 'Menyemak…' : 'Semak'}
              </button>
            </form>
            {found && (
              <div className="border-t border-slate-100 pt-4" aria-live="polite">
                <p className="mb-2 font-mono text-sm font-bold tracking-widest">{found.reference}</p>
                <BookingSummary booking={found} />
                {found.can_cancel && (
                  <button
                    type="button"
                    onClick={doCancel}
                    disabled={lookupBusy}
                    className="mt-4 w-full rounded-xl border border-red-300 px-4 py-3 text-sm font-semibold text-red-700 hover:bg-red-50 disabled:opacity-40"
                  >
                    Batalkan tempahan
                  </button>
                )}
              </div>
            )}
          </section>
        ) : !info.enabled ? (
          <section className={`${card} text-center`}>
            <p className="font-semibold">Tempahan dalam talian belum dibuka</p>
            <p className="mt-1 text-sm text-slate-600">Sila hubungi kedai terus untuk membuat temujanji.</p>
          </section>
        ) : (
          <form onSubmit={submit} className="space-y-4">
            {info.note && (
              <p className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900 whitespace-pre-wrap">
                {info.note}
              </p>
            )}

            <section className={card}>
              <StepTitle n={1}>Pilih servis</StepTitle>
              <div className="space-y-2" role="radiogroup" aria-label="Servis">
                {info.services.map((s) => {
                  const selected = service?.id === s.id
                  return (
                    <button
                      key={s.id}
                      type="button"
                      role="radio"
                      aria-checked={selected}
                      onClick={() => setService(s)}
                      className={`flex w-full items-start justify-between gap-3 rounded-xl border px-4 py-3 text-left transition ${
                        selected ? 'border-slate-900 bg-slate-900 text-white' : 'border-slate-200 hover:border-slate-400'
                      }`}
                    >
                      <span className="min-w-0">
                        <span className="block font-semibold">{s.name}</span>
                        <span className={`block text-sm ${selected ? 'text-white/70' : 'text-slate-500'}`}>
                          {formatDuration(s.duration_min)}
                          {s.description ? ` · ${s.description}` : ''}
                        </span>
                      </span>
                      {s.price !== null && <span className="shrink-0 font-semibold tabular-nums">{formatPrice(s.price)}</span>}
                    </button>
                  )
                })}
              </div>
            </section>

            {service && (
              <section className={card}>
                <StepTitle n={2}>Pilih tarikh</StepTitle>
                <div className="-mx-1 flex gap-2 overflow-x-auto px-1 pb-2" role="radiogroup" aria-label="Tarikh">
                  {dates.map((d) => {
                    const selected = date === d.date
                    const day = Number(d.date.slice(8))
                    return (
                      <button
                        key={d.date}
                        type="button"
                        role="radio"
                        aria-checked={selected}
                        aria-label={formatDateMs(d.date) + (d.closed ? ' (tutup)' : '')}
                        disabled={d.closed}
                        onClick={() => setDate(d.date)}
                        className={`flex w-14 shrink-0 flex-col items-center rounded-xl border py-2 transition ${
                          selected
                            ? 'border-slate-900 bg-slate-900 text-white'
                            : d.closed
                              ? 'border-slate-100 bg-slate-50 text-slate-300'
                              : 'border-slate-200 hover:border-slate-400'
                        }`}
                      >
                        <span className="text-[11px]">{WEEKDAY_LABELS[d.weekday].slice(0, 3)}</span>
                        <span className="text-lg font-bold tabular-nums">{day}</span>
                        <span className="text-[10px]">{d.date === info.today ? 'Hari ini' : formatDateMs(d.date).split(' ')[2]}</span>
                      </button>
                    )
                  })}
                </div>
                {date && <p className="mt-1 text-sm text-slate-600">{formatDateMs(date)}</p>}
              </section>
            )}

            {service && date && (
              <section className={card} aria-live="polite">
                <StepTitle n={3}>Pilih masa</StepTitle>
                {slotsLoading ? (
                  <div className="flex justify-center py-6">
                    <div className="h-6 w-6 animate-spin rounded-full border-2 border-slate-300 border-t-slate-900" />
                  </div>
                ) : (
                  <>
                    {slots.length > 0 && (
                      <div className="grid grid-cols-3 gap-2 sm:grid-cols-4" role="radiogroup" aria-label="Masa">
                        {slots.map((s) => (
                          <button
                            key={s.time}
                            type="button"
                            role="radio"
                            aria-checked={time === s.time}
                            disabled={!s.available}
                            onClick={() => setTime(s.time)}
                            className={`rounded-xl border py-2.5 text-sm font-semibold tabular-nums transition ${
                              time === s.time
                                ? 'border-slate-900 bg-slate-900 text-white'
                                : s.available
                                  ? 'border-slate-200 hover:border-slate-400'
                                  : 'border-slate-100 bg-slate-50 text-slate-300 line-through'
                            }`}
                          >
                            {formatTime12(s.time)}
                          </button>
                        ))}
                      </div>
                    )}
                    {slotsMessage && <p className="mt-3 text-sm text-slate-600">{slotsMessage}</p>}
                  </>
                )}
              </section>
            )}

            {service && date && time && (
              <section className={`${card} space-y-3`}>
                <StepTitle n={4}>Maklumat anda</StepTitle>
                <label className="block text-sm font-medium text-slate-700">
                  Nama
                  <input className={`${input} mt-1`} value={name} maxLength={120} autoComplete="name" onChange={(e) => setName(e.target.value)} required />
                </label>
                <label className="block text-sm font-medium text-slate-700">
                  Nombor telefon (WhatsApp)
                  <input
                    className={`${input} mt-1`}
                    type="tel"
                    inputMode="tel"
                    autoComplete="tel"
                    placeholder="012-345 6789"
                    value={phone}
                    onChange={(e) => setPhone(e.target.value)}
                    required
                  />
                </label>
                <label className="block text-sm font-medium text-slate-700">
                  Nota (pilihan)
                  <textarea className={`${input} mt-1`} rows={2} maxLength={500} value={notes} onChange={(e) => setNotes(e.target.value)} />
                </label>
                <p className="rounded-xl bg-slate-50 px-4 py-3 text-sm text-slate-700">
                  <strong>{service.name}</strong> · {formatDateMs(date)} · {formatTime12(time)}
                  {service.price !== null ? ` · ${formatPrice(service.price)}` : ''}
                </p>
                {formError && <ErrorBox>{formError}</ErrorBox>}
                <button type="submit" className={primaryBtn} disabled={!canSubmit || submitting}>
                  {submitting ? 'Menghantar…' : 'Sahkan tempahan'}
                </button>
              </section>
            )}
          </form>
        )}

        <p className="text-center text-sm">
          {view === 'lookup' ? (
            <button type="button" onClick={() => setView(booking ? 'done' : 'book')} className="font-medium text-slate-600 underline">
              ← Kembali
            </button>
          ) : (
            <button type="button" onClick={() => setView('lookup')} className="font-medium text-slate-600 underline">
              Sudah menempah? Semak atau batalkan tempahan
            </button>
          )}
        </p>
      </div>
    </main>
  )
}
