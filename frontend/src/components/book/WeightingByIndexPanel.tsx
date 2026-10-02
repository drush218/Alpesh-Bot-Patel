import type { IndexExposureRow as IndexExposureRowType } from '../../types/book'
import { IndexExposureRow } from './IndexExposureRow'

interface Props {
  rows: IndexExposureRowType[]
}

export function WeightingByIndexPanel({ rows }: Props) {
  return (
    <section
      style={{
        border: '1px solid var(--line)',
        background: 'var(--panel)',
        borderRadius: 4,
        padding: '15px 16px 14px',
        marginBottom: 14,
        boxShadow: 'var(--shadow)',
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 6, flexWrap: 'wrap', gap: 8 }}>
        <h2
          style={{
            margin: 0,
            fontFamily: "'IBM Plex Sans', system-ui, sans-serif",
            fontSize: 14,
            fontWeight: 600,
            letterSpacing: '.01em',
          }}
        >
          Weighting by index
        </h2>
        <span style={{ fontSize: 10.5, color: 'var(--ink3)' }}>
          limit line at 40% of invested · index = primary listing benchmark
        </span>
      </div>
      <div style={{ overflowX: 'auto' }}>
        {rows.length === 0 ? (
          <p style={{ color: 'var(--ink3)', fontSize: 11.5 }}>No index exposure yet.</p>
        ) : (
          rows.map((row, i) => <IndexExposureRow key={row.code} row={row} rank={i} />)
        )}
      </div>
    </section>
  )
}
