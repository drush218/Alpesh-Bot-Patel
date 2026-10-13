import { useEffect, useMemo, useState } from 'react'
import { fetchAnalyses } from '../../lib/apiClient'
import { signedInt } from '../../lib/macro'
import { fmt, signed } from '../../lib/modelRows'
import type { AnalysesList, AnalysesRow } from '../../types/analysis'

type Filter = 'all' | 'held' | 'watch'
type SortKey = 'ticker' | 'status' | 'weight' | 'ppl' | 'pe_actual' | 'pe' | 'eps' | 'macronet' | 'growth' | 'value' | 'income' | 'total' | 'asof'

const SORTS: Record<SortKey, (r: AnalysesRow) => number | string | null> = {
  ticker: (r) => r.ticker,
  status: (r) => (r.held ? 0 : 1),
  weight: (r) => r.weight_pct,
  ppl: (r) => r.ppl_pct,
  pe_actual: (r) => r.pe_actual,
  pe: (r) => r.pe,
  eps: (r) => r.eps_cagr,
  growth: (r) => r.scores?.growth ?? null,
  value: (r) => r.scores?.value ?? null,
  income: (r) => r.scores?.income ?? null,
  total: (r) => total(r),
  macronet: (r) => r.macro.net,
  asof: (r) => r.data_as_of,
}

const COLUMNS: { key: SortKey; label: string; title?: string; align?: 'right' | 'center' }[] = [
  { key: 'ticker', label: 'Company' },
  { key: 'status', label: 'Status' },
  { key: 'weight', label: 'Weight', align: 'right' },
  { key: 'ppl', label: 'P&L', align: 'right' },
  { key: 'pe_actual', label: 'PE', title: 'Current price over base-year EPS, calculated from the analysis actuals', align: 'right' },
  { key: 'pe', label: 'Fwd PE', title: 'Current price over BAU EPS for the first forecast year', align: 'right' },
  { key: 'eps', label: 'EPS CAGR', title: 'BAU EPS growth per year across the forecast years', align: 'right' },
  { key: 'macronet', label: 'Macro', title: 'Net of the analysis macro links: strong ±2, mild ±1', align: 'right' },
  { key: 'growth', label: 'G', title: 'Your growth score (0–3)', align: 'center' },
  { key: 'value', label: 'V', title: 'Your value score (0–3)', align: 'center' },
  { key: 'income', label: 'I', title: 'Your income score (0–3)', align: 'center' },
  { key: 'total', label: 'Total', title: 'Growth + value + income, out of 9 (blank until all three are scored)', align: 'center' },
  { key: 'asof', label: 'Data as of', align: 'right' },
]

const fmtDate = (iso: string | null) =>
  iso ? new Date(`${iso}T00:00:00`).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: '2-digit' }) : '—'

const total = (r: AnalysesRow) => {
  const s = r.scores
  return s && s.growth != null && s.value != null && s.income != null ? s.growth + s.value + s.income : null
}

// Macro net shaded by strength: faint near zero, full colour from ±4 (|net| ≥ 3 is "strong").
const macroTone = (net: number) =>
  net === 0 ? 'var(--ink3)' : `color-mix(in srgb, ${net > 0 ? 'var(--up)' : 'var(--down)'} ${Math.round(35 + 65 * Math.min(Math.abs(net), 4) / 4)}%, var(--ink3))`

const tone = (x: number | null) => (x == null || x === 0 ? undefined : x > 0 ? 'var(--up)' : 'var(--down)')

