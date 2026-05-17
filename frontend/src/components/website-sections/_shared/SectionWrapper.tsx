/**
 * SectionWrapper — shared wrapper for all website section components.
 *
 * Provides: id anchor, AOS animation attributes, consistent padding,
 * and max-width container.
 */

import React from 'react'

interface SectionWrapperProps {
  id: string
  children: React.ReactNode
  animation?: string
  animationDelay?: number
  className?: string
  fullWidth?: boolean
}

export default function SectionWrapper({
  id,
  children,
  animation = 'fade-up',
  animationDelay = 0,
  className = '',
  fullWidth = false,
}: SectionWrapperProps) {
  return (
    <section
      id={id}
      data-aos={animation}
      data-aos-delay={animationDelay}
      className={`py-20 px-4 sm:px-6 lg:px-8 ${className}`}
    >
      {fullWidth ? (
        children
      ) : (
        <div className="mx-auto" style={{ maxWidth: 'var(--max-width, 1280px)' }}>
          {children}
        </div>
      )}
    </section>
  )
}
