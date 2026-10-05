import { useCallback, useState } from 'react'
import { currencySymbol } from '../../lib/modelRows'
import type { WorkspaceResult } from '../../types/analysis'
import { ScenarioWorkspace } from './ScenarioWorkspace'
import { Scorecard } from './Scorecard'

export function AnalysisScreen({ ticker }: { ticker: string }) {
  const [base, setBase] = useState<WorkspaceResult | null>(null)
  const onBaseLoaded = useCallback((r: WorkspaceResult) => setBase(r), [])
  const meta = base?.base_inputs.meta
  const ref = meta?.reference_price

  return (
    <main style={mainStyle}>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 12, flexWrap: 'wrap', marginBottom: 6 }}>
        <span style={{ fontSize: 26, fontWeight: 600, letterSpacing: '.02em' }}>{ticker}</span>
        {meta && (
          <span style={{ fontFamily: "'IBM Plex Sans', system-ui, sans-serif", fontSize: 15, color: 'var(--ink2)' }}>
            {meta.company}
          </span>
        )}
        {meta?.exchange && (
          <span style={{ fontSize: 10.5, letterSpacing: '.06em', border: '1px solid var(--line2)', borderRadius: 2, padding: '1px 6px', color: 'var(--ink2)' }}>
            {meta.exchange}
          </span>
        )}
      </div>
      {meta && (
        <div style={{ display: 'flex', gap: 22, flexWrap: 'wrap', fontSize: 11, color: 'var(--ink3)', marginBottom: 20 }}>
          {base?.price && (
            <span>
              current price <b style={{ color: 'var(--ink)', fontWeight: 500 }}>{currencySymbol(base.price.currency)}{base.price.close.toFixed(2)}</b>
            </span>
          )}
          {ref && (
            <span>
              analysis struck <b style={{ color: 'var(--ink)', fontWeight: 500 }}>{meta.data_as_of}</b> at {currencySymbol(base?.price?.currency)}{ref.value.toFixed(2)}
            </span>
          )}
          <span>base year <b style={{ color: 'var(--ink)', fontWeight: 500 }}>{meta.base_year}</b></span>
          {meta.units && <span>units <b style={{ color: 'var(--ink)', fontWeight: 500 }}>{meta.units}</b> · {meta.reporting_currency}</span>}
        </div>
      )}

      <div className="an-grid">
        <div style={{ minWidth: 0 }}>
          <ScenarioWorkspace key={ticker} ticker={ticker} onBaseLoaded={onBaseLoaded} />
        </div>
        <aside>
          <Scorecard key={ticker} ticker={ticker} />
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
