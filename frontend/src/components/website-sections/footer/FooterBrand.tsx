/**
 * FooterBrand — footer with logo text, tagline, social icons, and copyright.
 */

import React from 'react'
import type { FooterBrandProps } from '@/types/recipe'

export default function FooterBrand({
  business_name,
  tagline,
  social_links,
  copyright_year,
  powered_by = true,
  whatsapp_number,
}: FooterBrandProps) {
  const year = copyright_year || new Date().getFullYear()

  return (
    <footer
      className="py-12 px-4 sm:px-6 lg:px-8"
      style={{
        backgroundColor: 'var(--color-text)',
        color: 'var(--color-background)',
      }}
    >
      <div className="mx-auto" style={{ maxWidth: 'var(--max-width, 1280px)' }}>
        <div className="flex flex-col items-center text-center gap-6">
          {/* Brand */}
          <div>
            <h3
              className="text-2xl font-bold"
              style={{ fontFamily: 'var(--font-heading)' }}
            >
              {business_name}
            </h3>
            {tagline && (
              <p className="mt-1 text-sm opacity-70">{tagline}</p>
            )}
          </div>

          {/* Social links */}
          {social_links && social_links.length > 0 && (
            <div className="flex gap-4">
              {social_links.map((link, i) => (
                <a
                  key={i}
                  href={link.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="w-10 h-10 rounded-full flex items-center justify-center transition-opacity duration-200 hover:opacity-80"
                  style={{ backgroundColor: 'var(--color-primary)' }}
                  aria-label={link.platform}
                >
                  <i className={`${link.icon} text-white`} />
                </a>
              ))}
            </div>
          )}

          {/* WhatsApp */}
          {whatsapp_number && (
            <a
              href={`https://wa.me/${whatsapp_number}`}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 text-sm opacity-80 hover:opacity-100 transition-opacity"
            >
              <i className="fa-brands fa-whatsapp" />
              +{whatsapp_number}
            </a>
          )}

          {/* Divider */}
          <hr className="w-full max-w-xs opacity-20" />

          {/* Copyright + Powered by */}
          <div className="text-xs opacity-60 space-y-1">
            <p>&copy; {year} {business_name}</p>
            {powered_by && (
              <p>
                Dibina dengan{' '}
                <a
                  href="https://binaapp.my"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="underline hover:opacity-100"
                >
                  BinaApp
                </a>
              </p>
            )}
          </div>
        </div>
      </div>
    </footer>
  )
}
