'use client'

import { ChevronRight } from 'lucide-react'
import { Card } from './primitives/Card'
import { LinkBtn } from './primitives/LinkBtn'
import { Pill, type PillTone } from './primitives/Pill'

export type InvoiceStatus = 'success' | 'pending' | 'failed'

export interface Invoice {
  id: string
  invoiceNumber: string | null
  label: string
  date: string
  amount: number | null
  status: InvoiceStatus
  toyyibpayBillCode?: string | null
}

interface BillingCardProps {
  invoices: Invoice[] | null
  hasActiveBilling: boolean
  nextChargeDate: string | null
  onViewAll: () => void
  onChangePayment: () => void
  onDownloadReceipt: (invoice: Invoice) => void
}

const STATUS_PILL: Record<InvoiceStatus, { tone: PillTone; label: string }> = {
  success: { tone: 'green', label: 'Bayar' },
  pending: { tone: 'amber', label: 'Pending' },
  failed:  { tone: 'red',   label: 'Gagal' },
}

function formatAmount(amount: number | null): string {
  if (amount === null || !Number.isFinite(amount)) return '—'
  return `RM${amount.toFixed(2)}`
}

export function BillingCard({
  invoices,
  hasActiveBilling,
  nextChargeDate,
  onViewAll,
  onChangePayment,
  onDownloadReceipt,
}: BillingCardProps) {
  const loading = invoices === null
  const isEmpty = !loading && invoices.length === 0

  return (
    <Card>
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginBottom: 16,
          gap: 12,
        }}
      >
        <h3 style={{ fontSize: 15, fontWeight: 500, margin: 0 }}>Bil &amp; pembayaran</h3>
        <LinkBtn onClick={onViewAll}>
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}>
            Muat turun semua
            <ChevronRight size={12} strokeWidth={1.5} style={{ display: 'inline-block' }} />
          </span>
        </LinkBtn>
      </div>

      {hasActiveBilling && (
        <div
          style={{
            background: '#f7f7f8',
            border: '0.5px solid var(--border)',
            borderRadius: 10,
            padding: '12px 14px',
            display: 'flex',
            alignItems: 'center',
            gap: 12,
            flexWrap: 'wrap',
          }}
        >
          <span
            style={{
              background: '#fff',
              border: '0.5px solid var(--border-strong)',
              borderRadius: 4,
              fontSize: 10,
              fontWeight: 500,
              letterSpacing: 0.5,
              color: 'var(--ink-1)',
              padding: '3px 6px',
            }}
          >
            FPX
          </span>
          <span style={{ fontSize: 13, color: 'var(--ink-1)' }}>ToyyibPay · auto-bayar</span>
          {nextChargeDate && (
            <span style={{ fontSize: 13, color: 'var(--ink-3)' }}>
              · caj seterusnya {nextChargeDate}
            </span>
          )}
          <div style={{ flex: 1 }} />
          <LinkBtn onClick={onChangePayment}>Tukar</LinkBtn>
        </div>
      )}

      {loading && (
        <div style={{ marginTop: 16 }}>
          {[0, 1, 2].map((i) => (
            <div
              key={i}
              style={{
                display: 'grid',
                gridTemplateColumns: '1fr auto',
                alignItems: 'center',
                gap: 16,
                padding: '14px 0',
                borderTop: i === 0 ? 'none' : '0.5px solid var(--border)',
              }}
            >
              <div>
                <div style={{ height: 12, width: 120, background: '#eeeff2', borderRadius: 4 }} />
                <div style={{ height: 10, width: 80, background: '#eeeff2', borderRadius: 4, marginTop: 6 }} />
              </div>
              <div style={{ height: 12, width: 60, background: '#eeeff2', borderRadius: 4 }} />
            </div>
          ))}
        </div>
      )}

      {isEmpty && (
        <div
          style={{
            marginTop: 16,
            padding: '20px 0',
            textAlign: 'center',
            fontSize: 13,
            color: 'var(--ink-3)',
          }}
        >
          Belum ada invois
        </div>
      )}

      {!loading && !isEmpty && (
        <div style={{ marginTop: 16 }}>
          {invoices.map((inv, i) => {
            const pill = STATUS_PILL[inv.status]
            return (
              <div
                key={inv.id}
                className="profile-row"
                style={{
                  display: 'grid',
                  gridTemplateColumns: '1fr auto auto auto',
                  alignItems: 'center',
                  gap: 16,
                  padding: '14px 0',
                  borderTop: i === 0 ? 'none' : '0.5px solid var(--border)',
                }}
              >
                <div className="profile-row__main" style={{ minWidth: 0 }}>
                  <div
                    style={{
                      fontSize: 13,
                      color: 'var(--ink-1)',
                      fontWeight: 500,
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                    }}
                  >
                    {inv.label}
                  </div>
                  <div style={{ fontSize: 12, color: 'var(--ink-3)', marginTop: 2 }}>{inv.date}</div>
                </div>
                <Pill tone={pill.tone}>{pill.label}</Pill>
                <span
                  style={{
                    fontSize: 13,
                    color: 'var(--ink-1)',
                    fontVariantNumeric: 'tabular-nums',
                    minWidth: 60,
                    textAlign: 'right',
                  }}
                >
                  {formatAmount(inv.amount)}
                </span>
                <LinkBtn onClick={() => onDownloadReceipt(inv)}>Resit</LinkBtn>
              </div>
            )
          })}
        </div>
      )}
    </Card>
  )
}
