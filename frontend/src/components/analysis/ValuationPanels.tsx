import { useState } from 'react'
import { currencySymbol, fmt, peAt } from '../../lib/modelRows'
import type { ModelOutputs, Price } from '../../types/analysis'

export const MULTIPLES = [25, 30, 35, 40] as const

interface Props {
  outputs: ModelOutputs
  years: string[]
  price: Price | null
  epsCcy: string | undefined
  multiple: number
}

/** Implied price at the reference multiple, in the quote currency. */
const priceAt = (eps: number, mult: number, price: Price | null) => eps * mult * (price?.fx ?? 1)

export function MultipleControl({ value, onChange }: { value: number; onChange: (m: number) => void }) {
  return (
    <div role="group" aria-label="Reference multiple" style={{ display: 'flex', border: '1px solid var(--line2)', borderRadius: 3, overflow: 'hidden' }}>
      {MULTIPLES.map((m) => (
        <button
          key={m}
          onClick={() => onChange(m)}
          style={{
            border: 0,
            padding: '5px 11px',
            fontSize: 11.5,
            letterSpacing: '.05em',
            cursor: 'pointer',
            background: m === value ? 'var(--accent)' : 'transparent',
            color: m === value ? 'var(--bg)' : 'var(--ink2)',
            fontWeight: m === value ? 600 : 400,
          }}
        >
          {m}×
        </button>
      ))}
    </div>
  )
}

/* ---------------- price vs scenario band ---------------- */

const W = 900, H = 320
const PAD = { l: 52, r: 96, t: 18, b: 34 }

