'use client'

const BM_DAYS = ['Ahad', 'Isnin', 'Selasa', 'Rabu', 'Khamis', 'Jumaat', 'Sabtu'] as const
const BM_MONTHS = [
  'Januari', 'Februari', 'Mac', 'April', 'Mei', 'Jun',
  'Julai', 'Ogos', 'September', 'Oktober', 'November', 'Disember',
] as const

function getGreeting(hour: number): string {
  if (hour < 12) return 'Selamat pagi'
  if (hour < 18) return 'Selamat petang'
  return 'Selamat malam'
}

function formatBMDate(date: Date): { dayName: string; dateStr: string } {
  const dayName = BM_DAYS[date.getDay()]
  const day = date.getDate()
  const month = BM_MONTHS[date.getMonth()]
  const year = date.getFullYear()
  return { dayName, dateStr: `${day} ${month} ${year}` }
}

interface DashboardGreetingProps {
  /** User's first name or display name */
  userName: string
  /** @deprecated No longer displayed — kept for API compat */
  businessName?: string
  /** Override the current date/time (useful for testing) */
  now?: Date
}

export default function DashboardGreeting({
  userName,
  now,
}: DashboardGreetingProps) {
  const current = now ?? new Date()
  const greeting = getGreeting(current.getHours())
  const { dayName, dateStr } = formatBMDate(current)

  return (
    <div className="px-4 pt-8 pb-2 lg:px-0">
      <h1 className="text-2xl font-semibold text-white sm:text-3xl">
        {greeting}, {userName}.
      </h1>
      <p className="mt-1 text-sm text-white/40">
        {dayName}, {dateStr}
      </p>
    </div>
  )
}
