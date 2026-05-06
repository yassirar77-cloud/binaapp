'use client'

import { useEffect, useMemo, useState } from 'react'
import { useRouter } from 'next/navigation'
import toast from 'react-hot-toast'
import { useCustomerStore } from '../customer-store'
import {
  createDispute,
  CreateDisputeError,
  DISPUTE_RESOLUTIONS,
  type DisputeCategoryId,
  type DisputeResolutionId,
} from '../dispute-api'
import {
  fetchTrackedOrder,
  TrackOrderError,
  type TrackedOrderDetail,
} from '../tracking-api'
import { CategoryChipsGrid } from './CategoryChipsGrid'
import {
  DescriptionInput,
  DESCRIPTION_MIN_LENGTH,
} from './DescriptionInput'
import { DisputeHeader } from './DisputeHeader'
import { OrderContextCard } from './OrderContextCard'
import {
  PhotoUpload,
  type DisputePhoto,
} from './PhotoUpload'
import { ResolutionRadios } from './ResolutionRadios'
import { SubmitButton } from './SubmitButton'
import { SuccessOverlay } from './SuccessOverlay'

interface DisputePageClientProps {
  orderNumber: string
}

/**
 * Orchestrator for the customer dispute page.
 *
 * Mount-time guards:
 *   1. Fetch the tracked order (gives us the UUID + items + total
 *      needed for the order-context card and the dispute payload).
 *   2. Customer identity guard — redirect to /order/identify if no
 *      phone in the customer store.
 *   3. Order-not-found → redirect back to menu with toast.
 *
 * Toggles a `dispute-route` class on `.order-flow` so the page
 * background flips to var(--bg-soft) per the design.
 *
 * On submit:
 *   1. Wait for any in-flight photo uploads.
 *   2. Append the customer's preferred resolution to the description
 *      (no dedicated backend column yet — see TODO(disputes) in
 *      ResolutionRadios).
 *   3. POST /api/v1/disputes/customer-create with order UUID +
 *      category + description + evidence_urls.
 *   4. On success, swap the form for the success overlay.
 *   5. On failure, show inline error, KEEP the form contents, allow
 *      retry.
 */
