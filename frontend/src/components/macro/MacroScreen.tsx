import { useEffect, useState } from 'react'
import { fetchMacro } from '../../lib/apiClient'
import { Chip } from '../common/Chip'
import { SegmentedControl } from '../common/SegmentedControl'
import type { MacroFactor, MacroHolding, MacroView, Verdict } from '../../types/macro'

type Mode = 'list' | 'matrix'
const MODE_KEY = 'pt.macroMode'
const FACTOR_KEY = 'pt.macroFactor'
const sans = { fontFamily: "'IBM Plex Sans', system-ui, sans-serif" } as const

const read = (k: string, fallback: string) => {
  try {
    return localStorage.getItem(k) ?? fallback
  } catch {
    return fallback
  }
}
const write = (k: string, v: string) => {
  try {
    localStorage.setItem(k, v)
  } catch {
    /* per-browser convenience only */
  }
}

function verdictOf(score: number): Verdict {
  if (score <= -3) return 'strong headwind'
  if (score <= -1) return 'headwind'
  if (score < 1) return 'neutral'
  if (score < 3) return 'tailwind'
  return 'strong tailwind'
}
const toneOf = (v: Verdict) => (v.includes('headwind') ? 'down' : v.includes('tailwind') ? 'up' : 'neutral') as 'up' | 'down' | 'neutral'
const cssTone = (v: Verdict) => ({ up: 'var(--up)', down: 'var(--down)', neutral: 'var(--line)' })[toneOf(v)]

function VerdictChip({ v }: { v: Verdict }) {
  return <Chip tone={toneOf(v)} strength={v.startsWith('strong') ? 'full' : v === 'neutral' ? 'neutral' : 'half'}>{v}</Chip>
}

function Sparkline({ values, move }: { values: number[]; move: MacroFactor['move'] }) {
  if (values.length < 2) return <div style={{ height: 30 }} />
  const min = Math.min(...values), max = Math.max(...values)
  const span = max - min || 1
  const pts = values.map((v, i) => `${((i / (values.length - 1)) * 100).toFixed(2)},${(28 - ((v - min) / span) * 26).toFixed(2)}`).join(' ')
  const color = move === 'up' ? 'var(--accent)' : move === 'down' ? 'var(--ink2)' : 'var(--ink3)'
  return (
    <svg viewBox="0 0 100 30" preserveAspectRatio="none" style={{ width: '100%', height: 30, display: 'block' }} aria-hidden="true">
      <polyline points={pts} fill="none" stroke={color} strokeWidth={1.5} vectorEffect="non-scaling-stroke" />
    </svg>
  )
}

function FactorCard({ f, selected, onSelect }: { f: MacroFactor; selected: boolean; onSelect: () => void }) {
  const arrow = f.move === 'up' ? '↑' : f.move === 'down' ? '↓' : '→'
  const change = f.change == null ? null : `${f.change > 0 ? '+' : f.change < 0 ? '−' : '±'}${Math.abs(f.change).toFixed(f.unit === 'pp' ? 2 : 1)}${f.unit}`
  return (
    <button
      onClick={onSelect}
      disabled={!f.used}
      style={{
        textAlign: 'left',
        border: `1px solid ${selected ? 'var(--accent)' : 'var(--line)'}`,
        background: 'var(--panel)',
        borderRadius: 4,
        padding: '13px 14px 11px',
        cursor: f.used ? 'pointer' : 'default',
        display: 'flex',
        flexDirection: 'column',
        gap: 4,
        color: 'var(--ink)',
        boxShadow: 'var(--shadow)',
        opacity: f.used ? 1 : 0.75,
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8 }}>
        <span className="an-micro">{f.name}</span>
        <span style={{ color: f.move === 'up' ? 'var(--accent)' : 'var(--ink3)' }}>{arrow}</span>
      </div>
      <span style={{ fontSize: 12, color: 'var(--ink2)' }}>{f.series ? f.state : 'No data source set'}</span>
      <Sparkline values={f.spark} move={f.move} />
      <span style={{ fontSize: 12 }}>
        {f.value != null ? <b style={{ fontWeight: 600 }}>{f.value.toLocaleString('en-GB', { maximumFractionDigits: 2 })}</b> : '—'}
        {change && <span className="an-sub"> · 1m {change}</span>}
      </span>
      <span className="an-sub" style={{ borderTop: '1px solid var(--line)', paddingTop: 6, marginTop: 2 }}>
        {f.used ? `${f.affected} holding${f.affected === 1 ? '' : 's'} affected` : 'no analysis uses this'}
        {f.as_of && ` · ${f.as_of}`}
        {f.series && ` · ${f.series}`}
      </span>
    </button>
  )
}