export function ScenarioBandChart({ outputs, years, price, multiple }: Props) {
  const sym = currencySymbol(price?.currency)
  const series = (k: 'low' | 'bau' | 'high') => outputs.scenarios[k].map((r) => priceAt(r.eps, multiple, price))
  const low = series('low'), bau = series('bau'), high = series('high')
  const now = price?.close ?? null
  const top = Math.max(...high, now ?? 0) * 1.12
  const x = (i: number) => PAD.l + (years.length === 1 ? 0 : (i / (years.length - 1)) * (W - PAD.l - PAD.r))
  const y = (v: number) => PAD.t + (1 - v / top) * (H - PAD.t - PAD.b)
  const step = niceStep(top / 4)
  const ticks = Array.from({ length: Math.floor(top / step) + 1 }, (_, i) => i * step)
  const line = (vals: number[]) => vals.map((v, i) => `${i ? 'L' : 'M'}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(' ')
  const band = `${line(high)} ${[...low].reverse().map((v, j) => `L${x(low.length - 1 - j).toFixed(1)},${y(v).toFixed(1)}`).join(' ')} Z`
  const last = years.length - 1

  return (
    <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`Implied price at ${multiple}x EPS by scenario, against the current price`} style={{ width: '100%', height: 'auto', display: 'block' }}>
      {ticks.map((t) => (
        <g key={t}>
          <line x1={PAD.l} x2={W - PAD.r} y1={y(t)} y2={y(t)} stroke="var(--line)" strokeWidth={1} />
          <text x={PAD.l - 8} y={y(t) + 4} textAnchor="end" fontSize={11} fill="var(--ink3)">{sym}{t.toFixed(0)}</text>
        </g>
      ))}
      {years.map((yr, i) => (
        <text key={yr} x={x(i)} y={H - 10} textAnchor="middle" fontSize={11} fill="var(--ink3)">{yr}</text>
      ))}
      <path d={band} fill="var(--bandLow)" stroke="none" />
      <path d={line(high)} fill="none" stroke="var(--up)" strokeWidth={1.5} strokeDasharray="5 4" />
      <path d={line(low)} fill="none" stroke="var(--ink3)" strokeWidth={1.5} strokeDasharray="5 4" />
      <path d={line(bau)} fill="none" stroke="var(--ink2)" strokeWidth={1.5} />
      {[['HIGH', high, 'var(--up)'], ['BAU', bau, 'var(--ink2)'], ['LOW', low, 'var(--ink3)']].map(([label, vals, color]) => (
        <text key={label as string} x={x(last) + 8} y={y((vals as number[])[last]) + 4} fontSize={11} fill={color as string}>
          {label as string} {sym}{(vals as number[])[last].toFixed(0)}
        </text>
      ))}
      {now != null && (
        <g>
          <line x1={PAD.l} x2={W - PAD.r} y1={y(now)} y2={y(now)} stroke="var(--accent)" strokeWidth={2} />
          <rect x={PAD.l + 6} y={y(now) - 20} width={88} height={16} rx={2} fill="var(--accent)" />
          <text x={PAD.l + 50} y={y(now) - 8} textAnchor="middle" fontSize={11} fontWeight={600} fill="var(--bg)">now {sym}{now.toFixed(2)}</text>
        </g>
      )}
    </svg>
  )
}

function niceStep(raw: number) {
  const p = 10 ** Math.floor(Math.log10(raw || 1))
  const n = raw / p
  return (n <= 1 ? 1 : n <= 2 ? 2 : n <= 5 ? 5 : 10) * p
}

/* ---------------- live valuation ---------------- */

export function LiveValuation({ outputs, years, price, epsCcy, multiple }: Props) {
  const sym = currencySymbol(epsCcy)
  const psym = currencySymbol(price?.currency)
  const bau = outputs.scenarios.bau
  const row = (label: string, cells: (string | null)[], note?: string, strong?: boolean) => (
    <tr className={strong ? 'pe' : undefined}>
      <td className="lbl">{label}{note && <span className="u">{note}</span>}</td>
      {cells.map((c, i) => <td key={years[i]}><span className="v">{c ?? '—'}</span></td>)}
    </tr>
  )
  return (
    <div className="an-scroll">
      <table className="an-table an-out" aria-label="Live valuation">
        <thead>
          <tr><th />{years.map((y) => <th key={y}>{y}</th>)}</tr>
        </thead>
        <tbody>
          {row('EPS modelled', bau.map((r) => `${sym}${fmt(r.eps, 2)}`), 'BAU')}
          {row('Macro adjustment', bau.map(() => null), 'not live yet')}
          {row(`PE at ${psym}${price ? price.close.toFixed(2) : '—'}`, bau.map((r) => fmt(peAt(r.eps, price), 1) + '×'), 'current price', true)}
          {row(`Price at ${multiple}×`, bau.map((r) => `${psym}${fmt(priceAt(r.eps, multiple, price), 2)}`), 'BAU')}
          {row(
            `Range at ${multiple}×`,
            years.map((_, i) => `${psym}${fmt(priceAt(outputs.scenarios.low[i].eps, multiple, price), 0)}–${fmt(priceAt(outputs.scenarios.high[i].eps, multiple, price), 0)}`),
            'LOW–HIGH',
          )}
        </tbody>
      </table>
    </div>
  )
}

/* ---------------- BAU bridge ---------------- */

export function BauBridge({ outputs, years, epsCcy }: Omit<Props, 'price' | 'multiple'>) {
  const [open, setOpen] = useState(false)
  const bau = outputs.scenarios.bau
  const sym = currencySymbol(epsCcy)
  const lines: [string, (i: number) => string, boolean?][] = [
    ['Revenue', (i) => fmt(bau[i].revenue, 0), true],
    ['Operating costs', (i) => fmt(-(bau[i].revenue - bau[i].operating_income), 0)],
    ['Operating income', (i) => fmt(bau[i].operating_income, 0), true],
    ['Net interest & other', (i) => fmt(bau[i].pretax - bau[i].operating_income, 0)],
    ['Pre-tax income', (i) => fmt(bau[i].pretax, 0), true],
    ['Tax', (i) => fmt(-bau[i].tax, 0)],
    ['Net income', (i) => fmt(bau[i].net_income, 0), true],
    ['Diluted shares (m)', (i) => fmt(bau[i].shares_diluted, 1)],
    [`EPS ${sym}`, (i) => fmt(bau[i].eps, 2), true],
  ]
  return (
    <section className="an-card">
      <button
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        style={{ background: 'transparent', border: 0, padding: 0, cursor: 'pointer', display: 'flex', gap: 8, alignItems: 'baseline', color: 'var(--ink)' }}
      >
        <span style={{ color: 'var(--accent)' }}>{open ? '▾' : '▸'}</span>
        <h2>BAU bridge</h2>
        <span className="an-sub">revenue → EPS, {sym}m</span>
      </button>
      {open && (
        <div className="an-scroll" style={{ marginTop: 12 }}>
          <table className="an-table" aria-label="BAU bridge">
            <thead><tr><th />{years.map((y) => <th key={y}>{y}</th>)}</tr></thead>
            <tbody>
              {lines.map(([label, f, strong]) => (
                <tr key={label}>
                  <td className="lbl" style={strong ? { color: 'var(--ink)', fontWeight: 600 } : undefined}>{label}</td>
                  {years.map((y, i) => <td key={y} style={strong ? { fontWeight: 600 } : { color: 'var(--ink2)' }}>{f(i)}</td>)}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}
