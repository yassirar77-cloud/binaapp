'use client';

/**
 * The "Post to TikTok" form, laid out the way TikTok's Content Sharing
 * Guidelines for Direct Post require:
 *
 *  1. media + preview (video or up to 35 photos)
 *  2. caption (editable; AI draft button; UTF-16 counter against the limit)
 *  3. creator settings fetched fresh from creator_info/query:
 *     - "Posting to <nickname>"
 *     - privacy dropdown: only privacy_level_options, NO default
 *     - Allow comments / Duet / Stitch: off by default, disabled when the
 *       creator's settings disallow them; photos show only comments
 *     - commercial content disclosure: off by default; Your brand /
 *       Branded content with the exact label wording; posting blocked until
 *       one is picked; Branded content ⟂ "Only you"
 *     - the Music Usage Confirmation / Branded Content Policy declaration
 *     - the "may take a few minutes to process" notice
 *  4. two actions: "Send to TikTok drafts" (inbox) and "Post now" (direct),
 *     each behind an explicit confirm step.
 */

import { useCallback, useEffect, useMemo, useState } from 'react';
import toast from 'react-hot-toast';
import { Button } from '@/components/ui';
import { confirmDialog } from '@/components/ui/popups';
import { TikTokAiVideoPanel } from '@/components/admin/tiktok/TikTokAiVideoPanel';
import {
  BRANDED_CONTENT_POLICY_URL,
  DISCLOSURE_COPY,
  EMPTY_DRAFT,
  MUSIC_USAGE_URL,
  PRIVACY_LABELS,
  brandedContentDisabled,
  checkDraft,
  createTikTokPost,
  declarationText,
  draftTikTokCaption,
  fetchCreatorInfo,
  privacyOptionDisabled,
  privacyOptions,
  probeVideoDuration,
  utf16Length,
  type AiVideoJob,
  type CreatorInfo,
  type MediaType,
  type PostDraft,
  type PrivacyLevel,
  type TikTokAccount,
  type TikTokConfig,
  type TikTokPost,
} from '@/lib/tiktok';

interface Props {
  config: TikTokConfig;
  account: TikTokAccount;
  onPostCreated: (post: TikTokPost, notice: string) => void;
  onAuthError: (message: string) => void;
}

const VIDEO_ACCEPT = 'video/mp4,video/quicktime,video/webm,.mp4,.mov,.webm';
const PHOTO_ACCEPT = 'image/jpeg,image/png,image/webp';

function formatBytes(n: number): string {
  if (n < 1024 * 1024) return `${Math.round(n / 1024)} KB`;
  return `${(n / (1024 * 1024)).toFixed(1)} MB`;
}

