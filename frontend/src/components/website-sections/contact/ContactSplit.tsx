/**
 * ContactSplit — contact info on one side, Google Map embed on the other.
 * Mobile: stacks vertically.
 */

import React from 'react'
import type { ContactSplitProps } from '@/types/recipe'

export default function ContactSplit({
  heading,
  whatsapp_number,
  whatsapp_cta = 'WhatsApp',
  address,
  hours,
  show_map = false,
  map_query,
  email,
}: ContactSplitProps) {
  const mapSrc = show_map && (map_query || address)
    ? `https://maps.google.com/maps?q=${encodeURIComponent(map_query || address || '')}&output=embed`
    : null

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 lg:gap-16 items-start">
      {/* Info side */}
      <div>
        <h2
          className="text-3xl sm:text-4xl font-bold"
          style={{ fontFamily: 'var(--font-heading)', color: 'var(--color-text)' }}
        >
          {heading}
        </h2>

        <div className="mt-8 space-y-6">
          {whatsapp_number && (
            <a
              href={`https://wa.me/${whatsapp_number}`}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-3 text-white font-semibold rounded-2xl px-7 py-3.5 transition-colors duration-200"
              style={{ backgroundColor: '#25D366' }}
            >
              <i className="fa-brands fa-whatsapp text-xl" />
              {whatsapp_cta}
            </a>
          )}

          {address && (
            <div className="flex items-start gap-3">
              <i
                className="fa-solid fa-location-dot mt-1"
                style={{ color: 'var(--color-primary)' }}
              />
              <p style={{ color: 'var(--color-text-muted)' }}>{address}</p>
            </div>
          )}

          {hours && (
            <div className="flex items-start gap-3">
              <i
                className="fa-solid fa-clock mt-1"
                style={{ color: 'var(--color-primary)' }}
              />
              <p style={{ color: 'var(--color-text-muted)' }}>{hours}</p>
            </div>
          )}

          {email && (
            <div className="flex items-start gap-3">
              <i
                className="fa-solid fa-envelope mt-1"
                style={{ color: 'var(--color-primary)' }}
              />
              <a
                href={`mailto:${email}`}
                className="hover:underline"
                style={{ color: 'var(--color-text-muted)' }}
              >
                {email}
              </a>
            </div>
          )}
        </div>
      </div>

      {/* Map side */}
      {mapSrc ? (
        <div className="rounded-2xl overflow-hidden" style={{ boxShadow: 'var(--shadow-lg)' }}>
          <iframe
            src={mapSrc}
            width="100%"
            height="350"
            style={{ border: 0 }}
            allowFullScreen
            loading="lazy"
            referrerPolicy="no-referrer-when-downgrade"
            title="Location map"
          />
        </div>
      ) : (
        <div
          className="rounded-2xl flex items-center justify-center"
          style={{
            height: '350px',
            backgroundColor: 'var(--color-surface)',
            boxShadow: 'var(--shadow)',
          }}
        >
          <i
            className="fa-solid fa-map text-5xl"
            style={{ color: 'var(--color-text-muted)', opacity: 0.3 }}
          />
        </div>
      )}
    </div>
  )
}
