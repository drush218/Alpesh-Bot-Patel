import { useState } from 'react'
import { fetchBenchmarks } from '../../lib/apiClient'
import { formatGbp, formatPct, formatSignedGbp, formatSignedPct } from '../../lib/format'
import type { AccountSummary, BenchmarksResponse } from '../../types/account'

type Tone = 'up' | 'down' | 'ink3'

interface Metric {
  label: string
  value: string
  sub?: string
  tone?: Tone
}

const toneOf = (v: number | null | undefined): Tone => (v == null ? 'ink3' : v < 0 ? 'down' : 'up')

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' })
}

function metricsFor(a: AccountSummary): Metric[] {
  const hasDeposits = a.net_deposited_gbp != null
  return [
    { label: 'portfolio value', value: formatGbp(a.portfolio_value_gbp) },
    {
      label: 'net deposited',
      value: hasDeposits ? formatGbp(a.net_deposited_gbp!) : '—',
      sub: a.first_deposit_date ? `since ${formatDate(a.first_deposit_date)}` : undefined,
      tone: 'ink3',
    },
    {
      label: 'total return',
      value: a.total_return_gbp != null ? formatSignedGbp(a.total_return_gbp) : '—',
      sub: a.total_return_pct != null ? formatSignedPct(a.total_return_pct) : undefined,
      tone: toneOf(a.total_return_pct),
    },
    {
      label: 'annualised (money-weighted)',
      value: a.cagr_pct != null ? formatPct(a.cagr_pct) : '—',
      sub: [
        a.years != null ? `over ${a.years.toFixed(1)} yrs` : null,
        a.simple_cagr_pct != null ? `day-one basis ${formatPct(a.simple_cagr_pct)}` : null,
      ].filter(Boolean).join(' · ') || undefined,
      tone: 'ink3',
    },
    { label: 'cost basis', value: formatGbp(a.cost_basis_gbp) },
    {
      label: 'cash',
      value: formatGbp(a.cash_gbp),
      sub: a.cash_pct_of_book != null ? `${formatPct(a.cash_pct_of_book)} of book` : undefined,
      tone: 'ink3',
    },
    {
      label: 'unrealised P&L',
      value: formatSignedGbp(a.unrealised_ppl_gbp),
      sub: a.unrealised_ppl_pct != null ? formatSignedPct(a.unrealised_ppl_pct) : undefined,
      tone: toneOf(a.unrealised_ppl_pct),
    },
  ]
}

const labelStyle = { fontSize: 10, letterSpacing: '.09em', color: 'var(--ink3)', textTransform: 'uppercase' } as const

export function AccountStrip({ account }: { account: AccountSummary }) {
  const [open, setOpen] = useState(false)
  const [benchmarks, setBenchmarks] = useState<BenchmarksResponse | null>(null)
  const [benchError, setBenchError] = useState<string | null>(null)

  const toggle = () => {
    setOpen((o) => !o)
    if (!benchmarks && !benchError) {
      fetchBenchmarks()
        .then(setBenchmarks)
        .catch((e) => setBenchError(e.message || 'Failed to load index returns'))
    }
  }

  return (
    <section
      style={{
        border: '1px solid var(--line)',
        background: 'var(--panel)',
        borderRadius: 4,
        padding: 18,
        marginBottom: 14,
        boxShadow: 'var(--shadow)',
      }}
    >
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(148px, 1fr))', gap: '16px 20px' }}>
        {metricsFor(account).map((m) => (
          <div key={m.label}>
            <div style={labelStyle}>{m.label}</div>
            <div style={{ fontSize: 19, fontWeight: 600, letterSpacing: '-.01em', fontVariantNumeric: 'tabular-nums' }}>
              {m.value}
            </div>
            {m.sub && (
              <div style={{ fontSize: 11, marginTop: 2, color: `var(--${m.tone ?? 'ink3'})` }}>{m.sub}</div>
            )}
          </div>
        ))}
      </div>

      <div style={{ marginTop: 14, paddingTop: 13, borderTop: '1px solid var(--line)' }}>
        <button
          onClick={toggle}
          disabled={account.cagr_pct == null}
          style={{
            fontFamily: 'inherit',
            fontSize: 12,
            color: 'var(--ink2)',
            background: 'transparent',
            border: 0,
            padding: 0,
            cursor: account.cagr_pct == null ? 'default' : 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: 8,
          }}
        >
          <span style={{ color: 'var(--accent)' }}>{open ? '▾' : '▸'}</span>
          Return vs indices <span style={{ color: 'var(--ink3)' }}>your deposits, same dates, put in each index</span>
        </button>

        {open && (
          <div style={{ marginTop: 13 }}>
            {benchError && <p style={{ color: 'var(--down)', fontSize: 11, margin: 0 }}>{benchError}</p>}
            {!benchmarks && !benchError && <p style={{ color: 'var(--ink3)', fontSize: 11, margin: 0 }}>Loading…</p>}
            {benchmarks && (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))', gap: 14 }}>
                {benchmarks.indices.map((i) => {
                  const delta = i.cagr_pct != null && account.cagr_pct != null ? account.cagr_pct - i.cagr_pct : null
                  return (
                    <div key={i.symbol}>
                      <div style={labelStyle}>{i.name}</div>
                      <div style={{ fontSize: 16 }}>{i.cagr_pct != null ? formatPct(i.cagr_pct) : 'N/A'}</div>
                      {delta != null && (
                        <div style={{ fontSize: 11, color: delta >= 0 ? 'var(--up)' : 'var(--down)' }}>
                          {delta >= 0 ? '+' : '−'}
                          {Math.abs(delta).toFixed(1)}pp
                        </div>
                      )}
                    </div>
                  )
                })}
              </div>
            )}
          </div>
        )}
      </div>
    </section>
  )
}
