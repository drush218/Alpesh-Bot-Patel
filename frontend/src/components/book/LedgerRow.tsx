import type { LedgerRow as LedgerRowType } from '../../types/book'
import { formatGbp, formatSignedPct, instrumentTicker, truncate } from '../../lib/format'

const WEIGHT_BAR_SCALE = 20 // bars are on a 0-20% scale; 20% weight = a full bar

interface Props {
  row: LedgerRowType
  open: boolean
  onToggle: () => void
  onOpenAnalysis: (ticker: string) => void
}

function Dimmed() {
  return <span style={{ color: 'var(--ink3)' }}>—</span>
}

function MoveExplain({ row, onOpenAnalysis }: { row: LedgerRowType; onOpenAnalysis: (t: string) => void }) {
  const actual = row.today_vs_exp_pct ?? 0
  const expected = row.expected_pct ?? 0
  const residual = row.residual_pct ?? 0
  const total = Math.abs(expected) + Math.abs(residual) || 1
  const fig = (label: string, v: string, color?: string) => (
    <div>
      <div style={{ fontSize: 10, letterSpacing: '.08em', textTransform: 'uppercase', color: 'var(--ink3)' }}>{label}</div>
      <div style={{ fontSize: 15, color: color ?? 'var(--ink)' }}>{v}</div>
    </div>
  )
  const ticker = instrumentTicker(row.ticker)
  return (
    <div style={{ marginBottom: 14, paddingBottom: 12, borderBottom: '1px solid var(--line)' }}>
      <div style={{ display: 'flex', gap: 28, flexWrap: 'wrap' }}>
        {fig('actual', formatSignedPct(actual), actual >= 0 ? 'var(--up)' : 'var(--down)')}
        {fig('expected', formatSignedPct(expected))}
        {fig('residual', formatSignedPct(residual), row.flag ? 'var(--accent)' : undefined)}
        {fig('z', (row.z_score ?? 0).toFixed(1), row.flag ? 'var(--accent)' : undefined)}
      </div>
      <div style={{ display: 'flex', gap: 1, height: 9, margin: '10px 0 4px', maxWidth: 420 }}>
        <div style={{ flex: Math.abs(expected) / total, background: 'var(--ink3)', opacity: 0.6 }} />
        <div style={{ flex: Math.abs(residual) / total, background: 'var(--accent)' }} />
      </div>
      <div style={{ fontSize: 10.5 }}>
        index {formatSignedPct(expected)} (β {row.index_beta?.toFixed(2) ?? '—'}) · <span style={{ color: 'var(--accent)' }}>residual {formatSignedPct(residual)}</span>
        {row.fit_r2 != null && ` · fit R² ${row.fit_r2.toFixed(2)}`} · {row.move_date}
      </div>
      {row.flag === 'unexplained' && (
        <div style={{ marginTop: 8, fontSize: 11.5, color: 'var(--ink2)' }}>
          Moved well beyond what its index explains.{' '}
          {row.modelled ? (
            <button onClick={() => onOpenAnalysis(ticker)} style={{ border: 0, background: 'transparent', color: 'var(--accent)', cursor: 'pointer', padding: 0, font: 'inherit' }}>
              Check the {ticker} analysis ▸
            </button>
          ) : (
            <span style={{ color: 'var(--accent)' }}>No analysis on file: worth running one.</span>
          )}
        </div>
      )}
      {row.flag === 'earnings' && <div style={{ marginTop: 8, fontSize: 11.5, color: 'var(--ink2)' }}>Large move on a results day, labelled earnings rather than unexplained.</div>}
    </div>
  )
}

