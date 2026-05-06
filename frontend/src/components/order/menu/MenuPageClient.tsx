'use client'

import { useEffect, useMemo, useState } from 'react'
import { useRouter } from 'next/navigation'
import { ChefHat, WifiOff } from 'lucide-react'
import toast from 'react-hot-toast'
import type { MenuData, MenuItem } from '../menu-types'
import { fetchMenu, MenuFetchError } from '../menu-api'
import { useCartStore } from '../cart-store'
import { useCustomerStore } from '../customer-store'
import { useRestaurant } from '../ThemeProvider'
import { CategoryChips } from './CategoryChips'
import { EmptyState } from './EmptyState'
import { FloatingCartButton } from './FloatingCartButton'
import { ItemDetailSheet } from './ItemDetailSheet'
import { MenuGrid } from './MenuGrid'
import { MenuHeader } from './MenuHeader'
import { SearchBar } from './SearchBar'

interface MenuPageClientProps {
  /** Initial menu fetched server-side. May be null when the SSR fetch failed. */
  initialMenu: MenuData | null
  /** Set when the SSR fetch failed — drives the error UI + retry button. */
  initialError?: string | null
}

/**
 * Client component that owns all interactive state for the menu page:
 * search query, active category, item detail sheet, cart syncs.
 *
 * Responsibilities on mount:
 *   1. Redirect to /order/identify if the customer hasn't been
 *      identified yet (no phone in the customer store).
 *   2. Cross-restaurant cart guard — if the cart was last bound to a
 *      different restaurant, clear it with a toast warning. Always
 *      bind the cart to the current restaurant afterwards.
 */
export function MenuPageClient({ initialMenu, initialError }: MenuPageClientProps) {
  const router = useRouter()
  const restaurant = useRestaurant()

  const customer = useCustomerStore((s) => s.customer)
  const cartRestaurantId = useCartStore((s) => s.restaurantId)
  const setCartRestaurantId = useCartStore((s) => s.setRestaurantId)
  const clearCart = useCartStore((s) => s.clear)
  const addToCart = useCartStore((s) => s.add)
  const setCartQty = useCartStore((s) => s.setQty)

  const [hydrated, setHydrated] = useState(false)
  const [menu, setMenu] = useState<MenuData | null>(initialMenu)
  const [error, setError] = useState<string | null>(initialError ?? null)
  const [retrying, setRetrying] = useState(false)

  const [searchQuery, setSearchQuery] = useState('')
  const [activeCategoryId, setActiveCategoryId] = useState('all')
  const [selectedItem, setSelectedItem] = useState<MenuItem | null>(null)

  // ---- Hydration gate. Customer redirect + cross-restaurant guard
  //      both depend on persisted Zustand state, which is not yet
  //      populated on the server-rendered first paint. We wait one
  //      tick before reading.
  useEffect(() => {
    setHydrated(true)
  }, [])

  // ---- Customer identity guard (Step 8 edge case).
  useEffect(() => {
    if (!hydrated) return
    if (!customer?.phone) {
      router.replace('/order/identify')
    }
  }, [hydrated, customer?.phone, router])

  // ---- Cross-restaurant cart contamination guard.
  useEffect(() => {
    if (!hydrated) return
    if (cartRestaurantId && cartRestaurantId !== restaurant.websiteId) {
      clearCart()
      toast('Keranjang dikosongkan kerana anda tukar restoran', {
        duration: 4000,
        icon: '⚠️',
      })
    }
    setCartRestaurantId(restaurant.websiteId)
    // Run only when restaurant changes or once after hydration.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [hydrated, restaurant.websiteId])

  // ---- Filtered items (category + search).
  const filteredItems = useMemo(() => {
    if (!menu) return []
    const q = searchQuery.trim().toLowerCase()
    return menu.items.filter((item) => {
      if (activeCategoryId !== 'all' && item.categoryId !== activeCategoryId) {
        return false
      }
      if (q) {
        const haystack = `${item.name} ${item.description}`.toLowerCase()
        if (!haystack.includes(q)) return false
      }
      return true
    })
  }, [menu, activeCategoryId, searchQuery])

  // ---- Cart wire-up.
  const handleAddItem = (item: MenuItem, qty = 1) => {
    addToCart(
      { id: item.id, name: item.name, price: item.price, img: item.image || undefined },
      qty
    )
  }

  const handleSetQty = (item: MenuItem, qty: number) => {
    setCartQty(item.id, qty)
  }

  const handleSheetAdd = (item: MenuItem, qty: number) => {
    handleAddItem(item, qty)
    setSelectedItem(null)
  }

  // ---- Retry after fetch error.
  const handleRetry = async () => {
    setRetrying(true)
    setError(null)
    try {
      const next = await fetchMenu(restaurant.websiteId)
      setMenu(next)
    } catch (err) {
      const msg =
        err instanceof MenuFetchError
          ? err.message
          : 'Tidak dapat memuatkan menu. Cuba lagi sebentar.'
      setError(msg)
    } finally {
      setRetrying(false)
    }
  }

  // ---- Render branches.
  // Don't show the menu surface (header/search/grid) for users we're
  // about to redirect — avoids a flash of menu-for-anonymous-user.
  if (hydrated && !customer?.phone) {
    return null
  }

  if (error && !menu) {
    return (
      <>
        <div className="menu-header">
          <MenuHeader />
        </div>
        <EmptyState
          icon={WifiOff}
          title="Tidak dapat memuatkan menu"
          body={error}
          cta={{ label: retrying ? 'Sedang cuba…' : 'Cuba lagi', onClick: handleRetry }}
        />
      </>
    )
  }

  if (menu && menu.items.length === 0) {
    return (
      <>
        <div className="menu-header">
          <MenuHeader />
        </div>
        <EmptyState
          icon={ChefHat}
          title="Restoran belum tambah menu"
          body="Sila kembali lagi sebentar nanti."
        />
      </>
    )
  }

  const categories = menu?.categories ?? [{ id: 'all', name: 'Semua' }]

  return (
    <>
      <div className="menu-header">
        <MenuHeader />
        <SearchBar value={searchQuery} onChange={setSearchQuery} />
        <CategoryChips
          categories={categories}
          activeId={activeCategoryId}
          onChange={setActiveCategoryId}
        />
      </div>

      <MenuGrid
        items={filteredItems}
        onOpen={(item) => setSelectedItem(item)}
        onAdd={(item) => handleAddItem(item, 1)}
        onSetQty={handleSetQty}
        searchQuery={searchQuery}
      />

      <FloatingCartButton
        onClick={() => router.push('/order/cart')}
        hidden={selectedItem !== null}
      />

      <ItemDetailSheet
        item={selectedItem}
        onClose={() => setSelectedItem(null)}
        onAdd={handleSheetAdd}
      />
    </>
  )
}
