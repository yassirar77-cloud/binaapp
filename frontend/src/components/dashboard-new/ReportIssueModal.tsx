'use client'

/**
 * "Report Issue" modal for a generated website.
 *
 * Category picker (5 BM options) + optional description (500 chars) →
 * POST /websites/{id}/report-issue. Three outcomes:
 *  - regen_granted → success + CTA to the regenerate-capable editor
 *    (the backend makes the next regenerate of this site free
 *    automatically — no special parameter needed).
 *  - escalated → "team will review" message.
 *  - error → friendly BM error inline.
 * A 404 (ISSUE_REPORT_ENABLED off) reports feature_disabled upward so
 * the dashboard hides the Report button for the rest of the session.
 */

import { ReactElement, useState } from 'react'
import { Flag, X, CheckCircle2, Clock3, RefreshCw } from 'lucide-react'
import {
  ISSUE_CATEGORIES,
  ISSUE_DESCRIPTION_MAX,
  IssueCategory,
  ReportOutcome,
  submitIssueReport,
} from '@/lib/issueReport'

interface ReportIssueModalProps {
  websiteId: string
  websiteName: string
  onClose: () => void
  /** Navigate to the regenerate-capable editor after a granted report. */
  onGoToRegenerate: (websiteId: string) => void
  /** Called when the backend says the feature flag is off (hide buttons). */
  onFeatureDisabled: () => void
}

export default function ReportIssueModal({
  websiteId,
  websiteName,
  onClose,
  onGoToRegenerate,
  onFeatureDisabled,
}: ReportIssueModalProps): ReactElement {
  const [category, setCategory] = useState<IssueCategory | null>(null)
  const [description, setDescription] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [errorMsg, setErrorMsg] = useState<string | null>(null)
  const [result, setResult] = useState<ReportOutcome | null>(null)

  const handleSubmit = async () => {
    if (!category || submitting) return
    setSubmitting(true)
    setErrorMsg(null)

    const outcome = await submitIssueReport(websiteId, category, description)

    setSubmitting(false)
    if (outcome.kind === 'feature_disabled') {
      onFeatureDisabled()
      onClose()
      return
    }
    if (outcome.kind === 'error') {
      setErrorMsg(outcome.message)
      return
    }
    setResult(outcome)
  }

  return (
    <div
      className="fixed inset-0 z-50 grid place-items-center p-4"
      style={{ background: 'rgba(5,5,12,0.7)', backdropFilter: 'blur(6px)' }}
      onClick={onClose}
    >
      <div
        className="dash-surface-flat w-full max-w-md p-6 relative"
        style={{ background: '#0F0F1A', border: '1px solid rgba(255,255,255,.08)', borderRadius: 16 }}
        onClick={(e) => e.stopPropagation()}
      >
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-ink-400 hover:text-white transition-colors"
          aria-label="Tutup"
        >
          <X size={16} />
        </button>

        {result === null ? (
          <>
            <div className="flex items-center gap-2.5 mb-1">
              <Flag size={16} className="text-err-400" />
              <h3 className="font-geist font-semibold text-base text-white tracking-[-0.02em]">
                Report masalah
              </h3>
            </div>
            <p className="text-[12.5px] text-ink-400 mb-4">
              Ada yang tak kena dengan <span className="text-white">{websiteName}</span>? Beritahu kami.
            </p>

            {/* Category picker */}
            <div className="flex flex-col gap-1.5 mb-4">
              {ISSUE_CATEGORIES.map((c) => (
                <button
                  key={c.id}
                  onClick={() => setCategory(c.id)}
                  className="flex items-center gap-2.5 text-left font-geist text-[13px] py-2.5 px-3 rounded-[10px] cursor-pointer transition-colors"
                  style={{
                    background: category === c.id ? 'rgba(199,255,61,.10)' : 'rgba(255,255,255,.04)',
                    border: category === c.id
                      ? '1px solid rgba(199,255,61,.45)'
                      : '1px solid rgba(255,255,255,.08)',
                    color: category === c.id ? '#F5F5FA' : '#B8B8C8',
                  }}
                >
                  <span aria-hidden>{c.emoji}</span> {c.label}
                </button>
              ))}
            </div>

            {/* Optional description */}
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value.slice(0, ISSUE_DESCRIPTION_MAX))}
              placeholder="Ceritakan sikit apa yang tak kena... (pilihan)"
              rows={3}
              maxLength={ISSUE_DESCRIPTION_MAX}
              className="w-full font-geist text-[13px] text-white p-3 rounded-[10px] resize-none outline-none"
              style={{ background: 'rgba(255,255,255,.04)', border: '1px solid rgba(255,255,255,.08)' }}
            />
            <div className="text-right text-[10.5px] text-ink-400 mt-1 mb-4 font-geist-mono">
              {description.length}/{ISSUE_DESCRIPTION_MAX}
            </div>

            {errorMsg && (
              <div className="rounded-[10px] bg-red-500/10 border border-red-500/20 p-3 text-red-400 text-[12.5px] mb-3">
                {errorMsg}
              </div>
            )}

            <button
              onClick={handleSubmit}
              disabled={!category || submitting}
              className="w-full flex items-center justify-center gap-2 font-geist text-[13px] font-medium py-2.5 rounded-[10px] cursor-pointer transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
              style={{ background: '#C7FF3D', color: '#05050C' }}
            >
              {submitting ? 'Menghantar...' : 'Hantar report'}
            </button>
          </>
        ) : result.kind === 'regen_granted' ? (
          <div className="text-center py-2">
            <CheckCircle2 size={36} className="mx-auto mb-3" style={{ color: '#22C08F' }} />
            <h3 className="font-geist font-semibold text-base text-white mb-2">
              Regenerate percuma diberikan!
            </h3>
            <p className="text-[13px] text-ink-300 mb-1">{result.message}</p>
            {result.regensRemaining !== null && (
              <p className="text-[11.5px] text-ink-400 font-geist-mono mb-4">
                {result.regensRemaining} regenerate percuma berbaki untuk site ini
              </p>
            )}
            <button
              onClick={() => onGoToRegenerate(websiteId)}
              className="w-full flex items-center justify-center gap-2 font-geist text-[13px] font-medium py-2.5 rounded-[10px] cursor-pointer transition-colors mb-2"
              style={{ background: '#C7FF3D', color: '#05050C' }}
            >
              <RefreshCw size={13} /> Regenerate sekarang
            </button>
            <button
              onClick={onClose}
              className="w-full text-xs text-ink-400 hover:text-ink-300 transition-colors py-1.5"
            >
              Nanti dulu
            </button>
          </div>
        ) : (
          <div className="text-center py-2">
            <Clock3 size={36} className="mx-auto mb-3" style={{ color: '#F59E0B' }} />
            <h3 className="font-geist font-semibold text-base text-white mb-2">
              Report diterima
            </h3>
            <p className="text-[13px] text-ink-300 mb-4">{result.message}</p>
            <button
              onClick={onClose}
              className="w-full font-geist text-[13px] font-medium py-2.5 rounded-[10px] cursor-pointer transition-colors bg-white/[0.06] text-white border border-white/[0.1] hover:bg-white/[0.1]"
            >
              Tutup
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