export function LedgerRow({ row, open, onToggle, onOpenAnalysis }: Props) {
  const weightBarPct = Math.min(100, (row.weight_of_book_pct / WEIGHT_BAR_SCALE) * 100)
  const costDotPct = row.cost_basis_of_book_pct != null ? Math.min(100, (row.cost_basis_of_book_pct / WEIGHT_BAR_SCALE) * 100) : null

  return (
    <>
      <div className={`ledger-row${open ? ' open' : ''}`} onClick={onToggle}>
        <span style={{ alignSelf: 'stretch', background: row.has_flag ? 'var(--accent)' : 'transparent' }} />

        <div style={{ minWidth: 0 }}>
          <div
            style={{
              fontFamily: "'IBM Plex Sans', system-ui, sans-serif",
              fontSize: 12.5,
              fontWeight: 600,
              color: 'var(--ink)',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
            }}
          >
            {truncate(row.company, 22)}
          </div>
          <div style={{ fontSize: 10.5, letterSpacing: '.05em', color: 'var(--ink3)' }}>
            {row.ticker}
            {row.ppl_pct != null && (
              <span style={{ color: row.ppl_pct >= 0 ? 'var(--up)' : 'var(--down)' }}> {formatSignedPct(row.ppl_pct)}</span>
            )}
          </div>
        </div>

        <div style={{ position: 'relative', height: 8, background: 'var(--panel2)', borderRadius: 1 }}>
          <div
            style={{
              position: 'absolute',
              left: 0,
              top: 0,
              bottom: 0,
              width: `${weightBarPct}%`,
              background: 'var(--accent)',
              opacity: 0.85,
              borderRadius: 1,
            }}
          />
          {costDotPct != null && (
            <div
              style={{
                position: 'absolute',
                left: `${costDotPct}%`,
                top: '50%',
                width: 6,
                height: 6,
                borderRadius: '50%',
                border: '1px solid var(--ink2)',
                background: 'var(--panel)',
                transform: 'translate(-50%, -50%)',
              }}
            />
          )}
        </div>

        <span className="tabular-nums" style={{ textAlign: 'right', color: 'var(--ink)' }}>
          {row.weight_of_book_pct.toFixed(1)}%
        </span>

        <span className="tabular-nums" style={{ textAlign: 'right', color: row.price != null ? 'var(--ink)' : 'var(--ink3)' }}>
          {row.price != null ? row.price.toFixed(2) : <Dimmed />}
        </span>

        <span className="tabular-nums" style={{ textAlign: 'right', lineHeight: 1.25 }}>
          {row.today_vs_exp_pct != null ? (
            <>
              <span style={{ color: row.today_vs_exp_pct >= 0 ? 'var(--up)' : 'var(--down)', fontWeight: row.flag ? 600 : 400 }}>
                {formatSignedPct(row.today_vs_exp_pct)}
              </span>
              <span style={{ display: 'block', fontSize: 10, color: 'var(--ink3)' }}>exp {formatSignedPct(row.expected_pct ?? 0)}</span>
            </>
          ) : (
            <Dimmed />
          )}
        </span>

        <span className="tabular-nums" style={{ textAlign: 'right' }}>
          <Dimmed />
        </span>

        <span className="tabular-nums" style={{ textAlign: 'right' }}>
          <Dimmed />
        </span>

        <span style={{ textAlign: 'right', color: 'var(--ink3)' }}>{open ? '▾' : '▸'}</span>
      </div>

      {open && (
        <div className="ledger-drawer">
          {row.today_vs_exp_pct != null && <MoveExplain row={row} onOpenAnalysis={onOpenAnalysis} />}
          <div style={{ display: 'flex', gap: 24, flexWrap: 'wrap' }}>
            <div>
              <div style={{ fontSize: 10, letterSpacing: '.08em', textTransform: 'uppercase', color: 'var(--ink3)' }}>Weight</div>
              <div style={{ fontSize: 13, color: 'var(--ink)' }}>
                {row.weight_of_book_pct.toFixed(1)}%
                {row.cost_basis_of_book_pct != null && ` · cost basis ${row.cost_basis_of_book_pct.toFixed(1)}%`}
              </div>
            </div>
            {!row.is_cash && (
              <>
                <div>
                  <div style={{ fontSize: 10, letterSpacing: '.08em', textTransform: 'uppercase', color: 'var(--ink3)' }}>Value</div>
                  <div style={{ fontSize: 13, color: 'var(--ink)' }}>{formatGbp(row.value_gbp)}</div>
                </div>
                <div>
                  <div style={{ fontSize: 10, letterSpacing: '.08em', textTransform: 'uppercase', color: 'var(--ink3)' }}>P&amp;L</div>
                  <div style={{ fontSize: 13, color: (row.ppl_pct ?? 0) >= 0 ? 'var(--up)' : 'var(--down)' }}>
                    {row.ppl_gbp != null ? formatGbp(row.ppl_gbp) : '—'}
                    {row.ppl_pct != null && ` (${formatSignedPct(row.ppl_pct)})`}
                  </div>
                </div>
              </>
            )}
            <div>
              <div style={{ fontSize: 10, letterSpacing: '.08em', textTransform: 'uppercase', color: 'var(--ink3)' }}>
                Band, PE, sensitivities
              </div>
              <div style={{ fontSize: 13, color: 'var(--ink3)' }}>
                {row.is_cash ? '—' : row.modelled ? 'analysed, expected-move model not yet live' : 'no model yet'}
              </div>
            </div>
            {row.modelled && (
              <button
                onClick={() => onOpenAnalysis(instrumentTicker(row.ticker))}
                style={{
                  alignSelf: 'center',
                  marginLeft: 'auto',
                  padding: '6px 11px',
                  border: '1px solid var(--line2)',
                  background: 'transparent',
                  borderRadius: 3,
                  fontSize: 11.5,
                  color: 'var(--accent)',
                  cursor: 'pointer',
                }}
              >
                Open analysis ▸
              </button>
            )}
          </div>
        </div>
      )}
    </>
  )
}
