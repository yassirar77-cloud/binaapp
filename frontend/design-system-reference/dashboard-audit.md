# Dashboard Audit Report — April 22, 2026
# Reference for /dashboard redesign

## 1. Directory structure

```
frontend/src/app/dashboard/
├── layout.tsx                 (2.3KB) — subscription status gate
├── page.tsx                   (15.7KB) — "My Projects" main view
├── billing/
│   ├── page.tsx               (15.5KB) — plans, addons, renew
│   └── billing.css            (10.4KB)
├── chat/
│   └── page.tsx               (6.9KB) — customer chat hub
├── create/
│   └── page.tsx               (3.8KB) — duplicate of /create (simpler)
└── transactions/
    ├── page.tsx               (7.9KB) — history + CSV export
    └── transactions.css       (7.6KB)
```

## 2. Sections on the main dashboard

Top to bottom:
1. **`SubscriptionLockOverlay`** (from layout) — full-screen block when `isLocked`
2. **`SubscriptionBanner`** (from layout) — shown during grace/expired/≤5 days without auto-renew
3. **`SubscriptionExpiredBanner`** (extra, on the page itself)
4. **Sticky header nav** — Logo → "/", "Langganan" → billing, "Profile", "Create New Website" button, "Log Out"
5. **Title block** — "My Projects" + tagline
6. **Stats cards row (3)** — Total Websites, Published (counts `published_at`), Total Views (hardcoded `-`, "Coming Soon")
7. **Error banner** (conditional)
8. **Content area**: loading skeletons → empty state → 1/2/3-col projects grid
9. **Project card** — gradient thumbnail + ExternalLink icon, name, subdomain, created date, `View | Edit | Delete` row with inline "Confirm?" step
10. **Mobile FAB** — bottom-right `+` button (`md:hidden`)
11. **Desktop usage sidebar** — `UsageWidget` fixed right at `lg:block`, top-24, w-72
12. **`LimitReachedModal`** — triggered when trying to create past plan+addon limit

## 3. Data fetches

**Main dashboard (`page.tsx`) — all Supabase direct:**
- `supabase.auth.getUser()` (fallback after `getStoredToken` + `getCurrentUser`)
- `.from('websites').select('*').eq('user_id', ...).order('created_at')` — project list
- `.from('websites').delete().eq('id', ...)` — delete
- `.from('websites').select('id', {count: 'exact'})` — count for limit check
- `.from('subscriptions').select('subscription_plans(websites_limit)')` — plan limit (nested join)
- `.from('addon_purchases').select('quantity_remaining')` — addon credits

**Layout:** `useSubscriptionStatus()` hook (status, isLocked, isGrace, daysRemaining, tier, paymentUrl…)

**Billing page — all backend REST:**
- GET `/api/v1/subscription/plans`
- GET `/api/v1/subscription/status`
- GET `/api/v1/subscription/addons/available`
- POST `/api/v1/subscription/upgrade` (redirects to ToyyibPay)
- POST `/api/v1/subscription/renew` (may auto-confirm free plan)
- POST `/api/v1/subscription/addons/purchase`
- Reads `?payment=success` query on return

**Chat page:**
- `supabase.from('profiles').select('full_name, business_name')`
- `supabase.from('websites').select('id, business_name, name, subdomain')`
- Renders `<OwnerChatDashboard>` (dynamic import, SSR off)

**Transactions page:**
- GET `/api/v1/subscription/transactions?limit=100&transaction_type=&from_date=&to_date=`
- CSV export is client-side

**Create page (dashboard/create):** POST `/api/generate` via `apiFetch` — **duplicate** of top-level `/create`, but simpler.

## 4. Sub-routes and outbound links

**From `/dashboard` (main):** `/` · `/dashboard/billing` · `/profile` · `/create` · `/login` · `/edit/{id}` · external `project.url`

**From `/dashboard/billing`:** `/dashboard` · `/dashboard/transactions` · `/login` · external ToyyibPay URLs

