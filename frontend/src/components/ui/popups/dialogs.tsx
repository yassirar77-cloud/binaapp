'use client'

import { cn } from '@/lib/utils'
import { AlertTriangle, CheckCircle2, HelpCircle, Info, XCircle } from 'lucide-react'
import { ReactNode, useEffect, useState } from 'react'
import { Modal } from './Modal'

// ---------------------------------------------------------------------------
// Imperative dialog store — drop-in replacements for window.confirm/prompt/
// alert. `<PopupHost />` (mounted once in the root layout) renders the queue.
// ---------------------------------------------------------------------------

export interface ConfirmOptions {
  title: string
  message?: ReactNode
  confirmText?: string
  cancelText?: string
  variant?: 'default' | 'danger'
}

export interface PromptOptions extends Omit<ConfirmOptions, 'variant'> {
  placeholder?: string
  defaultValue?: string
  multiline?: boolean
}

export interface AlertOptions {
  title?: string
  message: ReactNode
  confirmText?: string
  variant?: 'info' | 'success' | 'warning' | 'error'
}

type DialogRequest =
  | { kind: 'confirm'; id: number; opts: ConfirmOptions; resolve: (v: boolean) => void }
  | { kind: 'prompt'; id: number; opts: PromptOptions; resolve: (v: string | null) => void }
  | { kind: 'alert'; id: number; opts: AlertOptions; resolve: () => void }

let nextId = 1
let queue: DialogRequest[] = []
const listeners = new Set<() => void>()

function notify() {
  listeners.forEach((l) => l())
}

function push(req: DialogRequest) {
  queue = [...queue, req]
  notify()
}

function remove(id: number) {
  queue = queue.filter((r) => r.id !== id)
  notify()
}

/** Modal replacement for `window.confirm`. Resolves true on confirm, false otherwise. */
export function confirmDialog(opts: ConfirmOptions): Promise<boolean> {
  return new Promise((resolve) => {
    push({ kind: 'confirm', id: nextId++, opts, resolve })
  })
}

/** Modal replacement for `window.prompt`. Resolves the entered string, or null on cancel. */
export function promptDialog(opts: PromptOptions): Promise<string | null> {
  return new Promise((resolve) => {
    push({ kind: 'prompt', id: nextId++, opts, resolve })
  })
}

/** Modal replacement for `window.alert`. Resolves when acknowledged. */
export function alertDialog(opts: AlertOptions): Promise<void> {
  return new Promise((resolve) => {
    push({ kind: 'alert', id: nextId++, opts, resolve })
  })
}

/** Test helper — clears any queued dialogs. */
export function __resetDialogs() {
  queue = []
  notify()
}

// ---------------------------------------------------------------------------
// Rendering
// ---------------------------------------------------------------------------

const btnBase =
  'inline-flex h-11 items-center justify-center rounded-xl px-4 text-sm font-semibold transition-colors sm:h-10'
const btnPrimary = cn(btnBase, 'bg-volt-400 text-ink-900 hover:bg-volt-300 active:bg-volt-500')
const btnDanger = cn(btnBase, 'bg-err-500 text-white hover:bg-err-400 active:bg-err-500')
const btnGhost = cn(
  btnBase,
  'bg-white/[0.06] text-ink-100 ring-1 ring-white/[0.08] hover:bg-white/[0.1]',
)

const ICONS = {
  danger: { Icon: AlertTriangle, chip: 'bg-err-400/15 text-err-400' },
  confirm: { Icon: HelpCircle, chip: 'bg-volt-400/15 text-volt-400' },
  info: { Icon: Info, chip: 'bg-info-400/15 text-info-400' },
  success: { Icon: CheckCircle2, chip: 'bg-ok-400/15 text-ok-400' },
  warning: { Icon: AlertTriangle, chip: 'bg-warn-400/15 text-warn-400' },
  error: { Icon: XCircle, chip: 'bg-err-400/15 text-err-400' },
} as const

function IconChip({ kind }: { kind: keyof typeof ICONS }) {
  const { Icon, chip } = ICONS[kind]
  return (
    <div
      className={cn('mb-3 flex h-10 w-10 items-center justify-center rounded-xl', chip)}
      aria-hidden="true"
    >
      <Icon className="h-5 w-5" />
    </div>
  )
}

