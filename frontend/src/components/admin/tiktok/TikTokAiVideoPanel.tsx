'use client';

/**
 * "Generate AI video" — a vertical promo clip from 1–3 real photos + a brief,
 * made by the existing Wan 3.0 (DashScope) integration on the backend.
 *
 * Money is visible before anything runs: the estimate for the chosen
 * resolution × duration, today's usage against WAN_DAILY_VIDEO_LIMIT, and a
 * cost log of recent generations. The job is asynchronous: we poll until it
 * is ready, show the clip, and offer Regenerate (same inputs, new job) or
 * "Use this video", which hands the MP4 to the composer as if it had been
 * chosen with the file picker (and ticks "This content is AI-generated").
 */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import toast from 'react-hot-toast';
import { Button } from '@/components/ui';
import {
  aiVideoAsFile,
  createAiVideoJob,
  describeAiVideo,
  estimateAiVideoCost,
  fetchAiVideoConfig,
  fetchAiVideoJob,
  fetchAiVideoJobs,
  formatRm,
  isAiVideoActive,
  tiktokMediaUrl,
  type AiVideoConfig,
  type AiVideoJob,
  type AiVideoResolution,
} from '@/lib/tiktok';

interface Props {
  disabled?: boolean;
  onUseVideo: (file: File, job: AiVideoJob) => void;
}

const PHOTO_ACCEPT = 'image/jpeg,image/png,image/webp';

