'use client'

import { useEffect, useState } from 'react'

import {
  WEEKDAYS,
  WEEKDAY_LABELS,
  fetchSettings,
  formatDateMs,
  hoursProblem,
  saveSettings,
  type BookingSettings,
  type Weekday,
} from '@/lib/booking'

import { Button, Field, Notice, TextInput, errorText, inputClass } from './ui'

const INTERVALS = [15, 20, 30, 45, 60, 90, 120]
const LEAD_TIMES: Array<[number, string]> = [
  [0, 'Tiada'],
  [30, '30 minit'],
  [60, '1 jam'],
  [120, '2 jam'],
  [240, '4 jam'],
  [720, '12 jam'],
  [1440, '1 hari'],
  [2880, '2 hari'],
]

function clampInt(raw: string, min: number, max: number, fallback: number): number {
  const n = parseInt(raw, 10)
  if (Number.isNaN(n)) return fallback
  return Math.max(min, Math.min(max, n))
}

export default function SettingsTab({ websiteId }: { websiteId: string }) {
  const [settings, setSettings] = useState<BookingSettings | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [saved, setSaved] = useState(false)
  const [newClosed, setNewClosed] = useState('')

  useEffect(() => {
    let stale = false
    setLoading(true)
    fetchSettings(websiteId)
      .then((s) => !stale && setSettings(s))
      .catch((err) => !stale && setError(errorText(err, 'Gagal memuatkan tetapan.')))
      .finally(() => !stale && setLoading(false))
    return () => {
      stale = true
    }
  }, [websiteId])

  const patch = (changes: Partial<BookingSettings>) => {
    setSaved(false)
    setSettings((s) => (s ? { ...s, ...changes } : s))
  }

  const setDay = (day: Weekday, ranges: BookingSettings['weekly_hours'][Weekday]) => {
    if (!settings) return
    patch({ weekly_hours: { ...settings.weekly_hours, [day]: ranges } })
  }

  const save = async () => {
    if (!settings) return
    for (const day of WEEKDAYS) {
      const problem = hoursProblem(settings.weekly_hours[day] || [])
      if (problem) {
        setError(`${WEEKDAY_LABELS[day]}: ${problem}`)
        return
      }
    }
    setSaving(true)
    setError('')
    try {
      setSettings(await saveSettings(websiteId, settings))
      setSaved(true)
    } catch (err) {
      setError(errorText(err, 'Gagal menyimpan tetapan.'))
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return (
      <div className="flex justify-center py-16">
        <div className="h-7 w-7 animate-spin rounded-full border-2 border-white/20 border-t-[#C7FF3D]" />
      </div>
    )
  }
  if (!settings) return <Notice tone="error">{error || 'Gagal memuatkan tetapan.'}</Notice>

  return (
    <div className="space-y-4">
      {error && <Notice tone="error">{error}</Notice>}
      {saved && <Notice tone="success">Tetapan disimpan.</Notice>}

      <div className="dash-surface p-5 flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-white">Tempahan dalam talian</p>
          <p className="text-[12px] text-white/45">
            {settings.enabled
              ? 'Dibuka — pelanggan boleh menempah slot melalui pautan tempahan.'
              : 'Ditutup — halaman tempahan memaparkan "belum dibuka".'}
          </p>
        </div>
        <button
          type="button"
          role="switch"
          aria-checked={settings.enabled}
          aria-label="Buka tempahan dalam talian"
          onClick={() => patch({ enabled: !settings.enabled })}
          className={`relative h-7 w-12 rounded-full transition ${settings.enabled ? 'bg-[#C7FF3D]' : 'bg-white/15'}`}
        >
          <span
            className={`absolute top-1 h-5 w-5 rounded-full bg-black transition-all ${settings.enabled ? 'left-6' : 'left-1'}`}
          />
        </button>
      </div>

      <div className="dash-surface p-5 space-y-3">
        <h2 className="text-sm font-semibold text-white">Waktu operasi</h2>
        {WEEKDAYS.map((day) => {
          const ranges = settings.weekly_hours[day] || []
          return (
            <div key={day} className="flex flex-wrap items-start gap-3 border-t border-white/[0.06] pt-3 first:border-0 first:pt-0">
              <p className="w-20 pt-2 text-sm text-white/80">{WEEKDAY_LABELS[day]}</p>
              <div className="flex-1 space-y-2">
                {ranges.length === 0 && <p className="pt-2 text-[13px] text-white/35">Tutup</p>}
                {ranges.map((range, i) => (
                  <div key={i} className="flex items-center gap-2">
                    <input
                      type="time"
                      aria-label={`${WEEKDAY_LABELS[day]} buka`}
                      value={range.open}
                      onChange={(e) =>
                        setDay(day, ranges.map((r, j) => (j === i ? { ...r, open: e.target.value } : r)))
                      }
                      className={`${inputClass} !w-32`}
                    />
                    <span className="text-white/40 text-sm">hingga</span>
                    <input
                      type="time"
                      aria-label={`${WEEKDAY_LABELS[day]} tutup`}
                      value={range.close === '24:00' ? '23:59' : range.close}
                      onChange={(e) =>
                        setDay(day, ranges.map((r, j) => (j === i ? { ...r, close: e.target.value } : r)))
                      }
                      className={`${inputClass} !w-32`}
                    />
                    <button
                      type="button"
                      aria-label="Buang julat masa"
                      onClick={() => setDay(day, ranges.filter((_, j) => j !== i))}
                      className="px-2 text-white/40 hover:text-[#FF9A9D]"
                    >
                      ✕
                    </button>
                  </div>
                ))}
              </div>
              {ranges.length < 4 && (
                <Button
                  onClick={() =>
                    setDay(day, [
                      ...ranges,
                      ranges.length === 0
                        ? { open: '09:00', close: '18:00' }
                        : { open: ranges[ranges.length - 1].close, close: '22:00' },
                    ])
                  }
                >
                  {ranges.length === 0 ? 'Buka' : '+ Julat'}
                </Button>
              )}
            </div>
          )
        })}
        <p className="text-[11px] text-white/35">
          Tambah dua julat untuk waktu rehat (cth. 9:00–13:00 dan 14:00–18:00).
        </p>
      </div>

      <div className="dash-surface p-5 grid grid-cols-1 sm:grid-cols-2 gap-4">
        <Field label="Jarak antara slot">
          <select
            value={settings.slot_interval_min}
            onChange={(e) => patch({ slot_interval_min: Number(e.target.value) })}
            className={inputClass}
          >
            {[...new Set([...INTERVALS, settings.slot_interval_min])].sort((a, b) => a - b).map((m) => (
              <option key={m} value={m} className="bg-[#161623]">
                Setiap {m} minit
              </option>
            ))}
          </select>
        </Field>
        <Field label="Pelanggan serentak setiap slot" hint="cth. 2 jika ada dua kerusi / dua staf">
          <TextInput
            type="number"
            min={1}
            max={50}
            value={settings.capacity_per_slot}
            onChange={(e) => patch({ capacity_per_slot: clampInt(e.target.value, 1, 50, 1) })}
          />
        </Field>
        <Field label="Notis minimum" hint="Slot yang terlalu hampir tidak boleh ditempah">
          <select
            value={settings.lead_time_min}
            onChange={(e) => patch({ lead_time_min: Number(e.target.value) })}
            className={inputClass}
          >
            {!LEAD_TIMES.some(([m]) => m === settings.lead_time_min) && (
              <option value={settings.lead_time_min} className="bg-[#161623]">
                {settings.lead_time_min} minit
              </option>
            )}
            {LEAD_TIMES.map(([m, label]) => (
              <option key={m} value={m} className="bg-[#161623]">
                {label}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Tempahan dibuka berapa hari ke hadapan">
          <TextInput
            type="number"
            min={1}
            max={180}
            value={settings.max_days_ahead}
            onChange={(e) => patch({ max_days_ahead: clampInt(e.target.value, 1, 180, 30) })}
          />
        </Field>
      </div>

      <div className="dash-surface p-5 space-y-3">
        <h2 className="text-sm font-semibold text-white">Tarikh tutup (cuti)</h2>
        <div className="flex flex-wrap items-center gap-2">
          <input
            type="date"
            aria-label="Tarikh tutup baru"
            value={newClosed}
            onChange={(e) => setNewClosed(e.target.value)}
            className={`${inputClass} !w-44`}
          />
          <Button
            disabled={!newClosed || settings.closed_dates.includes(newClosed)}
            onClick={() => {
              patch({ closed_dates: [...settings.closed_dates, newClosed].sort() })
              setNewClosed('')
            }}
          >
            Tambah
          </Button>
        </div>
        {settings.closed_dates.length === 0 ? (
          <p className="text-[13px] text-white/35">Tiada tarikh tutup.</p>
        ) : (
          <ul className="flex flex-wrap gap-2">
            {settings.closed_dates.map((d) => (
              <li key={d} className="flex items-center gap-2 rounded-full bg-white/[0.06] px-3 py-1 text-xs text-white/75">
                {formatDateMs(d)}
                <button
                  type="button"
                  aria-label={`Buang ${d}`}
                  onClick={() => patch({ closed_dates: settings.closed_dates.filter((x) => x !== d) })}
                  className="text-white/40 hover:text-[#FF9A9D]"
                >
                  ✕
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="dash-surface p-5">
        <Field label="Nota untuk pelanggan (pilihan)" hint="Dipaparkan di halaman tempahan — cth. syarat deposit, tempat letak kereta">
          <textarea
            rows={3}
            maxLength={500}
            value={settings.note}
            onChange={(e) => patch({ note: e.target.value })}
            className={inputClass}
          />
        </Field>
      </div>

      <Button variant="primary" onClick={save} disabled={saving} className="!px-6 !py-2.5">
        {saving ? 'Menyimpan…' : 'Simpan tetapan'}
      </Button>
    </div>
  )
}
