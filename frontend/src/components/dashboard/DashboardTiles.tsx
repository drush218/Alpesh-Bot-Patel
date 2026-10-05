import { useEffect, useState, type ReactNode } from 'react'
import { fetchDashboard } from '../../lib/apiClient'
import { formatGbp } from '../../lib/format'
import { currencySymbol } from '../../lib/modelRows'
import { Chip } from '../common/Chip'
import type { DashboardData } from '../../types/dashboard'
import type { Verdict } from '../../types/macro'
import type { Screen } from '../layout/Header'

const RAMP = [100, 66, 46, 32, 22, 14, 10]
const swatch = (i: number) => `color-mix(in srgb, var(--accent) ${RAMP[i] ?? 10}%, var(--panel2))`
const signedPct = (x: number | null | undefined, d = 1) => (x == null ? '—' : `${x > 0 ? '+' : x < 0 ? '−' : '±'}${Math.abs(x).toFixed(d)}%`)
const tone = (x: number | null | undefined) => (x == null || x === 0 ? 'var(--ink3)' : x > 0 ? 'var(--up)' : 'var(--down)')
const daysAway = (iso: string) => Math.round((new Date(`${iso}T00:00:00`).getTime() - new Date(new Date().toDateString()).getTime()) / 86400000)
const fmtDay = (iso: string) => new Date(`${iso}T00:00:00`).toLocaleDateString('en-GB', { day: '2-digit', month: 'short' })
const vTone = (v: Verdict) => (v.includes('headwind') ? 'down' : v.includes('tailwind') ? 'up' : 'neutral') as 'up' | 'down' | 'neutral'

function Tile({ name, badge, onClick, children }: { name: string; badge?: ReactNode; onClick?: () => void; children: ReactNode }) {
  return (
    <article
      onClick={onClick}
      className={onClick ? 'dash-tile clickable' : 'dash-tile'}
      style={{ display: 'flex', flexDirection: 'column', border: '1px solid var(--line)', background: 'var(--panel)', borderRadius: 4, padding: '15px 16px 14px', boxShadow: 'var(--shadow)', cursor: onClick ? 'pointer' : 'default', minWidth: 0 }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 8, marginBottom: 12 }}>
        <span style={{ fontSize: 10, letterSpacing: '.11em', textTransform: 'uppercase', color: 'var(--ink3)' }}>{name}</span>
        {badge}
      </div>
      {children}
    </article>
  )
}

function Stat({ label, value, color }: { label: string; value: ReactNode; color?: string }) {
  return (
    <div>
      <div className="an-micro">{label}</div>
      <div style={{ fontSize: 12.5, color: color ?? 'var(--ink)' }}>{value}</div>
    </div>
  )
}

function readMultiple() {
  try {
    const v = Number(localStorage.getItem('pt.referenceMultiple'))
    return [25, 30, 35, 40].includes(v) ? v : 30
  } catch {
    return 30
  }
}

