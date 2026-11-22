'use client'

/**
 * Video Maskot — the merchant uploads a short clip of their shop or food,
 * picks a mascot, and gets the clip back with the mascot in the scene.
 *
 * Everything goes through /api/v1/mascot-videos/*. The feature is behind
 * MASCOT_VIDEO_ENABLED on the server: when it is off the config call 404s
 * and this page says the feature is not available yet.
 */

import { useCallback, useEffect, useRef, useState } from 'react'
import { useRouter } from 'next/navigation'

import DashboardHeader from '@/components/dashboard-new/DashboardHeader'
import {
  MASCOT_PRESETS,
  STATUS_LABEL,
  clipProblem,
  createMascotVideo,
  fetchMascotVideo,
  fetchMascotVideoConfig,
  fetchMascotVideos,
  generateMascot,
  isActive,
  readClipSeconds,
  applyMascotVideoToHero,
  type MascotChoice,
  type MascotVideoConfig,
  type MascotVideoJob,
} from '@/lib/mascotVideo'
import { getApiAuthToken, getCurrentUser, signOut, supabase } from '@/lib/supabase'

import { Button, Field, Notice, errorText, inputClass } from '../tempahan/components/ui'

import '@/components/dashboard-new/dashboard.css'

interface WebsiteOption {
  id: string
  label: string
}

type MascotPick =
  | { kind: 'preset'; key: string; src: string }
  | { kind: 'upload'; file: File; preview: string }
  | { kind: 'generated'; url: string }

