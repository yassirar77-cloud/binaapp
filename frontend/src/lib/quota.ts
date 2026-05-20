/**
 * Website creation quota.
 *
 * The gating check goes through the backend (checkCreateWebsiteAllowed)
 * because the frontend supabase client has no user session — signIn
 * issues a custom JWT, so RLS-protected reads on `subscriptions` return
 * 0 rows and we can't tell "unlimited PRO" from "no row visible".
 *
 * getWebsiteLimit / canCreateWebsite remain for the cosmetic dashboard
 * widget; they must not be used to gate navigation.
 */
import { supabase, getApiAuthToken } from '@/lib/supabase'
import { API_BASE_URL } from '@/lib/env'

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
    // Either genuinely no subscription, or the anon client can't see the
    // row (RLS — see file header). Don't synthesize limit: 0 here, that
    // produces "X/0" in the modal. Leave limit null and let callers
    // decide; gating should go through checkCreateWebsiteAllowed.
    return { allowed: false, currentUsage, limit: null, addonCredits: 0, planName: null }
  }

  if (limit === null) {
    return { allowed: true, currentUsage, limit: null, addonCredits: 0, planName }
  }

  // Schema (migrations 015 + 024) has quantity + quantity_used.
  // available = quantity - quantity_used; we filter in code rather than
  // by URL because PostgREST can't express arithmetic in filters.
  const { data: addons } = await supabase
    .from('addon_purchases')
    .select('quantity,quantity_used')
    .eq('user_id', userId)
    .eq('addon_type', 'website')
    .eq('status', 'active')

  const addonCredits = (addons || []).reduce(
    (s: number, a: { quantity: number | null; quantity_used: number | null }) =>
      s + Math.max(0, (a.quantity ?? 0) - (a.quantity_used ?? 0)),
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

export interface CreateWebsiteCheck {
  allowed: boolean
  currentUsage: number
  limit: number | null // null = unlimited / unknown
  unlimited: boolean
  canBuyAddon: boolean
  addonPrice?: number
  requiresRenewal: boolean
}

/**
 * Authoritative gating check via the backend (service role; sees RLS-hidden
 * rows; knows about admin bypass, grace period, expiry). Use this anywhere
 * we'd otherwise open the "Had Tercapai" modal. On transport failure we
 * fail open — the create POST will still 403 if the user genuinely can't.
 */
export async function checkCreateWebsiteAllowed(): Promise<CreateWebsiteCheck> {
  const failOpen: CreateWebsiteCheck = {
    allowed: true,
    currentUsage: 0,
    limit: null,
    unlimited: true,
    canBuyAddon: false,
    requiresRenewal: false,
  }
  try {
    const token = await getApiAuthToken()
    if (!token) return failOpen
    const res = await fetch(`${API_BASE_URL}/api/v1/subscription/check-limit`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ action: 'create_website' }),
    })
    if (!res.ok) return failOpen
    const d = await res.json()
    const limit = d.limit ?? null
    return {
      allowed: !!d.allowed,
      currentUsage: d.current_usage ?? 0,
      limit,
      unlimited: !!d.unlimited || limit === null,
      canBuyAddon: !!d.can_buy_addon,
      addonPrice: d.addon_price ?? undefined,
      requiresRenewal: !!d.requires_renewal,
    }
  } catch {
    return failOpen
  }
}