export function DashboardTiles({ onNavigate, onOpenAnalysis }: { onNavigate: (s: Screen) => void; onOpenAnalysis: (t: string) => void }) {
  const [d, setD] = useState<DashboardData | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchDashboard()
      .then((r) => (r.error ? setError(r.error) : setD(r)))
      .catch((e) => setError(e.message))
  }, [])

  if (error) return <p style={{ color: 'var(--down)' }}>{error}</p>
  if (!d) return <p className="an-sub">Loading tiles… (prices, index levels and earnings dates from Yahoo)</p>

  const b = d.book
  const unexplained = b.flags.filter((f) => f.category === 'unexplained')
  const a = d.analysis
  const mult = readMultiple()
  const low = a?.eps_low != null ? a.eps_low * mult * (a.fx ?? 1) : null
  const high = a?.eps_high != null ? a.eps_high * mult * (a.fx ?? 1) : null
  const pos = a?.price != null && low != null && high != null && high > low ? Math.max(0, Math.min(1, (a.price - low) / (high - low))) : null
  const sym = currencySymbol(a?.currency ?? undefined)
  const top = d.indices.rows[0]
  const maxMove = Math.max(...d.macro.factors.map((f) => Math.abs(f.change)), 1e-9)

  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: 14 }}>
      <Tile
        name="Book"
        onClick={() => onNavigate('book')}
        badge={unexplained.length ? <Chip tone="down" strength="half">{unexplained.length} unexplained</Chip> : <span className="an-sub">no unexplained moves</span>}
      >
        <div style={{ display: 'flex', alignItems: 'baseline', gap: 10, flexWrap: 'wrap' }}>
          <span style={{ fontSize: 23, fontWeight: 600, letterSpacing: '-.015em', color: tone(b.day_pnl_gbp) }}>
            {b.day_pnl_gbp >= 0 ? '+' : '−'}{formatGbp(Math.abs(b.day_pnl_gbp))}
          </span>
          <span className="an-sub">day · {signedPct(b.day_pct, 2)}</span>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 10, margin: '12px 0', paddingBottom: 12, borderBottom: '1px solid var(--line)' }}>
          <Stat label="best" value={b.best ? <>{b.best.ticker} {signedPct(b.best.day_pct)}</> : '—'} color={tone(b.best?.day_pct)} />
          <Stat label="worst" value={b.worst ? <>{b.worst.ticker} {signedPct(b.worst.day_pct)}</> : '—'} color={tone(b.worst?.day_pct)} />
          <Stat label="breadth" value={`${b.up} up / ${b.down} dn`} />
        </div>
        {b.flags.length > 0 && (
          <div style={{ display: 'grid', gap: 5, marginBottom: 10 }}>
            <span style={{ fontSize: 11, color: 'var(--accent)' }}>{unexplained.length} unexplained{b.flags.length > unexplained.length ? ` · ${b.flags.length - unexplained.length} on results` : ''}</span>
            {b.flags.map((f) => (
              <div key={f.ticker} style={{ display: 'grid', gridTemplateColumns: '54px 1fr auto', gap: 8, fontSize: 12, color: tone(f.actual_pct) }}>
                <b style={{ fontWeight: 600 }}>{f.ticker}</b>
                <span>
                  {signedPct(f.actual_pct)} <span className="an-sub">exp {signedPct(f.expected_pct)}</span>
                  {f.category === 'earnings' ? <span className="an-sub"> · results</span> : !f.modelled && <span style={{ color: 'var(--accent)' }}> · run an analysis</span>}
                </span>
                <span>z {f.z.toFixed(1)}</span>
              </div>
            ))}
          </div>
        )}
        <span className="an-sub" style={{ marginTop: 'auto' }}>
          {b.priced} of {b.holdings} priced · day move in local currency, FX excluded
        </span>
      </Tile>

      <Tile
        name="Macro"
        onClick={() => onNavigate('macro')}
        badge={d.macro.tilt.verdict ? <Chip tone={vTone(d.macro.tilt.verdict)} strength="half">book {d.macro.tilt.verdict}</Chip> : undefined}
      >
        <div style={{ display: 'grid', gap: 8 }}>
          {d.macro.factors.map((f) => {
            const w = (Math.abs(f.change) / maxMove) * 50
            const color = f.move === 'up' ? 'var(--accent)' : f.move === 'down' ? 'var(--ink2)' : 'var(--ink3)'
            return (
              <div key={f.code} style={{ display: 'grid', gridTemplateColumns: '120px 1fr 64px', gap: 10, alignItems: 'center', fontSize: 11.5 }}>
                <span style={{ color: 'var(--ink2)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{f.name}</span>
                <div style={{ position: 'relative', height: 8, background: 'var(--panel2)', borderRadius: 1 }}>
                  <div style={{ position: 'absolute', top: 0, bottom: 0, background: color, borderRadius: 1, left: f.change >= 0 ? '50%' : `${50 - w}%`, width: `${w}%` }} />
                </div>
                <span style={{ textAlign: 'right' }}>
                  {f.change > 0 ? '+' : f.change < 0 ? '−' : '±'}{Math.abs(f.change).toFixed(f.unit === 'pp' ? 2 : 1)}{f.unit}
                </span>
              </div>
            )
          })}
        </div>
        <div style={{ marginTop: 'auto', paddingTop: 12, borderTop: '1px solid var(--line)', marginBlockStart: 12 }}>
          <div className="an-micro" style={{ marginBottom: 6 }}>most affected</div>
          {d.macro.most_affected.length === 0 ? (
            <span className="an-sub">No modelled holdings exposed.</span>
          ) : (
            d.macro.most_affected.map((h) => (
              <div key={h.ticker} style={{ display: 'flex', justifyContent: 'space-between', gap: 8, fontSize: 12, alignItems: 'center' }}>
                <span><b style={{ fontWeight: 600 }}>{h.ticker}</b> <span className="an-sub">{h.weight_pct?.toFixed(1)}%</span></span>
                {h.verdict && <Chip tone={vTone(h.verdict)} strength="half">{h.verdict}</Chip>}
              </div>
            ))
          )}
          <span className="an-sub">{d.macro.tilt.modelled} of {d.macro.tilt.total} holdings modelled</span>
        </div>
      </Tile>

      {a && (
        <Tile
          name={`Analysis · ${a.ticker}`}
          onClick={() => onOpenAnalysis(a.ticker)}
          badge={a.is_stale ? <Chip tone="neutral" strength="half"><span style={{ color: 'var(--accent)' }}>stale {a.last_earnings ? `since ${fmtDay(a.last_earnings)}` : ''}</span></Chip> : undefined}
        >
          <div style={{ display: 'flex', alignItems: 'baseline', gap: 10, flexWrap: 'wrap' }}>
            <span style={{ fontSize: 23, fontWeight: 600, letterSpacing: '-.015em' }}>{a.price != null ? `${sym}${a.price.toFixed(2)}` : '—'}</span>
            {a.price != null && a.reference_price && (
              <span style={{ fontSize: 11.5, color: tone(a.price - a.reference_price) }}>{signedPct((a.price / a.reference_price - 1) * 100)} since strike</span>
            )}
          </div>
          {pos != null && (
            <div style={{ margin: '14px 0 6px' }}>
              <div style={{ position: 'relative', height: 20, background: 'var(--panel2)', borderRadius: 2 }}>
                <div style={{ position: 'absolute', inset: 0, background: 'var(--bandLow)', borderRadius: 2 }} />
                <div style={{ position: 'absolute', top: -2, bottom: -2, width: 2, background: 'var(--accent)', left: `calc(${(pos * 100).toFixed(1)}% - 1px)` }} />
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10.5, color: 'var(--ink3)', marginTop: 4 }}>
                <span>LOW {sym}{low!.toFixed(2)}</span>
                <span>{a.price! > high! ? 'above HIGH' : a.price! < low! ? 'below LOW' : `${Math.round(pos * 100)}% of range`}</span>
                <span>HIGH {sym}{high!.toFixed(2)}</span>
              </div>
            </div>
          )}
          <div style={{ marginTop: 'auto', paddingTop: 10, borderTop: '1px solid var(--line)', display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 10 }}>
            <Stat label="struck" value={a.data_as_of ? fmtDay(a.data_as_of) : '—'} />
            <Stat label="band" value={`${a.year} at ${mult}×`} />
            <Stat label="analyses" value={a.count} />
          </div>
        </Tile>
      )}

      <Tile
        name="Indices"
        onClick={() => onNavigate('book')}
        badge={top ? <Chip tone={top.over_limit ? 'down' : 'neutral'} strength={top.over_limit ? 'half' : 'neutral'}>{top.code} {top.share_of_invested_pct.toFixed(0)}% of invested</Chip> : undefined}
      >
        <div style={{ display: 'grid', gridTemplateColumns: '8px 1fr 62px 52px 52px', gap: 11, fontSize: 10, letterSpacing: '.09em', textTransform: 'uppercase', color: 'var(--ink3)', paddingBottom: 6, borderBottom: '1px solid var(--line)' }}>
          <span /><span>index</span><span style={{ textAlign: 'right' }}>level</span><span style={{ textAlign: 'right' }}>day</span><span style={{ textAlign: 'right' }}>you</span>
        </div>
        {d.indices.rows.map((r, i) => (
          <div key={r.code} style={{ display: 'grid', gridTemplateColumns: '8px 1fr 62px 52px 52px', gap: 11, fontSize: 12, padding: '5px 0', alignItems: 'center' }}>
            <span style={{ width: 8, height: 8, borderRadius: 2, background: swatch(i) }} />
            <span>{r.name}</span>
            <span style={{ textAlign: 'right' }}>{r.level != null ? r.level.toLocaleString('en-GB', { maximumFractionDigits: 0 }) : '—'}</span>
            <span style={{ textAlign: 'right', color: tone(r.day_pct) }}>{signedPct(r.day_pct)}</span>
            <span style={{ textAlign: 'right', fontWeight: 600 }}>{r.weight_pct.toFixed(1)}%</span>
          </div>
        ))}
        <div style={{ marginTop: 'auto', paddingTop: 10 }}>
          <div style={{ display: 'flex', gap: 1, height: 9 }}>
            {d.indices.rows.map((r, i) => <div key={r.code} title={`${r.name} ${r.weight_pct.toFixed(1)}%`} style={{ flex: r.weight_pct, background: swatch(i) }} />)}
            {d.indices.unmapped_pct > 0 && <div title={`no index ${d.indices.unmapped_pct.toFixed(1)}%`} style={{ flex: d.indices.unmapped_pct, background: 'var(--ink3)', opacity: 0.4 }} />}
            <div title={`cash ${d.indices.cash_pct.toFixed(1)}%`} style={{ flex: d.indices.cash_pct, background: 'var(--line)' }} />
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10.5, color: 'var(--ink3)', marginTop: 4 }}>
            <span>book by index</span>
            <span>{d.indices.cash_pct.toFixed(1)}% cash</span>
          </div>
        </div>
      </Tile>

      <Tile name="Calendar" badge={<span className="an-sub">next 30d</span>}>
        <div style={{ display: 'grid', gap: 5 }}>
          {d.calendar.earnings.length === 0 && d.calendar.later.length === 0 && <span className="an-sub">No earnings dates found.</span>}
          {d.calendar.earnings.length === 0 && d.calendar.later.length > 0 && <span className="an-sub">Nothing in 30 days. Next:</span>}
          {(d.calendar.earnings.length ? d.calendar.earnings : d.calendar.later).map((e) => (
            <div key={e.ticker + e.date} style={{ display: 'grid', gridTemplateColumns: '60px 1fr 60px 52px', gap: 10, fontSize: 12 }}>
              <b style={{ fontWeight: 600 }}>{e.ticker}</b>
              <span style={{ color: 'var(--ink2)' }}>results</span>
              <span style={{ textAlign: 'right' }}>{fmtDay(e.date)}</span>
              <span style={{ textAlign: 'right', color: 'var(--ink3)' }}>{daysAway(e.date)}d</span>
            </div>
          ))}
        </div>
        <div style={{ marginTop: 'auto', paddingTop: 12, borderTop: '1px solid var(--line)', marginBlockStart: 12 }}>
          <div className="an-micro" style={{ marginBottom: 6 }}>dividend income</div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 10 }}>
            <Stat label="run-rate" value={`${formatGbp(d.calendar.dividend_run_rate_gbp)} / yr`} />
            <Stat label="yield on book" value={d.calendar.yield_on_book_pct != null ? `${d.calendar.yield_on_book_pct.toFixed(2)}%` : '—'} />
            <Stat label="received YTD" value={<span style={{ color: 'var(--ink3)' }}>not tracked</span>} />
          </div>
          <span className="an-sub">run-rate = last 12 months paid per share × shares held</span>
        </div>
      </Tile>
    </div>
  )
}
