/**
 * Menu API client + normalizer.
 *
 * Calls `GET /api/v1/delivery/menu/{website_id}` (public — no auth) and
 * shapes the response into the normalized `MenuData` consumed by the
 * customer-flow UI.
 */

import type { MenuCategory, MenuData, MenuItem } from './menu-types'

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || 'https://binaapp-backend.onrender.com'

/* ----- Backend response shapes (snake_case, raw) ------------------------ */

interface BackendMenuCategory {
  id: string
  website_id: string
  name: string
  name_en?: string | null
  icon?: string | null
  sort_order: number
  is_active: boolean
  created_at?: string
}

interface BackendMenuItem {
  id: string
  website_id: string
  category_id?: string | null
  name: string
  description?: string | null
  price: number | string
  image_url?: string | null
  /** Some older rows may carry `image` instead of `image_url`. */
  image?: string | null
  /** And some experimental rows ship multiple. */
  images?: string[] | null
  is_available: boolean
  is_popular: boolean
  preparation_time?: number
  sort_order?: number
  created_at?: string
  updated_at?: string
  options?: unknown[]
}

interface BackendMenuResponse {
  categories: BackendMenuCategory[]
  items: BackendMenuItem[]
}

/* ----- Normalizer ------------------------------------------------------- */

/**
 * Image field-mapping fallback per the PR-3 product decision:
 * `image` → `image_url` → `images[0]` → empty string (UI renders a placeholder).
 *
 * TODO(menu): Replace plain `<img>` tag with `next/image` when image
 *             domains are configured in `next.config.js`.
 */
function pickImage(raw: BackendMenuItem): string {
  if (raw.image && typeof raw.image === 'string') return raw.image
  if (raw.image_url && typeof raw.image_url === 'string') return raw.image_url
  if (raw.images && raw.images.length > 0 && typeof raw.images[0] === 'string') {
    return raw.images[0]
  }
  return ''
}

function normalizeCategory(raw: BackendMenuCategory): MenuCategory {
  return { id: raw.id, name: raw.name }
}

function normalizeItem(raw: BackendMenuItem): MenuItem {
  return {
    id: raw.id,
    categoryId: raw.category_id ?? null,
    name: raw.name,
    description: raw.description ?? '',
    price: typeof raw.price === 'number' ? raw.price : Number(raw.price) || 0,
    image: pickImage(raw),
    isAvailable: raw.is_available,
    isPopular: raw.is_popular,
  }
}

export function normalizeMenu(raw: BackendMenuResponse): MenuData {
  const categories: MenuCategory[] = [
    { id: 'all', name: 'Semua' },
    ...(raw.categories || []).map(normalizeCategory),
  ]
  const items: MenuItem[] = (raw.items || []).map(normalizeItem)
  return { categories, items }
}

/* ----- Fetcher ---------------------------------------------------------- */

export class MenuFetchError extends Error {
  constructor(
    message: string,
    public status: number
  ) {
    super(message)
    this.name = 'MenuFetchError'
  }
}

/**
 * Fetch and normalize the full menu for a website.
 *
 * Used both server-side (in `app/order/menu/page.tsx`) for the initial
 * render and client-side (for retry-after-error). `cache: 'no-store'`
 * keeps the menu live so price/availability changes propagate without
 * a redeploy.
 */
export async function fetchMenu(websiteId: string): Promise<MenuData> {
  const url = `${API_BASE}/api/v1/delivery/menu/${encodeURIComponent(websiteId)}`
  const res = await fetch(url, {
    method: 'GET',
    headers: { Accept: 'application/json' },
    cache: 'no-store',
  })
  if (!res.ok) {
    throw new MenuFetchError(`Menu fetch failed (${res.status})`, res.status)
  }
  const raw = (await res.json()) as BackendMenuResponse
  return normalizeMenu(raw)
}
