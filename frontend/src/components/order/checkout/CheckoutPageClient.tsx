'use client'

import { useEffect, useMemo, useRef, useState } from 'react'
import { useRouter } from 'next/navigation'
import toast from 'react-hot-toast'
import { cartTotal, useCartStore } from '../cart-store'
import {
  CoverageError,
  type CoveredZone,
  fetchZoneCoverage,
  geocodeAddress,
  GeocodeError,
  placeOrder,
  PlaceOrderError,
  type OrderPaymentMethod,
} from '../checkout-api'
import { useCustomerStore } from '../customer-store'
import { clearPromoQuoteCache, usePromoQuote } from '../promo'
import { useRestaurantStore, useTable } from '../restaurant-store'
import { useRestaurant } from '../ThemeProvider'
import { AddressSection, type AddressChoice } from './AddressSection'
import { CheckoutHeader } from './CheckoutHeader'
import { CoverageStatusSection } from './CoverageStatusSection'
import { CustomerInfoSection } from './CustomerInfoSection'
import { DineInSection } from './DineInSection'
import { LoyaltySection } from './LoyaltySection'
import { OrderSummaryAccordion } from './OrderSummaryAccordion'
import { PaymentMethodSection } from './PaymentMethodSection'
import { PlaceOrderCTA } from './PlaceOrderCTA'

/**
 * Orchestrates the checkout page.
 *
 * Mount-time guards:
 *   1. Customer identity guard — redirect to /order/identify if no
 *      phone in the customer store.
 *   2. Empty cart guard — redirect to /order/menu if items is empty.
 *      Toasts "Keranjang anda kosong" so the customer understands why.
 *   3. Cross-restaurant guard — redirect to /order/menu if the cart
 *      was bound to a different restaurant. Cart is left untouched
 *      (the menu page handles the actual clear).
 *
 * Toggles a `checkout-route` class on `.order-flow` so the page
 * background flips to var(--bg-soft) per the design.
 *
 * Order placement (COD only — BinaApp does not process customer food
 * payments. See PaymentMethodSection.):
 *   1. POST /api/v1/delivery/orders with the normalized payload.
 *   2. On success, clear the cart and replace the route with
 *      /order/tracking/{order_number}.
 *   3. On failure, surface the error inline above the CTA — DO NOT
 *      clear the form, the customer can retry.
 *
 * Dine-in (arrived from a table QR — see restaurant-store): the address
 * and coverage sections are replaced by the table card, there is no
 * delivery fee, and the order is sent with order_type 'dine_in'.
 *
 * Promotions: every discount on this page comes from the server quote
 * (promo.ts). The CTA is disabled while a quote is in flight so the
 * customer can never confirm a total that is about to change.
 */