export default function MascotVideoClient() {
  const router = useRouter()
  const [userName, setUserName] = useState('Pengguna')
  const [loading, setLoading] = useState(true)
  const [config, setConfig] = useState<MascotVideoConfig | null>(null)
  const [jobs, setJobs] = useState<MascotVideoJob[]>([])
  const [websites, setWebsites] = useState<WebsiteOption[]>([])
  const [websiteId, setWebsiteId] = useState('')
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')

  const [clip, setClip] = useState<File | null>(null)
  const [clipPreview, setClipPreview] = useState('')
  const [clipError, setClipError] = useState('')
  const [mascot, setMascot] = useState<MascotPick | null>(null)
  const [description, setDescription] = useState('')
  const [generating, setGenerating] = useState(false)
  const [prompt, setPrompt] = useState('')
  const [consent, setConsent] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [applying, setApplying] = useState('')

  const clipInput = useRef<HTMLInputElement>(null)
  const mascotInput = useRef<HTMLInputElement>(null)

  const refresh = useCallback(async () => {
    const token = await getApiAuthToken()
    if (!token) return
    const data = await fetchMascotVideos(token)
    setJobs(data.jobs)
    setConfig((current) => (current ? { ...current, daily: data.daily } : current))
  }, [])

  useEffect(() => {
    const load = async () => {
      const token = await getApiAuthToken()
      const user = await getCurrentUser()
      if (!token || !user) {
        router.push('/login')
        return
      }
      setUserName((user as any).user_metadata?.full_name || user.email || 'Pengguna')
      try {
        const cfg = await fetchMascotVideoConfig(token)
        setConfig(cfg)
        if (cfg) {
          setJobs((await fetchMascotVideos(token)).jobs)
          if (supabase) {
            const { data: rows } = await supabase
              .from('websites')
              .select('id, business_name, subdomain')
              .eq('user_id', user.id)
              .order('created_at', { ascending: false })
            const options = (rows || []).map((w: any) => ({
              id: w.id,
              label: w.business_name || w.subdomain || 'Website',
            }))
            setWebsites(options)
            setWebsiteId(options[0]?.id || '')
          }
        }
      } catch (err) {
        setError(errorText(err, 'Gagal memuatkan Video Maskot.'))
      }
      setLoading(false)
    }
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Poll while a job is in flight.
  const activeJob = jobs.find((job) => isActive(job.status))
  const activeId = activeJob?.id
  const pollSeconds = config?.poll_interval_seconds || 10
  useEffect(() => {
    if (!activeId) return
    const timer = setInterval(async () => {
      try {
        const token = await getApiAuthToken()
        if (!token) return
        const job = await fetchMascotVideo(token, activeId)
        setJobs((current) => current.map((j) => (j.id === job.id ? job : j)))
        if (!isActive(job.status)) refresh().catch(() => undefined)
      } catch {
        // A failed poll is retried on the next tick.
      }
    }, pollSeconds * 1000)
    return () => clearInterval(timer)
  }, [activeId, pollSeconds, refresh])

  useEffect(
    () => () => {
      if (clipPreview) URL.revokeObjectURL(clipPreview)
    },
    [clipPreview]
  )

  const pickClip = async (file: File | undefined) => {
    setClipError('')
    if (!file || !config) return
    const seconds = await readClipSeconds(file)
    const problem = clipProblem(file, seconds, config)
    if (problem) {
      setClip(null)
      setClipPreview('')
      setClipError(problem)
      return
    }
    setClip(file)
    setClipPreview(URL.createObjectURL(file))
  }

  const pickMascotFile = (file: File | undefined) => {
    if (!file || !config) return
    if (!['image/png', 'image/jpeg', 'image/webp'].includes(file.type)) {
      setError('Maskot mesti gambar PNG, JPEG atau WebP.')
      return
    }
    if (file.size > config.max_mascot_mb * 1024 * 1024) {
      setError(`Gambar maskot terlalu besar. Maksimum ${config.max_mascot_mb} MB.`)
      return
    }
    setError('')
    setMascot({ kind: 'upload', file, preview: URL.createObjectURL(file) })
  }

  const createMascot = async () => {
    setError('')
    setGenerating(true)
    try {
      const token = await getApiAuthToken()
      if (!token) throw new Error('Sesi tamat. Sila log masuk semula.')
      const url = await generateMascot(token, description.trim())
      setMascot({ kind: 'generated', url })
    } catch (err) {
      setError(errorText(err, 'Maskot tidak dapat dijana.'))
    }
    setGenerating(false)
  }

  const mascotChoice = async (pick: MascotPick): Promise<MascotChoice> => {
    if (pick.kind === 'generated') return { url: pick.url }
    if (pick.kind === 'upload') return { file: pick.file, name: pick.file.name }
    const res = await fetch(pick.src)
    if (!res.ok) throw new Error('Maskot tidak dapat dimuatkan.')
    return { file: await res.blob(), name: `${pick.key}.png` }
  }

  const submit = async () => {
    if (!clip || !mascot || !consent) return
    setError('')
    setNotice('')
    setSubmitting(true)
    try {
      const token = await getApiAuthToken()
      if (!token) throw new Error('Sesi tamat. Sila log masuk semula.')
      const job = await createMascotVideo(token, {
        clip,
        mascot: await mascotChoice(mascot),
        prompt: prompt.trim(),
        consent,
      })
      setJobs((current) => [job, ...current])
      setClip(null)
      setClipPreview('')
      setConsent(false)
      if (clipInput.current) clipInput.current.value = ''
    } catch (err) {
      setError(errorText(err, 'Video tidak dapat dijana.'))
    }
    setSubmitting(false)
  }

  const putOnHero = async (job: MascotVideoJob) => {
    if (!websiteId) return
    setError('')
    setNotice('')
    setApplying(job.id)
    try {
      const token = await getApiAuthToken()
      if (!token) throw new Error('Sesi tamat. Sila log masuk semula.')
      const result = await applyMascotVideoToHero(token, job.id, websiteId)
      setNotice(result.warning ? `${result.message} ${result.warning}` : result.message)
    } catch (err) {
      setError(errorText(err, 'Video tidak dapat dipasang pada hero.'))
    }
    setApplying('')
  }

  const mascotPreview =
    mascot?.kind === 'preset' ? mascot.src : mascot?.kind === 'upload' ? mascot.preview : mascot?.url
  const attemptsSpent =
    !!config && config.daily.attempt_limit !== undefined && (config.daily.attempts || 0) >= config.daily.attempt_limit
  const capReached = !!config && (config.daily.remaining <= 0 || attemptsSpent)
  const canSubmit =
    !!clip && !!mascot && consent && !submitting && !activeJob && !capReached && !!config?.available

  return (
    <div className="dash-bg min-h-screen font-geist">
      <div className="dash-dotgrid" />
      <div className="dash-glow-top" />
      <DashboardHeader userName={userName} onLogout={() => signOut()} />

      <main className="relative mx-auto max-w-5xl px-4 lg:px-6 py-6 space-y-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-xl font-semibold text-white tracking-tight">Video Maskot</h1>
            <p className="text-[13px] text-white/40 mt-0.5">
              Muat naik klip kedai atau makanan anda, pilih maskot, dan AI akan masukkan maskot ke dalam klip itu
            </p>
          </div>
          {config && (
            <span className="dash-tnum rounded-full border border-white/[0.08] bg-white/[0.04] px-3.5 py-1.5 text-xs text-white/70">
              Hari ini: {config.daily.used}/{config.daily.limit} video
            </span>
          )}
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-32">
            <div className="h-8 w-8 animate-spin rounded-full border-2 border-white/20 border-t-[#C7FF3D]" />
          </div>
        ) : !config ? (
          <div className="dash-surface p-10 text-center">
            <p className="text-white font-medium">Video Maskot belum tersedia</p>
            <p className="text-[13px] text-white/40 mt-1">
              {error || 'Ciri ini akan dibuka tidak lama lagi.'}
            </p>
          </div>
        ) : (
          <>
            {error && <Notice tone="error">{error}</Notice>}
            {notice && <Notice tone="success">{notice}</Notice>}
            {!config.available && (
              <Notice tone="info">Penjana video tidak tersedia buat masa ini. Sila cuba lagi nanti.</Notice>
            )}
            {capReached && (
              <Notice tone="info">
                {config.daily.remaining <= 0
                  ? `Had harian dicapai (${config.daily.used}/${config.daily.limit}). `
                  : 'Terlalu banyak percubaan hari ini. '}
                Anda boleh menjana video baharu esok.
              </Notice>
            )}

            <section className="dash-surface p-5 space-y-5">
              <div className="grid gap-5 md:grid-cols-2">
                {/* 1. clip */}
                <div className="space-y-2">
                  <p className="dash-eyebrow">1. Klip anda</p>
                  <input
                    ref={clipInput}
                    type="file"
                    accept="video/mp4,video/quicktime"
                    className="hidden"
                    onChange={(e) => pickClip(e.target.files?.[0])}
                  />
                  {clipPreview ? (
                    <video
                      src={clipPreview}
                      controls
                      muted
                      playsInline
                      className="aspect-video w-full rounded-xl border border-white/[0.08] bg-black object-contain"
                    />
                  ) : (
                    <button
                      type="button"
                      onClick={() => clipInput.current?.click()}
                      className="flex aspect-video w-full flex-col items-center justify-center rounded-xl border border-dashed border-white/[0.15] bg-white/[0.02] text-center transition hover:border-[#C7FF3D]/50"
                    >
                      <span className="text-sm font-medium text-white">Muat naik klip</span>
                      <span className="mt-1 text-[11px] text-white/40">
                        MP4 atau MOV · {config.min_clip_seconds}–{config.max_clip_seconds} saat · maksimum{' '}
                        {config.max_clip_mb} MB
                      </span>
                    </button>
                  )}
                  {clipPreview && (
                    <Button onClick={() => clipInput.current?.click()}>Tukar klip</Button>
                  )}
                  {clipError && <p className="text-xs text-[#FF9A9D]">{clipError}</p>}
                </div>

                {/* 2. mascot */}
                <div className="space-y-3">
                  <p className="dash-eyebrow">2. Maskot</p>
                  <div className="flex flex-wrap gap-2">
                    {MASCOT_PRESETS.map((preset) => {
                      const selected = mascot?.kind === 'preset' && mascot.key === preset.key
                      return (
                        <button
                          key={preset.key}
                          type="button"
                          aria-pressed={selected}
                          onClick={() => setMascot({ kind: 'preset', key: preset.key, src: preset.src })}
                          className={`w-24 rounded-xl border p-1.5 text-center transition ${
                            selected ? 'border-[#C7FF3D] bg-[#C7FF3D]/10' : 'border-white/[0.08] hover:border-white/30'
                          }`}
                        >
                          {/* eslint-disable-next-line @next/next/no-img-element */}
                          <img src={preset.src} alt={preset.label} className="aspect-square w-full rounded-lg bg-white object-contain" />
                          <span className="mt-1 block text-[11px] text-white/70">{preset.label}</span>
                        </button>
                      )
                    })}
                    {mascot && mascot.kind !== 'preset' && mascotPreview && (
                      <div className="w-24 rounded-xl border border-[#C7FF3D] bg-[#C7FF3D]/10 p-1.5 text-center">
                        {/* eslint-disable-next-line @next/next/no-img-element */}
                        <img src={mascotPreview} alt="Maskot anda" className="aspect-square w-full rounded-lg bg-white object-contain" />
                        <span className="mt-1 block text-[11px] text-white/70">Maskot anda</span>
                      </div>
                    )}
                  </div>
                  <input
                    ref={mascotInput}
                    type="file"
                    accept="image/png,image/jpeg,image/webp"
                    className="hidden"
                    onChange={(e) => pickMascotFile(e.target.files?.[0])}
                  />
                  <Button onClick={() => mascotInput.current?.click()}>Muat naik maskot sendiri</Button>
                  <Field label="Atau cipta maskot baharu" hint="Contoh: kucing oren comel memakai apron merah">
                    <div className="flex gap-2">
                      <input
                        value={description}
                        maxLength={config.mascot_description_max}
                        onChange={(e) => setDescription(e.target.value)}
                        placeholder="Terangkan maskot anda"
                        className={inputClass}
                      />
                      <Button
                        className="shrink-0"
                        disabled={generating || description.trim().length < 3}
                        onClick={createMascot}
                      >
                        {generating ? 'Mencipta…' : 'Cipta'}
                      </Button>
                    </div>
                  </Field>
                </div>
              </div>

              <Field label="3. Apa yang maskot buat? (pilihan)" hint="Kosongkan untuk maskot tersenyum dan melambai">
                <input
                  value={prompt}
                  maxLength={config.prompt_max}
                  onChange={(e) => setPrompt(e.target.value)}
                  placeholder="Contoh: melambai sambil memegang secawan teh tarik"
                  className={inputClass}
                />
              </Field>

              <label className="flex items-start gap-2.5 text-[13px] text-white/70">
                <input
                  type="checkbox"
                  checked={consent}
                  onChange={(e) => setConsent(e.target.checked)}
                  className="mt-0.5 h-4 w-4 shrink-0 accent-[#C7FF3D]"
                />
                <span>
                  Saya mengesahkan bahawa semua orang yang kelihatan dalam klip ini telah bersetuju untuk dirakam dan
                  klip ini digunakan.
                </span>
              </label>

              <div className="flex flex-wrap items-center gap-3">
                <Button variant="primary" disabled={!canSubmit} onClick={submit}>
                  {submitting ? 'Memuat naik…' : 'Jana video'}
                </Button>
                {activeJob && (
                  <span className="text-xs text-white/50">Satu video sedang dijana. Tunggu sehingga ia siap.</span>
                )}
              </div>
            </section>

            <section className="space-y-3">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <p className="dash-eyebrow">Video anda</p>
                {websites.length > 1 && (
                  <select
                    aria-label="Website untuk video hero"
                    value={websiteId}
                    onChange={(e) => setWebsiteId(e.target.value)}
                    className="rounded-full bg-white/[0.05] border border-white/[0.08] px-3.5 py-1.5 text-xs text-white/80 focus:outline-none focus:border-[#C7FF3D]/50"
                  >
                    {websites.map((w) => (
                      <option key={w.id} value={w.id} className="bg-[#161623]">
                        {w.label}
                      </option>
                    ))}
                  </select>
                )}
              </div>
              {jobs.length === 0 ? (
                <div className="dash-surface p-8 text-center text-[13px] text-white/40">
                  Belum ada video. Jana video pertama anda di atas.
                </div>
              ) : (
                <div className="grid gap-4 sm:grid-cols-2">
                  {jobs.map((job) => (
                    <article key={job.id} className="dash-surface overflow-hidden">
                      <div className="relative aspect-video bg-black">
                        {job.status === 'ready' && job.result_url ? (
                          // The "Dijana AI" label is burned into the file itself.
                          <video
                            src={job.result_url}
                            controls
                            loop
                            muted
                            playsInline
                            className="h-full w-full object-contain"
                          />
                        ) : (
                          <div className="flex h-full flex-col items-center justify-center gap-3 px-6 text-center">
                            {isActive(job.status) && (
                              <div className="h-7 w-7 animate-spin rounded-full border-2 border-white/20 border-t-[#C7FF3D]" />
                            )}
                            <p className={`text-sm ${isActive(job.status) ? 'text-white/80' : 'text-[#FF9A9D]'}`}>
                              {STATUS_LABEL[job.status]}
                            </p>
                            {!isActive(job.status) && job.error && (
                              <p className="text-xs text-white/50">{job.error}</p>
                            )}
                          </div>
                        )}
                      </div>
                      <div className="flex flex-wrap items-center justify-between gap-2 p-3">
                        <span className="dash-tnum text-[11px] text-white/40">
                          {new Date(job.created_at).toLocaleString('ms-MY', { dateStyle: 'medium', timeStyle: 'short' })}
                        </span>
                        {job.status === 'ready' && job.result_url && (
                          <div className="flex gap-2">
                            <a
                              href={job.result_url}
                              download={`video-maskot-${job.id.slice(0, 8)}.mp4`}
                              className="rounded-full border border-white/[0.08] bg-white/[0.06] px-4 py-2 text-xs font-semibold text-white/80 transition hover:bg-white/[0.1]"
                            >
                              Muat turun
                            </a>
                            {websiteId && (
                              <Button
                                variant="primary"
                                disabled={applying === job.id}
                                onClick={() => putOnHero(job)}
                              >
                                {applying === job.id ? 'Memasang…' : 'Guna sebagai video hero'}
                              </Button>
                            )}
                          </div>
                        )}
                      </div>
                    </article>
                  ))}
                </div>
              )}
            </section>
          </>
        )}
      </main>
    </div>
  )
}