export function TikTokComposer({ config, account, onPostCreated, onAuthError }: Props) {
  const [mediaType, setMediaType] = useState<MediaType>('video');
  // Where the video comes from: the file picker, or a Wan 3.0 clip made here.
  const [videoSource, setVideoSource] = useState<'file' | 'ai'>('file');
  const [aiSourceJob, setAiSourceJob] = useState<AiVideoJob | null>(null);
  const [files, setFiles] = useState<File[]>([]);
  const [previews, setPreviews] = useState<string[]>([]);
  const [draft, setDraft] = useState<PostDraft>(EMPTY_DRAFT);
  const [creator, setCreator] = useState<CreatorInfo | null>(null);
  const [creatorError, setCreatorError] = useState<string | null>(null);
  const [loadingCreator, setLoadingCreator] = useState(false);
  const [brief, setBrief] = useState('');
  const [language, setLanguage] = useState<'ms' | 'en' | 'mixed'>('mixed');
  const [drafting, setDrafting] = useState(false);
  const [submitting, setSubmitting] = useState<'direct' | 'inbox' | null>(null);
  const [uploadPct, setUploadPct] = useState(0);

  // ---- creator info: fetched fresh whenever the form is shown -------------
  const loadCreator = useCallback(async () => {
    setLoadingCreator(true);
    setCreatorError(null);
    try {
      const info = await fetchCreatorInfo();
      setCreator(info);
      // A previously chosen privacy that the account no longer offers is cleared.
      setDraft((d) =>
        d.privacy_level && !info.privacy_level_options.includes(d.privacy_level) ? { ...d, privacy_level: null } : d,
      );
    } catch (err) {
      const e = err as { message?: string; status?: number; code?: string | null };
      setCreator(null);
      setCreatorError(e.message || 'Could not load creator settings.');
      if (e.status === 401) onAuthError(e.message || 'TikTok session expired');
    } finally {
      setLoadingCreator(false);
    }
  }, [onAuthError]);

  useEffect(() => {
    loadCreator();
  }, [loadCreator, account.id]);

  // ---- media -----------------------------------------------------------------
  useEffect(() => {
    const urls = files.map((f) => URL.createObjectURL(f));
    setPreviews(urls);
    return () => urls.forEach((u) => URL.revokeObjectURL(u));
  }, [files]);

  const onPickFiles = async (list: FileList | null) => {
    const picked = Array.from(list || []);
    if (!picked.length) return;
    if (mediaType === 'video') {
      const file = picked[0];
      const maxBytes = config.max_upload_mb * 1024 * 1024;
      if (file.size > maxBytes) {
        toast.error(`Video is ${formatBytes(file.size)}; the upload limit is ${config.max_upload_mb} MB.`);
        return;
      }
      setFiles([file]);
      setAiSourceJob(null);
      const duration = await probeVideoDuration(file);
      setDraft((d) => ({ ...d, media_type: 'video', duration_sec: duration }));
    } else {
      if (picked.length > config.limits.max_photos) {
        toast.error(`TikTok allows up to ${config.limits.max_photos} photos per post.`);
        return;
      }
      setFiles(picked);
      setDraft((d) => ({ ...d, media_type: 'photo', duration_sec: null, photo_cover_index: 0 }));
    }
  };

  const switchMediaType = (t: MediaType) => {
    setMediaType(t);
    setFiles([]);
    setAiSourceJob(null);
    if (t === 'photo') setVideoSource('file');
    setDraft((d) => ({ ...d, media_type: t, duration_sec: null, allow_duet: false, allow_stitch: false }));
  };

  /** "Use this video" from the AI panel: load the clip exactly as if it had
   *  been picked with the file input, and tick the AIGC label for the admin. */
  const useAiVideo = async (file: File, job: AiVideoJob) => {
    setMediaType('video');
    setFiles([file]);
    setAiSourceJob(job);
    const duration = await probeVideoDuration(file);
    setDraft((d) => ({
      ...d,
      media_type: 'video',
      duration_sec: duration ?? job.duration_sec,
      is_aigc: true,
    }));
  };

  // ---- derived ---------------------------------------------------------------
  const options = useMemo(() => privacyOptions(creator), [creator]);
  const directCheck = useMemo(
    () => checkDraft({ ...draft, mode: 'direct' }, creator, config.limits, files.length > 0),
    [draft, creator, config.limits, files.length],
  );
  const inboxCheck = useMemo(
    () => checkDraft({ ...draft, mode: 'inbox' }, creator, config.limits, files.length > 0),
    [draft, creator, config.limits, files.length],
  );
  const declaration = declarationText(draft);
  const titleMax = mediaType === 'video' ? config.limits.video_title_max : config.limits.photo_title_max;
  const titleLen = utf16Length(draft.title);
  const busy = submitting !== null;

  // ---- actions ---------------------------------------------------------------
  const onDraftCaption = async () => {
    setDrafting(true);
    try {
      const res = await draftTikTokCaption(brief, language, mediaType);
      setDraft((d) => ({ ...d, title: res.caption }));
      toast.success(`Caption drafted (${res.provider}). Edit it as you like.`);
    } catch (err) {
      toast.error((err as Error).message || 'Could not draft a caption');
    } finally {
      setDrafting(false);
    }
  };

  const submit = async (mode: 'direct' | 'inbox') => {
    const check = mode === 'direct' ? directCheck : inboxCheck;
    if (!check.ok) {
      toast.error(check.problems[0]);
      return;
    }
    const who = creator?.creator_nickname || account.display_name || 'your TikTok account';
    const privacyLabel = draft.privacy_level ? PRIVACY_LABELS[draft.privacy_level] : '—';
    const disclosures = draft.disclose_commercial
      ? [draft.your_brand && 'Your brand (Promotional content)', draft.branded_content && 'Branded content (Paid partnership)']
          .filter(Boolean)
          .join(' + ')
      : 'none';
    const confirmed = await confirmDialog({
      title: mode === 'direct' ? `Post now to ${who}?` : `Send to ${who}'s TikTok drafts?`,
      message:
        mode === 'direct' ? (
          <div className="space-y-1 text-sm">
            <p>
              <strong>Who can view:</strong> {privacyLabel}
            </p>
            <p>
              <strong>Commercial disclosure:</strong> {disclosures}
            </p>
            <p>
              <strong>Caption:</strong> {draft.title ? draft.title.slice(0, 140) : '(none)'}
              {draft.title.length > 140 ? '…' : ''}
            </p>
            <p className="text-ink-500 pt-1">{declaration.text}</p>
          </div>
        ) : (
          <p className="text-sm">
            The {mediaType} will appear in the TikTok app inbox as a draft. Caption, privacy and settings are chosen
            in the app before it goes live.
          </p>
        ),
      confirmText: mode === 'direct' ? 'Post now' : 'Send to drafts',
      cancelText: 'Cancel',
    });
    if (!confirmed) return;

    setSubmitting(mode);
    setUploadPct(0);
    try {
      const res = await createTikTokPost({ ...draft, mode, media_type: mediaType }, files, setUploadPct);
      onPostCreated(res.post, res.processing_notice);
      setFiles([]);
      setAiSourceJob(null);
      setDraft((d) => ({ ...EMPTY_DRAFT, media_type: d.media_type }));
    } catch (err) {
      const e = err as { message?: string; status?: number };
      toast.error(e.message || 'TikTok rejected the post');
      if (e.status === 401) onAuthError(e.message || 'TikTok session expired');
    } finally {
      setSubmitting(null);
    }
  };

  // ---- render ----------------------------------------------------------------
  const toggle = (key: keyof PostDraft) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setDraft((d) => ({ ...d, [key]: e.target.checked }));

  return (
    <section className="rounded-2xl border border-ink-200 bg-white p-5 shadow-soft space-y-6" aria-labelledby="tt-compose-h">
      <div className="flex items-center justify-between gap-3">
        <h2 id="tt-compose-h" className="text-base font-semibold text-ink-900">
          Post to TikTok
        </h2>
        <div className="inline-flex rounded-xl border border-ink-200 p-0.5 text-sm" role="tablist" aria-label="Media type">
          {(['video', 'photo'] as MediaType[]).map((t) => (
            <button
              key={t}
              role="tab"
              aria-selected={mediaType === t}
              disabled={busy}
              onClick={() => switchMediaType(t)}
              className={`px-3 py-1.5 rounded-lg ${mediaType === t ? 'bg-ink-900 text-white' : 'text-ink-600 hover:bg-ink-050'}`}
            >
              {t === 'video' ? 'Video' : 'Photos'}
            </button>
          ))}
        </div>
      </div>

      {/* 1. Media */}
      <div className="space-y-3">
        {mediaType === 'video' && (
          <div className="inline-flex rounded-xl border border-ink-200 p-0.5 text-sm" role="tablist" aria-label="Video source">
            {(['file', 'ai'] as const).map((src) => (
              <button
                key={src}
                role="tab"
                aria-selected={videoSource === src}
                disabled={busy}
                onClick={() => setVideoSource(src)}
                className={`px-3 py-1.5 rounded-lg ${videoSource === src ? 'bg-ink-900 text-white' : 'text-ink-600 hover:bg-ink-050'}`}
              >
                {src === 'file' ? 'Choose file' : '✨ Generate AI video'}
              </button>
            ))}
          </div>
        )}

        {mediaType === 'video' && videoSource === 'ai' && (
          <TikTokAiVideoPanel disabled={busy} onUseVideo={useAiVideo} />
        )}

        {(mediaType === 'photo' || videoSource === 'file') && (
          <label className="block text-sm font-medium text-ink-800">
            {mediaType === 'video' ? 'Video (MP4 H.264, MOV or WebM)' : `Photos (JPEG, PNG or WebP · up to ${config.limits.max_photos})`}
            <input
              type="file"
              className="mt-2 block w-full text-sm text-ink-600 file:mr-3 file:rounded-lg file:border-0 file:bg-ink-900 file:px-3 file:py-2 file:text-white"
              accept={mediaType === 'video' ? VIDEO_ACCEPT : PHOTO_ACCEPT}
              multiple={mediaType === 'photo'}
              disabled={busy}
              onChange={(e) => onPickFiles(e.target.files)}
            />
          </label>
        )}

        {files.length > 0 && mediaType === 'video' && (
          <div className="flex flex-wrap gap-4 items-start">
            <video src={previews[0]} controls className="w-56 max-h-96 rounded-xl bg-black" aria-label="Video preview" />
            <dl className="text-sm text-ink-600 space-y-1">
              <div>
                <dt className="inline font-medium text-ink-800">File: </dt>
                <dd className="inline">{files[0].name} · {formatBytes(files[0].size)}</dd>
              </div>
              {aiSourceJob && (
                <div>
                  <dt className="inline font-medium text-ink-800">Source: </dt>
                  <dd className="inline">AI video (Wan 3.0, {aiSourceJob.resolution}) — labelled AI-generated</dd>
                </div>
              )}
              <div>
                <dt className="inline font-medium text-ink-800">Duration: </dt>
                <dd className="inline">
                  {draft.duration_sec != null ? `${Math.round(draft.duration_sec)}s` : 'reading…'}
                  {creator?.max_video_post_duration_sec ? ` (this account: up to ${creator.max_video_post_duration_sec}s)` : ''}
                </dd>
              </div>
            </dl>
          </div>
        )}
        {files.length > 0 && mediaType === 'photo' && (
          <div className="space-y-2">
            <div className="grid grid-cols-3 sm:grid-cols-5 gap-2">
              {previews.map((src, i) => (
                <button
                  type="button"
                  key={src}
                  onClick={() => setDraft((d) => ({ ...d, photo_cover_index: i }))}
                  className={`relative aspect-[3/4] overflow-hidden rounded-xl border-2 ${
                    draft.photo_cover_index === i ? 'border-brand-500' : 'border-transparent'
                  }`}
                  aria-label={`Photo ${i + 1}${draft.photo_cover_index === i ? ' (cover)' : ''}`}
                >
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img src={src} alt="" className="h-full w-full object-cover" />
                  {draft.photo_cover_index === i && (
                    <span className="absolute bottom-1 left-1 rounded bg-brand-500 px-1.5 text-[10px] font-semibold text-white">
                      Cover
                    </span>
                  )}
                </button>
              ))}
            </div>
            <p className="text-xs text-ink-500">
              Tap a photo to make it the cover. Photos are staged at {config.photo_media_public_base}/… for TikTok to
              fetch (that prefix must be verified in the TikTok developer portal).
            </p>
          </div>
        )}
      </div>

      {/* 2. Caption */}
      <div className="space-y-3">
        <div className="flex items-end justify-between gap-3">
          <label htmlFor="tt-caption" className="text-sm font-medium text-ink-800">
            Caption {mediaType === 'photo' && <span className="text-ink-500">(title)</span>}
          </label>
          <span className={`text-xs ${titleLen > titleMax ? 'text-err-500 font-semibold' : 'text-ink-500'}`}>
            {titleLen} / {titleMax}
          </span>
        </div>
        <textarea
          id="tt-caption"
          rows={4}
          value={draft.title}
          disabled={busy}
          onChange={(e) => setDraft((d) => ({ ...d, title: e.target.value }))}
          placeholder="Write a caption, or draft one with AI below. #hashtags and @mentions are allowed."
          className="w-full rounded-xl border border-ink-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-400"
        />
        {mediaType === 'photo' && (
          <textarea
            rows={3}
            value={draft.description}
            disabled={busy}
            onChange={(e) => setDraft((d) => ({ ...d, description: e.target.value }))}
            placeholder={`Description (optional, up to ${config.limits.photo_description_max} characters)`}
            aria-label="Photo post description"
            className="w-full rounded-xl border border-ink-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-400"
          />
        )}

        <div className="rounded-xl bg-ink-050 p-3 space-y-2">
          <p className="text-xs font-medium text-ink-700">Draft caption with AI</p>
          <div className="flex flex-col sm:flex-row gap-2">
            <input
              value={brief}
              disabled={busy || drafting}
              onChange={(e) => setBrief(e.target.value)}
              placeholder="What is this clip about? e.g. 'kedai nasi lemak gets a website in 3 minutes'"
              className="flex-1 rounded-lg border border-ink-200 px-3 py-2 text-sm"
              aria-label="Brief for the AI caption"
            />
            <select
              value={language}
              disabled={busy || drafting}
              onChange={(e) => setLanguage(e.target.value as 'ms' | 'en' | 'mixed')}
              className="rounded-lg border border-ink-200 px-2 py-2 text-sm"
              aria-label="Caption language"
            >
              <option value="mixed">BM + English</option>
              <option value="ms">Bahasa Malaysia</option>
              <option value="en">English</option>
            </select>
            <Button variant="secondary" size="md" onClick={onDraftCaption} loading={drafting} disabled={busy}>
              ✨ Draft caption with AI
            </Button>
          </div>
          <p className="text-[11px] text-ink-500">The draft is a suggestion — it stays fully editable above before anything is posted.</p>
        </div>
      </div>

      {/* 3. Creator settings (Direct Post) */}
      <div className="rounded-2xl border border-ink-200 p-4 space-y-4">
        <div className="flex items-center justify-between gap-3">
          <div>
            <h3 className="text-sm font-semibold text-ink-900">Post settings</h3>
            {creator ? (
              <p className="text-sm text-ink-600">
                Posting to <strong className="text-ink-900">{creator.creator_nickname || account.display_name}</strong>
                {creator.creator_username ? <span className="text-ink-500"> (@{creator.creator_username})</span> : null}
              </p>
            ) : (
              <p className="text-sm text-ink-500">{loadingCreator ? 'Loading creator settings from TikTok…' : creatorError || '—'}</p>
            )}
          </div>
          <Button variant="ghost" size="sm" onClick={loadCreator} loading={loadingCreator} disabled={busy}>
            Reload
          </Button>
        </div>

        {creatorError && !loadingCreator && (
          <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700" role="alert">
            {creatorError}
          </p>
        )}

        {!config.audited && (
          <p className="rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-800">
            Until the app passes TikTok review, the TikTok account itself must be set to <strong>Private</strong> and the
            post must be <strong>Only you</strong>. Or use <strong>Send to TikTok drafts</strong>.
          </p>
        )}

        {/* Privacy — no default */}
        <div>
          <label htmlFor="tt-privacy" className="block text-sm font-medium text-ink-800">
            Who can view this video
          </label>
          <select
            id="tt-privacy"
            value={draft.privacy_level ?? ''}
            disabled={busy || !creator}
            onChange={(e) => setDraft((d) => ({ ...d, privacy_level: (e.target.value || null) as PrivacyLevel | null }))}
            className="mt-1 w-full sm:w-72 rounded-xl border border-ink-200 px-3 py-2 text-sm"
            required
          >
            <option value="" disabled>
              Select who can view
            </option>
            {options.map((o) => (
              <option key={o} value={o} disabled={privacyOptionDisabled(o, draft)}>
                {PRIVACY_LABELS[o]}
                {privacyOptionDisabled(o, draft) ? ' — not available for branded content' : ''}
              </option>
            ))}
          </select>
          {draft.disclose_commercial && draft.branded_content && (
            <p className="mt-1 text-xs text-ink-500">{DISCLOSURE_COPY.brandedNotPrivate}</p>
          )}
        </div>

        {/* Interactions — none on by default */}
        <fieldset className="space-y-2">
          <legend className="text-sm font-medium text-ink-800">Allow users to</legend>
          <label className="flex items-center gap-2 text-sm text-ink-700">
            <input
              type="checkbox"
              checked={draft.allow_comment}
              disabled={busy || !creator || creator.comment_disabled}
              onChange={toggle('allow_comment')}
            />
            Comment
            {creator?.comment_disabled && <span className="text-xs text-ink-500">(turned off in your TikTok settings)</span>}
          </label>
          {mediaType === 'video' && (
            <>
              <label className="flex items-center gap-2 text-sm text-ink-700">
                <input
                  type="checkbox"
                  checked={draft.allow_duet}
                  disabled={busy || !creator || creator.duet_disabled}
                  onChange={toggle('allow_duet')}
                />
                Duet
                {creator?.duet_disabled && <span className="text-xs text-ink-500">(not available for this account)</span>}
              </label>
              <label className="flex items-center gap-2 text-sm text-ink-700">
                <input
                  type="checkbox"
                  checked={draft.allow_stitch}
                  disabled={busy || !creator || creator.stitch_disabled}
                  onChange={toggle('allow_stitch')}
                />
                Stitch
                {creator?.stitch_disabled && <span className="text-xs text-ink-500">(not available for this account)</span>}
              </label>
            </>
          )}
        </fieldset>

        {/* Commercial content disclosure — off by default */}
        <fieldset className="space-y-2">
          <label className="flex items-start gap-3">
            <input
              type="checkbox"
              className="mt-1"
              checked={draft.disclose_commercial}
              disabled={busy}
              onChange={(e) =>
                setDraft((d) => ({
                  ...d,
                  disclose_commercial: e.target.checked,
                  your_brand: e.target.checked ? d.your_brand : false,
                  branded_content: e.target.checked ? d.branded_content : false,
                }))
              }
            />
            <span>
              <span className="block text-sm font-medium text-ink-800">Disclose commercial content</span>
              <span className="block text-xs text-ink-500">
                Turn on to indicate whether this content promotes yourself, a brand, product or service.
              </span>
            </span>
          </label>

          {draft.disclose_commercial && (
            <div className="ml-7 space-y-2 rounded-xl bg-ink-050 p-3">
              <label className="flex items-start gap-2 text-sm text-ink-700">
                <input type="checkbox" className="mt-0.5" checked={draft.your_brand} disabled={busy} onChange={toggle('your_brand')} />
                <span>
                  <span className="font-medium text-ink-900">Your brand</span>
                  <span className="block text-xs text-ink-500">
                    You are promoting yourself or your own business. {DISCLOSURE_COPY.yourBrand(mediaType)}.
                  </span>
                </span>
              </label>
              <label
                className={`flex items-start gap-2 text-sm text-ink-700 ${brandedContentDisabled(draft) ? 'opacity-60' : ''}`}
                title={brandedContentDisabled(draft) ? DISCLOSURE_COPY.brandedNotPrivate : undefined}
              >
                <input
                  type="checkbox"
                  className="mt-0.5"
                  checked={draft.branded_content}
                  disabled={busy || brandedContentDisabled(draft)}
                  onChange={toggle('branded_content')}
                />
                <span>
                  <span className="font-medium text-ink-900">Branded content</span>
                  <span className="block text-xs text-ink-500">
                    You are promoting another brand or a third party (paid partnership). {DISCLOSURE_COPY.brandedContent(mediaType)}.
                    {brandedContentDisabled(draft) && <> {DISCLOSURE_COPY.brandedNotPrivate}</>}
                  </span>
                </span>
              </label>
              {!draft.your_brand && !draft.branded_content && (
                <p className="text-xs font-medium text-amber-700">{DISCLOSURE_COPY.needOne}</p>
              )}
            </div>
          )}
        </fieldset>

        <label className="flex items-center gap-2 text-sm text-ink-700">
          <input type="checkbox" checked={draft.is_aigc} disabled={busy} onChange={toggle('is_aigc')} />
          This content is AI-generated (adds TikTok&apos;s AIGC label)
        </label>
      </div>

      {/* 4. Actions */}
      <div className="space-y-3">
        <p className="text-xs text-ink-600">
          {declaration.brandedPolicy ? (
            <>
              By posting, you agree to TikTok&apos;s{' '}
              <a className="underline" href={BRANDED_CONTENT_POLICY_URL} target="_blank" rel="noreferrer">
                Branded Content Policy
              </a>{' '}
              and{' '}
              <a className="underline" href={MUSIC_USAGE_URL} target="_blank" rel="noreferrer">
                Music Usage Confirmation
              </a>
              .
            </>
          ) : (
            <>
              By posting, you agree to TikTok&apos;s{' '}
              <a className="underline" href={MUSIC_USAGE_URL} target="_blank" rel="noreferrer">
                Music Usage Confirmation
              </a>
              .
            </>
          )}
        </p>
        <p className="text-xs text-ink-500">{DISCLOSURE_COPY.processing}</p>

        {submitting && (
          <div className="h-2 w-full overflow-hidden rounded-full bg-ink-100" aria-label="Upload progress">
            <div className="h-full bg-brand-500 transition-all" style={{ width: `${Math.round(uploadPct * 100)}%` }} />
          </div>
        )}

        <div className="flex flex-wrap gap-3">
          <Button
            variant="secondary"
            onClick={() => submit('inbox')}
            loading={submitting === 'inbox'}
            disabled={busy || !inboxCheck.ok}
            title={inboxCheck.ok ? undefined : inboxCheck.problems.join(' ')}
          >
            Send to TikTok drafts
          </Button>
          <Button
            onClick={() => submit('direct')}
            loading={submitting === 'direct'}
            disabled={busy || !directCheck.ok}
            title={directCheck.ok ? undefined : directCheck.problems.join(' ')}
          >
            Post now
          </Button>
        </div>
        {!directCheck.ok && files.length > 0 && creator && (
          <ul className="text-xs text-ink-500 list-disc pl-5" aria-live="polite">
            {directCheck.problems.map((p) => (
              <li key={p}>{p}</li>
            ))}
          </ul>
        )}
      </div>
    </section>
  );
}