export function TikTokAiVideoPanel({ disabled, onUseVideo }: Props) {
  const [config, setConfig] = useState<AiVideoConfig | null>(null);
  const [configError, setConfigError] = useState<string | null>(null);
  const [photos, setPhotos] = useState<File[]>([]);
  const [previews, setPreviews] = useState<string[]>([]);
  const [brief, setBrief] = useState('');
  const [resolution, setResolution] = useState<AiVideoResolution>('720P');
  const [duration, setDuration] = useState(10);
  const [job, setJob] = useState<AiVideoJob | null>(null);
  const [starting, setStarting] = useState(false);
  const [using, setUsing] = useState(false);
  const [log, setLog] = useState<AiVideoJob[]>([]);
  const [logTotals, setLogTotals] = useState<{ count: number; estimated_cost_rm: number; estimated_cost_usd: number } | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const loadConfig = useCallback(async () => {
    try {
      const cfg = await fetchAiVideoConfig();
      setConfig(cfg);
      setResolution(cfg.default_resolution);
      setDuration(cfg.default_duration);
      setConfigError(null);
    } catch (err) {
      setConfigError((err as Error).message || 'Could not load AI video settings');
    }
  }, []);

  const loadLog = useCallback(async () => {
    try {
      const res = await fetchAiVideoJobs(10);
      setLog(res.jobs);
      setLogTotals(res.totals);
      setConfig((c) => (c ? { ...c, daily: res.daily } : c));
    } catch {
      /* the log is informational */
    }
  }, []);

  useEffect(() => {
    loadConfig();
    loadLog();
  }, [loadConfig, loadLog]);

  useEffect(() => {
    const urls = photos.map((f) => URL.createObjectURL(f));
    setPreviews(urls);
    return () => urls.forEach((u) => URL.revokeObjectURL(u));
  }, [photos]);

  // Poll the running job.
  useEffect(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
    if (!job || !isAiVideoActive(job)) return;
    const every = Math.max(3, config?.poll_interval_seconds ?? 5) * 1000;
    pollRef.current = setInterval(async () => {
      try {
        const { job: fresh } = await fetchAiVideoJob(job.id);
        setJob(fresh);
        if (!isAiVideoActive(fresh)) {
          const s = describeAiVideo(fresh);
          if (s.tone === 'ok') toast.success('AI video is ready — preview it below');
          else toast.error(s.label);
          loadLog();
        }
      } catch (err) {
        // transient; keep polling
        console.warn('[tiktok ai video] poll failed', err);
      }
    }, every);
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [job, config?.poll_interval_seconds, loadLog]);

  const estimate = useMemo(() => estimateAiVideoCost(config, resolution, duration), [config, resolution, duration]);
  const capReached = !!config && config.daily.remaining <= 0;
  const canGenerate =
    !!config?.enabled && !capReached && photos.length >= (config?.min_photos ?? 1) && !starting && !isAiVideoActive(job) && !disabled;

  const onPick = (list: FileList | null) => {
    const picked = Array.from(list || []);
    if (!picked.length) return;
    const max = config?.max_photos ?? 3;
    if (picked.length > max) {
      toast.error(`Up to ${max} photos.`);
      return;
    }
    const tooBig = picked.find((f) => f.size > 20 * 1024 * 1024);
    if (tooBig) {
      toast.error(`${tooBig.name} is over 20 MB (Wan 3.0 limit).`);
      return;
    }
    setPhotos(picked);
  };

  const generate = async () => {
    if (!config) return;
    setStarting(true);
    try {
      const res = await createAiVideoJob(photos, brief.trim(), resolution, duration);
      setJob(res.job);
      setConfig((c) => (c ? { ...c, daily: res.daily } : c));
      toast(`Generating… estimated ${estimate ? formatRm(estimate.rm) : ''}`.trim());
    } catch (err) {
      const e = err as { message?: string; code?: string | null };
      toast.error(e.message || 'Could not start the AI video');
      if (e.code === 'daily_limit') loadConfig();
      loadLog();
    } finally {
      setStarting(false);
    }
  };

  const useVideo = async () => {
    if (!job || job.status !== 'ready') return;
    setUsing(true);
    try {
      const file = await aiVideoAsFile(job);
      onUseVideo(file, job);
      toast.success('AI video loaded into the post — "AI-generated" is ticked for you');
    } catch (err) {
      toast.error((err as Error).message || 'Could not load the clip');
    } finally {
      setUsing(false);
    }
  };

  const videoSrc = job?.video_key ? tiktokMediaUrl(job.video_key) : null;

  return (
    <div className="rounded-2xl border border-ink-200 bg-ink-050/60 p-4 space-y-4" aria-labelledby="tt-ai-h">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <h3 id="tt-ai-h" className="text-sm font-semibold text-ink-900">Generate AI video (Wan 3.0)</h3>
          <p className="text-xs text-ink-500">
            Upload 1–3 real photos of the food, shop or product and a short brief. The clip is vertical 9:16 and the
            photos are used as references so the real product is shown.
          </p>
        </div>
        {config && (
          <span
            className={`rounded-full px-2.5 py-1 text-xs font-medium ${
              capReached ? 'bg-red-50 text-red-700' : 'bg-white text-ink-700 border border-ink-200'
            }`}
            title="Clips sent to Wan 3.0 today vs WAN_DAILY_VIDEO_LIMIT"
          >
            Today: {config.daily.used} / {config.daily.limit}
          </span>
        )}
      </div>

      {configError && (
        <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700" role="alert">
          {configError}{' '}
          <button className="underline" onClick={loadConfig}>
            Retry
          </button>
        </p>
      )}
      {config && !config.enabled && (
        <p className="rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-800" role="alert">
          AI video is not available: the backend needs DASHSCOPE_API_KEY and a wan3.x DASHSCOPE_VIDEO_MODEL.
        </p>
      )}

      {/* inputs */}
      <div className="grid gap-3 sm:grid-cols-2">
        <label className="block text-sm font-medium text-ink-800 sm:col-span-2">
          Reference photos (1–3, JPEG/PNG/WebP, up to 20 MB each)
          <input
            type="file"
            accept={PHOTO_ACCEPT}
            multiple
            disabled={disabled || isAiVideoActive(job)}
            onChange={(e) => onPick(e.target.files)}
            className="mt-2 block w-full text-sm text-ink-600 file:mr-3 file:rounded-lg file:border-0 file:bg-ink-900 file:px-3 file:py-2 file:text-white"
          />
        </label>
        {previews.length > 0 && (
          <div className="flex gap-2 sm:col-span-2">
            {previews.map((src, i) => (
              // eslint-disable-next-line @next/next/no-img-element
              <img key={src} src={src} alt={`Reference photo ${i + 1}`} className="h-20 w-20 rounded-lg object-cover ring-1 ring-ink-200" />
            ))}
          </div>
        )}
        <label className="block text-sm font-medium text-ink-800 sm:col-span-2">
          Brief
          <input
            value={brief}
            maxLength={config?.brief_max ?? 400}
            disabled={disabled || isAiVideoActive(job)}
            onChange={(e) => setBrief(e.target.value)}
            placeholder='e.g. "promo nasi kandar RM12, Khulafa Seksyen 7"'
            className="mt-1 w-full rounded-lg border border-ink-200 px-3 py-2 text-sm"
          />
        </label>
        <label className="block text-sm font-medium text-ink-800">
          Resolution
          <select
            value={resolution}
            disabled={disabled || isAiVideoActive(job)}
            onChange={(e) => setResolution(e.target.value as AiVideoResolution)}
            className="mt-1 w-full rounded-lg border border-ink-200 px-2 py-2 text-sm"
          >
            {(config?.resolutions ?? ['720P', '1080P']).map((r) => (
              <option key={r} value={r}>
                {r === '720P' ? '720p (default)' : r === '1080P' ? '1080p' : r}
              </option>
            ))}
          </select>
        </label>
        <label className="block text-sm font-medium text-ink-800">
          Duration
          <select
            value={duration}
            disabled={disabled || isAiVideoActive(job)}
            onChange={(e) => setDuration(Number(e.target.value))}
            className="mt-1 w-full rounded-lg border border-ink-200 px-2 py-2 text-sm"
          >
            {(config?.durations ?? [10, 15]).map((d) => (
              <option key={d} value={d}>
                {d} seconds
              </option>
            ))}
          </select>
        </label>
      </div>

      {/* estimate + action */}
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl bg-white border border-ink-200 px-3 py-2">
        <p className="text-sm text-ink-700" aria-live="polite">
          <span className="font-medium text-ink-900">Estimated cost:</span>{' '}
          {estimate ? (
            <>
              {formatRm(estimate.rm)} <span className="text-ink-500">(${estimate.usd.toFixed(2)} · {resolution} × {duration}s)</span>
            </>
          ) : (
            '—'
          )}
        </p>
        <div className="flex gap-2">
          {job && !isAiVideoActive(job) && (
            <Button variant="secondary" size="sm" onClick={generate} disabled={!canGenerate} loading={starting}>
              Regenerate
            </Button>
          )}
          {(!job || isAiVideoActive(job)) && (
            <Button size="sm" onClick={generate} disabled={!canGenerate} loading={starting || isAiVideoActive(job)}>
              {isAiVideoActive(job) ? 'Generating…' : 'Generate video'}
            </Button>
          )}
        </div>
      </div>
      {capReached && (
        <p className="text-xs text-red-700">Daily AI video limit reached ({config?.daily.used}/{config?.daily.limit}). Try again tomorrow.</p>
      )}

      {/* result */}
      {job && (
        <div className="rounded-xl bg-white border border-ink-200 p-3 space-y-3">
          {(() => {
            const s = describeAiVideo(job);
            const tone = s.tone === 'ok' ? 'text-emerald-600' : s.tone === 'err' ? 'text-red-600' : 'text-sky-600';
            return (
              <p className={`text-sm ${tone}`} role="status" aria-live="polite">
                {isAiVideoActive(job) && (
                  <span className="inline-block w-3 h-3 mr-1 align-middle border-2 border-current border-t-transparent rounded-full animate-spin" />
                )}
                {s.label}
                {job.status === 'failed' && (
                  <>
                    {' '}
                    <button className="underline" onClick={generate} disabled={!canGenerate}>
                      Try again
                    </button>
                  </>
                )}
              </p>
            );
          })()}
          {job.status === 'ready' && videoSrc && (
            <div className="flex flex-wrap gap-4 items-start">
              <video src={videoSrc} controls playsInline className="w-48 max-h-[26rem] rounded-xl bg-black" aria-label="AI video preview" />
              <div className="space-y-2 text-sm text-ink-600">
                <p>
                  {job.resolution} · {job.duration_sec}s · {job.video_bytes ? `${(job.video_bytes / (1024 * 1024)).toFixed(1)} MB` : ''}
                  <br />
                  Estimated cost {formatRm(job.estimated_cost_rm)}
                </p>
                <div className="flex gap-2">
                  <Button size="sm" onClick={useVideo} loading={using} disabled={disabled}>
                    Use this video
                  </Button>
                  <Button variant="secondary" size="sm" onClick={generate} disabled={!canGenerate} loading={starting}>
                    Regenerate
                  </Button>
                </div>
                <p className="text-xs text-ink-500">“Use this video” loads the clip into the post below and ticks “This content is AI-generated”.</p>
              </div>
            </div>
          )}
        </div>
      )}

      {/* cost log */}
      <details className="text-sm">
        <summary className="cursor-pointer text-ink-700">
          Cost log · {logTotals ? `${logTotals.count} clips, est. ${formatRm(logTotals.estimated_cost_rm)} ($${logTotals.estimated_cost_usd.toFixed(2)})` : '—'}
        </summary>
        {log.length === 0 ? (
          <p className="mt-2 text-xs text-ink-500">No AI videos generated yet.</p>
        ) : (
          <table className="mt-2 w-full text-xs">
            <thead className="text-ink-500">
              <tr>
                <th className="text-left font-medium py-1">When</th>
                <th className="text-left font-medium py-1">Brief</th>
                <th className="text-left font-medium py-1">Res × s</th>
                <th className="text-right font-medium py-1">Est. cost</th>
                <th className="text-left font-medium py-1 pl-3">Status</th>
              </tr>
            </thead>
            <tbody>
              {log.map((j) => (
                <tr key={j.id} className="border-t border-ink-100">
                  <td className="py-1 whitespace-nowrap">{j.created_at ? new Date(j.created_at).toLocaleString() : ''}</td>
                  <td className="py-1 truncate max-w-[12rem]">{j.brief || '—'}</td>
                  <td className="py-1 whitespace-nowrap">{j.resolution} × {j.duration_sec}</td>
                  <td className="py-1 text-right whitespace-nowrap">{j.submitted ? formatRm(j.estimated_cost_rm) : '—'}</td>
                  <td className="py-1 pl-3">{j.status}{!j.submitted && j.status === 'failed' ? ' (not charged)' : ''}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </details>
    </div>
  );
}
