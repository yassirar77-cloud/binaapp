import { notFound } from 'next/navigation'
import DevShowcase from './DevShowcase'

/**
 * /order/dev — Primitive showcase for the customer-flow design system.
 *
 * Gated by NODE_ENV === 'development' so production builds 404 without
 * shipping any of the showcase code. This page exists only to verify the
 * primitives in isolation before they're consumed by real pages — delete
 * this whole `dev/` folder in PR 2 once the phone-identification page
 * proves the primitives work in real usage.
 *
 * The folder is named `dev` (not `_dev`) because Next.js opts any
 * underscore-prefixed folder out of routing entirely, which would make
 * the page unreachable even in development. The `notFound()` guard below
 * is what keeps it out of production.
 */
export default function DevShowcasePage() {
  if (process.env.NODE_ENV !== 'development') {
    notFound()
  }
  return <DevShowcase />
}
