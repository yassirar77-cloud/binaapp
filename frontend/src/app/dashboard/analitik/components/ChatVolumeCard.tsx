'use client'

import Sparkline from '@/components/dashboard-new/Sparkline'

import type { ChatResponse } from '../lib/analytics'
import AnalitikEmptyState from './AnalitikEmptyState'

/** AI chat volume: conversation sparkline + totals for the window. */
export default function ChatVolumeCard({ chat }: { chat: ChatResponse }) {
  const points = chat.series.map((p) => ({ value: p.conversations, label: p.date }))
  const hasData = chat.total_conversations > 0

  return (
    <div className="dash-surface p-5">
      <div className="dash-eyebrow mb-4">Chat AI</div>
      {!hasData ? (
        <AnalitikEmptyState
          heading="Tiada perbualan lagi"
          sub="Perbualan chat pelanggan anda akan dikira di sini."
        />
      ) : (
        <>
          <div className="flex items-end justify-between gap-4 mb-4">
            <div>
              <div className="font-geist font-bold dash-tnum text-[32px] leading-none text-white mb-1.5">
                {chat.total_conversations}
              </div>
              <div className="text-[12px] text-white/40">
                perbualan · {chat.total_messages} mesej
              </div>
            </div>
            <Sparkline
              points={points.slice(-14)}
              color="rgba(199,255,61,0.35)"
              highlightColor="#C7FF3D"
              width={150}
              height={44}
            />
          </div>
        </>
      )}
    </div>
  )
}
