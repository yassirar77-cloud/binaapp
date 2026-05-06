'use client'

import { useEffect, useMemo, useState } from 'react'
import { useRouter } from 'next/navigation'
import toast from 'react-hot-toast'
import {
  cartDiscount,
  cartTotal,
  useCartStore,
} from '../cart-store'
import {
  fetchDeliveryZones,
  placeOrder,
  PlaceOrderError,
  ZoneFetchError,
  type DeliveryZone,
  type OrderPaymentMethod,
} from '../checkout-api'
import { useCustomerStore } from '../customer-store'
import { useRestaurant } from '../ThemeProvider'
import { AddressSection, type AddressChoice } from './AddressSection'
import { CheckoutHeader } from './CheckoutHeader'
import { CustomerInfoSection } from './CustomerInfoSection'
import { DeliveryZoneSection } from './DeliveryZoneSection'
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
 * Order placement (COD only for v1 — see PaymentMethodSection):
 *   1. POST /api/v1/delivery/orders with the normalized payload.
 *   2. On success, clear the cart and replace the route with
 *      /order/{order_id}/track (PR 6 territory; route may 404 today).
 *   3. On failure, surface the error inline above the CTA — DO NOT
 *      clear the form, the customer can retry.
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
  const clearCart = useCartStore((s) => s.clear)

  const [hydrated, setHydrated] = useState(false)

  // Local section state
  const [addressChoice, setAddressChoice] = useState<AddressChoice>('saved')
  const [newAddressText, setNewAddressText] = useState('')
  const [pickedLatLng, setPickedLatLng] = useState<{ lat: number; lng: number } | null>(null)
  const [riderNotes, setRiderNotes] = useState('')
  const [paymentMethod, setPaymentMethod] = useState<OrderPaymentMethod>('cod')

  // Zones
  const [zones, setZones] = useState<DeliveryZone[]>([])
  const [zonesLoading, setZonesLoading] = useState(true)
  const [zonesError, setZonesError] = useState<string | null>(null)
  const [selectedZoneId, setSelectedZoneId] = useState<string | null>(null)

  // Place-order state
  const [placing, setPlacing] = useState(false)
  const [placeError, setPlaceError] = useState<string | null>(null)

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
    if (cartItems.length === 0) {
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

  // ---- Fetch delivery zones once.
  useEffect(() => {
    let active = true
    setZonesLoading(true)
    setZonesError(null)
    fetchDeliveryZones(restaurant.websiteId)
      .then((next) => {
        if (!active) return
        setZones(next)
        // Auto-select the only zone if there's just one.
        if (next.length === 1) setSelectedZoneId(next[0].id)
      })
      .catch((err: unknown) => {
        if (!active) return
        const msg =
          err instanceof ZoneFetchError
            ? err.message
            : 'Tidak dapat memuatkan zon penghantaran.'
        setZonesError(msg)
      })
      .finally(() => {
        if (active) setZonesLoading(false)
      })
    return () => {
      active = false
    }
  }, [restaurant.websiteId])

  // ---- Money math.
  const subtotal = useMemo(() => cartTotal(cartItems), [cartItems])
  const discount = useMemo(() => cartDiscount(cartItems, promoCode), [cartItems, promoCode])
  const selectedZone = useMemo(
    () => zones.find((z) => z.id === selectedZoneId) ?? null,
    [zones, selectedZoneId]
  )
  const deliveryFee = selectedZone?.fee ?? 0
  const total = Math.max(0, subtotal - discount + deliveryFee)
  const minOrderShortfall =
    selectedZone && selectedZone.minOrder > 0 && subtotal < selectedZone.minOrder
      ? selectedZone.minOrder - subtotal
      : 0

  // ---- Validity for the place-order CTA.
  const resolvedAddress =
    addressChoice === 'saved' ? customer?.address ?? '' : newAddressText
  const valid =
    !!customer?.phone &&
    !!customer?.name?.trim() &&
    resolvedAddress.trim().length >= 8 &&
    !!selectedZoneId &&
    minOrderShortfall === 0 &&
    paymentMethod === 'cod'

  // ---- Place the order.
  const handlePlace = async () => {
    if (!valid || placing || !customer) return
    setPlacing(true)
    setPlaceError(null)
    try {
      const placed = await placeOrder({
        website_id: restaurant.websiteId,
        customer_name: customer.name.trim(),
        customer_phone: customer.phone,
        delivery_address: resolvedAddress.trim(),
        delivery_latitude: pickedLatLng?.lat,
        delivery_longitude: pickedLatLng?.lng,
        delivery_notes: [kitchenNotes, riderNotes].filter(Boolean).join(' · '),
        delivery_zone_id: selectedZoneId ?? undefined,
        items: cartItems.map((c) => ({
          menu_item_id: c.id,
          quantity: c.qty,
        })),
        payment_method: paymentMethod,
      })

      // Persist customer name/address so future checkouts pre-fill.
      updateCustomer({
        id: customer.id,
        name: customer.name.trim(),
        address: resolvedAddress.trim(),
      })

      // Cart goes away on a successful order.
      clearCart()

      // Tracking endpoint is keyed by order_number (e.g. "ORD-3847"),
      // not the UUID — see GET /api/v1/delivery/orders/{order_number}/track.
      router.replace(`/order/${encodeURIComponent(placed.order_number)}/track`)
    } catch (err) {
      const msg =
        err instanceof PlaceOrderError
          ? err.message
          : 'Gagal membuat pesanan. Sila cuba lagi.'
      setPlaceError(msg)
      setPlacing(false)
    }
  }

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

        <AddressSection
          customer={customer}
          choice={addressChoice}
          onChoiceChange={setAddressChoice}
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

        <DeliveryZoneSection
          zones={zones}
          selectedZoneId={selectedZoneId}
          onSelect={setSelectedZoneId}
          subtotal={subtotal}
          loading={zonesLoading}
          error={zonesError}
        />

        <PaymentMethodSection
          selected={paymentMethod}
          onSelect={setPaymentMethod}
        />

        <OrderSummaryAccordion
          items={cartItems}
          subtotal={subtotal}
          deliveryFee={deliveryFee}
          discount={discount}
          promoCode={promoCode}
          total={total}
        />

        {/* Optional rider notes */}
        <div className="co-sec fade-up" style={{ animationDelay: '200ms' }}>
          <div className="co-sec-head">
            <h2>
              <span className="num">6</span>
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
