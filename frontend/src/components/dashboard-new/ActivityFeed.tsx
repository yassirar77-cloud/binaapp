'use client'

import { ReactElement, ReactNode } from 'react'

export interface ActivityEvent {
  /** Time string, e.g. "14:32" */
  time: string
  /** Icon element */
  icon: ReactNode
  /** Accent color for icon background */
  color: string
  /** Event description (supports ReactNode for bold/colored spans) */
  text: ReactNode
  /** Channel tag, e.g. "WhatsApp", "Delivery", "Order" */
  tag: string
}

interface ActivityFeedProps {
  events: ActivityEvent[]
}

export default function ActivityFeed({
  events,
}: ActivityFeedProps): ReactElement {
  return (
    <div className="dash-surface-flat overflow-hidden">
      {events.map((event, i) => (
        <ActivityItem
          key={i}
          event={event}
          isLast={i === events.length - 1}
        />
      ))}
    </div>
  )
}

function ActivityItem({
  event,
  isLast,
}: {
  event: ActivityEvent
  isLast: boolean
}): ReactElement {
  return (
    <div
      className={`flex items-center gap-3.5 py-3.5 px-5 ${
        !isLast ? 'border-b border-white/[0.04]' : ''
      }`}
    >
      {/* Timestamp */}
      <div className="font-geist-mono text-[11px] text-ink-400 dash-tnum w-11 shrink-0">
        {event.time}
      </div>

      {/* Icon */}
      <div
        className="w-7 h-7 rounded-lg grid place-items-center shrink-0"
        style={{
          background: `${event.color}1A`,
          border: `1px solid ${event.color}33`,
          color: event.color,
        }}
      >
        {event.icon}
      </div>

      {/* Text */}
      <div className="flex-1 font-geist text-[13.5px] text-ink-300 tracking-[-0.005em] min-w-0 truncate">
        {event.text}
      </div>

      {/* Tag */}
      <div className="font-geist-mono text-[10px] text-[#4A4A5C] tracking-[0.08em] uppercase py-0.5 px-2 border border-white/[0.06] rounded-md shrink-0">
        {event.tag}
      </div>
    </div>
  )
}
