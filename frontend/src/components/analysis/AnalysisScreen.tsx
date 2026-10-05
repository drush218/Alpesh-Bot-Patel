import { useCallback, useEffect, useState } from 'react'
import { fetchAnalysis } from '../../lib/apiClient'
import { formatGbp } from '../../lib/format'
import { currencySymbol, signed } from '../../lib/modelRows'
import type { AnalysisView, WorkspaceResult } from '../../types/analysis'
import { DataSource, Panel, PositionPanel, Sensitivities, Thesis, Upcoming, WhatChanged } from './InfoPanels'
import { ScenarioWorkspace } from './ScenarioWorkspace'
import { Scorecard } from './Scorecard'
import { BauBridge, LiveValuation, MULTIPLES, MultipleControl, ScenarioBandChart } from './ValuationPanels'

const MULT_KEY = 'pt.referenceMultiple'

function loadMultiple(): number {
  try {
    const v = Number(localStorage.getItem(MULT_KEY))
    return (MULTIPLES as readonly number[]).includes(v) ? v : 30
  } catch {
    return 30
  }
}

const fmtDate = (iso: string | null | undefined) =>
  iso ? new Date(`${iso}T00:00:00`).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' }) : '—'

function Metric({ label, value, tone }: { label: string; value: string; tone?: 'up' | 'down' }) {
  return (
    <div>
      <div className="an-micro">{label}</div>
      <div style={{ fontSize: 15, fontWeight: 600, color: tone ? `var(--${tone})` : 'var(--ink)' }}>{value}</div>
    </div>
  )
}

export function AnalysisScreen({ ticker, onSize }: { ticker: string; onSize: (t: string) => void }) {
  const [view, setView] = useState<AnalysisView | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [base, setBase] = useState<WorkspaceResult | null>(null)
  const [multiple, setMultipleState] = useState(loadMultiple)
  const onBaseLoaded = useCallback((r: WorkspaceResult) => setBase(r), [])

  const setMultiple = (m: number) => {
    setMultipleState(m)
    try {
      localStorage.setItem(MULT_KEY, String(m))
    } catch {
      /* per-browser convenience only */
    }
  }

  useEffect(() => {
    fetchAnalysis(ticker).then(setView).catch((e) => setError(e.message))
  }, [ticker])

  const meta = view?.meta
  const price = view?.price ?? null
  const psym = currencySymbol(price?.currency ?? meta?.price_currency)
  const ref = meta?.reference_price
  const sinceStrike = price && ref ? (price.close / ref.value - 1) * 100 : null
  const pos = view?.position
  const years = base?.base_inputs.meta.forecast_years ?? []

  return (
    <main style={mainStyle}>
      {error && <p style={{ color: 'var(--down)' }}>{error}</p>}

      {view && (view.stale.is_stale || view.warnings.length > 0) && (
        <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginBottom: 16 }}>
          {view.stale.is_stale && (
            <div className="an-callout" style={{ flex: '1 1 320px', marginBottom: 0 }}>
              <span className="k">STALE</span>
              <span>Struck on {fmtDate(view.data_as_of)} data; {ticker} has reported since ({fmtDate(view.stale.last_earnings)}). Re-run the analysis to refresh it.</span>
            </div>
          )}
          {view.warnings.length > 0 && (
            <div className="an-callout" style={{ flex: '1 1 320px', marginBottom: 0, borderColor: 'var(--line)', background: 'var(--panel)' }}>
              <span className="k" style={{ color: 'var(--ink2)' }}>PARSE</span>
              <ul>{view.warnings.map((w) => <li key={w}>{w}</li>)}</ul>
            </div>
          )}
        </div>
      )}

      <div style={{ display: 'flex', alignItems: 'baseline', gap: 12, flexWrap: 'wrap', marginBottom: 10 }}>
        <span style={{ fontSize: 26, fontWeight: 600, letterSpacing: '.02em' }}>{ticker}</span>
        {meta && <span style={{ fontFamily: "'IBM Plex Sans', system-ui, sans-serif", fontSize: 15, color: 'var(--ink2)' }}>{meta.company}</span>}
        {meta?.exchange && (
          <span style={{ fontSize: 10.5, letterSpacing: '.06em', border: '1px solid var(--line2)', borderRadius: 2, padding: '1px 6px', color: 'var(--ink2)' }}>
            {meta.exchange}
          </span>
        )}
      </div>
      {view && (
        <div style={{ display: 'flex', gap: 28, flexWrap: 'wrap', marginBottom: 20 }}>
          <Metric label="price now" value={price ? `${psym}${price.close.toFixed(2)}` : '—'} />
          <Metric
            label={ref ? `since strike (${psym}${ref.value.toFixed(2)})` : 'since strike'}
            value={sinceStrike != null ? `${signed(sinceStrike)}%` : '—'}
            tone={sinceStrike == null ? undefined : sinceStrike >= 0 ? 'up' : 'down'}
          />
          <Metric label="weight" value={pos?.weight_pct != null ? `${pos.weight_pct.toFixed(1)}%` : '—'} />
          <Metric
            label="P&L"
            value={pos ? `${pos.ppl_gbp >= 0 ? '+' : '−'}${formatGbp(Math.abs(pos.ppl_gbp))} · ${signed(pos.ppl_pct)}%` : '—'}
            tone={pos ? (pos.ppl_gbp >= 0 ? 'up' : 'down') : undefined}
          />
        </div>
      )}

      <div className="an-grid">
        <div style={{ minWidth: 0, display: 'grid', gap: 14 }}>
          {base && (
            <>
              <Panel title="Price vs scenario band" note={<MultipleControl value={multiple} onChange={setMultiple} />}>
                <ScenarioBandChart outputs={base.base_outputs} years={years} price={price} epsCcy={meta?.reporting_currency} multiple={multiple} />
                <p className="an-sub" style={{ margin: '6px 0 0' }}>
                  Implied price = EPS × {multiple}× for LOW, BAU and HIGH, from the base analysis.
                </p>
              </Panel>
              <Panel title="Live valuation" note={`reference multiple ${multiple}×`}>
                <LiveValuation outputs={base.base_outputs} years={years} price={price} epsCcy={meta?.reporting_currency} multiple={multiple} />
              </Panel>
            </>
          )}
          <ScenarioWorkspace key={ticker} ticker={ticker} onBaseLoaded={onBaseLoaded} />
          {view && <Sensitivities view={view} factorNames={view.factor_names} />}
          {base && <BauBridge outputs={base.base_outputs} years={years} epsCcy={meta?.reporting_currency} />}
        </div>
        <aside>
          <Scorecard key={ticker} ticker={ticker} />
          {view && (
            <>
              <Thesis view={view} />
              <WhatChanged view={view} />
              <PositionPanel view={view} onSize={() => onSize(ticker)} />
              <Upcoming view={view} />
              <DataSource view={view} />
            </>
          )}
        </aside>
      </div>
    </main>
  )
}

const mainStyle = {
  maxWidth: 1240,
  margin: '0 auto',
  padding: '26px 20px 80px',
} as const
