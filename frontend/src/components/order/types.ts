/**
 * Shared types for the customer-facing /order flow.
 *
 * Convention: camelCase in TS. The DB column convention is snake_case
 * (e.g. websites.brand_primary). When real subdomain resolution lands
 * (PR 2+), add a mapper at the data-fetch boundary.
 */

export type RestaurantStatus = 'open' | 'closed' | 'busy'

export interface RestaurantTheme {
  /** Full display name. e.g. "Nasi Kandar Pelita" */
  name: string
  /** Short name for headlines. e.g. "Pelita" */
  short: string
  /** 2-3 char monogram for the logo mark. e.g. "NP" */
  initials: string
  /** Cuisine eyebrow. e.g. "Mamak · Indian Muslim" */
  cuisine: string
  /** Open/closed state shown via pill in header. */
  status: RestaurantStatus

  /** Primary brand color. Used for buttons, accents, focus rings. */
  brandPrimary: string
  /** Hover variant of the primary color. */
  brandPrimaryHover: string
  /** Foreground color rendered on top of brandPrimary fills. */
  brandPrimaryFg: string
  /**
   * RESERVED. Defined in theme.css but not used by any current customer-flow
   * page. Kept on the type for future use (e.g. accent borders, illustration).
   */
  brandSecondary: string
  /**
   * RESERVED. Optional URL for an image-logo restaurant. Currently every
   * restaurant uses the initials mark only.
   */
  brandLogoUrl?: string
}

export interface CartItem {
  id: number
  name: string
  price: number
  qty: number
  img?: string
}
