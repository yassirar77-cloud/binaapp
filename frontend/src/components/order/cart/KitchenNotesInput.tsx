'use client'

import { Textarea } from '../primitives'
import { useCartStore, useKitchenNotes } from '../cart-store'

/**
 * Free-text instructions for the kitchen (e.g. "kurang pedas", "tanpa
 * bawang"). Persists to the cart store so reloading the cart page
 * preserves the typed note.
 *
 * Per the PR-4 prompt this is intentionally unbounded — no character
 * limit, no validation. Real moderation can be added at the order
 * placement boundary in PR 5.
 */
export function KitchenNotesInput() {
  const notes = useKitchenNotes()
  const setKitchenNotes = useCartStore((s) => s.setKitchenNotes)

  return (
    <div className="notes-section">
      <div className="lbl">
        Nota untuk restoran <span className="opt">(pilihan)</span>
      </div>
      <Textarea
        rows={2}
        placeholder="cth: Kurang pedas, tiada bawang, beg berasingan…"
        value={notes}
        onChange={(e) => setKitchenNotes(e.target.value)}
        aria-label="Nota untuk restoran"
      />
    </div>
  )
}
