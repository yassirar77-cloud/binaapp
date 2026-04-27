/**
 * ComponentRegistry — maps component name strings (from PageRecipe)
 * to lazily-loaded React components.
 *
 * Usage:
 *   const Component = getComponent('HeroSplit')
 *   <Component {...section.props} />
 */

import React from 'react'

type LazyComponent = React.LazyExoticComponent<React.ComponentType<any>>

const REGISTRY: Record<string, LazyComponent> = {
  // Hero
  HeroSplit: React.lazy(() => import('../hero/HeroSplit')),

  // About
  AboutStory: React.lazy(() => import('../about/AboutStory')),

  // Menu
  MenuGrid: React.lazy(() => import('../menu/MenuGrid')),

  // Gallery
  GalleryMasonry: React.lazy(() => import('../gallery/GalleryMasonry')),

  // Testimonial
  TestimonialCards: React.lazy(() => import('../testimonial/TestimonialCards')),

  // Contact
  ContactSplit: React.lazy(() => import('../contact/ContactSplit')),

  // Footer
  FooterBrand: React.lazy(() => import('../footer/FooterBrand')),
}

export function getComponent(name: string): LazyComponent {
  const component = REGISTRY[name]
  if (!component) {
    throw new Error(
      `Component "${name}" not found in registry. Available: ${Object.keys(REGISTRY).join(', ')}`
    )
  }
  return component
}

export function getAllComponentNames(): string[] {
  return Object.keys(REGISTRY)
}

export default REGISTRY