export function DisputePageClient({ orderNumber }: DisputePageClientProps) {
  const router = useRouter()
  const customer = useCustomerStore((s) => s.customer)

  const [hydrated, setHydrated] = useState(false)
  const [orderLoading, setOrderLoading] = useState(true)
  const [orderError, setOrderError] = useState<string | null>(null)
  const [order, setOrder] = useState<TrackedOrderDetail | null>(null)

  const [category, setCategory] = useState<DisputeCategoryId | null>(null)
  const [description, setDescription] = useState('')
  const [photos, setPhotos] = useState<DisputePhoto[]>([])
  const [resolution, setResolution] = useState<DisputeResolutionId | null>(null)

  const [submitting, setSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState<string | null>(null)
  const [success, setSuccess] = useState<{ disputeNumber: string } | null>(null)

  // ---- Toggle the dispute-route class.
  useEffect(() => {
    const flow = document.querySelector('.order-flow')
    if (!flow) return
    flow.classList.add('dispute-route')
    return () => flow.classList.remove('dispute-route')
  }, [])

  // ---- Hydration gate.
  useEffect(() => {
    setHydrated(true)
  }, [])

  // ---- Customer identity guard.
  useEffect(() => {
    if (!hydrated) return
    if (!customer?.phone) {
      router.replace('/order/identify')
    }
  }, [hydrated, customer?.phone, router])

  // ---- Fetch the order to populate the context card.
  useEffect(() => {
    let alive = true
    setOrderLoading(true)
    setOrderError(null)
    fetchTrackedOrder(orderNumber)
      .then((next) => {
        if (!alive) return
        setOrder(next)
        setOrderLoading(false)
      })
      .catch((err: unknown) => {
        if (!alive) return
        if (err instanceof TrackOrderError && err.status === 404) {
          toast('Pesanan tidak ditemui')
          router.replace('/order/menu')
          return
        }
        setOrderError(
          err instanceof Error
            ? err.message
            : 'Tidak dapat memuatkan pesanan.'
        )
        setOrderLoading(false)
      })
    return () => {
      alive = false
    }
  }, [orderNumber, router])

  const uploading = useMemo(
    () => photos.some((p) => p.uploading),
    [photos]
  )
  const photosWithError = useMemo(
    () => photos.some((p) => p.error),
    [photos]
  )

  const ready =
    !!category &&
    !!resolution &&
    description.trim().length >= DESCRIPTION_MIN_LENGTH &&
    !uploading

  const handleSubmit = async () => {
    if (!ready || submitting || !order || !category || !resolution) return

    setSubmitting(true)
    setSubmitError(null)

    try {
      const resolutionLabel =
        DISPUTE_RESOLUTIONS.find((r) => r.id === resolution)?.label ?? resolution
      const description_with_pref = `${description.trim()}\n\nResolusi yang diharapkan: ${resolutionLabel}`

      const evidenceUrls = photos
        .map((p) => p.uploadedUrl)
        .filter((u): u is string => typeof u === 'string' && u.length > 0)

      const placed = await createDispute({
        orderId: order.order.id,
        category,
        description: description_with_pref,
        evidenceUrls,
        customerName: customer?.name || order.order.customerName,
        customerPhone: customer?.phone || order.order.customerPhone,
      })

      setSuccess({ disputeNumber: placed.disputeNumber })
    } catch (err) {
      const msg =
        err instanceof CreateDisputeError
          ? err.status === 409
            ? 'Aduan untuk pesanan ini sudah ada. Sila semak status aduan.'
            : err.message
          : err instanceof Error
            ? err.message
            : 'Gagal menghantar aduan. Sila cuba lagi.'
      setSubmitError(msg)
      setSubmitting(false)
    }
  }

  // ---- Render branches.
  if (!hydrated || (hydrated && !customer?.phone)) {
    return null
  }

  if (orderLoading) {
    return (
      <>
        <DisputeHeader orderNumber={orderNumber} />
        <div style={{ padding: '40px 20px', color: 'var(--fg-muted)', fontSize: 13 }}>
          Memuatkan pesanan…
        </div>
      </>
    )
  }

  if (orderError || !order) {
    return (
      <>
        <DisputeHeader orderNumber={orderNumber} />
        <div className="dp-sections">
          <div className="dp-sec">
            <h3>Tidak dapat memuatkan pesanan</h3>
            <p style={{ fontSize: 13, color: 'var(--fg-muted)', margin: 0 }}>
              {orderError ?? 'Pesanan tidak ditemui.'}
            </p>
          </div>
        </div>
      </>
    )
  }

  if (success) {
    return (
      <>
        <DisputeHeader title="Aduan dihantar" orderNumber={orderNumber} />
        <SuccessOverlay
          disputeNumber={success.disputeNumber}
          orderNumber={order.order.orderNumber}
        />
      </>
    )
  }

  return (
    <>
      <DisputeHeader orderNumber={orderNumber} />

      <div className="empathy">
        <h2>Maaf ada masalah dengan pesanan anda</h2>
        <p>Beritahu kami apa yang berlaku — kami akan bantu selesaikan.</p>
      </div>

      <div className="dp-sections">
        <OrderContextCard order={order.order} items={order.items} />

        <CategoryChipsGrid selected={category} onSelect={setCategory} />

        <DescriptionInput value={description} onChange={setDescription} />

        <PhotoUpload
          orderNumber={order.order.orderNumber}
          photos={photos}
          onChange={setPhotos}
        />

        <ResolutionRadios selected={resolution} onSelect={setResolution} />

        {photosWithError && (
          <div className="submit-error" role="status">
            <span>
              Sebahagian gambar gagal dimuat naik. Tap silang untuk buang dan cuba lagi
              jika perlu — atau hantar aduan tanpa gambar tersebut.
            </span>
          </div>
        )}
      </div>

      <SubmitButton
        disabled={!ready}
        loading={submitting}
        uploading={uploading}
        error={submitError}
        onSubmit={handleSubmit}
      />
    </>
  )
}