export function AnalysesScreen({ onOpen, active }: { onOpen: (ticker: string) => void; active: boolean }) {
  const [data, setData] = useState<AnalysesList | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [filter, setFilter] = useState<Filter>('all')
  const [sort, setSort] = useState<{ key: SortKey; desc: boolean }>({ key: 'status', desc: false })

  // Kept mounted between visits: the old list shows instantly and is refreshed quietly each time
  // the screen comes back, since scorecards or analyses may have changed in the meantime.
  useEffect(() => {
    if (active) fetchAnalyses().then(setData).catch((e) => setError(e.message))
  }, [active])

  const rows = useMemo(() => {
    if (!data) return []
    const kept = data.rows.filter((r) => filter === 'all' || (filter === 'held') === r.held)
    const get = SORTS[sort.key]
    return [...kept].sort((a, b) => {
      const x = get(a), y = get(b)
      if (x == null && y == null) return a.ticker.localeCompare(b.ticker)
      if (x == null) return 1 // blanks last either way
      if (y == null) return -1
      const c = x < y ? -1 : x > y ? 1 : a.ticker.localeCompare(b.ticker)
      return sort.desc ? -c : c
    })
  }, [data, filter, sort])

  const counts = data && {
    all: data.rows.length,
    held: data.rows.filter((r) => r.held).length,
    watch: data.rows.filter((r) => !r.held).length,
  }

  const onSort = (key: SortKey) =>
    setSort((s) => (s.key === key ? { key, desc: !s.desc } : { key, desc: !['ticker', 'status'].includes(key) }))

  return (
    <main style={{ maxWidth: 1240, margin: '0 auto', padding: '26px 20px 80px' }}>
      <div className="an-head">
        <div>
          <h1 style={{ fontFamily: "'IBM Plex Sans', system-ui, sans-serif", fontSize: 20, fontWeight: 600, margin: 0 }}>Analyses</h1>
          <div className="an-sub">Everything analysed, held and watch side by side. Click a row for the full analysis.</div>
        </div>
        {counts && (
          <div className="an-tools">
            {(['all', 'held', 'watch'] as const).map((f) => (
              <button key={f} className={`an-btn${filter === f ? ' primary' : ''}`} onClick={() => setFilter(f)}>
                {f === 'all' ? 'All' : f === 'held' ? 'Held' : 'Watch'} · {counts[f]}
              </button>
            ))}
          </div>
        )}
      </div>

      {error && <p style={{ color: 'var(--down)' }}>{error}</p>}
      {data && !data.holdings_available && (
        <div className="an-callout">
          <span className="k">HOLDINGS</span>
          <span>Couldn't reach Trading212, so every analysis shows as Watch.</span>
        </div>
      )}

      {data && (
        <div className="an-card" style={{ padding: 0, overflowX: 'auto' }}>
          <table className="as-table">
            <thead>
              <tr>
                {COLUMNS.map((c) => (
                  <th key={c.key} title={c.title} style={{ textAlign: c.align ?? 'left' }} onClick={() => onSort(c.key)}>
                    {c.label}
                    {sort.key === c.key && <span className="as-arrow">{sort.desc ? '▾' : '▴'}</span>}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.ticker} onClick={() => onOpen(r.ticker)}>
                  <td>
                    <b>{r.ticker}</b>
                    <div className="an-sub">{r.company}</div>
                  </td>
                  <td>
                    <span className={`as-badge${r.held ? ' held' : ''}`}>{r.held ? 'HELD' : 'WATCH'}</span>
                  </td>
                  <td style={{ textAlign: 'right' }}>{r.weight_pct == null ? '—' : `${fmt(r.weight_pct, 1)}%`}</td>
                  <td style={{ textAlign: 'right', color: tone(r.ppl_pct) }}>{r.ppl_pct == null ? '—' : `${signed(r.ppl_pct, 1)}%`}</td>
                  <td style={{ textAlign: 'right' }} title={r.pe_actual_year ? `${r.pe_actual_year}A EPS` : undefined}>
                    {r.pe_actual == null ? '—' : `${fmt(r.pe_actual, 1)}×`}
                  </td>
                  <td style={{ textAlign: 'right' }}>
                    {r.pe == null ? '—' : `${fmt(r.pe, 1)}×`}
                  </td>
                  <td style={{ textAlign: 'right' }} title={r.eps_cagr_years ?? undefined}>
                    {r.eps_cagr == null ? '—' : `${signed(r.eps_cagr, 1)}%`}
                  </td>
                  <td style={{ textAlign: 'right' }} title={`${r.macro.verdict} · ${r.macro.tailwind_links} tailwind · ${r.macro.headwind_links} headwind links`}>
                    <span style={{ color: macroTone(r.macro.net), fontWeight: Math.abs(r.macro.net) >= 3 ? 600 : 400 }}>{signedInt(r.macro.net)}</span>
                  </td>
                  {(['growth', 'value', 'income'] as const).map((d) => (
                    <td key={d} style={{ textAlign: 'center' }} className="as-score">
                      {r.scores?.[d] ?? '—'}
                    </td>
                  ))}
                  <td style={{ textAlign: 'center' }} className="as-score">
                    {total(r) == null ? '—' : <b>{total(r)}</b>}
                  </td>
                  <td style={{ textAlign: 'right' }}>
                    {r.stale && <span className="as-stale" title="Earnings reported since this analysis's data date">STALE</span>}
                    {fmtDate(r.data_as_of)}
                  </td>
                </tr>
              ))}
              {rows.length === 0 && (
                <tr className="as-empty">
                  <td colSpan={COLUMNS.length}>Nothing here.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {data && data.not_modelled.length > 0 && filter !== 'watch' && (
        <p className="an-sub" style={{ marginTop: 12 }}>
          Held, not modelled: <b>{data.not_modelled.join(', ')}</b>
        </p>
      )}
    </main>
  )
}
