import type { ReactNode } from 'react'
import { Chip } from '../common/Chip'
import { currencySymbol, fmt, signed } from '../../lib/modelRows'
import { formatGbp } from '../../lib/format'
import type { AnalysisView, Lever, MacroLink } from '../../types/analysis'

const fmtDate = (iso: string | null | undefined) =>
  iso ? new Date(iso.length === 10 ? `${iso}T00:00:00` : iso).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' }) : '—'
const sans = { fontFamily: "'IBM Plex Sans', system-ui, sans-serif" } as const
const STRENGTH: Record<string, 'full' | 'half' | 'neutral'> = { strong: 'full', medium: 'full', mild: 'half', negligible: 'neutral' }

export function Panel({ title, note, children }: { title: string; note?: ReactNode; children: ReactNode }) {
  return (
    <section className="an-card">
      <div className="an-head" style={{ marginBottom: 10 }}>
        <h2>{title}</h2>
        {note && <span className="an-sub">{note}</span>}
      </div>
      {children}
    </section>
  )
}

function DirectionChip({ m }: { m: Pick<MacroLink, 'direction' | 'strength'> }) {
  const tone = m.direction === 'bull' ? 'up' : m.direction === 'bear' ? 'down' : 'neutral'
  const word = m.direction === 'bull' ? 'tailwind' : m.direction === 'bear' ? 'headwind' : 'neutral'
  return <Chip tone={tone} strength={STRENGTH[m.strength] ?? 'half'}>{m.strength} {word}</Chip>
}

/* ---------------- sensitivities (macro links) ---------------- */

function MacroBlock({ m, name }: { m: MacroLink; name: string }) {
  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0,1fr) auto', gap: '4px 12px', padding: '10px 0', borderTop: '1px solid var(--line)' }}>
      <span style={{ fontSize: 12.5 }}>
        <b style={{ fontWeight: 600 }}>{name}</b> <span className="an-sub">{m.factor} · {m.channel} · {m.speed}</span>
      </span>
      <DirectionChip m={m} />
      {m.ref && <span style={{ ...sans, fontSize: 12, color: 'var(--ink2)', gridColumn: '1 / -1' }}>{m.ref}</span>}
    </div>
  )
}

export function Sensitivities({ view, factorNames }: { view: AnalysisView; factorNames: Record<string, string> }) {
  const eps = view.macro.filter((m) => m.channel !== 'valuation')
  const multiple = view.macro.filter((m) => m.channel === 'valuation')
  const name = (code: string) => factorNames[code] ?? code
  return (
    <Panel title="Sensitivities" note="macro links from the analysis · % EPS impact not in v2 files">
      {eps.length === 0 && multiple.length === 0 && <p className="an-sub">None in this analysis.</p>}
      {eps.map((m) => <MacroBlock key={m.factor + m.channel} m={m} name={name(m.factor)} />)}
      {multiple.length > 0 && (
        <div style={{ marginTop: 14 }}>
          <div className="an-micro" style={{ marginBottom: 2 }}>Affects the multiple, not EPS</div>
          {multiple.map((m) => <MacroBlock key={m.factor + m.channel} m={m} name={name(m.factor)} />)}
        </div>
      )}
      {view.levers.length > 0 && <Levers levers={view.levers} />}
    </Panel>
  )
}

