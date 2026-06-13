'use client'

import toast, { type ToastOptions } from 'react-hot-toast'
import { createElement } from 'react'
import { Info, AlertTriangle } from 'lucide-react'

/**
 * appToast — the single transient-message helper for BinaApp.
 *
 * Thin wrapper over react-hot-toast so every toast inherits the dark-navy + lime
 * styling configured on the global <Toaster> in app/layout.tsx. Use this instead
 * of raw alert() for non-blocking feedback (saved / error / info / warning).
 *
 * Blocking dialogs (payment exceeded, confirm actions) use <AppModal> instead.
 */
export const appToast = {
  success: (message: string, opts?: ToastOptions) => toast.success(message, opts),
  error: (message: string, opts?: ToastOptions) => toast.error(message, opts),
  info: (message: string, opts?: ToastOptions) =>
    toast(message, {
      icon: createElement(Info, { className: 'h-5 w-5', color: '#3FB8FF' }),
      ...opts,
    }),
  warning: (message: string, opts?: ToastOptions) =>
    toast(message, {
      icon: createElement(AlertTriangle, { className: 'h-5 w-5', color: '#FFB020' }),
      ...opts,
    }),
}

export default appToast