export function CheckoutPageClient() {
  const router = useRouter()
  const restaurant = useRestaurant()

  // Customer store
  const customer = useCustomerStore((s) => s.customer)
  const updateCustomer = useCustomerStore((s) => s.updateCustomer)

  // Cart store
  const cartItems = useCartStore((s) => s.items)
  const cartRestaurantId = useCartStore((s) => s.restaurantId)
  const kitchenNotes = useCartStore((s) => s.kitchenNotes)
  const promoCode = useCartStore((s) => s.promoCode)
  const redeemPoints = useCartStore((s) => s.redeemPoints)
  const setRedeemPoints = useCartStore((s) => s.setRedeemPoints)
  const clearPromoCode = useCartStore((s) => s.clearPromoCode)
  const clearCart = useCartStore((s) => s.clear)

  // Dine-in table (null = normal delivery flow).
  const table = useTable()
  const clearTable = useRestaurantStore((s) => s.clearTable)
  const dineIn = !!table

  // Server-priced voucher + loyalty for this cart.
  const promo = usePromoQuote({ withLoyalty: true })

  const [hydrated, setHydrated] = useState(false)

  // Local section state
  const [addressChoice, setAddressChoice] = useState<AddressChoice>('saved')
  const [newAddressText, setNewAddressText] = useState('')
  const [pickedLatLng, setPickedLatLng] = useState<{ lat: number; lng: number } | null>(null)
  const [riderNotes, setRiderNotes] = useState('')
  const [paymentMethod, setPaymentMethod] = useState<OrderPaymentMethod>('cod')

  // Coverage detection — the customer doesn't pick a ring. Whenever
  // pickedLatLng changes (geolocation, "Semak alamat", saved-address
  // auto-geocode), we hit /zones/{id}/cover and let the server tell us
  // which ring covers them. detectedZone holds the resolved ring (with
  // fee in RM) or null. coverageStatus drives the CoverageStatusSection
  // display + the place-order CTA's enabled state.
  type CoverageStatus = 'idle' | 'checking' | 'covered' | 'uncovered' | 'error'
  const [coverageStatus, setCoverageStatus] = useState<CoverageStatus>('idle')
  const [detectedZone, setDetectedZone] = useState<CoveredZone | null>(null)
  const [coverageError, setCoverageError] = useState<string | null>(null)

  // Place-order state
  const [placing, setPlacing] = useState(false)
  const [placeError, setPlaceError] = useState<string | null>(null)
  // Prevents the empty-cart guard from hijacking navigation after a
  // successful order clears the cart.
  const orderedRef = useRef(false)

  // ---- Toggle the page-background class for /order/checkout.
  useEffect(() => {
    const flow = document.querySelector('.order-flow')
    if (!flow) return
    flow.classList.add('checkout-route')
    return () => {
      flow.classList.remove('checkout-route')
    }
  }, [])

  // ---- Hydration gate.
  useEffect(() => {
    setHydrated(true)
  }, [])

  // ---- Guards. Run after hydration so persisted state is real.
  useEffect(() => {
    if (!hydrated) return
    if (!customer?.phone) {
      router.replace('/order/identify')
      return
    }
    if (cartItems.length === 0 && !orderedRef.current) {
      toast('Keranjang anda kosong', { icon: '🛒' })
      router.replace('/order/menu')
      return
    }
    if (cartRestaurantId && cartRestaurantId !== restaurant.websiteId) {
      router.replace('/order/menu')
    }
  }, [hydrated, customer?.phone, cartItems.length, cartRestaurantId, restaurant.websiteId, router])

  // ---- Initial address choice — saved if available, else new.
  useEffect(() => {
    if (!hydrated) return
    if (!customer?.address?.trim()) {
      setAddressChoice('new')
    }
  }, [hydrated, customer?.address])

  // Generous client-side timeout for backend fetches. Render free-tier
  // cold starts can take ~30s; we'd rather surface an error than leave
  // coverageStatus stuck on 'checking' with the CTA permanently disabled.
  const REQUEST_TIMEOUT_MS = 30_000

  // ---- Auto-geocode the saved address. When the customer's chosen path
  //      is 'saved' and we don't already have coords, resolve the saved
  //      text through the backend Nominatim proxy so the coverage check
  //      below can fire. The typed-address path uses an explicit "Semak
  //      alamat" button instead (see AddressSection) to avoid hammering
  //      Nominatim on every keystroke.
  useEffect(() => {
    if (!hydrated) return
    if (dineIn) return  // no address to resolve at a table
    if (addressChoice !== 'saved') return
    const saved = customer?.address?.trim()
    if (!saved || saved.length < 4) return
    if (pickedLatLng) return  // already geocoded

    let active = true
    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS)

    geocodeAddress(saved, controller.signal)
      .then((hit) => {
        if (!active) return
        if (hit.found && hit.lat != null && hit.lng != null) {
          setPickedLatLng({ lat: hit.lat, lng: hit.lng })
        } else {
          // Couldn't resolve the saved string. Surface as "uncovered" so
          // the customer is nudged toward "Tambah alamat baru".
          setCoverageStatus('uncovered')
          setDetectedZone(null)
        }
      })
      .catch((err: unknown) => {
        if (!active) return
        // AbortError from useEffect cleanup is caught here too, but
        // `active` is false by then so we won't reach this branch.
        // A timeout-driven abort, however, leaves `active` true.
        setCoverageStatus('error')
        setCoverageError(
          err instanceof DOMException && err.name === 'AbortError'
            ? 'Permintaan masa tamat. Sila cuba lagi.'
            : 'Tidak dapat menyemak alamat tersimpan. Sila cuba lagi.'
        )
      })
    return () => {
      active = false
      clearTimeout(timeoutId)
      controller.abort()
    }
  }, [hydrated, dineIn, addressChoice, customer?.address, pickedLatLng])

  // ---- Coverage check — fires whenever pickedLatLng changes.
  //      No coords → idle. Coords set → checking → covered/uncovered/error.
  //
  //      Race handling: when pickedLatLng changes mid-flight (customer
  //      hits "Semak alamat" right after geolocating), the cleanup runs
  //      first — it aborts the in-flight request and flips `active` to
  //      false. Any stale .then/.catch that still fires will bail on the
  //      `active` guard, so the newer request always wins.
  useEffect(() => {
    if (!pickedLatLng) {
      setCoverageStatus('idle')
      setDetectedZone(null)
      setCoverageError(null)
      return
    }
    let active = true
    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS)

    setCoverageStatus('checking')
    setCoverageError(null)
    fetchZoneCoverage(
      restaurant.websiteId,
      pickedLatLng.lat,
      pickedLatLng.lng,
      controller.signal
    )
      .then((res) => {
        if (!active) return
        if (res.covered) {
          setDetectedZone(res.zone)
          setCoverageStatus('covered')
        } else {
          setDetectedZone(null)
          setCoverageStatus('uncovered')
        }
      })
      .catch((err: unknown) => {
        if (!active) return
        const isTimeout = err instanceof DOMException && err.name === 'AbortError'
        const msg = isTimeout
          ? 'Permintaan masa tamat. Sila cuba lagi.'
          : err instanceof CoverageError || err instanceof GeocodeError
            ? err.message
            : 'Tidak dapat menyemak liputan. Sila cuba lagi.'
        setCoverageError(msg)
        setCoverageStatus('error')
      })
    return () => {
      active = false
      clearTimeout(timeoutId)
      controller.abort()
    }
  }, [restaurant.websiteId, pickedLatLng])

  // ---- Money math.
  const subtotal = useMemo(() => cartTotal(cartItems), [cartItems])
  const voucher = promo.quote?.voucher ?? null
  const loyalty = promo.quote?.loyalty ?? null
  const voucherDiscount = voucher?.valid ? voucher.discount : 0
  const pointsDiscount = loyalty?.applied ? loyalty.redeemDiscount : 0
  const discount = voucherDiscount + pointsDiscount
  const deliveryFee = dineIn ? 0 : detectedZone?.fee ?? 0
  const total = Math.max(0, subtotal - discount) + deliveryFee
  const minOrderShortfall =
    !dineIn && detectedZone && detectedZone.minOrder > 0 && subtotal < detectedZone.minOrder
      ? detectedZone.minOrder - subtotal
      : 0

  // ---- Validity for the place-order CTA.
  const resolvedAddress =
    addressChoice === 'saved' ? customer?.address ?? '' : newAddressText
  const destinationValid = dineIn
    ? true
    : resolvedAddress.trim().length >= 8 &&
      coverageStatus === 'covered' &&
      !!detectedZone &&
      !!pickedLatLng &&
      minOrderShortfall === 0
  const valid =
    !!customer?.phone &&
    !!customer?.name?.trim() &&
    destinationValid &&
    !promo.loading &&
    paymentMethod === 'cod'

  // ---- Place the order.
  const handlePlace = async () => {
    if (!valid || placing || !customer) return
    // For delivery, `valid` already requires coverageStatus==='covered',
    // detectedZone and pickedLatLng — narrow them so the payload types
    // are happy.
    if (!dineIn && (!pickedLatLng || !detectedZone)) return
    setPlacing(true)
    setPlaceError(null)
    try {
      const promoFields = {
        // Only send a code the server has just confirmed for this cart.
        voucher_code: voucher?.valid ? voucher.code : undefined,
        redeem_points: !!loyalty?.applied,
      }
      const items = cartItems.map((c) => ({
        menu_item_id: c.id,
        quantity: c.qty,
      }))
      const placed = await placeOrder(
        dineIn
          ? {
              website_id: restaurant.websiteId,
              customer_name: customer.name.trim(),
              customer_phone: customer.phone,
              order_type: 'dine_in',
              table_number: table ?? undefined,
              delivery_notes: kitchenNotes,
              items,
              payment_method: paymentMethod,
              ...promoFields,
            }
          : {
              website_id: restaurant.websiteId,
              customer_name: customer.name.trim(),
              customer_phone: customer.phone,
              delivery_address: resolvedAddress.trim(),
              delivery_latitude: pickedLatLng!.lat,
              delivery_longitude: pickedLatLng!.lng,
              delivery_notes: [kitchenNotes, riderNotes].filter(Boolean).join(' · '),
              // Server ignores this and recomputes from lat/lng — we send it so
              // the mismatch-telemetry warning doesn't fire on our own traffic.
              delivery_zone_id: detectedZone!.id,
              items,
              payment_method: paymentMethod,
              ...promoFields,
            }
      )

      // The order spent a voucher use and/or points: cached quotes are stale.
      clearPromoQuoteCache()

      // Persist customer name (and, for delivery, the address) so future
      // checkouts pre-fill. A table is not an address worth remembering.
      updateCustomer(
        dineIn
          ? { id: customer.id, name: customer.name.trim() }
          : { id: customer.id, name: customer.name.trim(), address: resolvedAddress.trim() }
      )

      // Flag before clearing so the empty-cart guard doesn't redirect
      // to /order/menu — we're about to navigate to the tracking page.
      orderedRef.current = true
      clearCart()

      // Tracking endpoint is keyed by order_number (e.g. "ORD-3847"),
      // not the UUID — see GET /api/v1/delivery/orders/{order_number}/track.
      router.replace(`/order/tracking/${encodeURIComponent(placed.order_number)}`)
    } catch (err) {
      let msg =
        err instanceof PlaceOrderError
          ? err.message
          : 'Gagal membuat pesanan. Sila cuba lagi.'
      // The server refused a promotion we showed (voucher just ran out,
      // points spent on another device). Drop it so the page re-prices,
      // and tell the customer the total changed before they confirm again.
      if (err instanceof PlaceOrderError && err.code === 'VOUCHER_INVALID') {
        clearPromoQuoteCache()
        clearPromoCode()
        msg = `${msg}. Kod promo dibuang — sila semak jumlah baharu.`
      } else if (err instanceof PlaceOrderError && err.code === 'LOYALTY_INSUFFICIENT') {
        clearPromoQuoteCache()
        setRedeemPoints(false)
        msg = `${msg} Sila semak jumlah baharu.`
      }
      setPlaceError(msg)
      setPlacing(false)
    }
  }

  // ---- Section numbers. Sections come and go (dine-in drops address +
  //      coverage, loyalty appears only when the merchant enabled it), so
  //      the badges are counted rather than hardcoded.
  const steps = (() => {
    let n = dineIn ? 2 : 3 // customer (1) + table (2), or + address (2) + coverage (3)
    const payment = ++n
    const loyaltyStep = loyalty?.enabled ? ++n : n
    const summary = ++n
    const notes = ++n
    return { payment, loyalty: loyaltyStep, summary, notes }
  })()

  // ---- Render.
  // Don't show the form for users we're about to redirect.
  if (!hydrated) {
    return (
      <>
        <CheckoutHeader />
        <div className="co-sections" style={{ paddingTop: 60, color: 'var(--fg-muted)', fontSize: 13 }}>
          Memuatkan…
        </div>
      </>
    )
  }
  if (!customer?.phone || cartItems.length === 0) {
    return null
  }

  return (
    <>
      <CheckoutHeader />

      <div className="co-sections">
        <CustomerInfoSection customer={customer} onUpdate={updateCustomer} />

        {dineIn && table ? (
          <DineInSection
            table={table}
            onSwitchToDelivery={() => {
              clearTable()
              toast('Ditukar ke penghantaran', { icon: '🛵' })
            }}
          />
        ) : (
          <>
            <AddressSection
              customer={customer}
              choice={addressChoice}
              onChoiceChange={(c) => {
                setAddressChoice(c)
                // Switching choice invalidates any coords we resolved for
                // the previous choice's text. The relevant useEffect will
                // re-geocode (saved) or wait for "Semak alamat" (new).
                setPickedLatLng(null)
              }}
              newAddressText={newAddressText}
              onNewAddressChange={(t) => {
                setNewAddressText(t)
                // Clear lat/lng when the user manually edits the textarea.
                if (pickedLatLng) setPickedLatLng(null)
              }}
              onGeolocated={({ address, latitude, longitude }) => {
                setNewAddressText(address)
                setPickedLatLng({ lat: latitude, lng: longitude })
              }}
            />

            <CoverageStatusSection
              status={coverageStatus}
              zone={detectedZone}
              subtotal={subtotal}
              error={coverageError}
            />
          </>
        )}

        <PaymentMethodSection
          selected={paymentMethod}
          onSelect={setPaymentMethod}
          step={steps.payment}
          dineIn={dineIn}
        />

        {loyalty?.enabled && (
          <LoyaltySection
            loyalty={loyalty}
            redeem={redeemPoints}
            onRedeemChange={setRedeemPoints}
            step={steps.loyalty}
          />
        )}

        <OrderSummaryAccordion
          items={cartItems}
          subtotal={subtotal}
          deliveryFee={deliveryFee}
          voucherDiscount={voucherDiscount}
          promoCode={voucher?.valid ? voucher.code : null}
          pointsDiscount={pointsDiscount}
          pointsUsed={loyalty?.applied ? loyalty.redeemablePoints : 0}
          dineIn={dineIn}
          total={total}
          step={steps.summary}
        />

        {promoCode && voucher && !voucher.valid && !promo.loading && (
          <div className="promo-error" role="alert">
            Kod {promoCode}: {voucher.message}. Diskaun tidak digunakan.
          </div>
        )}

        {/* Optional rider notes — delivery only */}
        {!dineIn && (
          <div className="co-sec fade-up" style={{ animationDelay: '200ms' }}>
            <div className="co-sec-head">
              <h2>
                <span className="num">{steps.notes}</span>
                Nota untuk rider <span style={{ color: 'var(--fg-muted)', fontWeight: 400, fontSize: 12, marginLeft: 4 }}>(pilihan)</span>
              </h2>
            </div>
            <textarea
              className="addr-textarea"
              placeholder="cth: Pintu pagar bawah, ketuk dulu sebelum hantar…"
              value={riderNotes}
              onChange={(e) => setRiderNotes(e.target.value)}
              aria-label="Nota untuk rider"
            />
          </div>
        )}
      </div>

      <PlaceOrderCTA
        total={total}
        disabled={!valid}
        loading={placing}
        error={placeError}
        onPlace={handlePlace}
      />
    </>
  )
}
