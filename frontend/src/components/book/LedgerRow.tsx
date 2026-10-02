import type { LedgerRow as LedgerRowType } from '../../types/book'
import { formatGbp, formatSignedPct, truncate } from '../../lib/format'

const WEIGHT_BAR_SCALE = 20 // bars are on a 0-20% scale; 20% weight = a full bar

interface Props {
  row: LedgerRowType
  open: boolean
  onToggle: () => void
}

function Dimmed() {
  return <span style={{ color: 'var(--ink3)' }}>—</span>
}

export function LedgerRow({ row, open, onToggle }: Props) {
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

        <span className="tabular-nums" style={{ textAlign: 'right' }}>
          <Dimmed />
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
          </div>
        </div>
      )}
    </>
  )
}
