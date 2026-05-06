'use client'

import { useEffect, useRef, useState } from 'react'
import { useRouter } from 'next/navigation'
import { ArrowRight, Info, Lock } from 'lucide-react'
import { Button, Spinner } from '../primitives'
import { lookupCustomer } from '../api'
import { useCustomerStore } from '../customer-store'
import {
  fromStorageFormat,
  isValidTyped,
  toStorageFormat,
} from '../phone'
import { useRestaurant } from '../ThemeProvider'
import type { Customer } from '../types'
import { PhoneInput } from './PhoneInput'
import { ReturningCustomerCard } from './ReturningCustomerCard'

type Phase =
  | { kind: 'idle' }
  | { kind: 'loading' }
  | { kind: 'returning'; customer: { id: string; name: string; address: string; phone: string } }
  | { kind: 'new' }

/**
 * State machine + API wiring for the phone-identification page.
 *
 *   idle (digits < 9)
 *     ↓ user types up to 9 digits
 *   loading
 *     ↓ GET /api/v1/customers/lookup
 *   returning  ──▶ user taps Continue ──▶ /order/menu
 *   new        ──▶ user taps Continue ──▶ /order/menu
 *
 * If the API errors, we fall back to `new` so a flaky backend never
 * blocks a customer from ordering.
 */
export function IdentifyForm() {
  const restaurant = useRestaurant()
  const router = useRouter()
  const setCustomer = useCustomerStore((s) => s.setCustomer)
  const storedCustomer = useCustomerStore((s) => s.customer)
  const inputRef = useRef<HTMLInputElement>(null)
  const abortRef = useRef<AbortController | null>(null)

  const [typed, setTyped] = useState('') // 9 digits max, no leading 0
  const [phase, setPhase] = useState<Phase>({ kind: 'idle' })
  const [submitting, setSubmitting] = useState(false)

  // ---- Pre-fill from localStorage on mount (Q3: never auto-redirect, do
  //      pre-fill so a returning customer is one tap away from continuing).
  useEffect(() => {
    if (storedCustomer?.phone) {
      const stripped = fromStorageFormat(storedCustomer.phone).slice(0, 9)
      if (stripped.length === 9) {
        setTyped(stripped)
      }
    }
    // intentionally only on mount — we don't want to overwrite the user's
    // typing if the store updates later via another tab
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // ---- Lookup whenever we have 9 digits. AbortController guards against
  //      stale results: if the user keeps typing or backspaces, the
  //      in-flight request gets cancelled before its result lands.
  useEffect(() => {
    abortRef.current?.abort()

    if (!isValidTyped(typed)) {
      setPhase({ kind: 'idle' })
      return
    }

    const controller = new AbortController()
    abortRef.current = controller
    setPhase({ kind: 'loading' })

    const run = async () => {
      try {
        const storage = toStorageFormat(typed)
        const result = await lookupCustomer(restaurant.websiteId, storage, controller.signal)
        if (controller.signal.aborted) return

        if (result.exists) {
          setPhase({ kind: 'returning', customer: result.customer })
        } else {
          setPhase({ kind: 'new' })
        }
      } catch (err) {
        if (controller.signal.aborted) return
        // Defensive fallback: treat unexpected backend errors as new
        // customer — never block ordering on a flaky lookup.
        // eslint-disable-next-line no-console
        console.error('[order/identify] lookup failed, falling back to new customer:', err)
        setPhase({ kind: 'new' })
      }
    }

    void run()

    return () => controller.abort()
  }, [typed, restaurant.websiteId])

  const handleContinue = async () => {
    if (!isValidTyped(typed) || submitting) return
    setSubmitting(true)

    const phone = toStorageFormat(typed)
    const isReturning = phase.kind === 'returning'

    const customer: Customer = isReturning
      ? {
          id: phase.customer.id,
          phone: phase.customer.phone || phone,
          name: phase.customer.name,
          address: phase.customer.address,
          savedAt: new Date().toISOString(),
        }
      : {
          id: null,
          phone,
          name: '',
          address: '',
          savedAt: new Date().toISOString(),
        }

    try {
      setCustomer(customer)
    } catch (err) {
      // Private browsing / quota issues — proceed without persistence.
      // eslint-disable-next-line no-console
      console.warn('[order/identify] could not persist customer:', err)
    }

    router.push('/order/menu')
  }

  const buttonDisabled =
    !isValidTyped(typed) || phase.kind === 'loading' || submitting

  return (
    <>
      <div className="resto-header fade-up">
        <div className="resto-logo" aria-hidden="true">
          {restaurant.initials}
        </div>
        <div style={{ textAlign: 'center' }}>
          <p className="resto-name">{restaurant.name}</p>
          <div className="resto-cuisine">{restaurant.cuisine}</div>
        </div>
      </div>

      <div className="welcome fade-up" style={{ animationDelay: '60ms' }}>
        <h1>Selamat datang ke {restaurant.short}</h1>
        <p>Masukkan nombor telefon untuk mula.</p>
      </div>

      <div className="fade-up" style={{ animationDelay: '120ms' }}>
        <PhoneInput
          ref={inputRef}
          value={typed}
          onChange={setTyped}
          disabled={submitting}
          autoFocus
        />
      </div>

      {phase.kind === 'loading' && (
        <div className="checking fade-up" aria-live="polite">
          <Spinner />
          <span>Menyemak nombor anda…</span>
        </div>
      )}

      {phase.kind === 'returning' && (
        <ReturningCustomerCard
          name={phase.customer.name}
          address={phase.customer.address}
        />
      )}

      {phase.kind === 'new' && (
        <div className="new-customer-note fade-up" aria-live="polite">
          <Info className="icon" size={14} aria-hidden="true" />
          <span>Pelanggan baru? Anda akan didaftarkan automatik.</span>
        </div>
      )}

      <div className="continue-area">
        <Button
          disabled={buttonDisabled}
          loading={phase.kind === 'loading' || submitting}
          onClick={handleContinue}
        >
          {phase.kind === 'loading' ? (
            <>Sebentar…</>
          ) : submitting ? (
            <>Sedang teruskan…</>
          ) : (
            <>
              Teruskan
              <ArrowRight size={18} />
            </>
          )}
        </Button>
      </div>

      <div className="privacy">
        <Lock className="icon" size={12} aria-hidden="true" />
        <span>Kami tidak akan kongsi nombor anda.</span>
      </div>
      <div className="powered">
        <span className="dot">●</span> Dikuasakan oleh BinaApp
      </div>
    </>
  )
}
