// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { Modal } from './Modal'
import {
  PopupHost,
  __resetDialogs,
  alertDialog,
  confirmDialog,
  promptDialog,
} from './dialogs'

afterEach(() => {
  cleanup()
  __resetDialogs()
})

describe('Modal', () => {
  it('renders title and children when open', () => {
    render(
      <Modal open onClose={() => {}} title="Tajuk ujian">
        <p>Kandungan</p>
      </Modal>,
    )
    expect(screen.getByRole('dialog')).toBeTruthy()
    expect(screen.getByText('Tajuk ujian')).toBeTruthy()
    expect(screen.getByText('Kandungan')).toBeTruthy()
  })

  it('renders nothing when closed', () => {
    render(
      <Modal open={false} onClose={() => {}} title="Tersembunyi">
        <p>Kandungan</p>
      </Modal>,
    )
    expect(screen.queryByRole('dialog')).toBeNull()
  })

  it('calls onClose on Escape', () => {
    const onClose = vi.fn()
    render(
      <Modal open onClose={onClose} title="ESC test">
        <p>Body</p>
      </Modal>,
    )
    fireEvent.keyDown(document, { key: 'Escape' })
    expect(onClose).toHaveBeenCalledTimes(1)
  })

  it('does not close on Escape when not dismissible', () => {
    const onClose = vi.fn()
    render(
      <Modal open onClose={onClose} title="Locked" dismissible={false}>
        <p>Body</p>
      </Modal>,
    )
    fireEvent.keyDown(document, { key: 'Escape' })
    expect(onClose).not.toHaveBeenCalled()
  })

  it('closes on backdrop mousedown but not on panel mousedown', () => {
    const onClose = vi.fn()
    render(
      <Modal open onClose={onClose} title="Backdrop test">
        <p>Body</p>
      </Modal>,
    )
    fireEvent.mouseDown(screen.getByText('Body'))
    expect(onClose).not.toHaveBeenCalled()
    fireEvent.mouseDown(screen.getByRole('dialog'))
    expect(onClose).toHaveBeenCalledTimes(1)
  })

  it('locks body scroll while open and restores it on close', () => {
    const { unmount } = render(
      <Modal open onClose={() => {}} title="Scroll lock">
        <p>Body</p>
      </Modal>,
    )
    expect(document.body.style.overflow).toBe('hidden')
    unmount()
    expect(document.body.style.overflow).toBe('')
  })
})

describe('confirmDialog', () => {
  it('resolves true when the confirm button is clicked', async () => {
    render(<PopupHost />)
    const result = confirmDialog({
      title: 'Padam item?',
      confirmText: 'Padam',
      cancelText: 'Batal',
      variant: 'danger',
    })
    const confirmBtn = await screen.findByRole('button', { name: 'Padam' })
    fireEvent.click(confirmBtn)
    await expect(result).resolves.toBe(true)
  })

  it('resolves false when cancelled', async () => {
    render(<PopupHost />)
    const result = confirmDialog({ title: 'Teruskan?' })
    const cancelBtn = await screen.findByRole('button', { name: 'Batal' })
    fireEvent.click(cancelBtn)
    await expect(result).resolves.toBe(false)
  })

  it('resolves false on Escape', async () => {
    render(<PopupHost />)
    const result = confirmDialog({ title: 'ESC?' })
    await screen.findByText('ESC?')
    fireEvent.keyDown(document, { key: 'Escape' })
    await expect(result).resolves.toBe(false)
  })

  it('shows queued dialogs one at a time', async () => {
    render(<PopupHost />)
    const first = confirmDialog({ title: 'Pertama' })
    confirmDialog({ title: 'Kedua' })
    await screen.findByText('Pertama')
    expect(screen.queryByText('Kedua')).toBeNull()
    fireEvent.click(screen.getByRole('button', { name: 'Teruskan' }))
    await expect(first).resolves.toBe(true)
    await waitFor(() => expect(screen.queryByText('Kedua')).toBeTruthy(), {
      timeout: 2000,
    })
  })
})

describe('promptDialog', () => {
  it('resolves the typed value on OK', async () => {
    render(<PopupHost />)
    const result = promptDialog({ title: 'Sebab penggantungan:' })
    const input = (await screen.findByRole('textbox')) as HTMLInputElement
    fireEvent.change(input, { target: { value: 'melanggar syarat' } })
    fireEvent.click(screen.getByRole('button', { name: 'OK' }))
    await expect(result).resolves.toBe('melanggar syarat')
  })

  it('resolves null on cancel (native prompt semantics)', async () => {
    render(<PopupHost />)
    const result = promptDialog({ title: 'Nota:' })
    const cancelBtn = await screen.findByRole('button', { name: 'Batal' })
    fireEvent.click(cancelBtn)
    await expect(result).resolves.toBeNull()
  })

  it('supports a default value and multiline textarea', async () => {
    render(<PopupHost />)
    const result = promptDialog({
      title: 'Nota penyelesaian:',
      defaultValue: 'selesai',
      multiline: true,
    })
    const box = (await screen.findByRole('textbox')) as HTMLTextAreaElement
    expect(box.tagName).toBe('TEXTAREA')
    expect(box.value).toBe('selesai')
    fireEvent.click(screen.getByRole('button', { name: 'OK' }))
    await expect(result).resolves.toBe('selesai')
  })
})

describe('alertDialog', () => {
  it('resolves when acknowledged', async () => {
    render(<PopupHost />)
    const result = alertDialog({ message: 'Tetapan berjaya disimpan!', variant: 'success' })
    expect(await screen.findByText('Tetapan berjaya disimpan!')).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: 'OK' }))
    await expect(result).resolves.toBeUndefined()
  })
})
