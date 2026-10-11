import { useState } from 'react'
import { currencySymbol, fmt, peAt, signed } from '../../lib/modelRows'
import type { ModelOutputs, Price } from '../../types/analysis'

interface Props {
  outputs: ModelOutputs
  years: string[]
  price: Price | null
  epsCcy: string | undefined
  multiple: number
}

/** Implied price at the reference multiple, in the quote currency. */
const priceAt = (eps: number, mult: number, price: Price | null) => eps * mult * (price?.fx ?? 1)

/** PE input; blank or invalid entries are ignored until they parse. */
export function PeControl({ value, current, onChange }: { value: number; current: number | null; onChange: (pe: number | null) => void }) {
  const [text, setText] = useState(value.toFixed(1))
  const [prev, setPrev] = useState(value)
  if (value !== prev) {
    setPrev(value)
    setText(value.toFixed(1))
  }
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
      <label className="an-micro" htmlFor="pe-input">PE</label>
      <input
        id="pe-input"
        className="an-select"
        type="number"
        min={1}
        step={0.5}
        value={text}
        onChange={(e) => {
          setText(e.target.value)
          const v = Number(e.target.value)
          if (v > 0) {
            setPrev(v) // typed here, so don't reformat what's being typed
            onChange(v)
          }
        }}
        onWheel={(e) => e.currentTarget.blur()} // page scroll mustn't nudge the PE
        style={{ width: 72, textAlign: 'right' }}
      />
      <span>×</span>
      {current != null && Math.abs(value - current) > 0.05 && (
        <button className="an-btn" onClick={() => onChange(null)}>Reset to {current.toFixed(1)}×</button>
      )}
    </div>
  )
}

/* ---------------- shared chart frame ---------------- */

const W = 900, H = 260
const PAD = { l: 56, r: 24, t: 26, b: 34 }

function niceStep(raw: number) {
  const p = 10 ** Math.floor(Math.log10(raw || 1))
  const n = raw / p
  return (n <= 1 ? 1 : n <= 2 ? 2 : n <= 5 ? 5 : 10) * p
}

/** Line across the forecast years with a callout per point, on an axis from 0; optional reference line. */
function YearLine({ years, values, callout, tick, aria, refLine }: {
  years: string[]
  values: (number | null)[]
  callout: (v: number) => { text: string; color?: string }
  tick: (v: number) => string
  aria: string
  refLine?: { value: number; label: string }
}) {
  const known = values.filter((v): v is number => v != null)
  const hi = Math.max(0, ...known, refLine?.value ?? 0) || 1
  const step = niceStep(hi / 4)
  const top = Math.ceil((hi * 1.15) / step) * step
  const y = (v: number) => PAD.t + (1 - v / top) * (H - PAD.t - PAD.b)
  const ticks = Array.from({ length: Math.round(top / step) + 1 }, (_, i) => i * step)
  const x = (i: number) => PAD.l + (years.length === 1 ? 0.5 : i / (years.length - 1)) * (W - PAD.l - PAD.r)
  const pts = values.map((v, i) => (v == null ? null : ([x(i), y(v)] as const)))
  const path = pts
    .filter((p) => p != null)
    .map((p, i) => `${i ? 'L' : 'M'}${p[0].toFixed(1)},${p[1].toFixed(1)}`)
    .join(' ')
  const anchor = (i: number) => (i === 0 ? 'start' : i === years.length - 1 ? 'end' : 'middle')

  return (
    <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={aria} style={{ width: '100%', height: 'auto', display: 'block' }}>
      {ticks.map((t) => (
        <g key={t}>
          <line x1={PAD.l} x2={W - PAD.r} y1={y(t)} y2={y(t)} stroke="var(--line)" strokeWidth={1} />
          <text x={PAD.l - 8} y={y(t) + 4} textAnchor="end" fontSize={11} fill="var(--ink3)">{tick(t)}</text>
        </g>
      ))}
      {years.map((yr, i) => (
        <text key={yr} x={x(i)} y={H - 10} textAnchor={anchor(i)} fontSize={11} fill="var(--ink3)">{yr}</text>
      ))}
      {refLine && (
        <g>
          <line x1={PAD.l} x2={W - PAD.r} y1={y(refLine.value)} y2={y(refLine.value)} stroke="var(--accent)" strokeWidth={1.5} strokeDasharray="5 4" />
          <text x={W - PAD.r} y={y(refLine.value) + 15} textAnchor="end" fontSize={11} fontWeight={600} fill="var(--accent)">{refLine.label}</text>
        </g>
      )}
      <path d={path} fill="none" stroke="var(--ink2)" strokeWidth={2} />
      {pts.map((p, i) => {
        if (!p) return null
        const c = callout(values[i] as number)
        return (
          <g key={years[i]}>
            <circle cx={p[0]} cy={p[1]} r={4} fill="var(--panel)" stroke="var(--ink2)" strokeWidth={2} />
            <text x={p[0]} y={p[1] - 11} textAnchor={anchor(i)} fontSize={12} fontWeight={600} fill={c.color ?? 'var(--ink)'}>{c.text}</text>
          </g>
        )
      })}
    </svg>
  )
}

/* ---------------- PE at current price ---------------- */

export function PeChart({ outputs, years, price }: Omit<Props, 'multiple' | 'epsCcy'>) {
  const values = outputs.scenarios.bau.map((r) => peAt(r.eps, price))
  return (
    <YearLine
      years={years}
      values={values}
      callout={(v) => ({ text: `${fmt(v, 1)}×` })}
      tick={(v) => `${v.toFixed(0)}×`}
      aria="PE at the current price on BAU EPS, by forecast year"
    />
  )
}

/* ---------------- implied share price at a chosen PE ---------------- */

export function UpsideChart({ outputs, years, price, multiple }: Omit<Props, 'epsCcy'>) {
  const sym = currencySymbol(price?.currency)
  const values = outputs.scenarios.bau.map((r) => (price ? priceAt(r.eps, multiple, price) : null))
  return (
    <YearLine
      years={years}
      values={values}
      callout={(v) => {
        const pct = price ? (v / price.close - 1) * 100 : 0
        return { text: `${signed(pct, 1)}%`, color: pct > 0.05 ? 'var(--up)' : pct < -0.05 ? 'var(--down)' : 'var(--ink2)' }
      }}
      tick={(v) => `${sym}${v.toFixed(0)}`}
      aria={`Implied share price at ${fmt(multiple, 1)}x BAU EPS, by forecast year, against the current price`}
      refLine={price ? { value: price.close, label: `now ${sym}${price.close.toFixed(2)}` } : undefined}
    />
  )
}
