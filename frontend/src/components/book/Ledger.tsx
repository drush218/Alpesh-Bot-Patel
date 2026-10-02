import { useState } from 'react'
import type { LedgerRow as LedgerRowType } from '../../types/book'
import { LedgerRow } from './LedgerRow'

interface Props {
  rows: LedgerRowType[]
}

export function Ledger({ rows }: Props) {
  const [expanded, setExpanded] = useState<string | null>(null)

  return (
    <>
      <section
        style={{
          border: '1px solid var(--line)',
          background: 'var(--panel)',
          borderRadius: 4,
          overflow: 'hidden',
          boxShadow: 'var(--shadow)',
        }}
      >
        <div
          className="ledger-header"
          style={{
            borderBottom: '1px solid var(--line)',
            background: 'var(--panel2)',
            fontSize: 10,
            letterSpacing: '.09em',
            textTransform: 'uppercase',
            color: 'var(--ink3)',
          }}
        >
          <span />
          <span>holding</span>
          <span>weight · cost basis ○</span>
          <span style={{ textAlign: 'right' }}>wt</span>
          <span style={{ textAlign: 'right' }}>price</span>
          <span style={{ textAlign: 'right' }}>today vs exp</span>
          <span style={{ textAlign: 'right' }}>live PE</span>
          <span style={{ textAlign: 'right' }}>band</span>
          <span />
        </div>

        {rows.length === 0 ? (
          <p style={{ padding: 16, color: 'var(--ink3)', fontSize: 11.5 }}>No holdings match this filter.</p>
        ) : (
          rows.map((row) => (
            <LedgerRow
              key={row.ticker}
              row={row}
              open={expanded === row.ticker}
              onToggle={() => setExpanded((prev) => (prev === row.ticker ? null : row.ticker))}
            />
          ))
        )}
      </section>
      <p style={{ fontSize: 10.5, color: 'var(--ink3)', marginTop: 8 }}>
        bars GBP weight, 20% scale · ○ cost basis · accent gutter = open flag · band = price in LOW–HIGH at reference multiple
      </p>
    </>
  )
}