function ConfirmDialogView({ req }: { req: Extract<DialogRequest, { kind: 'confirm' }> }) {
  const [open, setOpen] = useState(true)
  const { opts } = req
  const danger = opts.variant === 'danger'

  const finish = (value: boolean) => {
    if (!open) return
    setOpen(false)
    req.resolve(value)
    setTimeout(() => remove(req.id), 220)
  }

  return (
    <Modal
      open={open}
      onClose={() => finish(false)}
      title={opts.title}
      hideClose
      footer={
        <>
          <button type="button" className={btnGhost} onClick={() => finish(false)}>
            {opts.cancelText ?? 'Batal'}
          </button>
          <button
            type="button"
            className={danger ? btnDanger : btnPrimary}
            onClick={() => finish(true)}
            data-autofocus
          >
            {opts.confirmText ?? 'Teruskan'}
          </button>
        </>
      }
    >
      <IconChip kind={danger ? 'danger' : 'confirm'} />
      {opts.message && <div className="whitespace-pre-line">{opts.message}</div>}
    </Modal>
  )
}

function PromptDialogView({ req }: { req: Extract<DialogRequest, { kind: 'prompt' }> }) {
  const [open, setOpen] = useState(true)
  const [value, setValue] = useState(req.opts.defaultValue ?? '')
  const { opts } = req

  const finish = (result: string | null) => {
    if (!open) return
    setOpen(false)
    req.resolve(result)
    setTimeout(() => remove(req.id), 220)
  }

  const inputCls =
    'w-full rounded-xl bg-white/[0.04] px-3 py-2.5 text-sm text-ink-050 ring-1 ring-white/[0.08] placeholder:text-ink-500 focus:outline-none focus:ring-2 focus:ring-volt-400/60'

  return (
    <Modal
      open={open}
      onClose={() => finish(null)}
      title={opts.title}
      hideClose
      footer={
        <>
          <button type="button" className={btnGhost} onClick={() => finish(null)}>
            {opts.cancelText ?? 'Batal'}
          </button>
          <button type="button" className={btnPrimary} onClick={() => finish(value)}>
            {opts.confirmText ?? 'OK'}
          </button>
        </>
      }
    >
      {opts.message && <div className="mb-3 whitespace-pre-line">{opts.message}</div>}
      <form
        onSubmit={(e) => {
          e.preventDefault()
          finish(value)
        }}
      >
        {opts.multiline ? (
          <textarea
            className={cn(inputCls, 'min-h-[96px] resize-y')}
            value={value}
            placeholder={opts.placeholder}
            onChange={(e) => setValue(e.target.value)}
            data-autofocus
          />
        ) : (
          <input
            type="text"
            className={inputCls}
            value={value}
            placeholder={opts.placeholder}
            onChange={(e) => setValue(e.target.value)}
            data-autofocus
          />
        )}
        {/* Allow Enter-to-submit for single-line prompts */}
        {!opts.multiline && <button type="submit" hidden />}
      </form>
    </Modal>
  )
}

function AlertDialogView({ req }: { req: Extract<DialogRequest, { kind: 'alert' }> }) {
  const [open, setOpen] = useState(true)
  const { opts } = req

  const finish = () => {
    if (!open) return
    setOpen(false)
    req.resolve()
    setTimeout(() => remove(req.id), 220)
  }

  return (
    <Modal
      open={open}
      onClose={finish}
      title={opts.title}
      hideClose
      footer={
        <button type="button" className={btnPrimary} onClick={finish} data-autofocus>
          {opts.confirmText ?? 'OK'}
        </button>
      }
    >
      <IconChip kind={opts.variant ?? 'info'} />
      <div className="whitespace-pre-line">{opts.message}</div>
    </Modal>
  )
}

/**
 * Mount once (root layout). Renders the oldest pending imperative dialog.
 */
export function PopupHost() {
  const [, setTick] = useState(0)

  useEffect(() => {
    const listener = () => setTick((t) => t + 1)
    listeners.add(listener)
    return () => {
      listeners.delete(listener)
    }
  }, [])

  const current = queue[0]
  if (!current) return null

  switch (current.kind) {
    case 'confirm':
      return <ConfirmDialogView key={current.id} req={current} />
    case 'prompt':
      return <PromptDialogView key={current.id} req={current} />
    case 'alert':
      return <AlertDialogView key={current.id} req={current} />
  }
}
