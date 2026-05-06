'use client'

import { Pill } from '../primitives'
import { useRestaurant } from '../ThemeProvider'

/**
 * Sticky restaurant header at the top of the menu page. Logo mark +
 * name + open/closed pill. No cart icon — the FAB is the only cart
 * affordance per the design.
 *
 * Matches the `.menu-header-row` block in the prototype but drops the
 * info icon (the filter button on the right is hidden for v1 per the
 * pre-locked product decision).
 */
export function MenuHeader() {
  const restaurant = useRestaurant()

  // Tone for the open-state pill — matches the design's status colors.
  const statusPill =
    restaurant.status === 'open' ? (
      <Pill tone="ok" dot>
        Buka sekarang
      </Pill>
    ) : restaurant.status === 'busy' ? (
      <Pill tone="warn" dot>
        Sibuk
      </Pill>
    ) : (
      <Pill tone="err" dot>
        Tutup
      </Pill>
    )

  return (
    <div className="menu-header-row">
      <div className="h-logo" aria-hidden="true">
        {restaurant.initials}
      </div>
      <div className="h-name">
        <h2>{restaurant.name}</h2>
        <div className="meta">
          {statusPill}
          <span aria-hidden="true">·</span>
          <span>{restaurant.cuisine}</span>
        </div>
      </div>
    </div>
  )
}
