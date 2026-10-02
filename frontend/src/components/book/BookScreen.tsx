import { useEffect, useState } from 'react'
import { fetchBook } from '../../lib/apiClient'
import type { BookResponse } from '../../types/book'
import { formatGbp } from '../../lib/format'
import { SegmentedControl } from '../common/SegmentedControl'
import { WeightingByIndexPanel } from './WeightingByIndexPanel'
import { Ledger } from './Ledger'

type Filter = 'all' | 'flagged' | 'modelled'

const FILTER_OPTIONS: { value: Filter; label: string }[] = [
  { value: 'all', label: 'All' },
  { value: 'flagged', label: 'Flagged' },
  { value: 'modelled', label: 'Modelled' },
]

export function BookScreen() {
  const [data, setData] = useState<BookResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState<Filter>('all')

  useEffect(() => {
    fetchBook()
      .then(setData)
      .catch((e) => setError(e.message || 'Failed to load Book'))
      .finally(() => setLoading(false))
  }, [])

  if (loading) {
    return <main style={mainStyle}><p style={{ color: 'var(--ink3)' }}>Loading…</p></main>
  }

  if (error) {
    return (
      <main style={mainStyle}>
        <p style={{ color: 'var(--down)' }}>{error}</p>
      </main>
    )
  }

  if (!data) return null

  const filteredLedger = data.ledger.filter((row) => {
    if (filter === 'flagged') return row.has_flag
    if (filter === 'modelled') return row.modelled
    return true
  })

  return (
    <main style={mainStyle}>
      <div style={{ marginBottom: 16 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', flexWrap: 'wrap', gap: 12 }}>
          <h1
            style={{
              margin: 0,
              fontFamily: "'IBM Plex Sans', system-ui, sans-serif",
              fontSize: 24,
              fontWeight: 600,
              letterSpacing: '-.012em',
            }}
          >
            Holdings
          </h1>
          <SegmentedControl options={FILTER_OPTIONS} value={filter} onChange={setFilter} />
        </div>
        <p style={{ color: 'var(--ink3)', fontSize: 11, marginTop: 4 }}>
          {data.summary.holdings_count} holdings · {formatGbp(data.summary.total_book_gbp)} ·{' '}
          {data.summary.unexplained_count} unexplained overnight · {data.summary.no_model_count} without a model
        </p>
      </div>

      <WeightingByIndexPanel rows={data.index_exposure} />
      <Ledger rows={filteredLedger} />
    </main>
  )
}

const mainStyle = {
  maxWidth: 1240,
  margin: '0 auto',
  padding: '26px 20px 80px',
} as const