function topLink(h: MacroHolding, factor: string) {
  const ls = factor === 'ALL' ? h.links : h.links.filter((l) => l.factor === factor)
  return [...ls].sort((a, b) => Math.abs(b.score) - Math.abs(a.score))[0]
}

function HoldingRow({ h, factor, names, open, onToggle }: { h: MacroHolding; factor: string; names: Record<string, string>; open: boolean; onToggle: () => void }) {
  const score = factor === 'ALL' ? h.score : h.factor_scores[factor] ?? null
  const v = score == null ? null : verdictOf(score)
  const link = topLink(h, factor)
  const strong = v?.startsWith('strong')
  return (
    <>
      <div className={`macro-row${open ? ' open' : ''}`} onClick={onToggle}>
        <span style={{ alignSelf: 'stretch', background: v && v !== 'neutral' ? `color-mix(in srgb, ${cssTone(v)} ${strong ? 85 : 45}%, transparent)` : 'var(--line)' }} />
        <div style={{ minWidth: 0 }}>
          <div style={{ ...sans, fontSize: 12.5, fontWeight: 600, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{h.company ?? h.ticker}</div>
          <div style={{ fontSize: 10.5, color: 'var(--ink3)', letterSpacing: '.05em' }}>
            {h.ticker}{h.weight_pct != null && ` · ${h.weight_pct.toFixed(1)}% of book`}
          </div>
        </div>
        <span>{v ? <VerdictChip v={v} /> : <span className="an-sub">{h.modelled ? 'not exposed' : 'no analysis'}</span>}</span>
        <span style={{ ...sans, fontSize: 11.5, color: 'var(--ink2)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {link?.ref ?? (h.modelled ? '' : 'add an analysis to score this holding')}
        </span>
        <span style={{ color: 'var(--ink3)', textAlign: 'right' }}>{open ? '▾' : '▸'}</span>
      </div>
      {open && (
        <div className="ledger-drawer">
          <div className="an-micro" style={{ marginBottom: 6 }}>factor by factor</div>
          {h.links.length === 0 && <p style={{ margin: 0 }}>No macro links on file for {h.ticker}.</p>}
          <div style={{ display: 'grid', gap: 6 }}>
            {h.links.map((l) => (
              <div key={l.factor + l.channel} style={{ display: 'grid', gridTemplateColumns: '170px 132px minmax(0,1fr)', gap: 12, alignItems: 'center' }}>
                <span style={{ color: 'var(--ink)' }}>
                  {names[l.factor] ?? l.factor} <span className="an-sub">{l.channel}</span>
                </span>
                <span>
                  <VerdictChip v={verdictOf(l.score)} />
                </span>
                <span style={{ ...sans, color: 'var(--ink2)' }}>
                  {l.ref} <span className="an-sub">· {l.strength} {l.direction} · factor {l.move ?? 'no data'}</span>
                </span>
              </div>
            ))}
          </div>
          <p style={{ margin: '10px 0 0', fontSize: 10.5 }}>
            {h.modelled ? `From the current ${h.ticker} analysis, crossed with each factor's 1-month move.` : 'No analysis on file, so no factor effects (no sector prior yet).'}
          </p>
        </div>
      )}
    </>
  )
}

const MARK = (s: number | undefined) => (s == null ? '' : s <= -2 ? '−−' : s < 0 ? '−' : s === 0 ? '·' : s < 2 ? '+' : '++')

function Matrix({ view, names, open, onToggle }: { view: MacroView; names: Record<string, string>; open: string | null; onToggle: (t: string) => void }) {
  const cols = view.matrix_factors
  const grid = `minmax(140px,1fr) repeat(${cols.length}, 64px) 12px 116px`
  return (
    <section className="an-card" style={{ padding: 0, overflow: 'hidden' }}>
      <div style={{ display: 'grid', gridTemplateColumns: grid, gap: 4, padding: '9px 16px', background: 'var(--panel2)', borderBottom: '1px solid var(--line)' }}>
        <span className="an-micro">holding</span>
        {cols.map((c) => <span key={c} className="an-micro" style={{ textAlign: 'center', overflow: 'hidden', textOverflow: 'ellipsis' }} title={names[c] ?? c}>{(names[c] ?? c).split(' ')[0]}</span>)}
        <span />
        <span className="an-micro">combined</span>
      </div>
      {view.holdings.map((h) => (
        <div key={h.ticker}>
          <div onClick={() => onToggle(h.ticker)} style={{ display: 'grid', gridTemplateColumns: grid, gap: 4, padding: '5px 16px', borderBottom: '1px solid var(--line)', cursor: 'pointer', alignItems: 'center' }}>
            <span style={{ fontSize: 12 }}>
              <b style={{ fontWeight: 600 }}>{h.ticker}</b> <span className="an-sub">{h.weight_pct != null ? `${h.weight_pct.toFixed(1)}%` : ''}</span>
            </span>
            {cols.map((c) => {
              const s = h.factor_scores[c]
              const l = h.links.find((x) => x.factor === c)
              const tone = s == null || s === 0 ? null : s < 0 ? 'var(--down)' : 'var(--up)'
              return (
                <span
                  key={c}
                  title={l ? `${names[c] ?? c} · ${l.channel}: ${l.ref ?? ''}` : names[c] ?? c}
                  style={{
                    textAlign: 'center',
                    fontSize: 12,
                    padding: '3px 0',
                    borderRadius: 2,
                    color: tone ?? 'var(--ink3)',
                    background: tone ? `color-mix(in srgb, ${tone} ${Math.abs(s!) >= 2 ? 20 : 10}%, transparent)` : 'transparent',
                  }}
                >
                  {MARK(s)}
                </span>
              )
            })}
            <span />
            <span>{h.verdict ? <VerdictChip v={h.verdict} /> : <span className="an-sub">no analysis</span>}</span>
          </div>
          {open === h.ticker && h.links.length > 0 && (
            <div className="ledger-drawer">
              {h.links.map((l) => (
                <div key={l.factor + l.channel} style={sans}>
                  <b style={{ color: 'var(--ink)', fontWeight: 600 }}>{names[l.factor] ?? l.factor}</b> · {l.ref}
                </div>
              ))}
            </div>
          )}
        </div>
      ))}
    </section>
  )
}

export function MacroScreen() {
  const [view, setView] = useState<MacroView | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [mode, setModeState] = useState<Mode>(() => (read(MODE_KEY, 'list') === 'matrix' ? 'matrix' : 'list'))
  const [factor, setFactorState] = useState(() => read(FACTOR_KEY, 'ALL'))
  const [open, setOpen] = useState<string | null>(null)

  useEffect(() => {
    fetchMacro().then(setView).catch((e) => setError(e.message))
  }, [])

  const setMode = (m: Mode) => {
    setModeState(m)
    write(MODE_KEY, m)
  }
  const setFactor = (f: string) => {
    setFactorState(f)
    write(FACTOR_KEY, f)
  }
  const names = Object.fromEntries((view?.factors ?? []).map((f) => [f.code, f.name]))
  const activeFactor = view && factor !== 'ALL' && !view.matrix_factors.includes(factor) ? 'ALL' : factor
  const sorted = view
    ? [...view.holdings].sort((a, b) => {
        const s = (h: MacroHolding) => (activeFactor === 'ALL' ? h.score : h.factor_scores[activeFactor] ?? null)
        const sa = s(a), sb = s(b)
        if (sa == null || sb == null) return sa == null ? 1 : -1
        return sa - sb || (b.weight_pct ?? 0) - (a.weight_pct ?? 0)
      })
    : []
  const groups = view
    ? (['trim', 'hold', 'add'] as const).map((g) => ({
        g,
        rows: view.holdings.filter((h) => h.verdict && (g === 'trim' ? h.verdict.includes('headwind') : g === 'add' ? h.verdict.includes('tailwind') : h.verdict === 'neutral')),
      }))
    : []

  return (
    <main style={{ maxWidth: 1240, margin: '0 auto', padding: '26px 20px 80px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', gap: 12, flexWrap: 'wrap', marginBottom: 16 }}>
        <h1 style={{ margin: 0, ...sans, fontSize: 24, fontWeight: 600, letterSpacing: '-.012em' }}>Macro</h1>
        {view?.tilt.verdict && (
          <span className="an-sub" style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            positioning read · book tilt <VerdictChip v={view.tilt.verdict} />
            <span>from {view.tilt.modelled} of {view.tilt.total} holdings</span>
          </span>
        )}
      </div>
      {error && <p style={{ color: 'var(--down)' }}>{error}</p>}
      {!view && !error && <p className="an-sub">Loading…</p>}
      {view && (
        <>
          {view.warnings.map((w) => <p key={w} style={{ color: 'var(--down)', fontSize: 11.5 }}>{w}</p>)}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(238px, 1fr))', gap: 12, marginBottom: 16 }}>
            {view.factors.map((f) => (
              <FactorCard key={f.code} f={f} selected={activeFactor === f.code} onSelect={() => { setMode('list'); setFactor(f.code) }} />
            ))}
          </div>

          <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', alignItems: 'center', marginBottom: 12 }}>
            <SegmentedControl options={[{ value: 'list', label: 'Ranked list' }, { value: 'matrix', label: 'Matrix' }]} value={mode} onChange={setMode} />
            {mode === 'list' ? (
              <>
                <SegmentedControl
                  options={[{ value: 'ALL', label: 'Combined' }, ...view.matrix_factors.map((c) => ({ value: c, label: (names[c] ?? c).split(' ')[0] }))]}
                  value={activeFactor}
                  onChange={setFactor}
                />
                <span className="an-sub">{activeFactor === 'ALL' ? 'sum of every factor, worst first' : `${names[activeFactor]} only`}</span>
              </>
            ) : (
              <span className="an-sub">−− strong headwind · − headwind · · flat · + tailwind · ++ strong tailwind (1-month move × analysis link)</span>
            )}
          </div>

          {mode === 'list' ? (
            <section className="an-card" style={{ padding: 0, overflow: 'hidden' }}>
              {sorted.map((h) => (
                <HoldingRow key={h.ticker} h={h} factor={activeFactor} names={names} open={open === h.ticker} onToggle={() => setOpen((o) => (o === h.ticker ? null : h.ticker))} />
              ))}
            </section>
          ) : (
            <Matrix view={view} names={names} open={open} onToggle={(t) => setOpen((o) => (o === t ? null : t))} />
          )}

          <section className="an-card" style={{ marginTop: 14 }}>
            <div className="an-head" style={{ marginBottom: 10 }}>
              <h2>Weight direction</h2>
              <span className="an-sub">{view.tilt.modelled} modelled · {view.tilt.total - view.tilt.modelled} without an analysis</span>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 14 }}>
              {groups.map(({ g, rows }) => (
                <div key={g}>
                  <div className="an-micro" style={{ marginBottom: 6 }}>{g}</div>
                  {rows.length === 0 ? (
                    <span className="an-sub">—</span>
                  ) : (
                    rows.map((h) => (
                      <div key={h.ticker} style={{ fontSize: 12 }}>
                        <b style={{ fontWeight: 600 }}>{h.ticker}</b> <span className="an-sub">{h.weight_pct != null ? `${h.weight_pct.toFixed(1)}%` : ''}</span>
                      </div>
                    ))
                  )}
                </div>
              ))}
            </div>
            <p className="an-sub" style={{ margin: '10px 0 0' }}>A positioning read from the macro backdrop only, not a trade signal.</p>
          </section>
        </>
      )}
    </main>
  )
}