**From `/dashboard/chat`:** `/dashboard` · `/login` · `/profile` · `/my-projects` · `/create`

**From `/dashboard/transactions`:** `/dashboard` · `/login`

**Orphaned top-level routes NOT linked from dashboard** (exist under `frontend/src/app/` but have no nav entry): `analytics`, `ai-chat-settings`, `ai-support`, `delivery`, `disputes`, `menu-designer`, `monitor`, `my-projects`, `notifications`, `referrals`, `rider`, `sla`, `trust-score`, `website-health`, `website-rebuild`, `subscription`. `/dashboard/chat` itself is also not linked from the main dashboard — you can only reach it by typing the URL. **No `website-builder` route exists** (listed as an example; it's not there).

## 5. Dashboard-specific components

Owned by the dashboard flow:
- `components/dashboard/DashboardTab.tsx` (only file in that dir)
- `components/subscription/SubscriptionBanner.tsx`
- `components/subscription/SubscriptionLockOverlay.tsx`
- `components/SubscriptionExpiredBanner.tsx` + `.css`
- `components/UsageWidget.tsx` + `.css` (used by dashboard + billing)
- `components/LimitReachedModal.tsx` + `.css`
- `components/OwnerChatDashboard.tsx` (dashboard/chat only)
- `hooks/useSubscriptionStatus`

## Actions users can take

Create website · View live site · Edit site (`/edit/{id}`) · Delete site (confirm twice) · Open billing/plans · Buy addons · Renew subscription · Upgrade plan · View transaction history · Export CSV · Access customer chat (if they know the URL) · Profile · Logout

## DO NOT BREAK

1. **Dual-auth pattern** — backend token (`getStoredToken` → `getCurrentUser`) tried FIRST, Supabase session fallback. Breaking order logs out backend-auth users.
2. **Subscription gate in `layout.tsx`** — `SubscriptionLockOverlay` must still wrap dashboard content when `isLocked`; `SubscriptionBanner` during grace/expiry. If you replace the layout, re-wire this or users in grace/locked states get into the app.
3. **Client-side limit check on "Create"** — `handleCreateWebsiteClick` (page.tsx:153-214) reads websites count + plan limit + addon credits, pops `LimitReachedModal` BEFORE routing to `/create`. Removing this sends users to the create form where backend silently rejects.
4. **`UsageWidget` callbacks** — both `onUpgradeClick` and `onRenewClick` currently route to `/dashboard/billing`. Billing page expects these same props.
5. **`?payment=success` handling on billing** — ToyyibPay returns users to billing with this query. Don't drop the `useSearchParams` check or localStorage cleanup.
6. **Project `published` heuristic** — "Published" stat counts `published_at`, which the transform sets to `website.updated_at`. Every update will inflate this count — it's not really "published", but changing it will change the displayed number.
7. **Subdomain fallback URL** — `https://${subdomain}.binaapp.my` is hardcoded. Projects without `published_url` rely on this.
8. **Delete has TWO confirms** — a `window.confirm()` AND an inline "Confirm?" button swap (lines 397-412). Redundant but user-tested; remove consciously.
9. **Responsive breakpoints** — projects grid is `1/md:2/lg:3`; sidebar fixed at `lg:block w-72`; FAB `md:hidden`. Sidebar overlaps page content at ≥lg because it's `fixed`, not part of the grid — any new layout with a proper sidebar needs to account for this.
10. **Malay/English mix** — Header says "Langganan" (MS) next to "Create New Website" (EN); stats are EN; billing/transactions/chat are fully MS. If you standardise during redesign, flag it so copy QA catches it.
11. **`/dashboard/create` duplicates `/create`** — two entry points to website creation exist. The dashboard button routes to `/create` (not `/dashboard/create`). Don't delete `/dashboard/create` without checking if anything links there.
12. **Dashboard does NOT link to chat / analytics / menu-designer / delivery / rider / notifications / etc.** — if the redesign is meant to surface these features, this is intentional new work, not preservation.
