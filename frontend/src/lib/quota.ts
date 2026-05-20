/**
 * Website creation quota — single source of truth for client-side checks.
 *
 * Used by the dashboard "Bina Website" button and the /create page so they
 * agree on whether the user is over their plan limit. The backend
 * (backend/app/api/v1/endpoints/websites.py) is the authoritative enforcer;
 * this helper mirrors its logic to avoid showing a wrong "Had Tercapai"
 * modal for unlimited (Pro) users.
 */
import { supabase } from '@/lib/supabase'

// Mirror of subscription_plans.websites_limit in DB
// (backend/migrations/005_subscription_management.sql).
// null = unlimited. Used only as a fallback when the joined plan row from
// Supabase is missing but the plan_name is known.
export const PLAN_WEBSITE_LIMITS: Record<string, number | null> = {
  starter: 1,
  basic: 5,
  pro: null,
}

export interface WebsiteQuota {
  allowed: boolean
  currentUsage: number
  limit: number | null // null = unlimited
  addonCredits: number
  planName: string | null
}

export async function canCreateWebsite(userId: string): Promise<WebsiteQuota> {
  if (!supabase) {
    // No client — fail open; the backend will still enforce.
    return { allowed: true, currentUsage: 0, limit: null, addonCredits: 0, planName: null }
  }

  const { count } = await supabase
    .from('websites')
    .select('id', { count: 'exact', head: true })
    .eq('user_id', userId)
  const currentUsage = count ?? 0

  const { limit, planName, hasActiveSubscription } = await getWebsiteLimit(userId)

  if (!hasActiveSubscription) {
    // No active subscription — backend will return 403; surface that here.
    return { allowed: false, currentUsage, limit: 0, addonCredits: 0, planName: null }
  }

  if (limit === null) {
    return { allowed: true, currentUsage, limit: null, addonCredits: 0, planName }
  }

  const { data: addons } = await supabase
    .from('addon_purchases')
    .select('quantity_remaining')
    .eq('user_id', userId)
    .eq('addon_type', 'website')
    .eq('status', 'active')
    .gt('quantity_remaining', 0)

  const addonCredits = (addons || []).reduce(
    (s: number, a: { quantity_remaining: number | null }) => s + (a.quantity_remaining ?? 0),
    0,
  )
  const totalAllowed = limit + addonCredits

  return {
    allowed: currentUsage < totalAllowed,
    currentUsage,
    limit,
    addonCredits,
    planName,
  }
}

/**
 * Fetch just the plan-level website limit for the user (no counts, no addons).
 * Used for the dashboard display widgets. Ordering matches the backend
 * (websites.py:97) so frontend and backend pick the same active subscription
 * row when a user has multiple (e.g. legacy Starter + current Pro).
 */
export async function getWebsiteLimit(userId: string): Promise<{
  limit: number | null
  planName: string | null
  hasActiveSubscription: boolean
}> {
  if (!supabase) {
    return { limit: null, planName: null, hasActiveSubscription: false }
  }

  // supabase-js can't infer FK arity from the select string, so it defaults
  // the joined relation to an array. The FK subscriptions.subscription_plan_id
  // → subscription_plans.id is many-to-one, so the runtime shape is a single
  // object (or null).
  const { data: subRows } = await supabase
    .from('subscriptions')
    .select('subscription_plans(plan_name,websites_limit)')
    .eq('user_id', userId)
    .eq('status', 'active')
    .order('current_period_end', { ascending: false, nullsFirst: false })
    .order('end_date', { ascending: false, nullsFirst: false })
    .limit(1)
    .returns<{ subscription_plans: { plan_name: string | null; websites_limit: number | null } | null }[]>()

  const subRow = (subRows ?? [])[0]
  const planRow = subRow?.subscription_plans ?? null
  const planName = planRow?.plan_name ?? null

  let limit: number | null
  if (planRow && planRow.websites_limit !== undefined) {
    limit = planRow.websites_limit
  } else if (planName && planName in PLAN_WEBSITE_LIMITS) {
    limit = PLAN_WEBSITE_LIMITS[planName]
  } else if (subRow) {
    // Active subscription with unknown plan — treat as unlimited and warn.
    console.warn('[quota] active subscription with unknown plan; failing open', { subRow })
    limit = null
  } else {
    limit = null
  }

  return { limit, planName, hasActiveSubscription: !!subRow }
}
