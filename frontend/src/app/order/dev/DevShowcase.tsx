'use client'

import { useState } from 'react'
import { Plus, Minus, ArrowRight, Phone } from 'lucide-react'
import {
  Button,
  Card,
  Eyebrow,
  Input,
  Pill,
  Sheet,
  Skeleton,
  Spinner,
  Textarea,
} from '@/components/order/primitives'
import {
  useCartStore,
  useCartCount,
  useCartTotal,
} from '@/components/order/cart-store'

/**
 * DEV-ONLY primitive showcase. See app/order/_dev/page.tsx for gating.
 */
export default function DevShowcase() {
  const [sheetOpen, setSheetOpen] = useState(false)
  const [phone, setPhone] = useState('')
  const [note, setNote] = useState('')

  const items = useCartStore((s) => s.items)
  const add = useCartStore((s) => s.add)
  const setQty = useCartStore((s) => s.setQty)
  const remove = useCartStore((s) => s.remove)
  const clear = useCartStore((s) => s.clear)
  const count = useCartCount()
  const total = useCartTotal()

  const sample = { id: 1, name: 'Roti canai telur', price: 4.5 }

  return (
    <div className="viewport" style={{ paddingBottom: 80 }}>
      <header style={{ padding: '20px 20px 8px' }}>
        <Eyebrow>Dev showcase</Eyebrow>
        <h1
          style={{
            fontSize: 22,
            fontWeight: 500,
            letterSpacing: '-0.02em',
            margin: '4px 0 0',
          }}
        >
          Customer-flow primitives
        </h1>
        <p style={{ fontSize: 13, color: 'var(--fg-muted)', margin: '4px 0 0' }}>
          Visual verification only · NODE_ENV=development
        </p>
      </header>

      <Section title="Buttons">
        <Stack>
          <Button>Primary · default</Button>
          <Button>
            Teruskan <ArrowRight size={18} />
          </Button>
          <Button loading>Sebentar…</Button>
          <Button disabled>Disabled</Button>
          <Button variant="ghost">Ghost</Button>
          <Row>
            <Button size="sm">Sm</Button>
            <Button size="pill">Pill</Button>
            <Button size="sm" variant="ghost">
              Ghost sm
            </Button>
          </Row>
        </Stack>
      </Section>

      <Section title="Inputs">
        <Stack>
          <Input
            placeholder="12-345 6789"
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
            inputMode="numeric"
          />
          <Textarea
            rows={3}
            placeholder="Nota untuk restoran…"
            value={note}
            onChange={(e) => setNote(e.target.value)}
          />
        </Stack>
      </Section>

      <Section title="Pills">
        <Row>
          <Pill>Neutral</Pill>
          <Pill tone="ok" dot>
            Buka sekarang
          </Pill>
          <Pill tone="warn">Sibuk</Pill>
          <Pill tone="err" dot>
            Tutup
          </Pill>
          <Pill tone="info">Promo</Pill>
          <Pill tone="brand">Pelita</Pill>
        </Row>
      </Section>

      <Section title="Card">
        <Card>
          <Eyebrow>Pesanan</Eyebrow>
          <h3
            style={{
              fontSize: 15,
              fontWeight: 500,
              margin: '4px 0 6px',
              letterSpacing: '-0.01em',
            }}
          >
            #ORD-3847
          </h3>
          <p style={{ fontSize: 13, color: 'var(--fg-muted)', margin: 0 }}>
            Nasi kandar campur, Teh tarik, Roti canai telur.
          </p>
        </Card>
      </Section>

      <Section title="Eyebrow / divider">
        <Eyebrow>Saiz</Eyebrow>
        <div className="divider" />
        <Eyebrow>Pelarasan</Eyebrow>
      </Section>

      <Section title="Skeleton">
        <Stack>
          <Skeleton style={{ height: 14, width: '60%' }} />
          <Skeleton style={{ height: 14, width: '90%' }} />
          <Skeleton style={{ height: 80, borderRadius: 12 }} />
        </Stack>
      </Section>

      <Section title="Spinner">
        <Row>
          <Spinner />
          <span style={{ fontSize: 13, color: 'var(--fg-muted)' }}>
            Menyemak nombor anda…
          </span>
        </Row>
      </Section>

      <Section title="Logo mark">
        <div className="logo-mark">NP</div>
      </Section>

      <Section title="Cart store (Zustand + localStorage)">
        <Stack>
          <Row>
            <Pill tone="brand">{count} item</Pill>
            <Pill>RM {total.toFixed(2)}</Pill>
          </Row>
          <Row>
            <Button size="sm" onClick={() => add(sample)}>
              <Plus size={14} /> Tambah {sample.name}
            </Button>
            {items.length > 0 && (
              <Button size="sm" variant="ghost" onClick={clear}>
                Kosongkan
              </Button>
            )}
          </Row>
          {items.map((it) => (
            <Card
              key={it.id}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 12,
                padding: 12,
              }}
            >
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: 14, fontWeight: 500 }}>{it.name}</div>
                <div style={{ fontSize: 12, color: 'var(--fg-muted)' }}>
                  RM {(it.price * it.qty).toFixed(2)}
                </div>
              </div>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => setQty(it.id, it.qty - 1)}
                aria-label="Kurang"
              >
                <Minus size={14} />
              </Button>
              <span
                style={{
                  fontSize: 13,
                  fontWeight: 500,
                  fontVariantNumeric: 'tabular-nums',
                  minWidth: 16,
                  textAlign: 'center',
                }}
              >
                {it.qty}
              </span>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => setQty(it.id, it.qty + 1)}
                aria-label="Tambah"
              >
                <Plus size={14} />
              </Button>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => remove(it.id)}
                aria-label="Buang"
              >
                ×
              </Button>
            </Card>
          ))}
        </Stack>
      </Section>

      <Section title="Sheet (bottom sheet)">
        <Button onClick={() => setSheetOpen(true)}>
          <Phone size={16} /> Buka sheet contoh
        </Button>
      </Section>

      <Sheet
        open={sheetOpen}
        onClose={() => setSheetOpen(false)}
        ariaLabel="Contoh sheet"
      >
        <div style={{ padding: '12px 20px 22px' }}>
          <h2
            style={{
              fontSize: 20,
              fontWeight: 500,
              letterSpacing: '-0.02em',
              margin: '0 0 4px',
            }}
          >
            Contoh sheet
          </h2>
          <p
            style={{
              fontSize: 14,
              color: 'var(--fg-2)',
              margin: '0 0 16px',
              lineHeight: 1.5,
            }}
          >
            Tutup dengan klik backdrop, tekan ESC, atau butang di bawah.
          </p>
          <Button onClick={() => setSheetOpen(false)}>Tutup</Button>
        </div>
      </Sheet>
    </div>
  )
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section style={{ padding: '20px' }}>
      <Eyebrow style={{ marginBottom: 10 }}>{title}</Eyebrow>
      {children}
    </section>
  )
}

function Stack({ children }: { children: React.ReactNode }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>{children}</div>
  )
}

function Row({ children }: { children: React.ReactNode }) {
  return (
    <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
      {children}
    </div>
  )
}