function Levers({ levers }: { levers: Lever[] }) {
  return (
    <div style={{ marginTop: 14 }}>
      <div className="an-micro" style={{ marginBottom: 2 }}>Lever register</div>
      {levers.map((l) => (
        <div key={l.lever_name} style={{ padding: '10px 0', borderTop: '1px solid var(--line)', display: 'grid', gap: 4 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', gap: 10, flexWrap: 'wrap' }}>
            <span style={{ fontSize: 12.5 }}>
              <b style={{ fontWeight: 600 }}>{l.lever_name}</b>{' '}
              <span className="an-sub">{l.base} · {l.exposure}{l.exposure_pct != null ? ` ${l.exposure_pct}%` : ''} · {l.speed}{l.macro_factor_code ? ` · ${l.macro_factor_code}` : ''}</span>
            </span>
            <Chip tone={l.direction === 'bull' ? 'up' : l.direction === 'bear' ? 'down' : 'neutral'} strength="half">{l.direction}</Chip>
          </div>
          {(l.watch_metric || l.current_reading) && (
            <span style={{ ...sans, fontSize: 12, color: 'var(--ink2)' }}>
              Watch {l.watch_metric ?? '—'}{l.current_reading ? `: ${l.current_reading}` : ''}
            </span>
          )}
          {(l.pushes_low || l.pushes_high) && (
            <span className="an-sub">
              {l.pushes_low && <>→ LOW if {l.pushes_low}</>}
              {l.pushes_low && l.pushes_high && ' · '}
              {l.pushes_high && <>→ HIGH if {l.pushes_high}</>}
            </span>
          )}
        </div>
      ))}
    </div>
  )
}

/* ---------------- sidebar ---------------- */

export function Thesis({ view }: { view: AnalysisView }) {
  return (
    <Panel title="Thesis" note={`as of ${fmtDate(view.data_as_of)}`}>
      <p style={{ ...sans, fontSize: 12.5, lineHeight: 1.55, margin: 0, color: 'var(--ink)' }}>
        {view.bottom_line ?? 'No bottom line in this analysis.'}
      </p>
    </Panel>
  )
}

export function WhatChanged({ view }: { view: AnalysisView }) {
  const wc = view.what_changed
  if (!wc) {
    return (
      <Panel title="What changed">
        <p className="an-sub" style={{ margin: 0 }}>First analysis on file, nothing to compare yet.</p>
      </Panel>
    )
  }
  const sym = currencySymbol(view.meta.reporting_currency)
  return (
    <Panel title="What changed" note={`vs ${fmtDate(wc.previous_as_of)}`}>
      <div style={{ display: 'grid', gap: 5, fontSize: 11.5 }}>
        {wc.rows.map((r) => {
          const d = (r.eps_now / r.eps_was - 1) * 100
          return (
            <div key={r.year} style={{ display: 'grid', gridTemplateColumns: '58px 1fr auto', gap: 8 }}>
              <span style={{ color: 'var(--ink3)' }}>{r.year}</span>
              <span>EPS {sym}{fmt(r.eps_was, 2)} → <b style={{ fontWeight: 600 }}>{sym}{fmt(r.eps_now, 2)}</b></span>
              <span style={{ color: Math.abs(d) < 0.05 ? 'var(--ink3)' : d > 0 ? 'var(--up)' : 'var(--down)' }}>{signed(d)}%</span>
            </div>
          )
        })}
        {wc.new_years.length > 0 && <span className="an-sub">New years: {wc.new_years.join(', ')}</span>}
        {wc.dropped_years.length > 0 && <span className="an-sub">Rolled off: {wc.dropped_years.join(', ')}</span>}
      </div>
    </Panel>
  )
}

export function PositionPanel({ view }: { view: AnalysisView }) {
  const p = view.position
  const psym = currencySymbol(view.price?.currency ?? view.meta.price_currency)
  return (
    <Panel title="Position">
      {!p ? (
        <p className="an-sub" style={{ margin: 0 }}>Not held.</p>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px 14px' }}>
          {[
            ['held', `${fmt(p.quantity, p.quantity % 1 ? 4 : 0)} sh`],
            ['avg cost', `${psym}${fmt(p.avg_price, 2)}`],
            ['value', formatGbp(p.value_gbp)],
            ['weight', p.weight_pct != null ? `${fmt(p.weight_pct)}% of book` : '—'],
          ].map(([l, v]) => (
            <div key={l}>
              <div className="an-micro">{l}</div>
              <div style={{ fontSize: 13 }}>{v}</div>
            </div>
          ))}
          <div style={{ gridColumn: '1 / -1' }}>
            <div className="an-micro">P&amp;L</div>
            <div style={{ fontSize: 13, color: p.ppl_gbp >= 0 ? 'var(--up)' : 'var(--down)' }}>
              {p.ppl_gbp >= 0 ? '+' : '−'}{formatGbp(Math.abs(p.ppl_gbp))} ({signed(p.ppl_pct)}%)
            </div>
          </div>
        </div>
      )}
    </Panel>
  )
}

export function Upcoming({ view }: { view: AnalysisView }) {
  return (
    <Panel title="Upcoming" note="from the analysis calendar">
      {view.calendar.length === 0 ? (
        <p className="an-sub" style={{ margin: 0 }}>Nothing dated ahead.</p>
      ) : (
        <div style={{ display: 'grid', gap: 6 }}>
          {view.calendar.map((e) => (
            <div key={e.date + e.event} style={{ display: 'grid', gridTemplateColumns: '84px 1fr', gap: 8, fontSize: 11.5 }}>
              <span style={{ color: 'var(--ink3)' }}>{fmtDate(e.date)}</span>
              <span style={sans}>
                {e.event}
                {e.confirmed === false && <span className="an-sub"> · unconfirmed</span>}
              </span>
            </div>
          ))}
        </div>
      )}
    </Panel>
  )
}

export function DataSource({ view }: { view: AnalysisView }) {
  const m = view.meta
  return (
    <Panel title="Data source">
      <div style={{ display: 'grid', gap: 6, fontSize: 11.5, color: 'var(--ink2)' }}>
        <span>data as of <b style={{ color: 'var(--ink)', fontWeight: 500 }}>{fmtDate(view.data_as_of)}</b> · added {fmtDate(view.ingested_at)}</span>
        {m.data_sources?.length ? <span>{m.data_sources.join(' · ')}</span> : null}
        {m.structure_note && <span style={sans}>{m.structure_note}</span>}
        <span className="an-sub">EPS in {m.reporting_currency ?? '—'} · price in {m.price_currency ?? '—'} · fiscal year ends {(m as { fiscal_year_end?: string }).fiscal_year_end ?? '—'}</span>
      </div>
    </Panel>
  )
}
